import pytest
from pydantic import ValidationError

from agentic_review_board.domain.review import ReviewInput


def test_review_input_accepts_minimal_valid_description() -> None:
    review_input = ReviewInput(description="Evaluate a proposed technical change.")

    assert review_input.description == "Evaluate a proposed technical change."
    assert review_input.title is None
    assert review_input.objective is None
    assert review_input.constraints == []
    assert review_input.context == []
    assert review_input.stated_facts == []


def test_review_input_accepts_and_preserves_optional_context() -> None:
    review_input = ReviewInput(
        description="  Keep this exact description.  ",
        title="  Exact title  ",
        objective="  Exact objective  ",
        constraints=["  Constraint A  "],
        context=["  Background A  "],
        stated_facts=["  Fact A  "],
    )

    assert review_input.description == "  Keep this exact description.  "
    assert review_input.title == "  Exact title  "
    assert review_input.objective == "  Exact objective  "
    assert review_input.constraints == ["  Constraint A  "]
    assert review_input.context == ["  Background A  "]
    assert review_input.stated_facts == ["  Fact A  "]


@pytest.mark.parametrize("description", ["", "   ", "\t\n"])
def test_review_input_rejects_blank_description(description: str) -> None:
    with pytest.raises(ValidationError):
        ReviewInput(description=description)


def test_review_input_is_frozen_after_validation() -> None:
    review_input = ReviewInput(description="Review this.")

    with pytest.raises(ValidationError):
        review_input.description = "Changed"  # type: ignore[misc]


def test_review_input_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        ReviewInput(description="Review this.", unexpected="value")  # type: ignore[call-arg]
