"""Production composition root for the local pedagogical Streamlit UI."""

from __future__ import annotations

import os

from agentic_review_board.application.observation import ReviewObserver
from agentic_review_board.domain.execution import Review
from agentic_review_board.infrastructure.llm.composition import (
    ConfiguredReviewRuntime,
)
from agentic_review_board.infrastructure.llm.config import load_llm_runtime_config
from agentic_review_board.ui import render_app


def execute_review(
    created_review: Review,
    *,
    observer: ReviewObserver,
) -> Review:
    """Run exactly one Review with a fresh, deterministically closed runtime."""

    environment = dict(os.environ)
    config = load_llm_runtime_config(environment)
    with ConfiguredReviewRuntime.from_config(config, environment) as runtime:
        return runtime.execute(created_review, observer=observer)


def main() -> None:
    """Render the inert UI shell; runtime construction occurs only after Start."""

    render_app(execute_review)


if __name__ == "__main__":
    main()
