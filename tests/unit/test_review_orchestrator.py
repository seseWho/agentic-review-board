from collections.abc import Mapping

import pytest

from agentic_review_board.application.orchestrator import ReviewOrchestrator
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    Review,
    ReviewErrorKind,
    ReviewStatus,
    SolutionArchitectStageInput,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.solution_architect import SolutionArchitect


class RecordingLLM:
    def __init__(
        self,
        responses: Mapping[str, Mapping[str, object]],
        events: list[str] | None = None,
        failures: Mapping[str, BaseException] | None = None,
    ) -> None:
        self._responses = responses
        self._failures = failures or {}
        self.events = events if events is not None else []
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        self.events.append(f"invoke:{role}")
        self.calls.append((role, payload))
        failure = self._failures.get(role)
        if failure is not None:
            raise failure
        return self._responses[role]


def analyst_response() -> dict[str, object]:
    return {
        "objective": "Determine whether further evaluation is useful.",
        "facts": [],
        "constraints": [],
        "assumptions": [],
        "missing_information": [],
        "uncertainties": [],
    }


def invalid_analyst_response() -> dict[str, object]:
    return {"objective": 123}


def two_alternative_response() -> dict[str, object]:
    return {
        "alternatives": [
            {
                "id": "ALT-001",
                "name": "Local deployment",
                "description": "Run the capability in the existing local environment.",
                "advantages": ["Keeps operation local."],
                "disadvantages": ["Requires local lifecycle management."],
                "assumptions": ["Suitable local compute is available."],
                "implementation_complexity": "MEDIUM",
                "relevant_constraints": [],
            },
            {
                "id": "ALT-002",
                "name": "Managed deployment",
                "description": "Run the capability in a managed environment.",
                "advantages": ["Reduces local operational work."],
                "disadvantages": ["Introduces an external operational dependency."],
                "assumptions": ["A managed environment is available."],
                "implementation_complexity": "MEDIUM",
                "relevant_constraints": [],
            },
        ]
    }


def invalid_solution_architect_response() -> dict[str, object]:
    return {"alternatives": [{"id": "ALT-001"}]}


def zero_alternative_response() -> dict[str, object]:
    return {
        "alternatives": [],
        "generation_notes": {
            "explanation": "Current evidence is insufficient for useful alternatives.",
            "blocking_missing_information": [],
            "blocking_uncertainties": [],
        },
    }


def create_review() -> Review:
    return Review.create(
        ReviewInput(
            description="Review a proposed technical change.",
            title="Technical change review",
        )
    )


def orchestrator_with(llm: RecordingLLM) -> ReviewOrchestrator:
    return ReviewOrchestrator(Analyst(llm), SolutionArchitect(llm))


def assert_later_stages_pending(review: Review) -> None:
    for identity in (
        StageIdentity.RISK_REVIEWER,
        StageIdentity.CRITIC,
        StageIdentity.COORDINATOR,
    ):
        stage = review.stage(identity)
        assert stage.status is StageStatus.PENDING
        assert stage.inputs is None
        assert stage.output is None
        assert stage.error is None


def test_orchestrator_executes_analyst_then_solution_architect_with_trusted_handoff(
    monkeypatch,
) -> None:
    events: list[str] = []
    original_start_analyst = Review.start_analyst
    original_start_solution_architect = Review.start_solution_architect

    def recording_start_analyst(self: Review) -> Review:
        events.append("record:analyst_inputs")
        return original_start_analyst(self)

    def recording_start_solution_architect(self: Review) -> Review:
        events.append("record:solution_architect_inputs")
        return original_start_solution_architect(self)

    monkeypatch.setattr(Review, "start_analyst", recording_start_analyst)
    monkeypatch.setattr(
        Review,
        "start_solution_architect",
        recording_start_solution_architect,
    )

    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": two_alternative_response(),
        },
        events,
    )
    created = create_review()

    result = orchestrator_with(llm).execute(created)

    assert created.status is ReviewStatus.CREATED
    assert result.status is ReviewStatus.RUNNING
    assert events == [
        "record:analyst_inputs",
        "invoke:analyst",
        "record:solution_architect_inputs",
        "invoke:solution_architect",
    ]
    assert [role for role, _ in llm.calls] == ["analyst", "solution_architect"]

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)

    assert analyst_stage.status is StageStatus.COMPLETED
    assert architect_stage.status is StageStatus.COMPLETED
    assert isinstance(analyst_stage.inputs, AnalystStageInput)
    assert isinstance(architect_stage.inputs, SolutionArchitectStageInput)
    assert analyst_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.problem_analysis is analyst_stage.output
    assert_later_stages_pending(result)


def test_orchestrator_accepts_valid_zero_alternative_result_without_false_failure() -> None:
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": zero_alternative_response(),
        }
    )

    result = orchestrator_with(llm).execute(create_review())

    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert architect_stage.status is StageStatus.COMPLETED
    assert architect_stage.output is not None
    assert architect_stage.output.alternatives == ()
    assert result.status is ReviewStatus.RUNNING


@pytest.mark.parametrize(
    ("responses", "failures", "expected_kind", "expected_message"),
    [
        (
            {
                "analyst": invalid_analyst_response(),
                "solution_architect": two_alternative_response(),
            },
            {},
            ReviewErrorKind.OUTPUT_VALIDATION,
            "Analyst output validation failed",
        ),
        (
            {
                "analyst": analyst_response(),
                "solution_architect": two_alternative_response(),
            },
            {"analyst": RuntimeError("provider secret detail")},
            ReviewErrorKind.EXECUTION,
            "Analyst execution failed",
        ),
    ],
)
def test_analyst_failure_fails_closed_and_stops_dependent_execution(
    responses: Mapping[str, Mapping[str, object]],
    failures: Mapping[str, BaseException],
    expected_kind: ReviewErrorKind,
    expected_message: str,
) -> None:
    llm = RecordingLLM(responses, failures=failures)

    result = orchestrator_with(llm).execute(create_review())

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert result.status is ReviewStatus.INCOMPLETE
    assert analyst_stage.status is StageStatus.FAILED
    assert isinstance(analyst_stage.inputs, AnalystStageInput)
    assert analyst_stage.inputs.review_input is result.review_input
    assert analyst_stage.output is None
    assert analyst_stage.error is not None
    assert analyst_stage.error.kind is expected_kind
    assert analyst_stage.error.message == expected_message
    assert "provider secret detail" not in analyst_stage.error.message
    assert architect_stage.status is StageStatus.PENDING
    assert [role for role, _ in llm.calls] == ["analyst"]
    assert_later_stages_pending(result)


@pytest.mark.parametrize(
    ("architect_response", "failure", "expected_kind", "expected_message"),
    [
        (
            invalid_solution_architect_response(),
            None,
            ReviewErrorKind.OUTPUT_VALIDATION,
            "Solution Architect output validation failed",
        ),
        (
            two_alternative_response(),
            RuntimeError("provider secret detail"),
            ReviewErrorKind.EXECUTION,
            "Solution Architect execution failed",
        ),
    ],
)
def test_solution_architect_failure_preserves_completed_analyst_work(
    architect_response: Mapping[str, object],
    failure: BaseException | None,
    expected_kind: ReviewErrorKind,
    expected_message: str,
) -> None:
    failures = {} if failure is None else {"solution_architect": failure}
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": architect_response,
        },
        failures=failures,
    )

    result = orchestrator_with(llm).execute(create_review())

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert result.status is ReviewStatus.INCOMPLETE
    assert analyst_stage.status is StageStatus.COMPLETED
    assert analyst_stage.output is not None
    assert architect_stage.status is StageStatus.FAILED
    assert isinstance(architect_stage.inputs, SolutionArchitectStageInput)
    assert architect_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.problem_analysis is analyst_stage.output
    assert architect_stage.output is None
    assert architect_stage.error is not None
    assert architect_stage.error.kind is expected_kind
    assert architect_stage.error.message == expected_message
    assert "provider secret detail" not in architect_stage.error.message
    assert [role for role, _ in llm.calls] == ["analyst", "solution_architect"]
    assert_later_stages_pending(result)


def test_orchestrator_does_not_convert_lifecycle_errors_outside_participant_boundary() -> None:
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": two_alternative_response(),
        }
    )
    already_running = create_review().start()

    with pytest.raises(ValueError, match="only a created review can start"):
        orchestrator_with(llm).execute(already_running)

    assert llm.calls == []


@pytest.mark.parametrize("control_signal", [KeyboardInterrupt(), SystemExit()])
def test_orchestrator_does_not_swallow_base_exception_control_signals(
    control_signal: BaseException,
) -> None:
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": two_alternative_response(),
        },
        failures={"analyst": control_signal},
    )

    with pytest.raises(type(control_signal)):
        orchestrator_with(llm).execute(create_review())
