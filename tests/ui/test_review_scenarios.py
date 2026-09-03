from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.execution import (
    CANONICAL_STAGE_ORDER,
    CoordinatorStageInput,
    CriticStageInput,
    Review,
    ReviewErrorKind,
    ReviewStatus,
    RiskReviewerStageInput,
    SolutionArchitectStageInput,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.final_reviews import (
    FinalReview,
    RecommendationOutcome,
)
from agentic_review_board.domain.review import ReviewInput

from .fixtures.review_scenarios import ScenarioKind, scenario_executor


def created_review(description: str = "Evaluate deployment options.") -> Review:
    return Review.create(
        ReviewInput(
            description=description,
            title="Deployment Review",
            objective="Choose the next validation step.",
            constraints=("Use current local capacity.",),
            context=("This is a pedagogical PoC.",),
            stated_facts=("The workflow contains five agents.",),
        )
    )


def test_complete_scenario_runs_real_five_agent_collaboration() -> None:
    executor = scenario_executor(ScenarioKind.COMPLETE)
    observed: list[Review] = []

    result = executor(created_review(), observer=observed.append)

    assert [role for role, _ in executor.calls] == [
        "analyst",
        "solution_architect",
        "risk_reviewer",
        "critic",
        "coordinator",
    ]
    assert len(observed) == 11
    assert observed[-1] is result
    assert result.status is ReviewStatus.COMPLETED
    assert tuple(stage.identity for stage in result.stages) == CANONICAL_STAGE_ORDER
    assert all(stage.status is StageStatus.COMPLETED for stage in result.stages)

    analyst = result.stage(StageIdentity.ANALYST)
    architect = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    reviewer = result.stage(StageIdentity.RISK_REVIEWER)
    critic = result.stage(StageIdentity.CRITIC)
    coordinator = result.stage(StageIdentity.COORDINATOR)
    assert isinstance(architect.inputs, SolutionArchitectStageInput)
    assert architect.inputs.problem_analysis is analyst.output
    assert isinstance(reviewer.inputs, RiskReviewerStageInput)
    assert reviewer.inputs.problem_analysis is analyst.output
    assert reviewer.inputs.solution_alternatives is architect.output
    assert isinstance(critic.inputs, CriticStageInput)
    assert critic.inputs.risk_assessment is reviewer.output
    assert isinstance(critic.output, CriticalReview)
    assert isinstance(coordinator.inputs, CoordinatorStageInput)
    assert coordinator.inputs.critical_review is critic.output
    assert isinstance(coordinator.output, FinalReview)


def test_insufficient_evidence_is_a_trusted_completed_scenario() -> None:
    executor = scenario_executor(ScenarioKind.INSUFFICIENT_EVIDENCE)
    result = executor(created_review(), observer=lambda review: None)

    coordinator = result.stage(StageIdentity.COORDINATOR)
    assert result.status is ReviewStatus.COMPLETED
    assert isinstance(coordinator.output, FinalReview)
    assert (
        coordinator.output.recommendation_outcome
        is RecommendationOutcome.INSUFFICIENT_EVIDENCE
    )
    assert coordinator.output.preferred_alternative_id is None
    assert coordinator.output.ranked_alternatives == ()
    assert coordinator.output.next_validation_step


def test_critic_output_validation_failure_stops_coordinator() -> None:
    executor = scenario_executor(ScenarioKind.CRITIC_OUTPUT_VALIDATION_FAILURE)
    observed: list[Review] = []

    result = executor(created_review(), observer=observed.append)

    assert [role for role, _ in executor.calls] == [
        "analyst",
        "solution_architect",
        "risk_reviewer",
        "critic",
    ]
    assert len(observed) == 9
    assert observed[-1] is result
    assert result.status is ReviewStatus.INCOMPLETE
    assert all(
        result.stage(identity).status is StageStatus.COMPLETED
        for identity in CANONICAL_STAGE_ORDER[:3]
    )
    critic = result.stage(StageIdentity.CRITIC)
    coordinator = result.stage(StageIdentity.COORDINATOR)
    assert critic.status is StageStatus.FAILED
    assert critic.output is None
    assert critic.error is not None
    assert critic.error.kind is ReviewErrorKind.OUTPUT_VALIDATION
    assert coordinator.status is StageStatus.PENDING
    assert coordinator.output is None


def test_critic_execution_failure_has_distinct_safe_category() -> None:
    executor = scenario_executor(ScenarioKind.CRITIC_EXECUTION_FAILURE)

    result = executor(created_review(), observer=lambda review: None)

    critic = result.stage(StageIdentity.CRITIC)
    assert result.status is ReviewStatus.INCOMPLETE
    assert critic.status is StageStatus.FAILED
    assert critic.error is not None
    assert critic.error.kind is ReviewErrorKind.EXECUTION
    assert critic.error.message == "Critic execution failed"
    assert "provider-secret-marker" not in critic.error.message
    assert result.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_reused_scenario_executor_keeps_reviews_and_observers_isolated() -> None:
    executor = scenario_executor(ScenarioKind.COMPLETE)
    first_observed: list[Review] = []
    second_observed: list[Review] = []
    first_created = created_review("First isolated Review.")
    second_created = created_review("Second isolated Review.")

    first = executor(first_created, observer=first_observed.append)
    second = executor(second_created, observer=second_observed.append)

    assert first.status is ReviewStatus.COMPLETED
    assert second.status is ReviewStatus.COMPLETED
    assert first.review_input is first_created.review_input
    assert second.review_input is second_created.review_input
    assert first.review_input is not second.review_input
    assert all(review.review_input is first.review_input for review in first_observed)
    assert all(review.review_input is second.review_input for review in second_observed)
    assert len(first_observed) == len(second_observed) == 11
    assert len(executor.calls) == 10
    assert first.stage(StageIdentity.ANALYST).output is not second.stage(
        StageIdentity.ANALYST
    ).output
