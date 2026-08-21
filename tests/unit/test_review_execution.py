import pytest
from pydantic import ValidationError

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    Review,
    ReviewError,
    ReviewErrorKind,
    ReviewStatus,
    SolutionArchitectStageInput,
    StageExecution,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
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


def execution_error() -> ReviewError:
    return ReviewError(
        kind=ReviewErrorKind.EXECUTION,
        message="Analyst execution failed",
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
        StageExecution,
        Review,
    )

    for contract_type in contract_types:
        assert contract_type.model_config.get("extra") == "forbid"
        assert contract_type.model_config.get("frozen") is True

    review_input = valid_review_input()
    problem_analysis = valid_problem_analysis()
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
        StageIdentity.RISK_REVIEWER,
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
