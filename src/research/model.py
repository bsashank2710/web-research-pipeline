"""Types shared by the planner, the browsers, and the checker."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    description: str

    @property
    def year(self) -> bool:
        return "year" in f"{self.name} {self.description}".lower()


@dataclass(frozen=True)
class Schema:
    fields: tuple[Field, ...]

    @staticmethod
    def from_json(data: dict) -> "Schema":
        if data.get("type") != "object":
            raise ValueError("schema type must be object")
        props = data.get("properties")
        if not isinstance(props, dict) or not props:
            raise ValueError("schema needs properties")
        required = data.get("required", list(props))
        fields = []
        for name in required:
            spec = props.get(name)
            if not isinstance(spec, dict) or spec.get("type") not in {"string", "integer"}:
                raise ValueError(f"unsupported field {name}")
            fields.append(Field(name, spec["type"], str(spec.get("description", name))))
        return Schema(tuple(fields))


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    text: str
    facts: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Citation:
    field: str
    url: str
    quote: str


@dataclass
class Answer:
    ok: bool
    values: dict
    citations: tuple[Citation, ...]
    attempts: int
    errors: tuple[str, ...]

    def to_json(self) -> dict:
        answer = None
        if self.ok:
            answer = dict(self.values)
            answer["citations"] = [asdict(item) for item in self.citations]
        return {
            "ok": self.ok,
            "attempts": self.attempts,
            "errors": list(self.errors),
            "answer": answer,
        }
