import pytest
from pydantic import ValidationError

from agentic_review_board.domain.final_reviews import (
    CriticismDisposition,
    CriticismDispositionOutcome,
    CriticUnresolvedKind,
    CriticUnresolvedReference,
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
