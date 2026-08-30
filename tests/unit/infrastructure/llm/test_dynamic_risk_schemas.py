from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy

import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    RiskReviewerPayloadSnapshot,
    build_risk_reviewer_payload_snapshot,
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
