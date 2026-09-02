from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_review_board.domain.review import ReviewInput

EXAMPLE_REVIEW_DIRECTORY = Path(__file__).parents[2] / "examples" / "reviews"
EXAMPLE_REVIEW_PATHS = tuple(sorted(EXAMPLE_REVIEW_DIRECTORY.glob("*.json")))


def test_example_review_catalog_is_not_empty() -> None:
    assert EXAMPLE_REVIEW_PATHS


@pytest.mark.parametrize(
    "path",
    EXAMPLE_REVIEW_PATHS,
    ids=lambda path: path.name,
)
def test_example_review_input_satisfies_domain_contract(path: Path) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))

    review_input = ReviewInput.model_validate(document)

    assert review_input.description == document["description"]
    assert review_input.title
    assert review_input.objective
    for collection in (
        review_input.constraints,
        review_input.context,
        review_input.stated_facts,
    ):
        assert collection
        assert all(item.strip() for item in collection)
        assert len(collection) == len(set(collection))
