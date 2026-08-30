from __future__ import annotations

import os

import pytest

from agentic_review_board.infrastructure.llm.config import (
    load_llm_runtime_config,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.errors import LLMAdapterError
from agentic_review_board.infrastructure.llm.http_client import _create_http_client
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)
from agentic_review_board.infrastructure.llm.smoke import verify_selected_profiles


def minimal_critic_payload() -> dict[str, object]:
    return {
        "review_input": {
            "description": "Check Slice 7.1 dynamic Critic schema compatibility.",
            "title": None,
            "objective": None,
            "constraints": [],
            "context": [],
            "stated_facts": [],
        },
        "problem_analysis": {
            "objective": "Check dynamic schema compatibility.",
            "facts": [],
            "constraints": [],
            "assumptions": [],
            "missing_information": [],
            "uncertainties": [],
        },
        "solution_alternatives": {
            "alternatives": [],
            "generation_notes": {
                "explanation": "No alternatives are needed for this compatibility smoke.",
                "blocking_missing_information": [],
                "blocking_uncertainties": [],
            },
        },
        "risk_assessment": {"risks": [], "overall_observations": []},
    }


@pytest.mark.live_llm
def test_selected_llm_profiles_accept_canonical_smoke_contract() -> None:
    verified_names: tuple[str, ...] = ()
    failure_message: str | None = None
    try:
        config = load_llm_runtime_config(os.environ)
        verified_names = verify_selected_profiles(
            config,
            os.environ,
            report_profile=lambda name: print(f"live LLM profile: {name}"),
        )
    except LLMAdapterError as error:
        failure_message = str(error)

    if failure_message is not None:
        pytest.fail(failure_message, pytrace=False)

    assert verified_names


@pytest.mark.live_llm
def test_selected_critic_profile_accepts_slice_7_1_dynamic_schema() -> None:
    failure_message: str | None = None
    result: object = None
    client = None
    try:
        config = load_llm_runtime_config(os.environ)
        assignment = resolve_llm_runtime_config(config, os.environ)
        print(f"live dynamic Critic profile: {assignment.critic.name}")
        client = _create_http_client()
        result = OpenAICompatibleLLMAdapter(
            profile=assignment.critic,
            client=client,
        ).generate_structured(
            role="critic",
            payload=minimal_critic_payload(),
        )
    except LLMAdapterError as error:
        failure_message = str(error)
    finally:
        if client is not None:
            client.close()

    if failure_message is not None:
        pytest.fail(failure_message, pytrace=False)

    assert isinstance(result, dict)
