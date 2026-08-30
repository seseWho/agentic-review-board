from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy

import pytest
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    build_critic_payload_snapshot,
)

from agentic_review_board.domain.analysis import ProblemAnalysis
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
