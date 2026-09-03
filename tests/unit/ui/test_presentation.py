from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import (
    Contradiction,
    ContradictionSide,
    ContradictionSupportStatus,
    CriticalReview,
    CriticReference,
    CriticReferenceKind,
    CriticReferenceSource,
)
from agentic_review_board.domain.execution import (
    CANONICAL_STAGE_ORDER,
    Review,
    ReviewError,
    ReviewErrorKind,
    ReviewStatus,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.final_reviews import (
    FinalReview,
    RankedAlternative,
    RecommendationOutcome,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import (
    AlternativeValidationStatus,
    SolutionAlternative,
    SolutionAlternatives,
)
from agentic_review_board.ui.presentation import (
    REVIEW_STATUS_LABELS,
    STAGE_DESCRIPTORS,
    STAGE_STATUS_LABELS,
    final_result,
    output_sections,
    stage_presentations,
    trusted_output,
)


def problem_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        objective="Compare two bounded approaches.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )


def solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives(
        alternatives=(
            SolutionAlternative(
                id="ALT-001",
                validation_status=AlternativeValidationStatus.PROPOSED,
                name="Local",
                description="Run locally.",
                advantages=("Local control.",),
                disadvantages=("Local operations.",),
                assumptions=("Capacity exists.",),
                implementation_complexity=QualitativeLevel.MEDIUM,
                relevant_constraints=(),
            ),
            SolutionAlternative(
                id="ALT-002",
                validation_status=AlternativeValidationStatus.EVIDENCED,
                name="Managed",
                description="Run in a managed service.",
                advantages=("Managed operations.",),
                disadvantages=("External dependency.",),
                assumptions=("Service is available.",),
                implementation_complexity=QualitativeLevel.MEDIUM,
                relevant_constraints=(),
            ),
        )
    )


def critical_review(review_input: ReviewInput) -> CriticalReview:
    return CriticalReview(
        contradictions=(
            Contradiction(
                id="CONTRA-001",
                support_status=ContradictionSupportStatus.UNVERIFIED,
                side_a=ContradictionSide(
                    reference=CriticReference(
                        source=CriticReferenceSource.REVIEW_INPUT,
                        kind=CriticReferenceKind.DESCRIPTION,
                        value=review_input.description,
                    ),
                    statement=review_input.description,
                ),
                side_b=ContradictionSide(
                    reference=CriticReference(
                        source=CriticReferenceSource.REVIEW_INPUT,
                        kind=CriticReferenceKind.TITLE,
                        value=review_input.title,
                    ),
                    statement=review_input.title or "",
                ),
                rationale="The two visible statements require verification.",
            ),
        )
    )


def completed_review() -> Review:
    created = Review.create(
        ReviewInput(description="Review this.", title="Technical Review")
    )
    review = created.start().start_analyst().complete_analyst(problem_analysis())
    review = review.start_solution_architect().complete_solution_architect(
        solution_alternatives()
    )
    review = review.start_risk_reviewer().complete_risk_reviewer(
        RiskAssessment(risks=(), overall_observations=())
    )
    review = review.start_critic().complete_critic(critical_review(review.review_input))
    final = FinalReview(
        situation_summary="Two approaches remain visible.",
        ranked_alternatives=(
            RankedAlternative(
                alternative_id="ALT-002",
                validation_status=AlternativeValidationStatus.EVIDENCED,
                position=1,
                justification="It has explicit evidence.",
                considerations=("Validate service availability.",),
            ),
            RankedAlternative(
                alternative_id="ALT-001",
                validation_status=AlternativeValidationStatus.PROPOSED,
                position=2,
                justification="It remains proposed.",
                considerations=("Validate local capacity.",),
            ),
        ),
        recommendation_outcome=RecommendationOutcome.RECOMMENDED,
        preferred_alternative_id="ALT-002",
        conclusion_rationale="Evidence currently favors ALT-002.",
        principal_risks=(),
        unresolved_questions=(),
        criticism_dispositions=(),
        next_validation_step="Validate service availability.",
        confidence=QualitativeLevel.MEDIUM,
    )
    return review.start_coordinator().complete_coordinator(final)


def test_descriptors_and_status_labels_are_exhaustive_and_readable() -> None:
    assert tuple(STAGE_DESCRIPTORS) == CANONICAL_STAGE_ORDER
    assert set(STAGE_STATUS_LABELS) == set(StageStatus)
    assert set(REVIEW_STATUS_LABELS) == set(ReviewStatus)
    assert len({descriptor.display_name for descriptor in STAGE_DESCRIPTORS.values()}) == 5
    assert all(descriptor.responsibility.strip() for descriptor in STAGE_DESCRIPTORS.values())
    assert all(descriptor.input_artifact_labels for descriptor in STAGE_DESCRIPTORS.values())
    assert all(descriptor.output_artifact_label for descriptor in STAGE_DESCRIPTORS.values())
    assert all(status.value.lower() in label.lower() for status, label in STAGE_STATUS_LABELS.items())


def test_stage_presentations_reference_exact_executions_and_descriptors() -> None:
    review = completed_review()

    presentations = stage_presentations(review)

    assert tuple(item.execution.identity for item in presentations) == CANONICAL_STAGE_ORDER
    for item in presentations:
        assert item.execution is review.stage(item.execution.identity)
        assert item.descriptor is STAGE_DESCRIPTORS[item.execution.identity]
        assert item.blocked_by is None


def test_blocked_stage_is_derived_only_downstream_of_trusted_failure() -> None:
    running = Review.create(ReviewInput(description="Failure Review.")).start()
    incomplete = running.start_analyst().fail_analyst(
        ReviewError(
            kind=ReviewErrorKind.OUTPUT_VALIDATION,
            message="Analyst output validation failed",
        )
    )

    presentations = stage_presentations(incomplete)

    assert presentations[0].execution.status is StageStatus.FAILED
    assert presentations[0].blocked_by is None
    assert all(
        item.execution.status is StageStatus.PENDING
        and item.blocked_by is StageIdentity.ANALYST
        for item in presentations[1:]
    )
    assert all(stage.status is not StageStatus.FAILED for stage in incomplete.stages[1:])


def test_trusted_output_is_available_only_for_completed_stage() -> None:
    created = Review.create(ReviewInput(description="Output trust Review."))
    running = created.start().start_analyst()
    failed = running.fail_analyst(
        ReviewError(kind=ReviewErrorKind.EXECUTION, message="Analyst execution failed")
    )
    completed = completed_review()

    assert trusted_output(created.stage(StageIdentity.ANALYST)) is None
    assert trusted_output(running.stage(StageIdentity.ANALYST)) is None
    assert trusted_output(failed.stage(StageIdentity.ANALYST)) is None
    for identity in CANONICAL_STAGE_ORDER:
        stage = completed.stage(identity)
        assert trusted_output(stage) is stage.output


def test_role_sections_preserve_empty_values_and_evidence_states() -> None:
    review = completed_review()
    expected_labels = {
        StageIdentity.ANALYST: (
            "Objective",
            "Facts",
            "Constraints",
            "Assumptions",
            "Missing information",
            "Uncertainties",
        ),
        StageIdentity.SOLUTION_ARCHITECT: ("Alternatives", "Generation notes"),
        StageIdentity.RISK_REVIEWER: ("Risks", "Overall observations"),
        StageIdentity.CRITIC: (
            "Criticisms",
            "Validated points",
            "Missing alternatives",
            "Contradictions",
            "Unresolved issues",
        ),
        StageIdentity.COORDINATOR: (
            "Situation summary",
            "Ranked alternatives",
            "Recommendation outcome",
            "Preferred alternative",
            "Conclusion rationale",
            "Principal risks",
            "Unresolved questions",
            "Criticism dispositions",
            "Next validation step",
            "Confidence",
            "Decision-support notice",
        ),
    }

    for identity, labels in expected_labels.items():
        sections = output_sections(review.stage(identity))
        assert tuple(section.label for section in sections) == labels
        assert all(section.value is not None or section.empty_message for section in sections)

    architect_sections = output_sections(review.stage(StageIdentity.SOLUTION_ARCHITECT))
    alternatives = architect_sections[0].value
    assert isinstance(alternatives, tuple)
    assert [alternative.validation_status for alternative in alternatives] == [
        AlternativeValidationStatus.PROPOSED,
        AlternativeValidationStatus.EVIDENCED,
    ]
    critic_sections = output_sections(review.stage(StageIdentity.CRITIC))
    contradictions = critic_sections[3].value
    assert isinstance(contradictions, tuple)
    assert contradictions[0].support_status is ContradictionSupportStatus.UNVERIFIED
    assert output_sections(
        Review.create(ReviewInput(description="Pending.")).stage(StageIdentity.ANALYST)
    ) == ()


def test_final_result_is_exact_and_only_available_after_completion() -> None:
    completed = completed_review()
    final = completed.stage(StageIdentity.COORDINATOR).output
    incomplete = Review.create(ReviewInput(description="Incomplete.")).start().start_analyst()
    incomplete = incomplete.fail_analyst(
        ReviewError(kind=ReviewErrorKind.EXECUTION, message="Analyst execution failed")
    )

    assert isinstance(final, FinalReview)
    assert final_result(completed) is final
    assert final_result(Review.create(ReviewInput(description="Not started."))) is None
    assert final_result(incomplete) is None
    assert final.recommendation_outcome is RecommendationOutcome.RECOMMENDED
    assert final.preferred_alternative_id == "ALT-002"
    assert isinstance(final.confidence, QualitativeLevel)
    assert not isinstance(final.confidence.value, (int, float))
    assert "human decision-making" in final.decision_support_notice
