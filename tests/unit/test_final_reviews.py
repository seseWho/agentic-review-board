import pytest
from pydantic import ValidationError

from agentic_review_board.domain.final_reviews import (
    CriticismDispositionOutcome,
    FinalReviewSection,
    PrincipalRisk,
    RankedAlternative,
    RecommendationOutcome,
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
        ranked.position = 2  # type: ignore[misc]

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
        principal.risk_id = "RISK-002"  # type: ignore[misc]


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
