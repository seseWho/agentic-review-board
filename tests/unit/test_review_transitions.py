import pytest

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    CriticStageInput,
    Review,
    ReviewError,
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


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(risks=(), overall_observations=())


def analyst_error() -> ReviewError:
    return ReviewError(
        kind=ReviewErrorKind.EXECUTION,
        message="Analyst execution failed",
    )


def architect_error() -> ReviewError:
    return ReviewError(
        kind=ReviewErrorKind.EXECUTION,
        message="Solution Architect execution failed",
    )


def risk_error() -> ReviewError:
    return ReviewError(
        kind=ReviewErrorKind.EXECUTION,
        message="Risk Reviewer execution failed",
    )


def architect_completed_review(
    original_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
) -> Review:
    return (
        Review.create(original_input)
        .start()
        .start_analyst()
        .complete_analyst(analysis)
        .start_solution_architect()
        .complete_solution_architect(alternatives)
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


def test_review_validation_and_lookup_use_identity_not_tuple_position() -> None:
    running = Review.create(review_input()).start().start_analyst()
    reordered_stages = (
        running.stage(StageIdentity.COORDINATOR),
        running.stage(StageIdentity.ANALYST),
        running.stage(StageIdentity.CRITIC),
        running.stage(StageIdentity.SOLUTION_ARCHITECT),
        running.stage(StageIdentity.RISK_REVIEWER),
    )

    reordered = Review(
        review_input=running.review_input,
        status=ReviewStatus.RUNNING,
        stages=reordered_stages,
    )

    assert reordered.stage(StageIdentity.ANALYST).status is StageStatus.RUNNING
    assert reordered.stage(StageIdentity.SOLUTION_ARCHITECT).status is StageStatus.PENDING
    assert reordered.stages == reordered_stages


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


def test_fail_analyst_atomically_builds_incomplete_review() -> None:
    running = Review.create(review_input()).start().start_analyst()
    previous_architect = running.stage(StageIdentity.SOLUTION_ARCHITECT)

    failed = running.fail_analyst(analyst_error())

    analyst = failed.stage(StageIdentity.ANALYST)
    assert failed.status is ReviewStatus.INCOMPLETE
    assert analyst.status is StageStatus.FAILED
    assert isinstance(analyst.inputs, AnalystStageInput)
    assert analyst.inputs.review_input is failed.review_input
    assert analyst.output is None
    assert analyst.error == analyst_error()
    assert failed.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert failed.stage(StageIdentity.SOLUTION_ARCHITECT).status is StageStatus.PENDING


def test_fail_solution_architect_atomically_preserves_completed_analyst() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    architect_running = (
        Review.create(original_input)
        .start()
        .start_analyst()
        .complete_analyst(analysis)
        .start_solution_architect()
    )
    previous_analyst = architect_running.stage(StageIdentity.ANALYST)

    failed = architect_running.fail_solution_architect(architect_error())

    analyst = failed.stage(StageIdentity.ANALYST)
    architect = failed.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert failed.status is ReviewStatus.INCOMPLETE
    assert analyst is previous_analyst
    assert analyst.status is StageStatus.COMPLETED
    assert analyst.output is analysis
    assert architect.status is StageStatus.FAILED
    assert isinstance(architect.inputs, SolutionArchitectStageInput)
    assert architect.inputs.review_input is original_input
    assert architect.inputs.problem_analysis is analysis
    assert architect.output is None
    assert architect.error == architect_error()


def test_failure_transitions_require_current_stage_running() -> None:
    created = Review.create(review_input())
    running = created.start()

    with pytest.raises(ValueError):
        running.fail_analyst(analyst_error())
    with pytest.raises(ValueError):
        running.fail_solution_architect(architect_error())

    analyst_completed = running.start_analyst().complete_analyst(problem_analysis())
    with pytest.raises(ValueError):
        analyst_completed.fail_analyst(analyst_error())
    with pytest.raises(ValueError):
        analyst_completed.fail_solution_architect(architect_error())


def test_start_risk_reviewer_records_exact_trusted_upstream_inputs() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    completed = architect_completed_review(original_input, analysis, alternatives)
    previous_analyst = completed.stage(StageIdentity.ANALYST)
    previous_architect = completed.stage(StageIdentity.SOLUTION_ARCHITECT)
    previous_critic = completed.stage(StageIdentity.CRITIC)
    previous_coordinator = completed.stage(StageIdentity.COORDINATOR)

    started = completed.start_risk_reviewer()

    reviewer = started.stage(StageIdentity.RISK_REVIEWER)
    assert started.status is ReviewStatus.RUNNING
    assert reviewer.status is StageStatus.RUNNING
    assert isinstance(reviewer.inputs, RiskReviewerStageInput)
    assert reviewer.inputs.review_input is original_input
    assert reviewer.inputs.problem_analysis is analysis
    assert reviewer.inputs.solution_alternatives is alternatives
    assert reviewer.output is None
    assert reviewer.error is None
    assert started.stage(StageIdentity.ANALYST) is previous_analyst
    assert started.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert started.stage(StageIdentity.CRITIC) is previous_critic
    assert started.stage(StageIdentity.COORDINATOR) is previous_coordinator


def test_start_risk_reviewer_rejects_premature_or_repeated_start() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    running = Review.create(original_input).start()

    with pytest.raises(ValueError):
        running.start_risk_reviewer()

    analyst_completed = running.start_analyst().complete_analyst(analysis)
    with pytest.raises(ValueError):
        analyst_completed.start_risk_reviewer()

    architect_running = analyst_completed.start_solution_architect()
    with pytest.raises(ValueError):
        architect_running.start_risk_reviewer()

    completed = architect_running.complete_solution_architect(alternatives)
    reviewer_running = completed.start_risk_reviewer()
    with pytest.raises(ValueError):
        reviewer_running.start_risk_reviewer()


def test_complete_risk_reviewer_preserves_recorded_inputs_and_exact_output() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    reviewer_running = architect_completed_review(
        original_input,
        analysis,
        alternatives,
    ).start_risk_reviewer()
    running_stage = reviewer_running.stage(StageIdentity.RISK_REVIEWER)
    assert isinstance(running_stage.inputs, RiskReviewerStageInput)
    recorded_inputs = running_stage.inputs
    previous_analyst = reviewer_running.stage(StageIdentity.ANALYST)
    previous_architect = reviewer_running.stage(StageIdentity.SOLUTION_ARCHITECT)
    previous_critic = reviewer_running.stage(StageIdentity.CRITIC)
    previous_coordinator = reviewer_running.stage(StageIdentity.COORDINATOR)

    completed = reviewer_running.complete_risk_reviewer(assessment)

    reviewer = completed.stage(StageIdentity.RISK_REVIEWER)
    assert completed.status is ReviewStatus.RUNNING
    assert reviewer.status is StageStatus.COMPLETED
    assert reviewer.inputs is recorded_inputs
    assert reviewer.output is assessment
    assert reviewer.error is None
    assert completed.stage(StageIdentity.ANALYST) is previous_analyst
    assert completed.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert completed.stage(StageIdentity.CRITIC) is previous_critic
    assert completed.stage(StageIdentity.COORDINATOR) is previous_coordinator
    assert completed.stage(StageIdentity.CRITIC).status is StageStatus.PENDING
    assert completed.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_complete_risk_reviewer_requires_running_stage() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    completed = architect_completed_review(original_input, analysis, alternatives)

    with pytest.raises(ValueError):
        completed.complete_risk_reviewer(risk_assessment())

    reviewer_completed = completed.start_risk_reviewer().complete_risk_reviewer(risk_assessment())
    with pytest.raises(ValueError):
        reviewer_completed.complete_risk_reviewer(risk_assessment())


def test_fail_risk_reviewer_atomically_preserves_upstream_work_and_inputs() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    reviewer_running = architect_completed_review(
        original_input,
        analysis,
        alternatives,
    ).start_risk_reviewer()
    running_stage = reviewer_running.stage(StageIdentity.RISK_REVIEWER)
    assert isinstance(running_stage.inputs, RiskReviewerStageInput)
    recorded_inputs = running_stage.inputs
    previous_analyst = reviewer_running.stage(StageIdentity.ANALYST)
    previous_architect = reviewer_running.stage(StageIdentity.SOLUTION_ARCHITECT)
    previous_critic = reviewer_running.stage(StageIdentity.CRITIC)
    previous_coordinator = reviewer_running.stage(StageIdentity.COORDINATOR)
    error = risk_error()

    failed = reviewer_running.fail_risk_reviewer(error)

    reviewer = failed.stage(StageIdentity.RISK_REVIEWER)
    assert failed.status is ReviewStatus.INCOMPLETE
    assert reviewer.status is StageStatus.FAILED
    assert reviewer.inputs is recorded_inputs
    assert reviewer.output is None
    assert reviewer.error is error
    assert failed.stage(StageIdentity.ANALYST) is previous_analyst
    assert failed.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert failed.stage(StageIdentity.CRITIC) is previous_critic
    assert failed.stage(StageIdentity.COORDINATOR) is previous_coordinator
    assert failed.stage(StageIdentity.CRITIC).status is StageStatus.PENDING
    assert failed.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_fail_risk_reviewer_requires_running_stage_and_nonterminal_review() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    completed = architect_completed_review(original_input, analysis, alternatives)

    with pytest.raises(ValueError):
        completed.fail_risk_reviewer(risk_error())

    reviewer_completed = completed.start_risk_reviewer().complete_risk_reviewer(risk_assessment())
    with pytest.raises(ValueError):
        reviewer_completed.fail_risk_reviewer(risk_error())

    reviewer_failed = completed.start_risk_reviewer().fail_risk_reviewer(risk_error())
    with pytest.raises(ValueError):
        reviewer_failed.fail_risk_reviewer(risk_error())


def test_risk_reviewer_transitions_use_identity_and_preserve_noncanonical_order() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    canonical = architect_completed_review(original_input, analysis, alternatives)
    reordered_stages = (
        canonical.stage(StageIdentity.COORDINATOR),
        canonical.stage(StageIdentity.RISK_REVIEWER),
        canonical.stage(StageIdentity.ANALYST),
        canonical.stage(StageIdentity.CRITIC),
        canonical.stage(StageIdentity.SOLUTION_ARCHITECT),
    )
    reordered = Review(
        review_input=original_input,
        status=ReviewStatus.RUNNING,
        stages=reordered_stages,
    )
    expected_order = tuple(stage.identity for stage in reordered.stages)

    started = reordered.start_risk_reviewer()
    assert tuple(stage.identity for stage in started.stages) == expected_order
    assert started.stage(StageIdentity.RISK_REVIEWER).status is StageStatus.RUNNING

    completed = started.complete_risk_reviewer(risk_assessment())
    assert tuple(stage.identity for stage in completed.stages) == expected_order
    assert completed.stage(StageIdentity.RISK_REVIEWER).status is StageStatus.COMPLETED

    failed = reordered.start_risk_reviewer().fail_risk_reviewer(risk_error())
    assert tuple(stage.identity for stage in failed.stages) == expected_order
    assert failed.stage(StageIdentity.RISK_REVIEWER).status is StageStatus.FAILED


def critic_error() -> ReviewError:
    return ReviewError(
        kind=ReviewErrorKind.EXECUTION,
        message="Critic execution failed",
    )


def risk_completed_review(
    original_input: ReviewInput,
    analysis: ProblemAnalysis,
    alternatives: SolutionAlternatives,
    assessment: RiskAssessment,
) -> Review:
    return (
        architect_completed_review(original_input, analysis, alternatives)
        .start_risk_reviewer()
        .complete_risk_reviewer(assessment)
    )


def test_start_critic_records_exact_four_trusted_upstream_inputs() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    completed = risk_completed_review(
        original_input,
        analysis,
        alternatives,
        assessment,
    )
    previous_analyst = completed.stage(StageIdentity.ANALYST)
    previous_architect = completed.stage(StageIdentity.SOLUTION_ARCHITECT)
    previous_reviewer = completed.stage(StageIdentity.RISK_REVIEWER)
    previous_coordinator = completed.stage(StageIdentity.COORDINATOR)

    started = completed.start_critic()

    critic = started.stage(StageIdentity.CRITIC)
    assert started.status is ReviewStatus.RUNNING
    assert critic.status is StageStatus.RUNNING
    assert isinstance(critic.inputs, CriticStageInput)
    assert critic.inputs.review_input is original_input
    assert critic.inputs.problem_analysis is analysis
    assert critic.inputs.solution_alternatives is alternatives
    assert critic.inputs.risk_assessment is assessment
    assert critic.output is None
    assert critic.error is None
    assert started.stage(StageIdentity.ANALYST) is previous_analyst
    assert started.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert started.stage(StageIdentity.RISK_REVIEWER) is previous_reviewer
    assert started.stage(StageIdentity.COORDINATOR) is previous_coordinator
    assert started.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_start_critic_rejects_premature_or_repeated_start() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    running = Review.create(original_input).start()

    with pytest.raises(ValueError):
        running.start_critic()

    analyst_completed = running.start_analyst().complete_analyst(analysis)
    with pytest.raises(ValueError):
        analyst_completed.start_critic()

    architect_completed = (
        analyst_completed
        .start_solution_architect()
        .complete_solution_architect(alternatives)
    )
    with pytest.raises(ValueError):
        architect_completed.start_critic()

    reviewer_running = architect_completed.start_risk_reviewer()
    with pytest.raises(ValueError):
        reviewer_running.start_critic()

    reviewer_completed = reviewer_running.complete_risk_reviewer(assessment)
    critic_running = reviewer_completed.start_critic()
    with pytest.raises(ValueError):
        critic_running.start_critic()


def test_complete_critic_preserves_recorded_inputs_and_exact_output() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    critical_review = CriticalReview()
    critic_running = risk_completed_review(
        original_input,
        analysis,
        alternatives,
        assessment,
    ).start_critic()
    running_stage = critic_running.stage(StageIdentity.CRITIC)
    assert isinstance(running_stage.inputs, CriticStageInput)
    recorded_inputs = running_stage.inputs
    previous_analyst = critic_running.stage(StageIdentity.ANALYST)
    previous_architect = critic_running.stage(StageIdentity.SOLUTION_ARCHITECT)
    previous_reviewer = critic_running.stage(StageIdentity.RISK_REVIEWER)
    previous_coordinator = critic_running.stage(StageIdentity.COORDINATOR)

    completed = critic_running.complete_critic(critical_review)

    critic = completed.stage(StageIdentity.CRITIC)
    assert completed.status is ReviewStatus.RUNNING
    assert critic.status is StageStatus.COMPLETED
    assert critic.inputs is recorded_inputs
    assert critic.output is critical_review
    assert critic.error is None
    assert completed.stage(StageIdentity.ANALYST) is previous_analyst
    assert completed.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert completed.stage(StageIdentity.RISK_REVIEWER) is previous_reviewer
    assert completed.stage(StageIdentity.COORDINATOR) is previous_coordinator
    assert completed.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_complete_critic_requires_running_stage() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    completed = risk_completed_review(
        original_input,
        analysis,
        alternatives,
        assessment,
    )

    with pytest.raises(ValueError):
        completed.complete_critic(CriticalReview())

    critic_completed = completed.start_critic().complete_critic(CriticalReview())
    with pytest.raises(ValueError):
        critic_completed.complete_critic(CriticalReview())


def test_fail_critic_atomically_preserves_upstream_work_and_recorded_inputs() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    critic_running = risk_completed_review(
        original_input,
        analysis,
        alternatives,
        assessment,
    ).start_critic()
    running_stage = critic_running.stage(StageIdentity.CRITIC)
    assert isinstance(running_stage.inputs, CriticStageInput)
    recorded_inputs = running_stage.inputs
    previous_analyst = critic_running.stage(StageIdentity.ANALYST)
    previous_architect = critic_running.stage(StageIdentity.SOLUTION_ARCHITECT)
    previous_reviewer = critic_running.stage(StageIdentity.RISK_REVIEWER)
    previous_coordinator = critic_running.stage(StageIdentity.COORDINATOR)
    error = critic_error()

    failed = critic_running.fail_critic(error)

    critic = failed.stage(StageIdentity.CRITIC)
    assert failed.status is ReviewStatus.INCOMPLETE
    assert critic.status is StageStatus.FAILED
    assert critic.inputs is recorded_inputs
    assert critic.output is None
    assert critic.error is error
    assert failed.stage(StageIdentity.ANALYST) is previous_analyst
    assert failed.stage(StageIdentity.SOLUTION_ARCHITECT) is previous_architect
    assert failed.stage(StageIdentity.RISK_REVIEWER) is previous_reviewer
    assert failed.stage(StageIdentity.COORDINATOR) is previous_coordinator
    assert failed.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING


def test_fail_critic_requires_running_stage_and_nonterminal_review() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    completed = risk_completed_review(
        original_input,
        analysis,
        alternatives,
        assessment,
    )

    with pytest.raises(ValueError):
        completed.fail_critic(critic_error())

    critic_completed = completed.start_critic().complete_critic(CriticalReview())
    with pytest.raises(ValueError):
        critic_completed.fail_critic(critic_error())

    critic_failed = completed.start_critic().fail_critic(critic_error())
    with pytest.raises(ValueError):
        critic_failed.fail_critic(critic_error())


def test_critic_transitions_use_identity_and_preserve_noncanonical_order() -> None:
    original_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    assessment = risk_assessment()
    canonical = risk_completed_review(
        original_input,
        analysis,
        alternatives,
        assessment,
    )
    reordered_stages = (
        canonical.stage(StageIdentity.COORDINATOR),
        canonical.stage(StageIdentity.CRITIC),
        canonical.stage(StageIdentity.ANALYST),
        canonical.stage(StageIdentity.RISK_REVIEWER),
        canonical.stage(StageIdentity.SOLUTION_ARCHITECT),
    )
    reordered = Review(
        review_input=original_input,
        status=ReviewStatus.RUNNING,
        stages=reordered_stages,
    )
    expected_order = tuple(stage.identity for stage in reordered.stages)

    started = reordered.start_critic()
    assert tuple(stage.identity for stage in started.stages) == expected_order
    assert started.stage(StageIdentity.CRITIC).status is StageStatus.RUNNING

    completed = started.complete_critic(CriticalReview())
    assert tuple(stage.identity for stage in completed.stages) == expected_order
    assert completed.stage(StageIdentity.CRITIC).status is StageStatus.COMPLETED

    failed = reordered.start_critic().fail_critic(critic_error())
    assert tuple(stage.identity for stage in failed.stages) == expected_order
    assert failed.stage(StageIdentity.CRITIC).status is StageStatus.FAILED
