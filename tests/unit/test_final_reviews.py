import pytest
from pydantic import ValidationError

from agentic_review_board.domain.final_reviews import (
    CriticismDisposition,
    CriticismDispositionOutcome,
    CriticUnresolvedKind,
    CriticUnresolvedReference,
    FinalReview,
    FinalReviewSection,
    PrincipalRisk,
    ProblemUnresolvedKind,
    ProblemUnresolvedReference,
    RankedAlternative,
    RecommendationOutcome,
    RiskUnresolvedReference,
    SolutionUnresolvedKind,
    SolutionUnresolvedReference,
    UnresolvedQuestion,
    UnresolvedQuestionSource,
)
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import AlternativeValidationStatus


def ranked_alternative(**overrides: object) -> RankedAlternative:
    data: dict[str, object] = {
        "alternative_id": "ALT-001",
        "position": 1,
        "justification": "Best current alignment with the stated objective.",
        "considerations": ["Confirm operational ownership."],
        "conditions_that_could_change_ranking": ["New cost evidence."],
    }
    data.update(overrides)
    return RankedAlternative.model_validate(data)


def test_coordinator_enums_are_exact_and_closed() -> None:
    assert list(RecommendationOutcome) == [
        RecommendationOutcome.RECOMMENDED,
        RecommendationOutcome.INSUFFICIENT_EVIDENCE,
    ]
    assert [value.value for value in RecommendationOutcome] == [
        "RECOMMENDED",
        "INSUFFICIENT_EVIDENCE",
    ]
    assert list(CriticismDispositionOutcome) == [
        CriticismDispositionOutcome.REFLECTED,
        CriticismDispositionOutcome.DISMISSED,
    ]
    assert [value.value for value in FinalReviewSection] == [
        "SITUATION_SUMMARY",
        "RANKING",
        "CONCLUSION",
        "PRINCIPAL_RISKS",
        "UNRESOLVED_QUESTIONS",
        "NEXT_VALIDATION_STEP",
        "CONFIDENCE",
    ]

    with pytest.raises(ValueError):
        RecommendationOutcome("CONDITIONAL")
    with pytest.raises(ValueError):
        CriticismDispositionOutcome("IGNORED")
    with pytest.raises(ValueError):
        FinalReviewSection("PREFERRED_ALTERNATIVE")


def test_ranked_alternative_accepts_valid_immutable_closed_contract() -> None:
    ranked = ranked_alternative(
        considerations=["Confirm ownership.", "Validate support effort."],
        conditions_that_could_change_ranking=["Measured cost exceeds the budget."],
    )

    assert ranked.alternative_id == "ALT-001"
    assert ranked.position == 1
    assert ranked.validation_status is AlternativeValidationStatus.PROPOSED
    assert ranked.considerations == (
        "Confirm ownership.",
        "Validate support effort.",
    )
    assert ranked.conditions_that_could_change_ranking == (
        "Measured cost exceeds the budget.",
    )

    with pytest.raises(ValidationError):
        ranked.position = 2

    with pytest.raises(ValidationError):
        RankedAlternative.model_validate(
            {
                **ranked.model_dump(),
                "unexpected": "forbidden",
            }
        )


def test_ranked_alternative_validation_status_uses_closed_solution_vocabulary() -> None:
    evidenced = ranked_alternative(validation_status="EVIDENCED")

    assert evidenced.validation_status is AlternativeValidationStatus.EVIDENCED

    with pytest.raises(ValidationError):
        ranked_alternative(validation_status="VALIDATED")


@pytest.mark.parametrize("position", [True, False, 0, -1, 1.0, "1"])
def test_ranked_alternative_requires_strict_positive_integer_position(
    position: object,
) -> None:
    with pytest.raises(ValidationError):
        ranked_alternative(position=position)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("alternative_id", " "),
        ("justification", ""),
        ("considerations", []),
        ("considerations", ["valid", " "]),
        ("considerations", ["duplicate", "duplicate"]),
        ("conditions_that_could_change_ranking", [" "]),
        ("conditions_that_could_change_ranking", ["duplicate", "duplicate"]),
    ],
)
def test_ranked_alternative_rejects_invalid_required_content(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        ranked_alternative(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "description",
        "advantages",
        "disadvantages",
        "assumptions",
        "implementation_complexity",
        "score",
        "weight",
        "probability",
    ],
)
def test_ranked_alternative_rejects_replacement_or_numeric_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        ranked_alternative(**{field: "forbidden"})


def test_principal_risk_is_a_minimal_immutable_reference() -> None:
    principal = PrincipalRisk(
        risk_id="RISK-001",
        rationale="This risk could materially affect the preferred approach.",
    )

    assert principal.risk_id == "RISK-001"
    assert principal.rationale == (
        "This risk could materially affect the preferred approach."
    )

    with pytest.raises(ValidationError):
        principal.risk_id = "RISK-002"


@pytest.mark.parametrize("field", ["risk_id", "rationale"])
def test_principal_risk_rejects_blank_required_text(field: str) -> None:
    with pytest.raises(ValidationError):
        PrincipalRisk.model_validate(
            {
                "risk_id": "RISK-001",
                "rationale": "Material to the decision.",
                field: " ",
            }
        )


@pytest.mark.parametrize(
    "field",
    ["description", "severity", "mitigation", "affected_scope", "basis"],
)
def test_principal_risk_rejects_copied_risk_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        PrincipalRisk.model_validate(
            {
                "risk_id": "RISK-001",
                "rationale": "Material to the decision.",
                field: "forbidden",
            }
        )


def test_problem_unresolved_reference_accepts_all_exact_kinds() -> None:
    for kind in ProblemUnresolvedKind:
        reference = ProblemUnresolvedReference(
            source=UnresolvedQuestionSource.PROBLEM_ANALYSIS,
            kind=kind,
            value="Visible unresolved analysis item.",
            item_id="AN-001",
        )
        assert reference.kind is kind
        assert reference.value == "Visible unresolved analysis item."
        assert reference.item_id == "AN-001"

    without_id = ProblemUnresolvedReference(
        source=UnresolvedQuestionSource.PROBLEM_ANALYSIS,
        kind=ProblemUnresolvedKind.UNCERTAINTY,
        value="Exact unique uncertainty.",
    )
    assert without_id.item_id is None
    assert [kind.value for kind in ProblemUnresolvedKind] == [
        "PROBLEM_ASSUMPTION",
        "MISSING_INFORMATION",
        "UNCERTAINTY",
    ]


@pytest.mark.parametrize(
    "data",
    [
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "MISSING_INFORMATION",
            "value": "wrong source",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "PROBLEM_ASSUMPTION",
            "value": " ",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "UNCERTAINTY",
            "value": "valid",
            "item_id": "",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "UNCERTAINTY",
            "value": "valid",
            "unexpected": "forbidden",
        },
    ],
)
def test_problem_unresolved_reference_rejects_invalid_shapes(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ProblemUnresolvedReference.model_validate(data)


@pytest.mark.parametrize("kind", list(SolutionUnresolvedKind))
def test_solution_unresolved_reference_accepts_kind_specific_shapes(
    kind: SolutionUnresolvedKind,
) -> None:
    if kind is SolutionUnresolvedKind.ALTERNATIVE_ASSUMPTION:
        reference = SolutionUnresolvedReference(
            source=UnresolvedQuestionSource.SOLUTION_ALTERNATIVES,
            kind=kind,
            value="Suitable local compute is available.",
            alternative_id="ALT-001",
        )
        assert reference.alternative_id == "ALT-001"
        assert reference.item_id is None
    else:
        reference = SolutionUnresolvedReference(
            source=UnresolvedQuestionSource.SOLUTION_ALTERNATIVES,
            kind=kind,
            value="Required benchmark is missing.",
            item_id="BLOCK-001",
        )
        assert reference.alternative_id is None
        assert reference.item_id == "BLOCK-001"

    assert [value.value for value in SolutionUnresolvedKind] == [
        "ALTERNATIVE_ASSUMPTION",
        "BLOCKING_MISSING_INFORMATION",
        "BLOCKING_UNCERTAINTY",
    ]


@pytest.mark.parametrize(
    "data",
    [
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE_ASSUMPTION",
            "value": "assumption",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE_ASSUMPTION",
            "value": "assumption",
            "alternative_id": "ALT-001",
            "item_id": "forbidden",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "BLOCKING_MISSING_INFORMATION",
            "value": "blocker",
            "alternative_id": "forbidden",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "BLOCKING_UNCERTAINTY",
            "value": "blocker",
            "alternative_id": "ALT-001",
            "item_id": "BLOCK-001",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "BLOCKING_UNCERTAINTY",
            "value": " ",
        },
    ],
)
def test_solution_unresolved_reference_rejects_invalid_field_combinations(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SolutionUnresolvedReference.model_validate(data)


def test_risk_and_critic_unresolved_references_are_closed_and_exact() -> None:
    risk = RiskUnresolvedReference(
        source=UnresolvedQuestionSource.RISK_ASSESSMENT,
        risk_id="RISK-001",
        value="Actual support effort is unknown.",
    )
    assert risk.risk_id == "RISK-001"

    expected_values = [
        "MISSING_ALTERNATIVE",
        "CONTRADICTION",
        "UNRESOLVED_ISSUE",
    ]
    assert [kind.value for kind in CriticUnresolvedKind] == expected_values
    for kind in CriticUnresolvedKind:
        reference = CriticUnresolvedReference(
            source=UnresolvedQuestionSource.CRITICAL_REVIEW,
            kind=kind,
            item_id="CRIT-FINDING-001",
            value="Exact visible compatibility value.",
        )
        assert reference.kind is kind


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (
            RiskUnresolvedReference,
            {
                "source": "RISK_ASSESSMENT",
                "risk_id": " ",
                "value": "valid",
            },
        ),
        (
            RiskUnresolvedReference,
            {
                "source": "RISK_ASSESSMENT",
                "risk_id": "RISK-001",
                "value": "",
            },
        ),
        (
            CriticUnresolvedReference,
            {
                "source": "CRITICAL_REVIEW",
                "kind": "CRITICISM",
                "item_id": "CRIT-001",
                "value": "invalid kind",
            },
        ),
        (
            CriticUnresolvedReference,
            {
                "source": "CRITICAL_REVIEW",
                "kind": "CONTRADICTION",
                "item_id": "",
                "value": "valid",
            },
        ),
    ],
)
def test_risk_and_critic_unresolved_references_reject_invalid_shapes(
    model: type[RiskUnresolvedReference] | type[CriticUnresolvedReference],
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize(
    "reference",
    [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "MISSING_INFORMATION",
            "value": "Which capacity is required?",
            "item_id": "MISS-001",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE_ASSUMPTION",
            "value": "Suitable local compute is available.",
            "alternative_id": "ALT-001",
        },
        {
            "source": "RISK_ASSESSMENT",
            "risk_id": "RISK-001",
            "value": "Actual support effort is unknown.",
        },
        {
            "source": "CRITICAL_REVIEW",
            "kind": "UNRESOLVED_ISSUE",
            "item_id": "ISSUE-001",
            "value": "Operational ownership remains undefined.",
        },
    ],
)
def test_unresolved_question_parses_each_discriminated_reference(
    reference: dict[str, object],
) -> None:
    question = UnresolvedQuestion.model_validate(
        {
            "id": "QUESTION-001",
            "reference": reference,
            "question": "What must be validated before a decision?",
            "rationale": "The referenced issue remains decision-relevant.",
        }
    )

    assert question.reference.source in UnresolvedQuestionSource

    with pytest.raises(ValidationError):
        question.question = "changed"


@pytest.mark.parametrize(
    "field",
    ["id", "question", "rationale"],
)
def test_unresolved_question_rejects_blank_or_extra_fields(field: str) -> None:
    data: dict[str, object] = {
        "id": "QUESTION-001",
        "reference": {
            "source": "RISK_ASSESSMENT",
            "risk_id": "RISK-001",
            "value": "Unknown effort.",
        },
        "question": "What remains unknown?",
        "rationale": "This affects the decision.",
    }
    data[field] = " "

    with pytest.raises(ValidationError):
        UnresolvedQuestion.model_validate(data)

    with pytest.raises(ValidationError):
        UnresolvedQuestion.model_validate({**data, field: "valid", "extra": "forbidden"})


def test_criticism_disposition_enforces_outcome_specific_sections() -> None:
    reflected = CriticismDisposition(
        criticism_id="CRIT-001",
        outcome=CriticismDispositionOutcome.REFLECTED,
        rationale="The criticism changes the ranking rationale.",
        reflected_in=(
            FinalReviewSection.RANKING,
            FinalReviewSection.CONCLUSION,
        ),
    )
    dismissed = CriticismDisposition(
        criticism_id="CRIT-002",
        outcome=CriticismDispositionOutcome.DISMISSED,
        rationale="The criticism does not affect the current decision.",
    )

    assert reflected.reflected_in == (
        FinalReviewSection.RANKING,
        FinalReviewSection.CONCLUSION,
    )
    assert dismissed.reflected_in == ()

    with pytest.raises(ValidationError):
        reflected.rationale = "changed"


@pytest.mark.parametrize(
    "data",
    [
        {
            "criticism_id": "CRIT-001",
            "outcome": "REFLECTED",
            "rationale": "Must identify a section.",
            "reflected_in": [],
        },
        {
            "criticism_id": "CRIT-001",
            "outcome": "DISMISSED",
            "rationale": "Cannot identify reflected sections.",
            "reflected_in": ["CONCLUSION"],
        },
        {
            "criticism_id": "CRIT-001",
            "outcome": "REFLECTED",
            "rationale": "Duplicate sections.",
            "reflected_in": ["RANKING", "RANKING"],
        },
        {
            "criticism_id": " ",
            "outcome": "DISMISSED",
            "rationale": "valid",
        },
        {
            "criticism_id": "CRIT-001",
            "outcome": "DISMISSED",
            "rationale": " ",
        },
        {
            "criticism_id": "CRIT-001",
            "outcome": "DISMISSED",
            "rationale": "valid",
            "extra": "forbidden",
        },
    ],
)
def test_criticism_disposition_rejects_invalid_shapes(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CriticismDisposition.model_validate(data)


DECISION_SUPPORT_NOTICE = (
    "This review supports, but does not replace, human decision-making."
)


def final_review(**overrides: object) -> FinalReview:
    data: dict[str, object] = {
        "situation_summary": "Two viable approaches remain.",
        "ranked_alternatives": [
            {
                "alternative_id": "ALT-002",
                "position": 2,
                "justification": "Viable fallback.",
                "considerations": ["Validate support effort."],
            },
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "Best current fit.",
                "considerations": ["Confirm ownership."],
                "conditions_that_could_change_ranking": ["Cost exceeds budget."],
            },
        ],
        "recommendation_outcome": "RECOMMENDED",
        "preferred_alternative_id": "ALT-001",
        "conclusion_rationale": "Current evidence supports ALT-001.",
        "principal_risks": [
            {"risk_id": "RISK-001", "rationale": "Material delivery risk."}
        ],
        "unresolved_questions": [
            {
                "id": "QUESTION-001",
                "reference": {
                    "source": "RISK_ASSESSMENT",
                    "risk_id": "RISK-001",
                    "value": "Support effort is unknown.",
                },
                "question": "What support effort is required?",
                "rationale": "It may change the decision.",
            }
        ],
        "criticism_dispositions": [
            {
                "criticism_id": "CRIT-001",
                "outcome": "REFLECTED",
                "rationale": "The concern is visible in the conclusion.",
                "reflected_in": ["CONCLUSION"],
            }
        ],
        "next_validation_step": "Measure support effort.",
        "confidence": "MEDIUM",
        "decision_support_notice": DECISION_SUPPORT_NOTICE,
    }
    data.update(overrides)
    return FinalReview.model_validate(data)


def test_final_review_accepts_tuple_order_independent_contiguous_ranking() -> None:
    review = final_review()

    assert [item.position for item in review.ranked_alternatives] == [2, 1]
    assert review.preferred_alternative_id == "ALT-001"
    assert review.confidence is QualitativeLevel.MEDIUM
    assert isinstance(review.ranked_alternatives, tuple)
    assert isinstance(review.principal_risks, tuple)
    assert isinstance(review.unresolved_questions, tuple)
    assert isinstance(review.criticism_dispositions, tuple)


@pytest.mark.parametrize(
    "outcome, preferred, ranking",
    [
        ("RECOMMENDED", "ALT-001", None),
        ("INSUFFICIENT_EVIDENCE", None, None),
        ("INSUFFICIENT_EVIDENCE", None, []),
    ],
)
def test_final_review_accepts_consistent_recommendation_shapes(
    outcome: str,
    preferred: str | None,
    ranking: list[object] | None,
) -> None:
    overrides: dict[str, object] = {
        "recommendation_outcome": outcome,
        "preferred_alternative_id": preferred,
    }
    if ranking is not None:
        overrides["ranked_alternatives"] = ranking

    review = final_review(**overrides)
    assert review.recommendation_outcome.value == outcome


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "recommendation_outcome": "RECOMMENDED",
            "preferred_alternative_id": None,
        },
        {
            "recommendation_outcome": "RECOMMENDED",
            "preferred_alternative_id": "ALT-002",
        },
        {
            "recommendation_outcome": "RECOMMENDED",
            "preferred_alternative_id": "ALT-001",
            "ranked_alternatives": [],
        },
        {
            "recommendation_outcome": "INSUFFICIENT_EVIDENCE",
            "preferred_alternative_id": "ALT-001",
        },
        {"conclusion_rationale": " "},
    ],
)
def test_final_review_rejects_inconsistent_recommendation_shapes(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        final_review(**overrides)


def test_zero_ranking_requires_insufficient_evidence() -> None:
    review = final_review(
        ranked_alternatives=[],
        recommendation_outcome="INSUFFICIENT_EVIDENCE",
        preferred_alternative_id=None,
    )
    assert review.ranked_alternatives == ()

    with pytest.raises(ValidationError):
        final_review(
            ranked_alternatives=[],
            recommendation_outcome="RECOMMENDED",
            preferred_alternative_id="ALT-001",
        )


def test_final_review_is_closed_frozen_and_uses_fixed_human_notice() -> None:
    review = final_review()

    assert review.decision_support_notice == DECISION_SUPPORT_NOTICE
    with pytest.raises(ValidationError):
        review.confidence = QualitativeLevel.HIGH
    with pytest.raises(ValidationError):
        final_review(extra="forbidden")
    with pytest.raises(ValidationError):
        final_review(decision_support_notice="A model makes the final decision.")
    with pytest.raises(ValidationError):
        final_review(confidence=0.8)


@pytest.mark.parametrize(
    "field",
    ["score", "weight", "probability", "confidence_score"],
)
def test_final_review_rejects_numeric_decision_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        final_review(**{field: 1})


@pytest.mark.parametrize(
    "field",
    ["situation_summary", "conclusion_rationale", "next_validation_step"],
)
def test_final_review_rejects_blank_required_text(field: str) -> None:
    with pytest.raises(ValidationError):
        final_review(**{field: " "})


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "ranked_alternatives": [
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
            ]
        },
        {
            "ranked_alternatives": [
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
            ]
        },
        {
            "ranked_alternatives": [
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
            ]
        },
        {
            "principal_risks": [
                {"risk_id": "RISK-001", "rationale": "First."},
                {"risk_id": "RISK-001", "rationale": "Duplicate."},
            ]
        },
        {
            "unresolved_questions": [
                {
                    "id": "QUESTION-001",
                    "reference": {
                        "source": "RISK_ASSESSMENT",
                        "risk_id": "RISK-001",
                        "value": "First.",
                    },
                    "question": "First?",
                    "rationale": "First.",
                },
                {
                    "id": "QUESTION-001",
                    "reference": {
                        "source": "RISK_ASSESSMENT",
                        "risk_id": "RISK-002",
                        "value": "Second.",
                    },
                    "question": "Second?",
                    "rationale": "Second.",
                },
            ]
        },
        {
            "unresolved_questions": [
                {
                    "id": "QUESTION-001",
                    "reference": {
                        "source": "RISK_ASSESSMENT",
                        "risk_id": "RISK-001",
                        "value": "Same.",
                    },
                    "question": "First?",
                    "rationale": "First.",
                },
                {
                    "id": "QUESTION-002",
                    "reference": {
                        "source": "RISK_ASSESSMENT",
                        "risk_id": "RISK-001",
                        "value": "Same.",
                    },
                    "question": "Second?",
                    "rationale": "Second.",
                },
            ]
        },
        {
            "criticism_dispositions": [
                {
                    "criticism_id": "CRIT-001",
                    "outcome": "DISMISSED",
                    "rationale": "First.",
                },
                {
                    "criticism_id": "CRIT-001",
                    "outcome": "DISMISSED",
                    "rationale": "Duplicate.",
                },
            ]
        },
    ],
)
def test_final_review_rejects_intrinsic_aggregate_duplicates_and_gaps(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        final_review(**overrides)


def test_final_review_rejects_one_invalid_nested_item_atomically() -> None:
    with pytest.raises(ValidationError):
        final_review(
            principal_risks=[
                {"risk_id": "RISK-001", "rationale": "Valid."},
                {"risk_id": " ", "rationale": "Invalid."},
            ]
        )
