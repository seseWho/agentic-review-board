from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator


class RecommendationOutcome(StrEnum):
    """Whether current evidence supports a preferred alternative."""

    RECOMMENDED = "RECOMMENDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CriticismDispositionOutcome(StrEnum):
    """How Coordinator accounts for one current Critic criticism."""

    REFLECTED = "REFLECTED"
    DISMISSED = "DISMISSED"


class FinalReviewSection(StrEnum):
    """Bounded visible FinalReview sections affected by a criticism."""

    SITUATION_SUMMARY = "SITUATION_SUMMARY"
    RANKING = "RANKING"
    CONCLUSION = "CONCLUSION"
    PRINCIPAL_RISKS = "PRINCIPAL_RISKS"
    UNRESOLVED_QUESTIONS = "UNRESOLVED_QUESTIONS"
    NEXT_VALIDATION_STEP = "NEXT_VALIDATION_STEP"
    CONFIDENCE = "CONFIDENCE"


class RankedAlternative(BaseModel):
    """One explicit position assigned to an existing alternative."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    alternative_id: str
    position: StrictInt
    justification: str
    considerations: tuple[str, ...]
    conditions_that_could_change_ranking: tuple[str, ...] = ()

    @field_validator("alternative_id", "justification")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("position must be positive")
        return value

    @field_validator("considerations", "conditions_that_could_change_ranking")
    @classmethod
    def validate_text_collection(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value for value in values):
            raise ValueError("collection items must not be empty")
        if len(values) != len(set(values)):
            raise ValueError("collection items must be unique")
        return values

    @model_validator(mode="after")
    def validate_considerations(self) -> Self:
        if not self.considerations:
            raise ValueError("ranked alternative requires at least one consideration")
        return self


class PrincipalRisk(BaseModel):
    """Decision-relevant selection of one existing upstream risk."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    risk_id: str
    rationale: str

    @field_validator("risk_id", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value



class UnresolvedQuestionSource(StrEnum):
    """Current upstream artifact family owning an unresolved item."""

    PROBLEM_ANALYSIS = "PROBLEM_ANALYSIS"
    SOLUTION_ALTERNATIVES = "SOLUTION_ALTERNATIVES"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    CRITICAL_REVIEW = "CRITICAL_REVIEW"


class ProblemUnresolvedKind(StrEnum):
    """Supported unresolved ProblemAnalysis collections."""

    PROBLEM_ASSUMPTION = "PROBLEM_ASSUMPTION"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    UNCERTAINTY = "UNCERTAINTY"


class SolutionUnresolvedKind(StrEnum):
    """Supported unresolved SolutionAlternatives values."""

    ALTERNATIVE_ASSUMPTION = "ALTERNATIVE_ASSUMPTION"
    BLOCKING_MISSING_INFORMATION = "BLOCKING_MISSING_INFORMATION"
    BLOCKING_UNCERTAINTY = "BLOCKING_UNCERTAINTY"


class CriticUnresolvedKind(StrEnum):
    """Supported unresolved CriticalReview finding collections."""

    MISSING_ALTERNATIVE = "MISSING_ALTERNATIVE"
    CONTRADICTION = "CONTRADICTION"
    UNRESOLVED_ISSUE = "UNRESOLVED_ISSUE"


class ProblemUnresolvedReference(BaseModel):
    """Coordinator-specific reference to one unresolved Analyst finding."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    source: Literal[UnresolvedQuestionSource.PROBLEM_ANALYSIS] = (
        UnresolvedQuestionSource.PROBLEM_ANALYSIS
    )
    kind: ProblemUnresolvedKind
    value: str
    item_id: str | None = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("item_id")
    @classmethod
    def validate_optional_id(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("item_id must not be empty when provided")
        return value


class SolutionUnresolvedReference(BaseModel):
    """Coordinator-specific reference to an alternative assumption or generation blocker."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    source: Literal[UnresolvedQuestionSource.SOLUTION_ALTERNATIVES] = (
        UnresolvedQuestionSource.SOLUTION_ALTERNATIVES
    )
    kind: SolutionUnresolvedKind
    value: str
    alternative_id: str | None = None
    item_id: str | None = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("alternative_id", "item_id")
    @classmethod
    def validate_optional_id(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("identifier must not be empty when provided")
        return value

    @model_validator(mode="after")
    def validate_kind_shape(self) -> Self:
        if self.kind is SolutionUnresolvedKind.ALTERNATIVE_ASSUMPTION:
            if self.alternative_id is None or self.item_id is not None:
                raise ValueError(
                    "alternative assumption requires alternative_id and forbids item_id"
                )
        elif self.alternative_id is not None:
            raise ValueError("generation blocker forbids alternative_id")
        return self


class RiskUnresolvedReference(BaseModel):
    """Coordinator-specific reference to one current residual risk uncertainty."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    source: Literal[UnresolvedQuestionSource.RISK_ASSESSMENT] = (
        UnresolvedQuestionSource.RISK_ASSESSMENT
    )
    risk_id: str
    value: str

    @field_validator("risk_id", "value")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value


class CriticUnresolvedReference(BaseModel):
    """Coordinator-specific reference to one unresolved Critic finding."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    source: Literal[UnresolvedQuestionSource.CRITICAL_REVIEW] = (
        UnresolvedQuestionSource.CRITICAL_REVIEW
    )
    kind: CriticUnresolvedKind
    item_id: str
    value: str

    @field_validator("item_id", "value")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value


UnresolvedQuestionReference = Annotated[
    ProblemUnresolvedReference
    | SolutionUnresolvedReference
    | RiskUnresolvedReference
    | CriticUnresolvedReference,
    Field(discriminator="source"),
]


class UnresolvedQuestion(BaseModel):
    """One final decision question grounded in a visible unresolved upstream item."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    reference: UnresolvedQuestionReference
    question: str
    rationale: str

    @field_validator("id", "question", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value


class CriticismDisposition(BaseModel):
    """How Coordinator visibly accounts for one current Critic criticism."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    criticism_id: str
    outcome: CriticismDispositionOutcome
    rationale: str
    reflected_in: tuple[FinalReviewSection, ...] = ()

    @field_validator("criticism_id", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value

    @field_validator("reflected_in")
    @classmethod
    def validate_unique_sections(
        cls,
        values: tuple[FinalReviewSection, ...],
    ) -> tuple[FinalReviewSection, ...]:
        if len(values) != len(set(values)):
            raise ValueError("reflected sections must be unique")
        return values

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> Self:
        if self.outcome is CriticismDispositionOutcome.REFLECTED:
            if not self.reflected_in:
                raise ValueError("reflected criticism requires at least one final section")
        elif self.reflected_in:
            raise ValueError("dismissed criticism must not identify reflected sections")
        return self
