from __future__ import annotations

import os

import pytest

from agentic_review_board.infrastructure.llm.config import load_llm_runtime_config
from agentic_review_board.infrastructure.llm.smoke import verify_selected_profiles


@pytest.mark.live_llm
def test_selected_llm_profiles_accept_canonical_smoke_contract() -> None:
    config = load_llm_runtime_config(os.environ)

    verified_names = verify_selected_profiles(
        config,
        os.environ,
        report_profile=lambda name: print(f"live LLM profile: {name}"),
    )

    assert verified_names
