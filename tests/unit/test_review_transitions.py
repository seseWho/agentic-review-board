import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    Review,
    ReviewStatus,
    SolutionArchitectStageInput,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.solutions import SolutionAlternatives


def review_input() -> ReviewInput:
    return ReviewInput(description="Review a proposed technical change.")


def problem_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        objective="Determine whether further evaluation is useful.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )


def solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives.model_validate(
        {
            "alternatives": [],
            "generation_notes": {
                "explanation": "Evidence is insufficient for useful alternatives.",
                "blocking_missing_information": [],
                "blocking_uncertainties": [],
            },
        }
    )


def test_success_transitions_build_valid_immutable_snapshots() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    created = Review.create(original_input)

    running = created.start()
    analyst_running = running.start_analyst()
    analyst_completed = analyst_running.complete_analyst(analysis)
    architect_running = analyst_completed.start_solution_architect()
    architect_completed = architect_running.complete_solution_architect(alternatives)

    assert created.status is ReviewStatus.CREATED
    assert running.status is ReviewStatus.RUNNING
    assert architect_completed.status is ReviewStatus.RUNNING
    assert architect_completed.review_input is original_input

    analyst_stage = analyst_completed.stage(StageIdentity.ANALYST)
    assert analyst_stage.status is StageStatus.COMPLETED
    assert isinstance(analyst_stage.inputs, AnalystStageInput)
    assert analyst_stage.inputs.review_input is original_input
    assert analyst_stage.output is analysis

    architect_stage = architect_completed.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert architect_stage.status is StageStatus.COMPLETED
    assert isinstance(architect_stage.inputs, SolutionArchitectStageInput)
    assert architect_stage.inputs.review_input is original_input
    assert architect_stage.inputs.problem_analysis is analysis
    assert architect_stage.output is alternatives

    for identity in (
        StageIdentity.RISK_REVIEWER,
        StageIdentity.CRITIC,
        StageIdentity.COORDINATOR,
    ):
        assert architect_completed.stage(identity).status is StageStatus.PENDING


def test_transitions_preserve_unaffected_stage_objects_and_order() -> None:
    created = Review.create(review_input())
    running = created.start()
    analyst_running = running.start_analyst()

    assert [stage.identity for stage in analyst_running.stages] == list(StageIdentity)
    assert running.stages == created.stages
    assert analyst_running.stage(StageIdentity.SOLUTION_ARCHITECT) is running.stage(
        StageIdentity.SOLUTION_ARCHITECT
    )


def test_transitions_reject_illegal_repeated_or_out_of_order_calls() -> None:
    created = Review.create(review_input())

    with pytest.raises(ValueError):
        created.start_analyst()
    with pytest.raises(ValueError):
        created.start_solution_architect()

    running = created.start()
    with pytest.raises(ValueError):
        running.start()
    with pytest.raises(ValueError):
        running.complete_analyst(problem_analysis())
    with pytest.raises(ValueError):
        running.start_solution_architect()

    analyst_running = running.start_analyst()
    with pytest.raises(ValueError):
        analyst_running.start_analyst()

    analyst_completed = analyst_running.complete_analyst(problem_analysis())
    with pytest.raises(ValueError):
        analyst_completed.complete_analyst(problem_analysis())

    architect_running = analyst_completed.start_solution_architect()
    with pytest.raises(ValueError):
        architect_running.start_solution_architect()

    completed = architect_running.complete_solution_architect(solution_alternatives())
    with pytest.raises(ValueError):
        completed.complete_solution_architect(solution_alternatives())
