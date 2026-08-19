# Feature Specification: Review Input + Analyst v0.1

**Feature Branch**: `001-review-input-analyst`  
**Created**: 2026-08-19  
**Status**: Draft  
**Input**: First executable product increment derived from the canonical MVP documents.

## User Scenarios & Testing

### User Story 1 - Structure a review problem (Priority: P1)

As a professional user, I want a submitted review problem to be transformed into a structured analysis so that later review stages can reason from explicit facts, constraints, assumptions, missing information, and uncertainty.

**Why this priority**: Every downstream participant depends on a valid Analyst result. This is the smallest product increment that proves the review contracts and provider-independent participant boundary.

**Independent Test**: Supply a valid review problem and a deterministic Analyst response; verify that a validated `ProblemAnalysis` is produced with objective, facts, constraints, assumptions, missing information, and uncertainties kept structurally distinct.

**Acceptance Scenarios**:

1. **Given** a non-empty review description, **When** the Analyst returns a structurally valid response, **Then** the system produces a validated `ProblemAnalysis`.
2. **Given** user-provided facts or context, **When** the Analyst identifies facts, **Then** each fact exposes a reference to an allowed `ReviewInput` field.
3. **Given** assumptions are needed, **When** the Analyst returns them, **Then** they remain structurally separate from facts.
4. **Given** material information is missing, **When** the Analyst returns its analysis, **Then** missing information and uncertainty remain explicit.

---

### User Story 2 - Reject invalid review input (Priority: P1)

As a user, I want an empty review problem to be rejected immediately so that an invalid review never reaches an AI participant.

**Independent Test**: Attempt to create a review input whose description is empty or whitespace-only and verify that validation fails with a clear error.

**Acceptance Scenarios**:

1. **Given** an empty or whitespace-only description, **When** review input is created, **Then** validation rejects it.
2. **Given** a non-empty description with no optional fields, **When** review input is created, **Then** it is accepted.

---

### User Story 3 - Fail closed on invalid Analyst output (Priority: P1)

As a user, I want malformed Analyst output to fail explicitly so that untrusted generated data cannot silently become trusted review state.

**Independent Test**: Provide deterministic malformed Analyst outputs and verify that contract validation rejects them before any downstream use.

**Acceptance Scenarios**:

1. **Given** Analyst output missing a required collection, **When** it is validated, **Then** the Analyst execution fails explicitly.
2. **Given** a fact whose source reference is not an allowed `ReviewInput` field, **When** it is validated, **Then** the output is rejected.
3. **Given** duplicate review-local finding identifiers, **When** the output is validated, **Then** the output is rejected.

## Edge Cases

- Optional title, objective, constraints, context, and stated facts may all be absent.
- Empty collections are valid when no findings exist for that category.
- Text values containing only whitespace are invalid when the field is required.
- Finding identifiers must be unique within one `ProblemAnalysis`.
- A fact may reference only an explicit field of the current `ReviewInput`.
- This increment does not attempt semantic verification that a fact's text is perfectly entailed by its referenced source field; it guarantees structural provenance only.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST represent a review input containing a required description and optional title, objective, constraints, context, and stated facts.
- **FR-002**: The system MUST reject an empty or whitespace-only review description.
- **FR-003**: The original textual values supplied in `ReviewInput` MUST not be rewritten by this increment.
- **FR-004**: The Analyst MUST depend only on `ReviewInput` and a provider-neutral structured-generation capability.
- **FR-005**: The Analyst MUST produce a `ProblemAnalysis` containing objective, facts, constraints, assumptions, missing information, and uncertainties.
- **FR-006**: Facts MUST remain structurally distinct from assumptions.
- **FR-007**: Every fact MUST contain a review-local identifier and an allowed source reference to `ReviewInput`.
- **FR-008**: Constraints, assumptions, missing-information findings, and uncertainty findings MUST expose review-local identifiers.
- **FR-009**: Finding identifiers MUST be unique within a `ProblemAnalysis`.
- **FR-010**: Model-generated Analyst output MUST be treated as untrusted until validated.
- **FR-011**: Missing mandatory Analyst fields or structurally invalid values MUST cause explicit validation failure.
- **FR-012**: Invalid Analyst output MUST NOT be returned as a valid `ProblemAnalysis`.
- **FR-013**: The core behavior MUST be testable using a deterministic substitute instead of a live LLM.
- **FR-014**: The increment MUST NOT add UI, persistence, RAG, tool execution, external actions, or a concrete LLM provider SDK.

### Key Entities

- **ReviewInput**: Immutable representation of the current user-provided problem and optional context.
- **ProblemAnalysis**: Validated structured Analyst result.
- **FactFinding**: A fact with review-local ID, text, and explicit source reference.
- **ReferencedFinding**: A review-local finding used for constraints, assumptions, missing information, and uncertainties.
- **LLMPort**: Provider-neutral structured-generation boundary consumed by the Analyst.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All core tests for this increment run without network access or a real LLM.
- **SC-002**: A valid deterministic Analyst response produces a complete `ProblemAnalysis` in one participant invocation.
- **SC-003**: Every representative invalid structured response in the feature test suite fails before becoming a valid domain result.
- **SC-004**: No production dependency is required to implement this increment beyond the Python standard library.
- **SC-005**: The implementation preserves the architectural boundary between participant semantics and concrete model providers.
