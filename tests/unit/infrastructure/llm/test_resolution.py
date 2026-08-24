from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import FrozenInstanceError

import httpx
import pytest

from agentic_review_board.infrastructure.llm.config import (
    RawLLMRuntimeConfig,
    ResolvedLLMProfile,
    StructuredOutputMode,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.errors import LLMConfigurationError


def profile_data(
    *,
    base_url: str = "http://localhost:11434/v1",
    model: str = "model",
    api_key_env: str | None = None,
    timeout_seconds: float = 30.0,
    structured_output_mode: str = "PROMPT_ONLY",
) -> dict[str, object]:
    result: dict[str, object] = {
        "base_url": base_url,
        "model": model,
        "timeout_seconds": timeout_seconds,
        "structured_output_mode": structured_output_mode,
    }
    if api_key_env is not None:
        result["api_key_env"] = api_key_env
    return result


def assignment_data(
    *,
    analyst: str = "local",
    solution_architect: str = "local",
    risk_reviewer: str = "local",
    critic: str = "local",
    coordinator: str = "local",
) -> dict[str, str]:
    return {
        "analyst": analyst,
        "solution_architect": solution_architect,
        "risk_reviewer": risk_reviewer,
        "critic": critic,
        "coordinator": coordinator,
    }


def runtime_config(
    *,
    profiles: dict[str, dict[str, object]] | None = None,
    assignments: dict[str, str] | None = None,
) -> RawLLMRuntimeConfig:
    return RawLLMRuntimeConfig.model_validate(
        {
            "profiles": profiles or {"local": profile_data()},
            "assignments": assignments or assignment_data(),
        }
    )


class RecordingEnvironment(Mapping[str, str]):
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values
        self.reads: list[str] = []

    def __getitem__(self, key: str) -> str:
        self.reads.append(key)
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


def resolved_profiles(assignment: object) -> tuple[ResolvedLLMProfile, ...]:
    return (
        assignment.analyst,
        assignment.solution_architect,
        assignment.risk_reviewer,
        assignment.critic,
        assignment.coordinator,
    )


def test_resolution_selects_exact_assigned_names_and_retains_raw_profiles() -> None:
    config = runtime_config(
        profiles={
            "local": profile_data(),
            "Remote": profile_data(
                base_url="https://api.example.test/v1",
                api_key_env="REMOTE_KEY",
                structured_output_mode="JSON_OBJECT",
            ),
            "unused": profile_data(
                base_url="https://unused.example.test/v1",
                api_key_env="UNUSED_KEY",
            ),
        },
        assignments=assignment_data(
            solution_architect="Remote",
            critic="Remote",
            coordinator="Remote",
        ),
    )

    resolved = resolve_llm_runtime_config(config, {"REMOTE_KEY": "remote-secret"})

    assert {profile.name for profile in resolved_profiles(resolved)} == {"local", "Remote"}
    assert set(config.profiles) == {"local", "Remote", "unused"}


def test_selected_unauthenticated_profile_has_no_secret() -> None:
    resolved = resolve_llm_runtime_config(runtime_config(), {})

    assert resolved.analyst.api_key is None


def test_selected_authenticated_profile_uses_explicit_environment_mapping() -> None:
    config = runtime_config(
        profiles={"remote": profile_data(api_key_env="REMOTE_KEY")},
        assignments=assignment_data(
            analyst="remote",
            solution_architect="remote",
            risk_reviewer="remote",
            critic="remote",
            coordinator="remote",
        ),
    )

    resolved = resolve_llm_runtime_config(config, {"REMOTE_KEY": "exact secret value"})

    assert resolved.analyst.api_key is not None
    assert resolved.analyst.api_key.get_secret_value() == "exact secret value"


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"REMOTE_KEY": ""},
        {"REMOTE_KEY": "   "},
        {"REMOTE_KEY": " leading"},
        {"REMOTE_KEY": "trailing "},
        {"REMOTE_KEY": "\tsecret"},
        {"REMOTE_KEY": "secret\n"},
    ],
)
def test_selected_invalid_credential_fails_closed(
    environment: dict[str, str],
) -> None:
    config = runtime_config(
        profiles={"remote": profile_data(api_key_env="REMOTE_KEY")},
        assignments=assignment_data(
            analyst="remote",
            solution_architect="remote",
            risk_reviewer="remote",
            critic="remote",
            coordinator="remote",
        ),
    )

    with pytest.raises(LLMConfigurationError, match=r"^LLM configuration invalid$"):
        resolve_llm_runtime_config(config, environment)


def test_unselected_credential_is_never_read_or_required() -> None:
    environment = RecordingEnvironment({})
    config = runtime_config(
        profiles={
            "local": profile_data(),
            "unused": profile_data(api_key_env="UNUSED_KEY"),
        }
    )

    resolved = resolve_llm_runtime_config(config, environment)

    assert resolved.analyst.name == "local"
    assert environment.reads == []


def test_only_selected_credential_names_are_read() -> None:
    environment = RecordingEnvironment(
        {"ANALYST_KEY": "analyst-secret", "CRITIC_KEY": "critic-secret"}
    )
    config = runtime_config(
        profiles={
            "analyst": profile_data(api_key_env="ANALYST_KEY"),
            "critic": profile_data(api_key_env="CRITIC_KEY"),
            "unused": profile_data(api_key_env="UNUSED_KEY"),
        },
        assignments=assignment_data(
            analyst="analyst",
            solution_architect="analyst",
            risk_reviewer="analyst",
            critic="critic",
            coordinator="critic",
        ),
    )

    resolve_llm_runtime_config(config, environment)

    assert set(environment.reads) == {"ANALYST_KEY", "CRITIC_KEY"}
    assert "UNUSED_KEY" not in environment.reads


def test_secret_is_absent_from_repr_and_ordinary_serialization() -> None:
    secret = "unique-secret-marker"
    config = runtime_config(
        profiles={"remote": profile_data(api_key_env="REMOTE_KEY")},
        assignments=assignment_data(
            analyst="remote",
            solution_architect="remote",
            risk_reviewer="remote",
            critic="remote",
            coordinator="remote",
        ),
    )

    resolved = resolve_llm_runtime_config(config, {"REMOTE_KEY": secret})

    assert secret not in repr(resolved.analyst)
    assert secret not in str(resolved.analyst)
    assert secret not in repr(resolved)
    assert secret not in config.model_dump_json()
    assert not hasattr(resolved.analyst, "model_dump")
    assert not hasattr(resolved.analyst, "model_dump_json")


def test_invalid_credential_error_does_not_disclose_value() -> None:
    secret = " secret-that-must-not-leak "
    config = runtime_config(
        profiles={"remote": profile_data(api_key_env="REMOTE_KEY")},
        assignments=assignment_data(
            analyst="remote",
            solution_architect="remote",
            risk_reviewer="remote",
            critic="remote",
            coordinator="remote",
        ),
    )

    with pytest.raises(LLMConfigurationError) as caught:
        resolve_llm_runtime_config(config, {"REMOTE_KEY": secret})

    assert secret not in str(caught.value)
    assert secret not in repr(caught.value)


@pytest.mark.parametrize("timeout", [0.1, 1.0, 45.5])
def test_scalar_timeout_expands_to_all_httpx_phases(timeout: float) -> None:
    config = runtime_config(
        profiles={"local": profile_data(timeout_seconds=timeout)}
    )

    resolved = resolve_llm_runtime_config(config, {})

    assert isinstance(resolved.analyst.timeout, httpx.Timeout)
    assert resolved.analyst.timeout.connect == timeout
    assert resolved.analyst.timeout.read == timeout
    assert resolved.analyst.timeout.write == timeout
    assert resolved.analyst.timeout.pool == timeout


def test_repeated_assignments_reuse_exact_resolved_profile_object() -> None:
    resolved = resolve_llm_runtime_config(runtime_config(), {})

    assert resolved.analyst is resolved.solution_architect
    assert resolved.analyst is resolved.risk_reviewer
    assert resolved.analyst is resolved.critic
    assert resolved.analyst is resolved.coordinator


def test_different_profile_names_produce_distinct_resolved_objects() -> None:
    config = runtime_config(
        profiles={
            "local": profile_data(),
            "remote": profile_data(base_url="https://api.example.test/v1"),
        },
        assignments=assignment_data(critic="remote", coordinator="remote"),
    )

    resolved = resolve_llm_runtime_config(config, {})

    assert resolved.analyst is not resolved.critic
    assert resolved.critic is resolved.coordinator


def test_resolved_values_are_immutable() -> None:
    resolved = resolve_llm_runtime_config(runtime_config(), {})

    with pytest.raises(FrozenInstanceError):
        resolved.analyst.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        resolved.analyst = resolved.coordinator  # type: ignore[misc]

    assert resolved.analyst.name == "local"
    assert resolved.analyst.structured_output_mode is StructuredOutputMode.PROMPT_ONLY
