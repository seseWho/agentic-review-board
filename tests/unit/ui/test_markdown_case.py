import pytest

from agentic_review_board.ui.markdown_case import (
    MAX_MARKDOWN_CASE_BYTES,
    MarkdownCaseError,
    decode_markdown_case,
    parse_markdown_case,
)


def test_complete_markdown_case_preserves_semantic_values_and_order() -> None:
    case = parse_markdown_case(
        """# Modernización crítica

## Description

First paragraph.

Second paragraph with **Markdown**.

## Objective

Choose an approach.

## Constraints

- Offline operation
- ARM64 support
- Offline operation

## Context

* Existing WPF client
+ Limited team

## Stated facts

- SQLite is embedded.
"""
    )

    assert case.title == "Modernización crítica"
    assert case.description == "First paragraph.\n\nSecond paragraph with **Markdown**."
    assert case.objective == "Choose an approach."
    assert case.constraints == ("Offline operation", "ARM64 support", "Offline operation")
    assert case.context == ("Existing WPF client", "Limited team")
    assert case.stated_facts == ("SQLite is embedded.",)


def test_spanish_headings_and_utf8_bom_are_supported() -> None:
    case = decode_markdown_case(
        """\ufeff# Caso español

## Descripción

Descripción con ñ y €.

## Objetivo

Elegir con evidencia.

## Restricciones

- Sin conexión

## Contexto

- Equipo pequeño

## Hechos declarados

- Existen cinco agentes
""".encode()
    )

    assert case.title == "Caso español"
    assert case.description == "Descripción con ñ y €."
    assert case.constraints == ("Sin conexión",)
    assert case.stated_facts == ("Existen cinco agentes",)


def test_only_description_is_required() -> None:
    case = parse_markdown_case("## Description\n\nA sufficient problem statement.\n")

    assert case.title == ""
    assert case.objective == ""
    assert case.constraints == ()
    assert case.context == ()
    assert case.stated_facts == ()


def test_hash_in_title_is_preserved_but_optional_closing_markers_are_removed() -> None:
    assert parse_markdown_case("# C# migration\n## Description\nValid").title == "C# migration"
    assert parse_markdown_case("# Marked title ##\n## Description\nValid").title == (
        "Marked title"
    )


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("# Title\n", "requires a Description"),
        ("## Description\n\n  \n", "must contain non-blank"),
        (
            "## Description\nValid\n## Description\nDuplicate",
            "Duplicate Markdown section",
        ),
        (
            "## Description\nValid\n## Descripción\nDuplicate alias",
            "Duplicate Markdown section",
        ),
        ("## Description\nValid\n## Notes\nHidden", "Unknown Markdown section"),
        ("Loose content\n## Description\nValid", "inside a supported"),
        ("## Description\nValid\n### Detail\nText", "Only level-one and level-two"),
        (
            "## Description\nValid\n## Constraints\nNot a bullet",
            "one flat bullet item per line",
        ),
        (
            "## Description\nValid\n# Late title",
            "title must appear once before",
        ),
    ],
)
def test_invalid_structure_fails_without_partial_result(document: str, message: str) -> None:
    with pytest.raises(MarkdownCaseError, match=message):
        parse_markdown_case(document)


def test_invalid_utf8_and_oversized_documents_are_rejected() -> None:
    with pytest.raises(MarkdownCaseError, match="UTF-8"):
        decode_markdown_case(b"\xff\xfe")

    with pytest.raises(MarkdownCaseError, match="1 MiB"):
        decode_markdown_case(b"x" * (MAX_MARKDOWN_CASE_BYTES + 1))


def test_null_characters_are_rejected() -> None:
    with pytest.raises(MarkdownCaseError, match="null characters"):
        parse_markdown_case("## Description\nUnsafe\x00content")
