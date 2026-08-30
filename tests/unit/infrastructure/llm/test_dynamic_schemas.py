from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy

import pytest
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    AllowedCriticReference,
    build_allowed_critic_references,
    build_critic_payload_snapshot,
)

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticReferenceKind, CriticReferenceSource
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.infrastructure.llm.errors import LLMRequestSchemaError

CRITIC_PAYLOAD_KEYS = {
    "review_input",
    "problem_analysis",
    "solution_alternatives",
    "risk_assessment",
}


def minimal_critic_payload() -> dict[str, object]:
    review_input = ReviewInput(description="Review a local migration.")
    problem_analysis = ProblemAnalysis.model_validate(
        {
            "objective": "Assess migration feasibility.",
            "facts": [],
            "constraints": [],
            "assumptions": [],
            "missing_information": [],
            "uncertainties": [],
        }
    )
    solution_alternatives = SolutionAlternatives.model_validate(
        {
            "alternatives": [],
            "generation_notes": {
                "explanation": "No viable alternative can yet be grounded.",
                "blocking_missing_information": [],
                "blocking_uncertainties": [],
            },
        }
    )
    risk_assessment = RiskAssessment.model_validate(
        {"risks": [], "overall_observations": []}
    )
    return {
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
        "solution_alternatives": solution_alternatives.model_dump(mode="json"),
        "risk_assessment": risk_assessment.model_dump(mode="json"),
    }


def full_critic_payload() -> dict[str, object]:
    review_input = ReviewInput(
        description="Review a local migration.",
        title="Desktop migration",
        objective="Select a safe migration direction.",
        constraints=("Must work offline.",),
        context=("Devices use ARM64.",),
        stated_facts=("The current client uses WPF.",),
    )
    problem_analysis = ProblemAnalysis.model_validate(
        {
            "objective": "Assess migration feasibility.",
            "facts": [
                {
                    "id": "FACT-001",
                    "text": "The current client uses WPF.",
                    "source_ref": "stated_facts",
                }
            ],
            "constraints": [{"id": "CON-001", "text": "Must work offline."}],
            "assumptions": [{"id": "ASM-001", "text": "Drivers support ARM64."}],
            "missing_information": [
                {"id": "MISS-001", "text": "Measured ARM64 memory usage."}
            ],
            "uncertainties": [
                {"id": "UNC-001", "text": "ARM64 performance degradation."}
            ],
        }
    )
    solution_alternatives = SolutionAlternatives.model_validate(
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
                        {"source": "REVIEW_INPUT", "kind": "TEXT", "value": "Must work offline."}
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
                        {"source": "PROBLEM_ANALYSIS", "kind": "ID", "value": "CON-001"}
                    ],
                },
            ],
            "generation_notes": {
                "explanation": "Two viable approaches were identified.",
                "blocking_missing_information": [
                    {"id": "MISS-001", "text": "Measured ARM64 memory usage."}
                ],
                "blocking_uncertainties": [
                    {"id": "UNC-001", "text": "ARM64 performance degradation."}
                ],
            },
        }
    )
    risk_assessment = RiskAssessment.model_validate(
        {
            "risks": [
                {
                    "id": "RISK-001",
                    "category": "PERFORMANCE",
                    "description": "ARM64 performance may be insufficient.",
                    "affected_scope": {"kind": "ALTERNATIVES", "alternative_ids": ["ALT-001"]},
                    "severity": "HIGH",
                    "basis": [
                        {
                            "source": "PROBLEM_ANALYSIS",
                            "kind": "UNCERTAINTY",
                            "id": "UNC-001",
                            "text": "ARM64 performance degradation.",
                        }
                    ],
                    "mitigation": "Measure representative workloads.",
                    "residual_uncertainty": "Production workload variance remains.",
                }
            ],
            "overall_observations": ["Performance evidence is incomplete."],
        }
    )
    return {
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
        "solution_alternatives": solution_alternatives.model_dump(mode="json"),
        "risk_assessment": risk_assessment.model_dump(mode="json"),
    }


class SingleReadMapping(Mapping[str, object]):
    def __init__(self, values: dict[str, object]) -> None:
        self._values = values
        self.iterations = 0

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("Critic payload mapping was read more than once")
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


@pytest.mark.parametrize("payload_factory", [minimal_critic_payload, full_critic_payload])
def test_snapshot_accepts_exact_four_artifact_payload(payload_factory: object) -> None:
    assert callable(payload_factory)
    payload = payload_factory()

    snapshot = build_critic_payload_snapshot(payload)

    assert set(payload) == CRITIC_PAYLOAD_KEYS
    assert json.loads(snapshot.serialized_payload) == payload
    assert snapshot.review_input == ReviewInput.model_validate(payload["review_input"])
    assert snapshot.problem_analysis == ProblemAnalysis.model_validate(
        payload["problem_analysis"]
    )
    assert snapshot.solution_alternatives == SolutionAlternatives.model_validate(
        payload["solution_alternatives"]
    )
    assert snapshot.risk_assessment == RiskAssessment.model_validate(
        payload["risk_assessment"]
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.pop("risk_assessment"),
        lambda payload: payload.update({"unexpected": {}}),
        lambda payload: payload.update({"review_input": []}),
        lambda payload: payload.update({"problem_analysis": {"objective": "incomplete"}}),
        lambda payload: payload.update({"risk_assessment": {"risks": float("nan")}}),
    ],
)
def test_snapshot_rejects_invalid_critic_payload_with_safe_error(mutate: object) -> None:
    assert callable(mutate)
    payload = minimal_critic_payload()
    mutate(payload)
    original = deepcopy(payload)

    with pytest.raises(LLMRequestSchemaError, match="^LLM request schema construction failed$"):
        build_critic_payload_snapshot(payload)

    assert payload.keys() == original.keys()
    for key in payload:
        if key == "risk_assessment" and isinstance(payload[key], dict):
            continue
        assert payload[key] == original[key]


def test_snapshot_rejects_non_mapping_with_safe_error() -> None:
    with pytest.raises(LLMRequestSchemaError, match="^LLM request schema construction failed$"):
        build_critic_payload_snapshot([])  # type: ignore[arg-type]


def test_snapshot_is_one_detached_immutable_serialization() -> None:
    original = full_critic_payload()
    payload = SingleReadMapping(original)
    expected_serialized = json.dumps(
        original,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    snapshot = build_critic_payload_snapshot(payload)
    original["review_input"]["description"] = "mutated"  # type: ignore[index]
    original["problem_analysis"]["facts"].clear()  # type: ignore[index,union-attr]

    assert payload.iterations == 1
    assert snapshot.serialized_payload == expected_serialized
    assert snapshot.review_input.description == "Review a local migration."
    assert len(snapshot.problem_analysis.facts) == 1


def test_failed_snapshot_does_not_mutate_nested_caller_values() -> None:
    payload = minimal_critic_payload()
    payload["review_input"] = {"description": ""}
    before = deepcopy(payload)

    with pytest.raises(LLMRequestSchemaError):
        build_critic_payload_snapshot(payload)

    assert payload == before


def reference_by_kind(
    references: tuple[AllowedCriticReference, ...],
    kind: CriticReferenceKind,
) -> tuple[AllowedCriticReference, ...]:
    return tuple(reference for reference in references if reference.kind is kind)


def test_review_input_catalog_covers_exact_value_only_targets() -> None:
    references = build_allowed_critic_references(
        build_critic_payload_snapshot(full_critic_payload())
    )
    review_references = tuple(
        reference
        for reference in references
        if reference.source is CriticReferenceSource.REVIEW_INPUT
    )

    assert [reference.kind for reference in review_references] == [
        CriticReferenceKind.DESCRIPTION,
        CriticReferenceKind.TITLE,
        CriticReferenceKind.REVIEW_OBJECTIVE,
        CriticReferenceKind.REVIEW_CONSTRAINT,
        CriticReferenceKind.CONTEXT,
        CriticReferenceKind.STATED_FACT,
    ]
    assert [reference.value for reference in review_references] == [
        "Review a local migration.",
        "Desktop migration",
        "Select a safe migration direction.",
        "Must work offline.",
        "Devices use ARM64.",
        "The current client uses WPF.",
    ]
    assert all(reference.item_id is None for reference in review_references)
    assert [reference.target_key for reference in review_references[3:]] == [
        ("REVIEW_INPUT", "REVIEW_CONSTRAINT", "0"),
        ("REVIEW_INPUT", "CONTEXT", "0"),
        ("REVIEW_INPUT", "STATED_FACT", "0"),
    ]


def test_problem_analysis_catalog_covers_findings_with_actual_optional_ids() -> None:
    payload = full_critic_payload()
    payload["problem_analysis"]["assumptions"][0]["id"] = None  # type: ignore[index]

    references = build_allowed_critic_references(build_critic_payload_snapshot(payload))
    problem_references = tuple(
        reference
        for reference in references
        if reference.source is CriticReferenceSource.PROBLEM_ANALYSIS
    )

    assert [reference.kind for reference in problem_references] == [
        CriticReferenceKind.PROBLEM_OBJECTIVE,
        CriticReferenceKind.PROBLEM_FACT,
        CriticReferenceKind.PROBLEM_CONSTRAINT,
        CriticReferenceKind.PROBLEM_ASSUMPTION,
        CriticReferenceKind.MISSING_INFORMATION,
        CriticReferenceKind.UNCERTAINTY,
    ]
    assert [reference.item_id for reference in problem_references] == [
        None,
        "FACT-001",
        "CON-001",
        None,
        "MISS-001",
        "UNC-001",
    ]
    assert [reference.target_key for reference in problem_references] == [
        ("PROBLEM_ANALYSIS", "PROBLEM_OBJECTIVE"),
        ("PROBLEM_ANALYSIS", "PROBLEM_FACT", "0"),
        ("PROBLEM_ANALYSIS", "PROBLEM_CONSTRAINT", "0"),
        ("PROBLEM_ANALYSIS", "PROBLEM_ASSUMPTION", "0"),
        ("PROBLEM_ANALYSIS", "MISSING_INFORMATION", "0"),
        ("PROBLEM_ANALYSIS", "UNCERTAINTY", "0"),
    ]


def test_solution_catalog_covers_canonical_alternatives_and_generation_notes() -> None:
    references = build_allowed_critic_references(
        build_critic_payload_snapshot(full_critic_payload())
    )
    solution_references = tuple(
        reference
        for reference in references
        if reference.source is CriticReferenceSource.SOLUTION_ALTERNATIVES
    )

    assert [reference.kind for reference in solution_references] == [
        CriticReferenceKind.ALTERNATIVE,
        CriticReferenceKind.ALTERNATIVE,
        CriticReferenceKind.ALTERNATIVE_NAME,
        CriticReferenceKind.ALTERNATIVE_NAME,
        CriticReferenceKind.ALTERNATIVE_DESCRIPTION,
        CriticReferenceKind.ALTERNATIVE_DESCRIPTION,
        CriticReferenceKind.ADVANTAGE,
        CriticReferenceKind.ADVANTAGE,
        CriticReferenceKind.DISADVANTAGE,
        CriticReferenceKind.DISADVANTAGE,
        CriticReferenceKind.ALTERNATIVE_ASSUMPTION,
        CriticReferenceKind.ALTERNATIVE_ASSUMPTION,
        CriticReferenceKind.IMPLEMENTATION_COMPLEXITY,
        CriticReferenceKind.IMPLEMENTATION_COMPLEXITY,
        CriticReferenceKind.GENERATION_EXPLANATION,
        CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
        CriticReferenceKind.BLOCKING_UNCERTAINTY,
    ]
    alternative_references = reference_by_kind(
        solution_references, CriticReferenceKind.ALTERNATIVE
    )
    assert [(reference.item_id, reference.value) for reference in alternative_references] == [
        ("ALT-001", "Incremental migration"),
        ("ALT-002", "Cross-platform rewrite"),
    ]
    assert [reference.visible_value for reference in alternative_references] == [
        "Incremental migration",
        "Cross-platform rewrite",
    ]
    assert [
        (reference.kind, reference.item_id, reference.value)
        for reference in solution_references[-3:]
    ] == [
        (
            CriticReferenceKind.GENERATION_EXPLANATION,
            None,
            "Two viable approaches were identified.",
        ),
        (
            CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
            "MISS-001",
            "Measured ARM64 memory usage.",
        ),
        (
            CriticReferenceKind.BLOCKING_UNCERTAINTY,
            "UNC-001",
            "ARM64 performance degradation.",
        ),
    ]


def test_solution_catalog_handles_zero_alternatives_and_local_ambiguity() -> None:
    zero_references = build_allowed_critic_references(
        build_critic_payload_snapshot(minimal_critic_payload())
    )
    zero_solution_references = tuple(
        reference
        for reference in zero_references
        if reference.source is CriticReferenceSource.SOLUTION_ALTERNATIVES
    )
    assert [(reference.kind, reference.value) for reference in zero_solution_references] == [
        (
            CriticReferenceKind.GENERATION_EXPLANATION,
            "No viable alternative can yet be grounded.",
        )
    ]

    payload = full_critic_payload()
    alternatives = payload["solution_alternatives"]["alternatives"]  # type: ignore[index]
    alternatives[0]["assumptions"] = []  # type: ignore[index]
    alternatives[0]["advantages"] = ["Repeated.", "Repeated."]  # type: ignore[index]
    alternatives[1]["advantages"] = ["Repeated."]  # type: ignore[index]
    references = build_allowed_critic_references(build_critic_payload_snapshot(payload))
    advantages = reference_by_kind(references, CriticReferenceKind.ADVANTAGE)

    assert [
        (reference.item_id, reference.value, reference.target_key)
        for reference in advantages
    ] == [
        (
            "ALT-002",
            "Repeated.",
            ("SOLUTION_ALTERNATIVES", "ADVANTAGE", "ALT-002", "0"),
        )
    ]
    assumptions = reference_by_kind(references, CriticReferenceKind.ALTERNATIVE_ASSUMPTION)
    assert [(reference.item_id, reference.value) for reference in assumptions] == [
        ("ALT-002", "MAUI meets desktop requirements.")
    ]


def test_risk_catalog_covers_canonical_and_optional_risk_fields() -> None:
    references = build_allowed_critic_references(
        build_critic_payload_snapshot(full_critic_payload())
    )
    risk_references = tuple(
        reference
        for reference in references
        if reference.source is CriticReferenceSource.RISK_ASSESSMENT
    )

    assert [reference.kind for reference in risk_references] == [
        CriticReferenceKind.RISK,
        CriticReferenceKind.RISK_CATEGORY,
        CriticReferenceKind.RISK_DESCRIPTION,
        CriticReferenceKind.RISK_SEVERITY,
        CriticReferenceKind.MITIGATION,
        CriticReferenceKind.RESIDUAL_UNCERTAINTY,
        CriticReferenceKind.OVERALL_OBSERVATION,
    ]
    assert (risk_references[0].item_id, risk_references[0].value) == (
        "RISK-001",
        "ARM64 performance may be insufficient.",
    )
    assert risk_references[0].visible_value == "ARM64 performance may be insufficient."

    payload = full_critic_payload()
    payload["risk_assessment"]["risks"][0]["residual_uncertainty"] = None  # type: ignore[index]
    without_optional = build_allowed_critic_references(
        build_critic_payload_snapshot(payload)
    )
    assert not reference_by_kind(
        without_optional, CriticReferenceKind.RESIDUAL_UNCERTAINTY
    )
