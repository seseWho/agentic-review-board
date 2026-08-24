from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import pytest

PRODUCTION_PACKAGE = (
    Path(__file__).resolve().parents[2] / "src" / "agentic_review_board"
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PREFIXES = (
    "httpx",
    "agentic_review_board.infrastructure",
)
EXTERNAL_PROTOCOL_MARKERS = (
    "/chat/completions",
    "Authorization",
    "Bearer ",
    "choices",
)
FORBIDDEN_RUNTIME_IMPORTS = {
    "anthropic",
    "boto3",
    "chromadb",
    "faiss",
    "fastapi",
    "flask",
    "google.generativeai",
    "gradio",
    "langchain",
    "litellm",
    "llama_index",
    "ollama",
    "openai",
    "requests",
    "sqlalchemy",
    "streamlit",
}
FORBIDDEN_EXECUTABLE_TOKENS = {
    "browse",
    "browsing",
    "fallback",
    "persistence",
    "rag",
    "registry",
    "repository",
    "retrieval",
    "retries",
    "retry",
    "router",
    "routing",
    "tool",
    "tools",
    "ui",
}


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


def string_literals(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return tuple(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def definition_tokens(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = (
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return {
        token.lower()
        for name in names
        for token in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", name)
    }


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


def test_production_never_imports_test_modules() -> None:
    violations = [
        f"{path.relative_to(PRODUCTION_PACKAGE)}: {module}"
        for path in sorted(PRODUCTION_PACKAGE.rglob("*.py"))
        for module in imported_modules(path)
        if module == "tests" or module.startswith("tests.")
    ]

    assert violations == []


@pytest.mark.parametrize("marker", EXTERNAL_PROTOCOL_MARKERS)
def test_only_infrastructure_owns_external_protocol_markers(marker: str) -> None:
    infrastructure_root = PRODUCTION_PACKAGE / "infrastructure"
    violations = [
        str(path.relative_to(PRODUCTION_PACKAGE))
        for path in sorted(PRODUCTION_PACKAGE.rglob("*.py"))
        if not path.is_relative_to(infrastructure_root)
        if any(marker in literal for literal in string_literals(path))
    ]

    assert violations == []


def test_runtime_dependencies_remain_exactly_pydantic_and_httpx() -> None:
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = pyproject["project"]["dependencies"]
    names = {
        re.split(r"[<>=!~\[]", dependency, maxsplit=1)[0].strip().lower()
        for dependency in dependencies
    }

    assert names == {"pydantic", "httpx"}


def test_production_imports_no_provider_sdk_or_out_of_scope_framework() -> None:
    violations = [
        f"{path.relative_to(PRODUCTION_PACKAGE)}: {module}"
        for path in sorted(PRODUCTION_PACKAGE.rglob("*.py"))
        for module in imported_modules(path)
        if any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in FORBIDDEN_RUNTIME_IMPORTS
        )
    ]

    assert violations == []


def test_production_defines_no_out_of_scope_executable_capability() -> None:
    violations = [
        f"{path.relative_to(PRODUCTION_PACKAGE)}: {sorted(tokens)}"
        for path in sorted(PRODUCTION_PACKAGE.rglob("*.py"))
        if (tokens := definition_tokens(path) & FORBIDDEN_EXECUTABLE_TOKENS)
    ]

    assert violations == []
