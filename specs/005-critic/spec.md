# Feature Specification: Critic v0.1

**Branch**: `005-critic`  
**Date**: 2026-08-22  
**Status**: Draft — revised after canonical review; awaiting explicit approval before planning

## 1. Purpose

Slice 5 introduces the Critic as the fourth executable participant in the Agentic Review Board MVP.

The Critic SHALL challenge the quality and support of the review artifacts produced so far without taking ownership of final ranking or recommendation.

It answers:

> Where are the weak assumptions, contradictions, omissions, unsupported conclusions, underestimated risks, or otherwise insufficiently supported points in the current review?

The Critic is adversarial toward weak reasoning, not adversarial for its own sake.

This slice extends the already implemented execution sequence:

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
Coordinator (still pending / not implemented in Slice 5)
```

Slice 5 SHALL preserve all accepted Slice 1–4 contracts unless an explicit approved change is required.

---

## 2. Canonical Source Alignment

This specification is constrained by the existing canonical documents:

- `docs/02-requirements.md` — especially FR-026 through FR-030, FR-049 through FR-057, AI-001, AI-002, and AI-005;
- `docs/03-architecture.md` — explicit stage dependency order, validation boundary, traceability, failure semantics, provider independence, and minimal implementation complexity;
- `docs/04-agent-model.md` — Critic responsibility, allowed inputs, `CriticalReview`, invariants, missing-alternative behavior, contradictions, and prohibited behavior;
- `docs/05-quality-security.md` — existing quality/security constraints;
- `.specify/memory/constitution.md`;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`;
- approved and merged Slice 1–4 contracts.

Where this specification does not define an implementation detail, the canonical documents remain authoritative.

---

## 3. Scope

### 3.1 In Scope

Slice 5 SHALL add the minimum behavior required to:

1. represent a validated Critic output as an explicit `CriticalReview` contract;
2. allow the Critic to consume exactly the current review's original `ReviewInput`, validated `ProblemAnalysis`, validated `SolutionAlternatives`, and validated `RiskAssessment`;
3. challenge weak or unsupported upstream reasoning using visible review artifacts;
4. identify contradictions when supported by current review artifacts;
5. identify genuinely material missing alternative classes without designing a replacement solution portfolio;
6. explicitly validate points that appear sufficiently supported;
7. preserve unresolved issues and newly identified uncertainty for downstream use;
8. extend `StageExecution`, `Review`, and the explicit `ReviewOrchestrator` sequence through Critic;
9. fail closed when the Critic produces invalid structured output or invalid references;
10. preserve exact same-execution provenance for the Critic stage;
11. leave Coordinator unimplemented and `PENDING` after successful Slice 5 execution.

### 3.2 Out of Scope

Slice 5 SHALL NOT introduce Coordinator implementation; final ranking, preferred-alternative selection, recommendation, or `FinalReview`; autonomous actions; retries/timeouts/concurrency; persistence/RAG/browsing/tools/UI integrations; provider-specific SDK dependencies in the core; organization-specific knowledge absent from the review; generic workflow/stage registries; generic cross-stage reference frameworks without separate approval; mutation of upstream outputs; replacement solution portfolios; or numeric confidence/probability scoring without an approved methodology.

---

## 4. User Stories

### US1 — Produce an evidence-based critical review

As a user, I want the Critic to inspect the review artifacts produced so far and return concise structured challenges so that weak reasoning is visible before any final recommendation is produced.

#### Acceptance criteria

1. Critic receives all four current upstream artifacts from the same review execution.
2. Critic returns a validated `CriticalReview` rather than free-form text alone.
3. Material criticisms identify what is being challenged whenever current artifacts make that possible.
4. Criticism is grounded in visible current-review artifacts rather than fabricated facts or hidden external information.
5. Critic explicitly evaluates, where present, unsupported assumptions, contradictions, missing or weak alternatives, weak arguments, underestimated risks, unjustified optimism, and conclusions unsupported by visible evidence.
6. Critic does not rank alternatives or recommend a winner.

### US2 — Preserve explicit traceability of criticism

As a user, I want material criticisms to point back to explicit review artifacts so that I can inspect why a challenge exists.

#### Acceptance criteria

1. A material criticism identifies its target type.
2. When an explicit target exists and resolves unambiguously, the criticism SHALL reference it; Critic SHALL NOT omit an available target merely to evade contextual validation.
3. A criticism MAY lack a single target reference only when it genuinely spans artifacts or describes an omission with no single explicit target; its rationale SHALL still identify its visible basis.
4. Critic can challenge assumptions, alternatives or characteristics, risks or mitigations, constraint interpretation, and cross-stage conclusions.
5. Unknown, mismatched, or ambiguous generated references fail closed rather than being silently repaired.
6. Generated-reference validation remains distinct from StageExecution same-execution provenance.

### US3 — Allow agreement as well as challenge

As a user, I want the Critic to identify adequately supported points so that the system does not manufacture disagreement.

#### Acceptance criteria

1. `CriticalReview` can contain validated/supported points.
2. A validated point SHOULD identify its explicit upstream artifact or finding whenever practical and unambiguous.
3. Critic is not required to manufacture a criticism.
4. A valid review with no material criticism remains representable.
5. A fully empty `CriticalReview` is structurally valid when no criticism, validated point, missing alternative, contradiction, or unresolved issue is justified.
6. Validation does not become ranking/recommendation and does not promote an assumption to fact.

### US4 — Surface missing alternatives and contradictions without rewriting upstream work

As a user, I want Critic to expose omissions and contradictions without replacing prior artifacts.

#### Acceptance criteria

1. Critic may identify a genuinely material missing alternative class.
2. A missing-alternative finding explains what category appears omitted, why it matters, and whether the omission is serious enough to weaken a later Coordinator's ability to justify a final recommendation.
3. Critic does not design or insert a replacement `SolutionAlternative`.
4. Critic may identify contradictions across explicit artifacts.
5. When both contradiction sides correspond to explicit referencable artifacts, both SHALL be identifiable against those artifacts.
6. Upstream validated artifacts remain unchanged.
7. Newly identified uncertainty or unresolved issues remain explicit.

### US5 — Execute Critic as the fourth mandatory stage

As a user, I want Critic to run only after Analyst, Solution Architect, and Risk Reviewer succeed.

#### Acceptance criteria

1. Critic starts only after all three upstream stages are `COMPLETED` with valid outputs.
2. Critic stage records the exact current ReviewInput, ProblemAnalysis, SolutionAlternatives, and RiskAssessment instances used.
3. Success produces `COMPLETED` with a validated `CriticalReview`.
4. Review remains `RUNNING`; Coordinator remains `PENDING`.
5. Critic failure makes Review `INCOMPLETE`, preserves completed upstream results, and leaves Coordinator `PENDING`.
6. Critic cannot execute after an upstream mandatory failure or before prerequisites complete.

### US6 — Fail closed at the Critic trust boundary

As a user, I want malformed or unsupported Critic output to stop the review before Coordinator.

#### Acceptance criteria

1. Raw model output remains untrusted until structural validation succeeds.
2. Contextual references are validated before `CriticalReview` enters trusted state.
3. Structural/contextual output failure produces a dedicated Critic output-validation failure.
4. Ordinary participant/model execution failure remains distinguishable from output-validation failure.
5. No partially trusted `CriticalReview` is stored.
6. Coordinator remains unexecuted after Critic failure.
7. Internal domain/invariant failures outside the participant-call boundary are not silently converted into participant failures.

---

## 5. Functional Requirements

### CRIT-FR-001 — Explicit Critic Inputs
Critic SHALL receive the current `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives`, and `RiskAssessment`.

### CRIT-FR-002 — Structured CriticalReview Output
Critic SHALL produce a structured `CriticalReview` containing conceptually `criticisms[]`, `validated_points[]`, `missing_alternatives[]`, `contradictions[]`, and `unresolved_issues[]`. Exact structures are deferred to plan/data-model. All five collections MAY be empty simultaneously; the contract SHALL NOT require fabricated activity.

### CRIT-FR-003 — Structured Criticism
Each material criticism SHOULD support the canonical fields `id`, `target_type`, `target_reference`, `issue`, `importance`, `rationale`, and optional `correction_or_question`. Exact target representation is deferred to data-model. When an explicit target exists and resolves unambiguously, it SHALL be referenced. Absence of a single target is valid only for genuinely cross-artifact findings or omissions without one explicit target, while rationale SHALL still expose visible basis.

### CRIT-FR-004 — Qualitative Importance
Criticism importance MAY use `LOW`, `MEDIUM`, or `HIGH`; if used, it is ordinal judgment, not calibrated probability or numeric score.

### CRIT-FR-005 — Evidence-Constrained Criticism
Material Critic findings SHALL be grounded in explicit current-review artifacts. Critic SHALL evaluate, where present: unsupported assumptions; contradictions; missing or weak alternatives; weak arguments; underestimated risks; unjustified optimism; and conclusions unsupported by visible evidence. Critic SHALL NOT introduce fabricated user facts or organization-specific policies absent from the review.

### CRIT-FR-006 — Preserve Facts and Assumptions
Critic SHALL preserve fact/assumption semantics. Repetition, validation, or challenge SHALL NOT promote an assumption to fact unless original ReviewInput explicitly establishes it.

### CRIT-FR-007 — No Artificial Disagreement
Critic MUST NOT invent objections. A valid `CriticalReview` MAY contain no criticisms and MAY be fully empty when no Critic finding is justified.

### CRIT-FR-008 — Validated Points
Critic SHALL be able to identify adequately supported upstream points. A validated point SHOULD identify its explicit upstream artifact/finding whenever practical and unambiguous. Validation does not make a final decision/recommendation and does not promote assumptions to facts.

### CRIT-FR-009 — Missing Alternatives
Critic MAY identify a genuinely material omitted alternative class. It SHALL state what category appears omitted, why the omission matters, and whether it is serious enough to weaken a later Coordinator's ability to justify a final recommendation. Critic SHALL NOT itself recommend, mutate `SolutionAlternatives`, or construct a replacement set.

### CRIT-FR-010 — Contradictions
Critic SHALL represent contradictions between explicit current-review artifacts when present. Both sides SHALL remain inspectable; when both correspond to explicit referencable artifacts, both SHALL be identifiable and contextually validated. Exact representation is deferred to data-model.

### CRIT-FR-011 — Unresolved Issues
Critic SHALL preserve material unresolved issues/new uncertainty explicitly rather than resolving them with invented information.

### CRIT-FR-012 — No Ranking or Recommendation
Critic SHALL NOT rank alternatives, select a preferred alternative, declare a winner, issue the final recommendation, or use criticism importance as substitute ranking. These remain Coordinator responsibilities.

### CRIT-FR-013 — No Silent Upstream Mutation
Critic SHALL NOT rewrite, replace, or mutate `ProblemAnalysis`, `SolutionAlternatives`, or `RiskAssessment`; `CriticalReview` coexists as a new artifact.

### CRIT-FR-014 — Structured Validation Boundary
Generated Critic output SHALL remain untrusted until validated. Invalid output SHALL NOT enter Review state or propagate downstream.

### CRIT-FR-015 — Current-Review Contextual Validation
Explicit generated references SHALL resolve against exact current Critic inputs before trust. No-match/ambiguity fails closed. Critic SHALL NOT avoid required contextual validation by omitting an available explicit target.

### CRIT-FR-016 — Same-Execution Provenance
A non-PENDING Critic StageExecution SHALL retain provenance to the exact current ReviewInput and exact completed Analyst, Solution Architect, and Risk Reviewer outputs. Equal-but-independent copies do not satisfy provenance.

### CRIT-FR-017 — Critic Lifecycle
Critic supports `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED` with existing immutable validated lifecycle semantics.

### CRIT-FR-018 — Coordinator Remains Pending
Coordinator SHALL remain `PENDING`; successful Slice 5 execution SHALL not create `ReviewStatus.COMPLETED` or `FinalReview`.

### CRIT-FR-019 — Failure Semantics
Critic failure produces Critic `FAILED` + Review `INCOMPLETE`; Coordinator remains `PENDING`; completed upstream outputs remain inspectable; no Critic output is trusted or propagated.

### CRIT-FR-020 — Review Isolation
Critic SHALL retain no hidden mutable review state between executions; fresh Reviews inherit no prior Critic artifacts.

---

## 6. Architectural and Quality Constraints

- **CRIT-NFR-001 Provider Independence** — Critic domain/application semantics SHALL NOT depend on concrete provider SDKs.
- **CRIT-NFR-002 Deterministic Testability** — all core behavior SHALL be testable without live network/LLM.
- **CRIT-NFR-003 Explicit Orchestration** — extend only the explicit synchronous sequence; no generic stage loop/registry/graph engine.
- **CRIT-NFR-004 Minimal New Abstractions** — prefer Critic-specific contracts; no generic cross-stage reference framework merely for this slice.
- **CRIT-NFR-005 Immutable Trusted Contracts** — follow accepted closed, immutable structured-contract approach.
- **CRIT-NFR-006 Bounded Output** — favor concise inspectable structured findings.
- **CRIT-NFR-007 No Private Chain-of-Thought Dependency** — traceability relies on explicit findings/rationale/targets/artifacts only.
- **CRIT-NFR-008 No Persistence Requirement** — Slice 5 remains in-memory.

---

## 7. Required Slice 5 End States

### Successful execution
```text
Review                 RUNNING
Analyst                COMPLETED
Solution Architect     COMPLETED
Risk Reviewer          COMPLETED
Critic                 COMPLETED
Coordinator            PENDING
```

### Critic failure
```text
Review                 INCOMPLETE
Analyst                COMPLETED
Solution Architect     COMPLETED
Risk Reviewer          COMPLETED
Critic                 FAILED
Coordinator            PENDING
```

If any mandatory upstream stage fails, Critic remains `PENDING` and does not execute.

---

## 8. Edge Cases That Must Remain Valid

1. Fully empty `CriticalReview` when no finding is justified.
2. No criticism but one or more traceable validated points.
3. Challenge an Analyst assumption without promoting it to fact.
4. Validate a strong point rather than object artificially.
5. Identify omitted alternative class without generating replacement and state its potential effect on later recommendation quality.
6. Cross-artifact contradiction with both explicit sides traceable when referencable.
7. Reference a current Risk and its mitigation.
8. Identify weak argument, underestimated risk, or unjustified optimism grounded in current artifacts.
9. Unknown generated reference fails closed.
10. Ambiguous generated reference fails closed.
11. Required explicit target omitted despite being unambiguously resolvable fails closed under the approved data model.
12. Valid zero-alternative upstream result does not force fabricated alternatives.
13. Valid zero-risk assessment does not force fabricated risks.
14. Structurally malformed Critic output.
15. Ordinary model/provider failure during Critic invocation.
16. Internal invariant failure outside participant boundary.
17. Reuse of participant/orchestrator objects without cross-review contamination.
18. Noncanonical valid stage tuple ordering remains interpreted by `StageIdentity`, not position.

---

## 9. Acceptance Gate for Planning

Proceed to `plan.md` only after explicit review confirms:

1. Critic is separated from Coordinator ranking/recommendation.
2. All four upstream inputs are preserved.
3. FR-027 challenge categories are explicitly covered and evidence-constrained.
4. Strong analysis may be validated and validated points are traceable where practical.
5. Missing alternatives do not become replacement portfolios and may signal weakened later recommendation quality.
6. Contradictions preserve both sides and trace them when explicitly referencable.
7. Assumption semantics are preserved.
8. Generated-reference validation remains distinct from same-execution provenance.
9. Critic failure prevents Coordinator execution.
10. No future-slice architecture is introduced prematurely.
11. Zero-criticism, fully empty CriticalReview, zero-alternative, and zero-risk cases do not force fabricated activity.
12. Explicit resolvable targets cannot evade contextual validation through omitted references.

Only after this `spec.md` is reviewed and explicitly approved should `plan.md` be created.
