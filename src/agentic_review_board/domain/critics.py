from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CriticReferenceSource(StrEnum):
    """Trusted current-review artifact family referenced by Critic."""

    REVIEW_INPUT = "REVIEW_INPUT"
    PROBLEM_ANALYSIS = "PROBLEM_ANALYSIS"
    SOLUTION_ALTERNATIVES = "SOLUTION_ALTERNATIVES"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"


class CriticReferenceKind(StrEnum):
    """Bounded Critic-specific vocabulary for visible upstream values."""

    DESCRIPTION = "DESCRIPTION"
    TITLE = "TITLE"
    REVIEW_OBJECTIVE = "REVIEW_OBJECTIVE"
    REVIEW_CONSTRAINT = "REVIEW_CONSTRAINT"
    CONTEXT = "CONTEXT"
    STATED_FACT = "STATED_FACT"

    PROBLEM_OBJECTIVE = "PROBLEM_OBJECTIVE"
    PROBLEM_FACT = "PROBLEM_FACT"
    PROBLEM_CONSTRAINT = "PROBLEM_CONSTRAINT"
    PROBLEM_ASSUMPTION = "PROBLEM_ASSUMPTION"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    UNCERTAINTY = "UNCERTAINTY"

    ALTERNATIVE = "ALTERNATIVE"
    ALTERNATIVE_NAME = "ALTERNATIVE_NAME"
    ALTERNATIVE_DESCRIPTION = "ALTERNATIVE_DESCRIPTION"
    ADVANTAGE = "ADVANTAGE"
    DISADVANTAGE = "DISADVANTAGE"
    ALTERNATIVE_ASSUMPTION = "ALTERNATIVE_ASSUMPTION"
    IMPLEMENTATION_COMPLEXITY = "IMPLEMENTATION_COMPLEXITY"
    GENERATION_EXPLANATION = "GENERATION_EXPLANATION"
    BLOCKING_MISSING_INFORMATION = "BLOCKING_MISSING_INFORMATION"
    BLOCKING_UNCERTAINTY = "BLOCKING_UNCERTAINTY"

    RISK = "RISK"
    RISK_CATEGORY = "RISK_CATEGORY"
    RISK_DESCRIPTION = "RISK_DESCRIPTION"
    RISK_SEVERITY = "RISK_SEVERITY"
    MITIGATION = "MITIGATION"
    RESIDUAL_UNCERTAINTY = "RESIDUAL_UNCERTAINTY"
    OVERALL_OBSERVATION = "OVERALL_OBSERVATION"


_REVIEW_INPUT_KINDS = frozenset(
    {
        CriticReferenceKind.DESCRIPTION,
        CriticReferenceKind.TITLE,
        CriticReferenceKind.REVIEW_OBJECTIVE,
        CriticReferenceKind.REVIEW_CONSTRAINT,
        CriticReferenceKind.CONTEXT,
        CriticReferenceKind.STATED_FACT,
    }
)

_PROBLEM_ANALYSIS_KINDS = frozenset(
    {
        CriticReferenceKind.PROBLEM_OBJECTIVE,
        CriticReferenceKind.PROBLEM_FACT,
        CriticReferenceKind.PROBLEM_CONSTRAINT,
        CriticReferenceKind.PROBLEM_ASSUMPTION,
        CriticReferenceKind.MISSING_INFORMATION,
        CriticReferenceKind.UNCERTAINTY,
    }
)

_SOLUTION_ALTERNATIVES_KINDS = frozenset(
    {
        CriticReferenceKind.ALTERNATIVE,
        CriticReferenceKind.ALTERNATIVE_NAME,
        CriticReferenceKind.ALTERNATIVE_DESCRIPTION,
        CriticReferenceKind.ADVANTAGE,
        CriticReferenceKind.DISADVANTAGE,
        CriticReferenceKind.ALTERNATIVE_ASSUMPTION,
        CriticReferenceKind.IMPLEMENTATION_COMPLEXITY,
        CriticReferenceKind.GENERATION_EXPLANATION,
        CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
        CriticReferenceKind.BLOCKING_UNCERTAINTY,
    }
)

_RISK_ASSESSMENT_KINDS = frozenset(
    {
        CriticReferenceKind.RISK,
        CriticReferenceKind.RISK_CATEGORY,
        CriticReferenceKind.RISK_DESCRIPTION,
        CriticReferenceKind.RISK_SEVERITY,
        CriticReferenceKind.MITIGATION,
        CriticReferenceKind.RESIDUAL_UNCERTAINTY,
        CriticReferenceKind.OVERALL_OBSERVATION,
    }
)

_LEGAL_KINDS_BY_SOURCE = {
    CriticReferenceSource.REVIEW_INPUT: _REVIEW_INPUT_KINDS,
    CriticReferenceSource.PROBLEM_ANALYSIS: _PROBLEM_ANALYSIS_KINDS,
    CriticReferenceSource.SOLUTION_ALTERNATIVES: _SOLUTION_ALTERNATIVES_KINDS,
    CriticReferenceSource.RISK_ASSESSMENT: _RISK_ASSESSMENT_KINDS,
}

_VALUE_ONLY_KINDS = frozenset(
    {
        CriticReferenceKind.DESCRIPTION,
        CriticReferenceKind.TITLE,
        CriticReferenceKind.REVIEW_OBJECTIVE,
        CriticReferenceKind.REVIEW_CONSTRAINT,
        CriticReferenceKind.CONTEXT,
        CriticReferenceKind.STATED_FACT,
        CriticReferenceKind.PROBLEM_OBJECTIVE,
        CriticReferenceKind.GENERATION_EXPLANATION,
        CriticReferenceKind.OVERALL_OBSERVATION,
    }
)

_OPTIONAL_FINDING_ID_KINDS = frozenset(
    {
        CriticReferenceKind.PROBLEM_FACT,
        CriticReferenceKind.PROBLEM_CONSTRAINT,
        CriticReferenceKind.PROBLEM_ASSUMPTION,
        CriticReferenceKind.MISSING_INFORMATION,
        CriticReferenceKind.UNCERTAINTY,
        CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
        CriticReferenceKind.BLOCKING_UNCERTAINTY,
    }
)

_ID_PRIMARY_KINDS = frozenset(
    {
        CriticReferenceKind.ALTERNATIVE,
        CriticReferenceKind.RISK,
    }
)


class CriticReference(BaseModel):
    """Critic-specific exact reference to one visible current-review value."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    source: CriticReferenceSource
    kind: CriticReferenceKind
    item_id: str | None = None
    value: str | None = None

    @field_validator("item_id", "value")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("reference text must not be empty when provided")
        return value

    @model_validator(mode="after")
    def validate_reference_shape(self) -> Self:
        if self.kind not in _LEGAL_KINDS_BY_SOURCE[self.source]:
            raise ValueError("reference kind is not valid for source")

        if self.kind in _VALUE_ONLY_KINDS:
            if self.item_id is not None or self.value is None:
                raise ValueError(
                    "value-only reference requires value and forbids item_id"
                )
        elif self.kind in _OPTIONAL_FINDING_ID_KINDS:
            if self.value is None:
                raise ValueError("finding reference requires value")
        elif self.kind in _ID_PRIMARY_KINDS:
            if self.item_id is None:
                raise ValueError("ID-primary reference requires item_id")
        elif self.item_id is None or self.value is None:
            raise ValueError("nested reference requires item_id and value")

        return self


class CriticismImportance(StrEnum):
    """Qualitative importance of a Critic finding."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CriticismTargetType(StrEnum):
    """Semantic classification of the reasoning challenged by Critic."""

    ASSUMPTION = "ASSUMPTION"
    CONSTRAINT = "CONSTRAINT"
    ANALYSIS = "ANALYSIS"
    ALTERNATIVE = "ALTERNATIVE"
    ALTERNATIVE_CHARACTERISTIC = "ALTERNATIVE_CHARACTERISTIC"
    RISK = "RISK"
    MITIGATION = "MITIGATION"
    CROSS_ARTIFACT_CONCLUSION = "CROSS_ARTIFACT_CONCLUSION"
    OMISSION = "OMISSION"


class Criticism(BaseModel):
    """One evidence-constrained Critic challenge."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    target_type: CriticismTargetType
    target_reference: CriticReference | None = None
    basis_references: tuple[CriticReference, ...]
    issue: str
    importance: CriticismImportance
    rationale: str
    correction_or_question: str | None = None

    @field_validator("id", "issue", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value

    @field_validator("correction_or_question")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("optional text must not be empty when provided")
        return value

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        if self.target_reference is None and not self.basis_references:
            raise ValueError("criticism requires a target or basis reference")

        for index, reference in enumerate(self.basis_references):
            if reference in self.basis_references[:index]:
                raise ValueError("basis references must not contain exact duplicates")
            if reference == self.target_reference:
                raise ValueError("target reference must not be repeated as basis")

        return self


class ValidatedPoint(BaseModel):
    """One explicit upstream point that Critic considers adequately supported."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    target_reference: CriticReference
    rationale: str

    @field_validator("id", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value


class MissingAlternative(BaseModel):
    """One omitted alternative class without a generated replacement portfolio."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    category: str
    rationale: str
    weakens_later_recommendation: bool
    basis_references: tuple[CriticReference, ...] = Field(min_length=1)

    @field_validator("id", "category", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value

    @model_validator(mode="after")
    def validate_basis(self) -> Self:
        if not self.basis_references:
            raise ValueError(
                "missing alternative requires at least one basis reference"
            )

        for index, reference in enumerate(self.basis_references):
            if reference in self.basis_references[:index]:
                raise ValueError("basis references must not contain exact duplicates")

        return self


class ContradictionSide(BaseModel):
    """One visible proposition forming a side of a contradiction."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    reference: CriticReference
    statement: str

    @field_validator("statement")
    @classmethod
    def validate_statement(cls, value: str) -> str:
        if not value:
            raise ValueError("statement must not be empty")
        return value


class ContradictionSupportStatus(StrEnum):
    """Whether a contradiction is an unverified assertion or externally evidenced."""

    UNVERIFIED = "UNVERIFIED"
    EVIDENCED = "EVIDENCED"


class Contradiction(BaseModel):
    """Two visible propositions that cannot comfortably coexist as expressed."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    support_status: ContradictionSupportStatus = ContradictionSupportStatus.UNVERIFIED
    side_a: ContradictionSide
    side_b: ContradictionSide
    rationale: str

    @field_validator("id", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value

    @model_validator(mode="after")
    def validate_distinct_sides(self) -> Self:
        if self.side_a == self.side_b:
            raise ValueError("contradiction sides must not be identical")
        return self


class UnresolvedIssue(BaseModel):
    """One material issue that remains unresolved by visible current artifacts."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    issue: str
    rationale: str
    basis_references: tuple[CriticReference, ...] = Field(min_length=1)

    @field_validator("id", "issue", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text must not be empty")
        return value

    @model_validator(mode="after")
    def validate_basis(self) -> Self:
        if not self.basis_references:
            raise ValueError("unresolved issue requires at least one basis reference")

        for index, reference in enumerate(self.basis_references):
            if reference in self.basis_references[:index]:
                raise ValueError("basis references must not contain exact duplicates")

        return self


class CriticalReview(BaseModel):
    """Validated intrinsic Critic result; contextual trust is established later."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    criticisms: tuple[Criticism, ...] = ()
    validated_points: tuple[ValidatedPoint, ...] = ()
    missing_alternatives: tuple[MissingAlternative, ...] = ()
    contradictions: tuple[Contradiction, ...] = ()
    unresolved_issues: tuple[UnresolvedIssue, ...] = ()

    @model_validator(mode="after")
    def validate_aggregate_invariants(self) -> Self:
        for findings in (
            self.criticisms,
            self.validated_points,
            self.missing_alternatives,
            self.contradictions,
            self.unresolved_issues,
        ):
            ids = [finding.id for finding in findings]
            if len(ids) != len(set(ids)):
                raise ValueError("finding ids must be unique within each collection")

        targets = [point.target_reference for point in self.validated_points]
        if len(targets) != len(set(targets)):
            raise ValueError("validated point targets must be unique")

        categories = [finding.category for finding in self.missing_alternatives]
        if len(categories) != len(set(categories)):
            raise ValueError("missing alternative categories must be unique")

        for index, contradiction in enumerate(self.contradictions):
            for previous in self.contradictions[:index]:
                same_order = (
                    contradiction.side_a == previous.side_a
                    and contradiction.side_b == previous.side_b
                )
                reverse_order = (
                    contradiction.side_a == previous.side_b
                    and contradiction.side_b == previous.side_a
                )
                if same_order or reverse_order:
                    raise ValueError("contradiction side pairs must be unique")

        return self
