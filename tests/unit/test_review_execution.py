import pytest
from pydantic import ValidationError

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    CoordinatorStageInput,
    CriticStageInput,
    Review,
    ReviewError,
    ReviewErrorKind,
    ReviewStatus,
    RiskReviewerStageInput,
    SolutionArchitectStageInput,
    StageExecution,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.final_reviews import FinalReview
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives


def valid_review_input() -> ReviewInput:
    return ReviewInput(
        description="Review a proposed technical change.",
        title="Technical change review",
        constraints=("Keep the initial review small.",),
    )


def valid_problem_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        objective="Determine whether the proposal merits further evaluation.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )


def valid_solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives.model_validate(
        {
            "alternatives": [],
            "generation_notes": {
                "explanation": "The available evidence is insufficient for useful alternatives.",
                "blocking_missing_information": [],
                "blocking_uncertainties": [],
            },
        }
    )


def valid_risk_assessment() -> RiskAssessment:
    return RiskAssessment(risks=(), overall_observations=())


def execution_error() -> ReviewError:
    return ReviewError(
        kind=ReviewErrorKind.EXECUTION,
        message="Analyst execution failed",
    )


def pending_later_stages() -> tuple[StageExecution, StageExecution, StageExecution]:
    return (
        StageExecution(identity=StageIdentity.RISK_REVIEWER, status=StageStatus.PENDING),
        StageExecution(identity=StageIdentity.CRITIC, status=StageStatus.PENDING),
        StageExecution(identity=StageIdentity.COORDINATOR, status=StageStatus.PENDING),
    )


def pending_final_stages() -> tuple[StageExecution, StageExecution]:
    return (
        StageExecution(identity=StageIdentity.CRITIC, status=StageStatus.PENDING),
        StageExecution(identity=StageIdentity.COORDINATOR, status=StageStatus.PENDING),
    )


def completed_upstream_stages(
    review_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
) -> tuple[StageExecution, StageExecution]:
    analyst = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=AnalystStageInput(review_input=review_input),
        output=analysis,
    )
    architect = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=SolutionArchitectStageInput(
            review_input=review_input,
            problem_analysis=analysis,
        ),
        output=alternatives,
    )
    return analyst, architect


def risk_inputs(
    review_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
) -> RiskReviewerStageInput:
    return RiskReviewerStageInput(
        review_input=review_input,
        problem_analysis=analysis,
        solution_alternatives=alternatives,
    )


def test_execution_vocabularies_are_closed_and_exact() -> None:
    assert [identity.value for identity in StageIdentity] == [
        "ANALYST",
        "SOLUTION_ARCHITECT",
        "RISK_REVIEWER",
        "CRITIC",
        "COORDINATOR",
    ]
    assert {status.value for status in StageStatus} == {
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
    }
    assert {status.value for status in ReviewStatus} == {
        "CREATED",
        "RUNNING",
        "INCOMPLETE",
        "COMPLETED",
    }
    assert {kind.value for kind in ReviewErrorKind} == {
        "OUTPUT_VALIDATION",
        "EXECUTION",
    }


def test_execution_state_contracts_are_closed_and_frozen() -> None:
    contract_types = (
        ReviewError,
        AnalystStageInput,
        SolutionArchitectStageInput,
        RiskReviewerStageInput,
        StageExecution,
        Review,
    )

    for contract_type in contract_types:
        assert contract_type.model_config.get("extra") == "forbid"
        assert contract_type.model_config.get("frozen") is True

    review_input = valid_review_input()
    problem_analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    instances_and_mutations = (
        (
            ReviewError(kind=ReviewErrorKind.EXECUTION, message="Analyst execution failed"),
            "message",
            "Changed",
        ),
        (AnalystStageInput(review_input=review_input), "review_input", valid_review_input()),
        (
            SolutionArchitectStageInput(
                review_input=review_input,
                problem_analysis=problem_analysis,
            ),
            "problem_analysis",
            valid_problem_analysis(),
        ),
        (
            risk_inputs(review_input, problem_analysis, alternatives),
            "solution_alternatives",
            valid_solution_alternatives(),
        ),
        (
            StageExecution(identity=StageIdentity.ANALYST, status=StageStatus.PENDING),
            "status",
            StageStatus.RUNNING,
        ),
        (Review.create(review_input), "status", ReviewStatus.RUNNING),
    )

    for instance, field_name, replacement in instances_and_mutations:
        with pytest.raises(ValidationError):
            setattr(instance, field_name, replacement)


def test_review_error_requires_strict_non_empty_message() -> None:
    error = ReviewError(
        kind=ReviewErrorKind.OUTPUT_VALIDATION,
        message="Analyst output validation failed",
    )

    assert error.message == "Analyst output validation failed"

    with pytest.raises(ValidationError):
        ReviewError(kind=ReviewErrorKind.EXECUTION, message="   ")
    with pytest.raises(ValidationError):
        ReviewError.model_validate(
            {
                "kind": ReviewErrorKind.EXECUTION,
                "message": 123,
            }
        )


def test_review_create_builds_fresh_canonical_created_state() -> None:
    review_input = valid_review_input()

    review = Review.create(review_input)

    assert review.review_input is review_input
    assert review.status is ReviewStatus.CREATED
    assert isinstance(review.stages, tuple)
    assert [stage.identity for stage in review.stages] == [
        StageIdentity.ANALYST,
        StageIdentity.SOLUTION_ARCHITECT,
        StageIdentity.RISK_REVIEWER,
        StageIdentity.CRITIC,
        StageIdentity.COORDINATOR,
    ]
    assert len({stage.identity for stage in review.stages}) == 5
    assert len({id(stage) for stage in review.stages}) == 5

    for stage in review.stages:
        assert stage.status is StageStatus.PENDING
        assert stage.inputs is None
        assert stage.output is None
        assert stage.error is None


def test_analyst_stage_accepts_exact_valid_local_lifecycle_shapes() -> None:
    review_input = valid_review_input()
    inputs = AnalystStageInput(review_input=review_input)
    analysis = valid_problem_analysis()

    pending = StageExecution(identity=StageIdentity.ANALYST, status=StageStatus.PENDING)
    running = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.RUNNING,
        inputs=inputs,
    )
    completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=inputs,
        output=analysis,
    )
    failed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.FAILED,
        inputs=inputs,
        error=execution_error(),
    )

    assert pending.inputs is None
    assert running.inputs is inputs
    assert completed.output is analysis
    assert failed.error is not None


def test_solution_architect_stage_accepts_exact_valid_local_lifecycle_shapes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    alternatives = valid_solution_alternatives()

    pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    running = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=inputs,
    )
    completed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=inputs,
        output=alternatives,
    )
    failed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.FAILED,
        inputs=inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Solution Architect execution failed",
        ),
    )

    assert pending.inputs is None
    assert running.inputs is inputs
    assert completed.output is alternatives
    assert failed.error is not None


def test_risk_reviewer_stage_accepts_exact_valid_local_lifecycle_shapes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    inputs = risk_inputs(review_input, analysis, alternatives)
    assessment = valid_risk_assessment()

    pending = StageExecution(identity=StageIdentity.RISK_REVIEWER, status=StageStatus.PENDING)
    running = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=inputs,
    )
    completed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.COMPLETED,
        inputs=inputs,
        output=assessment,
    )
    failed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.FAILED,
        inputs=inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Risk Reviewer execution failed",
        ),
    )

    assert pending.inputs is None
    assert running.inputs is inputs
    assert completed.output is assessment
    assert failed.error is not None


def test_risk_reviewer_completed_stage_requires_risk_assessment_output() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    inputs = risk_inputs(review_input, analysis, alternatives)

    with pytest.raises(ValidationError):
        StageExecution(
            identity=StageIdentity.RISK_REVIEWER,
            status=StageStatus.COMPLETED,
            inputs=inputs,
            output=alternatives,
        )


@pytest.mark.parametrize(
    ("status", "inputs", "output", "error"),
    [
        (StageStatus.PENDING, AnalystStageInput(review_input=valid_review_input()), None, None),
        (StageStatus.PENDING, None, valid_problem_analysis(), None),
        (StageStatus.PENDING, None, None, execution_error()),
        (StageStatus.RUNNING, None, None, None),
        (
            StageStatus.RUNNING,
            AnalystStageInput(review_input=valid_review_input()),
            valid_problem_analysis(),
            None,
        ),
        (
            StageStatus.RUNNING,
            AnalystStageInput(review_input=valid_review_input()),
            None,
            execution_error(),
        ),
        (
            StageStatus.COMPLETED,
            AnalystStageInput(review_input=valid_review_input()),
            None,
            None,
        ),
        (
            StageStatus.COMPLETED,
            AnalystStageInput(review_input=valid_review_input()),
            valid_problem_analysis(),
            execution_error(),
        ),
        (
            StageStatus.FAILED,
            AnalystStageInput(review_input=valid_review_input()),
            None,
            None,
        ),
        (
            StageStatus.FAILED,
            AnalystStageInput(review_input=valid_review_input()),
            valid_problem_analysis(),
            execution_error(),
        ),
    ],
)
def test_stage_execution_rejects_invalid_lifecycle_shapes(
    status: StageStatus,
    inputs: AnalystStageInput | None,
    output: ProblemAnalysis | None,
    error: ReviewError | None,
) -> None:
    with pytest.raises(ValidationError):
        StageExecution(
            identity=StageIdentity.ANALYST,
            status=status,
            inputs=inputs,
            output=output,
            error=error,
        )


def test_stage_execution_rejects_identity_input_output_mismatches() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )

    invalid_cases = (
        {
            "identity": StageIdentity.ANALYST,
            "status": StageStatus.RUNNING,
            "inputs": architect_inputs,
        },
        {
            "identity": StageIdentity.ANALYST,
            "status": StageStatus.COMPLETED,
            "inputs": analyst_inputs,
            "output": valid_solution_alternatives(),
        },
        {
            "identity": StageIdentity.SOLUTION_ARCHITECT,
            "status": StageStatus.RUNNING,
            "inputs": analyst_inputs,
        },
        {
            "identity": StageIdentity.SOLUTION_ARCHITECT,
            "status": StageStatus.COMPLETED,
            "inputs": architect_inputs,
            "output": analysis,
        },
    )

    for case in invalid_cases:
        with pytest.raises(ValidationError):
            StageExecution.model_validate(case)


@pytest.mark.parametrize(
    "identity",
    [
        StageIdentity.CRITIC,
        StageIdentity.COORDINATOR,
    ],
)
def test_unimplemented_stages_are_pending_only(identity: StageIdentity) -> None:
    pending = StageExecution(identity=identity, status=StageStatus.PENDING)

    assert pending.inputs is None
    assert pending.output is None
    assert pending.error is None

    with pytest.raises(ValidationError):
        StageExecution(
            identity=identity,
            status=StageStatus.RUNNING,
            inputs=AnalystStageInput(review_input=valid_review_input()),
        )


def test_review_accepts_every_valid_slice3_running_prefix() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    analyst_pending = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.PENDING,
    )
    analyst_running = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.RUNNING,
        inputs=analyst_inputs,
    )
    analyst_completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=analyst_inputs,
        output=analysis,
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    architect_running = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=architect_inputs,
    )
    architect_completed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=architect_inputs,
        output=valid_solution_alternatives(),
    )

    valid_prefixes = (
        (analyst_pending, architect_pending),
        (analyst_running, architect_pending),
        (analyst_completed, architect_pending),
        (analyst_completed, architect_running),
        (analyst_completed, architect_completed),
    )

    for analyst_stage, architect_stage in valid_prefixes:
        review = Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(analyst_stage, architect_stage, *pending_later_stages()),
        )
        assert review.status is ReviewStatus.RUNNING


def test_review_accepts_only_the_two_valid_slice3_incomplete_shapes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    analyst_inputs = AnalystStageInput(review_input=review_input)
    analyst_failed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.FAILED,
        inputs=analyst_inputs,
        error=execution_error(),
    )
    analyst_completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=analyst_inputs,
        output=analysis,
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    architect_failed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.FAILED,
        inputs=SolutionArchitectStageInput(
            review_input=review_input,
            problem_analysis=analysis,
        ),
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Solution Architect execution failed",
        ),
    )

    analyst_failure = Review(
        review_input=review_input,
        status=ReviewStatus.INCOMPLETE,
        stages=(analyst_failed, architect_pending, *pending_later_stages()),
    )
    architect_failure = Review(
        review_input=review_input,
        status=ReviewStatus.INCOMPLETE,
        stages=(analyst_completed, architect_failed, *pending_later_stages()),
    )

    assert analyst_failure.status is ReviewStatus.INCOMPLETE
    assert architect_failure.status is ReviewStatus.INCOMPLETE


def test_review_rejects_missing_or_duplicate_canonical_stages() -> None:
    review_input = valid_review_input()
    created = Review.create(review_input)

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.CREATED,
            stages=created.stages[:-1],
        )

    duplicate_analyst = (
        created.stages[0],
        created.stages[0],
        *created.stages[2:],
    )
    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.CREATED,
            stages=duplicate_analyst,
        )


def test_review_rejects_global_lifecycle_and_dependency_inconsistencies() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    analyst_pending = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.PENDING,
    )
    analyst_running = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.RUNNING,
        inputs=analyst_inputs,
    )
    analyst_completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=analyst_inputs,
        output=analysis,
    )
    analyst_failed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.FAILED,
        inputs=analyst_inputs,
        error=execution_error(),
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    architect_running = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=architect_inputs,
    )
    architect_completed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=architect_inputs,
        output=valid_solution_alternatives(),
    )
    architect_failed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.FAILED,
        inputs=architect_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Solution Architect execution failed",
        ),
    )

    invalid_reviews = (
        (ReviewStatus.CREATED, analyst_running, architect_pending),
        (ReviewStatus.RUNNING, analyst_failed, architect_pending),
        (ReviewStatus.RUNNING, analyst_pending, architect_running),
        (ReviewStatus.INCOMPLETE, analyst_pending, architect_pending),
        (ReviewStatus.INCOMPLETE, analyst_failed, architect_failed),
        (ReviewStatus.COMPLETED, analyst_completed, architect_completed),
    )

    for status, analyst_stage, architect_stage in invalid_reviews:
        with pytest.raises(ValidationError):
            Review(
                review_input=review_input,
                status=status,
                stages=(analyst_stage, architect_stage, *pending_later_stages()),
            )


def test_review_preserves_exact_same_execution_provenance() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    analyst_stage = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=AnalystStageInput(review_input=review_input),
        output=analysis,
    )
    architect_stage = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=SolutionArchitectStageInput(
            review_input=review_input,
            problem_analysis=analysis,
        ),
    )

    review = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=(analyst_stage, architect_stage, *pending_later_stages()),
    )

    assert isinstance(analyst_stage.inputs, AnalystStageInput)
    assert isinstance(architect_stage.inputs, SolutionArchitectStageInput)
    assert analyst_stage.inputs.review_input is review.review_input
    assert architect_stage.inputs.review_input is review.review_input
    assert architect_stage.inputs.problem_analysis is analyst_stage.output


def test_review_rejects_equal_but_independent_analyst_review_input_provenance() -> None:
    review_input = valid_review_input()
    equal_but_independent = ReviewInput.model_validate(review_input.model_dump())
    assert equal_but_independent == review_input
    assert equal_but_independent is not review_input

    analyst_stage = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.RUNNING,
        inputs=AnalystStageInput(review_input=equal_but_independent),
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(
                analyst_stage,
                StageExecution(
                    identity=StageIdentity.SOLUTION_ARCHITECT,
                    status=StageStatus.PENDING,
                ),
                *pending_later_stages(),
            ),
        )


def test_review_rejects_equal_but_independent_architect_review_input_provenance() -> None:
    review_input = valid_review_input()
    equal_but_independent = ReviewInput.model_validate(review_input.model_dump())
    analysis = valid_problem_analysis()
    analyst_stage = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=AnalystStageInput(review_input=review_input),
        output=analysis,
    )
    architect_stage = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=SolutionArchitectStageInput(
            review_input=equal_but_independent,
            problem_analysis=analysis,
        ),
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(analyst_stage, architect_stage, *pending_later_stages()),
        )


def test_review_rejects_equal_but_independent_problem_analysis_provenance() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    equal_but_independent = ProblemAnalysis.model_validate(analysis.model_dump())
    assert equal_but_independent == analysis
    assert equal_but_independent is not analysis

    analyst_stage = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=AnalystStageInput(review_input=review_input),
        output=analysis,
    )
    architect_stage = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=SolutionArchitectStageInput(
            review_input=review_input,
            problem_analysis=equal_but_independent,
        ),
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(analyst_stage, architect_stage, *pending_later_stages()),
        )


def test_review_accepts_all_seven_slice4_running_prefixes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    reviewer_inputs = risk_inputs(review_input, analysis, alternatives)

    analyst_pending = StageExecution(identity=StageIdentity.ANALYST, status=StageStatus.PENDING)
    analyst_running = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.RUNNING,
        inputs=analyst_inputs,
    )
    analyst_completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=analyst_inputs,
        output=analysis,
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    architect_running = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=architect_inputs,
    )
    architect_completed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=architect_inputs,
        output=alternatives,
    )
    reviewer_pending = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.PENDING,
    )
    reviewer_running = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=reviewer_inputs,
    )
    reviewer_completed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.COMPLETED,
        inputs=reviewer_inputs,
        output=assessment,
    )

    prefixes = (
        (analyst_pending, architect_pending, reviewer_pending),
        (analyst_running, architect_pending, reviewer_pending),
        (analyst_completed, architect_pending, reviewer_pending),
        (analyst_completed, architect_running, reviewer_pending),
        (analyst_completed, architect_completed, reviewer_pending),
        (analyst_completed, architect_completed, reviewer_running),
        (analyst_completed, architect_completed, reviewer_completed),
    )

    for analyst_stage, architect_stage, reviewer_stage in prefixes:
        review = Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(
                analyst_stage,
                architect_stage,
                reviewer_stage,
                *pending_final_stages(),
            ),
        )
        assert review.status is ReviewStatus.RUNNING


def test_review_accepts_exact_three_slice4_incomplete_shapes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    reviewer_inputs = risk_inputs(review_input, analysis, alternatives)

    analyst_failed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.FAILED,
        inputs=analyst_inputs,
        error=execution_error(),
    )
    analyst_completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=analyst_inputs,
        output=analysis,
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    architect_failed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.FAILED,
        inputs=architect_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Solution Architect execution failed",
        ),
    )
    architect_completed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=architect_inputs,
        output=alternatives,
    )
    reviewer_pending = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.PENDING,
    )
    reviewer_failed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.FAILED,
        inputs=reviewer_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Risk Reviewer execution failed",
        ),
    )

    shapes = (
        (analyst_failed, architect_pending, reviewer_pending),
        (analyst_completed, architect_failed, reviewer_pending),
        (analyst_completed, architect_completed, reviewer_failed),
    )

    for analyst_stage, architect_stage, reviewer_stage in shapes:
        review = Review(
            review_input=review_input,
            status=ReviewStatus.INCOMPLETE,
            stages=(
                analyst_stage,
                architect_stage,
                reviewer_stage,
                *pending_final_stages(),
            ),
        )
        assert review.status is ReviewStatus.INCOMPLETE


def test_review_rejects_slice4_skips_multiple_failures_and_later_execution() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    analyst_completed, architect_completed = completed_upstream_stages(
        review_input,
        analysis,
        alternatives,
    )
    reviewer_running = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=risk_inputs(review_input, analysis, alternatives),
    )
    reviewer_failed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.FAILED,
        inputs=risk_inputs(review_input, analysis, alternatives),
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Risk Reviewer execution failed",
        ),
    )
    critic_running = StageExecution.model_construct(
        identity=StageIdentity.CRITIC,
        status=StageStatus.RUNNING,
        inputs=AnalystStageInput(review_input=review_input),
        output=None,
        error=None,
    )

    invalid_stage_sets = (
        (
            ReviewStatus.RUNNING,
            StageExecution(identity=StageIdentity.ANALYST, status=StageStatus.PENDING),
            StageExecution(identity=StageIdentity.SOLUTION_ARCHITECT, status=StageStatus.PENDING),
            reviewer_running,
            *pending_final_stages(),
        ),
        (
            ReviewStatus.INCOMPLETE,
            StageExecution(
                identity=StageIdentity.ANALYST,
                status=StageStatus.FAILED,
                inputs=AnalystStageInput(review_input=review_input),
                error=execution_error(),
            ),
            StageExecution(
                identity=StageIdentity.SOLUTION_ARCHITECT,
                status=StageStatus.FAILED,
                inputs=SolutionArchitectStageInput(
                    review_input=review_input,
                    problem_analysis=analysis,
                ),
                error=execution_error(),
            ),
            reviewer_failed,
            *pending_final_stages(),
        ),
        (
            ReviewStatus.RUNNING,
            analyst_completed,
            architect_completed,
            StageExecution(identity=StageIdentity.RISK_REVIEWER, status=StageStatus.PENDING),
            critic_running,
            StageExecution(identity=StageIdentity.COORDINATOR, status=StageStatus.PENDING),
        ),
    )

    for status, *stages in invalid_stage_sets:
        with pytest.raises(ValidationError):
            Review(
                review_input=review_input,
                status=status,
                stages=tuple(stages),
            )


def test_review_completed_remains_unreachable_while_critic_and_coordinator_are_pending_only() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    analyst, architect = completed_upstream_stages(review_input, analysis, alternatives)
    reviewer = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.COMPLETED,
        inputs=risk_inputs(review_input, analysis, alternatives),
        output=valid_risk_assessment(),
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.COMPLETED,
            stages=(analyst, architect, reviewer, *pending_final_stages()),
        )


def test_risk_reviewer_same_execution_provenance_uses_exact_current_instances() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    analyst, architect = completed_upstream_stages(review_input, analysis, alternatives)
    reviewer = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=risk_inputs(review_input, analysis, alternatives),
    )

    review = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=(analyst, architect, reviewer, *pending_final_stages()),
    )

    assert isinstance(reviewer.inputs, RiskReviewerStageInput)
    assert reviewer.inputs.review_input is review.review_input
    assert reviewer.inputs.problem_analysis is analyst.output
    assert reviewer.inputs.solution_alternatives is architect.output


@pytest.mark.parametrize("field", ["review_input", "problem_analysis", "solution_alternatives"])
def test_risk_reviewer_rejects_equal_but_independent_upstream_provenance(field: str) -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    analyst, architect = completed_upstream_stages(review_input, analysis, alternatives)

    equal_review_input = ReviewInput.model_validate(review_input.model_dump())
    equal_analysis = ProblemAnalysis.model_validate(analysis.model_dump())
    equal_alternatives = SolutionAlternatives.model_validate(alternatives.model_dump())
    values = {
        "review_input": equal_review_input if field == "review_input" else review_input,
        "problem_analysis": equal_analysis if field == "problem_analysis" else analysis,
        "solution_alternatives": equal_alternatives if field == "solution_alternatives" else alternatives,
    }
    reviewer = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=RiskReviewerStageInput.model_validate(values),
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(analyst, architect, reviewer, *pending_final_stages()),
        )


def test_review_semantics_use_stage_identity_for_noncanonical_tuple_order() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    analyst, architect = completed_upstream_stages(review_input, analysis, alternatives)
    reviewer = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=risk_inputs(review_input, analysis, alternatives),
    )
    critic, coordinator = pending_final_stages()
    reordered = (coordinator, reviewer, analyst, critic, architect)

    review = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=reordered,
    )

    assert review.stage(StageIdentity.ANALYST) is analyst
    assert review.stage(StageIdentity.SOLUTION_ARCHITECT) is architect
    assert review.stage(StageIdentity.RISK_REVIEWER) is reviewer
    assert review.stages == reordered


def test_review_create_remains_canonical_and_existing_replacements_preserve_valid_order() -> None:
    review_input = valid_review_input()
    created = Review.create(review_input)
    assert tuple(stage.identity for stage in created.stages) == (
        StageIdentity.ANALYST,
        StageIdentity.SOLUTION_ARCHITECT,
        StageIdentity.RISK_REVIEWER,
        StageIdentity.CRITIC,
        StageIdentity.COORDINATOR,
    )

    reordered = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=(
            created.stage(StageIdentity.COORDINATOR),
            created.stage(StageIdentity.RISK_REVIEWER),
            created.stage(StageIdentity.CRITIC),
            created.stage(StageIdentity.ANALYST),
            created.stage(StageIdentity.SOLUTION_ARCHITECT),
        ),
    )
    before = tuple(stage.identity for stage in reordered.stages)
    started = reordered.start_analyst()

    assert tuple(stage.identity for stage in started.stages) == before
    assert started.stage(StageIdentity.ANALYST).status is StageStatus.RUNNING


def completed_slice4_stages(
    review_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
    assessment: RiskAssessment,
) -> tuple[StageExecution, StageExecution, StageExecution]:
    analyst, architect = completed_upstream_stages(
        review_input,
        analysis,
        alternatives,
    )
    reviewer = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.COMPLETED,
        inputs=risk_inputs(review_input, analysis, alternatives),
        output=assessment,
    )
    return analyst, architect, reviewer


def critic_inputs(
    review_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
    assessment: RiskAssessment,
) -> CriticStageInput:
    return CriticStageInput(
        review_input=review_input,
        problem_analysis=analysis,
        solution_alternatives=alternatives,
        risk_assessment=assessment,
    )


def test_critic_stage_input_is_closed_frozen_and_preserves_four_artifacts() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    inputs = critic_inputs(review_input, analysis, alternatives, assessment)

    assert inputs.review_input is review_input
    assert inputs.problem_analysis is analysis
    assert inputs.solution_alternatives is alternatives
    assert inputs.risk_assessment is assessment
    assert CriticStageInput.model_config.get("extra") == "forbid"
    assert CriticStageInput.model_config.get("frozen") is True

    with pytest.raises(ValidationError):
        inputs.risk_assessment = valid_risk_assessment()

    with pytest.raises(ValidationError):
        CriticStageInput.model_validate(
            {
                **inputs.model_dump(),
                "unexpected": "not allowed",
            }
        )


def test_critic_stage_accepts_exact_four_local_lifecycle_shapes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    inputs = critic_inputs(review_input, analysis, alternatives, assessment)
    critical_review = CriticalReview()

    pending = StageExecution(identity=StageIdentity.CRITIC, status=StageStatus.PENDING)
    running = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.RUNNING,
        inputs=inputs,
    )
    completed = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.COMPLETED,
        inputs=inputs,
        output=critical_review,
    )
    failed = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.FAILED,
        inputs=inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Critic execution failed",
        ),
    )

    assert pending.inputs is None
    assert running.inputs is inputs
    assert completed.output is critical_review
    assert failed.error is not None


def test_critic_stage_rejects_wrong_input_and_completed_output_types() -> None:
    review_input = valid_review_input()

    with pytest.raises(ValidationError):
        StageExecution(
            identity=StageIdentity.CRITIC,
            status=StageStatus.RUNNING,
            inputs=AnalystStageInput(review_input=review_input),
        )

    with pytest.raises(ValidationError):
        StageExecution(
            identity=StageIdentity.CRITIC,
            status=StageStatus.COMPLETED,
            inputs=critic_inputs(
                review_input,
                valid_problem_analysis(),
                valid_solution_alternatives(),
                valid_risk_assessment(),
            ),
            output=valid_risk_assessment(),
        )


def test_coordinator_remains_pending_only_as_a_local_stage() -> None:
    pending = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )
    assert pending.status is StageStatus.PENDING

    invalid = StageExecution.model_construct(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.RUNNING,
        inputs=AnalystStageInput(review_input=valid_review_input()),
        output=None,
        error=None,
    )
    with pytest.raises(ValidationError):
        StageExecution.model_validate(invalid.model_dump())


def test_review_accepts_exact_nine_slice5_running_prefixes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    critical_review = CriticalReview()

    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    reviewer_inputs = risk_inputs(review_input, analysis, alternatives)
    current_critic_inputs = critic_inputs(
        review_input,
        analysis,
        alternatives,
        assessment,
    )

    analyst_pending = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.PENDING,
    )
    analyst_running = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.RUNNING,
        inputs=analyst_inputs,
    )
    analyst_completed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.COMPLETED,
        inputs=analyst_inputs,
        output=analysis,
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    architect_running = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.RUNNING,
        inputs=architect_inputs,
    )
    architect_completed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.COMPLETED,
        inputs=architect_inputs,
        output=alternatives,
    )
    reviewer_pending = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.PENDING,
    )
    reviewer_running = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.RUNNING,
        inputs=reviewer_inputs,
    )
    reviewer_completed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.COMPLETED,
        inputs=reviewer_inputs,
        output=assessment,
    )
    critic_pending = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.PENDING,
    )
    critic_running = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.RUNNING,
        inputs=current_critic_inputs,
    )
    critic_completed = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.COMPLETED,
        inputs=current_critic_inputs,
        output=critical_review,
    )
    coordinator_pending = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )

    prefixes = (
        (analyst_pending, architect_pending, reviewer_pending, critic_pending),
        (analyst_running, architect_pending, reviewer_pending, critic_pending),
        (analyst_completed, architect_pending, reviewer_pending, critic_pending),
        (analyst_completed, architect_running, reviewer_pending, critic_pending),
        (analyst_completed, architect_completed, reviewer_pending, critic_pending),
        (analyst_completed, architect_completed, reviewer_running, critic_pending),
        (analyst_completed, architect_completed, reviewer_completed, critic_pending),
        (analyst_completed, architect_completed, reviewer_completed, critic_running),
        (analyst_completed, architect_completed, reviewer_completed, critic_completed),
    )

    for stages in prefixes:
        review = Review(
            review_input=review_input,
            status=ReviewStatus.RUNNING,
            stages=(*stages, coordinator_pending),
        )
        assert review.status is ReviewStatus.RUNNING
        assert review.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_review_accepts_exact_four_slice5_incomplete_shapes() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()

    analyst_inputs = AnalystStageInput(review_input=review_input)
    architect_inputs = SolutionArchitectStageInput(
        review_input=review_input,
        problem_analysis=analysis,
    )
    reviewer_inputs = risk_inputs(review_input, analysis, alternatives)
    current_critic_inputs = critic_inputs(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    analyst_completed, architect_completed, reviewer_completed = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )

    analyst_failed = StageExecution(
        identity=StageIdentity.ANALYST,
        status=StageStatus.FAILED,
        inputs=analyst_inputs,
        error=execution_error(),
    )
    architect_failed = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.FAILED,
        inputs=architect_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Solution Architect execution failed",
        ),
    )
    reviewer_failed = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.FAILED,
        inputs=reviewer_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Risk Reviewer execution failed",
        ),
    )
    critic_failed = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.FAILED,
        inputs=current_critic_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Critic execution failed",
        ),
    )
    architect_pending = StageExecution(
        identity=StageIdentity.SOLUTION_ARCHITECT,
        status=StageStatus.PENDING,
    )
    reviewer_pending = StageExecution(
        identity=StageIdentity.RISK_REVIEWER,
        status=StageStatus.PENDING,
    )
    critic_pending = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.PENDING,
    )
    coordinator_pending = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )

    shapes = (
        (analyst_failed, architect_pending, reviewer_pending, critic_pending),
        (analyst_completed, architect_failed, reviewer_pending, critic_pending),
        (analyst_completed, architect_completed, reviewer_failed, critic_pending),
        (analyst_completed, architect_completed, reviewer_completed, critic_failed),
    )

    for stages in shapes:
        review = Review(
            review_input=review_input,
            status=ReviewStatus.INCOMPLETE,
            stages=(*stages, coordinator_pending),
        )
        assert review.status is ReviewStatus.INCOMPLETE
        assert review.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_review_rejects_slice5_skips_multiple_failures_and_later_execution() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    analyst, architect, reviewer = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    current_critic_inputs = critic_inputs(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    critic_running = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.RUNNING,
        inputs=current_critic_inputs,
    )
    critic_failed = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.FAILED,
        inputs=current_critic_inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Critic execution failed",
        ),
    )
    coordinator_pending = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )
    coordinator_running = StageExecution.model_construct(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.RUNNING,
        inputs=AnalystStageInput(review_input=review_input),
        output=None,
        error=None,
    )

    invalid_stage_sets = (
        (
            ReviewStatus.RUNNING,
            analyst,
            architect,
            StageExecution(
                identity=StageIdentity.RISK_REVIEWER,
                status=StageStatus.PENDING,
            ),
            critic_running,
            coordinator_pending,
        ),
        (
            ReviewStatus.INCOMPLETE,
            StageExecution(
                identity=StageIdentity.ANALYST,
                status=StageStatus.FAILED,
                inputs=AnalystStageInput(review_input=review_input),
                error=execution_error(),
            ),
            architect,
            reviewer,
            critic_failed,
            coordinator_pending,
        ),
        (
            ReviewStatus.INCOMPLETE,
            analyst,
            architect,
            reviewer,
            critic_failed,
            coordinator_running,
        ),
    )

    for status, *stages in invalid_stage_sets:
        with pytest.raises(ValidationError):
            Review(
                review_input=review_input,
                status=status,
                stages=tuple(stages),
            )


def test_review_completed_remains_unreachable_after_critic_completion() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    analyst, architect, reviewer = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    critic = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.COMPLETED,
        inputs=critic_inputs(review_input, analysis, alternatives, assessment),
        output=CriticalReview(),
    )
    coordinator = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=ReviewStatus.COMPLETED,
            stages=(analyst, architect, reviewer, critic, coordinator),
        )


@pytest.mark.parametrize("status", [StageStatus.RUNNING, StageStatus.COMPLETED, StageStatus.FAILED])
def test_critic_same_execution_provenance_uses_exact_instances_for_all_executed_shapes(
    status: StageStatus,
) -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    analyst, architect, reviewer = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    output = CriticalReview() if status is StageStatus.COMPLETED else None
    error = (
        ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Critic execution failed",
        )
        if status is StageStatus.FAILED
        else None
    )
    critic = StageExecution(
        identity=StageIdentity.CRITIC,
        status=status,
        inputs=critic_inputs(review_input, analysis, alternatives, assessment),
        output=output,
        error=error,
    )

    review = Review(
        review_input=review_input,
        status=(
            ReviewStatus.INCOMPLETE
            if status is StageStatus.FAILED
            else ReviewStatus.RUNNING
        ),
        stages=(
            analyst,
            architect,
            reviewer,
            critic,
            StageExecution(
                identity=StageIdentity.COORDINATOR,
                status=StageStatus.PENDING,
            ),
        ),
    )

    assert isinstance(critic.inputs, CriticStageInput)
    assert critic.inputs.review_input is review.review_input
    assert critic.inputs.problem_analysis is analyst.output
    assert critic.inputs.solution_alternatives is architect.output
    assert critic.inputs.risk_assessment is reviewer.output


@pytest.mark.parametrize("status", [StageStatus.RUNNING, StageStatus.COMPLETED, StageStatus.FAILED])
@pytest.mark.parametrize(
    "field",
    ["review_input", "problem_analysis", "solution_alternatives", "risk_assessment"],
)
def test_critic_rejects_equal_but_independent_provenance_for_every_executed_shape(
    status: StageStatus,
    field: str,
) -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    analyst, architect, reviewer = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    equal_values: dict[str, object] = {
        "review_input": ReviewInput.model_validate(review_input.model_dump()),
        "problem_analysis": ProblemAnalysis.model_validate(analysis.model_dump()),
        "solution_alternatives": SolutionAlternatives.model_validate(
            alternatives.model_dump()
        ),
        "risk_assessment": RiskAssessment.model_validate(assessment.model_dump()),
    }
    exact_values: dict[str, object] = {
        "review_input": review_input,
        "problem_analysis": analysis,
        "solution_alternatives": alternatives,
        "risk_assessment": assessment,
    }
    exact_values[field] = equal_values[field]
    current_inputs = CriticStageInput.model_validate(exact_values)

    output = CriticalReview() if status is StageStatus.COMPLETED else None
    error = (
        ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Critic execution failed",
        )
        if status is StageStatus.FAILED
        else None
    )
    critic = StageExecution(
        identity=StageIdentity.CRITIC,
        status=status,
        inputs=current_inputs,
        output=output,
        error=error,
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=(
                ReviewStatus.INCOMPLETE
                if status is StageStatus.FAILED
                else ReviewStatus.RUNNING
            ),
            stages=(
                analyst,
                architect,
                reviewer,
                critic,
                StageExecution(
                    identity=StageIdentity.COORDINATOR,
                    status=StageStatus.PENDING,
                ),
            ),
        )


def test_slice5_review_semantics_use_identity_in_noncanonical_tuple_order() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    analyst, architect, reviewer = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    critic = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.RUNNING,
        inputs=critic_inputs(review_input, analysis, alternatives, assessment),
    )
    coordinator = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )
    reordered = (coordinator, critic, analyst, reviewer, architect)

    review = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=reordered,
    )

    assert review.stage(StageIdentity.CRITIC) is critic
    assert review.stage(StageIdentity.RISK_REVIEWER) is reviewer
    assert review.stages == reordered



def valid_final_review() -> FinalReview:
    return FinalReview.model_validate(
        {
            "situation_summary": "No defensible alternatives are currently available.",
            "ranked_alternatives": [],
            "recommendation_outcome": "INSUFFICIENT_EVIDENCE",
            "preferred_alternative_id": None,
            "conclusion_rationale": "Current evidence is insufficient.",
            "principal_risks": [],
            "unresolved_questions": [],
            "criticism_dispositions": [],
            "next_validation_step": "Collect the missing evidence.",
            "confidence": "LOW",
        }
    )


def coordinator_inputs(
    review_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
    assessment: RiskAssessment,
    critical_review: CriticalReview,
) -> CoordinatorStageInput:
    return CoordinatorStageInput(
        review_input=review_input,
        problem_analysis=analysis,
        solution_alternatives=alternatives,
        risk_assessment=assessment,
        critical_review=critical_review,
    )


def completed_slice5_stages(
    review_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
    assessment: RiskAssessment,
    critical_review: CriticalReview,
) -> tuple[StageExecution, StageExecution, StageExecution, StageExecution]:
    analyst, architect, reviewer = completed_slice4_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
    )
    critic = StageExecution(
        identity=StageIdentity.CRITIC,
        status=StageStatus.COMPLETED,
        inputs=critic_inputs(review_input, analysis, alternatives, assessment),
        output=critical_review,
    )
    return analyst, architect, reviewer, critic


def test_coordinator_stage_input_and_four_local_shapes_are_exact() -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    critique = CriticalReview()
    inputs = coordinator_inputs(
        review_input,
        analysis,
        alternatives,
        assessment,
        critique,
    )
    output = valid_final_review()

    assert inputs.review_input is review_input
    assert inputs.problem_analysis is analysis
    assert inputs.solution_alternatives is alternatives
    assert inputs.risk_assessment is assessment
    assert inputs.critical_review is critique
    assert CoordinatorStageInput.model_config.get("extra") == "forbid"
    assert CoordinatorStageInput.model_config.get("frozen") is True

    pending = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.PENDING,
    )
    running = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.RUNNING,
        inputs=inputs,
    )
    completed = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.COMPLETED,
        inputs=inputs,
        output=output,
    )
    failed = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.FAILED,
        inputs=inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Coordinator execution failed",
        ),
    )

    assert pending.inputs is None
    assert running.inputs is inputs
    assert completed.output is output
    assert failed.error is not None

    with pytest.raises(ValidationError):
        inputs.critical_review = CriticalReview()
    with pytest.raises(ValidationError):
        CoordinatorStageInput.model_validate(
            {**inputs.model_dump(), "unexpected": "forbidden"}
        )
    with pytest.raises(ValidationError):
        StageExecution(
            identity=StageIdentity.COORDINATOR,
            status=StageStatus.RUNNING,
            inputs=CriticStageInput(
                review_input=review_input,
                problem_analysis=analysis,
                solution_alternatives=alternatives,
                risk_assessment=assessment,
            ),
        )
    with pytest.raises(ValidationError):
        StageExecution(
            identity=StageIdentity.COORDINATOR,
            status=StageStatus.COMPLETED,
            inputs=inputs,
            output=CriticalReview(),
        )


def slice6_stage_variants() -> tuple[
    ReviewInput,
    tuple[StageExecution, ...],
    tuple[StageExecution, ...],
    StageExecution,
    StageExecution,
]:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    critique = CriticalReview()
    analyst, architect, reviewer, critic = completed_slice5_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
        critique,
    )
    coordinator_current_inputs = coordinator_inputs(
        review_input,
        analysis,
        alternatives,
        assessment,
        critique,
    )
    coordinator_running = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.RUNNING,
        inputs=coordinator_current_inputs,
    )
    coordinator_completed = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.COMPLETED,
        inputs=coordinator_current_inputs,
        output=valid_final_review(),
    )
    return (
        review_input,
        (analyst, architect, reviewer, critic),
        (
            StageExecution(
                identity=StageIdentity.ANALYST,
                status=StageStatus.PENDING,
            ),
            StageExecution(
                identity=StageIdentity.SOLUTION_ARCHITECT,
                status=StageStatus.PENDING,
            ),
            StageExecution(
                identity=StageIdentity.RISK_REVIEWER,
                status=StageStatus.PENDING,
            ),
            StageExecution(
                identity=StageIdentity.CRITIC,
                status=StageStatus.PENDING,
            ),
        ),
        coordinator_running,
        coordinator_completed,
    )


def test_review_accepts_tenth_running_and_single_completed_shape() -> None:
    (
        review_input,
        completed_upstream,
        _,
        coordinator_running,
        coordinator_completed,
    ) = slice6_stage_variants()

    running = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=(*completed_upstream, coordinator_running),
    )
    completed = Review(
        review_input=review_input,
        status=ReviewStatus.COMPLETED,
        stages=(*completed_upstream, coordinator_completed),
    )

    assert running.stage(StageIdentity.COORDINATOR) is coordinator_running
    assert completed.status is ReviewStatus.COMPLETED
    assert completed.stage(StageIdentity.COORDINATOR) is coordinator_completed


def test_review_accepts_fifth_incomplete_shape() -> None:
    review_input, completed_upstream, _, coordinator_running, _ = (
        slice6_stage_variants()
    )
    assert isinstance(coordinator_running.inputs, CoordinatorStageInput)
    failed = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=StageStatus.FAILED,
        inputs=coordinator_running.inputs,
        error=ReviewError(
            kind=ReviewErrorKind.EXECUTION,
            message="Coordinator execution failed",
        ),
    )

    review = Review(
        review_input=review_input,
        status=ReviewStatus.INCOMPLETE,
        stages=(*completed_upstream, failed),
    )
    assert review.stage(StageIdentity.COORDINATOR) is failed


@pytest.mark.parametrize(
    "status",
    [StageStatus.RUNNING, StageStatus.COMPLETED, StageStatus.FAILED],
)
def test_coordinator_provenance_requires_all_five_exact_instances(
    status: StageStatus,
) -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    critique = CriticalReview()
    analyst, architect, reviewer, critic = completed_slice5_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
        critique,
    )
    inputs = coordinator_inputs(
        review_input,
        analysis,
        alternatives,
        assessment,
        critique,
    )
    coordinator = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=status,
        inputs=inputs,
        output=valid_final_review() if status is StageStatus.COMPLETED else None,
        error=(
            ReviewError(
                kind=ReviewErrorKind.EXECUTION,
                message="Coordinator execution failed",
            )
            if status is StageStatus.FAILED
            else None
        ),
    )

    review = Review(
        review_input=review_input,
        status=(
            ReviewStatus.COMPLETED
            if status is StageStatus.COMPLETED
            else (
                ReviewStatus.INCOMPLETE
                if status is StageStatus.FAILED
                else ReviewStatus.RUNNING
            )
        ),
        stages=(analyst, architect, reviewer, critic, coordinator),
    )

    assert isinstance(coordinator.inputs, CoordinatorStageInput)
    assert coordinator.inputs.review_input is review.review_input
    assert coordinator.inputs.problem_analysis is analyst.output
    assert coordinator.inputs.solution_alternatives is architect.output
    assert coordinator.inputs.risk_assessment is reviewer.output
    assert coordinator.inputs.critical_review is critic.output


@pytest.mark.parametrize(
    "status",
    [StageStatus.RUNNING, StageStatus.COMPLETED, StageStatus.FAILED],
)
@pytest.mark.parametrize(
    "field",
    [
        "review_input",
        "problem_analysis",
        "solution_alternatives",
        "risk_assessment",
        "critical_review",
    ],
)
def test_coordinator_rejects_equal_independent_provenance_one_field_at_a_time(
    field: str,
    status: StageStatus,
) -> None:
    review_input = valid_review_input()
    analysis = valid_problem_analysis()
    alternatives = valid_solution_alternatives()
    assessment = valid_risk_assessment()
    critique = CriticalReview()
    upstream = completed_slice5_stages(
        review_input,
        analysis,
        alternatives,
        assessment,
        critique,
    )
    exact: dict[str, object] = {
        "review_input": review_input,
        "problem_analysis": analysis,
        "solution_alternatives": alternatives,
        "risk_assessment": assessment,
        "critical_review": critique,
    }
    copies: dict[str, object] = {
        "review_input": ReviewInput.model_validate(review_input.model_dump()),
        "problem_analysis": ProblemAnalysis.model_validate(analysis.model_dump()),
        "solution_alternatives": SolutionAlternatives.model_validate(
            alternatives.model_dump()
        ),
        "risk_assessment": RiskAssessment.model_validate(assessment.model_dump()),
        "critical_review": CriticalReview.model_validate(critique.model_dump()),
    }
    exact[field] = copies[field]
    inputs = CoordinatorStageInput.model_validate(exact)
    coordinator = StageExecution(
        identity=StageIdentity.COORDINATOR,
        status=status,
        inputs=inputs,
        output=valid_final_review() if status is StageStatus.COMPLETED else None,
        error=(
            ReviewError(
                kind=ReviewErrorKind.EXECUTION,
                message="Coordinator execution failed",
            )
            if status is StageStatus.FAILED
            else None
        ),
    )

    with pytest.raises(ValidationError):
        Review(
            review_input=review_input,
            status=(
                ReviewStatus.COMPLETED
                if status is StageStatus.COMPLETED
                else (
                    ReviewStatus.INCOMPLETE
                    if status is StageStatus.FAILED
                    else ReviewStatus.RUNNING
                )
            ),
            stages=(*upstream, coordinator),
        )


def test_slice6_review_semantics_use_identity_in_noncanonical_order() -> None:
    review_input, completed_upstream, _, coordinator_running, _ = (
        slice6_stage_variants()
    )
    analyst, architect, reviewer, critic = completed_upstream
    reordered = (coordinator_running, critic, analyst, reviewer, architect)

    review = Review(
        review_input=review_input,
        status=ReviewStatus.RUNNING,
        stages=reordered,
    )

    assert review.stage(StageIdentity.COORDINATOR) is coordinator_running
    assert review.stage(StageIdentity.ANALYST) is analyst
    assert review.stages == reordered
