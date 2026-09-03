from time import monotonic

import pytest
from streamlit.testing.v1 import AppTest

from agentic_review_board.domain.execution import ReviewStatus, StageIdentity, StageStatus
from tests.ui.fixtures.review_scenarios import ScenarioExecutor, ScenarioKind

from .test_streamlit_app import (
    APP_PATH,
    EXECUTOR_KEY,
    SCENARIO_KEY,
    all_rendered_text,
)

DELAY_KEY = "_arb_test_transition_delay_seconds"
TRANSITION_DELAY_SECONDS = 0.005


def delayed_walkthrough(kind: ScenarioKind) -> tuple[AppTest, ScenarioExecutor, float]:
    at = AppTest.from_file(str(APP_PATH), default_timeout=10).run()
    at.session_state[SCENARIO_KEY] = kind
    at.session_state[DELAY_KEY] = TRANSITION_DELAY_SECONDS
    at.run()
    at.text_area(key="arb_description").set_value(f"Delayed {kind.value} walkthrough.")

    started_at = monotonic()
    at.button(key="arb_start").click().run()
    elapsed = monotonic() - started_at

    executor = at.session_state[EXECUTOR_KEY]
    assert isinstance(executor, ScenarioExecutor)
    return at, executor, elapsed


@pytest.mark.parametrize(
    ("kind", "snapshot_count", "terminal_status"),
    [
        (ScenarioKind.COMPLETE, 11, ReviewStatus.COMPLETED),
        (
            ScenarioKind.CRITIC_OUTPUT_VALIDATION_FAILURE,
            9,
            ReviewStatus.INCOMPLETE,
        ),
    ],
)
def test_delayed_deterministic_acceptance_walkthrough(
    kind: ScenarioKind,
    snapshot_count: int,
    terminal_status: ReviewStatus,
) -> None:
    at, executor, elapsed = delayed_walkthrough(kind)
    state = at.session_state["arb_review_ui_state"]

    assert elapsed >= TRANSITION_DELAY_SECONDS * snapshot_count
    assert executor.execution_count == 1
    assert len(executor.observations[0]) == snapshot_count
    assert state.review is not None
    assert state.review.status is terminal_status
    assert executor.observations[0][-1] is state.review

    if terminal_status is ReviewStatus.COMPLETED:
        assert len(executor.calls) == 5
        assert all(stage.status is StageStatus.COMPLETED for stage in state.review.stages)
        assert "Final result" in all_rendered_text(at)
    else:
        assert len(executor.calls) == 4
        assert state.review.stage(StageIdentity.CRITIC).status is StageStatus.FAILED
        assert state.review.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING
        assert "Final result" not in all_rendered_text(at)
