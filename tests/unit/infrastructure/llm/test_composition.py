from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import httpx
import pytest
from agentic_review_board.infrastructure.llm.composition import (
    ConfiguredReviewRuntime,
    _create_http_client,
)

from agentic_review_board.application.orchestrator import ReviewOrchestrator
from agentic_review_board.infrastructure.llm import composition
from agentic_review_board.infrastructure.llm.config import RawLLMRuntimeConfig, ResolvedLLMProfile
from agentic_review_board.infrastructure.llm.errors import (
    LLMConfigurationError,
    LLMRuntimeClosedError,
)


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


def shared_runtime_config() -> RawLLMRuntimeConfig:
    return runtime_config(
        profiles={
            "shared": profile_data(
                base_url="http://localhost:11434/v1",
                model="shared-model",
            )
        },
        assignments={
            "analyst": "shared",
            "solution_architect": "shared",
            "risk_reviewer": "shared",
            "critic": "shared",
            "coordinator": "shared",
        },
    )


class CloseRecordingTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.close_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={}, request=request)

    def close(self) -> None:
        self.close_count += 1


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


def test_constructs_existing_orchestrator_with_exact_five_argument_order(
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
            "analyst": "shared",
            "solution_architect": "shared",
            "risk_reviewer": "shared",
            "critic": "shared",
            "coordinator": "shared",
        },
    )
    _, _, participant_adapters = record_runtime_composition(monkeypatch)
    orchestrator_calls: list[tuple[object, ...]] = []

    def construct_real_orchestrator(
        analyst: object,
        solution_architect: object,
        risk_reviewer: object,
        critic: object,
        coordinator: object,
    ) -> ReviewOrchestrator:
        participants = (
            analyst,
            solution_architect,
            risk_reviewer,
            critic,
            coordinator,
        )
        orchestrator_calls.append(participants)
        return ReviewOrchestrator(*participants)  # type: ignore[arg-type]

    monkeypatch.setattr(
        composition,
        "ReviewOrchestrator",
        construct_real_orchestrator,
    )

    runtime = ConfiguredReviewRuntime.from_config(config, {})
    runtime.close()

    assert orchestrator_calls == [
        (
            participant_adapters["analyst"],
            participant_adapters["solution_architect"],
            participant_adapters["risk_reviewer"],
            participant_adapters["critic"],
            participant_adapters["coordinator"],
        )
    ]


def test_completes_resolution_before_creating_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        profiles={
            "remote": profile_data(
                base_url="https://api.example.test/v1",
                model="remote-model",
                api_key_env="REMOTE_KEY",
            )
        },
        assignments={
            "analyst": "remote",
            "solution_architect": "remote",
            "risk_reviewer": "remote",
            "critic": "remote",
            "coordinator": "remote",
        },
    )
    events: list[str] = []
    real_resolve = composition.resolve_llm_runtime_config
    real_create_client = composition._create_http_client

    def resolve_before_resources(
        raw_config: RawLLMRuntimeConfig,
        environ: Mapping[str, str],
    ) -> Any:
        resolved = real_resolve(raw_config, environ)
        events.append("resolution-complete")
        return resolved

    def create_after_resolution(
        transport: httpx.BaseTransport | None = None,
    ) -> httpx.Client:
        assert events == ["resolution-complete"]
        events.append("client-created")
        return real_create_client(transport)

    monkeypatch.setattr(
        composition,
        "resolve_llm_runtime_config",
        resolve_before_resources,
    )
    monkeypatch.setattr(composition, "_create_http_client", create_after_resolution)

    runtime = ConfiguredReviewRuntime.from_config(
        config,
        {"REMOTE_KEY": "remote-secret-marker"},
    )
    runtime.close()

    assert events == ["resolution-complete", "client-created"]


def test_resolution_failure_occurs_before_http_client_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        profiles={
            "remote": profile_data(
                base_url="https://api.example.test/v1",
                model="remote-model",
                api_key_env="REMOTE_KEY",
            )
        },
        assignments={
            "analyst": "remote",
            "solution_architect": "remote",
            "risk_reviewer": "remote",
            "critic": "remote",
            "coordinator": "remote",
        },
    )
    client_creation_count = 0

    def must_not_create_client(
        transport: httpx.BaseTransport | None = None,
    ) -> httpx.Client:
        nonlocal client_creation_count
        client_creation_count += 1
        raise AssertionError(f"unexpected transport: {transport!r}")

    monkeypatch.setattr(composition, "_create_http_client", must_not_create_client)

    with pytest.raises(
        LLMConfigurationError,
        match=r"^LLM configuration invalid$",
    ):
        ConfiguredReviewRuntime.from_config(config, {})

    assert client_creation_count == 0


def test_unexpected_failure_after_client_creation_closes_client(
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
            "analyst": "shared",
            "solution_architect": "shared",
            "risk_reviewer": "shared",
            "critic": "shared",
            "coordinator": "shared",
        },
    )
    clients: list[httpx.Client] = []
    real_create_client = composition._create_http_client

    def track_client(
        transport: httpx.BaseTransport | None = None,
    ) -> httpx.Client:
        client = real_create_client(transport)
        clients.append(client)
        return client

    def fail_participant_construction(adapter: object) -> object:
        raise RuntimeError("unexpected construction failure marker")

    monkeypatch.setattr(composition, "_create_http_client", track_client)
    monkeypatch.setattr(composition, "Analyst", fail_participant_construction)

    with pytest.raises(
        RuntimeError,
        match=r"^unexpected construction failure marker$",
    ):
        ConfiguredReviewRuntime.from_config(config, {})

    assert len(clients) == 1
    assert clients[0].is_closed


def test_open_context_entry_returns_same_runtime() -> None:
    transport = CloseRecordingTransport()
    runtime = ConfiguredReviewRuntime.from_config(
        shared_runtime_config(),
        {},
        transport=transport,
    )

    entered = runtime.__enter__()
    runtime.close()

    assert entered is runtime
    assert transport.close_count == 1


def test_close_is_idempotent_and_closes_owned_client_once() -> None:
    transport = CloseRecordingTransport()
    runtime = ConfiguredReviewRuntime.from_config(
        shared_runtime_config(),
        {},
        transport=transport,
    )

    runtime.close()
    runtime.close()
    runtime.close()

    assert transport.close_count == 1


def test_context_exit_closes_runtime_even_when_body_raises() -> None:
    transport = CloseRecordingTransport()

    with pytest.raises(RuntimeError, match=r"^context failure marker$"):
        with ConfiguredReviewRuntime.from_config(
            shared_runtime_config(),
            {},
            transport=transport,
        ):
            raise RuntimeError("context failure marker")

    assert transport.close_count == 1


def test_closed_context_entry_fails_with_exact_safe_error() -> None:
    transport = CloseRecordingTransport()
    runtime = ConfiguredReviewRuntime.from_config(
        shared_runtime_config(),
        {},
        transport=transport,
    )
    runtime.close()

    with pytest.raises(
        LLMRuntimeClosedError,
        match=r"^LLM runtime is closed$",
    ):
        runtime.__enter__()

    assert transport.close_count == 1


def test_execute_is_the_only_public_review_execution_path() -> None:
    transport = CloseRecordingTransport()
    runtime = ConfiguredReviewRuntime.from_config(
        shared_runtime_config(),
        {},
        transport=transport,
    )

    public_callables = {
        name
        for name in dir(runtime)
        if not name.startswith("_") and callable(getattr(runtime, name))
    }
    runtime.close()

    assert public_callables == {"close", "execute", "from_config"}
    assert "run" not in public_callables
    assert "orchestrate" not in public_callables


def test_public_surface_does_not_expose_owned_runtime_objects() -> None:
    transport = CloseRecordingTransport()
    runtime = ConfiguredReviewRuntime.from_config(
        shared_runtime_config(),
        {},
        transport=transport,
    )

    public_names = {name for name in dir(runtime) if not name.startswith("_")}
    runtime.close()

    assert set(composition.__all__) == {"ConfiguredReviewRuntime"}
    assert {
        "adapter",
        "adapters",
        "adapter_by_profile",
        "assignment",
        "client",
        "http_client",
        "orchestrator",
        "profiles",
        "resolved_assignment",
        "resolved_profiles",
    }.isdisjoint(public_names)
