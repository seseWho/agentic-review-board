from pathlib import Path

from streamlit.testing.v1 import AppTest

from agentic_review_board.domain.execution import (
    CANONICAL_STAGE_ORDER,
    Review,
    ReviewStatus,
    StageIdentity,
    StageStatus,
)
from tests.ui.fixtures.review_scenarios import ScenarioExecutor, ScenarioKind

APP_PATH = Path(__file__).parent / "fixtures" / "deterministic_streamlit_app.py"
SCENARIO_KEY = "_arb_test_scenario"
EXECUTOR_KEY = "_arb_test_executor"


def app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=10).run()


def visible_text(at: AppTest) -> str:
    collections = (
        at.title,
        at.header,
        at.subheader,
        at.markdown,
        at.caption,
        at.info,
        at.warning,
        at.error,
        at.success,
    )
    return "\n".join(
        str(element.value)
        for collection in collections
        for element in collection
    )


def all_rendered_text(at: AppTest) -> str:
    values = [visible_text(at)]
    values.extend(str(element.value) for element in at.code)
    values.extend(str(element.value) for element in at.json)
    values.extend(str(element.label) for element in at.expander)
    return "\n".join(values)


def executor(at: AppTest) -> ScenarioExecutor:
    value = at.session_state[EXECUTOR_KEY]
    assert isinstance(value, ScenarioExecutor)
    return value


def submit_complete_form(at: AppTest) -> AppTest:
    at.text_input(key="arb_title").set_value("  UI title  ")
    at.text_area(key="arb_description").set_value("  UI description  ")
    at.text_area(key="arb_objective").set_value("  UI objective  ")
    at.text_area(key="arb_constraints").set_value(
        "Use current local capacity.\n  second constraint  "
    )
    at.text_area(key="arb_context").set_value("First context\nSecond context")
    at.text_area(key="arb_stated_facts").set_value(
        "The workflow contains five agents."
    )
    return at.button(key="arb_start").click().run()


def test_initial_form_is_explicit_complete_and_inert() -> None:
    at = app()
    text = visible_text(at)

    assert "Agentic Review Board" in text
    assert at.text_input(key="arb_title").label == "Title (optional)"
    assert at.text_area(key="arb_description").label == "Description (required)"
    assert at.text_area(key="arb_objective").label == "Objective (optional)"
    assert at.text_area(key="arb_constraints").label == "Constraints (optional, one per line)"
    assert at.text_area(key="arb_context").label == "Context (optional, one per line)"
    assert at.text_area(key="arb_stated_facts").label == "Stated facts (optional, one per line)"
    assert at.button(key="arb_start").label == "Start Review"
    assert executor(at).calls == ()
    assert all(name in text for name in (
        "Analyst",
        "Solution Architect",
        "Risk Reviewer",
        "Critic",
        "Coordinator",
    ))
    assert "Not started" in text

    at.text_area(key="arb_description").set_value("Editing is not submission.").run()
    assert executor(at).execution_count == 0


def test_invalid_input_never_starts_agents() -> None:
    at = app()

    at.button(key="arb_start").click().run()

    assert executor(at).calls == ()
    assert "Description is required" in visible_text(at)


def test_explicit_start_preserves_input_and_executes_once_across_reruns() -> None:
    at = submit_complete_form(app())
    scenario_executor_value = executor(at)

    assert scenario_executor_value.execution_count == 1
    assert len(scenario_executor_value.calls) == 5
    analyst_role, analyst_payload = scenario_executor_value.calls[0]
    assert analyst_role == "analyst"
    assert analyst_payload == {
        "description": "  UI description  ",
        "title": "  UI title  ",
        "objective": "  UI objective  ",
        "constraints": (
            "Use current local capacity.",
            "  second constraint  ",
        ),
        "context": ("First context", "Second context"),
        "stated_facts": ("The workflow contains five agents.",),
    }
    assert at.text_input == []
    assert all(button.key != "arb_start" for button in at.button)
    at.run()
    assert executor(at).execution_count == 1
    assert len(executor(at).calls) == 5


def test_complete_process_uses_canonical_agent_order_and_trusted_states() -> None:
    at = submit_complete_form(app())
    text = visible_text(at)

    stage_headings = [
        str(element.value).removeprefix("### ")
        for element in at.markdown
        if str(element.value).startswith("### ")
    ]
    assert stage_headings == [
        "Analyst",
        "Solution Architect",
        "Risk Reviewer",
        "Critic",
        "Coordinator",
    ]
    positions = [
        text.index(name)
        for name in (
            "Analyst",
            "Solution Architect",
            "Risk Reviewer",
            "Critic",
            "Coordinator",
        )
    ]
    assert positions == sorted(positions)
    assert text.count("Completed — trusted output") >= 5
    assert "Review completed" in text
    assert "ProblemAnalysis" in text
    assert "SolutionAlternatives" in text
    assert "RiskAssessment" in text
    assert "CriticalReview" in text
    assert "FinalReview" in text
    state = at.session_state["arb_review_ui_state"]
    assert state.review is not None
    assert isinstance(state.review, Review)
    assert state.review.status.value == "COMPLETED"


def test_process_is_driven_by_the_exact_sequential_observer_history() -> None:
    at = submit_complete_form(app())
    scenario_executor_value = executor(at)

    assert len(scenario_executor_value.observations) == 1
    observed = scenario_executor_value.observations[0]
    assert len(observed) == 11
    assert observed[0].status is ReviewStatus.RUNNING
    for index, identity in enumerate(CANONICAL_STAGE_ORDER):
        started = observed[1 + (index * 2)]
        finished = observed[2 + (index * 2)]
        assert started.stage(identity).status is StageStatus.RUNNING
        assert sum(
            stage.status is StageStatus.RUNNING for stage in started.stages
        ) == 1
        assert finished.stage(identity).status is StageStatus.COMPLETED
        if index < len(CANONICAL_STAGE_ORDER) - 1:
            next_started = observed[3 + (index * 2)]
            assert next_started.stage(identity).status is StageStatus.COMPLETED
            assert next_started.stage(CANONICAL_STAGE_ORDER[index + 1]).status is StageStatus.RUNNING

    text = visible_text(at)
    assert "Sequential dependency:" in text
    assert "Structure the problem" in text
    assert "ReviewInput" in text
    assert "ProblemAnalysis" in text


def test_all_role_artifacts_and_evidence_states_are_human_readable() -> None:
    at = submit_complete_form(app())
    text = all_rendered_text(at)

    for expected in (
        "FACT-001",
        "stated_facts",
        "ASM-001",
        "The PoC remains single-session.",
        "UNC-001",
        "Operational effort is not measured.",
        "ALT-001",
        "Local deployment",
        "Keeps operation local.",
        "Requires local lifecycle management.",
        "Suitable local capacity is available.",
        "MEDIUM",
        "RISK-001",
        "Assign explicit local lifecycle ownership.",
        "Actual support effort is not measured.",
        "CONTRA-001",
        "CRIT-001",
        "The operating assumption lacks measured support.",
        "HIGH",
        "UNVERIFIED",
        "PROPOSED",
    ):
        assert expected in text

    for section in (
        "Facts",
        "Assumptions",
        "Missing information",
        "Alternatives",
        "Risks",
        "Mitigation",
        "Contradictions",
        "Unresolved issues",
    ):
        assert section in text
    assert "No items" in text
    assert "Trusted technical detail (JSON)" in text
    assert "EVIDENCED" not in text


def test_each_agent_detail_shows_declared_and_actual_trusted_inputs() -> None:
    at = submit_complete_form(app())
    expectations = {
        StageIdentity.ANALYST: ("Analyst", ("ReviewInput",)),
        StageIdentity.SOLUTION_ARCHITECT: (
            "Solution Architect",
            ("ReviewInput", "ProblemAnalysis"),
        ),
        StageIdentity.RISK_REVIEWER: (
            "Risk Reviewer",
            ("ReviewInput", "ProblemAnalysis", "SolutionAlternatives"),
        ),
        StageIdentity.CRITIC: (
            "Critic",
            (
                "ReviewInput",
                "ProblemAnalysis",
                "SolutionAlternatives",
                "RiskAssessment",
            ),
        ),
        StageIdentity.COORDINATOR: (
            "Coordinator",
            (
                "ReviewInput",
                "ProblemAnalysis",
                "SolutionAlternatives",
                "RiskAssessment",
                "CriticalReview",
            ),
        ),
    }

    for identity, (name, artifact_labels) in expectations.items():
        at.selectbox(key="arb_stage_select").set_value(identity).run()
        text = all_rendered_text(at)
        assert f"Agent detail: {name}" in text
        assert "Input artifact types" in text
        assert "Inspect trusted stage inputs" in text
        assert all(label in text for label in artifact_labels)


def test_final_result_is_distinct_advisory_and_complete() -> None:
    at = submit_complete_form(app())
    text = all_rendered_text(at)

    assert "Final result" in text
    assert "RECOMMENDED" in text
    assert text.index("ALT-001") < text.index("ALT-002")
    assert "Preferred alternative" in text
    assert "Principal risks" in text
    assert "Unresolved questions" in text
    assert "Criticism dispositions" in text
    assert "CRIT-001" in text
    assert "REFLECTED" in text
    assert "NEXT_VALIDATION_STEP" in text
    assert "QUESTION-001" in text
    assert "What operational effort will the selected approach require?" in text
    assert "Next validation step (advisory)" in text
    assert "Qualitative confidence" in text
    assert "This review supports, but does not replace, human decision-making." in text
    assert not any(
        label in text for label in ("Accept recommendation", "Deploy", "Send", "Apply")
    )


def test_fixture_can_select_another_real_agent_scenario() -> None:
    at = app()
    at.session_state[SCENARIO_KEY] = ScenarioKind.INSUFFICIENT_EVIDENCE
    at.run()
    at.text_area(key="arb_description").set_value("Insufficient evidence Review.")
    at.button(key="arb_start").click().run()

    assert len(executor(at).calls) == 5
    text = all_rendered_text(at)
    assert "INSUFFICIENT_EVIDENCE" in text
    assert "Review completed" in text
    assert "Preferred alternative" in text
    assert "Not provided" in text
    assert "Current evidence does not support a preferred alternative." in text
    assert "Final result" in text
    assert "Process" in text


def _submit_scenario(kind: ScenarioKind) -> AppTest:
    at = app()
    at.session_state[SCENARIO_KEY] = kind
    at.run()
    at.text_area(key="arb_description").set_value(f"{kind.value} Review.")
    return at.button(key="arb_start").click().run()


def test_output_validation_failure_preserves_upstream_and_blocks_coordinator() -> None:
    at = _submit_scenario(ScenarioKind.CRITIC_OUTPUT_VALIDATION_FAILURE)
    text = all_rendered_text(at)
    state = at.session_state["arb_review_ui_state"]

    assert state.review is not None
    assert state.review.status is ReviewStatus.INCOMPLETE
    assert all(
        state.review.stage(identity).status is StageStatus.COMPLETED
        for identity in CANONICAL_STAGE_ORDER[:3]
    )
    assert state.review.stage(StageIdentity.CRITIC).status is StageStatus.FAILED
    assert state.review.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING
    assert "OUTPUT_VALIDATION" in text
    assert "Critic output validation failed" in text
    assert "Not executed because the mandatory upstream Critic stage failed." in text
    assert "ProblemAnalysis" in text
    assert "RiskAssessment" in text
    assert "Final result" not in text


def test_execution_failure_is_safe_and_distinct() -> None:
    at = _submit_scenario(ScenarioKind.CRITIC_EXECUTION_FAILURE)
    text = all_rendered_text(at)

    assert "EXECUTION" in text
    assert "Critic execution failed" in text
    assert "OUTPUT_VALIDATION" not in text
    assert "provider-secret-marker" not in text
    assert "Final result" not in text


def test_startup_and_application_faults_are_sanitized_without_fabricated_stage_failure() -> None:
    startup = _submit_scenario(ScenarioKind.STARTUP_FAILURE)
    startup_text = all_rendered_text(startup)
    startup_state = startup.session_state["arb_review_ui_state"]
    assert startup_state.review is None
    assert "The review could not be started" in startup_text
    assert "startup-secret-marker" not in startup_text
    assert "Review running" not in startup_text
    assert "Failed â€” no trusted output" not in startup_text

    application = _submit_scenario(ScenarioKind.APPLICATION_FAILURE)
    application_text = all_rendered_text(application)
    application_state = application.session_state["arb_review_ui_state"]
    assert application_state.review is not None
    assert application_state.review.status is ReviewStatus.RUNNING
    assert all(stage.status is StageStatus.PENDING for stage in application_state.review.stages)
    assert "could not complete this run safely" in application_text
    assert "application-secret-marker" not in application_text
    assert "Failed â€” no trusted output" not in application_text


def test_new_review_clears_complete_and_incomplete_session_state() -> None:
    for first_kind in (
        ScenarioKind.COMPLETE,
        ScenarioKind.CRITIC_OUTPUT_VALIDATION_FAILURE,
    ):
        at = _submit_scenario(first_kind)
        at.selectbox(key="arb_stage_select").set_value(StageIdentity.RISK_REVIEWER).run()
        assert "RISK-001" in all_rendered_text(at)

        at.session_state[SCENARIO_KEY] = ScenarioKind.COMPLETE
        at.button(key="arb_new_review").click().run()
        assert at.session_state["arb_review_ui_state"].review is None
        assert at.text_input(key="arb_title").value == ""
        assert all(
            at.text_area(key=key).value == ""
            for key in (
                "arb_description",
                "arb_objective",
                "arb_constraints",
                "arb_context",
                "arb_stated_facts",
            )
        )
        assert "RISK-001" not in all_rendered_text(at)

        at.text_area(key="arb_description").set_value("Fresh isolated Review.")
        at.button(key="arb_start").click().run()
        second_state = at.session_state["arb_review_ui_state"]
        assert second_state.review is not None
        assert second_state.review.review_input.description == "Fresh isolated Review."
        assert first_kind.value not in second_state.review.review_input.description


def test_rendered_content_excludes_private_and_sensitive_surfaces() -> None:
    for kind in (
        ScenarioKind.COMPLETE,
        ScenarioKind.CRITIC_EXECUTION_FAILURE,
        ScenarioKind.STARTUP_FAILURE,
        ScenarioKind.APPLICATION_FAILURE,
    ):
        text = all_rendered_text(_submit_scenario(kind)).lower()
        for forbidden in (
            "chain-of-thought",
            "private reasoning",
            "system prompt",
            "raw output",
            "raw response",
            "authorization:",
            "bearer ",
            "api key",
            "secret-marker",
            "accept recommendation",
            "execute recommendation",
        ):
            assert forbidden not in text
