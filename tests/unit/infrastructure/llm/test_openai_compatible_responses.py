from __future__ import annotations

import json
from collections.abc import Callable, Mapping

import httpx
import pytest

from agentic_review_board.infrastructure.llm.config import (
    RawLLMRuntimeConfig,
    ResolvedLLMProfile,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.errors import (
    LLMHTTPStatusError,
    LLMRequestTimeoutError,
    LLMResponseEnvelopeError,
    LLMStructuredContentError,
    LLMTransportError,
)
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)

Handler = Callable[[httpx.Request], httpx.Response]


def resolved_profile() -> ResolvedLLMProfile:
    profile_name = "selected"
    config = RawLLMRuntimeConfig.model_validate(
        {
            "profiles": {
                profile_name: {
                    "base_url": "https://endpoint-marker.example/v1",
                    "model": "model-marker",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "PROMPT_ONLY",
                }
            },
            "assignments": {
                "analyst": profile_name,
                "solution_architect": profile_name,
                "risk_reviewer": profile_name,
                "critic": profile_name,
                "coordinator": profile_name,
            },
        }
    )
    return resolve_llm_runtime_config(config, {}).analyst


def invoke(
    handler: Handler,
    *,
    payload: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAICompatibleLLMAdapter(
            profile=resolved_profile(),
            client=client,
        )
        return adapter.generate_structured(
            role="analyst",
            payload=payload if payload is not None else {"input": "payload-marker"},
        )


def envelope(content: object, **extras: object) -> dict[str, object]:
    return {
        "choices": [{"message": {"content": content}}],
        **extras,
    }


def response_with_json(value: object, status_code: int = 200) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=value)

    return handler


def response_with_content(content: bytes, status_code: int = 200) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            content=content,
            headers={"Content-Type": "application/json"},
        )

    return handler


def test_accepts_minimum_envelope_and_returns_direct_json_object() -> None:
    result = invoke(response_with_json(envelope('{"result":"ok"}')))
    assert result == {"result": "ok"}


def test_ignores_unrelated_provider_envelope_extras() -> None:
    result = invoke(
        response_with_json(
            envelope(
                '{"result":"ok"}',
                id="provider-id",
                model="provider-model",
                usage={"tokens": 99},
                created=123,
            )
        )
    )
    assert result == {"result": "ok"}


@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ],
)
def test_all_timeout_subclasses_map_to_fixed_timeout_error(
    error_type: type[httpx.TimeoutException],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type("provider timeout detail", request=request)

    with pytest.raises(
        LLMRequestTimeoutError,
        match=r"^LLM request timed out$",
    ) as caught:
        invoke(handler)

    assert "provider timeout detail" not in str(caught.value)
    assert "provider timeout detail" not in repr(caught.value)


@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ConnectError,
        httpx.ProxyError,
        httpx.RemoteProtocolError,
        httpx.DecodingError,
    ],
)
def test_request_errors_map_to_fixed_transport_error(
    error_type: type[httpx.RequestError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type("provider transport detail", request=request)

    with pytest.raises(
        LLMTransportError,
        match=r"^LLM transport failed$",
    ) as caught:
        invoke(handler)

    assert "provider transport detail" not in str(caught.value)
    assert "provider transport detail" not in repr(caught.value)


@pytest.mark.parametrize("status_code", [300, 302, 400, 401, 429, 500, 503])
def test_non_success_status_maps_to_fixed_http_error(status_code: int) -> None:
    handler = response_with_content(
        b'provider-body-marker {"error":"provider-error-marker"}',
        status_code,
    )

    with pytest.raises(
        LLMHTTPStatusError,
        match=r"^LLM HTTP request failed$",
    ) as caught:
        invoke(handler)

    rendered = str(caught.value) + repr(caught.value)
    assert "provider-body-marker" not in rendered
    assert "provider-error-marker" not in rendered


@pytest.mark.parametrize(
    "handler",
    [
        response_with_content(b"{"),
        response_with_json([]),
        response_with_json(None),
        response_with_json("envelope"),
        response_with_json({}),
        response_with_json({"choices": None}),
        response_with_json({"choices": {}}),
        response_with_json({"choices": []}),
        response_with_json(
            {
                "choices": [
                    {"message": {"content": "{}"}},
                    {"message": {"content": "{}"}},
                ]
            }
        ),
        response_with_json({"choices": [None]}),
        response_with_json({"choices": [{}]}),
        response_with_json({"choices": [{"message": None}]}),
        response_with_json({"choices": [{"message": {}}]}),
        response_with_json({"choices": [{"message": {"content": None}}]}),
        response_with_json({"choices": [{"message": {"content": 1}}]}),
        response_with_json({"choices": [{"message": {"content": ""}}]}),
        response_with_json({"choices": [{"message": {"content": "   "}}]}),
    ],
)
def test_invalid_provider_envelope_fails_closed(handler: Handler) -> None:
    with pytest.raises(
        LLMResponseEnvelopeError,
        match=r"^LLM response envelope invalid$",
    ):
        invoke(handler)


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "[]",
        '"scalar"',
        "1",
        "true",
        "false",
        "null",
        "```json\n{}\n```",
        "prefix {}",
        "{} suffix",
    ],
)
def test_invalid_or_non_object_structured_content_fails_closed(content: str) -> None:
    with pytest.raises(
        LLMStructuredContentError,
        match=r"^LLM structured content invalid$",
    ):
        invoke(response_with_json(envelope(content)))


def test_direct_json_allows_only_parser_whitespace_around_complete_object() -> None:
    result = invoke(response_with_json(envelope(' \n {"value": 1} \t ')))
    assert result == {"value": 1}


def test_safe_errors_do_not_expose_request_or_provider_markers() -> None:
    markers = (
        "endpoint-marker",
        "model-marker",
        "payload-marker",
        "provider-response-marker",
        "provider-error-marker",
        "credential-marker",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "provider-response-marker provider-error-marker credential-marker",
            request=request,
        )

    with pytest.raises(LLMTransportError) as caught:
        invoke(handler)

    rendered = str(caught.value) + repr(caught.value)
    assert all(marker not in rendered for marker in markers)


def test_malformed_content_attempts_exactly_one_request_without_repair() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=envelope("```json\n{}\n```"),
        )

    with pytest.raises(LLMStructuredContentError):
        invoke(handler)

    assert len(requests) == 1


def test_transport_failure_attempts_exactly_one_request_without_retry() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ConnectError("failed", request=request)

    with pytest.raises(LLMTransportError):
        invoke(handler)

    assert len(requests) == 1


def test_valid_json_object_is_returned_unchanged_for_participant_validation() -> None:
    semantically_invalid = {
        "unknown": {"nested": [1, True, None]},
        "extra": "participant must decide validity",
    }
    result = invoke(
        response_with_json(
            envelope(json.dumps(semantically_invalid, separators=(",", ":")))
        )
    )
    assert result == semantically_invalid
