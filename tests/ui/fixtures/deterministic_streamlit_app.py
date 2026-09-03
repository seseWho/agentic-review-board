"""Test-only Streamlit composition over real deterministic participants."""

import streamlit as st

from agentic_review_board.ui import render_app
from tests.ui.fixtures.review_scenarios import (
    ScenarioExecutor,
    ScenarioKind,
    scenario_executor,
)

SCENARIO_KEY = "_arb_test_scenario"
EXECUTOR_KEY = "_arb_test_executor"
EXECUTOR_KIND_KEY = "_arb_test_executor_kind"
DELAY_KEY = "_arb_test_transition_delay_seconds"

scenario = ScenarioKind(st.session_state.get(SCENARIO_KEY, ScenarioKind.COMPLETE))
transition_delay_seconds = float(st.session_state.get(DELAY_KEY, 0.0))
executor_configuration = (scenario, transition_delay_seconds)
if (
    EXECUTOR_KEY not in st.session_state
    or st.session_state.get(EXECUTOR_KIND_KEY) != executor_configuration
):
    st.session_state[EXECUTOR_KEY] = scenario_executor(
        scenario,
        transition_delay_seconds=transition_delay_seconds,
    )
    st.session_state[EXECUTOR_KIND_KEY] = executor_configuration

executor = st.session_state[EXECUTOR_KEY]
if not isinstance(executor, ScenarioExecutor):
    raise TypeError("deterministic scenario executor is invalid")

render_app(executor)
