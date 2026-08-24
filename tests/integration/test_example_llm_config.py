from __future__ import annotations

from pathlib import Path

from agentic_review_board.infrastructure.llm.config import (
    load_llm_runtime_config,
    resolve_llm_runtime_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = PROJECT_ROOT / "config" / "llm.example.json"


def test_example_config_loads_and_resolves_mixed_selected_profiles_safely() -> None:
    secret_marker = "synthetic-example-secret-not-in-file"
    environment = {
        "ARB_LLM_CONFIG_PATH": str(EXAMPLE_CONFIG),
        "REMOTE_LLM_API_KEY": secret_marker,
    }

    config = load_llm_runtime_config(environment)
    assignment = resolve_llm_runtime_config(config, environment)

    assert config.assignments.model_dump() == {
        "analyst": "local",
        "solution_architect": "remote",
        "risk_reviewer": "local",
        "critic": "remote",
        "coordinator": "remote",
    }
    assert assignment.analyst is assignment.risk_reviewer
    assert assignment.solution_architect is assignment.critic
    assert assignment.critic is assignment.coordinator
    assert assignment.analyst is not assignment.solution_architect
    assert {assignment.analyst.name, assignment.solution_architect.name} == {
        "local",
        "remote",
    }

    committed_text = EXAMPLE_CONFIG.read_text(encoding="utf-8")
    assert "REMOTE_LLM_API_KEY" in committed_text
    assert secret_marker not in committed_text
    assert secret_marker not in repr(config)
    assert secret_marker not in repr(assignment)
