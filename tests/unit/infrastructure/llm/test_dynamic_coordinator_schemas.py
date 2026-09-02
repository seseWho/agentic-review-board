from __future__ import annotations

from typing import Any, cast

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.infrastructure.llm.config import LLMRole
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    CoordinatorPayloadSnapshot,
    build_allowed_coordinator_references,
    build_coordinator_payload_snapshot,
    build_dynamic_coordinator_schema,
    build_dynamic_request_context,
)
from agentic_review_board.infrastructure.llm.prompts import get_role_prompt_definition


def as_object(value: object) -> dict[str, Any]:
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def as_array(value: object) -> list[Any]:
    assert isinstance(value, list)
    return value


def coordinator_payload() -> dict[str, object]:
    review_input = ReviewInput(description="Review a local migration.")
    problem_analysis = ProblemAnalysis.model_validate(
        {
            "objective": "Select a safe migration.",
            "facts": [],
            "constraints": [],
            "assumptions": [],
            "missing_information": [],
            "uncertainties": [
                {"id": "UNC-001", "text": "Offline integrity remains uncertain."}
            ],
        }
    )
    solution_alternatives = SolutionAlternatives.model_validate(
        {
            "alternatives": [
                {
                    "id": "ALT-001",
                    "name": "Incremental",
                    "description": "Migrate incrementally.",
                    "advantages": ["Lower delivery risk."],
                    "disadvantages": ["Retains coupling."],
                    "assumptions": ["Required libraries remain supported."],
                    "implementation_complexity": "MEDIUM",
                    "relevant_constraints": [],
                },
                {
                    "id": "ALT-002",
                    "name": "Rewrite",
                    "description": "Rewrite the client.",
                    "advantages": ["Modern architecture."],
                    "disadvantages": ["Higher delivery risk."],
                    "assumptions": ["The team can absorb the rewrite."],
                    "implementation_complexity": "HIGH",
                    "relevant_constraints": [],
                },
            ]
        }
    )
    risk_assessment = RiskAssessment.model_validate(
        {"risks": [], "overall_observations": []}
    )
    target = {
        "source": "PROBLEM_ANALYSIS",
        "kind": "UNCERTAINTY",
        "item_id": "UNC-001",
        "value": "Offline integrity remains uncertain.",
    }
    critical_review = CriticalReview.model_validate(
        {
            "criticisms": [
                {
                    "id": "CRIT-001",
                    "target_type": "ANALYSIS",
                    "target_reference": target,
                    "basis_references": [],
                    "issue": "Offline integrity needs validation.",
                    "importance": "HIGH",
                    "rationale": "The recommendation depends on it.",
                }
            ],
            "unresolved_issues": [
                {
                    "id": "ISSUE-001",
                    "issue": "Offline integrity remains unverified.",
                    "rationale": "No measurement is available.",
                    "basis_references": [target],
                }
            ],
        }
    )
    return {
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
        "solution_alternatives": solution_alternatives.model_dump(mode="json"),
        "risk_assessment": risk_assessment.model_dump(mode="json"),
        "critical_review": critical_review.model_dump(mode="json"),
    }


def exact_branch_value(branch: object) -> dict[str, object]:
    properties = as_object(as_object(branch)["properties"])
    return {
        key: as_object(value)["const"]
        for key, value in properties.items()
        if "const" in as_object(value)
    }


def test_coordinator_snapshot_owns_exact_five_artifact_payload() -> None:
    payload = coordinator_payload()

    snapshot = build_coordinator_payload_snapshot(payload)

    assert isinstance(snapshot, CoordinatorPayloadSnapshot)
    assert snapshot.critical_review.criticisms[0].id == "CRIT-001"
    assert snapshot.problem_analysis.uncertainties[0].text == (
        "Offline integrity remains uncertain."
    )


def test_coordinator_reference_catalog_contains_only_exact_resolvable_values() -> None:
    references = build_allowed_coordinator_references(
        build_coordinator_payload_snapshot(coordinator_payload())
    )
    wire_values = [reference.as_wire_object() for reference in references]

    assert {
        "source": "PROBLEM_ANALYSIS",
        "kind": "UNCERTAINTY",
        "value": "Offline integrity remains uncertain.",
        "item_id": "UNC-001",
    } in wire_values
    assert {
        "source": "CRITICAL_REVIEW",
        "kind": "UNRESOLVED_ISSUE",
        "item_id": "ISSUE-001",
        "value": "Offline integrity remains unverified.",
    } in wire_values
    assert all("Offline integrity is uncertain." not in value.values() for value in wire_values)


def test_dynamic_coordinator_schema_excludes_non_criticism_dispositions() -> None:
    snapshot = build_coordinator_payload_snapshot(coordinator_payload())

    schema = build_dynamic_coordinator_schema(snapshot)
    definitions = as_object(schema["$defs"])
    disposition = as_object(definitions["CriticismDisposition"])
    branches = as_array(disposition["oneOf"])
    wire_values = [exact_branch_value(branch) for branch in branches]

    assert {value["criticism_id"] for value in wire_values} == {"CRIT-001"}
    assert {value["outcome"] for value in wire_values} == {"REFLECTED", "DISMISSED"}
    assert all(value["criticism_id"] != "ISSUE-001" for value in wire_values)
    dispositions = as_object(as_object(schema["properties"])["criticism_dispositions"])
    assert dispositions["minItems"] == 1
    assert dispositions["maxItems"] == 1
    assert "uniqueItems" not in str(schema)


def test_dynamic_coordinator_schema_correlates_alternative_and_validation_status() -> None:
    schema = build_dynamic_coordinator_schema(
        build_coordinator_payload_snapshot(coordinator_payload())
    )
    definitions = as_object(schema["$defs"])
    ranked = as_object(definitions["RankedAlternative"])
    branches = as_array(ranked["oneOf"])
    pairs = {
        (
            exact_branch_value(branch)["alternative_id"],
            exact_branch_value(branch)["validation_status"],
        )
        for branch in branches
    }

    assert pairs == {("ALT-001", "PROPOSED"), ("ALT-002", "PROPOSED")}
    assert all("validation_status" in as_object(branch)["required"] for branch in branches)


def test_coordinator_request_context_uses_dynamic_schema_and_detached_payload() -> None:
    payload = coordinator_payload()
    definition = get_role_prompt_definition(LLMRole.COORDINATOR.value)

    context = build_dynamic_request_context(definition=definition, payload=payload)

    assert context is not None
    assert context.output_schema.new_document() == build_dynamic_coordinator_schema(
        build_coordinator_payload_snapshot(payload)
    )
    assert context.serialized_payload == build_coordinator_payload_snapshot(
        payload
    ).serialized_payload
