from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReferencedFinding:
    """Review-local finding with a stable identifier."""

    id: str
    text: str


@dataclass(frozen=True, slots=True)
class FactFinding:
    """Fact claimed from an explicit ReviewInput field."""

    id: str
    text: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class ProblemAnalysis:
    """Validated structured result produced by the Analyst."""

    objective: str
    facts: tuple[FactFinding, ...]
    constraints: tuple[ReferencedFinding, ...]
    assumptions: tuple[ReferencedFinding, ...]
    missing_information: tuple[ReferencedFinding, ...]
    uncertainties: tuple[ReferencedFinding, ...]
