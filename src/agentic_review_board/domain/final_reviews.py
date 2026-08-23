from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, StrictInt, field_validator, model_validator


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
