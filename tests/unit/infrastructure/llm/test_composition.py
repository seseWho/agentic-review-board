from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from agentic_review_board.infrastructure.llm import composition
from agentic_review_board.infrastructure.llm.composition import (
    ConfiguredReviewRuntime,
    _create_http_client,
)
from agentic_review_board.infrastructure.llm.config import RawLLMRuntimeConfig


def profile_data(*, base_url: str, model: str) -> dict[str, object]:
    return {
        "base_url": base_url,
        "model": model,
        "timeout_seconds": 10.0,
        "structured_output_mode": "PROMPT_ONLY",
    }


def runtime_config(
    *,
    profiles: dict[str, dict[str, object]],
    assignments: dict[str, str],
) -> RawLLMRuntimeConfig:
    return RawLLMRuntimeConfig.model_validate(
        {"profiles": profiles, "assignments": assignments}
    )


def test_http_client_constructor_uses_only_approved_explicit_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    captured: dict[str, object] = {}
    client_marker = object()

    def capture_client(**kwargs: Any) -> object:
        captured.update(kwargs)
        return client_marker

    monkeypatch.setattr(httpx, "Client", capture_client)

    result = _create_http_client(transport)

    assert result is client_marker
    assert captured == {
        "trust_env": True,
        "follow_redirects": False,
        "transport": transport,
    }
    assert {
        "auth",
        "base_url",
        "cookies",
        "headers",
        "timeout",
    }.isdisjoint(captured)


def test_http_client_constructor_omits_transport_when_not_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    client_marker = object()

    def capture_client(**kwargs: Any) -> object:
        captured.update(kwargs)
        return client_marker

    monkeypatch.setattr(httpx, "Client", capture_client)

    result = _create_http_client()

    assert result is client_marker
    assert captured == {"trust_env": True, "follow_redirects": False}


def test_http_client_does_not_follow_redirects() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            302,
            headers={"Location": "https://redirect-target.example/final"},
        )

    transport = httpx.MockTransport(handler)
    with _create_http_client(transport) as client:
        response = client.get("https://original-target.example/start")

    assert response.status_code == 302
    assert [str(request.url) for request in requests] == [
        "https://original-target.example/start"
    ]


def test_creates_one_adapter_per_selected_name_and_reuses_exact_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        profiles={
            "local": profile_data(
                base_url="http://localhost:11434/v1",
                model="local-model",
            ),
            "remote": profile_data(
                base_url="https://api.example.test/v1",
                model="remote-model",
            ),
            "unused": profile_data(
                base_url="https://unused.example.test/v1",
                model="unused-model",
            ),
        },
        assignments={
            "analyst": "local",
            "solution_architect": "remote",
            "risk_reviewer": "local",
            "critic": "remote",
            "coordinator": "remote",
        },
    )
    created_adapters: dict[str, object] = {}
    participant_adapters: dict[str, object] = {}

    def create_adapter(*, profile: Any, client: httpx.Client) -> object:
        assert isinstance(client, httpx.Client)
        marker = object()
        assert profile.name not in created_adapters
        created_adapters[profile.name] = marker
        return marker

    def participant_factory(role: str) -> Callable[[object], object]:
        def create_participant(adapter: object) -> object:
            participant_adapters[role] = adapter
            return object()

        return create_participant

    monkeypatch.setattr(composition, "OpenAICompatibleLLMAdapter", create_adapter)
    monkeypatch.setattr(composition, "Analyst", participant_factory("analyst"))
    monkeypatch.setattr(
        composition,
        "SolutionArchitect",
        participant_factory("solution_architect"),
    )
    monkeypatch.setattr(
        composition,
        "RiskReviewer",
        participant_factory("risk_reviewer"),
    )
    monkeypatch.setattr(composition, "Critic", participant_factory("critic"))
    monkeypatch.setattr(
        composition,
        "Coordinator",
        participant_factory("coordinator"),
    )
    monkeypatch.setattr(
        composition,
        "ReviewOrchestrator",
        lambda *participants: object(),
    )

    runtime = ConfiguredReviewRuntime.from_config(config, {})
    runtime.close()

    assert set(created_adapters) == {"local", "remote"}
    assert participant_adapters == {
        "analyst": created_adapters["local"],
        "solution_architect": created_adapters["remote"],
        "risk_reviewer": created_adapters["local"],
        "critic": created_adapters["remote"],
        "coordinator": created_adapters["remote"],
    }
    assert participant_adapters["analyst"] is participant_adapters["risk_reviewer"]
    assert participant_adapters["solution_architect"] is participant_adapters["critic"]
    assert participant_adapters["critic"] is participant_adapters["coordinator"]
