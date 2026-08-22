import pytest
from pydantic import TypeAdapter, ValidationError

from agentic_review_board.domain.risks import (
    ProblemAnalysisBasisReference,
    ProblemAnalysisFindingKind,
    ReviewInputBasisReference,
    Risk,
    RiskAssessment,
    RiskBasisReference,
    RiskBasisSource,
    RiskScope,
    RiskScopeKind,
    SolutionAlternativeBasisReference,
    SolutionAlternativeCharacteristicKind,
)
from agentic_review_board.domain.solutions import ConstraintReference


def test_overall_scope_requires_no_alternative_ids() -> None:
    scope = RiskScope(kind=RiskScopeKind.OVERALL)

    assert scope.kind is RiskScopeKind.OVERALL
    assert scope.alternative_ids == ()

    with pytest.raises(ValidationError):
        RiskScope(
            kind=RiskScopeKind.OVERALL,
            alternative_ids=("ALT-001",),
        )


def test_alternatives_scope_requires_at_least_one_alternative_id() -> None:
    scope = RiskScope(
        kind=RiskScopeKind.ALTERNATIVES,
        alternative_ids=("ALT-001", "ALT-002"),
    )

    assert scope.alternative_ids == ("ALT-001", "ALT-002")

    with pytest.raises(ValidationError):
        RiskScope(kind=RiskScopeKind.ALTERNATIVES)


def test_alternative_ids_must_be_non_blank_and_unique() -> None:
    with pytest.raises(ValidationError):
        RiskScope(
            kind=RiskScopeKind.ALTERNATIVES,
            alternative_ids=(" ",),
        )

    with pytest.raises(ValidationError):
        RiskScope(
            kind=RiskScopeKind.ALTERNATIVES,
            alternative_ids=("ALT-001", "ALT-001"),
        )


def test_scope_is_closed_frozen_and_tuple_backed() -> None:
    scope = RiskScope.model_validate(
        {
            "kind": "ALTERNATIVES",
            "alternative_ids": ["ALT-001"],
        }
    )

    assert scope.alternative_ids == ("ALT-001",)
    assert isinstance(scope.alternative_ids, tuple)

    with pytest.raises(ValidationError):
        scope.kind = RiskScopeKind.OVERALL

    with pytest.raises(ValidationError):
        RiskScope.model_validate(
            {
                "kind": "OVERALL",
                "alternative_ids": [],
                "unexpected": "not allowed",
            }
        )


def test_risk_basis_source_values_are_closed_and_exact() -> None:
    assert tuple(member.value for member in RiskBasisSource) == (
        "REVIEW_INPUT",
        "PROBLEM_ANALYSIS",
        "SOLUTION_ALTERNATIVE",
    )

    with pytest.raises(ValueError):
        RiskBasisSource("EXTERNAL_SOURCE")


def test_problem_analysis_finding_kind_values_are_closed_and_exact() -> None:
    assert tuple(member.value for member in ProblemAnalysisFindingKind) == (
        "FACT",
        "CONSTRAINT",
        "ASSUMPTION",
        "MISSING_INFORMATION",
        "UNCERTAINTY",
    )

    with pytest.raises(ValueError):
        ProblemAnalysisFindingKind("RECOMMENDATION")


def test_solution_alternative_characteristic_kind_values_are_closed_and_exact() -> None:
    assert tuple(member.value for member in SolutionAlternativeCharacteristicKind) == (
        "DESCRIPTION",
        "ADVANTAGE",
        "DISADVANTAGE",
        "ASSUMPTION",
        "IMPLEMENTATION_COMPLEXITY",
        "RELEVANT_CONSTRAINT",
    )

    with pytest.raises(ValueError):
        SolutionAlternativeCharacteristicKind("NAME")


def test_risk_basis_reference_discriminator_selects_review_input_variant() -> None:
    reference: RiskBasisReference = TypeAdapter(RiskBasisReference).validate_python(
        {
            "source": "REVIEW_INPUT",
            "field": "description",
            "value": "Review a proposed technical change.",
        }
    )

    assert isinstance(reference, ReviewInputBasisReference)
    assert reference.source is RiskBasisSource.REVIEW_INPUT


def test_risk_basis_reference_discriminator_selects_problem_analysis_variant() -> None:
    reference: RiskBasisReference = TypeAdapter(RiskBasisReference).validate_python(
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "FACT",
            "text": "The capability must run offline.",
            "id": "FACT-001",
        }
    )

    assert isinstance(reference, ProblemAnalysisBasisReference)
    assert reference.source is RiskBasisSource.PROBLEM_ANALYSIS


def test_risk_basis_reference_discriminator_selects_solution_alternative_variant() -> None:
    reference: RiskBasisReference = TypeAdapter(RiskBasisReference).validate_python(
        {
            "source": "SOLUTION_ALTERNATIVE",
            "alternative_id": "ALT-001",
            "characteristic": "DESCRIPTION",
            "value": "Run the capability in the existing local environment.",
        }
    )

    assert isinstance(reference, SolutionAlternativeBasisReference)
    assert reference.source is RiskBasisSource.SOLUTION_ALTERNATIVE


@pytest.mark.parametrize(
    ("model", "payload", "wrong_source"),
    [
        (
            ReviewInputBasisReference,
            {
                "field": "description",
                "value": "Review a proposed technical change.",
            },
            "PROBLEM_ANALYSIS",
        ),
        (
            ProblemAnalysisBasisReference,
            {
                "kind": "FACT",
                "text": "The capability must run offline.",
            },
            "SOLUTION_ALTERNATIVE",
        ),
        (
            SolutionAlternativeBasisReference,
            {
                "alternative_id": "ALT-001",
                "characteristic": "DESCRIPTION",
                "value": "Run the capability locally.",
            },
            "REVIEW_INPUT",
        ),
    ],
)
def test_each_basis_variant_enforces_its_literal_source_tag(
    model: type[
        ReviewInputBasisReference
        | ProblemAnalysisBasisReference
        | SolutionAlternativeBasisReference
    ],
    payload: dict[str, object],
    wrong_source: str,
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({"source": wrong_source, **payload})


def test_risk_basis_reference_rejects_unknown_discriminator_value() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(RiskBasisReference).validate_python(
            {
                "source": "EXTERNAL_SOURCE",
                "value": "Unsupported provenance.",
            }
        )


def test_review_input_basis_reference_rejects_blank_value() -> None:
    with pytest.raises(ValidationError):
        ReviewInputBasisReference.model_validate(
            {
                "source": "REVIEW_INPUT",
                "field": "description",
                "value": " ",
            }
        )


def test_problem_analysis_basis_reference_rejects_blank_text_and_optional_id() -> None:
    with pytest.raises(ValidationError):
        ProblemAnalysisBasisReference.model_validate(
            {
                "source": "PROBLEM_ANALYSIS",
                "kind": "FACT",
                "text": " ",
            }
        )

    with pytest.raises(ValidationError):
        ProblemAnalysisBasisReference.model_validate(
            {
                "source": "PROBLEM_ANALYSIS",
                "kind": "FACT",
                "text": "The capability must run offline.",
                "id": " ",
            }
        )


def test_solution_alternative_basis_reference_rejects_blank_required_text() -> None:
    with pytest.raises(ValidationError):
        SolutionAlternativeBasisReference.model_validate(
            {
                "source": "SOLUTION_ALTERNATIVE",
                "alternative_id": " ",
                "characteristic": "DESCRIPTION",
                "value": "Run the capability locally.",
            }
        )

    with pytest.raises(ValidationError):
        SolutionAlternativeBasisReference.model_validate(
            {
                "source": "SOLUTION_ALTERNATIVE",
                "alternative_id": "ALT-001",
                "characteristic": "DESCRIPTION",
                "value": " ",
            }
        )


def test_relevant_constraint_requires_structured_constraint_reference() -> None:
    reference = SolutionAlternativeBasisReference.model_validate(
        {
            "source": "SOLUTION_ALTERNATIVE",
            "alternative_id": "ALT-001",
            "characteristic": "RELEVANT_CONSTRAINT",
            "value": {
                "source": "PROBLEM_ANALYSIS",
                "kind": "ID",
                "value": "CON-001",
            },
        }
    )

    assert isinstance(reference.value, ConstraintReference)

    with pytest.raises(ValidationError):
        SolutionAlternativeBasisReference.model_validate(
            {
                "source": "SOLUTION_ALTERNATIVE",
                "alternative_id": "ALT-001",
                "characteristic": "RELEVANT_CONSTRAINT",
                "value": "CON-001",
            }
        )


def test_non_constraint_characteristics_require_strict_text_value() -> None:
    constraint = ConstraintReference.model_validate(
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        }
    )

    with pytest.raises(ValidationError):
        SolutionAlternativeBasisReference(
            alternative_id="ALT-001",
            characteristic=SolutionAlternativeCharacteristicKind.DESCRIPTION,
            value=constraint,
        )


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            ReviewInputBasisReference,
            {
                "source": "REVIEW_INPUT",
                "field": "description",
                "value": "Review a proposed technical change.",
            },
        ),
        (
            ProblemAnalysisBasisReference,
            {
                "source": "PROBLEM_ANALYSIS",
                "kind": "FACT",
                "text": "The capability must run offline.",
            },
        ),
        (
            SolutionAlternativeBasisReference,
            {
                "source": "SOLUTION_ALTERNATIVE",
                "alternative_id": "ALT-001",
                "characteristic": "DESCRIPTION",
                "value": "Run the capability locally.",
            },
        ),
    ],
)
def test_basis_reference_variants_forbid_extra_fields(
    model: type[
        ReviewInputBasisReference
        | ProblemAnalysisBasisReference
        | SolutionAlternativeBasisReference
    ],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({**payload, "unexpected": "not allowed"})


def risk_payload(*, risk_id: str = "RISK-001") -> dict[str, object]:
    return {
        "id": risk_id,
        "category": "technical",
        "description": "Local lifecycle management may increase operational burden.",
        "affected_scope": {"kind": "OVERALL", "alternative_ids": []},
        "severity": "MEDIUM",
        "basis": [
            {
                "source": "REVIEW_INPUT",
                "field": "description",
                "value": "Review a proposed technical change.",
            }
        ],
        "mitigation": "Define a minimal local maintenance process.",
        "residual_uncertainty": "Actual maintenance effort is not yet measured.",
    }


def test_risk_accepts_open_non_blank_category_label() -> None:
    payload = risk_payload()
    payload["category"] = "legal/compliance"

    risk = Risk.model_validate(payload)

    assert risk.category == "legal/compliance"


def test_all_risk_domain_models_are_frozen_and_extra_forbid() -> None:
    models = (
        RiskScope,
        ReviewInputBasisReference,
        ProblemAnalysisBasisReference,
        SolutionAlternativeBasisReference,
        Risk,
        RiskAssessment,
    )

    for model in models:
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("extra") == "forbid"


def test_risk_optional_text_fields_may_be_omitted() -> None:
    payload = risk_payload()
    payload.pop("category")
    payload.pop("mitigation")
    payload.pop("residual_uncertainty")

    risk = Risk.model_validate(payload)

    assert risk.category is None
    assert risk.mitigation is None
    assert risk.residual_uncertainty is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", " "),
        ("description", " "),
        ("category", " "),
        ("mitigation", " "),
        ("residual_uncertainty", " "),
    ],
)
def test_risk_rejects_blank_required_or_present_optional_text(
    field: str,
    value: str,
) -> None:
    payload = risk_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        Risk.model_validate(payload)


def test_risk_requires_non_empty_basis() -> None:
    payload = risk_payload()
    payload["basis"] = []

    with pytest.raises(ValidationError):
        Risk.model_validate(payload)


def test_risk_rejects_exact_duplicate_basis_references() -> None:
    payload = risk_payload()
    basis_reference = {
        "source": "REVIEW_INPUT",
        "field": "description",
        "value": "Review a proposed technical change.",
    }
    payload["basis"] = [basis_reference, basis_reference.copy()]

    with pytest.raises(ValidationError):
        Risk.model_validate(payload)


def test_risk_assessment_requires_unique_risk_ids() -> None:
    with pytest.raises(ValidationError):
        RiskAssessment.model_validate(
            {
                "risks": [risk_payload(), risk_payload()],
                "overall_observations": [],
            }
        )


def test_risk_assessment_rejects_blank_or_duplicate_observations() -> None:
    with pytest.raises(ValidationError):
        RiskAssessment.model_validate(
            {
                "risks": [],
                "overall_observations": [" "],
            }
        )

    with pytest.raises(ValidationError):
        RiskAssessment.model_validate(
            {
                "risks": [],
                "overall_observations": [
                    "Operational ownership remains unclear.",
                    "Operational ownership remains unclear.",
                ],
            }
        )


def test_zero_risk_and_fully_empty_assessments_are_valid() -> None:
    zero_risk = RiskAssessment.model_validate(
        {
            "risks": [],
            "overall_observations": ["No material risk is justified by the current inputs."],
        }
    )
    fully_empty = RiskAssessment.model_validate(
        {
            "risks": [],
            "overall_observations": [],
        }
    )

    assert zero_risk.risks == ()
    assert fully_empty.risks == ()
    assert fully_empty.overall_observations == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ranking", ["ALT-001", "ALT-002"]),
        ("preferred_alternative", "ALT-001"),
        ("recommendation", "Choose ALT-001"),
        ("winner", "ALT-001"),
        ("alternatives", [{"id": "ALT-003"}]),
        ("replacement_alternative", {"id": "ALT-003"}),
        ("replacement_alternatives", [{"id": "ALT-003"}]),
    ],
)
def test_risk_assessment_rejects_ranking_recommendation_and_alternative_redefinition(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RiskAssessment.model_validate(
            {
                "risks": [],
                "overall_observations": [],
                field: value,
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("probability", 0.7),
        ("likelihood", 0.7),
        ("risk_score", 7),
    ],
)
def test_risk_rejects_unsupported_numeric_probability_and_scoring_fields(
    field: str,
    value: object,
) -> None:
    payload = risk_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        Risk.model_validate(payload)
