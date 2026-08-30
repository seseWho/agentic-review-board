from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

import httpx

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.infrastructure.llm.config import (
    load_llm_runtime_config,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)
from agentic_review_board.participants.solution_architect import SolutionArchitect


class CapturedOutputPort(LLMPort):
    def __init__(self, output: Mapping[str, object]) -> None:
        self._output = output

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return self._output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe one live Solution Architect response.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--review-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    environment = dict(os.environ)
    environment["ARB_LLM_CONFIG_PATH"] = str(args.config.resolve())
    config = load_llm_runtime_config(environment)
    profile = resolve_llm_runtime_config(config, environment).solution_architect

    artifact = json.loads(args.review_artifact.read_text(encoding="utf-8"))
    review_input = ReviewInput.model_validate(artifact["review_input"])
    problem_analysis = ProblemAnalysis.model_validate(artifact["stages"][0]["output"])
    payload = {
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
    }

    with httpx.Client(trust_env=True) as client:
        raw = OpenAICompatibleLLMAdapter(profile=profile, client=client).generate_structured(
            role="solution_architect",
            payload=payload,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        SolutionArchitect(CapturedOutputPort(raw)).propose(review_input, problem_analysis)
    except Exception as error:
        print(f"validation error: {error!r}")
        if error.__cause__ is not None:
            print(f"validation cause: {error.__cause__}")
        print(f"raw artifact: {args.output.resolve()}")
        return 1

    print("validation: passed")
    print(f"raw artifact: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
