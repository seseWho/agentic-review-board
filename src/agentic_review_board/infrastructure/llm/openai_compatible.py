from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NoReturn

import httpx

from agentic_review_board.infrastructure.llm.config import (
    ResolvedLLMProfile,
    StructuredOutputMode,
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
_OUTPUT_SCHEMA_LABEL = "OUTPUT_JSON_SCHEMA:"


def _reject_non_json_constant(_value: str) -> NoReturn:
    raise ValueError("non-JSON numeric constant")


@dataclass(frozen=True, slots=True)
class OpenAICompatibleLLMAdapter:
    profile: ResolvedLLMProfile
    client: httpx.Client

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        definition = get_role_prompt_definition(role)
        serialized_payload = self._serialize_payload(payload)

        system_content = (
            f"{definition.semantic_instruction}\n\n"
            f"{_OUTPUT_SCHEMA_LABEL}\n{definition.serialized_schema}"
        )
        user_content = (
            f"{_UNTRUSTED_PAYLOAD_BEGIN}\n"
            f"{serialized_payload}\n"
            f"{_UNTRUSTED_PAYLOAD_END}"
        )
        request_body: dict[str, object] = {
            "model": self.profile.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "n": 1,
        }
        if self.profile.structured_output_mode is StructuredOutputMode.JSON_OBJECT:
            request_body["response_format"] = {"type": "json_object"}

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
        return self._parse_structured_content(content)

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
