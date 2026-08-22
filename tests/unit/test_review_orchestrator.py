from collections.abc import Mapping

import pytest

from agentic_review_board.application.orchestrator import ReviewOrchestrator
from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    Review,
    ReviewErrorKind,
    ReviewStatus,
    RiskReviewerStageInput,
    SolutionArchitectStageInput,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.risk_reviewer import (
    RiskReviewer,
    RiskReviewerOutputError,
)
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


def risk_response() -> dict[str, object]:
    return {
        "risks": [
            {
                "id": "RISK-001",
                "category": "operational",
                "description": "Local lifecycle management may create operational burden.",
                "affected_scope": {
                    "kind": "ALTERNATIVES",
                    "alternative_ids": ["ALT-001"],
                },
                "severity": "MEDIUM",
                "basis": [
                    {
                        "source": "SOLUTION_ALTERNATIVE",
                        "alternative_id": "ALT-001",
                        "characteristic": "DESCRIPTION",
                        "value": "Run the capability in the existing local environment.",
                    }
                ],
                "mitigation": "Define explicit local lifecycle ownership.",
                "residual_uncertainty": "Actual support effort is not yet measured.",
            }
        ],
        "overall_observations": ["Risk remains qualitative at this stage."],
    }


def zero_risk_response() -> dict[str, object]:
    return {
        "risks": [],
        "overall_observations": [
            "No material risk is justified by the current trusted inputs."
        ],
    }


def invalid_risk_reviewer_response() -> dict[str, object]:
    return {
        "risks": [
            {
                "id": "RISK-INVALID",
                "description": "Generated risk depends on a nonexistent alternative.",
                "affected_scope": {
                    "kind": "ALTERNATIVES",
                    "alternative_ids": ["ALT-999"],
                },
                "severity": "MEDIUM",
                "basis": [
                    {
                        "source": "SOLUTION_ALTERNATIVE",
                        "alternative_id": "ALT-999",
                        "characteristic": "DESCRIPTION",
                        "value": "Nonexistent alternative.",
                    }
                ],
            }
        ],
        "overall_observations": [],
    }


def successful_responses() -> dict[str, Mapping[str, object]]:
    return {
        "analyst": analyst_response(),
        "solution_architect": two_alternative_response(),
        "risk_reviewer": risk_response(),
    }


def create_review() -> Review:
    return Review.create(
        ReviewInput(
            description="Review a proposed technical change.",
            title="Technical change review",
        )
    )


def create_named_review(description: str) -> Review:
    return Review.create(ReviewInput(description=description))


def orchestrator_with(llm: RecordingLLM) -> ReviewOrchestrator:
    return ReviewOrchestrator(
        Analyst(llm),
        SolutionArchitect(llm),
        RiskReviewer(llm),
    )


def assert_downstream_stages_pending(
    review: Review,
    identities: tuple[StageIdentity, ...],
) -> None:
    for identity in identities:
        stage = review.stage(identity)
        assert stage.status is StageStatus.PENDING
        assert stage.inputs is None
        assert stage.output is None
        assert stage.error is None


def assert_later_stages_pending(review: Review) -> None:
    assert_downstream_stages_pending(
        review,
        (
            StageIdentity.RISK_REVIEWER,
            StageIdentity.CRITIC,
            StageIdentity.COORDINATOR,
        ),
    )


def assert_final_stages_pending(review: Review) -> None:
    assert_downstream_stages_pending(
        review,
        (StageIdentity.CRITIC, StageIdentity.COORDINATOR),
    )


def assert_fresh_created_review(review: Review) -> None:
    assert review.status is ReviewStatus.CREATED
    assert len(review.stages) == 5
    assert len({id(stage) for stage in review.stages}) == 5
    for stage in review.stages:
        assert stage.status is StageStatus.PENDING
        assert stage.inputs is None
        assert stage.output is None
        assert stage.error is None


def test_orchestrator_executes_three_roles_in_order_with_exact_trusted_handoffs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_start_analyst = Review.start_analyst
    original_start_solution_architect = Review.start_solution_architect
    original_start_risk_reviewer = Review.start_risk_reviewer

    def recording_start_analyst(self: Review) -> Review:
        events.append("record:analyst_inputs")
        return original_start_analyst(self)

    def recording_start_solution_architect(self: Review) -> Review:
        events.append("record:solution_architect_inputs")
        return original_start_solution_architect(self)

    def recording_start_risk_reviewer(self: Review) -> Review:
        events.append("record:risk_reviewer_inputs")
        return original_start_risk_reviewer(self)

    monkeypatch.setattr(Review, "start_analyst", recording_start_analyst)
    monkeypatch.setattr(
        Review,
        "start_solution_architect",
        recording_start_solution_architect,
    )
    monkeypatch.setattr(
        Review,
        "start_risk_reviewer",
        recording_start_risk_reviewer,
    )

    llm = RecordingLLM(successful_responses(), events)
    created = create_review()

    result = orchestrator_with(llm).execute(created)

    assert created.status is ReviewStatus.CREATED
    assert result.status is ReviewStatus.RUNNING
    assert events == [
        "record:analyst_inputs",
        "invoke:analyst",
        "record:solution_architect_inputs",
        "invoke:solution_architect",
        "record:risk_reviewer_inputs",
        "invoke:risk_reviewer",
    ]
    assert [role for role, _ in llm.calls] == [
        "analyst",
        "solution_architect",
        "risk_reviewer",
    ]

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    reviewer_stage = result.stage(StageIdentity.RISK_REVIEWER)

    assert analyst_stage.status is StageStatus.COMPLETED
    assert architect_stage.status is StageStatus.COMPLETED
    assert reviewer_stage.status is StageStatus.COMPLETED
    assert isinstance(analyst_stage.inputs, AnalystStageInput)
    assert isinstance(architect_stage.inputs, SolutionArchitectStageInput)
    assert isinstance(reviewer_stage.inputs, RiskReviewerStageInput)
    assert analyst_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.problem_analysis is analyst_stage.output
    assert reviewer_stage.inputs.review_input is result.review_input
    assert reviewer_stage.inputs.problem_analysis is analyst_stage.output
    assert reviewer_stage.inputs.solution_alternatives is architect_stage.output
    assert isinstance(reviewer_stage.output, RiskAssessment)

    risk_payload = llm.calls[2][1]
    assert risk_payload == {
        "review_input": result.review_input.model_dump(mode="json"),
        "problem_analysis": analyst_stage.output.model_dump(mode="json"),
        "solution_alternatives": architect_stage.output.model_dump(mode="json"),
    }
    assert_final_stages_pending(result)


@pytest.mark.parametrize(
    ("architect_response", "reviewer_response"),
    [
        (two_alternative_response(), zero_risk_response()),
        (zero_alternative_response(), zero_risk_response()),
    ],
)
def test_orchestrator_accepts_zero_risk_and_zero_alternative_results(
    architect_response: Mapping[str, object],
    reviewer_response: Mapping[str, object],
) -> None:
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": architect_response,
            "risk_reviewer": reviewer_response,
        }
    )

    result = orchestrator_with(llm).execute(create_review())

    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    reviewer_stage = result.stage(StageIdentity.RISK_REVIEWER)
    assert architect_stage.status is StageStatus.COMPLETED
    assert reviewer_stage.status is StageStatus.COMPLETED
    assert isinstance(architect_stage.output, SolutionAlternatives)
    assert isinstance(reviewer_stage.output, RiskAssessment)
    assert reviewer_stage.output.risks == ()
    assert result.status is ReviewStatus.RUNNING
    assert_final_stages_pending(result)


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


def test_invalid_risk_reviewer_generated_output_raises_dedicated_participant_error() -> None:
    current_input = create_review().review_input
    analysis = ProblemAnalysis.model_validate(analyst_response())
    alternatives = SolutionAlternatives.model_validate(two_alternative_response())
    llm = RecordingLLM({"risk_reviewer": invalid_risk_reviewer_response()})

    with pytest.raises(RiskReviewerOutputError):
        RiskReviewer(llm).assess(current_input, analysis, alternatives)


def test_risk_reviewer_output_validation_failure_is_mapped_fail_closed() -> None:
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": two_alternative_response(),
            "risk_reviewer": invalid_risk_reviewer_response(),
        }
    )

    result = orchestrator_with(llm).execute(create_review())

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    reviewer_stage = result.stage(StageIdentity.RISK_REVIEWER)

    assert result.status is ReviewStatus.INCOMPLETE
    assert analyst_stage.status is StageStatus.COMPLETED
    assert architect_stage.status is StageStatus.COMPLETED
    assert reviewer_stage.status is StageStatus.FAILED
    assert isinstance(reviewer_stage.inputs, RiskReviewerStageInput)
    assert reviewer_stage.inputs.review_input is result.review_input
    assert reviewer_stage.inputs.problem_analysis is analyst_stage.output
    assert reviewer_stage.inputs.solution_alternatives is architect_stage.output
    assert reviewer_stage.output is None
    assert reviewer_stage.error is not None
    assert reviewer_stage.error.kind is ReviewErrorKind.OUTPUT_VALIDATION
    assert reviewer_stage.error.message == "Risk Reviewer output validation failed"
    assert [role for role, _ in llm.calls] == [
        "analyst",
        "solution_architect",
        "risk_reviewer",
    ]
    assert_final_stages_pending(result)


def test_risk_reviewer_execution_failure_is_mapped_without_raw_exception_text() -> None:
    llm = RecordingLLM(
        successful_responses(),
        failures={"risk_reviewer": RuntimeError("provider secret risk detail")},
    )

    result = orchestrator_with(llm).execute(create_review())

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    reviewer_stage = result.stage(StageIdentity.RISK_REVIEWER)

    assert result.status is ReviewStatus.INCOMPLETE
    assert analyst_stage.status is StageStatus.COMPLETED
    assert architect_stage.status is StageStatus.COMPLETED
    assert reviewer_stage.status is StageStatus.FAILED
    assert isinstance(reviewer_stage.inputs, RiskReviewerStageInput)
    assert reviewer_stage.inputs.review_input is result.review_input
    assert reviewer_stage.inputs.problem_analysis is analyst_stage.output
    assert reviewer_stage.inputs.solution_alternatives is architect_stage.output
    assert reviewer_stage.output is None
    assert reviewer_stage.error is not None
    assert reviewer_stage.error.kind is ReviewErrorKind.EXECUTION
    assert reviewer_stage.error.message == "Risk Reviewer execution failed"
    assert "provider secret risk detail" not in reviewer_stage.error.message
    assert_final_stages_pending(result)


def test_orchestrator_does_not_convert_lifecycle_errors_outside_participant_boundary() -> None:
    llm = RecordingLLM(successful_responses())
    already_running = create_review().start()

    with pytest.raises(ValueError, match="only a created review can start"):
        orchestrator_with(llm).execute(already_running)

    assert llm.calls == []


def test_risk_reviewer_stage_invariant_failure_outside_participant_call_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = RecordingLLM(successful_responses())

    def invalid_start_risk_reviewer(self: Review) -> Review:
        raise ValueError("Risk Reviewer stage invariant failed")

    monkeypatch.setattr(Review, "start_risk_reviewer", invalid_start_risk_reviewer)

    with pytest.raises(ValueError, match="Risk Reviewer stage invariant failed"):
        orchestrator_with(llm).execute(create_review())

    assert [role for role, _ in llm.calls] == ["analyst", "solution_architect"]


@pytest.mark.parametrize("control_signal", [KeyboardInterrupt(), SystemExit()])
def test_orchestrator_does_not_swallow_base_exception_control_signals(
    control_signal: BaseException,
) -> None:
    llm = RecordingLLM(
        successful_responses(),
        failures={"risk_reviewer": control_signal},
    )

    with pytest.raises(type(control_signal)):
        orchestrator_with(llm).execute(create_review())

    assert [role for role, _ in llm.calls] == [
        "analyst",
        "solution_architect",
        "risk_reviewer",
    ]


def test_reused_orchestrator_keeps_sequential_successful_reviews_isolated() -> None:
    llm = RecordingLLM(successful_responses())
    orchestrator = orchestrator_with(llm)
    first_created = create_named_review("First independent review.")
    second_created = create_named_review("Second independent review.")

    assert_fresh_created_review(first_created)
    assert_fresh_created_review(second_created)
    assert first_created.review_input is not second_created.review_input
    for first_stage, second_stage in zip(first_created.stages, second_created.stages, strict=True):
        assert first_stage is not second_stage

    first_result = orchestrator.execute(first_created)

    assert_fresh_created_review(second_created)
    second_result = orchestrator.execute(second_created)

    first_analyst = first_result.stage(StageIdentity.ANALYST)
    second_analyst = second_result.stage(StageIdentity.ANALYST)
    first_architect = first_result.stage(StageIdentity.SOLUTION_ARCHITECT)
    second_architect = second_result.stage(StageIdentity.SOLUTION_ARCHITECT)
    first_reviewer = first_result.stage(StageIdentity.RISK_REVIEWER)
    second_reviewer = second_result.stage(StageIdentity.RISK_REVIEWER)

    assert first_result.review_input is first_created.review_input
    assert second_result.review_input is second_created.review_input
    assert first_result.review_input is not second_result.review_input
    assert first_analyst.output is not None
    assert second_analyst.output is not None
    assert first_analyst.output is not second_analyst.output
    assert first_architect.output is not None
    assert second_architect.output is not None
    assert first_architect.output is not second_architect.output
    assert isinstance(first_architect.inputs, SolutionArchitectStageInput)
    assert isinstance(second_architect.inputs, SolutionArchitectStageInput)
    assert first_architect.inputs.problem_analysis is first_analyst.output
    assert second_architect.inputs.problem_analysis is second_analyst.output
    assert second_architect.inputs.problem_analysis is not first_analyst.output
    assert isinstance(first_reviewer.inputs, RiskReviewerStageInput)
    assert isinstance(second_reviewer.inputs, RiskReviewerStageInput)
    assert first_reviewer.inputs.problem_analysis is first_analyst.output
    assert second_reviewer.inputs.problem_analysis is second_analyst.output
    assert first_reviewer.inputs.solution_alternatives is first_architect.output
    assert second_reviewer.inputs.solution_alternatives is second_architect.output
    assert first_reviewer.output is not None
    assert second_reviewer.output is not None
    assert first_reviewer.output is not second_reviewer.output
    assert first_result.status is ReviewStatus.RUNNING
    assert second_result.status is ReviewStatus.RUNNING
    assert_final_stages_pending(first_result)
    assert_final_stages_pending(second_result)


def test_risk_failure_does_not_contaminate_next_fresh_review() -> None:
    llm = RecordingLLM(
        successful_responses(),
        failures={"risk_reviewer": RuntimeError("first review provider detail")},
    )
    orchestrator = orchestrator_with(llm)
    first_created = create_named_review("Review expected to fail at risk stage.")

    first_result = orchestrator.execute(first_created)
    first_analyst = first_result.stage(StageIdentity.ANALYST)
    first_architect = first_result.stage(StageIdentity.SOLUTION_ARCHITECT)
    first_reviewer = first_result.stage(StageIdentity.RISK_REVIEWER)
    assert first_result.status is ReviewStatus.INCOMPLETE
    assert first_analyst.status is StageStatus.COMPLETED
    assert first_architect.status is StageStatus.COMPLETED
    assert first_reviewer.status is StageStatus.FAILED
    assert first_reviewer.output is None
    assert first_reviewer.error is not None

    llm._failures = {}
    second_created = create_named_review("Fresh review after a risk failure.")

    assert_fresh_created_review(second_created)
    for second_stage, first_stage in zip(second_created.stages, first_result.stages, strict=True):
        assert second_stage is not first_stage

    second_result = orchestrator.execute(second_created)
    second_analyst = second_result.stage(StageIdentity.ANALYST)
    second_architect = second_result.stage(StageIdentity.SOLUTION_ARCHITECT)
    second_reviewer = second_result.stage(StageIdentity.RISK_REVIEWER)

    assert second_result.status is ReviewStatus.RUNNING
    assert second_result.review_input is second_created.review_input
    assert second_result.review_input is not first_result.review_input
    assert second_analyst.status is StageStatus.COMPLETED
    assert second_architect.status is StageStatus.COMPLETED
    assert second_reviewer.status is StageStatus.COMPLETED
    assert isinstance(second_reviewer.inputs, RiskReviewerStageInput)
    assert second_reviewer.inputs.review_input is second_result.review_input
    assert second_reviewer.inputs.problem_analysis is second_analyst.output
    assert second_reviewer.inputs.solution_alternatives is second_architect.output
    assert second_reviewer.output is not None
    assert second_reviewer.error is None
    assert second_reviewer.output is not first_reviewer.output
    assert_final_stages_pending(second_result)
