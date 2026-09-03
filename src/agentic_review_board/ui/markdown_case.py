"""Deterministic import of a constrained user-authored Markdown review case."""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType

MAX_MARKDOWN_CASE_BYTES = 1024 * 1024


class MarkdownCaseError(ValueError):
    """A safe, user-correctable Markdown case format error."""


@dataclass(frozen=True, slots=True)
class MarkdownReviewCase:
    """Editable review-input values projected from one Markdown document."""

    description: str
    title: str = ""
    objective: str = ""
    constraints: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    stated_facts: tuple[str, ...] = ()


_SECTION_ALIASES = MappingProxyType(
    {
        "description": "description",
        "descripción": "description",
        "objective": "objective",
        "objetivo": "objective",
        "constraints": "constraints",
        "restricciones": "constraints",
        "context": "context",
        "contexto": "context",
        "stated facts": "stated_facts",
        "hechos declarados": "stated_facts",
    }
)
_COLLECTION_SECTIONS = frozenset({"constraints", "context", "stated_facts"})
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
_BULLET = re.compile(r"^[ \t]*[-*+][ \t]+(.+)$")


def _heading_text(raw_text: str) -> str:
    return re.sub(r"[ \t]+#+$", "", raw_text.rstrip())


def _trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _scalar_value(name: str, lines: list[str]) -> str:
    value = "\n".join(_trim_blank_lines(lines))
    if name == "description" and not value.strip():
        raise MarkdownCaseError("Description must contain non-blank text.")
    return value


def _collection_value(name: str, lines: list[str]) -> tuple[str, ...]:
    values: list[str] = []
    for line in _trim_blank_lines(lines):
        if not line.strip():
            continue
        match = _BULLET.fullmatch(line)
        if match is None or not match.group(1).strip():
            label = name.replace("_", " ").capitalize()
            raise MarkdownCaseError(f"{label} must contain one flat bullet item per line.")
        values.append(match.group(1))
    return tuple(values)


def parse_markdown_case(document: str) -> MarkdownReviewCase:
    """Parse the documented Markdown subset without silently discarding content."""

    if "\x00" in document:
        raise MarkdownCaseError("The Markdown case contains unsupported null characters.")

    title = ""
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for line in document.splitlines():
        heading = _HEADING.fullmatch(line)
        if heading is not None:
            level = len(heading.group(1))
            text = _heading_text(heading.group(2))
            if not text:
                raise MarkdownCaseError("Markdown headings must not be empty.")
            if level == 1:
                if title or sections:
                    raise MarkdownCaseError(
                        "The optional level-one title must appear once before all sections."
                    )
                title = text
                current_section = None
                continue
            if level != 2:
                raise MarkdownCaseError("Only level-one and level-two headings are supported.")

            canonical_name = _SECTION_ALIASES.get(text.casefold())
            if canonical_name is None:
                raise MarkdownCaseError(f"Unknown Markdown section: {text}.")
            if canonical_name in sections:
                raise MarkdownCaseError(f"Duplicate Markdown section: {text}.")
            sections[canonical_name] = []
            current_section = canonical_name
            continue

        if current_section is None:
            if line.strip():
                raise MarkdownCaseError("Content must appear inside a supported level-two section.")
            continue
        sections[current_section].append(line)

    if "description" not in sections:
        raise MarkdownCaseError("The Markdown case requires a Description section.")

    parsed: dict[str, str | tuple[str, ...]] = {}
    for name in ("description", "objective", "constraints", "context", "stated_facts"):
        lines = sections.get(name, [])
        parsed[name] = (
            _collection_value(name, lines)
            if name in _COLLECTION_SECTIONS
            else _scalar_value(name, lines)
        )

    return MarkdownReviewCase(
        title=title,
        description=str(parsed["description"]),
        objective=str(parsed["objective"]),
        constraints=tuple(parsed["constraints"]),
        context=tuple(parsed["context"]),
        stated_facts=tuple(parsed["stated_facts"]),
    )


def decode_markdown_case(content: bytes) -> MarkdownReviewCase:
    """Decode one bounded UTF-8 file and parse it atomically."""

    if len(content) > MAX_MARKDOWN_CASE_BYTES:
        raise MarkdownCaseError("The Markdown case must not exceed 1 MiB.")
    try:
        document = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise MarkdownCaseError("The Markdown case must use UTF-8 encoding.") from error
    return parse_markdown_case(document)
