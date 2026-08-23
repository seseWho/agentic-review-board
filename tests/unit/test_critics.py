import pytest
from pydantic import ValidationError

from agentic_review_board.domain.critics import (
    Contradiction,
    ContradictionSide,
    CriticalReview,
    Criticism,
    CriticismImportance,
    CriticismTargetType,
    CriticReference,
    CriticReferenceKind,
    CriticReferenceSource,
    MissingAlternative,
    UnresolvedIssue,
    ValidatedPoint,
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


def review_description_reference() -> CriticReference:
    return CriticReference(
        source=CriticReferenceSource.REVIEW_INPUT,
        kind=CriticReferenceKind.DESCRIPTION,
        value="Review a proposed technical change.",
    )


def problem_assumption_reference() -> CriticReference:
    return CriticReference(
        source=CriticReferenceSource.PROBLEM_ANALYSIS,
        kind=CriticReferenceKind.PROBLEM_ASSUMPTION,
        item_id="ASSUMPTION-001",
        value="The existing team can maintain the proposed solution.",
    )


def risk_reference() -> CriticReference:
    return CriticReference(
        source=CriticReferenceSource.RISK_ASSESSMENT,
        kind=CriticReferenceKind.RISK,
        item_id="RISK-001",
        value="Operational ownership is not established.",
    )


def criticism_payload(*, criticism_id: str = "CRIT-001") -> dict[str, object]:
    return {
        "id": criticism_id,
        "target_type": "ASSUMPTION",
        "target_reference": problem_assumption_reference().model_dump(mode="json"),
        "basis_references": [review_description_reference().model_dump(mode="json")],
        "issue": "The maintenance assumption is unsupported.",
        "importance": "HIGH",
        "rationale": "No current input establishes an available maintenance owner.",
        "correction_or_question": "Who will own ongoing maintenance?",
    }


def validated_point_payload(*, point_id: str = "VALID-001") -> dict[str, object]:
    return {
        "id": point_id,
        "target_reference": review_description_reference().model_dump(mode="json"),
        "rationale": "The review description clearly identifies the proposed change.",
    }


def missing_alternative_payload(*, finding_id: str = "MISSING-001") -> dict[str, object]:
    return {
        "id": finding_id,
        "category": "Incremental adoption",
        "rationale": "The current portfolio contains only full replacement approaches.",
        "weakens_later_recommendation": True,
        "basis_references": [review_description_reference().model_dump(mode="json")],
    }


def contradiction_payload(*, contradiction_id: str = "CONTRA-001") -> dict[str, object]:
    return {
        "id": contradiction_id,
        "side_a": {
            "reference": problem_assumption_reference().model_dump(mode="json"),
            "statement": "The existing team can maintain the proposed solution.",
        },
        "side_b": {
            "reference": risk_reference().model_dump(mode="json"),
            "statement": "Operational ownership is not established.",
        },
        "rationale": "The assumed maintenance capability conflicts with the ownership risk.",
    }


def unresolved_issue_payload(*, issue_id: str = "UNRESOLVED-001") -> dict[str, object]:
    return {
        "id": issue_id,
        "issue": "Operational ownership remains unresolved.",
        "rationale": "The current review identifies a risk but no confirmed owner.",
        "basis_references": [risk_reference().model_dump(mode="json")],
    }


def test_criticism_requires_target_or_visible_basis() -> None:
    with pytest.raises(ValidationError):
        Criticism.model_validate(
            {
                "id": "CRIT-001",
                "target_type": "ANALYSIS",
                "target_reference": None,
                "basis_references": [],
                "issue": "The analysis is weak.",
                "importance": "MEDIUM",
                "rationale": "No inspectable support was provided.",
                "correction_or_question": None,
            }
        )

    target_only = criticism_payload()
    target_only["basis_references"] = []
    criticism = Criticism.model_validate(target_only)

    assert criticism.target_reference == problem_assumption_reference()
    assert criticism.basis_references == ()


def test_criticism_rejects_duplicate_basis_and_target_repeated_as_basis() -> None:
    duplicate_basis = criticism_payload()
    basis = review_description_reference().model_dump(mode="json")
    duplicate_basis["basis_references"] = [basis, basis.copy()]

    with pytest.raises(ValidationError):
        Criticism.model_validate(duplicate_basis)

    repeated_target = criticism_payload()
    repeated_target["basis_references"] = [
        problem_assumption_reference().model_dump(mode="json")
    ]

    with pytest.raises(ValidationError):
        Criticism.model_validate(repeated_target)


@pytest.mark.parametrize(
    "field",
    ["id", "issue", "rationale", "correction_or_question"],
)
def test_criticism_rejects_blank_required_or_present_optional_text(field: str) -> None:
    payload = criticism_payload()
    payload[field] = " "

    with pytest.raises(ValidationError):
        Criticism.model_validate(payload)


def test_criticism_allows_omitted_correction_or_question() -> None:
    payload = criticism_payload()
    payload["correction_or_question"] = None

    criticism = Criticism.model_validate(payload)

    assert criticism.correction_or_question is None


def test_validated_point_requires_explicit_target_reference() -> None:
    payload = validated_point_payload()
    payload.pop("target_reference")

    with pytest.raises(ValidationError):
        ValidatedPoint.model_validate(payload)


def test_validated_point_preserves_assumption_reference_semantics() -> None:
    payload = validated_point_payload()
    payload["target_reference"] = problem_assumption_reference().model_dump(mode="json")

    point = ValidatedPoint.model_validate(payload)

    assert point.target_reference.kind is CriticReferenceKind.PROBLEM_ASSUMPTION
    assert not hasattr(point, "fact")
    assert not hasattr(point, "promoted_to_fact")


def test_missing_alternative_requires_non_empty_unique_basis() -> None:
    payload = missing_alternative_payload()
    payload["basis_references"] = []

    with pytest.raises(ValidationError):
        MissingAlternative.model_validate(payload)

    duplicate_payload = missing_alternative_payload()
    basis = review_description_reference().model_dump(mode="json")
    duplicate_payload["basis_references"] = [basis, basis.copy()]

    with pytest.raises(ValidationError):
        MissingAlternative.model_validate(duplicate_payload)


def test_missing_alternative_uses_boolean_recommendation_impact() -> None:
    finding = MissingAlternative.model_validate(missing_alternative_payload())

    assert finding.weakens_later_recommendation is True

    payload = missing_alternative_payload()
    payload["weakens_later_recommendation"] = "HIGH"

    with pytest.raises(ValidationError):
        MissingAlternative.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "description",
        "advantages",
        "disadvantages",
        "assumptions",
        "replacement_alternative",
        "replacement_alternatives",
    ],
)
def test_missing_alternative_rejects_replacement_portfolio_fields(field: str) -> None:
    payload = missing_alternative_payload()
    payload[field] = "not allowed"

    with pytest.raises(ValidationError):
        MissingAlternative.model_validate(payload)


def test_contradiction_requires_two_non_identical_sides() -> None:
    payload = contradiction_payload()
    payload["side_b"] = payload["side_a"]

    with pytest.raises(ValidationError):
        Contradiction.model_validate(payload)


def test_contradiction_side_requires_non_blank_statement() -> None:
    payload = contradiction_payload()
    side_a = dict(payload["side_a"])  # type: ignore[arg-type]
    side_a["statement"] = " "
    payload["side_a"] = side_a

    with pytest.raises(ValidationError):
        Contradiction.model_validate(payload)


def test_contradiction_does_not_decide_which_side_is_true() -> None:
    payload = contradiction_payload()
    payload["winner"] = "side_a"

    with pytest.raises(ValidationError):
        Contradiction.model_validate(payload)


def test_unresolved_issue_requires_non_empty_unique_basis() -> None:
    payload = unresolved_issue_payload()
    payload["basis_references"] = []

    with pytest.raises(ValidationError):
        UnresolvedIssue.model_validate(payload)

    duplicate_payload = unresolved_issue_payload()
    basis = risk_reference().model_dump(mode="json")
    duplicate_payload["basis_references"] = [basis, basis.copy()]

    with pytest.raises(ValidationError):
        UnresolvedIssue.model_validate(duplicate_payload)


def test_fully_empty_critical_review_is_valid_and_tuple_backed() -> None:
    review = CriticalReview()

    assert review.criticisms == ()
    assert review.validated_points == ()
    assert review.missing_alternatives == ()
    assert review.contradictions == ()
    assert review.unresolved_issues == ()

    for collection in (
        review.criticisms,
        review.validated_points,
        review.missing_alternatives,
        review.contradictions,
        review.unresolved_issues,
    ):
        assert isinstance(collection, tuple)


@pytest.mark.parametrize(
    ("collection", "first", "second"),
    [
        ("criticisms", criticism_payload(), criticism_payload()),
        ("validated_points", validated_point_payload(), validated_point_payload()),
        (
            "missing_alternatives",
            missing_alternative_payload(),
            missing_alternative_payload(),
        ),
        ("contradictions", contradiction_payload(), contradiction_payload()),
        ("unresolved_issues", unresolved_issue_payload(), unresolved_issue_payload()),
    ],
)
def test_critical_review_requires_unique_ids_within_each_collection(
    collection: str,
    first: dict[str, object],
    second: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CriticalReview.model_validate({collection: [first, second]})


def test_critical_review_allows_same_id_across_different_collections() -> None:
    criticism = criticism_payload(criticism_id="SHARED-001")
    validated_point = validated_point_payload(point_id="SHARED-001")

    review = CriticalReview.model_validate(
        {
            "criticisms": [criticism],
            "validated_points": [validated_point],
        }
    )

    assert review.criticisms[0].id == review.validated_points[0].id


def test_critical_review_rejects_duplicate_validated_point_targets() -> None:
    first = validated_point_payload(point_id="VALID-001")
    second = validated_point_payload(point_id="VALID-002")
    second["rationale"] = "A different rationale for the same target."

    with pytest.raises(ValidationError):
        CriticalReview.model_validate({"validated_points": [first, second]})


def test_critical_review_rejects_duplicate_missing_alternative_categories() -> None:
    first = missing_alternative_payload(finding_id="MISSING-001")
    second = missing_alternative_payload(finding_id="MISSING-002")
    first["category"] = "  Incremental adoption  "
    second["category"] = "Incremental adoption"

    with pytest.raises(ValidationError):
        CriticalReview.model_validate({"missing_alternatives": [first, second]})


def test_missing_alternative_duplicate_category_detection_does_not_case_fold() -> None:
    first = missing_alternative_payload(finding_id="MISSING-001")
    second = missing_alternative_payload(finding_id="MISSING-002")
    first["category"] = "Incremental adoption"
    second["category"] = "incremental adoption"

    review = CriticalReview.model_validate({"missing_alternatives": [first, second]})

    assert len(review.missing_alternatives) == 2


def test_critical_review_rejects_duplicate_unordered_contradiction_side_pairs() -> None:
    first = contradiction_payload(contradiction_id="CONTRA-001")
    second = contradiction_payload(contradiction_id="CONTRA-002")
    second["side_a"], second["side_b"] = second["side_b"], second["side_a"]

    with pytest.raises(ValidationError):
        CriticalReview.model_validate({"contradictions": [first, second]})


def test_unresolved_issues_do_not_use_fuzzy_semantic_duplicate_detection() -> None:
    first = unresolved_issue_payload(issue_id="UNRESOLVED-001")
    second = unresolved_issue_payload(issue_id="UNRESOLVED-002")
    second["issue"] = "Ownership of operations has not yet been resolved."
    second["rationale"] = "No named person or team owns the operational responsibility."

    review = CriticalReview.model_validate({"unresolved_issues": [first, second]})

    assert len(review.unresolved_issues) == 2


def test_all_critic_domain_models_are_frozen_and_extra_forbid() -> None:
    models = (
        CriticReference,
        Criticism,
        ValidatedPoint,
        MissingAlternative,
        ContradictionSide,
        Contradiction,
        UnresolvedIssue,
        CriticalReview,
    )

    for model in models:
        assert model.model_config.get("frozen") is True
        assert model.model_config.get("extra") == "forbid"
        assert model.model_config.get("str_strip_whitespace") is True


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (Criticism, criticism_payload()),
        (ValidatedPoint, validated_point_payload()),
        (MissingAlternative, missing_alternative_payload()),
        (Contradiction, contradiction_payload()),
        (UnresolvedIssue, unresolved_issue_payload()),
        (CriticalReview, {}),
    ],
)
def test_critic_domain_models_are_closed(
    model: type[
        Criticism
        | ValidatedPoint
        | MissingAlternative
        | Contradiction
        | UnresolvedIssue
        | CriticalReview
    ],
    payload: dict[str, object],
) -> None:
    payload["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "payload", "field", "value"),
    [
        (CriticalReview, {}, "ranking", ["ALT-001", "ALT-002"]),
        (CriticalReview, {}, "preferred_alternative", "ALT-001"),
        (CriticalReview, {}, "recommendation", "Choose ALT-001"),
        (CriticalReview, {}, "winner", "ALT-001"),
        (CriticalReview, {}, "replacement_portfolio", [{"id": "ALT-003"}]),
        (Criticism, criticism_payload(), "confidence", 0.8),
        (Criticism, criticism_payload(), "probability", 0.8),
        (Criticism, criticism_payload(), "score", 8),
        (Criticism, criticism_payload(), "provider_metadata", {"model": "external"}),
        (Criticism, criticism_payload(), "chain_of_thought", "hidden reasoning"),
    ],
)
def test_critic_contracts_reject_coordinator_provider_and_hidden_reasoning_fields(
    model: type[CriticalReview | Criticism],
    payload: dict[str, object],
    field: str,
    value: object,
) -> None:
    payload[field] = value

    with pytest.raises(ValidationError):
        model.model_validate(payload)
