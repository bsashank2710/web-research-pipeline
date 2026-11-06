"""Plan queries, bind schema fields to page evidence, and reject bad citations.

The first attempt searches the question itself. Later attempts add a query per
field and open pages that were not opened yet. A value is kept only when the
page is about the named entity, the value has the right type, and the quote
is text that was actually fetched.
"""

from __future__ import annotations

import re

from research.model import Answer, Citation, Field, Page, Schema
from research.parse import clean, sentences

STOP = {
    "a", "an", "the", "of", "was", "were", "is", "are", "it", "its", "by", "in",
    "for", "and", "or", "to", "that", "this", "with", "from", "on", "as", "be",
    "at", "who", "what", "when", "where", "which", "why", "how", "did", "does",
    "do", "person", "organization", "place", "number",
}

_WH = {"what", "who", "when", "where", "which", "why", "how"}
_EXTRA = {
    "founded": {"established", "founding"},
    "founder": {"founded"},
    "product": {"product"},
    "population": {"residents", "inhabitants"},
    "mayor": {"mayor"},
    "incorporated": {"incorporation"},
    "released": {"shipped", "launched", "release"},
    "release": {"released", "shipped", "launched"},
    "maker": {"manufacturer"},
    "price": {"cost"},
}


def entity_phrase(question: str) -> str:
    phrases = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", question)
    phrases = [phrase for phrase in phrases if phrase.lower() not in _WH]
    if not phrases:
        raise ValueError("question has no proper noun to search for")
    return phrases[-1]


def field_terms(field: Field) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", f"{field.name.replace('_', ' ')} {field.description}".lower()))
    words -= STOP
    extra: set[str] = set()
    for word in words:
        extra |= _EXTRA.get(word, set())
    return {word for word in words | extra if word not in STOP}


def queries_for(question: str, schema: Schema, attempt: int) -> list[str]:
    planned = [question]
    if attempt > 1:
        entity = entity_phrase(question)
        for field in schema.fields:
            terms = " ".join(sorted(field_terms(field))[:4])
            planned.append(f"{entity} {terms}".strip())
    unique: list[str] = []
    for query in planned:
        if query not in unique:
            unique.append(query)
    return unique


def depth_for(attempt: int) -> int:
    return min(3 * attempt, 9)


def _label_score(label: str, terms: set[str]) -> int:
    low = label.lower()
    words = set(re.findall(r"[a-z0-9]+", low))
    score = 0
    for term in terms:
        if " " in term and term in low:
            score += 2
        elif term in words:
            score += 1
    return score


def _coerce(field: Field, raw: str):
    text = clean(raw)
    if field.type == "integer":
        match = re.search(r"\d+", text)
        if match is None:
            return None
        number = int(match.group())
        if field.year and not 1000 <= number <= 2100:
            return None
        return number
    if field.type == "string":
        if not text or text.isdigit():
            return None
        return text
    return None


def _quote(page: Page, value: object, entity: str, terms: set[str]) -> str | None:
    needle = str(value).lower()
    found: list[tuple[int, int, str]] = []
    for sentence in sentences(page.text):
        low = sentence.lower()
        if needle not in low:
            continue
        score = 3 if entity.lower() in low else 0
        score += sum(1 for term in terms if term in low)
        found.append((score, -len(sentence), sentence))
    if not found:
        return None
    found.sort(reverse=True)
    return found[0][2]


def citation_error(citation: Citation, pages: list[Page], entity: str, value: object) -> str | None:
    page = next((item for item in pages if item.url == citation.url), None)
    if page is None:
        return f"{citation.field}: citation url was not fetched"
    quote = clean(citation.quote)
    if quote.lower() not in clean(page.text).lower():
        return f"{citation.field}: quote is not on the page"
    if str(value).lower() not in quote.lower():
        return f"{citation.field}: value is not in the quote"
    if entity.lower() not in page.title.lower() and entity.lower() not in quote.lower():
        return f"{citation.field}: page is not about {entity}"
    return None


def _relevant(pages: list[Page], entity: str) -> list[Page]:
    key = entity.lower()
    return [page for page in pages if key in page.title.lower()]


def _from_facts(field: Field, entity: str, pages: list[Page], terms: set[str]):
    best = None
    for page in pages:
        for label, raw in page.facts:
            score = _label_score(label, terms)
            if score <= 0:
                continue
            value = _coerce(field, raw)
            if value is None:
                continue
            quote = _quote(page, value, entity, terms)
            if quote is None:
                continue
            if best is None or score > best[0]:
                best = (score, value, Citation(field.name, page.url, quote))
    if best is None:
        return None
    return best[1], best[2]


def _from_sentences(field: Field, entity: str, pages: list[Page], terms: set[str]):
    best = None
    for page in pages:
        for sentence in sentences(page.text):
            low = sentence.lower()
            if entity.lower() not in low or not any(term in low for term in terms):
                continue
            value = _pull(field, sentence, terms)
            if value is None:
                continue
            score = sum(1 for term in terms if term in low)
            if best is None or score > best[0]:
                best = (score, value, Citation(field.name, page.url, sentence))
    if best is None:
        return None
    return best[1], best[2]


def _pull(field: Field, sentence: str, terms: set[str]):
    if field.type == "integer":
        numbers = [int(item) for item in re.findall(r"\d+", sentence)]
        if field.year:
            numbers = [number for number in numbers if 1000 <= number <= 2100]
        return numbers[0] if numbers else None
    for pattern in (
        r"\bfounded by ([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        r"\bmayor of [A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)* is ([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        r"\bmade by ([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
        r"\bfirst product was ([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)",
    ):
        match = re.search(pattern, sentence)
        if match and any(term in sentence.lower() for term in terms):
            return match.group(1)
    return None


def extract(question: str, schema: Schema, pages: list[Page]) -> Answer:
    try:
        entity = entity_phrase(question)
    except ValueError as exc:
        return Answer(False, {}, (), 0, (str(exc),))
    chosen = _relevant(pages, entity)
    values: dict = {}
    citations: list[Citation] = []
    errors: list[str] = []
    for field in schema.fields:
        terms = field_terms(field)
        found = _from_facts(field, entity, chosen, terms) or _from_sentences(field, entity, chosen, terms)
        if found is None:
            errors.append(f"no grounded value for {field.name}")
            continue
        value, citation = found
        problem = citation_error(citation, chosen, entity, value)
        if problem:
            errors.append(problem)
            continue
        values[field.name] = value
        citations.append(citation)
    if errors or len(values) != len(schema.fields):
        return Answer(False, {}, (), 0, tuple(errors or ["incomplete answer"]))
    return Answer(True, values, tuple(citations), 0, ())


def check_proposal(proposal: Answer, schema: Schema, pages: list[Page], entity: str) -> Answer:
    if set(proposal.values) != {field.name for field in schema.fields}:
        return Answer(False, {}, (), 0, ("proposal does not match the schema",))
    for field in schema.fields:
        value = proposal.values[field.name]
        if field.type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            return Answer(False, {}, (), 0, (f"{field.name} must be an integer",))
        if field.type == "string" and not isinstance(value, str):
            return Answer(False, {}, (), 0, (f"{field.name} must be a string",))
        if field.year and isinstance(value, int) and not 1000 <= value <= 2100:
            return Answer(False, {}, (), 0, (f"{field.name} is outside the year range",))
    by_field = {item.field: item for item in proposal.citations}
    for field in schema.fields:
        citation = by_field.get(field.name)
        if citation is None:
            return Answer(False, {}, (), 0, (f"{field.name}: missing citation",))
        problem = citation_error(citation, pages, entity, proposal.values[field.name])
        if problem:
            return Answer(False, {}, (), 0, (problem,))
    return Answer(True, dict(proposal.values), proposal.citations, 0, ())


def run(question: str, schema: Schema, web, answerer=None, max_attempts: int = 3) -> Answer:
    """Fetch, then accept an answerer proposal only if it is cited. Otherwise extract."""
    opened: dict[str, Page] = {}
    errors: list[str] = []
    for attempt in range(1, max_attempts + 1):
        try:
            planned = queries_for(question, schema, attempt)
            entity = entity_phrase(question)
        except ValueError as exc:
            return Answer(False, {}, (), attempt, (str(exc),))
        for query in planned:
            try:
                urls = web.search(query)
            except Exception as exc:
                errors.append(f"search failed: {exc}")
                continue
            for url in urls[: depth_for(attempt)]:
                if url in opened:
                    continue
                try:
                    opened[url] = web.open(url)
                except Exception as exc:
                    errors.append(f"{url}: {exc}")
        pages = list(opened.values())
        if answerer is not None:
            proposal = answerer.propose(question, schema, pages)
            checked = check_proposal(proposal, schema, pages, entity)
            if checked.ok:
                checked.attempts = attempt
                return checked
            errors.extend(checked.errors)
        extracted = extract(question, schema, pages)
        if extracted.ok:
            extracted.attempts = attempt
            return extracted
        errors.extend(extracted.errors)
    return Answer(False, {}, (), max_attempts, tuple(errors))
