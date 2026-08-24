from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from agentic_review_board.infrastructure.llm.config import RawLLMRuntimeConfig
from agentic_review_board.infrastructure.llm.errors import (
    LLMConfigurationError,
    LLMTransportError,
)
from agentic_review_board.infrastructure.llm.smoke import verify_selected_profiles


class TrackingTransport(httpx.BaseTransport):
    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler
        self.closed = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)

    def close(self) -> None:
        self.closed = True


def smoke_config() -> RawLLMRuntimeConfig:
    return RawLLMRuntimeConfig.model_validate(
        {
            "profiles": {
                "local": {
                    "base_url": "http://localhost:11434/v1",
                    "model": "local-model",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "PROMPT_ONLY",
                },
                "remote": {
                    "base_url": "https://api.example.test/v1",
                    "model": "remote-model",
                    "api_key_env": "REMOTE_KEY",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "JSON_OBJECT",
                },
                "unselected": {
                    "base_url": "https://unused.example.test/v1",
                    "model": "unused-model",
                    "api_key_env": "UNSELECTED_KEY",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "PROMPT_ONLY",
                },
            },
            "assignments": {
                "analyst": "local",
                "solution_architect": "remote",
                "risk_reviewer": "local",
                "critic": "remote",
                "coordinator": "remote",
            },
        }
    )


def test_smoke_verifies_each_selected_profile_exactly_once() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    verified_names = verify_selected_profiles(
        smoke_config(),
        {"REMOTE_KEY": "synthetic-secret"},
        transport=httpx.MockTransport(handler),
    )

    assert verified_names == ("local", "remote")
    assert [request.url.host for request in requests] == [
        "localhost",
        "api.example.test",
    ]


def test_smoke_uses_one_canonical_synthetic_role_and_payload_contract() -> None:
    request_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    verify_selected_profiles(
        smoke_config(),
        {"REMOTE_KEY": "synthetic-secret"},
        transport=httpx.MockTransport(handler),
    )

    assert len(request_bodies) == 2
    for body in request_bodies:
        messages = body["messages"]
        assert isinstance(messages, list)
        assert messages[1] == {
            "role": "user",
            "content": (
                "UNTRUSTED_PAYLOAD_JSON_BEGIN\n"
                '{"description":"Live LLM connectivity smoke check."}\n'
                "UNTRUSTED_PAYLOAD_JSON_END"
            ),
        }


def test_smoke_reports_only_safe_profile_names_and_closes_after_success() -> None:
    reported_names: list[str] = []
    transport = TrackingTransport(
        lambda _request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )
    )

    verified_names = verify_selected_profiles(
        smoke_config(),
        {"REMOTE_KEY": "secret-success-marker"},
        transport=transport,
        report_profile=reported_names.append,
    )

    assert verified_names == ("local", "remote")
    assert reported_names == ["local", "remote"]
    assert transport.closed is True
    assert "secret-success-marker" not in repr(reported_names)


def test_smoke_closes_after_provider_failure_without_leaking_dynamic_detail() -> None:
    reported_names: list[str] = []
    secret = "secret-failure-marker"
    endpoint = "https://api.example.test/v1/chat/completions"
    body = "provider-body-marker"
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if request.url.host == "api.example.test":
            raise httpx.ConnectError(
                f"{secret} {endpoint} {body}",
                request=request,
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    transport = TrackingTransport(handler)

    with pytest.raises(LLMTransportError) as captured:
        verify_selected_profiles(
            smoke_config(),
            {"REMOTE_KEY": secret},
            transport=transport,
            report_profile=reported_names.append,
        )

    public_diagnostic = f"{reported_names[-1]}: {captured.value}"
    assert attempts == 2
    assert reported_names == ["local", "remote"]
    assert public_diagnostic == "remote: LLM transport failed"
    assert all(marker not in public_diagnostic for marker in (secret, endpoint, body))
    assert transport.closed is True


@pytest.mark.parametrize("credential", [None, "", " leading", "trailing "])
def test_smoke_rejects_missing_or_invalid_selected_profile_credential(
    credential: str | None,
) -> None:
    environment = {} if credential is None else {"REMOTE_KEY": credential}
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500)

    with pytest.raises(LLMConfigurationError):
        verify_selected_profiles(
            smoke_config(),
            environment,
            transport=TrackingTransport(handler),
        )

    assert attempts == 0


def test_smoke_ignores_missing_unselected_profile_credential() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    verified_names = verify_selected_profiles(
        smoke_config(),
        {"REMOTE_KEY": "selected-only-secret"},
        transport=TrackingTransport(handler),
    )

    assert verified_names == ("local", "remote")
    assert attempts == 2
