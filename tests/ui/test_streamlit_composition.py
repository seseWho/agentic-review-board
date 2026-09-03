from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from streamlit.testing.v1 import AppTest

from agentic_review_board.domain.execution import Review
from agentic_review_board.domain.review import ReviewInput

ROOT_ENTRY = Path(__file__).parents[2] / "streamlit_app.py"


def created_review() -> Review:
    return Review.create(ReviewInput(description="Composition boundary Review."))


class RecordingRuntime:
    def __init__(self, result: Review, *, failure: Exception | None = None) -> None:
        self.result = result
        self.failure = failure
        self.enter_count = 0
        self.exit_count = 0
        self.execute_calls: list[tuple[Review, object]] = []

    def __enter__(self) -> RecordingRuntime:
        self.enter_count += 1
        return self

    def __exit__(self, *args: object) -> None:
        self.exit_count += 1

    def execute(self, review: Review, *, observer: object) -> Review:
        self.execute_calls.append((review, observer))
        if self.failure is not None:
            raise self.failure
        return self.result


def imported_entry() -> ModuleType:
    import streamlit_app

    return streamlit_app


@pytest.mark.parametrize("fails", [False, True])
def test_root_executor_loads_current_environment_forwards_once_and_closes(
    monkeypatch: pytest.MonkeyPatch,
    fails: bool,
) -> None:
    entry = imported_entry()
    created = created_review()
    returned = created.start()
    injected = RuntimeError("runtime failure") if fails else None
    runtime = RecordingRuntime(returned, failure=injected)
    config = object()
    loaded_environments: list[Mapping[str, str]] = []
    runtime_factory_calls: list[tuple[object, Mapping[str, str]]] = []
    observer = cast(object, lambda review: None)

    monkeypatch.setenv("ARB_LLM_CONFIG_PATH", "local-test-config.json")
    monkeypatch.setenv("ARB_COMPOSITION_COPY_MARKER", "copied")

    def load(environment: Mapping[str, str]) -> object:
        loaded_environments.append(environment)
        return config

    def create_runtime(
        supplied_config: object,
        environment: Mapping[str, str],
    ) -> RecordingRuntime:
        runtime_factory_calls.append((supplied_config, environment))
        return runtime

    monkeypatch.setattr(entry, "load_llm_runtime_config", load)
    monkeypatch.setattr(entry.ConfiguredReviewRuntime, "from_config", create_runtime)

    if fails:
        with pytest.raises(RuntimeError, match="runtime failure"):
            entry.execute_review(created, observer=observer)
    else:
        assert entry.execute_review(created, observer=observer) is returned

    assert len(loaded_environments) == 1
    copied_environment = loaded_environments[0]
    assert copied_environment is not os.environ
    assert copied_environment["ARB_LLM_CONFIG_PATH"] == "local-test-config.json"
    assert copied_environment["ARB_COMPOSITION_COPY_MARKER"] == "copied"
    assert runtime_factory_calls == [(config, copied_environment)]
    assert runtime.execute_calls == [(created, observer)]
    assert runtime.enter_count == 1
    assert runtime.exit_count == 1


def test_production_import_and_page_load_are_inert_until_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_review_board.infrastructure.llm import composition, config

    configuration_calls: list[Mapping[str, str]] = []
    runtime_calls: list[tuple[object, Mapping[str, str]]] = []

    def unexpected_load(environment: Mapping[str, str]) -> object:
        configuration_calls.append(environment)
        return object()

    def unexpected_runtime(
        supplied_config: object,
        environment: Mapping[str, str],
    ) -> object:
        runtime_calls.append((supplied_config, environment))
        return object()

    monkeypatch.setattr(config, "load_llm_runtime_config", unexpected_load)
    monkeypatch.setattr(
        composition.ConfiguredReviewRuntime,
        "from_config",
        unexpected_runtime,
    )

    at = AppTest.from_file(str(ROOT_ENTRY), default_timeout=10).run()

    assert not at.exception
    assert at.button(key="arb_start").label == "Start Review"
    assert configuration_calls == []
    assert runtime_calls == []
