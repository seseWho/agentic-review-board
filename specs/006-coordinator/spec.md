# Feature Specification: Coordinator v0.1

**Branch**: `006-coordinator`  
**Date**: 2026-08-23  
**Status**: Approved — reviewed against canonical documents; ready for planning

## 1. Purpose

Slice 6 introduces the Coordinator as the fifth and final executable participant in the Agentic Review Board MVP pipeline.

The Coordinator SHALL consolidate the complete validated review, order viable alternatives when comparison is justified, explain the position assigned to each alternative, and provide advisory decision support without replacing human decision authority.

It answers:

> Given the complete visible review, what conclusion is justified, how should the alternatives be ordered, and what still needs validation?

The completed execution sequence becomes:

```text
ReviewInput
    ↓
Analyst
    ↓ ProblemAnalysis
Solution Architect
    ↓ SolutionAlternatives
Risk Reviewer
    ↓ RiskAssessment
Critic
    ↓ CriticalReview
Coordinator
    ↓ FinalReview
```

Slice 6 SHALL preserve all accepted Slice 1–5 contracts unless an explicit approved change is required.

---

## 2. Canonical Source Alignment

This specification is constrained by:

- `docs/02-requirements.md`, especially FR-031 through FR-040 and FR-049 through FR-057;
- `docs/03-architecture.md`, including dependency order, validation, traceability, failure handling, provider independence, and human decision authority;
- `docs/04-agent-model.md`, including Coordinator inputs, output, ranking responsibility, invariants, and prohibited behavior;
- `docs/05-quality-security.md`;
- `.specify/memory/constitution.md`;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`;
- approved and merged Slice 1–5 contracts.

Where this specification does not define an implementation detail, the canonical documents remain authoritative.

---

## 3. Scope

### 3.1 In Scope

Slice 6 SHALL add the minimum behavior required to:

1. represent a validated Coordinator output as an explicit `FinalReview`;
2. consume exactly the current review's `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives`, `RiskAssessment`, and `CriticalReview`;
3. consolidate the visible situation, alternatives, risks, criticisms, validated points, contradictions, and unresolved issues;
4. rank every supplied alternative from most suitable to least suitable when multiple alternatives exist;
5. provide a justification and final considerations for every ranked alternative;
6. identify a preferred alternative only when the visible evidence supports doing so;
7. explicitly withhold recommendation when evidence is insufficient;
8. identify principal risks, unresolved questions, and a next validation step;
9. express confidence qualitatively rather than as an unsupported probability;
10. extend `StageExecution`, `Review`, transitions, and `ReviewOrchestrator` through Coordinator;
11. reach `ReviewStatus.COMPLETED` only after a valid Coordinator result;
12. fail closed on invalid Coordinator output while preserving all completed upstream artifacts.

### 3.2 Out of Scope

Slice 6 SHALL NOT introduce:

- autonomous execution or automatic acceptance of a recommendation;
- mutation or rewriting of upstream artifacts;
- new solution alternatives or a replacement portfolio;
- numeric scoring, weighted scoring, calibrated probabilities, or invented measurements;
- organization-specific decision policy absent from the current review;
- persistence, review history, RAG, browsing, external tools, or UI work;
- provider-specific SDK dependencies in domain/application;
- retries, timeouts, concurrency, distributed execution, or streaming;
- a generic workflow engine, stage registry, graph framework, or generic artifact-reference framework;
- comparison against previous reviews or hidden participant memory.

---

## 4. User Stories

### US1 — Produce a complete advisory review

As a user, I want the Coordinator to consolidate all validated review artifacts into one inspectable final result so that I can make the decision with the complete reasoning surface available.

#### Acceptance criteria

1. Coordinator receives all five exact current-execution upstream artifacts.
2. Coordinator returns a validated `FinalReview`.
3. The final result includes a concise situation summary, principal risks, unresolved questions, a next validation step, and qualitative confidence.
4. The final result contains an explicit decision-support notice stating that the result supports but does not replace human decision authority.
5. Coordinator does not silently alter any upstream artifact.

### US2 — Rank alternatives transparently

As a user, I want every proposed alternative ordered and individually justified so that the comparison is inspectable rather than hidden in a single recommendation.

#### Acceptance criteria

1. When multiple alternatives exist, every supplied alternative appears exactly once in the ranking.
2. Positions form one complete unambiguous order with no ties or gaps.
3. Each position identifies the exact existing alternative.
4. Each position includes a concise justification grounded in visible review artifacts.
5. Each position includes final considerations such as trade-offs, conditions, or material uncertainties.
6. Coordinator does not introduce a new alternative.
7. Ranking order is represented by explicit validated positions and is not derived implicitly from the tuple position of upstream alternatives.

### US3 — Recommend only when justified

As a user, I want the Coordinator to distinguish an evidence-supported preference from an insufficient-evidence outcome so that the system does not force a winner.

#### Acceptance criteria

1. When evidence is sufficient, the preferred alternative is one of the ranked existing alternatives.
2. The preferred alternative is consistent with the first-ranked position.
3. Recommendation rationale is based on visible review artifacts.
4. When evidence is insufficient, no preferred alternative is emitted.
5. The insufficient-evidence outcome states why recommendation is not justified.
6. Material unresolved information capable of changing the ranking remains visible.
7. Qualitative confidence does not imply statistical certainty.

### US4 — Handle zero alternatives honestly

As a user, I want the final result to remain valid when upstream work contains no alternatives so that Coordinator preserves insufficient evidence rather than fabricating comparison.

#### Acceptance criteria

1. With zero alternatives, ranking is empty and no preferred alternative is allowed.
2. With zero alternatives, the result explains why no recommendation can be justified.
3. Coordinator preserves the accepted upstream invariant that `SolutionAlternatives` contains exactly 0, 2, or 3 alternatives; a one-alternative input is not a valid trusted state.
4. No replacement alternatives are generated.

### US5 — Complete the five-stage lifecycle

As a user, I want Coordinator to execute only after all four upstream stages succeed and to complete the Review only with a valid final result.

#### Acceptance criteria

1. Coordinator starts only after Analyst, Solution Architect, Risk Reviewer, and Critic are `COMPLETED`.
2. Coordinator stage records the exact current `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives`, `RiskAssessment`, and `CriticalReview` instances.
3. Successful Coordinator execution produces Coordinator `COMPLETED` and Review `COMPLETED`.
4. Review `COMPLETED` is impossible without a trusted `FinalReview`.
5. Coordinator failure produces Coordinator `FAILED` and Review `INCOMPLETE`.
6. All successfully completed upstream stages remain unchanged and inspectable after Coordinator failure.

### US6 — Fail closed at the final trust boundary

As a user, I want malformed, inconsistent, or unsupported Coordinator output rejected so that an invalid ranking or recommendation cannot be presented as a completed review.

#### Acceptance criteria

1. Raw Coordinator output remains untrusted until structural and contextual validation succeed.
2. Unknown, duplicate, omitted, or invented alternative references fail validation.
3. An incomplete or inconsistent ranking fails validation.
4. A preferred alternative inconsistent with the ranking fails validation.
5. Invalid generated output stores no partial `FinalReview`.
6. Output-validation failure remains distinguishable from ordinary participant/model execution failure.
7. Provider exception details do not enter trusted Review state.
8. Internal domain/invariant failures outside the participant-call boundary are not silently converted into participant failures.
9. `BaseException` control signals are not swallowed.

---

## 5. Functional Requirements

### COORD-FR-001 — Explicit Coordinator Inputs

Coordinator SHALL receive exactly:

- current `ReviewInput`;
- validated `ProblemAnalysis`;
- validated `SolutionAlternatives`;
- validated `RiskAssessment`;
- validated `CriticalReview`.

### COORD-FR-002 — Structured FinalReview

Coordinator SHALL produce a structured `FinalReview` containing conceptually:

- situation summary;
- ranked alternatives;
- preferred alternative when justified;
- recommendation outcome;
- conclusion rationale;
- principal risks;
- unresolved questions;
- suggested next validation step;
- qualitative confidence;
- decision-support notice.

Exact field structure is deferred to data-model review.

### COORD-FR-003 — Complete Ranking

When multiple alternatives exist, the ranking SHALL:

- contain every existing alternative exactly once;
- contain no unknown alternative;
- define a total order without ties or gaps;
- provide justification and final considerations for every position.

### COORD-FR-004 — Existing Alternatives Only

Coordinator SHALL reference alternatives already present in `SolutionAlternatives`. It SHALL NOT generate, rename, merge, split, or replace alternatives.

### COORD-FR-005 — Evidence-Constrained Justification

Ranking and recommendation claims SHALL be grounded in visible current-review artifacts. Generated references, if included in the approved data model, SHALL resolve exactly and fail closed.

The data-model phase SHALL prefer the smallest Coordinator-specific traceability mechanism that satisfies canonical requirements and SHALL NOT introduce a generic artifact-reference framework without separate approval.

### COORD-FR-006 — Critic Is Advisory Input

Coordinator SHALL consider `CriticalReview`, including criticisms, validated points, missing alternatives, contradictions, and unresolved issues, but SHALL make the final ranking decision itself.

Every material criticism SHALL either:

- be visibly reflected in ranking justification, conclusion rationale, principal risks, unresolved questions, confidence, or the next validation step; or
- be explicitly identified as not decision-relevant, with a concise justification.

Critic findings SHALL NOT be treated as unquestionable facts or automatic ranking commands. Slice 6 SHALL NOT require a generic disposition matrix or a mechanical response to every validated point.

### COORD-FR-007 — Recommendation Outcome and Preferred Alternative Consistency

The recommendation outcome SHALL use exactly:

- `RECOMMENDED`;
- `INSUFFICIENT_EVIDENCE`.

The conclusion rationale SHALL always be required and non-empty.

When the outcome is `RECOMMENDED`:

- a preferred alternative SHALL be present;
- it SHALL identify an existing alternative;
- it SHALL be consistent with the top-ranked alternative;
- the conclusion rationale SHALL explain why the visible evidence supports preference.

When the outcome is `INSUFFICIENT_EVIDENCE`, preferred alternative SHALL be absent.

### COORD-FR-008 — Insufficient Evidence

When recommendation is not justified:

- preferred alternative SHALL be absent;
- the result SHALL explicitly state insufficient evidence;
- the reason SHALL be non-empty;
- unresolved information that materially blocks recommendation SHALL remain visible;
- the system SHALL NOT force a winner.

### COORD-FR-009 — Zero Alternatives

When `SolutionAlternatives.alternatives` is empty:

- ranking SHALL be empty;
- preferred alternative SHALL be absent;
- recommendation SHALL be withheld;
- the final result SHALL preserve the upstream explanation and identify the next validation need.

### COORD-FR-010 — Preserve Upstream Alternative Cardinality

Coordinator SHALL preserve the accepted `SolutionAlternatives` invariant that trusted upstream state contains exactly 0, 2, or 3 alternatives.

Slice 6 SHALL NOT expand that contract to admit one alternative. A directly constructed one-alternative value is invalid before Coordinator and is not a Coordinator edge case.

### COORD-FR-011 — Principal Risks

The final result SHALL expose material risks relevant to the conclusion without inventing risks absent from the visible review.

Principal risks SHALL reference exact existing `Risk.id` values and SHALL NOT duplicate or invent risks. The data-model phase SHALL define the smallest Coordinator-specific representation needed for this selection.

### COORD-FR-012 — Unresolved Questions

The final result SHALL preserve material missing information, uncertainty, contradictions, and unresolved issues that remain relevant to the human decision.

Where an upstream item has a stable explicit ID, the unresolved question SHALL reference it exactly. Bounded concise text MAY be used only for visible upstream values that have no stable ID. The data-model phase SHALL define Coordinator-specific reference shapes without introducing a generic artifact-reference framework.

### COORD-FR-013 — Suggested Next Validation Step

The final result SHALL always contain one concrete advisory next validation step, including when a recommendation is justified and confidence is high. It SHALL NOT execute the step or authorize an external action.

### COORD-FR-014 — Qualitative Confidence

Confidence SHALL use `LOW`, `MEDIUM`, or `HIGH`.

It represents strength of support in current artifacts, not calibrated probability. Numeric confidence or probability is forbidden.

### COORD-FR-015 — Preserve Fact and Assumption Semantics

Coordinator SHALL NOT promote an assumption to fact through repetition, ranking, validation, or recommendation.

### COORD-FR-016 — Structural Validation

Malformed, incomplete, extra-field, or wrong-type Coordinator output SHALL fail before entering trusted Review state.

### COORD-FR-017 — Contextual Validation

All generated identifiers or references to existing alternatives and other explicitly referenceable artifacts SHALL resolve exactly against the current five upstream inputs.

Validation SHALL be fail-closed:

- no fuzzy matching;
- no case folding;
- no silent repair;
- no invented IDs;
- no normalization beyond explicitly approved contract-level whitespace handling.

### COORD-FR-018 — Atomic Trust

The complete `FinalReview` becomes trusted only after every structural and contextual rule succeeds. No partial final result SHALL be stored.

### COORD-FR-019 — Same-Execution Provenance

Every non-`PENDING` Coordinator stage SHALL retain the exact five current Review artifact instances. Equality with independently constructed copies is insufficient.

Generated-reference validation and same-execution provenance remain separate concepts.

### COORD-FR-020 — Explicit Lifecycle

Slice 6 SHALL add only the explicit Coordinator states and transitions required to:

- start Coordinator;
- complete Coordinator with `FinalReview`;
- fail Coordinator with a safe `ReviewError`;
- make Review `COMPLETED` only on successful completion;
- make Review `INCOMPLETE` on Coordinator failure.

No generic transition engine is introduced.

### COORD-FR-021 — Dependency Enforcement

Coordinator SHALL remain `PENDING` unless all four upstream stages completed successfully. It SHALL never run after an upstream mandatory failure.

### COORD-FR-022 — Safe Failure Mapping

Coordinator output-validation failure and ordinary execution failure SHALL map to distinct provider-neutral error kinds with these exact safe messages:

```text
Coordinator output validation failed
Coordinator execution failed
```

Raw provider or validation details SHALL not be stored in trusted Review state.

### COORD-FR-023 — Stateless Execution

Reusing Coordinator, other participants, or `ReviewOrchestrator` across reviews SHALL not retain Review state or cross-review artifacts.

---

## 6. Lifecycle Expectations

Slice 6 extends the existing lifecycle without changing the valid Analyst, Solution Architect, Risk Reviewer, or Critic prefixes.

Across all five stages, Slice 6 SHALL accept exactly:

- 10 `RUNNING` combinations: the nine accepted Slice-5 prefixes plus Coordinator `RUNNING` after the first four stages complete;
- 5 `INCOMPLETE` combinations: exactly one failed stage with every previous stage completed and every later stage pending;
- 1 `COMPLETED` combination: all five stages completed.

### Successful terminal state

Exactly one successful terminal shape is introduced:

```text
Analyst             COMPLETED
Solution Architect  COMPLETED
Risk Reviewer       COMPLETED
Critic              COMPLETED
Coordinator         COMPLETED
Review              COMPLETED
```

### Coordinator execution state

```text
Analyst             COMPLETED
Solution Architect  COMPLETED
Risk Reviewer       COMPLETED
Critic              COMPLETED
Coordinator         RUNNING
Review              RUNNING
```

### Coordinator failure state

```text
Analyst             COMPLETED
Solution Architect  COMPLETED
Risk Reviewer       COMPLETED
Critic              COMPLETED
Coordinator         FAILED
Review              INCOMPLETE
```

No state may skip an upstream stage, execute after an earlier failure, contain multiple failed stages, or mark Review completed without Coordinator completion.

---

## 7. Validation and Failure Semantics

The Coordinator boundary follows:

```text
LLMPort structured response
        ↓ untrusted
structural FinalReview validation
        ↓
current-review contextual validation
        ↓ trusted
FinalReview
```

A structural or contextual failure SHALL:

1. raise a dedicated Coordinator output error at the participant boundary;
2. mark Coordinator `FAILED`;
3. mark Review `INCOMPLETE`;
4. retain exact Coordinator stage inputs;
5. store no `FinalReview`;
6. preserve all four upstream completed stages.

An ordinary participant/model exception SHALL follow the same lifecycle outcome with a distinct error kind and safe message.

Only exceptions raised by the participant call belong inside this mapping boundary. Stage transition, provenance, type-narrowing, and aggregate-invariant errors remain visible internal failures.

---

## 8. Edge Cases

The implementation SHALL define and test at least:

1. zero alternatives with explicit insufficient evidence;
2. two alternatives ranked exactly once each;
3. three alternatives ranked exactly once each;
4. empty `CriticalReview`;
5. validation-only `CriticalReview`;
6. a material criticism visibly reflected in the final result or explicitly dismissed as not decision-relevant with justification;
7. a missing-alternative finding preserved as decision-relevant uncertainty without requiring a predetermined recommendation outcome;
8. a contradiction or unresolved issue remaining visible without requiring a predetermined effect on ranking or confidence;
9. zero risks without forced risk language;
10. unknown ranked alternative ID;
11. duplicate ranked alternative;
12. omitted existing alternative in a required multi-alternative ranking;
13. duplicated, tied, or non-contiguous positions;
14. preferred alternative not ranked first;
15. preferred alternative present in an insufficient-evidence result;
16. recommendation marked sufficient without a preferred alternative;
17. numeric confidence or unsupported extra fields;
18. malformed output and ordinary provider failure;
19. upstream failure preventing Coordinator invocation;
20. equal-but-independent upstream objects rejected by same-execution provenance;
21. sequential reviews remaining isolated.

Subjective LLM quality SHALL not be asserted as deterministic truth. Tests SHALL focus on contracts, exact references, lifecycle, and observable behavior.

---

## 9. Success Criteria

Slice 6 is complete when:

1. Coordinator independently transforms deterministic untrusted output into a trusted `FinalReview`;
2. every existing alternative is ranked exactly once when multi-alternative ranking applies;
3. every ranking position contains justification and final considerations;
4. supported preference and insufficient-evidence outcomes are both representable and validated;
5. zero-alternative cases do not fabricate comparison or recommendation, and the accepted 0/2/3 upstream cardinality remains unchanged;
6. Review reaches `COMPLETED` only through successful Coordinator completion;
7. Coordinator failure produces `INCOMPLETE` while preserving all upstream work;
8. exact five-artifact same-execution provenance is enforced using identity;
9. deterministic orchestration covers success, validation failure, execution failure, upstream failure, and isolation;
10. the full Slice 1–6 suite, Ruff, mypy strict, and dependency checks pass;
11. no prohibited architectural expansion is introduced.

---

## 10. Resolved Specification Decisions

Specification review resolved the following decisions:

1. Coordinator preserves the accepted `SolutionAlternatives` cardinality of exactly 0, 2, or 3 alternatives; one alternative remains invalid upstream;
2. recommendation outcome uses exactly `RECOMMENDED` or `INSUFFICIENT_EVIDENCE`;
3. conclusion rationale is always required;
4. principal risks use exact existing `Risk.id` references; unresolved questions use exact IDs where available and bounded visible text otherwise;
5. exact safe boundary messages are `Coordinator output validation failed` and `Coordinator execution failed`;
6. one concrete advisory next validation step is always required;
7. `decision_support_notice` is mandatory;
8. material criticisms must be visibly reflected or explicitly dismissed with justification.

No plan or data model SHALL be created until this corrected specification is reviewed and explicitly approved.
