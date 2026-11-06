"""HTML to title, prose, and fact rows. The corpus HTML is deliberately simple."""

from __future__ import annotations

import re
from html.parser import HTMLParser

from research.model import Page

_SPACE = re.compile(r"\s+")


def clean(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", clean(text))
    return [part for part in parts if part]


class _Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts: list[str] = []
        self.facts: list[tuple[str, str]] = []
        self._capture: str | None = None
        self._buf: list[str] = []
        self._pending_th: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"title", "h1", "th", "td", "p", "li"}:
            self._capture = tag
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture != tag:
            return
        text = clean(" ".join(self._buf))
        if tag == "title" and text:
            self.title = text
        elif tag == "h1" and text:
            if not self.title:
                self.title = text
            self.parts.append(text + ".")
        elif tag == "th":
            self._pending_th = text
        elif tag == "td" and self._pending_th:
            self.facts.append((self._pending_th, text))
            self._pending_th = None
        elif tag in {"p", "li"} and text:
            self.parts.append(text if text.endswith((".", "!", "?")) else text + ".")
        self._capture = None

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buf.append(data)


def parse_html(url: str, html: str) -> Page:
    document = _Document()
    document.feed(html)
    document.close()
    for label, value in document.facts:
        document.parts.append(f"{label}: {value}.")
    return Page(url, document.title, clean(" ".join(document.parts)), tuple(document.facts))
