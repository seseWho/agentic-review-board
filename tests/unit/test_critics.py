import pytest
from pydantic import ValidationError

from agentic_review_board.domain.critics import (
    CriticReference,
    CriticReferenceKind,
    CriticReferenceSource,
    CriticismImportance,
    CriticismTargetType,
)


REVIEW_INPUT_KINDS = (
    CriticReferenceKind.DESCRIPTION,
    CriticReferenceKind.TITLE,
    CriticReferenceKind.REVIEW_OBJECTIVE,
    CriticReferenceKind.REVIEW_CONSTRAINT,
    CriticReferenceKind.CONTEXT,
    CriticReferenceKind.STATED_FACT,
)

PROBLEM_ANALYSIS_KINDS = (
    CriticReferenceKind.PROBLEM_OBJECTIVE,
    CriticReferenceKind.PROBLEM_FACT,
    CriticReferenceKind.PROBLEM_CONSTRAINT,
    CriticReferenceKind.PROBLEM_ASSUMPTION,
    CriticReferenceKind.MISSING_INFORMATION,
    CriticReferenceKind.UNCERTAINTY,
)

SOLUTION_ALTERNATIVES_KINDS = (
    CriticReferenceKind.ALTERNATIVE,
    CriticReferenceKind.ALTERNATIVE_NAME,
    CriticReferenceKind.ALTERNATIVE_DESCRIPTION,
    CriticReferenceKind.ADVANTAGE,
    CriticReferenceKind.DISADVANTAGE,
    CriticReferenceKind.ALTERNATIVE_ASSUMPTION,
    CriticReferenceKind.IMPLEMENTATION_COMPLEXITY,
    CriticReferenceKind.GENERATION_EXPLANATION,
    CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
    CriticReferenceKind.BLOCKING_UNCERTAINTY,
)

RISK_ASSESSMENT_KINDS = (
    CriticReferenceKind.RISK,
    CriticReferenceKind.RISK_CATEGORY,
    CriticReferenceKind.RISK_DESCRIPTION,
    CriticReferenceKind.RISK_SEVERITY,
    CriticReferenceKind.MITIGATION,
    CriticReferenceKind.RESIDUAL_UNCERTAINTY,
    CriticReferenceKind.OVERALL_OBSERVATION,
)

VALUE_ONLY_KINDS = (
    CriticReferenceKind.DESCRIPTION,
    CriticReferenceKind.TITLE,
    CriticReferenceKind.REVIEW_OBJECTIVE,
    CriticReferenceKind.REVIEW_CONSTRAINT,
    CriticReferenceKind.CONTEXT,
    CriticReferenceKind.STATED_FACT,
    CriticReferenceKind.PROBLEM_OBJECTIVE,
    CriticReferenceKind.GENERATION_EXPLANATION,
    CriticReferenceKind.OVERALL_OBSERVATION,
)

OPTIONAL_FINDING_ID_KINDS = (
    CriticReferenceKind.PROBLEM_FACT,
    CriticReferenceKind.PROBLEM_CONSTRAINT,
    CriticReferenceKind.PROBLEM_ASSUMPTION,
    CriticReferenceKind.MISSING_INFORMATION,
    CriticReferenceKind.UNCERTAINTY,
    CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
    CriticReferenceKind.BLOCKING_UNCERTAINTY,
)

ID_PRIMARY_KINDS = (
    CriticReferenceKind.ALTERNATIVE,
    CriticReferenceKind.RISK,
)

PARENT_ID_VALUE_KINDS = (
    CriticReferenceKind.ALTERNATIVE_NAME,
    CriticReferenceKind.ALTERNATIVE_DESCRIPTION,
    CriticReferenceKind.ADVANTAGE,
    CriticReferenceKind.DISADVANTAGE,
    CriticReferenceKind.ALTERNATIVE_ASSUMPTION,
    CriticReferenceKind.IMPLEMENTATION_COMPLEXITY,
    CriticReferenceKind.RISK_CATEGORY,
    CriticReferenceKind.RISK_DESCRIPTION,
    CriticReferenceKind.RISK_SEVERITY,
    CriticReferenceKind.MITIGATION,
    CriticReferenceKind.RESIDUAL_UNCERTAINTY,
)


def test_critic_reference_source_values_are_closed_and_exact() -> None:
    assert tuple(member.value for member in CriticReferenceSource) == (
        "REVIEW_INPUT",
        "PROBLEM_ANALYSIS",
        "SOLUTION_ALTERNATIVES",
        "RISK_ASSESSMENT",
    )

    with pytest.raises(ValueError):
        CriticReferenceSource("EXTERNAL_SOURCE")


def test_critic_reference_kind_values_are_closed_and_exact() -> None:
    assert tuple(member.value for member in CriticReferenceKind) == (
        "DESCRIPTION",
        "TITLE",
        "REVIEW_OBJECTIVE",
        "REVIEW_CONSTRAINT",
        "CONTEXT",
        "STATED_FACT",
        "PROBLEM_OBJECTIVE",
        "PROBLEM_FACT",
        "PROBLEM_CONSTRAINT",
        "PROBLEM_ASSUMPTION",
        "MISSING_INFORMATION",
        "UNCERTAINTY",
        "ALTERNATIVE",
        "ALTERNATIVE_NAME",
        "ALTERNATIVE_DESCRIPTION",
        "ADVANTAGE",
        "DISADVANTAGE",
        "ALTERNATIVE_ASSUMPTION",
        "IMPLEMENTATION_COMPLEXITY",
        "GENERATION_EXPLANATION",
        "BLOCKING_MISSING_INFORMATION",
        "BLOCKING_UNCERTAINTY",
        "RISK",
        "RISK_CATEGORY",
        "RISK_DESCRIPTION",
        "RISK_SEVERITY",
        "MITIGATION",
        "RESIDUAL_UNCERTAINTY",
        "OVERALL_OBSERVATION",
    )

    for unsupported in (
        "QUESTION",
        "INTERPRETATION",
        "KEY_CONSIDERATION",
        "ANALYSIS_UNCERTAINTY",
        "DEPENDENCY",
        "RESIDUAL_CONCERN",
        "RELEVANT_CONSTRAINT",
        "AFFECTED_SCOPE",
        "RISK_BASIS",
    ):
        with pytest.raises(ValueError):
            CriticReferenceKind(unsupported)


@pytest.mark.parametrize(
    ("source", "legal_kinds"),
    [
        (CriticReferenceSource.REVIEW_INPUT, REVIEW_INPUT_KINDS),
        (CriticReferenceSource.PROBLEM_ANALYSIS, PROBLEM_ANALYSIS_KINDS),
        (CriticReferenceSource.SOLUTION_ALTERNATIVES, SOLUTION_ALTERNATIVES_KINDS),
        (CriticReferenceSource.RISK_ASSESSMENT, RISK_ASSESSMENT_KINDS),
    ],
)
def test_reference_accepts_every_legal_source_kind_combination(
    source: CriticReferenceSource,
    legal_kinds: tuple[CriticReferenceKind, ...],
) -> None:
    for kind in legal_kinds:
        if kind in VALUE_ONLY_KINDS:
            reference = CriticReference(source=source, kind=kind, value="visible value")
        elif kind in OPTIONAL_FINDING_ID_KINDS:
            reference = CriticReference(source=source, kind=kind, value="finding text")
        elif kind in ID_PRIMARY_KINDS:
            reference = CriticReference(source=source, kind=kind, item_id="ITEM-001")
        else:
            reference = CriticReference(
                source=source,
                kind=kind,
                item_id="PARENT-001",
                value="nested value",
            )

        assert reference.source is source
        assert reference.kind is kind


@pytest.mark.parametrize(
    ("source", "legal_kinds"),
    [
        (CriticReferenceSource.REVIEW_INPUT, REVIEW_INPUT_KINDS),
        (CriticReferenceSource.PROBLEM_ANALYSIS, PROBLEM_ANALYSIS_KINDS),
        (CriticReferenceSource.SOLUTION_ALTERNATIVES, SOLUTION_ALTERNATIVES_KINDS),
        (CriticReferenceSource.RISK_ASSESSMENT, RISK_ASSESSMENT_KINDS),
    ],
)
def test_reference_rejects_every_illegal_source_kind_combination(
    source: CriticReferenceSource,
    legal_kinds: tuple[CriticReferenceKind, ...],
) -> None:
    illegal_kinds = tuple(kind for kind in CriticReferenceKind if kind not in legal_kinds)

    for kind in illegal_kinds:
        with pytest.raises(ValidationError):
            CriticReference(
                source=source,
                kind=kind,
                item_id="ITEM-001",
                value="visible value",
            )


@pytest.mark.parametrize("kind", VALUE_ONLY_KINDS)
def test_value_only_reference_shape(kind: CriticReferenceKind) -> None:
    source = (
        CriticReferenceSource.REVIEW_INPUT
        if kind in REVIEW_INPUT_KINDS
        else CriticReferenceSource.PROBLEM_ANALYSIS
        if kind in PROBLEM_ANALYSIS_KINDS
        else CriticReferenceSource.SOLUTION_ALTERNATIVES
        if kind in SOLUTION_ALTERNATIVES_KINDS
        else CriticReferenceSource.RISK_ASSESSMENT
    )

    reference = CriticReference(source=source, kind=kind, value="  visible value  ")

    assert reference.item_id is None
    assert reference.value == "visible value"

    with pytest.raises(ValidationError):
        CriticReference(source=source, kind=kind)

    with pytest.raises(ValidationError):
        CriticReference(source=source, kind=kind, item_id="ITEM-001", value="visible value")


@pytest.mark.parametrize("kind", OPTIONAL_FINDING_ID_KINDS)
def test_optional_finding_id_reference_shape(kind: CriticReferenceKind) -> None:
    source = (
        CriticReferenceSource.PROBLEM_ANALYSIS
        if kind in PROBLEM_ANALYSIS_KINDS
        else CriticReferenceSource.SOLUTION_ALTERNATIVES
    )

    without_id = CriticReference(source=source, kind=kind, value="finding text")
    with_id = CriticReference(
        source=source,
        kind=kind,
        item_id="  FINDING-001  ",
        value="  finding text  ",
    )

    assert without_id.item_id is None
    assert with_id.item_id == "FINDING-001"
    assert with_id.value == "finding text"

    with pytest.raises(ValidationError):
        CriticReference(source=source, kind=kind, item_id="FINDING-001")


@pytest.mark.parametrize("kind", ID_PRIMARY_KINDS)
def test_id_primary_reference_shape(kind: CriticReferenceKind) -> None:
    source = (
        CriticReferenceSource.SOLUTION_ALTERNATIVES
        if kind is CriticReferenceKind.ALTERNATIVE
        else CriticReferenceSource.RISK_ASSESSMENT
    )

    without_value = CriticReference(source=source, kind=kind, item_id="ITEM-001")
    with_value = CriticReference(
        source=source,
        kind=kind,
        item_id="ITEM-001",
        value="compatible visible value",
    )

    assert without_value.value is None
    assert with_value.value == "compatible visible value"

    with pytest.raises(ValidationError):
        CriticReference(source=source, kind=kind, value="compatible visible value")


@pytest.mark.parametrize("kind", PARENT_ID_VALUE_KINDS)
def test_parent_id_and_value_reference_shape(kind: CriticReferenceKind) -> None:
    source = (
        CriticReferenceSource.SOLUTION_ALTERNATIVES
        if kind in SOLUTION_ALTERNATIVES_KINDS
        else CriticReferenceSource.RISK_ASSESSMENT
    )

    reference = CriticReference(
        source=source,
        kind=kind,
        item_id="PARENT-001",
        value="nested value",
    )

    assert reference.item_id == "PARENT-001"
    assert reference.value == "nested value"

    with pytest.raises(ValidationError):
        CriticReference(source=source, kind=kind, item_id="PARENT-001")

    with pytest.raises(ValidationError):
        CriticReference(source=source, kind=kind, value="nested value")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "source": "REVIEW_INPUT",
            "kind": "DESCRIPTION",
            "value": " ",
        },
        {
            "source": "SOLUTION_ALTERNATIVES",
            "kind": "ALTERNATIVE",
            "item_id": " ",
        },
        {
            "source": "RISK_ASSESSMENT",
            "kind": "MITIGATION",
            "item_id": "RISK-001",
            "value": " ",
        },
    ],
)
def test_reference_rejects_blank_required_or_present_optional_text(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CriticReference.model_validate(payload)


def test_reference_is_frozen_and_forbids_extra_fields() -> None:
    reference = CriticReference(
        source=CriticReferenceSource.REVIEW_INPUT,
        kind=CriticReferenceKind.DESCRIPTION,
        value="visible value",
    )

    with pytest.raises(ValidationError):
        reference.value = "changed"

    with pytest.raises(ValidationError):
        CriticReference.model_validate(
            {
                "source": "REVIEW_INPUT",
                "kind": "DESCRIPTION",
                "value": "visible value",
                "unexpected": "not allowed",
            }
        )


def test_criticism_importance_values_are_closed_qualitative_and_exact() -> None:
    assert tuple(member.value for member in CriticismImportance) == (
        "LOW",
        "MEDIUM",
        "HIGH",
    )

    for unsupported in ("CRITICAL", "0", "1", "2", "3"):
        with pytest.raises(ValueError):
            CriticismImportance(unsupported)


def test_criticism_target_type_values_are_closed_and_exact() -> None:
    assert tuple(member.value for member in CriticismTargetType) == (
        "ASSUMPTION",
        "CONSTRAINT",
        "ANALYSIS",
        "ALTERNATIVE",
        "ALTERNATIVE_CHARACTERISTIC",
        "RISK",
        "MITIGATION",
        "CROSS_ARTIFACT_CONCLUSION",
        "OMISSION",
    )

    for unsupported in ("RANKING", "RECOMMENDATION", "WINNER"):
        with pytest.raises(ValueError):
            CriticismTargetType(unsupported)
