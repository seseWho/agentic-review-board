# Data Model: Review Input + Analyst v0.1

## ReviewInput

Immutable representation of the user-provided review problem.

Fields:

- `description: str` — required, non-empty after whitespace check.
- `title: str | None`
- `objective: str | None`
- `constraints: tuple[str, ...]`
- `context: tuple[str, ...]`
- `stated_facts: tuple[str, ...]`

Invariant: textual values are preserved; only emptiness of the required description is validated.

## ReferencedFinding

Generic review-local finding.

Fields:

- `id: str`
- `text: str`

Used for:

- constraints;
- assumptions;
- missing information;
- uncertainties.

## FactFinding

Fact attributed to an explicit ReviewInput field.

Fields:

- `id: str`
- `text: str`
- `source_ref: str`

Allowed `source_ref` values:

- `description`
- `title`
- `objective`
- `constraints`
- `context`
- `stated_facts`

## ProblemAnalysis

Validated Analyst result.

Fields:

- `objective: str`
- `facts: tuple[FactFinding, ...]`
- `constraints: tuple[ReferencedFinding, ...]`
- `assumptions: tuple[ReferencedFinding, ...]`
- `missing_information: tuple[ReferencedFinding, ...]`
- `uncertainties: tuple[ReferencedFinding, ...]`

Invariants:

- all required collections exist;
- required textual fields are non-empty;
- every fact uses an allowed source reference;
- all finding IDs are unique within the `ProblemAnalysis`;
- facts and assumptions remain separate collections.

## LLMPort

Provider-neutral application boundary rather than a persisted entity.

Operation:

```text
generate_structured(role, payload) -> mapping
```

The returned mapping is untrusted until parsed and validated by the Analyst boundary.

## AnalystOutputError

Explicit validation failure for malformed or contract-invalid generated Analyst output.

This increment does not yet model full stage execution state; that belongs to the later orchestration increment.
