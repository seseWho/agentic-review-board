from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy

import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import (
    ProblemAnalysisBasisReference,
    ProblemAnalysisFindingKind,
    ReviewInputBasisReference,
    SolutionAlternativeBasisReference,
    SolutionAlternativeCharacteristicKind,
)
from agentic_review_board.domain.solutions import ConstraintReference, SolutionAlternatives
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    AllowedRiskBasis,
    RiskReviewerPayloadSnapshot,
    build_allowed_risk_bases,
    build_risk_reviewer_payload_snapshot,
    normalize_allowed_risk_bases,
)
from agentic_review_board.infrastructure.llm.errors import LLMRequestSchemaError

RISK_REVIEWER_PAYLOAD_KEYS = {
    "review_input",
    "problem_analysis",
    "solution_alternatives",
}


def risk_reviewer_payload(
    review_input: ReviewInput,
    problem_analysis: ProblemAnalysis,
    solution_alternatives: SolutionAlternatives,
) -> dict[str, object]:
    return {
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
        "solution_alternatives": solution_alternatives.model_dump(mode="json"),
    }


def minimal_risk_reviewer_payload() -> dict[str, object]:
    return risk_reviewer_payload(
        ReviewInput(description="Review a local migration."),
        ProblemAnalysis.model_validate(
            {
                "objective": "Assess migration feasibility.",
                "facts": [],
                "constraints": [],
                "assumptions": [],
                "missing_information": [],
                "uncertainties": [],
            }
        ),
        SolutionAlternatives.model_validate(
            {
                "alternatives": [],
                "generation_notes": {
                    "explanation": "No viable alternative can yet be grounded.",
                    "blocking_missing_information": [],
                    "blocking_uncertainties": [],
                },
            }
        ),
    )


def full_risk_reviewer_payload() -> dict[str, object]:
    return risk_reviewer_payload(
        ReviewInput(
            description="Review a local migration.",
            title="Desktop migration",
            objective="Select a safe migration direction.",
            constraints=("Must work offline.", "Keep deployment simple."),
            context=("Devices use ARM64.",),
            stated_facts=("The current client uses WPF.",),
        ),
        ProblemAnalysis.model_validate(
            {
                "objective": "Assess migration feasibility.",
                "facts": [
                    {
                        "id": "FACT-001",
                        "text": "The current client uses WPF.",
                        "source_ref": "stated_facts",
                    }
                ],
                "constraints": [
                    {"id": "CON-001", "text": "Must work offline."},
                    {"id": "CON-002", "text": "Keep deployment simple."},
                ],
                "assumptions": [
                    {"id": "ASM-001", "text": "Drivers support ARM64."}
                ],
                "missing_information": [
                    {"id": "MISS-001", "text": "Measured ARM64 memory usage."}
                ],
                "uncertainties": [
                    {"id": "UNC-001", "text": "ARM64 performance degradation."}
                ],
            }
        ),
        SolutionAlternatives.model_validate(
            {
                "alternatives": [
                    {
                        "id": "ALT-001",
                        "name": "Incremental migration",
                        "description": "Move WPF to .NET 8 incrementally.",
                        "advantages": ["Lower delivery risk."],
                        "disadvantages": ["Retains Windows coupling."],
                        "assumptions": ["Required libraries support .NET 8."],
                        "implementation_complexity": "MEDIUM",
                        "relevant_constraints": [
                            {
                                "source": "REVIEW_INPUT",
                                "kind": "TEXT",
                                "value": "Must work offline.",
                            }
                        ],
                    },
                    {
                        "id": "ALT-002",
                        "name": "Cross-platform rewrite",
                        "description": "Rewrite the client with .NET MAUI.",
                        "advantages": ["Broadens platform options."],
                        "disadvantages": ["Requires substantial rework."],
                        "assumptions": ["MAUI meets desktop requirements."],
                        "implementation_complexity": "HIGH",
                        "relevant_constraints": [
                            {
                                "source": "PROBLEM_ANALYSIS",
                                "kind": "ID",
                                "value": "CON-001",
                            }
                        ],
                    },
                ],
                "generation_notes": {
                    "explanation": "Two viable approaches were identified.",
                    "blocking_missing_information": [],
                    "blocking_uncertainties": [],
                },
            }
        ),
    )


def duplicate_heavy_risk_reviewer_payload() -> dict[str, object]:
    payload = full_risk_reviewer_payload()
    review_input = payload["review_input"]
    problem_analysis = payload["problem_analysis"]
    solution_alternatives = payload["solution_alternatives"]
    assert isinstance(review_input, dict)
    assert isinstance(problem_analysis, dict)
    assert isinstance(solution_alternatives, dict)

    review_input["title"] = ""
    review_input["constraints"] = ["Repeated input.", "Repeated input.", ""]
    problem_analysis["uncertainties"] = [
        {"id": None, "text": "Repeated uncertainty."},
        {"id": "UNC-002", "text": "Repeated uncertainty."},
    ]
    alternatives = solution_alternatives["alternatives"]
    assert isinstance(alternatives, list)
    first = alternatives[0]
    second = alternatives[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    first["advantages"] = ["Repeated advantage.", "Repeated advantage."]
    second["advantages"] = ["Repeated advantage."]
    first["relevant_constraints"] = [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        },
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        },
    ]
    return payload


def zero_alternative_risk_reviewer_payload() -> dict[str, object]:
    payload = minimal_risk_reviewer_payload()
    review_input = payload["review_input"]
    assert isinstance(review_input, dict)
    review_input["context"] = ["Only overall exposure can currently be assessed."]
    return payload


class SingleReadMapping(Mapping[str, object]):
    def __init__(self, values: dict[str, object]) -> None:
        self._values = values
        self.iterations = 0

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("Risk Reviewer payload mapping was read more than once")
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


@pytest.mark.parametrize(
    "payload_factory",
    [
        minimal_risk_reviewer_payload,
        full_risk_reviewer_payload,
        duplicate_heavy_risk_reviewer_payload,
        zero_alternative_risk_reviewer_payload,
    ],
)
def test_snapshot_accepts_exact_three_artifact_payload(payload_factory: object) -> None:
    assert callable(payload_factory)
    payload = payload_factory()

    snapshot = build_risk_reviewer_payload_snapshot(payload)

    assert isinstance(snapshot, RiskReviewerPayloadSnapshot)
    assert set(payload) == RISK_REVIEWER_PAYLOAD_KEYS
    assert json.loads(snapshot.serialized_payload) == payload
    assert snapshot.review_input == ReviewInput.model_validate(payload["review_input"])
    assert snapshot.problem_analysis == ProblemAnalysis.model_validate(
        payload["problem_analysis"]
    )
    assert snapshot.solution_alternatives == SolutionAlternatives.model_validate(
        payload["solution_alternatives"]
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.pop("solution_alternatives"),
        lambda payload: payload.update({"unexpected": {}}),
        lambda payload: payload.update({"review_input": []}),
        lambda payload: payload.update(
            {"problem_analysis": {"objective": "Incomplete analysis."}}
        ),
        lambda payload: payload.update(
            {
                "solution_alternatives": {
                    "alternatives": [
                        {
                            "id": "ALT-001",
                            "name": "Only one",
                            "description": "Invalid aggregate cardinality.",
                            "advantages": [],
                            "disadvantages": [],
                            "assumptions": [],
                            "implementation_complexity": "LOW",
                            "relevant_constraints": [],
                        }
                    ],
                    "generation_notes": None,
                }
            }
        ),
        lambda payload: payload.update(
            {"review_input": {"description": float("nan")}}
        ),
    ],
)
def test_snapshot_rejects_invalid_payload_with_safe_error(mutate: object) -> None:
    assert callable(mutate)
    payload = minimal_risk_reviewer_payload()
    mutate(payload)
    before = deepcopy(payload)

    with pytest.raises(
        LLMRequestSchemaError,
        match="^LLM request schema construction failed$",
    ):
        build_risk_reviewer_payload_snapshot(payload)

    assert payload.keys() == before.keys()
    for key in payload:
        value = payload[key]
        original = before[key]
        if (
            key == "review_input"
            and isinstance(value, dict)
            and isinstance(value.get("description"), float)
        ):
            assert isinstance(original, dict)
            assert isinstance(original.get("description"), float)
        else:
            assert value == original


def test_snapshot_rejects_non_mapping_with_safe_error() -> None:
    with pytest.raises(
        LLMRequestSchemaError,
        match="^LLM request schema construction failed$",
    ):
        build_risk_reviewer_payload_snapshot([])  # type: ignore[arg-type]


def test_snapshot_is_one_detached_immutable_serialization() -> None:
    original = full_risk_reviewer_payload()
    payload = SingleReadMapping(original)
    expected_serialized = json.dumps(
        original,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    snapshot = build_risk_reviewer_payload_snapshot(payload)
    review_input = original["review_input"]
    problem_analysis = original["problem_analysis"]
    alternatives = original["solution_alternatives"]
    assert isinstance(review_input, dict)
    assert isinstance(problem_analysis, dict)
    assert isinstance(alternatives, dict)
    review_input["description"] = "mutated"
    facts = problem_analysis["facts"]
    solution_values = alternatives["alternatives"]
    assert isinstance(facts, list)
    assert isinstance(solution_values, list)
    facts.clear()
    solution_values.clear()

    assert payload.iterations == 1
    assert snapshot.serialized_payload == expected_serialized
    assert snapshot.review_input.description == "Review a local migration."
    assert len(snapshot.problem_analysis.facts) == 1
    assert len(snapshot.solution_alternatives.alternatives) == 2


def test_failed_snapshot_does_not_mutate_nested_caller_values() -> None:
    payload = minimal_risk_reviewer_payload()
    payload["review_input"] = {"description": ""}
    before = deepcopy(payload)

    with pytest.raises(LLMRequestSchemaError):
        build_risk_reviewer_payload_snapshot(payload)

    assert payload == before


def test_snapshot_serialization_is_independent_of_mapping_insertion_order() -> None:
    payload = full_risk_reviewer_payload()
    reverse_key_payload = dict(reversed(tuple(payload.items())))

    first = build_risk_reviewer_payload_snapshot(payload)
    second = build_risk_reviewer_payload_snapshot(reverse_key_payload)

    assert first.serialized_payload == second.serialized_payload
    assert first.review_input == second.review_input
    assert first.problem_analysis == second.problem_analysis
    assert first.solution_alternatives == second.solution_alternatives


def review_input_bases(
    bases: tuple[AllowedRiskBasis, ...],
) -> tuple[AllowedRiskBasis, ...]:
    return tuple(
        basis
        for basis in bases
        if isinstance(basis.reference, ReviewInputBasisReference)
    )


def problem_analysis_bases(
    bases: tuple[AllowedRiskBasis, ...],
) -> tuple[AllowedRiskBasis, ...]:
    return tuple(
        basis
        for basis in bases
        if isinstance(basis.reference, ProblemAnalysisBasisReference)
    )


def solution_alternative_bases(
    bases: tuple[AllowedRiskBasis, ...],
) -> tuple[AllowedRiskBasis, ...]:
    return tuple(
        basis
        for basis in bases
        if isinstance(basis.reference, SolutionAlternativeBasisReference)
    )


def test_review_input_catalog_covers_exact_fields_in_fixed_order() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(full_risk_reviewer_payload())

    bases = review_input_bases(build_allowed_risk_bases(snapshot))

    assert [basis.reference.field.value for basis in bases] == [
        "description",
        "title",
        "objective",
        "constraints",
        "constraints",
        "context",
        "stated_facts",
    ]
    assert [basis.reference.value for basis in bases] == [
        "Review a local migration.",
        "Desktop migration",
        "Select a safe migration direction.",
        "Must work offline.",
        "Keep deployment simple.",
        "Devices use ARM64.",
        "The current client uses WPF.",
    ]
    assert [basis.target_key for basis in bases] == [
        ("REVIEW_INPUT", "description"),
        ("REVIEW_INPUT", "title"),
        ("REVIEW_INPUT", "objective"),
        ("REVIEW_INPUT", "constraints", "0"),
        ("REVIEW_INPUT", "constraints", "1"),
        ("REVIEW_INPUT", "context", "0"),
        ("REVIEW_INPUT", "stated_facts", "0"),
    ]
    assert [basis.as_wire_object() for basis in bases] == [
        {
            "source": "REVIEW_INPUT",
            "field": basis.reference.field.value,
            "value": basis.reference.value,
        }
        for basis in bases
    ]


def test_review_input_catalog_excludes_blank_and_owner_field_duplicates() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(
        duplicate_heavy_risk_reviewer_payload()
    )

    bases = review_input_bases(build_allowed_risk_bases(snapshot))

    assert [basis.reference.field.value for basis in bases] == [
        "description",
        "objective",
        "context",
        "stated_facts",
    ]
    assert [basis.reference.value for basis in bases] == [
        "Review a local migration.",
        "Select a safe migration direction.",
        "Devices use ARM64.",
        "The current client uses WPF.",
    ]
    assert not any(
        basis.reference.value in {"", "Repeated input."} for basis in bases
    )


def test_review_input_equal_text_in_different_fields_remains_resolvable() -> None:
    payload = minimal_risk_reviewer_payload()
    review_input = payload["review_input"]
    assert isinstance(review_input, dict)
    review_input.update(
        {
            "title": "Shared exact value.",
            "constraints": ["Shared exact value."],
            "context": ["Shared exact value."],
            "stated_facts": ["Shared exact value."],
        }
    )

    bases = review_input_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    shared = tuple(
        basis for basis in bases if basis.reference.value == "Shared exact value."
    )

    assert [basis.reference.field.value for basis in shared] == [
        "title",
        "constraints",
        "context",
        "stated_facts",
    ]
    assert len({basis.emitted_identity for basis in shared}) == 4


def test_review_input_catalog_preserves_non_blank_whitespace_exactly() -> None:
    payload = minimal_risk_reviewer_payload()
    review_input = payload["review_input"]
    assert isinstance(review_input, dict)
    review_input["constraints"] = ["  exact constraint  "]

    bases = review_input_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    constraint = next(
        basis
        for basis in bases
        if basis.reference.field.value == "constraints"
    )

    assert constraint.reference.value == "  exact constraint  "
    assert constraint.as_wire_object()["value"] == "  exact constraint  "


def test_problem_analysis_catalog_covers_all_kinds_in_fixed_order() -> None:
    payload = full_risk_reviewer_payload()
    problem_analysis = payload["problem_analysis"]
    assert isinstance(problem_analysis, dict)
    assumptions = problem_analysis["assumptions"]
    assert isinstance(assumptions, list)
    assumption = assumptions[0]
    assert isinstance(assumption, dict)
    assumption["id"] = None

    bases = problem_analysis_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )

    assert [basis.reference.kind for basis in bases] == [
        ProblemAnalysisFindingKind.FACT,
        ProblemAnalysisFindingKind.CONSTRAINT,
        ProblemAnalysisFindingKind.CONSTRAINT,
        ProblemAnalysisFindingKind.ASSUMPTION,
        ProblemAnalysisFindingKind.MISSING_INFORMATION,
        ProblemAnalysisFindingKind.UNCERTAINTY,
    ]
    assert [basis.reference.id for basis in bases] == [
        "FACT-001",
        "CON-001",
        "CON-002",
        None,
        "MISS-001",
        "UNC-001",
    ]
    assert [basis.target_key for basis in bases] == [
        ("PROBLEM_ANALYSIS", "FACT", "0"),
        ("PROBLEM_ANALYSIS", "CONSTRAINT", "0"),
        ("PROBLEM_ANALYSIS", "CONSTRAINT", "1"),
        ("PROBLEM_ANALYSIS", "ASSUMPTION", "0"),
        ("PROBLEM_ANALYSIS", "MISSING_INFORMATION", "0"),
        ("PROBLEM_ANALYSIS", "UNCERTAINTY", "0"),
    ]
    assert "id" not in bases[3].as_wire_object()
    assert bases[0].as_wire_object() == {
        "source": "PROBLEM_ANALYSIS",
        "kind": "FACT",
        "text": "The current client uses WPF.",
        "id": "FACT-001",
    }


def test_problem_analysis_idless_duplicate_is_excluded_but_id_pair_survives() -> None:
    payload = duplicate_heavy_risk_reviewer_payload()

    bases = problem_analysis_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    uncertainties = tuple(
        basis
        for basis in bases
        if basis.reference.kind is ProblemAnalysisFindingKind.UNCERTAINTY
    )

    assert len(uncertainties) == 1
    assert uncertainties[0].reference.id == "UNC-002"
    assert uncertainties[0].reference.text == "Repeated uncertainty."


def test_problem_analysis_id_bearing_equal_text_targets_remain_distinct() -> None:
    payload = minimal_risk_reviewer_payload()
    problem_analysis = payload["problem_analysis"]
    assert isinstance(problem_analysis, dict)
    problem_analysis["assumptions"] = [
        {"id": "ASM-001", "text": "Same identified assumption."},
        {"id": "ASM-002", "text": "Same identified assumption."},
    ]

    bases = problem_analysis_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    assumptions = tuple(
        basis
        for basis in bases
        if basis.reference.kind is ProblemAnalysisFindingKind.ASSUMPTION
    )

    assert [basis.reference.id for basis in assumptions] == ["ASM-001", "ASM-002"]
    assert len({basis.emitted_identity for basis in assumptions}) == 2
    assert len({basis.target_key for basis in assumptions}) == 2


def test_problem_analysis_equal_text_across_kinds_remains_distinct() -> None:
    payload = minimal_risk_reviewer_payload()
    problem_analysis = payload["problem_analysis"]
    assert isinstance(problem_analysis, dict)
    problem_analysis["constraints"] = [
        {"id": "CON-001", "text": "Shared cross-kind text."}
    ]
    problem_analysis["assumptions"] = [
        {"id": "ASM-001", "text": "Shared cross-kind text."}
    ]

    bases = problem_analysis_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    shared = tuple(
        basis
        for basis in bases
        if basis.reference.text == "Shared cross-kind text."
    )

    assert [basis.reference.kind for basis in shared] == [
        ProblemAnalysisFindingKind.CONSTRAINT,
        ProblemAnalysisFindingKind.ASSUMPTION,
    ]
    assert len({basis.emitted_identity for basis in shared}) == 2


def test_observed_problem_analysis_kind_id_text_cross_product_is_not_emitted() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(full_risk_reviewer_payload())
    bases = problem_analysis_bases(build_allowed_risk_bases(snapshot))
    invalid = ProblemAnalysisBasisReference.model_validate(
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ASSUMPTION",
            "text": "Must work offline.",
            "id": "CON-001",
        }
    )
    invalid_wire = invalid.model_dump(mode="json", exclude_none=True)

    assert invalid_wire not in [basis.as_wire_object() for basis in bases]
    assert all(
        not (
            basis.reference.kind is ProblemAnalysisFindingKind.ASSUMPTION
            and basis.reference.id == "CON-001"
        )
        for basis in bases
    )


def test_solution_alternative_catalog_covers_exact_characteristics_in_fixed_order() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(full_risk_reviewer_payload())

    bases = solution_alternative_bases(build_allowed_risk_bases(snapshot))

    assert [basis.reference.characteristic for basis in bases] == [
        SolutionAlternativeCharacteristicKind.DESCRIPTION,
        SolutionAlternativeCharacteristicKind.DESCRIPTION,
        SolutionAlternativeCharacteristicKind.ADVANTAGE,
        SolutionAlternativeCharacteristicKind.ADVANTAGE,
        SolutionAlternativeCharacteristicKind.DISADVANTAGE,
        SolutionAlternativeCharacteristicKind.DISADVANTAGE,
        SolutionAlternativeCharacteristicKind.ASSUMPTION,
        SolutionAlternativeCharacteristicKind.ASSUMPTION,
        SolutionAlternativeCharacteristicKind.IMPLEMENTATION_COMPLEXITY,
        SolutionAlternativeCharacteristicKind.IMPLEMENTATION_COMPLEXITY,
        SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT,
        SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT,
    ]
    assert [basis.reference.alternative_id for basis in bases] == [
        "ALT-001",
        "ALT-002",
    ] * 6
    assert [basis.reference.value for basis in bases[:10]] == [
        "Move WPF to .NET 8 incrementally.",
        "Rewrite the client with .NET MAUI.",
        "Lower delivery risk.",
        "Broadens platform options.",
        "Retains Windows coupling.",
        "Requires substantial rework.",
        "Required libraries support .NET 8.",
        "MAUI meets desktop requirements.",
        "MEDIUM",
        "HIGH",
    ]
    serialized_bases = json.dumps(
        [basis.as_wire_object() for basis in bases],
        ensure_ascii=False,
        sort_keys=True,
    )
    assert "Incremental migration" not in serialized_bases
    assert "Cross-platform rewrite" not in serialized_bases
    assert "Two viable approaches were identified." not in serialized_bases


def test_solution_alternative_catalog_excludes_owner_local_text_duplicates() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(
        duplicate_heavy_risk_reviewer_payload()
    )

    bases = solution_alternative_bases(build_allowed_risk_bases(snapshot))
    advantages = tuple(
        basis
        for basis in bases
        if basis.reference.characteristic
        is SolutionAlternativeCharacteristicKind.ADVANTAGE
    )

    assert len(advantages) == 1
    assert advantages[0].reference.alternative_id == "ALT-002"
    assert advantages[0].reference.value == "Repeated advantage."


def test_relevant_constraint_remains_exact_nested_value() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(full_risk_reviewer_payload())

    bases = solution_alternative_bases(build_allowed_risk_bases(snapshot))
    constraints = tuple(
        basis
        for basis in bases
        if basis.reference.characteristic
        is SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT
    )

    assert len(constraints) == 2
    assert all(isinstance(basis.reference.value, ConstraintReference) for basis in constraints)
    assert constraints[1].reference.value == ConstraintReference.model_validate(
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        }
    )
    assert constraints[1].as_wire_object() == {
        "source": "SOLUTION_ALTERNATIVE",
        "alternative_id": "ALT-002",
        "characteristic": "RELEVANT_CONSTRAINT",
        "value": {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        },
    }
    assert isinstance(constraints[1].as_wire_object()["value"], dict)


def test_relevant_constraint_duplicates_are_owner_local() -> None:
    payload = duplicate_heavy_risk_reviewer_payload()
    solution_alternatives = payload["solution_alternatives"]
    assert isinstance(solution_alternatives, dict)
    alternatives = solution_alternatives["alternatives"]
    assert isinstance(alternatives, list)
    second = alternatives[1]
    assert isinstance(second, dict)
    second["relevant_constraints"] = [
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "ID",
            "value": "CON-001",
        }
    ]

    bases = solution_alternative_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    constraints = tuple(
        basis
        for basis in bases
        if basis.reference.characteristic
        is SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT
    )

    assert len(constraints) == 1
    assert constraints[0].reference.alternative_id == "ALT-002"
    assert constraints[0].target_key == (
        "SOLUTION_ALTERNATIVE",
        "ALT-002",
        "RELEVANT_CONSTRAINT",
        "0",
    )


def test_equal_relevant_constraints_in_different_alternatives_remain_distinct() -> None:
    payload = full_risk_reviewer_payload()
    solution_alternatives = payload["solution_alternatives"]
    assert isinstance(solution_alternatives, dict)
    alternatives = solution_alternatives["alternatives"]
    assert isinstance(alternatives, list)
    shared = {
        "source": "PROBLEM_ANALYSIS",
        "kind": "ID",
        "value": "CON-001",
    }
    for alternative in alternatives:
        assert isinstance(alternative, dict)
        alternative["relevant_constraints"] = [shared]

    bases = solution_alternative_bases(
        build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    )
    constraints = tuple(
        basis
        for basis in bases
        if basis.reference.characteristic
        is SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT
    )

    assert [basis.reference.alternative_id for basis in constraints] == [
        "ALT-001",
        "ALT-002",
    ]
    assert len({basis.emitted_identity for basis in constraints}) == 2
    assert len({basis.target_key for basis in constraints}) == 2


def test_catalog_has_exact_global_target_order_and_canonical_emitted_identities() -> None:
    snapshot = build_risk_reviewer_payload_snapshot(full_risk_reviewer_payload())

    bases = build_allowed_risk_bases(snapshot)

    assert [basis.target_key for basis in bases] == [
        ("REVIEW_INPUT", "description"),
        ("REVIEW_INPUT", "title"),
        ("REVIEW_INPUT", "objective"),
        ("REVIEW_INPUT", "constraints", "0"),
        ("REVIEW_INPUT", "constraints", "1"),
        ("REVIEW_INPUT", "context", "0"),
        ("REVIEW_INPUT", "stated_facts", "0"),
        ("PROBLEM_ANALYSIS", "FACT", "0"),
        ("PROBLEM_ANALYSIS", "CONSTRAINT", "0"),
        ("PROBLEM_ANALYSIS", "CONSTRAINT", "1"),
        ("PROBLEM_ANALYSIS", "ASSUMPTION", "0"),
        ("PROBLEM_ANALYSIS", "MISSING_INFORMATION", "0"),
        ("PROBLEM_ANALYSIS", "UNCERTAINTY", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-001", "DESCRIPTION"),
        ("SOLUTION_ALTERNATIVE", "ALT-002", "DESCRIPTION"),
        ("SOLUTION_ALTERNATIVE", "ALT-001", "ADVANTAGE", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-002", "ADVANTAGE", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-001", "DISADVANTAGE", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-002", "DISADVANTAGE", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-001", "ASSUMPTION", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-002", "ASSUMPTION", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-001", "IMPLEMENTATION_COMPLEXITY"),
        ("SOLUTION_ALTERNATIVE", "ALT-002", "IMPLEMENTATION_COMPLEXITY"),
        ("SOLUTION_ALTERNATIVE", "ALT-001", "RELEVANT_CONSTRAINT", "0"),
        ("SOLUTION_ALTERNATIVE", "ALT-002", "RELEVANT_CONSTRAINT", "0"),
    ]
    assert all(
        basis.emitted_identity
        == json.dumps(
            basis.as_wire_object(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        for basis in bases
    )
    assert all(
        isinstance(component, str)
        for basis in bases
        for component in basis.target_key
    )


def test_catalog_is_independent_of_payload_mapping_insertion_order() -> None:
    def reverse_mappings(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: reverse_mappings(item)
                for key, item in reversed(tuple(value.items()))
            }
        if isinstance(value, list):
            return [reverse_mappings(item) for item in value]
        return value

    payload = full_risk_reviewer_payload()
    reordered = reverse_mappings(payload)
    assert isinstance(reordered, dict)

    first = build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(payload))
    second = build_allowed_risk_bases(build_risk_reviewer_payload_snapshot(reordered))

    assert [basis.as_wire_object() for basis in first] == [
        basis.as_wire_object() for basis in second
    ]
    assert [basis.target_key for basis in first] == [
        basis.target_key for basis in second
    ]
    assert [basis.emitted_identity for basis in first] == [
        basis.emitted_identity for basis in second
    ]


def test_basis_normalization_deduplicates_or_excludes_by_semantic_target() -> None:
    description_reference = ReviewInputBasisReference(
        field="description",
        value="Exact description.",
    )
    first = AllowedRiskBasis(
        reference=description_reference,
        target_key=("REVIEW_INPUT", "description"),
    )
    identical = AllowedRiskBasis(
        reference=description_reference,
        target_key=("REVIEW_INPUT", "description"),
    )
    ambiguous_reference = ReviewInputBasisReference(
        field="constraints",
        value="Ambiguous exact value.",
    )
    ambiguous_first = AllowedRiskBasis(
        reference=ambiguous_reference,
        target_key=("REVIEW_INPUT", "constraints", "0"),
    )
    ambiguous_second = AllowedRiskBasis(
        reference=ambiguous_reference,
        target_key=("REVIEW_INPUT", "constraints", "1"),
    )
    unrelated = AllowedRiskBasis(
        reference=ProblemAnalysisBasisReference(
            kind="UNCERTAINTY",
            text="Independent uncertainty.",
            id="UNC-001",
        ),
        target_key=("PROBLEM_ANALYSIS", "UNCERTAINTY", "0"),
    )

    normalized = normalize_allowed_risk_bases(
        (
            first,
            ambiguous_first,
            identical,
            unrelated,
            ambiguous_second,
        )
    )

    assert normalized == (first, unrelated)
    assert normalized[0] is first
    assert normalized[1] is unrelated


def test_empty_basis_normalization_is_valid() -> None:
    assert normalize_allowed_risk_bases(()) == ()
