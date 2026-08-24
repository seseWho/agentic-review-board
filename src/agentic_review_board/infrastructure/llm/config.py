from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic.types import SecretStr

from agentic_review_board.infrastructure.llm.errors import LLMConfigurationError

_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROFILE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"
_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


class StructuredOutputMode(StrEnum):
    JSON_OBJECT = "JSON_OBJECT"
    PROMPT_ONLY = "PROMPT_ONLY"


class LLMRole(StrEnum):
    ANALYST = "analyst"
    SOLUTION_ARCHITECT = "solution_architect"
    RISK_REVIEWER = "risk_reviewer"
    CRITIC = "critic"
    COORDINATOR = "coordinator"


class RawLLMProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str
    model: str
    api_key_env: str | None = None
    timeout_seconds: float
    structured_output_mode: StructuredOutputMode

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, value: object) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("invalid base URL")
        if (
            any(
                character.isspace()
                or ord(character) < 32
                or ord(character) == 127
                for character in value
            )
            or "\\" in value
            or value.endswith("//")
            or _INVALID_PERCENT_ESCAPE.search(value) is not None
        ):
            raise ValueError("invalid base URL")

        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            parsed.port
        except ValueError as error:
            raise ValueError("invalid base URL") from error

        if (
            parsed.scheme not in {"http", "https"}
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid base URL")

        normalized = value.removesuffix("/")
        if normalized.endswith(_CHAT_COMPLETIONS_SUFFIX):
            raise ValueError("invalid base URL")
        return normalized

    @field_validator("model", mode="before")
    @classmethod
    def validate_model(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid model")
        normalized = value.strip()
        if not normalized:
            raise ValueError("invalid model")
        return normalized

    @field_validator("api_key_env", mode="before")
    @classmethod
    def validate_api_key_env(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or _ENVIRONMENT_NAME.fullmatch(value) is None:
            raise ValueError("invalid credential environment name")
        return value

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def validate_timeout(cls, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid timeout")
        result = float(value)
        if not math.isfinite(result) or result <= 0:
            raise ValueError("invalid timeout")
        return result


class ParticipantLLMAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    analyst: str
    solution_architect: str
    risk_reviewer: str
    critic: str
    coordinator: str

    @field_validator(
        "analyst",
        "solution_architect",
        "risk_reviewer",
        "critic",
        "coordinator",
        mode="before",
    )
    @classmethod
    def validate_profile_reference(cls, value: object) -> str:
        if not isinstance(value, str) or _PROFILE_NAME.fullmatch(value) is None:
            raise ValueError("invalid profile reference")
        return value


class RawLLMRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profiles: Mapping[str, RawLLMProfile] = Field(min_length=1)
    assignments: ParticipantLLMAssignment

    @field_validator("profiles", mode="before")
    @classmethod
    def validate_profile_names(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if any(
            not isinstance(name, str) or _PROFILE_NAME.fullmatch(name) is None
            for name in value
        ):
            raise ValueError("invalid profile name")
        return value

    @field_validator("profiles")
    @classmethod
    def freeze_profiles(
        cls, value: Mapping[str, RawLLMProfile]
    ) -> Mapping[str, RawLLMProfile]:
        return MappingProxyType(dict(value))

    @field_serializer("profiles")
    def serialize_profiles(
        self, value: Mapping[str, RawLLMProfile]
    ) -> dict[str, RawLLMProfile]:
        return dict(value)

    @model_validator(mode="after")
    def validate_assignment_references(self) -> RawLLMRuntimeConfig:
        assigned_names = self.assignments.model_dump().values()
        if any(name not in self.profiles for name in assigned_names):
            raise ValueError("unknown profile reference")
        return self


@dataclass(frozen=True, slots=True)
class ResolvedLLMProfile:
    name: str
    base_url: str
    model: str
    api_key: SecretStr | None
    _timeout_seconds: float = field(repr=False)
    structured_output_mode: StructuredOutputMode

    @property
    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self._timeout_seconds,
            read=self._timeout_seconds,
            write=self._timeout_seconds,
            pool=self._timeout_seconds,
        )


@dataclass(frozen=True, slots=True)
class ResolvedParticipantLLMAssignment:
    analyst: ResolvedLLMProfile
    solution_architect: ResolvedLLMProfile
    risk_reviewer: ResolvedLLMProfile
    critic: ResolvedLLMProfile
    coordinator: ResolvedLLMProfile


def _resolve_api_key(
    raw_profile: RawLLMProfile,
    environment: Mapping[str, str],
) -> SecretStr | None:
    if raw_profile.api_key_env is None:
        return None

    try:
        value = environment[raw_profile.api_key_env]
    except Exception as error:
        raise LLMConfigurationError() from error

    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise LLMConfigurationError()
    return SecretStr(value)


def _resolve_profile(
    name: str,
    raw_profile: RawLLMProfile,
    environment: Mapping[str, str],
) -> ResolvedLLMProfile:
    timeout = raw_profile.timeout_seconds
    return ResolvedLLMProfile(
        name=name,
        base_url=raw_profile.base_url,
        model=raw_profile.model,
        api_key=_resolve_api_key(raw_profile, environment),
        _timeout_seconds=timeout,
        structured_output_mode=raw_profile.structured_output_mode,
    )


def resolve_llm_runtime_config(
    config: RawLLMRuntimeConfig,
    environment: Mapping[str, str],
) -> ResolvedParticipantLLMAssignment:
    selected_names = frozenset(config.assignments.model_dump().values())
    resolved_by_name = {
        name: _resolve_profile(name, raw_profile, environment)
        for name, raw_profile in config.profiles.items()
        if name in selected_names
    }

    return ResolvedParticipantLLMAssignment(
        analyst=resolved_by_name[config.assignments.analyst],
        solution_architect=resolved_by_name[config.assignments.solution_architect],
        risk_reviewer=resolved_by_name[config.assignments.risk_reviewer],
        critic=resolved_by_name[config.assignments.critic],
        coordinator=resolved_by_name[config.assignments.coordinator],
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_llm_runtime_config(
    environment: Mapping[str, str],
) -> RawLLMRuntimeConfig:
    try:
        raw_path = environment["ARB_LLM_CONFIG_PATH"]
        if not isinstance(raw_path, str):
            raise ValueError("invalid path")
        normalized_path = raw_path.strip()
        if not normalized_path:
            raise ValueError("invalid path")

        path = Path(normalized_path)
        if not path.is_file():
            raise ValueError("invalid path")

        text = path.read_bytes().decode("utf-8")
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
        if not isinstance(document, dict):
            raise ValueError("invalid top-level JSON")
        return RawLLMRuntimeConfig.model_validate(document)
    except Exception as error:
        if isinstance(error, LLMConfigurationError):
            raise
        raise LLMConfigurationError() from error
