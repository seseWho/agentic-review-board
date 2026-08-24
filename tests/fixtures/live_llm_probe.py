from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.live_llm
def test_live_llm_probe_runs_only_after_explicit_authorization() -> None:
    Path(os.environ["ARB_LIVE_LLM_PROBE_PATH"]).write_text(
        "executed",
        encoding="utf-8",
    )
