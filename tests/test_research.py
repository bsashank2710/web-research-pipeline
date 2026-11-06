import json
import threading
from urllib.parse import parse_qs, urlparse

from research.browser import HttpBrowser, PlaywrightBrowser, load_corpus, render_search, serve
from research.engine import check_proposal, run
from research.model import Answer, Citation, Schema
from research.pages import HELD_OUT, HTML


def test_held_out_is_exact_and_cited():
    web = load_corpus()
    for item in HELD_OUT:
        result = run(item["question"], Schema.from_json(item["schema"]), web)
        assert result.ok, (item["id"], result.errors)
        assert result.attempts == 1
        for key, value in item["gold"].items():
            assert result.values[key] == value
        assert len(result.citations) == len(item["gold"])
        for citation in result.citations:
            page = web.open(citation.url)
            assert citation.quote in page.text
            assert str(result.values[citation.field]) in citation.quote


def test_distractor_year_is_not_the_answer():
    item = next(row for row in HELD_OUT if row["id"] == "northwind-year")
    result = run(item["question"], Schema.from_json(item["schema"]), load_corpus())
    assert result.values["founding_year"] == 2014


def test_retry_opens_the_page_the_first_query_missed():
    web = load_corpus()

    class Narrow:
        def search(self, query: str) -> list[str]:
            if query.startswith("What year was Northwind"):
                return ["https://corpus.local/lectures"]
            return ["https://corpus.local/northwind"]

        def open(self, url: str):
            return web.open(url)

    item = next(row for row in HELD_OUT if row["id"] == "northwind-year")
    result = run(item["question"], Schema.from_json(item["schema"]), Narrow())
    assert result.ok
    assert result.values["founding_year"] == 2014
    assert result.attempts == 2


def test_uncited_proposal_is_rejected_and_extraction_is_used():
    web = load_corpus()
    item = next(row for row in HELD_OUT if row["id"] == "northwind-year")
    schema = Schema.from_json(item["schema"])

    class Liar:
        def propose(self, question, schema, pages):
            url = pages[0].url
            return Answer(
                True,
                {"founding_year": 1972},
                (Citation("founding_year", url, "this sentence was not fetched"),),
                0,
                (),
            )

    result = run(item["question"], schema, web, answerer=Liar())
    assert result.values["founding_year"] == 2014
    proposal = Liar().propose(item["question"], schema, [web.open("https://corpus.local/northwind")])
    checked = check_proposal(proposal, schema, list(web.pages), "Northwind Labs")
    assert not checked.ok
    assert "quote is not on the page" in checked.errors[0]


def test_question_without_an_entity_is_json_and_not_ok():
    schema = Schema.from_json(HELD_OUT[0]["schema"])
    result = run("what year was it founded?", schema, load_corpus())
    assert not result.ok
    json.dumps(result.to_json())


def test_http_browser_answers_from_the_local_server():
    site = load_corpus()
    server = serve(HTML, lambda query: render_search(site, query))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        item = next(row for row in HELD_OUT if row["id"] == "cedar-mayor")
        result = run(
            item["question"],
            Schema.from_json(item["schema"]),
            HttpBrowser(f"http://127.0.0.1:{port}"),
        )
        assert result.ok
        assert result.values["mayor"] == "Jonah Hale"
    finally:
        server.shutdown()
        server.server_close()


def test_playwright_browser_uses_the_same_search_page():
    site = load_corpus()

    class FakePage:
        def __init__(self, fetch):
            self.fetch = fetch
            self.html = ""

        def goto(self, url, **kwargs):
            self.html = self.fetch(url)

        def content(self):
            return self.html

        def close(self):
            return None

    class FakeBrowser:
        def new_page(self):
            return FakePage(fetch)

    def fetch(url: str) -> str:
        parsed = urlparse(url)
        if parsed.path == "/search":
            return render_search(site, parse_qs(parsed.query)["q"][0])
        return HTML[parsed.path.strip("/")]

    item = next(row for row in HELD_OUT if row["id"] == "ledger-maker")
    result = run(
        item["question"],
        Schema.from_json(item["schema"]),
        PlaywrightBrowser("http://search.local", FakeBrowser()),
    )
    assert result.values["maker"] == "Kepler Transit"
