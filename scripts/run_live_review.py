from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from agentic_review_board.domain.execution import Review, ReviewStatus
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.infrastructure.llm.composition import ConfiguredReviewRuntime
from agentic_review_board.infrastructure.llm.config import load_llm_runtime_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one live five-participant review and save its JSON artifact."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--raw-output-dir", type=Path)
    return parser.parse_args()


def load_review_input(path: Path) -> ReviewInput:
    document = json.loads(path.read_text(encoding="utf-8"))
    return ReviewInput.model_validate(document)


def main() -> int:
    args = parse_args()
    environment = dict(os.environ)
    environment["ARB_LLM_CONFIG_PATH"] = str(args.config.resolve())

    config = load_llm_runtime_config(environment)
    review = Review.create(load_review_input(args.input))

    def observe_output(role: str, output: object) -> None:
        if args.raw_output_dir is None:
            return
        args.raw_output_dir.mkdir(parents=True, exist_ok=True)
        path = args.raw_output_dir / f"{role}.json"
        path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    started = time.perf_counter()
    with ConfiguredReviewRuntime.from_config(
        config,
        environment,
        output_observer=observe_output if args.raw_output_dir is not None else None,
    ) as runtime:
        print(f"profiles: {dict(runtime.participant_profile_names)}", flush=True)
        result = runtime.execute(review)
    elapsed = time.perf_counter() - started

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"review status: {result.status.value}", flush=True)
    for stage in result.stages:
        suffix = f" ({stage.error.kind.value}: {stage.error.message})" if stage.error else ""
        print(f"{stage.identity.value}: {stage.status.value}{suffix}", flush=True)
    print(f"elapsed seconds: {elapsed:.2f}", flush=True)
    print(f"artifact: {args.output.resolve()}", flush=True)

    return 0 if result.status is ReviewStatus.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
