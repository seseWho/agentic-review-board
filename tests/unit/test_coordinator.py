from collections.abc import Mapping
from copy import deepcopy

import pytest

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    ProblemAnalysis,
    ReviewInputSource,
)
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
    FindingReference,
    GenerationNotes,
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
        generation_notes=GenerationNotes(
            explanation="Required capacity evidence is unavailable.",
            blocking_missing_information=(
                FindingReference(
                    id="BLOCK-001",
                    text="Required capacity is unknown.",
                ),
            ),
            blocking_uncertainties=(),
        ),
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
                        field=ReviewInputSource.DESCRIPTION,
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
                "alternative_id": " ",
                "position": 1,
                "justification": "Blank ID.",
                "considerations": ["Valid."],
            },
            {
                "alternative_id": "ALT-002",
                "position": 2,
                "justification": "Second.",
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


def test_insufficient_evidence_forbids_preferred_id_with_existing_ranking() -> None:
    response = recommended_response()
    response["recommendation_outcome"] = "INSUFFICIENT_EVIDENCE"

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


def test_context_rejects_duplicate_principal_risk_selection() -> None:
    response = recommended_response()
    response["principal_risks"] = [
        {"risk_id": "RISK-001", "rationale": "First selection."},
        {"risk_id": "RISK-001", "rationale": "Duplicate selection."},
    ]

    with pytest.raises(CoordinatorOutputError):
        run_coordinator(response, risks=populated_risk_assessment())


@pytest.mark.parametrize("risk_id", ["UNKNOWN", "risk-001"])
def test_context_rejects_unknown_principal_risk_id(risk_id: str) -> None:
    response = recommended_response()
    response["principal_risks"] = [
        {"risk_id": risk_id, "rationale": "Generated selection."}
    ]

    with pytest.raises(CoordinatorOutputError):
        run_coordinator(response, risks=populated_risk_assessment())



def unresolved_response(*references: Mapping[str, object]) -> dict[str, object]:
    response = recommended_response()
    response["unresolved_questions"] = [
        {
            "id": f"QUESTION-{index:03d}",
            "reference": dict(reference),
            "question": "What must be validated?",
            "rationale": "This remains material to the decision.",
        }
        for index, reference in enumerate(references, start=1)
    ]
    return response


def populated_problem_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        objective="Choose a suitable deployment approach.",
        facts=(),
        constraints=(),
        assumptions=(AnalysisFinding(id="ASM-001", text="Local capacity is sufficient."),),
        missing_information=(
            AnalysisFinding(id="MISS-001", text="Peak load is unknown."),
        ),
        uncertainties=(
            AnalysisFinding(id=None, text="Operational ownership is unclear."),
        ),
    )


def solution_alternatives_with_blockers() -> SolutionAlternatives:
    current = solution_alternatives()
    return SolutionAlternatives(
        alternatives=current.alternatives,
        generation_notes=GenerationNotes(
            explanation="Alternatives exist but blockers remain visible.",
            blocking_missing_information=(
                FindingReference(id="BLOCK-001", text="Benchmark data is missing."),
            ),
            blocking_uncertainties=(
                FindingReference(id=None, text="Support effort is uncertain."),
            ),
        ),
    )


def unresolved_critical_review() -> CriticalReview:
    basis = {
        "source": "REVIEW_INPUT",
        "kind": "DESCRIPTION",
        "value": "Review a proposed deployment change.",
    }
    return CriticalReview.model_validate(
        {
            "missing_alternatives": [
                {
                    "id": "MISSING-001",
                    "category": "Incremental rollout",
                    "rationale": "The portfolio omits a staged approach.",
                    "weakens_later_recommendation": True,
                    "basis_references": [basis],
                }
            ],
            "contradictions": [
                {
                    "id": "CONTRA-001",
                    "side_a": {
                        "reference": basis,
                        "statement": "Review a proposed deployment change.",
                    },
                    "side_b": {
                        "reference": {
                            "source": "PROBLEM_ANALYSIS",
                            "kind": "PROBLEM_OBJECTIVE",
                            "value": "Choose a suitable deployment approach.",
                        },
                        "statement": "Choose a suitable deployment approach.",
                    },
                    "rationale": "The scopes are not aligned.",
                }
            ],
            "unresolved_issues": [
                {
                    "id": "ISSUE-001",
                    "issue": "Operational ownership remains undefined.",
                    "rationale": "Ownership affects feasibility.",
                    "basis_references": [basis],
                }
            ],
        }
    )


def run_coordinator_with_context(
    response: Mapping[str, object],
    *,
    analysis: ProblemAnalysis | None = None,
    alternatives: SolutionAlternatives | None = None,
    risks: RiskAssessment | None = None,
    critique: CriticalReview | None = None,
) -> FinalReview:
    return Coordinator(RecordingLLM(response)).coordinate(
        review_input(),
        analysis or problem_analysis(),
        alternatives or solution_alternatives(),
        risks or risk_assessment(),
        critique or critical_review(),
    )


@pytest.mark.parametrize(
    "reference",
    [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "PROBLEM_ASSUMPTION",
            "item_id": "ASM-001",
            "value": "Local capacity is sufficient.",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "MISSING_INFORMATION",
            "item_id": "MISS-001",
            "value": "Peak load is unknown.",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "UNCERTAINTY",
            "value": "Operational ownership is unclear.",
        },
    ],
)
def test_problem_unresolved_references_resolve_exact_current_findings(
    reference: dict[str, object],
) -> None:
    result = run_coordinator_with_context(
        unresolved_response(reference),
        analysis=populated_problem_analysis(),
    )
    assert result.unresolved_questions[0].reference.source.value == "PROBLEM_ANALYSIS"


@pytest.mark.parametrize(
    "reference",
    [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "PROBLEM_ASSUMPTION",
            "item_id": "UNKNOWN",
            "value": "Local capacity is sufficient.",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "MISSING_INFORMATION",
            "item_id": "MISS-001",
            "value": "peak load is unknown.",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "UNCERTAINTY",
            "value": "Unknown uncertainty.",
        },
    ],
)
def test_problem_unresolved_references_fail_closed(
    reference: dict[str, object],
) -> None:
    with pytest.raises(CoordinatorOutputError):
        run_coordinator_with_context(
            unresolved_response(reference),
            analysis=populated_problem_analysis(),
        )


@pytest.mark.parametrize(
    "reference",
    [
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE_ASSUMPTION",
            "alternative_id": "ALT-001",
            "value": "Local compute remains available.",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "BLOCKING_MISSING_INFORMATION",
            "item_id": "BLOCK-001",
            "value": "Benchmark data is missing.",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "BLOCKING_UNCERTAINTY",
            "value": "Support effort is uncertain.",
        },
    ],
)
def test_solution_unresolved_references_resolve_only_local_exact_targets(
    reference: dict[str, object],
) -> None:
    result = run_coordinator_with_context(
        unresolved_response(reference),
        alternatives=solution_alternatives_with_blockers(),
    )
    assert result.unresolved_questions[0].reference.source.value == (
        "SOLUTION_ALTERNATIVES"
    )


@pytest.mark.parametrize(
    "reference",
    [
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE_ASSUMPTION",
            "alternative_id": "UNKNOWN",
            "value": "Local compute remains available.",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE_ASSUMPTION",
            "alternative_id": "ALT-001",
            "value": "local compute remains available.",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "BLOCKING_MISSING_INFORMATION",
            "item_id": "BLOCK-001",
            "value": "Wrong blocker.",
        },
    ],
)
def test_solution_unresolved_references_reject_fallback_or_repair(
    reference: dict[str, object],
) -> None:
    with pytest.raises(CoordinatorOutputError):
        run_coordinator_with_context(
            unresolved_response(reference),
            alternatives=solution_alternatives_with_blockers(),
        )


def test_risk_unresolved_reference_targets_only_exact_residual_uncertainty() -> None:
    valid = {
        "source": "RISK_ASSESSMENT",
        "risk_id": "RISK-001",
        "value": "The final owner is unknown.",
    }
    result = run_coordinator_with_context(
        unresolved_response(valid),
        risks=populated_risk_assessment(),
    )
    assert result.unresolved_questions[0].reference.source.value == "RISK_ASSESSMENT"

    for invalid in (
        {**valid, "risk_id": "UNKNOWN"},
        {**valid, "value": "Operational ownership may remain unclear."},
        {**valid, "value": "the final owner is unknown."},
    ):
        with pytest.raises(CoordinatorOutputError):
            run_coordinator_with_context(
                unresolved_response(invalid),
                risks=populated_risk_assessment(),
            )


@pytest.mark.parametrize(
    "reference",
    [
        {
            "source": "CRITICAL_REVIEW",
            "kind": "MISSING_ALTERNATIVE",
            "item_id": "MISSING-001",
            "value": "Incremental rollout",
        },
        {
            "source": "CRITICAL_REVIEW",
            "kind": "CONTRADICTION",
            "item_id": "CONTRA-001",
            "value": "The scopes are not aligned.",
        },
        {
            "source": "CRITICAL_REVIEW",
            "kind": "UNRESOLVED_ISSUE",
            "item_id": "ISSUE-001",
            "value": "Operational ownership remains undefined.",
        },
    ],
)
def test_critic_unresolved_references_use_exact_kind_id_and_visible_value(
    reference: dict[str, object],
) -> None:
    result = run_coordinator_with_context(
        unresolved_response(reference),
        critique=unresolved_critical_review(),
    )
    assert result.unresolved_questions[0].reference.source.value == "CRITICAL_REVIEW"


def test_context_rejects_distinct_references_to_same_resolved_target() -> None:
    with pytest.raises(CoordinatorOutputError):
        run_coordinator_with_context(
            unresolved_response(
                {
                    "source": "PROBLEM_ANALYSIS",
                    "kind": "MISSING_INFORMATION",
                    "item_id": "MISS-001",
                    "value": "Peak load is unknown.",
                },
                {
                    "source": "PROBLEM_ANALYSIS",
                    "kind": "MISSING_INFORMATION",
                    "value": "Peak load is unknown.",
                },
            ),
            analysis=populated_problem_analysis(),
        )
