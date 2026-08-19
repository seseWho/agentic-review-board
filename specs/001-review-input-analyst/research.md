# Research: Review Input + Analyst v0.1

## Decision 1 — Use Python standard-library dataclasses for domain contracts

**Decision**: Implement `ReviewInput`, `ProblemAnalysis`, and finding types with frozen dataclasses.

**Rationale**: The current bootstrap has no production dependencies. The MVP requires explicit structured contracts but does not require a specific validation library. Standard-library dataclasses are sufficient for this first bounded increment and keep the architecture minimal.

**Alternatives considered**:

- Pydantic: strong validation ergonomics, but introduces a production dependency before a demonstrated need.
- Typed dictionaries only: lightweight, but weaker domain invariants and immutability.

## Decision 2 — Introduce a provider-neutral `LLMPort` Protocol

**Decision**: Define a minimal `Protocol` exposing structured generation as a mapping-based request/response boundary.

**Rationale**: The canonical architecture requires participant semantics to remain independent from provider SDKs and requires deterministic substitution for tests.

**Alternatives considered**:

- Concrete provider client: rejected because it violates provider independence.
- No port until a real provider exists: rejected because deterministic participant testing would then couple directly to implementation details.

## Decision 3 — Validate Analyst output inside the participant boundary for v0.1

**Decision**: The Analyst converts untrusted mapping output into trusted domain objects and raises an explicit `AnalystOutputError` when the contract is invalid.

**Rationale**: This gives the first increment a real validation boundary without introducing a generic validation framework prematurely.

**Alternatives considered**:

- Generic validation service: deferred because only one participant exists in this increment.
- UI-side validation: rejected by architecture and Constitution.

## Decision 4 — Structural provenance for facts

**Decision**: Every `FactFinding` contains a `source_ref` restricted to allowed `ReviewInput` fields.

**Rationale**: The MVP requires facts to be traceable to the original input. Exact semantic entailment cannot be guaranteed deterministically in this increment, but structural provenance can.

**Alternatives considered**:

- Exact substring matching: rejected because legitimate paraphrases would fail.
- No provenance field: rejected because traceability would remain implicit.

## Decision 5 — No application orchestrator yet

**Decision**: This increment exposes `ReviewInput`, `LLMPort`, and `Analyst` only. It does not introduce the full `Review`, `StageExecution`, or orchestrator lifecycle.

**Rationale**: Those concepts become necessary when more than one participant or user-visible execution state is implemented. Adding them now would create unused architecture.

**Alternatives considered**:

- Implement full five-stage orchestration shell now: rejected as premature complexity.

## Decision 6 — No real LLM or UI in this increment

**Decision**: Use deterministic fakes in tests and defer provider/UI integration.

**Rationale**: The first increment should prove contracts and boundaries before introducing nondeterministic external behavior.
