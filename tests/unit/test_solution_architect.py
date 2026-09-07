from collections.abc import Mapping

import pytest

from agentic_review_board.domain.analysis import AnalysisFinding, ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.solutions import (
    AlternativeValidationStatus,
    SolutionAlternative,
    SolutionAlternatives,
)
from agentic_review_board.participants.solution_architect import (
    SolutionArchitect,
    SolutionArchitectOutputError,
)


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


def review_input(*, duplicate_constraint: bool = False) -> ReviewInput:
    constraints = (
        ("Must run offline", "Must run offline")
        if duplicate_constraint
        else (
            "Must run offline",
            "Keep deployment simple",
        )
    )
    return ReviewInput(
        title="Deployment review",
        description="Choose a deployment approach for a small internal capability.",
        objective="Identify viable deployment approaches.",
        constraints=constraints,
        context=("The current environment is locally managed.",),
        stated_facts=("The capability must remain available without internet access.",),
    )


def problem_analysis(
    *,
    include_offline_constraint: bool = True,
    include_blockers: bool = False,
    duplicate_constraint_text: bool = False,
    duplicate_uncertainty_text: bool = False,
) -> ProblemAnalysis:
    constraints: tuple[AnalysisFinding, ...]
    if duplicate_constraint_text:
        constraints = (
            AnalysisFinding(id="CON-001", text="Must run offline"),
            AnalysisFinding(id="CON-002", text="Must run offline"),
        )
    elif include_offline_constraint:
        constraints = (
            AnalysisFinding(id="CON-001", text="Must run offline"),
            AnalysisFinding(id="CON-002", text="Keep deployment simple"),
        )
    else:
        constraints = (AnalysisFinding(id="CON-002", text="Keep deployment simple"),)

    missing_information = (
        (
            AnalysisFinding(
                id="MISS-001",
                text="Available deployment infrastructure is unknown.",
            ),
        )
        if include_blockers
        else ()
    )

    uncertainties: tuple[AnalysisFinding, ...]
    if duplicate_uncertainty_text:
        uncertainties = (
            AnalysisFinding(id="UNC-001", text="Operational ownership is unclear."),
            AnalysisFinding(id="UNC-002", text="Operational ownership is unclear."),
        )
    elif include_blockers:
        uncertainties = (AnalysisFinding(text="Operational ownership is unclear."),)
    else:
        uncertainties = ()

    return ProblemAnalysis(
        objective="Identify viable deployment approaches.",
        facts=(),
        constraints=constraints,
        assumptions=(
            AnalysisFinding(id="ASM-001", text="Local compute can host the workload."),
        ),
        missing_information=missing_information,
        uncertainties=uncertainties,
    )


def alternative(
    *,
    alternative_id: str,
    name: str,
    relevant_constraints: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "id": alternative_id,
        "name": name,
        "description": f"Use the {name.lower()} approach.",
        "solution_design": {
            "summary": f"Implement {name.lower()} as a bounded operational capability.",
            "building_blocks": ["Runtime and its owned configuration."],
            "key_interactions": [
                "User request flows through the runtime to local state."
            ],
            "operational_model": ["Assign explicit deployment and support ownership."],
            "delivery_steps": ["Build and pilot the bounded capability."],
            "validation_checks": ["Run an end-to-end operational pilot."],
        },
        "advantages": [f"{name} has a clear operational benefit."],
        "disadvantages": [f"{name} introduces a distinct operational trade-off."],
        "assumptions": ["Required implementation capability is available."],
        "implementation_complexity": "MEDIUM",
        "relevant_constraints": relevant_constraints or [],
    }


def base_alternatives() -> list[dict[str, object]]:
    return [
        alternative(
            alternative_id="ALT-001",
            name="Local deployment",
            relevant_constraints=[
                {
                    "source": "REVIEW_INPUT",
                    "kind": "TEXT",
                    "value": "Must run offline",
                }
            ],
        ),
        alternative(
            alternative_id="ALT-002",
            name="Managed edge deployment",
            relevant_constraints=[
                {
                    "source": "PROBLEM_ANALYSIS",
                    "kind": "ID",
                    "value": "CON-002",
                }
            ],
        ),
    ]


def response_from(alternatives: list[dict[str, object]]) -> dict[str, object]:
    return {"alternatives": alternatives}


def two_alternative_response() -> dict[str, object]:
    return response_from(base_alternatives())


def no_alternative_response() -> dict[str, object]:
    return {
        "alternatives": [],
        "generation_notes": {
            "explanation": "The current evidence does not support two meaningful alternatives.",
            "blocking_missing_information": [
                {
                    "id": "MISS-001",
                    "text": "Available deployment infrastructure is unknown.",
                }
            ],
            "blocking_uncertainties": [{"text": "Operational ownership is unclear."}],
        },
    }


def test_solution_architect_returns_trusted_two_alternative_result() -> None:
    llm = FakeLLM(two_alternative_response())
    current_input = review_input()
    analysis = problem_analysis()

    result = SolutionArchitect(llm).propose(current_input, analysis)

    assert isinstance(result, SolutionAlternatives)
    assert len(result.alternatives) == 2
    assert result.alternatives[0].id == "ALT-001"
    assert result.alternatives[1].id == "ALT-002"
    assert all(
        item.validation_status is AlternativeValidationStatus.PROPOSED
        for item in result.alternatives
    )


def test_solution_architect_cannot_self_promote_alternative_to_evidenced() -> None:
    alternatives = base_alternatives()
    alternatives[0]["validation_status"] = "EVIDENCED"

    with pytest.raises(
        SolutionArchitectOutputError,
        match="cannot claim validation evidence",
    ):
        SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
            review_input(),
            problem_analysis(),
        )


def test_solution_architect_accepts_valid_three_alternative_result() -> None:
    alternatives = base_alternatives()
    alternatives.append(alternative(alternative_id="ALT-003", name="Hybrid deployment"))

    result = SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
        review_input(),
        problem_analysis(),
    )

    assert len(result.alternatives) == 3


def test_solution_architect_invokes_provider_neutral_boundary_once_with_only_upstream_artifacts() -> (
    None
):
    llm = FakeLLM(two_alternative_response())
    current_input = review_input()
    analysis = problem_analysis()

    SolutionArchitect(llm).propose(current_input, analysis)

    assert len(llm.calls) == 1
    role, payload = llm.calls[0]
    assert role == "solution_architect"
    assert set(payload) == {"review_input", "problem_analysis"}
    assert payload["review_input"] == current_input.model_dump(mode="json")
    assert payload["problem_analysis"] == analysis.model_dump(mode="json")


def test_solution_architect_does_not_mutate_trusted_upstream_artifacts() -> None:
    current_input = review_input()
    analysis = problem_analysis()
    input_before = current_input.model_dump(mode="json")
    analysis_before = analysis.model_dump(mode="json")

    SolutionArchitect(FakeLLM(two_alternative_response())).propose(
        current_input, analysis
    )

    assert current_input.model_dump(mode="json") == input_before
    assert analysis.model_dump(mode="json") == analysis_before


def test_solution_architect_happy_path_preserves_role_boundary() -> None:
    result = SolutionArchitect(FakeLLM(two_alternative_response())).propose(
        review_input(),
        problem_analysis(),
    )

    forbidden_fields = {
        "ranking",
        "preferred_alternative",
        "winner",
        "final_recommendation",
        "final_decision",
        "risk_assessment",
        "critical_review",
    }

    assert forbidden_fields.isdisjoint(SolutionAlternatives.model_fields)
    assert forbidden_fields.isdisjoint(SolutionAlternative.model_fields)
    assert len(result.alternatives) == 2


def test_review_input_constraint_resolves_even_when_analyst_omitted_it() -> None:
    result = SolutionArchitect(FakeLLM(two_alternative_response())).propose(
        review_input(),
        problem_analysis(include_offline_constraint=False),
    )

    assert result.alternatives[0].relevant_constraints[0].value == "Must run offline"


def test_identical_duplicate_review_input_constraint_text_resolves_as_one_textual_target() -> (
    None
):
    alternatives = base_alternatives()
    alternatives[1]["relevant_constraints"] = []

    result = SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
        review_input(duplicate_constraint=True),
        problem_analysis(include_offline_constraint=False),
    )

    assert result.alternatives[0].relevant_constraints[0].value == "Must run offline"


def test_problem_analysis_constraint_resolves_by_id() -> None:
    alternatives = base_alternatives()
    alternatives[0]["relevant_constraints"] = [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        }
    ]

    result = SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
        review_input(),
        problem_analysis(),
    )

    assert result.alternatives[0].relevant_constraints[0].value == "CON-001"


def test_problem_analysis_constraint_resolves_by_exact_text_when_unambiguous() -> None:
    alternatives = base_alternatives()
    alternatives[0]["relevant_constraints"] = [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "TEXT",
            "value": "Must run offline",
        }
    ]

    result = SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
        review_input(),
        problem_analysis(),
    )

    assert result.alternatives[0].relevant_constraints[0].value == "Must run offline"


def test_solution_architect_returns_structured_no_alternative_result_with_valid_blockers() -> (
    None
):
    result = SolutionArchitect(FakeLLM(no_alternative_response())).propose(
        review_input(),
        problem_analysis(include_blockers=True),
    )

    assert result.alternatives == ()
    assert result.generation_notes is not None
    assert result.generation_notes.blocking_missing_information[0].id == "MISS-001"
    assert result.generation_notes.blocking_uncertainties[0].id is None


def test_generation_notes_id_and_text_must_resolve_to_same_missing_information_finding() -> (
    None
):
    result = SolutionArchitect(FakeLLM(no_alternative_response())).propose(
        review_input(),
        problem_analysis(include_blockers=True),
    )

    assert result.generation_notes is not None
    blocker = result.generation_notes.blocking_missing_information[0]
    assert blocker.id == "MISS-001"
    assert blocker.text == "Available deployment infrastructure is unknown."


def test_generation_notes_text_only_reference_resolves_when_unique() -> None:
    result = SolutionArchitect(FakeLLM(no_alternative_response())).propose(
        review_input(),
        problem_analysis(include_blockers=True),
    )

    assert result.generation_notes is not None
    blocker = result.generation_notes.blocking_uncertainties[0]
    assert blocker.id is None
    assert blocker.text == "Operational ownership is unclear."


def test_generation_notes_blockers_are_validated_even_when_alternatives_are_present() -> (
    None
):
    response = two_alternative_response()
    response["generation_notes"] = {
        "explanation": "One uncertainty still affects implementation planning.",
        "blocking_missing_information": [],
        "blocking_uncertainties": [{"text": "Operational ownership is unclear."}],
    }

    result = SolutionArchitect(FakeLLM(response)).propose(
        review_input(),
        problem_analysis(include_blockers=True),
    )

    assert len(result.alternatives) == 2
    assert result.generation_notes is not None
    assert (
        result.generation_notes.blocking_uncertainties[0].text
        == "Operational ownership is unclear."
    )


def test_unresolved_review_input_constraint_fails_closed() -> None:
    alternatives = base_alternatives()
    alternatives[0]["relevant_constraints"] = [
        {"source": "REVIEW_INPUT", "kind": "TEXT", "value": "Unknown constraint"}
    ]

    with pytest.raises(SolutionArchitectOutputError, match="unresolved ReviewInput"):
        SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
            review_input(),
            problem_analysis(),
        )


def test_unresolved_problem_analysis_constraint_by_id_or_text_fails_closed() -> None:
    for reference in (
        {"source": "PROBLEM_ANALYSIS", "kind": "ID", "value": "CON-999"},
        {"source": "PROBLEM_ANALYSIS", "kind": "TEXT", "value": "Unknown constraint"},
    ):
        alternatives = base_alternatives()
        alternatives[0]["relevant_constraints"] = [reference]

        with pytest.raises(
            SolutionArchitectOutputError, match="unresolved ProblemAnalysis"
        ):
            SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
                review_input(),
                problem_analysis(),
            )


def test_repeated_problem_analysis_constraint_text_is_ambiguous_for_text_reference() -> (
    None
):
    alternatives = base_alternatives()
    alternatives[0]["relevant_constraints"] = [
        {"source": "PROBLEM_ANALYSIS", "kind": "TEXT", "value": "Must run offline"}
    ]
    alternatives[1]["relevant_constraints"] = []

    with pytest.raises(SolutionArchitectOutputError, match="ambiguous ProblemAnalysis"):
        SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
            review_input(),
            problem_analysis(duplicate_constraint_text=True),
        )


def test_constraint_reference_matching_is_exact_without_trim_or_case_repair() -> None:
    for value in ("Must run offline ", "must run offline"):
        alternatives = base_alternatives()
        alternatives[0]["relevant_constraints"] = [
            {"source": "REVIEW_INPUT", "kind": "TEXT", "value": value}
        ]

        with pytest.raises(
            SolutionArchitectOutputError, match="unresolved ReviewInput"
        ):
            SolutionArchitect(FakeLLM(response_from(alternatives))).propose(
                review_input(),
                problem_analysis(),
            )


def test_unresolved_blocker_fails_closed_for_zero_and_multiple_alternatives() -> None:
    zero = no_alternative_response()
    zero["generation_notes"] = {
        "explanation": "Blocked.",
        "blocking_missing_information": [{"text": "Unknown blocker"}],
        "blocking_uncertainties": [],
    }
    multiple = two_alternative_response()
    multiple["generation_notes"] = {
        "explanation": "Still blocked.",
        "blocking_missing_information": [],
        "blocking_uncertainties": [{"text": "Unknown uncertainty"}],
    }

    for response in (zero, multiple):
        with pytest.raises(SolutionArchitectOutputError, match="unresolved"):
            SolutionArchitect(FakeLLM(response)).propose(
                review_input(),
                problem_analysis(include_blockers=True),
            )


def test_text_only_blocker_reference_fails_when_ambiguous() -> None:
    response = no_alternative_response()
    response["generation_notes"] = {
        "explanation": "Ownership uncertainty blocks comparison.",
        "blocking_missing_information": [],
        "blocking_uncertainties": [{"text": "Operational ownership is unclear."}],
    }

    with pytest.raises(SolutionArchitectOutputError, match="ambiguous uncertainty"):
        SolutionArchitect(FakeLLM(response)).propose(
            review_input(),
            problem_analysis(duplicate_uncertainty_text=True),
        )


def test_blocker_id_and_text_mismatch_fails_closed() -> None:
    response = no_alternative_response()
    response["generation_notes"] = {
        "explanation": "Missing information blocks comparison.",
        "blocking_missing_information": [
            {"id": "MISS-001", "text": "Different missing information text."}
        ],
        "blocking_uncertainties": [],
    }

    with pytest.raises(
        SolutionArchitectOutputError, match="unresolved missing information"
    ):
        SolutionArchitect(FakeLLM(response)).propose(
            review_input(),
            problem_analysis(include_blockers=True),
        )


def test_blocker_reference_matching_is_exact_without_trim_or_case_repair() -> None:
    for text in (
        "Operational ownership is unclear. ",
        "operational ownership is unclear.",
    ):
        response = no_alternative_response()
        response["generation_notes"] = {
            "explanation": "An uncertainty blocks comparison.",
            "blocking_missing_information": [],
            "blocking_uncertainties": [{"text": text}],
        }

        with pytest.raises(
            SolutionArchitectOutputError, match="unresolved uncertainty"
        ):
            SolutionArchitect(FakeLLM(response)).propose(
                review_input(),
                problem_analysis(include_blockers=True),
            )


def test_pydantic_contract_failure_is_normalized_to_solution_architect_output_error() -> (
    None
):
    response = two_alternative_response()
    response["ranking"] = ["ALT-001", "ALT-002"]

    with pytest.raises(
        SolutionArchitectOutputError, match="invalid Solution Architect output"
    ) as captured:
        SolutionArchitect(FakeLLM(response)).propose(review_input(), problem_analysis())

    assert captured.value.__cause__ is not None


def test_invalid_generated_data_is_not_repaired_before_failure() -> None:
    response = two_alternative_response()
    alternatives = base_alternatives()
    alternatives[0]["implementation_complexity"] = "VERY_HIGH"
    response["alternatives"] = alternatives

    with pytest.raises(
        SolutionArchitectOutputError, match="invalid Solution Architect output"
    ):
        SolutionArchitect(FakeLLM(response)).propose(review_input(), problem_analysis())

    assert alternatives[0]["implementation_complexity"] == "VERY_HIGH"


def test_provider_failure_is_not_misreported_as_solution_output_validation_error() -> (
    None
):
    with pytest.raises(ProviderFailure, match="provider unavailable"):
        SolutionArchitect(FailingLLM()).propose(review_input(), problem_analysis())
