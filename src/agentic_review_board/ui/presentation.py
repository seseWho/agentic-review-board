"""Pure mappings from trusted Review state to pedagogical presentation values."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.execution import (
    CANONICAL_STAGE_ORDER,
    Review,
    ReviewStatus,
    StageExecution,
    StageIdentity,
    StageOutput,
    StageStatus,
)
from agentic_review_board.domain.final_reviews import FinalReview
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives


@dataclass(frozen=True, slots=True)
class StageDescriptor:
    display_name: str
    responsibility: str
    input_artifact_labels: tuple[str, ...]
    output_artifact_label: str


STAGE_DESCRIPTORS: Mapping[StageIdentity, StageDescriptor] = MappingProxyType(
    {
        StageIdentity.ANALYST: StageDescriptor(
            display_name="Analyst",
            responsibility=(
                "Structure the problem, facts, assumptions, gaps, and uncertainty."
            ),
            input_artifact_labels=("ReviewInput",),
            output_artifact_label="ProblemAnalysis",
        ),
        StageIdentity.SOLUTION_ARCHITECT: StageDescriptor(
            display_name="Solution Architect",
            responsibility=(
                "Propose alternatives and explicit trade-offs within the known constraints."
            ),
            input_artifact_labels=("ReviewInput", "ProblemAnalysis"),
            output_artifact_label="SolutionAlternatives",
        ),
        StageIdentity.RISK_REVIEWER: StageDescriptor(
            display_name="Risk Reviewer",
            responsibility=(
                "Identify evidence-based risks, mitigations, and residual uncertainty."
            ),
            input_artifact_labels=(
                "ReviewInput",
                "ProblemAnalysis",
                "SolutionAlternatives",
            ),
            output_artifact_label="RiskAssessment",
        ),
        StageIdentity.CRITIC: StageDescriptor(
            display_name="Critic",
            responsibility=(
                "Challenge prior work, alternatives, contradictions, and unresolved issues."
            ),
            input_artifact_labels=(
                "ReviewInput",
                "ProblemAnalysis",
                "SolutionAlternatives",
                "RiskAssessment",
            ),
            output_artifact_label="CriticalReview",
        ),
        StageIdentity.COORDINATOR: StageDescriptor(
            display_name="Coordinator",
            responsibility=(
                "Synthesize trusted current-review artifacts into advisory decision support."
            ),
            input_artifact_labels=(
                "ReviewInput",
                "ProblemAnalysis",
                "SolutionAlternatives",
                "RiskAssessment",
                "CriticalReview",
            ),
            output_artifact_label="FinalReview",
        ),
    }
)

STAGE_STATUS_LABELS: Mapping[StageStatus, str] = MappingProxyType(
    {
        StageStatus.PENDING: "Pending — not started",
        StageStatus.RUNNING: "Running",
        StageStatus.COMPLETED: "Completed — trusted output",
        StageStatus.FAILED: "Failed — no trusted output",
    }
)

REVIEW_STATUS_LABELS: Mapping[ReviewStatus, str] = MappingProxyType(
    {
        ReviewStatus.CREATED: "Not started — Review created",
        ReviewStatus.RUNNING: "Review running",
        ReviewStatus.COMPLETED: "Review completed",
        ReviewStatus.INCOMPLETE: "Review incomplete",
    }
)


@dataclass(frozen=True, slots=True)
class StagePresentation:
    execution: StageExecution
    descriptor: StageDescriptor
    blocked_by: StageIdentity | None = None

    def __post_init__(self) -> None:
        if self.descriptor is not STAGE_DESCRIPTORS[self.execution.identity]:
            raise ValueError("stage descriptor does not match execution identity")


@dataclass(frozen=True, slots=True)
class OutputSection:
    label: str
    value: object | None
    empty_message: str | None = None


def stage_presentations(review: Review) -> tuple[StagePresentation, ...]:
    failed_identity = next(
        (
            identity
            for identity in CANONICAL_STAGE_ORDER
            if review.stage(identity).status is StageStatus.FAILED
        ),
        None,
    )
    failed_index = (
        CANONICAL_STAGE_ORDER.index(failed_identity)
        if failed_identity is not None
        else None
    )
    result: list[StagePresentation] = []
    for index, identity in enumerate(CANONICAL_STAGE_ORDER):
        execution = review.stage(identity)
        blocked_by = (
            failed_identity
            if review.status is ReviewStatus.INCOMPLETE
            and execution.status is StageStatus.PENDING
            and failed_index is not None
            and index > failed_index
            else None
        )
        result.append(
            StagePresentation(
                execution=execution,
                descriptor=STAGE_DESCRIPTORS[identity],
                blocked_by=blocked_by,
            )
        )
    return tuple(result)


def trusted_output(stage: StageExecution) -> StageOutput | None:
    if stage.status is not StageStatus.COMPLETED:
        return None
    if stage.output is None:
        raise ValueError("completed stage does not expose trusted output")
    return stage.output


def _section(label: str, value: object | None) -> OutputSection:
    if value is None:
        return OutputSection(label=label, value=None, empty_message="Not provided")
    if isinstance(value, tuple) and not value:
        return OutputSection(label=label, value=value, empty_message="No items")
    return OutputSection(label=label, value=value)


def output_sections(stage: StageExecution) -> tuple[OutputSection, ...]:
    output = trusted_output(stage)
    if output is None:
        return ()
    if isinstance(output, ProblemAnalysis):
        return (
            _section("Objective", output.objective),
            _section("Facts", output.facts),
            _section("Constraints", output.constraints),
            _section("Assumptions", output.assumptions),
            _section("Missing information", output.missing_information),
            _section("Uncertainties", output.uncertainties),
        )
    if isinstance(output, SolutionAlternatives):
        return (
            _section("Alternatives", output.alternatives),
            _section("Generation notes", output.generation_notes),
        )
    if isinstance(output, RiskAssessment):
        return (
            _section("Risks", output.risks),
            _section("Overall observations", output.overall_observations),
        )
    if isinstance(output, CriticalReview):
        return (
            _section("Criticisms", output.criticisms),
            _section("Validated points", output.validated_points),
            _section("Missing alternatives", output.missing_alternatives),
            _section("Contradictions", output.contradictions),
            _section("Unresolved issues", output.unresolved_issues),
        )
    if isinstance(output, FinalReview):
        return (
            _section("Situation summary", output.situation_summary),
            _section("Ranked alternatives", output.ranked_alternatives),
            _section("Recommendation outcome", output.recommendation_outcome),
            _section("Preferred alternative", output.preferred_alternative_id),
            _section("Conclusion rationale", output.conclusion_rationale),
            _section("Principal risks", output.principal_risks),
            _section("Unresolved questions", output.unresolved_questions),
            _section("Criticism dispositions", output.criticism_dispositions),
            _section("Next validation step", output.next_validation_step),
            _section("Confidence", output.confidence),
            _section("Decision-support notice", output.decision_support_notice),
        )
    raise ValueError("unsupported trusted stage output")


def final_result(review: Review) -> FinalReview | None:
    if review.status is not ReviewStatus.COMPLETED:
        return None
    output = trusted_output(review.stage(StageIdentity.COORDINATOR))
    if not isinstance(output, FinalReview):
        raise ValueError("completed Review does not expose trusted FinalReview")
    return output
