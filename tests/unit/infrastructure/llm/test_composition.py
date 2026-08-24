from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from agentic_review_board.infrastructure.llm.composition import (
    ConfiguredReviewRuntime,
    _create_http_client,
)

from agentic_review_board.infrastructure.llm import composition
from agentic_review_board.infrastructure.llm.config import RawLLMRuntimeConfig, ResolvedLLMProfile


def profile_data(
    *,
    base_url: str,
    model: str,
    api_key_env: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "base_url": base_url,
        "model": model,
        "timeout_seconds": 10.0,
        "structured_output_mode": "PROMPT_ONLY",
    }
    if api_key_env is not None:
        result["api_key_env"] = api_key_env
    return result


def runtime_config(
    *,
    profiles: dict[str, dict[str, object]],
    assignments: dict[str, str],
) -> RawLLMRuntimeConfig:
    return RawLLMRuntimeConfig.model_validate({"profiles": profiles, "assignments": assignments})


def record_runtime_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    dict[str, object],
    dict[str, ResolvedLLMProfile],
    dict[str, object],
]:
    created_adapters: dict[str, object] = {}
    created_profiles: dict[str, ResolvedLLMProfile] = {}
    participant_adapters: dict[str, object] = {}

    def create_adapter(*, profile: ResolvedLLMProfile, client: httpx.Client) -> object:
        assert isinstance(client, httpx.Client)
        marker = object()
        assert profile.name not in created_adapters
        created_adapters[profile.name] = marker
        created_profiles[profile.name] = profile
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
    return created_adapters, created_profiles, participant_adapters


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
    assert [str(request.url) for request in requests] == ["https://original-target.example/start"]


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
    created_adapters, _, participant_adapters = record_runtime_composition(monkeypatch)

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


def test_supports_one_profile_shared_by_all_five_participants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        profiles={
            "shared": profile_data(
                base_url="http://localhost:11434/v1",
                model="shared-model",
            )
        },
        assignments={
            role: "shared"
            for role in (
                "analyst",
                "solution_architect",
                "risk_reviewer",
                "critic",
                "coordinator",
            )
        },
    )
    created_adapters, _, participant_adapters = record_runtime_composition(monkeypatch)

    runtime = ConfiguredReviewRuntime.from_config(config, {})
    runtime.close()

    assert set(created_adapters) == {"shared"}
    assert set(participant_adapters) == {
        "analyst",
        "solution_architect",
        "risk_reviewer",
        "critic",
        "coordinator",
    }
    assert all(adapter is created_adapters["shared"] for adapter in participant_adapters.values())


def test_supports_five_distinct_selected_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roles = (
        "analyst",
        "solution_architect",
        "risk_reviewer",
        "critic",
        "coordinator",
    )
    config = runtime_config(
        profiles={
            role: profile_data(
                base_url=f"https://{role.replace('_', '-')}.example.test/v1",
                model=f"{role}-model",
            )
            for role in roles
        },
        assignments={role: role for role in roles},
    )
    created_adapters, _, participant_adapters = record_runtime_composition(monkeypatch)

    runtime = ConfiguredReviewRuntime.from_config(config, {})
    runtime.close()

    assert set(created_adapters) == set(roles)
    assert all(participant_adapters[role] is created_adapters[role] for role in roles)
    assert len({id(adapter) for adapter in participant_adapters.values()}) == 5


def test_supports_mixed_local_no_key_and_remote_key_profiles(
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
                api_key_env="REMOTE_KEY",
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
    _, created_profiles, _ = record_runtime_composition(monkeypatch)

    runtime = ConfiguredReviewRuntime.from_config(
        config,
        {"REMOTE_KEY": "remote-secret-marker"},
    )
    runtime.close()

    assert created_profiles["local"].api_key is None
    remote_key = created_profiles["remote"].api_key
    assert remote_key is not None
    assert remote_key.get_secret_value() == "remote-secret-marker"
