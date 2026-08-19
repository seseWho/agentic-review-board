from collections.abc import Mapping

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.participants.analyst import Analyst


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
            {"text": "The initial review should stay small."},
        ],
        "assumptions": [
            {"id": "ASM-001", "text": "The existing system can be changed."},
        ],
        "missing_information": [
            {"text": "Current architecture is unknown."},
        ],
        "uncertainties": [
            {"text": "The expected benefit is unclear."},
        ],
    }


def test_analyst_returns_trusted_problem_analysis_from_valid_generated_output() -> None:
    llm = FakeLLM(valid_response())
    review_input = ReviewInput(
        description="A technical change is proposed.",
        title="Technical change review",
        objective="Decide whether further evaluation is justified.",
        constraints=["Keep the initial review small."],
        context=["The change affects an existing system."],
        stated_facts=["A technical change is proposed."],
    )

    analysis = Analyst(llm).analyze(review_input)

    assert isinstance(analysis, ProblemAnalysis)
    assert analysis.objective == "Determine whether the proposal merits further evaluation."
    assert analysis.facts[0].source_ref.value == "description"
    assert analysis.facts[0].id == "FACT-001"
    assert analysis.assumptions[0].id == "ASM-001"
    assert analysis.missing_information[0].id is None


def test_analyst_invokes_provider_neutral_boundary_once_with_current_review_input() -> None:
    llm = FakeLLM(valid_response())
    review_input = ReviewInput(
        description="A technical change is proposed.",
        title="Technical change review",
        constraints=["Keep the initial review small."],
        context=["Existing system."],
        stated_facts=["A technical change is proposed."],
    )

    Analyst(llm).analyze(review_input)

    assert len(llm.calls) == 1
    role, payload = llm.calls[0]
    assert role == "analyst"
    assert payload["description"] == review_input.description
    assert payload["title"] == review_input.title
    assert payload["objective"] == review_input.objective
    assert payload["constraints"] == review_input.constraints
    assert payload["context"] == review_input.context
    assert payload["stated_facts"] == review_input.stated_facts


def test_analyst_happy_path_preserves_role_boundary() -> None:
    analysis = Analyst(FakeLLM(valid_response())).analyze(
        ReviewInput(description="A technical change is proposed.")
    )

    forbidden_fields = {
        "alternatives",
        "solution_alternatives",
        "ranking",
        "architecture_recommendation",
        "preferred_solution",
        "final_recommendation",
        "decision",
    }

    assert forbidden_fields.isdisjoint(analysis.model_fields)
