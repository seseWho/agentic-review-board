from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from agentic_review_board.domain.analysis import ReviewInputSource
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import ConstraintReference


class RiskScopeKind(StrEnum):
    """Scope at which a material risk applies."""

    OVERALL = "OVERALL"
    ALTERNATIVES = "ALTERNATIVES"


class RiskScope(BaseModel):
    """Review-local scope for one material risk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: RiskScopeKind
    alternative_ids: tuple[StrictStr, ...] = ()

    @field_validator("alternative_ids")
    @classmethod
    def validate_alternative_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("alternative ids must not be empty")
        if len(values) != len(set(values)):
            raise ValueError("alternative ids must be unique")
        return values

    @model_validator(mode="after")
    def validate_scope_shape(self) -> Self:
        if self.kind is RiskScopeKind.OVERALL and self.alternative_ids:
            raise ValueError("overall scope cannot contain alternative ids")
        if self.kind is RiskScopeKind.ALTERNATIVES and not self.alternative_ids:
            raise ValueError("alternatives scope requires at least one alternative id")
        return self


class RiskBasisSource(StrEnum):
    """Trusted current-review artifact referenced as risk basis."""

    REVIEW_INPUT = "REVIEW_INPUT"
    PROBLEM_ANALYSIS = "PROBLEM_ANALYSIS"
    SOLUTION_ALTERNATIVE = "SOLUTION_ALTERNATIVE"


class ProblemAnalysisFindingKind(StrEnum):
    """ProblemAnalysis collection from which a risk basis originates."""

    FACT = "FACT"
    CONSTRAINT = "CONSTRAINT"
    ASSUMPTION = "ASSUMPTION"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    UNCERTAINTY = "UNCERTAINTY"


class SolutionAlternativeCharacteristicKind(StrEnum):
    """Alternative characteristic that materially supports a risk."""

    DESCRIPTION = "DESCRIPTION"
    ADVANTAGE = "ADVANTAGE"
    DISADVANTAGE = "DISADVANTAGE"
    ASSUMPTION = "ASSUMPTION"
    IMPLEMENTATION_COMPLEXITY = "IMPLEMENTATION_COMPLEXITY"
    RELEVANT_CONSTRAINT = "RELEVANT_CONSTRAINT"


class ReviewInputBasisReference(BaseModel):
    """Risk basis that resolves to one visible ReviewInput value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal[RiskBasisSource.REVIEW_INPUT] = RiskBasisSource.REVIEW_INPUT
    field: ReviewInputSource
    value: StrictStr

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class ProblemAnalysisBasisReference(BaseModel):
    """Risk basis that resolves to one Analyst finding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal[RiskBasisSource.PROBLEM_ANALYSIS] = RiskBasisSource.PROBLEM_ANALYSIS
    kind: ProblemAnalysisFindingKind
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


class SolutionAlternativeBasisReference(BaseModel):
    """Risk basis that resolves to one characteristic of a candidate alternative."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal[RiskBasisSource.SOLUTION_ALTERNATIVE] = RiskBasisSource.SOLUTION_ALTERNATIVE
    alternative_id: StrictStr
    characteristic: SolutionAlternativeCharacteristicKind
    value: StrictStr | ConstraintReference

    @field_validator("alternative_id")
    @classmethod
    def validate_alternative_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("alternative id must not be empty")
        return value

    @field_validator("value")
    @classmethod
    def validate_text_value(cls, value: str | ConstraintReference) -> str | ConstraintReference:
        if isinstance(value, str) and not value.strip():
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def validate_characteristic_value_shape(self) -> Self:
        if self.characteristic is SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT:
            if not isinstance(self.value, ConstraintReference):
                raise ValueError("relevant constraint basis requires ConstraintReference")
        elif not isinstance(self.value, str):
            raise ValueError("non-constraint alternative basis requires text value")
        return self


RiskBasisReference = Annotated[
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference,
    Field(discriminator="source"),
]


class Risk(BaseModel):
    """One grounded qualitative material risk identified by Risk Reviewer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: StrictStr
    category: StrictStr | None = None
    description: StrictStr
    affected_scope: RiskScope
    severity: QualitativeLevel
    basis: tuple[RiskBasisReference, ...]
    mitigation: StrictStr | None = None
    residual_uncertainty: StrictStr | None = None

    @field_validator("id", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text must not be empty")
        return value

    @field_validator("category", "mitigation", "residual_uncertainty")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional text must not be empty when provided")
        return value

    @model_validator(mode="after")
    def validate_basis(self) -> Self:
        if not self.basis:
            raise ValueError("risk basis must contain at least one reference")
        for index, reference in enumerate(self.basis):
            if reference in self.basis[:index]:
                raise ValueError("risk basis references must not contain exact duplicates")
        return self


class RiskAssessment(BaseModel):
    """Validated structured result produced by Risk Reviewer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risks: tuple[Risk, ...]
    overall_observations: tuple[StrictStr, ...]

    @field_validator("overall_observations")
    @classmethod
    def validate_observations(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("observations must not be empty")
        if len(values) != len(set(values)):
            raise ValueError("observations must be unique")
        return values

    @model_validator(mode="after")
    def validate_unique_risk_ids(self) -> Self:
        ids = [risk.id for risk in self.risks]
        if len(ids) != len(set(ids)):
            raise ValueError("risk ids must be unique within RiskAssessment")
        return self
