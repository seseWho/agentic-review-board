from __future__ import annotations

import ast
from pathlib import Path

import pytest

PRODUCTION_PACKAGE = (
    Path(__file__).resolve().parents[2] / "src" / "agentic_review_board"
)
FORBIDDEN_PREFIXES = (
    "httpx",
    "agentic_review_board.infrastructure",
)


def imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return tuple(modules)


def is_forbidden(module: str) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_PREFIXES
    )


@pytest.mark.parametrize("layer", ["domain", "application", "participants"])
def test_core_layers_do_not_import_httpx_or_infrastructure(layer: str) -> None:
    layer_root = PRODUCTION_PACKAGE / layer
    violations = [
        f"{path.relative_to(PRODUCTION_PACKAGE)}: {module}"
        for path in sorted(layer_root.rglob("*.py"))
        for module in imported_modules(path)
        if is_forbidden(module)
    ]

    assert violations == []
