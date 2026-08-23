from collections.abc import Mapping
from copy import deepcopy

import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.final_reviews import FinalReview
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import (
    ReviewInputBasisReference,
    Risk,
    RiskAssessment,
    RiskScope,
    RiskScopeKind,
)
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import (
    SolutionAlternative,
    SolutionAlternatives,
)
from agentic_review_board.participants.coordinator import Coordinator, CoordinatorOutputError


class RecordingLLM:
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


def review_input() -> ReviewInput:
    return ReviewInput(
        title="Deployment review",
        description="Review a proposed deployment change.",
        objective="Choose the most suitable approach.",
        constraints=("Must run offline.",),
        context=("The environment is locally managed.",),
        stated_facts=("Local compute is available.",),
    )


def problem_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        objective="Choose a suitable deployment approach.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )


def solution_alternative(
    alternative_id: str,
    name: str,
    description: str,
) -> SolutionAlternative:
    return SolutionAlternative(
        id=alternative_id,
        name=name,
        description=description,
        advantages=("Works offline.",),
        disadvantages=("Requires local maintenance.",),
        assumptions=("Local compute remains available.",),
        implementation_complexity=QualitativeLevel.MEDIUM,
        relevant_constraints=(),
    )


def solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives(
        alternatives=(
            solution_alternative(
                "ALT-001",
                "Local deployment",
                "Deploy the capability locally.",
            ),
            solution_alternative(
                "ALT-002",
                "Managed appliance",
                "Use a managed on-premises appliance.",
            ),
        ),
    )


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(risks=(), overall_observations=())


def critical_review() -> CriticalReview:
    return CriticalReview()


def recommended_response() -> dict[str, object]:
    return {
        "situation_summary": "Two viable offline approaches remain.",
        "ranked_alternatives": [
            {
                "alternative_id": "ALT-002",
                "position": 2,
                "justification": "A viable fallback.",
                "considerations": ["Confirm appliance support."],
            },
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "Best aligned with current constraints.",
                "considerations": ["Confirm operational ownership."],
            },
        ],
        "recommendation_outcome": "RECOMMENDED",
        "preferred_alternative_id": "ALT-001",
        "conclusion_rationale": "Current evidence supports local deployment.",
        "principal_risks": [],
        "unresolved_questions": [],
        "criticism_dispositions": [],
        "next_validation_step": "Confirm operational ownership.",
        "confidence": "MEDIUM",
    }


def test_coordinator_calls_exact_boundary_and_returns_separate_trusted_review() -> None:
    current_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    risks = risk_assessment()
    critique = critical_review()
    upstream = (current_input, analysis, alternatives, risks, critique)
    before = tuple(artifact.model_dump(mode="json") for artifact in upstream)
    llm = RecordingLLM(recommended_response())

    result = Coordinator(llm).coordinate(
        current_input,
        analysis,
        alternatives,
        risks,
        critique,
    )

    assert isinstance(result, FinalReview)
    assert result.preferred_alternative_id == "ALT-001"
    assert id(result) not in {id(artifact) for artifact in upstream}
    assert tuple(artifact.model_dump(mode="json") for artifact in upstream) == before

    assert llm.calls == [
        (
            "coordinator",
            {
                "review_input": before[0],
                "problem_analysis": before[1],
                "solution_alternatives": before[2],
                "risk_assessment": before[3],
                "critical_review": before[4],
            },
        )
    ]



def three_solution_alternatives() -> SolutionAlternatives:
    current = solution_alternatives()
    return SolutionAlternatives(
        alternatives=(
            *current.alternatives,
            solution_alternative(
                "ALT-003",
                "Hybrid deployment",
                "Combine local and managed components.",
            ),
        )
    )


def zero_solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives(
        alternatives=(),
        generation_notes={
            "explanation": "Required capacity evidence is unavailable.",
            "blocking_missing_information": (
                {"id": "BLOCK-001", "text": "Required capacity is unknown."},
            ),
            "blocking_uncertainties": (),
        },
    )


def populated_risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        risks=(
            Risk(
                id="RISK-001",
                description="Operational ownership may remain unclear.",
                affected_scope=RiskScope(kind=RiskScopeKind.OVERALL),
                severity=QualitativeLevel.HIGH,
                basis=(
                    ReviewInputBasisReference(
                        field="description",
                        value="Review a proposed deployment change.",
                    ),
                ),
                residual_uncertainty="The final owner is unknown.",
            ),
        ),
        overall_observations=(),
    )


def run_coordinator(
    response: Mapping[str, object],
    *,
    alternatives: SolutionAlternatives | None = None,
    risks: RiskAssessment | None = None,
) -> FinalReview:
    return Coordinator(RecordingLLM(response)).coordinate(
        review_input(),
        problem_analysis(),
        alternatives or solution_alternatives(),
        risks or risk_assessment(),
        critical_review(),
    )


def test_context_accepts_complete_three_alternative_ranking_in_any_tuple_order() -> None:
    response = recommended_response()
    ranking = response["ranked_alternatives"]
    assert isinstance(ranking, list)
    ranking.insert(
        1,
        {
            "alternative_id": "ALT-003",
            "position": 3,
            "justification": "Useful only under changed operating conditions.",
            "considerations": ["Validate integration overhead."],
            "conditions_that_could_change_ranking": ["Ownership is outsourced."],
        },
    )

    result = run_coordinator(response, alternatives=three_solution_alternatives())

    assert {item.alternative_id for item in result.ranked_alternatives} == {
        "ALT-001",
        "ALT-002",
        "ALT-003",
    }
    assert [item.position for item in result.ranked_alternatives] == [2, 3, 1]


@pytest.mark.parametrize(
    "ranking",
    [
        [
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "First.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "UNKNOWN",
                "position": 2,
                "justification": "Unknown.",
                "considerations": ["Valid."],
            },
        ],
        [
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "Omitted second alternative.",
                "considerations": ["Valid."],
            }
        ],
        [
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "First.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "ALT-002",
                "position": 2,
                "justification": "Second.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "ALT-003",
                "position": 3,
                "justification": "Extra.",
                "considerations": ["Valid."],
            },
        ],
        [
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "First.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "ALT-001",
                "position": 2,
                "justification": "Duplicate.",
                "considerations": ["Valid."],
            },
        ],
        [
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "First.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "ALT-002",
                "position": 1,
                "justification": "Tie.",
                "considerations": ["Valid."],
            },
        ],
        [
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "First.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "ALT-002",
                "position": 3,
                "justification": "Gap.",
                "considerations": ["Valid."],
            },
        ],
    ],
)
def test_context_rejects_incomplete_or_invalid_ranking(
    ranking: list[dict[str, object]],
) -> None:
    response = recommended_response()
    response["ranked_alternatives"] = ranking

    with pytest.raises(CoordinatorOutputError):
        run_coordinator(response)


@pytest.mark.parametrize(
    "preferred",
    ["UNKNOWN", "ALT-002", None],
)
def test_context_rejects_invalid_recommended_preference(
    preferred: str | None,
) -> None:
    response = recommended_response()
    response["preferred_alternative_id"] = preferred

    with pytest.raises(CoordinatorOutputError):
        run_coordinator(response)


def test_zero_alternatives_require_empty_insufficient_evidence_result() -> None:
    response = recommended_response()
    response.update(
        {
            "ranked_alternatives": [],
            "recommendation_outcome": "INSUFFICIENT_EVIDENCE",
            "preferred_alternative_id": None,
        }
    )

    result = run_coordinator(response, alternatives=zero_solution_alternatives())
    assert result.ranked_alternatives == ()

    invalid_responses: list[dict[str, object]] = []
    recommended = deepcopy(response)
    recommended["recommendation_outcome"] = "RECOMMENDED"
    recommended["preferred_alternative_id"] = "ALT-001"
    invalid_responses.append(recommended)

    ranked = deepcopy(response)
    ranked["ranked_alternatives"] = recommended_response()["ranked_alternatives"]
    invalid_responses.append(ranked)

    for invalid in invalid_responses:
        with pytest.raises(CoordinatorOutputError):
            run_coordinator(invalid, alternatives=zero_solution_alternatives())


def test_principal_risks_resolve_exact_current_ids_and_allow_empty_selection() -> None:
    response = recommended_response()
    response["principal_risks"] = [
        {
            "risk_id": "RISK-001",
            "rationale": "It may change operational feasibility.",
        }
    ]

    result = run_coordinator(response, risks=populated_risk_assessment())
    assert result.principal_risks[0].risk_id == "RISK-001"

    response["principal_risks"] = []
    assert run_coordinator(response, risks=populated_risk_assessment()).principal_risks == ()


@pytest.mark.parametrize("risk_id", ["UNKNOWN", "risk-001"])
def test_context_rejects_unknown_principal_risk_id(risk_id: str) -> None:
    response = recommended_response()
    response["principal_risks"] = [
        {"risk_id": risk_id, "rationale": "Generated selection."}
    ]

    with pytest.raises(CoordinatorOutputError):
        run_coordinator(response, risks=populated_risk_assessment())
