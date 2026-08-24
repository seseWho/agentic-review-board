from __future__ import annotations

import json

import httpx
from agentic_review_board.infrastructure.llm.config import RawLLMRuntimeConfig
from agentic_review_board.infrastructure.llm.smoke import verify_selected_profiles


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
