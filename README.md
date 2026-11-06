# Web research pipeline

A question and a JSON schema go in. The pipeline plans queries, opens pages, and returns JSON. Every value has to appear in a quote from a page it fetched. A proposal that cites a sentence it did not fetch is thrown out, and the run tries again with a narrower query.

The bundled run is an encyclopedia of ten local pages, including distractors (a lecture page that mentions Northwind, a workshop founded in 1972, a second company that sells to Northwind). On those ten held-out questions the score is 10/10, and the first query is enough. That is this fixture. It is not a measurement of the open web, and this repo does not measure a 70% cut in research time.

## Run

```bash
pip install -e ".[dev]"
pytest -q
python -m research demo
python -m research eval
```

`demo` prints the JSON for "What year was Northwind Labs founded?". `eval` prints `held-out accuracy 10/10`.

Against a site that serves the same HTML:

```bash
python -m research ask "Who is the mayor of Cedar County?" --schema schema.json --browser http --base http://127.0.0.1:8000
python -m research ask "Who is the mayor of Cedar County?" --schema schema.json --browser playwright --base http://127.0.0.1:8000
```

Playwright is optional (`pip install -e ".[browser]"` and `playwright install chromium`). The eval uses the in-process corpus so it does not need a browser or a network. `HttpBrowser` and `PlaywrightBrowser` both read the search page (`a.result`) and then the article. The Playwright path is tested with a fake browser that returns that HTML. `ChromiumSession` is the real launcher.

## How a value is accepted

1. The proper noun in the question is the entity. "What year was Northwind Labs founded?" searches for Northwind Labs.
2. Attempt one searches that question and opens the top three hits. If a field is still empty, later attempts add a query per field and open pages not yet opened.
3. A page counts only when the entity is in the title. Body mentions are not enough, which is why the lecture page does not answer for Northwind.
4. Fact rows whose label shares a word with the field win. "Founder" does not match "founded", so the founder is not parsed as a year. A year field rejects values outside 1000–2100, which drops the price 49 on the product page.
5. The quote has to contain the value and be a substring of the fetched text. The 1972 sentence is about a workshop, and the fact row says 2014, so the answer is 2014.

An answerer, if you pass one, may propose the JSON. The same citation check applies. If it fails, extraction runs.

## Limits

The extractor knows a small set of field words (founded, mayor, population, released, maker). A schema about something else will return `ok: false` rather than guess. Search is lexical. There is no ranking model and no live search engine in this repo.

## License

MIT.
