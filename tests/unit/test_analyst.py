from collections.abc import Mapping

import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
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


class ProviderFailure(RuntimeError):
    pass


class FailingLLM:
    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        raise ProviderFailure("provider unavailable")


def valid_response() -> dict[str, object]:
    return {
        "objective": "Determine whether the proposal merits further evaluation.",
        "facts": [
            {
                "id": "FACT-001",
                "text": "A technical change is proposed.",
                "source_ref": "stated_facts",
            }
        ],
        "constraints": [
            {"id": "CON-001", "text": "Keep the initial review small."},
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
        constraints=("Keep the initial review small.",),
        context=("The change affects an existing system.",),
        stated_facts=("A technical change is proposed.",),
    )

    analysis = Analyst(llm).analyze(review_input)

    assert isinstance(analysis, ProblemAnalysis)
    assert analysis.objective == "Determine whether the proposal merits further evaluation."
    assert analysis.facts[0].source_ref.value == "stated_facts"
    assert analysis.facts[0].id == "FACT-001"
    assert analysis.assumptions[0].id == "ASM-001"
    assert analysis.missing_information[0].id is None


def test_analyst_invokes_provider_neutral_boundary_once_with_current_review_input() -> None:
    llm = FakeLLM(valid_response())
    review_input = ReviewInput(
        description="A technical change is proposed.",
        title="Technical change review",
        constraints=("Keep the initial review small.",),
        context=("Existing system.",),
        stated_facts=("A technical change is proposed.",),
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
    response = valid_response()
    response["facts"] = []
    response["constraints"] = []
    Analyst(FakeLLM(response)).analyze(
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

    assert forbidden_fields.isdisjoint(ProblemAnalysis.model_fields)


def test_analyst_rejects_fact_reference_to_absent_review_input_field() -> None:
    response = valid_response()
    response["facts"] = [
        {
            "text": "A title-specific fact.",
            "source_ref": "title",
        }
    ]

    with pytest.raises(AnalystOutputError, match="not applicable"):
        Analyst(FakeLLM(response)).analyze(ReviewInput(description="Review this."))


@pytest.mark.parametrize(
    "constraints",
    [
        [],
        [
            {"id": "CON-001", "text": "Keep the initial review small."},
            {"id": "CON-002", "text": "Keep the initial review small."},
        ],
        [{"id": "CON-001", "text": "Paraphrased constraint."}],
    ],
)
def test_analyst_rejects_omitted_duplicated_or_mutated_input_constraints(
    constraints: list[dict[str, str]],
) -> None:
    response = valid_response()
    response["constraints"] = constraints
    review_input = ReviewInput(
        description="A technical change is proposed.",
        constraints=("Keep the initial review small.",),
        stated_facts=("A technical change is proposed.",),
    )

    with pytest.raises(AnalystOutputError, match="authoritative constraints"):
        Analyst(FakeLLM(response)).analyze(review_input)


def test_analyst_rejects_reclassified_or_mutated_stated_facts() -> None:
    response = valid_response()
    response["facts"] = [
        {
            "id": "FACT-001",
            "text": "A paraphrased technical change is proposed.",
            "source_ref": "stated_facts",
        }
    ]
    review_input = ReviewInput(
        description="A technical change is proposed.",
        constraints=("Keep the initial review small.",),
        stated_facts=("A technical change is proposed.",),
    )

    with pytest.raises(AnalystOutputError, match="authoritative stated facts"):
        Analyst(FakeLLM(response)).analyze(review_input)


def test_analyst_normalizes_pydantic_contract_failure() -> None:
    response = valid_response()
    del response["assumptions"]

    with pytest.raises(AnalystOutputError, match="invalid Analyst output") as captured:
        Analyst(FakeLLM(response)).analyze(ReviewInput(description="Review this."))

    assert captured.value.__cause__ is not None


def test_analyst_does_not_repair_invalid_generated_data() -> None:
    response = valid_response()
    response["objective"] = 123

    with pytest.raises(AnalystOutputError, match="invalid Analyst output"):
        Analyst(FakeLLM(response)).analyze(ReviewInput(description="Review this."))

    assert response["objective"] == 123


def test_provider_failure_is_not_misreported_as_output_validation_error() -> None:
    with pytest.raises(ProviderFailure, match="provider unavailable"):
        Analyst(FailingLLM()).analyze(ReviewInput(description="Review this."))
