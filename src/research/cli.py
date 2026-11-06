"""Command line. `eval` scores the bundled held-out questions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research.browser import ChromiumSession, CorpusWeb, HttpBrowser, PlaywrightBrowser, load_corpus
from research.engine import run
from research.model import Schema
from research.pages import HELD_OUT


def score(web: CorpusWeb | None = None) -> tuple[int, int, list[str]]:
    site = web or load_corpus()
    misses = []
    correct = 0
    for item in HELD_OUT:
        result = run(item["question"], Schema.from_json(item["schema"]), site)
        gold = item["gold"]
        if result.ok and all(result.values.get(key) == value for key, value in gold.items()):
            correct += 1
        else:
            misses.append(item["id"])
    return correct, len(HELD_OUT), misses


def _web_from_args(args):
    if args.browser == "memory":
        return load_corpus(), None
    if args.browser == "http":
        if not args.base:
            raise SystemExit("--base is required for the http browser")
        return HttpBrowser(args.base), None
    if not args.base:
        raise SystemExit("--base is required for the playwright browser")
    session = ChromiumSession()
    browser = session.__enter__()
    return PlaywrightBrowser(args.base, browser), session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="research")
    parser.add_argument("--browser", choices=("memory", "http", "playwright"), default="memory")
    parser.add_argument("--base", default="")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo")
    demo.add_argument("--id", default="northwind-year")
    sub.add_parser("eval")
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--schema", required=True, help="path to a JSON schema file")

    args = parser.parse_args(argv)
    web, session = _web_from_args(args)
    try:
        if args.cmd == "eval":
            correct, total, misses = score(web)
            print(f"held-out accuracy {correct}/{total}")
            if misses:
                print("misses: " + ", ".join(misses))
            return 0 if correct == total else 1
        if args.cmd == "demo":
            item = next(row for row in HELD_OUT if row["id"] == args.id)
            question, schema = item["question"], Schema.from_json(item["schema"])
        else:
            question = args.question
            schema = Schema.from_json(json.loads(Path(args.schema).read_text(encoding="utf-8")))
        result = run(question, schema, web)
        json.dump(result.to_json(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if result.ok else 1
    finally:
        if session is not None:
            session.__exit__(None, None, None)
