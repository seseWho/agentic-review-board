from __future__ import annotations

import os

import pytest

_LIVE_MARKER = "live_llm"
_LIVE_OPTION = "--run-live-llm"
_LIVE_ENVIRONMENT_VARIABLE = "ARB_RUN_LIVE_LLM"
_CONFIG_PATH_VARIABLE = "ARB_LLM_CONFIG_PATH"
_SKIP_REASON = "live LLM smoke not explicitly authorized"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        _LIVE_OPTION,
        action="store_true",
        default=False,
        help="authorize explicitly selected live LLM smoke tests",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    option_enabled = bool(config.getoption(_LIVE_OPTION))
    environment_enabled = os.environ.get(_LIVE_ENVIRONMENT_VARIABLE) == "1"
    config_path_present = _CONFIG_PATH_VARIABLE in os.environ
    if option_enabled and environment_enabled and config_path_present:
        return

    skip = pytest.mark.skip(reason=_SKIP_REASON)
    for item in items:
        if _LIVE_MARKER in item.keywords:
            item.add_marker(skip)
