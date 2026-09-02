from collections.abc import Mapping

import httpx

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.infrastructure.llm.config import (
    RawLLMRuntimeConfig,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)


def invoke_through_unchanged_port(port: LLMPort) -> Mapping[str, object]:
    return port.generate_structured(
        role="analyst",
        payload={
            "description": "structural contract marker",
            "title": None,
            "objective": None,
            "constraints": [],
            "context": [],
            "stated_facts": [],
        },
    )


def test_production_adapter_structurally_satisfies_unchanged_llm_port() -> None:
    config = RawLLMRuntimeConfig.model_validate(
        {
            "profiles": {
                "contract": {
                    "base_url": "https://contract.example.test/v1",
                    "model": "contract-model",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "PROMPT_ONLY",
                }
            },
            "assignments": {
                "analyst": "contract",
                "solution_architect": "contract",
                "risk_reviewer": "contract",
                "critic": "contract",
                "coordinator": "contract",
            },
        }
    )
    profile = resolve_llm_runtime_config(config, {}).analyst

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"result":"ok"}'}}]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAICompatibleLLMAdapter(profile=profile, client=client)
        result = invoke_through_unchanged_port(adapter)

    assert LLMPort not in type(adapter).__mro__
    assert result == {"result": "ok"}
