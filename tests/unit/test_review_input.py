import pytest

from agentic_review_board.domain.review import ReviewInput


def test_review_input_accepts_minimal_valid_description() -> None:
    review_input = ReviewInput(description="Evaluate a proposed technical change.")
    assert review_input.description == "Evaluate a proposed technical change."


def test_review_input_rejects_blank_description() -> None:
    with pytest.raises(ValueError, match="description must not be empty"):
        ReviewInput(description="   ")
