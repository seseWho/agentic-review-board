from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import NoReturn

import httpx

from agentic_review_board.infrastructure.llm.config import (
    ResolvedLLMProfile,
    StructuredOutputMode,
)
from agentic_review_board.infrastructure.llm.dynamic_schemas import (
    build_critic_payload_snapshot,
    build_critic_request_output_schema,
    strict_json_schema_document,
)
from agentic_review_board.infrastructure.llm.errors import (
    LLMHTTPStatusError,
    LLMPayloadSerializationError,
    LLMRequestTimeoutError,
    LLMResponseEnvelopeError,
    LLMStructuredContentError,
    LLMTransportError,
)
from agentic_review_board.infrastructure.llm.prompts import (
    get_role_prompt_definition,
)

_UNTRUSTED_PAYLOAD_BEGIN = "UNTRUSTED_PAYLOAD_JSON_BEGIN"
_UNTRUSTED_PAYLOAD_END = "UNTRUSTED_PAYLOAD_JSON_END"
_UNTRUSTED_REQUEST_SCHEMA_BEGIN = "UNTRUSTED_REQUEST_SCHEMA_JSON_BEGIN"
_UNTRUSTED_REQUEST_SCHEMA_END = "UNTRUSTED_REQUEST_SCHEMA_JSON_END"
_OUTPUT_SCHEMA_LABEL = "OUTPUT_JSON_SCHEMA:"
_OUTPUT_INSTANCE_INSTRUCTION = (
    "The schema above is a constraint, not the requested output. "
    "Do not copy or return the schema, its metadata, or its properties definition. "
    "Return one concrete data instance that conforms to it."
)


def _strict_json_schema(schema: Mapping[str, object]) -> dict[str, object]:
    return strict_json_schema_document(schema)


def _reject_non_json_constant(_value: str) -> NoReturn:
    raise ValueError("non-JSON numeric constant")


@dataclass(frozen=True, slots=True)
class OpenAICompatibleLLMAdapter:
    profile: ResolvedLLMProfile
    client: httpx.Client
    output_observer: Callable[[str, Mapping[str, object]], None] | None = None

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        definition = get_role_prompt_definition(role)
        request_output_schema = None
        if definition.role.value == "critic":
            critic_snapshot = build_critic_payload_snapshot(payload)
            serialized_payload = critic_snapshot.serialized_payload
            request_output_schema = build_critic_request_output_schema(critic_snapshot)
        else:
            serialized_payload = self._serialize_payload(payload)

        system_content = (
            f"{definition.semantic_instruction}\n\n"
            f"{_OUTPUT_SCHEMA_LABEL}\n{definition.serialized_schema}\n\n"
            f"{_OUTPUT_INSTANCE_INSTRUCTION}"
        )
        user_content = (
            f"{_UNTRUSTED_PAYLOAD_BEGIN}\n"
            f"{serialized_payload}\n"
            f"{_UNTRUSTED_PAYLOAD_END}"
        )
        if request_output_schema is not None:
            user_content = (
                f"{user_content}\n\n"
                f"{_UNTRUSTED_REQUEST_SCHEMA_BEGIN}\n"
                f"{request_output_schema.serialized}\n"
                f"{_UNTRUSTED_REQUEST_SCHEMA_END}"
            )
        request_body: dict[str, object] = {
            "model": self.profile.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "n": 1,
        }
        if self.profile.max_output_tokens is not None:
            request_body["max_tokens"] = self.profile.max_output_tokens
        if self.profile.temperature is not None:
            request_body["temperature"] = self.profile.temperature
        if self.profile.seed is not None:
            request_body["seed"] = self.profile.seed
        if self.profile.structured_output_mode is StructuredOutputMode.JSON_OBJECT:
            request_body["response_format"] = {"type": "json_object"}
        elif self.profile.structured_output_mode is StructuredOutputMode.JSON_SCHEMA:
            provider_schema = (
                request_output_schema.new_document()
                if request_output_schema is not None
                else _strict_json_schema(definition.output_model.model_json_schema())
            )
            request_body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{role}_output",
                    "strict": True,
                    "schema": provider_schema,
                },
            }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.profile.api_key is not None:
            headers["Authorization"] = (
                f"Bearer {self.profile.api_key.get_secret_value()}"
            )

        try:
            response = self.client.post(
                f"{self.profile.base_url}/chat/completions",
                headers=headers,
                json=request_body,
                timeout=self.profile.timeout,
            )
        except httpx.TimeoutException as error:
            raise LLMRequestTimeoutError() from error
        except httpx.RequestError as error:
            raise LLMTransportError() from error

        if not 200 <= response.status_code < 300:
            raise LLMHTTPStatusError()

        content = self._extract_content(response)
        structured = self._parse_structured_content(content)
        if self.output_observer is not None:
            self.output_observer(role, structured)
        return structured

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        try:
            envelope = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise LLMResponseEnvelopeError() from error

        if not isinstance(envelope, dict):
            raise LLMResponseEnvelopeError()

        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise LLMResponseEnvelopeError()

        choice = choices[0]
        if not isinstance(choice, dict):
            raise LLMResponseEnvelopeError()

        message = choice.get("message")
        if not isinstance(message, dict):
            raise LLMResponseEnvelopeError()

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseEnvelopeError()
        return content

    @staticmethod
    def _parse_structured_content(content: str) -> dict[str, object]:
        try:
            parsed = json.loads(content, parse_constant=_reject_non_json_constant)
        except ValueError as error:
            raise LLMStructuredContentError() from error

        if not isinstance(parsed, dict):
            raise LLMStructuredContentError()
        return parsed

    @staticmethod
    def _serialize_payload(payload: Mapping[str, object]) -> str:
        try:
            payload_snapshot = dict(payload)
            return json.dumps(
                payload_snapshot,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except Exception as error:
            raise LLMPayloadSerializationError() from error
