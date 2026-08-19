from collections.abc import Mapping

import pytest

from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.participants.analyst import Analyst, AnalystOutputError


class FakeLLM:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        self.calls.append((role, payload))
        return self.response


def valid_response() -> dict[str, object]:
    return {
        "objective": "Determine whether the proposal merits further evaluation.",
        "facts": [
            {
                "id": "FACT-001",
                "text": "A technical change is proposed.",
                "source_ref": "description",
            }
        ],
        "constraints": [
            {"id": "CON-001", "text": "The initial review should stay small."}
        ],
        "assumptions": [
            {"id": "ASM-001", "text": "The existing system can be changed."}
        ],
        "missing_information": [
            {"id": "MISS-001", "text": "Current architecture is unknown."}
        ],
        "uncertainties": [
            {"id": "UNC-001", "text": "The expected benefit is unclear."}
        ],
    }


def test_analyst_returns_structured_problem_analysis() -> None:
    llm = FakeLLM(valid_response())
    review_input = ReviewInput(description="A technical change is proposed.")

    analysis = Analyst(llm).analyze(review_input)

    assert analysis.objective == "Determine whether the proposal merits further evaluation."
    assert analysis.facts[0].source_ref == "description"
    assert analysis.assumptions[0].id == "ASM-001"
    assert analysis.missing_information[0].id == "MISS-001"
    assert llm.calls[0][0] == "analyst"
    assert llm.calls[0][1]["description"] == review_input.description


def test_analyst_rejects_missing_required_collection() -> None:
    response = valid_response()
    del response["assumptions"]

    with pytest.raises(AnalystOutputError, match="assumptions must be a list"):
        Analyst(FakeLLM(response)).analyze(ReviewInput(description="Review this."))


def test_analyst_rejects_fact_without_valid_input_source() -> None:
    response = valid_response()
    response["facts"] = [
        {
            "id": "FACT-001",
            "text": "An invented fact.",
            "source_ref": "external_knowledge",
        }
    ]

    with pytest.raises(AnalystOutputError, match="invalid fact source_ref"):
        Analyst(FakeLLM(response)).analyze(ReviewInput(description="Review this."))


def test_analyst_rejects_duplicate_finding_ids() -> None:
    response = valid_response()
    response["assumptions"] = [{"id": "FACT-001", "text": "Duplicate identifier."}]

    with pytest.raises(AnalystOutputError, match="finding ids must be unique"):
        Analyst(FakeLLM(response)).analyze(ReviewInput(description="Review this."))
