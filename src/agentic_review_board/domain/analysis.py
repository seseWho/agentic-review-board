from enum import StrEnum

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator


class ReviewInputSource(StrEnum):
    """ReviewInput fields that may provide structural provenance for a fact."""

    DESCRIPTION = "description"
    TITLE = "title"
    OBJECTIVE = "objective"
    CONSTRAINTS = "constraints"
    CONTEXT = "context"
    STATED_FACTS = "stated_facts"


class AnalysisFinding(BaseModel):
    """Structured Analyst finding that is not classified as a user-provided fact."""

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


class FactFinding(BaseModel):
    """Fact structurally attributed to an explicit ReviewInput field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: StrictStr
    source_ref: ReviewInputSource
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


class ProblemAnalysis(BaseModel):
    """Validated structured result produced by the Analyst."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: StrictStr
    facts: list[FactFinding]
    constraints: list[AnalysisFinding]
    assumptions: list[AnalysisFinding]
    missing_information: list[AnalysisFinding]
    uncertainties: list[AnalysisFinding]

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("objective must not be empty")
        return value
