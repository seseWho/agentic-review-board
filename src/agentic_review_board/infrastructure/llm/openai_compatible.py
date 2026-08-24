from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from agentic_review_board.infrastructure.llm.config import (
    ResolvedLLMProfile,
    StructuredOutputMode,
)
from agentic_review_board.infrastructure.llm.errors import (
    LLMPayloadSerializationError,
    LLMResponseEnvelopeError,
)
from agentic_review_board.infrastructure.llm.prompts import (
    get_role_prompt_definition,
)

_UNTRUSTED_PAYLOAD_BEGIN = "UNTRUSTED_PAYLOAD_JSON_BEGIN"
_UNTRUSTED_PAYLOAD_END = "UNTRUSTED_PAYLOAD_JSON_END"
_OUTPUT_SCHEMA_LABEL = "OUTPUT_JSON_SCHEMA:"


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

        self.client.post(
            f"{self.profile.base_url}/chat/completions",
            headers=headers,
            json=request_body,
            timeout=self.profile.timeout,
        )

        # Phase 6 replaces this fail-closed boundary with strict envelope and
        # structured-content processing.
        raise LLMResponseEnvelopeError()

    @staticmethod
    def _serialize_payload(payload: Mapping[str, object]) -> str:
        try:
            payload_snapshot = dict(payload)
            return json.dumps(
                payload_snapshot,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except Exception as error:
            raise LLMPayloadSerializationError() from error
