from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from agentic_review_board.infrastructure.llm.config import (
    LLMRole,
    ParticipantLLMAssignment,
    RawLLMProfile,
    RawLLMRuntimeConfig,
    StructuredOutputMode,
    load_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.errors import (
    LLMAdapterError,
    LLMConfigurationError,
    LLMHTTPStatusError,
    LLMPayloadSerializationError,
    LLMRequestTimeoutError,
    LLMResponseEnvelopeError,
    LLMRuntimeClosedError,
    LLMStructuredContentError,
    LLMTransportError,
    UnsupportedLLMRoleError,
)


def profile_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "base_url": "http://localhost:11434/v1",
        "model": "local-model",
        "timeout_seconds": 30.0,
        "structured_output_mode": "PROMPT_ONLY",
    }
    data.update(overrides)
    return data


def assignment_data(profile: str = "local") -> dict[str, str]:
    return {
        "analyst": profile,
        "solution_architect": profile,
        "risk_reviewer": profile,
        "critic": profile,
        "coordinator": profile,
    }


def runtime_data() -> dict[str, object]:
    return {
        "profiles": {"local": profile_data()},
        "assignments": assignment_data(),
    }


@pytest.mark.parametrize("value", ["JSON_OBJECT", "PROMPT_ONLY"])
def test_structured_output_mode_accepts_only_exact_values(value: str) -> None:
    assert StructuredOutputMode(value).value == value


@pytest.mark.parametrize(
    "value",
    ["", " ", "json_object", "prompt_only", "JSON", " JSON_OBJECT", "PROMPT_ONLY "],
)
def test_structured_output_mode_rejects_aliases_and_normalization(value: str) -> None:
    with pytest.raises(ValueError):
        StructuredOutputMode(value)


@pytest.mark.parametrize(
    "value",
    ["analyst", "solution_architect", "risk_reviewer", "critic", "coordinator"],
)
def test_llm_role_accepts_only_exact_values(value: str) -> None:
    assert LLMRole(value).value == value


@pytest.mark.parametrize(
    "value",
    ["", "Analyst", "solution-architect", "risk reviewer", " analyst", "critic "],
)
def test_llm_role_rejects_aliases_and_normalization(value: str) -> None:
    with pytest.raises(ValueError):
        LLMRole(value)


@pytest.mark.parametrize(
    "missing",
    ["base_url", "model", "timeout_seconds", "structured_output_mode"],
)
def test_raw_profile_requires_all_non_optional_fields(missing: str) -> None:
    data = profile_data()
    del data[missing]
    with pytest.raises(ValidationError):
        RawLLMProfile.model_validate(data)


def test_raw_profile_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RawLLMProfile.model_validate(profile_data(temperature=0.2))


def test_raw_profile_strips_model_boundary_whitespace_once() -> None:
    profile = RawLLMProfile.model_validate(profile_data(model="  org/model name  "))
    assert profile.model == "org/model name"


@pytest.mark.parametrize("model", ["", " ", "\t\n", None, 123])
def test_raw_profile_rejects_invalid_models(model: object) -> None:
    with pytest.raises(ValidationError):
        RawLLMProfile.model_validate(profile_data(model=model))


@pytest.mark.parametrize("timeout", [1, 0.1, 60.0])
def test_raw_profile_accepts_positive_finite_numeric_timeout(timeout: float) -> None:
    assert RawLLMProfile.model_validate(
        profile_data(timeout_seconds=timeout)
    ).timeout_seconds == float(timeout)


@pytest.mark.parametrize(
    "timeout",
    [0, -1, math.inf, -math.inf, math.nan, True, False, "30", None],
)
def test_raw_profile_rejects_invalid_timeout(timeout: object) -> None:
    with pytest.raises(ValidationError):
        RawLLMProfile.model_validate(profile_data(timeout_seconds=timeout))


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://localhost:11434", "http://localhost:11434"),
        ("http://127.0.0.1:8000/v1/", "http://127.0.0.1:8000/v1"),
        ("https://api.example.test/v1", "https://api.example.test/v1"),
        ("https://models.internal:9443/api/v1/", "https://models.internal:9443/api/v1"),
    ],
)
def test_raw_profile_accepts_and_normalizes_base_urls(
    base_url: str, expected: str
) -> None:
    profile = RawLLMProfile.model_validate(profile_data(base_url=base_url))
    assert profile.base_url == expected


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        " ",
        "localhost:11434/v1",
        "ftp://example.test/v1",
        "https:///v1",
        "https://user@example.test/v1",
        "https://user:pass@example.test/v1",
        "https://example.test/v1?token=x",
        "https://example.test/v1#fragment",
        "https://example.test/v1/chat/completions",
        "https://example.test/chat/completions/",
        "https://example.test/v1\n",
        "https://example.test/\x00v1",
    ],
)
def test_raw_profile_rejects_unsafe_or_precomposed_base_urls(base_url: str) -> None:
    with pytest.raises(ValidationError):
        RawLLMProfile.model_validate(profile_data(base_url=base_url))


@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "_LOCAL_KEY", "KEY1", "a"])
def test_api_key_env_accepts_exact_environment_identity(name: str) -> None:
    profile = RawLLMProfile.model_validate(profile_data(api_key_env=name))
    assert profile.api_key_env == name


def test_api_key_env_may_be_absent_for_unauthenticated_profile() -> None:
    assert RawLLMProfile.model_validate(profile_data()).api_key_env is None


@pytest.mark.parametrize(
    "name",
    ["", " ", " OPENAI_API_KEY", "OPENAI_API_KEY ", "1KEY", "API-KEY", "API.KEY", "ÁPI_KEY"],
)
def test_api_key_env_rejects_invalid_or_repaired_identity(name: str) -> None:
    with pytest.raises(ValidationError):
        RawLLMProfile.model_validate(profile_data(api_key_env=name))


def test_assignment_requires_exactly_five_fields() -> None:
    assignment = ParticipantLLMAssignment.model_validate(assignment_data())
    assert assignment.model_dump() == assignment_data()


@pytest.mark.parametrize("missing", list(assignment_data()))
def test_assignment_rejects_missing_participant(missing: str) -> None:
    data = assignment_data()
    del data[missing]
    with pytest.raises(ValidationError):
        ParticipantLLMAssignment.model_validate(data)


def test_assignment_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ParticipantLLMAssignment.model_validate(
            {**assignment_data(), "observer": "local"}
        )


@pytest.mark.parametrize(
    "name",
    ["", " local", "local ", "_local", "1local", "local.profile", "LOCAL/profile"],
)
def test_assignment_rejects_invalid_or_repaired_profile_reference(name: str) -> None:
    with pytest.raises(ValidationError):
        ParticipantLLMAssignment.model_validate(assignment_data(name))


def test_runtime_config_accepts_declared_unselected_profiles() -> None:
    config = RawLLMRuntimeConfig.model_validate(
        {
            "profiles": {
                "local": profile_data(),
                "Remote-2": profile_data(
                    base_url="https://api.example.test/v1",
                    structured_output_mode="JSON_OBJECT",
                ),
            },
            "assignments": assignment_data("local"),
        }
    )
    assert set(config.profiles) == {"local", "Remote-2"}


def test_runtime_config_requires_at_least_one_profile() -> None:
    with pytest.raises(ValidationError):
        RawLLMRuntimeConfig.model_validate(
            {"profiles": {}, "assignments": assignment_data()}
        )


@pytest.mark.parametrize(
    "name",
    ["", "_local", "1local", "local.profile", " local", "local "],
)
def test_runtime_config_rejects_invalid_or_repaired_profile_name(name: str) -> None:
    with pytest.raises(ValidationError):
        RawLLMRuntimeConfig.model_validate(
            {"profiles": {name: profile_data()}, "assignments": assignment_data(name)}
        )


def test_runtime_config_forbids_top_level_extras() -> None:
    with pytest.raises(ValidationError):
        RawLLMRuntimeConfig.model_validate({**runtime_data(), "router": {}})


def test_runtime_config_resolves_assignments_by_exact_name() -> None:
    data = runtime_data()
    data["profiles"] = {"local": profile_data(), "LOCAL": profile_data()}
    data["assignments"] = {**assignment_data(), "critic": "LOCAL"}
    config = RawLLMRuntimeConfig.model_validate(data)
    assert config.assignments.analyst == "local"
    assert config.assignments.critic == "LOCAL"


def test_runtime_config_rejects_unknown_exact_reference() -> None:
    with pytest.raises(ValidationError):
        RawLLMRuntimeConfig.model_validate(
            {"profiles": {"local": profile_data()}, "assignments": assignment_data("Local")}
        )


def write_bytes(path: Path, content: bytes) -> None:
    path.write_bytes(content)


def load_from_path(path: Path) -> RawLLMRuntimeConfig:
    return load_llm_runtime_config({"ARB_LLM_CONFIG_PATH": str(path)})


@pytest.mark.parametrize("environment", [{}, {"ARB_LLM_CONFIG_PATH": ""}, {"ARB_LLM_CONFIG_PATH": " "}])
def test_loader_rejects_absent_or_blank_path(environment: dict[str, str]) -> None:
    with pytest.raises(LLMConfigurationError, match=r"^LLM configuration invalid$"):
        load_llm_runtime_config(environment)


def test_loader_rejects_missing_or_non_regular_file(tmp_path: Path) -> None:
    for path in (tmp_path / "missing.json", tmp_path):
        with pytest.raises(LLMConfigurationError, match=r"^LLM configuration invalid$"):
            load_from_path(path)


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xfe",
        b"{",
        b"[]",
        b"null",
        b'"value"',
    ],
)
def test_loader_rejects_non_utf8_malformed_or_non_object_json(
    tmp_path: Path, content: bytes
) -> None:
    path = tmp_path / "config.json"
    write_bytes(path, content)
    with pytest.raises(LLMConfigurationError, match=r"^LLM configuration invalid$"):
        load_from_path(path)


@pytest.mark.parametrize(
    "content",
    [
        '{"profiles":{},"profiles":{},"assignments":{}}',
        '{"profiles":{"local":{"base_url":"http://localhost","base_url":"https://x.test","model":"m","timeout_seconds":1,"structured_output_mode":"PROMPT_ONLY"}},"assignments":{"analyst":"local","solution_architect":"local","risk_reviewer":"local","critic":"local","coordinator":"local"}}',
        '{"profiles":{"local":{"base_url":"http://localhost","model":"m","timeout_seconds":1,"structured_output_mode":"PROMPT_ONLY"}},"assignments":{"analyst":"local","analyst":"local","solution_architect":"local","risk_reviewer":"local","critic":"local","coordinator":"local"}}',
    ],
)
def test_loader_rejects_duplicate_keys_at_every_nesting_level(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(LLMConfigurationError, match=r"^LLM configuration invalid$"):
        load_from_path(path)


def test_loader_returns_validated_config(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        '{"profiles":{"local":{"base_url":"http://localhost:11434/v1/","model":" model ","timeout_seconds":30,"structured_output_mode":"PROMPT_ONLY"}},"assignments":{"analyst":"local","solution_architect":"local","risk_reviewer":"local","critic":"local","coordinator":"local"}}',
        encoding="utf-8",
    )
    config = load_from_path(path)
    assert config.profiles["local"].base_url == "http://localhost:11434/v1"
    assert config.profiles["local"].model == "model"


ERROR_CASES: tuple[tuple[type[LLMAdapterError], str], ...] = (
    (LLMConfigurationError, "LLM configuration invalid"),
    (LLMRuntimeClosedError, "LLM runtime is closed"),
    (UnsupportedLLMRoleError, "LLM role unsupported"),
    (LLMPayloadSerializationError, "LLM payload serialization failed"),
    (LLMRequestTimeoutError, "LLM request timed out"),
    (LLMTransportError, "LLM transport failed"),
    (LLMHTTPStatusError, "LLM HTTP request failed"),
    (LLMResponseEnvelopeError, "LLM response envelope invalid"),
    (LLMStructuredContentError, "LLM structured content invalid"),
)


@pytest.mark.parametrize(("error_type", "message"), ERROR_CASES)
def test_adapter_errors_have_closed_inheritance_and_fixed_messages(
    error_type: type[LLMAdapterError], message: str
) -> None:
    error = error_type()
    assert isinstance(error, LLMAdapterError)
    assert isinstance(error, RuntimeError)
    assert type(error) is error_type
    assert str(error) == message
    assert error.args == (message,)


def test_safe_errors_do_not_accept_dynamic_public_detail() -> None:
    secret_marker = "sensitive-provider-detail"
    for error_type, _ in ERROR_CASES:
        dynamic_constructor = cast(Callable[[str], LLMAdapterError], error_type)
        with pytest.raises(TypeError):
            dynamic_constructor(secret_marker)
