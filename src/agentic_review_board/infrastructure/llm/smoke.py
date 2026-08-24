from __future__ import annotations

from collections.abc import Callable, Mapping

import httpx

from agentic_review_board.infrastructure.llm.composition import _create_http_client
from agentic_review_board.infrastructure.llm.config import (
    LLMRole,
    RawLLMRuntimeConfig,
    ResolvedLLMProfile,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.errors import LLMTransportError
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)

_SMOKE_PAYLOAD = {"description": "Live LLM connectivity smoke check."}


def verify_selected_profiles(
    config: RawLLMRuntimeConfig,
    environment: Mapping[str, str],
    *,
    transport: httpx.BaseTransport | None = None,
    report_profile: Callable[[str], None] | None = None,
) -> tuple[str, ...]:
    assignment = resolve_llm_runtime_config(config, environment)
    resolved_by_name: dict[str, ResolvedLLMProfile] = {}
    for profile in (
        assignment.analyst,
        assignment.solution_architect,
        assignment.risk_reviewer,
        assignment.critic,
        assignment.coordinator,
    ):
        resolved_by_name.setdefault(profile.name, profile)

    selected_names = tuple(sorted(resolved_by_name))
    client = _create_http_client(transport)
    operation_error: BaseException | None = None
    try:
        for name in selected_names:
            if report_profile is not None:
                report_profile(name)
            OpenAICompatibleLLMAdapter(
                profile=resolved_by_name[name],
                client=client,
            ).generate_structured(
                role=LLMRole.ANALYST.value,
                payload=_SMOKE_PAYLOAD,
            )
    except BaseException as error:
        operation_error = error
        raise
    finally:
        try:
            client.close()
        except BaseException as cleanup_error:
            if operation_error is None:
                raise LLMTransportError() from cleanup_error

    return selected_names
