from __future__ import annotations

import ast
from pathlib import Path

SMOKE_MODULE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "agentic_review_board"
    / "infrastructure"
    / "llm"
    / "smoke.py"
)
FORBIDDEN_IMPORT_PREFIXES = (
    "agentic_review_board.application.orchestrator",
    "agentic_review_board.domain.execution",
    "agentic_review_board.participants",
    "statistics",
    "time",
)
FORBIDDEN_IDENTIFIERS = {
    "ConfiguredReviewRuntime",
    "Review",
    "ReviewOrchestrator",
    "duration",
    "execute",
    "latency",
    "quality",
    "reasoning",
    "score",
    "timer",
}


def imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def referenced_identifiers(tree: ast.AST) -> set[str]:
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }


def test_smoke_runner_has_no_full_review_or_quality_measurement_capability() -> None:
    assert SMOKE_MODULE.is_file()
    tree = ast.parse(SMOKE_MODULE.read_text(encoding="utf-8"), filename=str(SMOKE_MODULE))

    forbidden_imports = {
        module
        for module in imported_modules(tree)
        if any(
            module == prefix or module.startswith(f"{prefix}.")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        )
    }
    forbidden_identifiers = referenced_identifiers(tree) & FORBIDDEN_IDENTIFIERS

    assert forbidden_imports == set()
    assert forbidden_identifiers == set()
