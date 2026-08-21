from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator, model_validator

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.solutions import SolutionAlternatives


class StageIdentity(StrEnum):
    """Canonical review stage identities in execution order."""

    ANALYST = "ANALYST"
    SOLUTION_ARCHITECT = "SOLUTION_ARCHITECT"
    RISK_REVIEWER = "RISK_REVIEWER"
    CRITIC = "CRITIC"
    COORDINATOR = "COORDINATOR"


class StageStatus(StrEnum):
    """Observable lifecycle state of one stage execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewStatus(StrEnum):
    """Observable lifecycle state of one complete review execution."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    INCOMPLETE = "INCOMPLETE"
    COMPLETED = "COMPLETED"


class ReviewErrorKind(StrEnum):
    """Provider-neutral failure categories exposed by review execution."""

    OUTPUT_VALIDATION = "OUTPUT_VALIDATION"
    EXECUTION = "EXECUTION"


class ReviewError(BaseModel):
    """Concise trusted failure information retained by a failed stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ReviewErrorKind
    message: StrictStr

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be empty")
        return value


class AnalystStageInput(BaseModel):
    """Trusted in-memory input provenance for Analyst execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_input: ReviewInput


class SolutionArchitectStageInput(BaseModel):
    """Trusted in-memory input provenance for Solution Architect execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_input: ReviewInput
    problem_analysis: ProblemAnalysis


StageInput = AnalystStageInput | SolutionArchitectStageInput
StageOutput = ProblemAnalysis | SolutionAlternatives


class StageExecution(BaseModel):
    """Validated local execution record for one canonical review stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: StageIdentity
    status: StageStatus
    inputs: StageInput | None = None
    output: StageOutput | None = None
    error: ReviewError | None = None

    @model_validator(mode="after")
    def validate_local_execution_state(self) -> Self:
        self._validate_status_shape()
        self._validate_identity_types()
        return self

    def _validate_status_shape(self) -> None:
        if self.status is StageStatus.PENDING:
            if self.inputs is not None or self.output is not None or self.error is not None:
                raise ValueError("pending stage must not contain inputs, output, or error")
            return

        if self.status is StageStatus.RUNNING:
            if self.inputs is None or self.output is not None or self.error is not None:
                raise ValueError("running stage requires inputs and forbids output or error")
            return

        if self.status is StageStatus.COMPLETED:
            if self.inputs is None or self.output is None or self.error is not None:
                raise ValueError("completed stage requires inputs and output and forbids error")
            return

        if self.status is StageStatus.FAILED:
            if self.inputs is None or self.output is not None or self.error is None:
                raise ValueError("failed stage requires inputs and error and forbids output")
            return

        raise ValueError("unsupported stage status")

    def _validate_identity_types(self) -> None:
        if self.identity is StageIdentity.ANALYST:
            if self.status is not StageStatus.PENDING and not isinstance(
                self.inputs, AnalystStageInput
            ):
                raise ValueError("Analyst stage requires AnalystStageInput")
            if self.status is StageStatus.COMPLETED and not isinstance(
                self.output, ProblemAnalysis
            ):
                raise ValueError("completed Analyst stage requires ProblemAnalysis output")
            return

        if self.identity is StageIdentity.SOLUTION_ARCHITECT:
            if self.status is not StageStatus.PENDING and not isinstance(
                self.inputs, SolutionArchitectStageInput
            ):
                raise ValueError("Solution Architect stage requires SolutionArchitectStageInput")
            if self.status is StageStatus.COMPLETED and not isinstance(
                self.output, SolutionAlternatives
            ):
                raise ValueError(
                    "completed Solution Architect stage requires SolutionAlternatives output"
                )
            return

        if self.status is not StageStatus.PENDING:
            raise ValueError("unimplemented Slice 3 stages must remain pending")


CANONICAL_STAGE_ORDER: tuple[StageIdentity, ...] = (
    StageIdentity.ANALYST,
    StageIdentity.SOLUTION_ARCHITECT,
    StageIdentity.RISK_REVIEWER,
    StageIdentity.CRITIC,
    StageIdentity.COORDINATOR,
)


class Review(BaseModel):
    """Immutable in-memory aggregate for one review execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_input: ReviewInput
    status: ReviewStatus
    stages: tuple[StageExecution, ...]

    @model_validator(mode="after")
    def validate_review_state(self) -> Self:
        self._validate_canonical_stage_set()
        self._validate_same_execution_provenance()
        self._validate_lifecycle_consistency()
        return self

    def _validate_canonical_stage_set(self) -> None:
        identities = tuple(stage.identity for stage in self.stages)
        if identities != CANONICAL_STAGE_ORDER:
            raise ValueError("review must contain the five canonical stages in canonical order")

    def _validate_same_execution_provenance(self) -> None:
        analyst = self.stages[0]
        architect = self.stages[1]

        if analyst.status is not StageStatus.PENDING:
            if not isinstance(analyst.inputs, AnalystStageInput):
                raise ValueError("executed Analyst stage must expose AnalystStageInput")
            if analyst.inputs.review_input is not self.review_input:
                raise ValueError("Analyst input must reference the current ReviewInput instance")

        if architect.status is not StageStatus.PENDING:
            if not isinstance(architect.inputs, SolutionArchitectStageInput):
                raise ValueError(
                    "executed Solution Architect stage must expose SolutionArchitectStageInput"
                )
            if architect.inputs.review_input is not self.review_input:
                raise ValueError(
                    "Solution Architect input must reference the current ReviewInput instance"
                )
            if analyst.status is not StageStatus.COMPLETED:
                raise ValueError("Solution Architect requires a completed Analyst stage")
            if not isinstance(analyst.output, ProblemAnalysis):
                raise ValueError("completed Analyst stage must expose ProblemAnalysis")
            if architect.inputs.problem_analysis is not analyst.output:
                raise ValueError(
                    "Solution Architect must reference the exact current Analyst output instance"
                )

    def _validate_lifecycle_consistency(self) -> None:
        analyst = self.stages[0]
        architect = self.stages[1]
        later = self.stages[2:]

        if any(stage.status is not StageStatus.PENDING for stage in later):
            raise ValueError("later Slice 3 stages must remain pending")

        if self.status is ReviewStatus.CREATED:
            if any(stage.status is not StageStatus.PENDING for stage in self.stages):
                raise ValueError("created review requires all stages pending")
            return

        if self.status is ReviewStatus.RUNNING:
            valid_prefixes = {
                (StageStatus.PENDING, StageStatus.PENDING),
                (StageStatus.RUNNING, StageStatus.PENDING),
                (StageStatus.COMPLETED, StageStatus.PENDING),
                (StageStatus.COMPLETED, StageStatus.RUNNING),
                (StageStatus.COMPLETED, StageStatus.COMPLETED),
            }
            if (analyst.status, architect.status) not in valid_prefixes:
                raise ValueError("running review has an invalid Slice 3 stage prefix")
            return

        if self.status is ReviewStatus.INCOMPLETE:
            valid_failures = {
                (StageStatus.FAILED, StageStatus.PENDING),
                (StageStatus.COMPLETED, StageStatus.FAILED),
            }
            if (analyst.status, architect.status) not in valid_failures:
                raise ValueError("incomplete review must contain one failed implemented stage")
            return

        if self.status is ReviewStatus.COMPLETED:
            if any(stage.status is not StageStatus.COMPLETED for stage in self.stages):
                raise ValueError("completed review requires all five stages completed")
            return

        raise ValueError("unsupported review status")

    @classmethod
    def create(cls, review_input: ReviewInput) -> "Review":
        return cls(
            review_input=review_input,
            status=ReviewStatus.CREATED,
            stages=tuple(
                StageExecution(identity=identity, status=StageStatus.PENDING)
                for identity in CANONICAL_STAGE_ORDER
            ),
        )
