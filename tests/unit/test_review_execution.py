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
