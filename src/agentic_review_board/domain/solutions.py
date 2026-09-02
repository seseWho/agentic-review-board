from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator, model_validator

from agentic_review_board.domain.shared import QualitativeLevel


class ConstraintSource(StrEnum):
    """Trusted upstream artifact that owns a referenced constraint."""

    REVIEW_INPUT = "REVIEW_INPUT"
    PROBLEM_ANALYSIS = "PROBLEM_ANALYSIS"


class ConstraintReferenceKind(StrEnum):
    """How a constraint is identified within its declared upstream source."""

    TEXT = "TEXT"
    ID = "ID"


class AlternativeValidationStatus(StrEnum):
    """Whether an alternative is merely proposed or backed by validation evidence."""

    PROPOSED = "PROPOSED"
    EVIDENCED = "EVIDENCED"


class ConstraintReference(BaseModel):
    """Explicit review-local reference to a known upstream constraint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: ConstraintSource
    kind: ConstraintReferenceKind
    value: StrictStr

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def validate_source_kind_compatibility(self) -> Self:
        if self.source is ConstraintSource.REVIEW_INPUT and self.kind is ConstraintReferenceKind.ID:
            raise ValueError("ReviewInput constraints do not support ID references")
        return self


class FindingReference(BaseModel):
    """Local readable reference to an Analyst finding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: StrictStr
    id: StrictStr | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value

    @field_validator("id")
    @classmethod
    def validate_optional_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("id must not be empty when provided")
        return value


class GenerationNotes(BaseModel):
    """Structured generation context and explicit no-alternative blockers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    explanation: StrictStr
    blocking_missing_information: tuple[FindingReference, ...]
    blocking_uncertainties: tuple[FindingReference, ...]

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation must not be empty")
        return value


class SolutionAlternative(BaseModel):
    """One candidate approach proposed by the Solution Architect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: StrictStr
    validation_status: AlternativeValidationStatus = AlternativeValidationStatus.PROPOSED
    name: StrictStr
    description: StrictStr
    advantages: tuple[StrictStr, ...]
    disadvantages: tuple[StrictStr, ...]
    assumptions: tuple[StrictStr, ...]
    implementation_complexity: QualitativeLevel
    relevant_constraints: tuple[ConstraintReference, ...]

    @field_validator("id", "name", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text must not be empty")
        return value

    @field_validator("advantages", "disadvantages", "assumptions")
    @classmethod
    def validate_text_collection(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("collection items must not be empty")
        return values


class SolutionAlternatives(BaseModel):
    """Validated structured result produced by the Solution Architect."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    alternatives: tuple[SolutionAlternative, ...]
    generation_notes: GenerationNotes | None = None

    @model_validator(mode="after")
    def validate_result_shape(self) -> Self:
        count = len(self.alternatives)
        if count not in {0, 2, 3}:
            raise ValueError("alternatives must contain exactly 0, 2, or 3 items")

        if count == 0 and self.generation_notes is None:
            raise ValueError("generation_notes are required when no alternatives are produced")

        ids = [alternative.id for alternative in self.alternatives]
        if len(ids) != len(set(ids)):
            raise ValueError("alternative ids must be unique within SolutionAlternatives")

        return self
