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
