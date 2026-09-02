from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.infrastructure.llm.config import LLMRole
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    AnalystPayloadSnapshot,
    build_analyst_payload_snapshot,
    build_dynamic_analyst_schema,
    build_dynamic_request_context,
    narrow_analyst_schema,
)
from agentic_review_board.infrastructure.llm.errors import LLMRequestSchemaError
from agentic_review_board.infrastructure.llm.prompts import get_role_prompt_definition


def as_object(value: object) -> dict[str, Any]:
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def analyst_payload() -> dict[str, object]:
    return ReviewInput(
        title="Depot charging",
        description="Review a charging expansion.",
        objective="Select a staged charging strategy.",
        constraints=(
            "Keep compatible existing chargers.",
            "Do not exceed the 8 MW import limit.",
        ),
        context=("The grid-upgrade date is not committed.",),
        stated_facts=(
            "The import limit is 8 MW.",
            "The first buses arrive in ten months.",
        ),
    ).model_dump(mode="json")


def test_analyst_snapshot_is_exact_detached_and_typed() -> None:
    payload = analyst_payload()

    snapshot = build_analyst_payload_snapshot(payload)

    assert isinstance(snapshot, AnalystPayloadSnapshot)
    assert snapshot.review_input == ReviewInput.model_validate(payload)
    payload["constraints"] = []
    assert snapshot.review_input.constraints == (
        "Keep compatible existing chargers.",
        "Do not exceed the 8 MW import limit.",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"description": "Missing the other exact fields."},
        {**analyst_payload(), "unexpected": "field"},
    ],
)
def test_analyst_snapshot_rejects_non_exact_payload_shape(
    payload: dict[str, object],
) -> None:
    with pytest.raises(LLMRequestSchemaError):
        build_analyst_payload_snapshot(payload)


def test_dynamic_analyst_schema_preserves_authoritative_input_exactly_once() -> None:
    snapshot = build_analyst_payload_snapshot(analyst_payload())

    schema = build_dynamic_analyst_schema(snapshot)
    properties = as_object(schema["properties"])

    assert properties["objective"] == {
        "const": "Select a staged charging strategy."
    }
    assert properties["facts"] == {
        "const": [
            {
                "text": "The import limit is 8 MW.",
                "source_ref": "stated_facts",
                "id": "FACT-001",
            },
            {
                "text": "The first buses arrive in ten months.",
                "source_ref": "stated_facts",
                "id": "FACT-002",
            },
            {
                "text": "The grid-upgrade date is not committed.",
                "source_ref": "context",
                "id": "FACT-003",
            },
        ]
    }
    assert properties["constraints"] == {
        "const": [
            {"text": "Keep compatible existing chargers.", "id": "CON-001"},
            {"text": "Do not exceed the 8 MW import limit.", "id": "CON-002"},
        ]
    }


def test_dynamic_analyst_schema_uses_empty_constants_for_empty_input_collections() -> None:
    snapshot = build_analyst_payload_snapshot(
        ReviewInput(description="Analyze an underspecified decision.").model_dump(mode="json")
    )

    schema = build_dynamic_analyst_schema(snapshot)
    properties = as_object(schema["properties"])

    assert properties["facts"] == {"const": []}
    assert properties["constraints"] == {"const": []}
    assert properties["objective"] != {"const": None}


def test_analyst_narrowing_owns_documents_and_rejects_invalid_base_shape() -> None:
    review_input = ReviewInput.model_validate(analyst_payload())
    base = ProblemAnalysis.model_json_schema()
    before = deepcopy(base)

    first = narrow_analyst_schema(base, review_input)
    as_object(first["properties"])["facts"] = {"mutated": True}
    second = narrow_analyst_schema(base, review_input)

    assert base == before
    assert as_object(second["properties"])["facts"] != {"mutated": True}

    invalid = ProblemAnalysis.model_json_schema()
    invalid.pop("properties")
    with pytest.raises(LLMRequestSchemaError):
        narrow_analyst_schema(invalid, review_input)


def test_analyst_dynamic_context_is_deterministic_and_preserves_one_snapshot() -> None:
    definition = get_role_prompt_definition(LLMRole.ANALYST.value)
    payload = analyst_payload()

    first = build_dynamic_request_context(definition=definition, payload=payload)
    second = build_dynamic_request_context(
        definition=definition,
        payload=dict(reversed(tuple(payload.items()))),
    )

    assert first is not None
    assert second is not None
    assert first.serialized_payload == second.serialized_payload
    assert first.output_schema.serialized == second.output_schema.serialized
