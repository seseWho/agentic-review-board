from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.infrastructure.llm.config import LLMRole
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    SolutionArchitectPayloadSnapshot,
    build_allowed_solution_blocker_references,
    build_allowed_solution_constraint_references,
    build_dynamic_request_context,
    build_dynamic_solution_architect_schema,
    build_solution_architect_payload_snapshot,
    narrow_solution_architect_schema,
)
from agentic_review_board.infrastructure.llm.errors import LLMRequestSchemaError
from agentic_review_board.infrastructure.llm.prompts import get_role_prompt_definition


def as_object(value: object) -> dict[str, Any]:
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def as_array(value: object) -> list[Any]:
    assert isinstance(value, list)
    return value


def branch_wire_object(branch: object) -> dict[str, object]:
    properties = as_object(as_object(branch)["properties"])
    return {name: as_object(value)["const"] for name, value in properties.items()}


def solution_payload() -> dict[str, object]:
    review_input = ReviewInput(
        description="Review a governed support assistant.",
        objective="Choose an implementation approach.",
        constraints=("A human must approve every response.",),
    )
    problem_analysis = ProblemAnalysis.model_validate(
        {
            "objective": "Choose an implementation approach.",
            "facts": [],
            "constraints": [
                {"id": "CON-001", "text": "A human must approve every response."},
                {"id": "CON-002", "text": "Every policy claim requires a source."},
            ],
            "assumptions": [],
            "missing_information": [
                {
                    "id": "MISS-001",
                    "text": "No accepted evaluation benchmark exists.",
                }
            ],
            "uncertainties": [
                {
                    "id": "UNC-001",
                    "text": "The knowledge estate contains outdated material.",
                }
            ],
        }
    )
    return {
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
    }


def test_solution_snapshot_is_exact_detached_and_typed() -> None:
    payload = solution_payload()

    snapshot = build_solution_architect_payload_snapshot(payload)

    assert isinstance(snapshot, SolutionArchitectPayloadSnapshot)
    assert snapshot.review_input == ReviewInput.model_validate(payload["review_input"])
    assert snapshot.problem_analysis == ProblemAnalysis.model_validate(
        payload["problem_analysis"]
    )
    payload.clear()
    assert snapshot.problem_analysis.constraints


def test_solution_constraint_catalog_contains_only_resolvable_exact_references() -> None:
    snapshot = build_solution_architect_payload_snapshot(solution_payload())

    references = build_allowed_solution_constraint_references(snapshot)
    emitted = [reference.model_dump(mode="json") for reference in references]

    assert emitted == [
        {
            "source": "REVIEW_INPUT",
            "kind": "TEXT",
            "value": "A human must approve every response.",
        },
        {"source": "PROBLEM_ANALYSIS", "kind": "ID", "value": "CON-001"},
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "TEXT",
            "value": "A human must approve every response.",
        },
        {"source": "PROBLEM_ANALYSIS", "kind": "ID", "value": "CON-002"},
        {
            "source": "PROBLEM_ANALYSIS",
            "kind": "TEXT",
            "value": "Every policy claim requires a source.",
        },
    ]


def test_solution_blocker_catalogs_remain_classification_specific() -> None:
    snapshot = build_solution_architect_payload_snapshot(solution_payload())

    schema = build_dynamic_solution_architect_schema(snapshot)
    definitions = as_object(schema["$defs"])
    notes = as_object(definitions["GenerationNotes"])
    properties = as_object(notes["properties"])
    missing = as_object(properties["blocking_missing_information"])
    uncertainties = as_object(properties["blocking_uncertainties"])
    missing_branches = as_array(as_object(missing["items"])["oneOf"])
    uncertainty_branches = as_array(as_object(uncertainties["items"])["oneOf"])

    assert [branch_wire_object(branch) for branch in missing_branches] == [
        {"text": "No accepted evaluation benchmark exists.", "id": "MISS-001"}
    ]
    assert [branch_wire_object(branch) for branch in uncertainty_branches] == [
        {
            "text": "The knowledge estate contains outdated material.",
            "id": "UNC-001",
        }
    ]
    assert {
        "text": "The knowledge estate contains outdated material.",
        "id": "MISS-001",
    } not in [branch_wire_object(branch) for branch in missing_branches]


def test_solution_schema_uses_exact_constraint_branches() -> None:
    snapshot = build_solution_architect_payload_snapshot(solution_payload())
    expected = [
        reference.model_dump(mode="json")
        for reference in build_allowed_solution_constraint_references(snapshot)
    ]

    schema = build_dynamic_solution_architect_schema(snapshot)
    definitions = as_object(schema["$defs"])
    reference_definition = as_object(definitions["ConstraintReference"])

    assert [
        branch_wire_object(branch)
        for branch in as_array(reference_definition["oneOf"])
    ] == expected


def test_solution_schema_requires_proposed_validation_status() -> None:
    schema = build_dynamic_solution_architect_schema(
        build_solution_architect_payload_snapshot(solution_payload())
    )
    definitions = as_object(schema["$defs"])
    alternative = as_object(definitions["SolutionAlternative"])
    properties = as_object(alternative["properties"])

    assert properties["validation_status"] == {"const": "PROPOSED"}
    assert "validation_status" in alternative["required"]


def test_solution_schema_closes_empty_reference_collections() -> None:
    review_input = ReviewInput(description="Review an underspecified choice.")
    problem_analysis = ProblemAnalysis(
        objective="Identify viable approaches.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )
    snapshot = build_solution_architect_payload_snapshot(
        {
            "review_input": review_input.model_dump(mode="json"),
            "problem_analysis": problem_analysis.model_dump(mode="json"),
        }
    )

    schema = build_dynamic_solution_architect_schema(snapshot)
    definitions = as_object(schema["$defs"])
    alternative = as_object(definitions["SolutionAlternative"])
    notes = as_object(definitions["GenerationNotes"])

    assert as_object(alternative["properties"])["relevant_constraints"] == {
        "const": []
    }
    assert as_object(notes["properties"])["blocking_missing_information"] == {
        "const": []
    }
    assert as_object(notes["properties"])["blocking_uncertainties"] == {"const": []}


def test_solution_narrowing_owns_documents_and_rejects_invalid_base_shape() -> None:
    snapshot = build_solution_architect_payload_snapshot(solution_payload())
    constraints = build_allowed_solution_constraint_references(snapshot)
    missing = build_allowed_solution_blocker_references(
        snapshot.problem_analysis.missing_information
    )
    uncertainties = build_allowed_solution_blocker_references(
        snapshot.problem_analysis.uncertainties
    )
    base = SolutionAlternatives.model_json_schema()
    before = deepcopy(base)

    first = narrow_solution_architect_schema(base, constraints, missing, uncertainties)
    as_object(first["$defs"])["ConstraintReference"] = {"mutated": True}
    second = narrow_solution_architect_schema(base, constraints, missing, uncertainties)

    assert base == before
    assert as_object(second["$defs"])["ConstraintReference"] != {"mutated": True}

    invalid = SolutionAlternatives.model_json_schema()
    as_object(invalid["$defs"]).pop("GenerationNotes")
    with pytest.raises(LLMRequestSchemaError):
        narrow_solution_architect_schema(invalid, constraints, missing, uncertainties)


def test_solution_dynamic_context_is_deterministic() -> None:
    definition = get_role_prompt_definition(LLMRole.SOLUTION_ARCHITECT.value)
    payload = solution_payload()

    first = build_dynamic_request_context(definition=definition, payload=payload)
    second = build_dynamic_request_context(
        definition=definition,
        payload=dict(reversed(tuple(payload.items()))),
    )

    assert first is not None
    assert second is not None
    assert first.serialized_payload == second.serialized_payload
    assert first.output_schema.serialized == second.output_schema.serialized
