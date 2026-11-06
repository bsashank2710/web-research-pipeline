"""Three ways to open the same pages: in memory, HTTP, or Playwright."""

from __future__ import annotations

import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import urlopen

from research.engine import STOP
from research.model import Page
from research.parse import parse_html

_RESULT = re.compile(r'<a class="result" href="([^"]+)">')


def result_hrefs(html: str) -> list[str]:
    return _RESULT.findall(html)


def absolutize(base: str, hrefs: list[str]) -> list[str]:
    root = base.rstrip("/")
    urls = []
    for href in hrefs:
        if href.startswith("http://") or href.startswith("https://"):
            urls.append(href)
        else:
            urls.append(root + "/" + href.lstrip("/"))
    return urls


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOP and len(token) > 1]


class CorpusWeb:
    """Search and open the bundled pages without a socket."""

    def __init__(self, pages: list[Page]) -> None:
        self.pages = pages
        self.by_url = {page.url: page for page in pages}

    def search(self, query: str) -> list[str]:
        tokens = _tokens(query)
        ranked: list[tuple[int, str]] = []
        for page in self.pages:
            title = page.title.lower()
            text = page.text.lower()
            score = 0
            for token in tokens:
                if token in title:
                    score += 3
                elif token in text:
                    score += 1
            if score:
                ranked.append((score, page.url))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [url for _, url in ranked]

    def open(self, url: str) -> Page:
        try:
            return self.by_url[url]
        except KeyError as exc:
            raise KeyError(url) from exc


def render_search(web: CorpusWeb, query: str) -> str:
    links = []
    for url in web.search(query)[:8]:
        page = web.by_url[url]
        href = "/" + url.rstrip("/").split("/")[-1]
        title = page.title.replace("&", "&amp;").replace("<", "&lt;")
        links.append(f'<a class="result" href="{href}">{title}</a>')
    body = "\n".join(links)
    return f"<!DOCTYPE html><html><head><title>Search</title></head><body>{body}</body></html>"


class HttpBrowser:
    def __init__(self, base_url: str, timeout: float = 5) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, query: str) -> list[str]:
        html = self._get(f"/search?q={quote(query)}")
        return absolutize(self.base, result_hrefs(html))

    def open(self, url: str) -> Page:
        return parse_html(url, self._get_absolute(url))

    def _get(self, path: str) -> str:
        return self._get_absolute(self.base + path)

    def _get_absolute(self, url: str) -> str:
        with urlopen(url, timeout=self.timeout) as response:
            return response.read().decode("utf-8")


class PlaywrightBrowser:
    """Same contract as HttpBrowser. `browser` is a Playwright browser, or a fake with new_page()."""

    def __init__(self, base_url: str, browser) -> None:
        self.base = base_url.rstrip("/")
        self.browser = browser

    def search(self, query: str) -> list[str]:
        html = self._html(f"{self.base}/search?q={quote(query)}")
        return absolutize(self.base, result_hrefs(html))

    def open(self, url: str) -> Page:
        return parse_html(url, self._html(url))

    def _html(self, url: str) -> str:
        page = self.browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return page.content()
        finally:
            page.close()


class ChromiumSession:
    """Launch headless Chromium. Used by the CLI, not by the fixture eval."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(headless=True)
        return self.browser

    def __exit__(self, exc_type, exc, tb) -> None:
        self.browser.close()
        self._playwright.stop()


def serve(html_by_slug: dict[str, str], search_page):
    """Serve slug HTML and a search page on 127.0.0.1. Returns the live server."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/search":
                query = parse_qs(parsed.query).get("q", [""])[0]
                body = search_page(query)
                status = 200
            else:
                body = html_by_slug.get(parsed.path.strip("/"))
                status = 200 if body is not None else 404
                if body is None:
                    body = "not found"
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return server


def load_corpus(base: str = "https://corpus.local") -> CorpusWeb:
    from research.pages import HTML

    pages = [parse_html(f"{base.rstrip('/')}/{slug}", html) for slug, html in HTML.items()]
    return CorpusWeb(pages)
