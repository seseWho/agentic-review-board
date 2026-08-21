# Feature Specification: Risk Reviewer v0.1

**Feature Branch**: `004-risk-reviewer`  
**Created**: 2026-08-21  
**Status**: Approved — ready for implementation planning  
**Input**: Fourth executable product increment derived from the canonical MVP documents and the completed Review Input + Analyst, Solution Architect, and Review Orchestrator slices.

## Purpose

This increment introduces the Risk Reviewer as the third executable review participant and extends the existing Review Orchestrator through the Risk Reviewer stage.

The Risk Reviewer SHALL identify and structure material downside exposure associated with the overall proposal and with the candidate alternatives already accepted into the current review.

The increment must demonstrate genuine information propagation across three distinct responsibilities:

```text
ReviewInput
    ↓
Analyst
    ↓ trusted ProblemAnalysis
Solution Architect
    ↓ trusted SolutionAlternatives
Risk Reviewer
    ↓ trusted RiskAssessment
```

The Risk Reviewer evaluates exposure. It does not choose, rank, or recommend a solution.

Critic and Coordinator remain represented but unexecuted in Slice 4. Therefore a successful Slice 4 review remains `RUNNING`, not `COMPLETED`.

---

## User Scenarios & Testing

### User Story 1 - Produce a structured risk assessment (Priority: P1)

As a professional user, I want the Risk Reviewer to identify material risks in a structured form so that downside exposure is explicit before later critical review and recommendation.

**Why this priority**: Risk analysis is the next mandatory stage in the canonical five-stage dependency chain and is required before Critic can evaluate whether risks have been underestimated.

**Independent Test**: Supply deterministic valid `ReviewInput`, `ProblemAnalysis`, and `SolutionAlternatives`; invoke the Risk Reviewer; verify that the returned `RiskAssessment` contains only validated structured risks and observations grounded in the supplied review artifacts.

**Acceptance Scenarios**:

1. **Given** valid original review input, trusted Analyst output, and trusted Solution Architect output, **When** the Risk Reviewer executes, **Then** it receives all three explicit inputs and no hidden conversational state.
2. **Given** a material risk affecting the overall proposal, **When** the Risk Reviewer returns it, **Then** the risk identifies overall scope, a qualitative severity, an explicit basis, and an optional mitigation/residual uncertainty.
3. **Given** a material risk affecting one candidate alternative, **When** the Risk Reviewer returns it, **Then** the risk identifies that existing alternative explicitly rather than describing an ambiguous unnamed scope.
4. **Given** a material risk affecting several alternatives, **When** the Risk Reviewer returns it, **Then** all affected alternatives are explicitly identified.
5. **Given** a risk with severity, **When** it enters trusted state, **Then** severity is exactly `LOW`, `MEDIUM`, or `HIGH` and is not represented as a numeric probability.
6. **Given** a risk basis, **When** it enters trusted state, **Then** the basis refers to visible review information such as ReviewInput, Analyst findings, or Solution Architect characteristics rather than unsupported external facts.
7. **Given** a mitigation, **When** it is present, **Then** the mitigation is represented as a risk-reduction consideration and does not imply the underlying risk has disappeared.

---

### User Story 2 - Preserve evidence, assumptions, and alternative references (Priority: P1)

As a user, I want each material risk to remain traceable to the current review artifacts so that later stages can inspect why the risk exists and what it affects.

**Independent Test**: Construct deterministic Risk Reviewer outputs that reference facts, constraints, assumptions, and alternatives; verify contextual validation accepts only references resolvable against the current Risk Reviewer inputs.

**Acceptance Scenarios**:

1. **Given** a risk basis references an Analyst fact, constraint, assumption, missing-information item, or uncertainty, **When** output validation occurs, **Then** the reference must identify an item present in the supplied current `ProblemAnalysis`.
2. **Given** a risk refers to an alternative, **When** output validation occurs, **Then** the alternative identifier must exist in the supplied current `SolutionAlternatives`.
3. **Given** a fabricated, unknown, ambiguous, or otherwise unresolvable reference, **When** output validation occurs, **Then** the Risk Reviewer output is rejected rather than silently repaired or accepted.
4. **Given** upstream content contains an assumption, **When** Risk Reviewer uses it as risk basis, **Then** it remains identifiable as assumption-derived support and is not promoted into a user-provided fact.
5. **Given** missing information materially limits risk interpretation, **When** Risk Reviewer reports that limitation, **Then** the uncertainty remains visible in structured output rather than being silently filled with invented detail.

Generated textual/local references establish only that they resolve unambiguously within the current trusted Risk Reviewer inputs. Same-execution provenance between stages is a separate Review execution invariant and is enforced through exact in-memory object identity.

---

### User Story 3 - Avoid fabricated risks and artificial completeness (Priority: P1)

As a user, I want the Risk Reviewer to report only risks supported by the current review so that the stage does not manufacture pessimism merely to appear active.

**Independent Test**: Provide deterministic inputs where no specific material risk can be justified and verify a valid `RiskAssessment` can represent that result without fabricated risk entries.

**Acceptance Scenarios**:

1. **Given** the visible review artifacts do not support a material risk, **When** the Risk Reviewer evaluates them, **Then** it is not required to fabricate a risk.
2. **Given** no justified risk is identified, **When** the Risk Reviewer completes, **Then** the result may contain zero risks together with concise observations explaining the limited risk evidence or remaining uncertainty.
3. **Given** the available Solution Architect result contains zero alternatives but is itself valid, **When** the Risk Reviewer executes, **Then** it may still assess risks affecting the overall proposal and SHALL NOT invent alternative-specific risks.
4. **Given** risk categories are used, **When** the Risk Reviewer produces output, **Then** it is not required to populate every category.
5. **Given** organization-specific policy, regulation, cost, or operational facts are absent from the current review input, **When** risk analysis occurs, **Then** the Risk Reviewer SHALL NOT invent those facts as established constraints.

---

### User Story 4 - Execute Risk Reviewer after trusted upstream success (Priority: P1)

As a user, I want the existing Review Orchestrator to execute Risk Reviewer only after Analyst and Solution Architect have completed successfully so that the third stage consumes trusted current-review artifacts rather than independent prompt context.

**Independent Test**: Execute a deterministic successful Review through one `ReviewOrchestrator` and verify exact invocation order, stage input registration, artifact identity/provenance, and final Slice 4 state.

**Acceptance Scenarios**:

1. **Given** a new Review, **When** Slice 4 orchestration succeeds, **Then** participant invocation order is exactly Analyst → Solution Architect → Risk Reviewer.
2. **Given** Risk Reviewer is about to execute, **When** its stage transitions to `RUNNING`, **Then** its execution-input record contains the current original `ReviewInput`, the exact trusted current Analyst `ProblemAnalysis`, and the exact trusted current Solution Architect `SolutionAlternatives`.
3. **Given** Risk Reviewer returns a trusted `RiskAssessment`, **When** orchestration accepts it, **Then** Risk Reviewer becomes `COMPLETED` with that exact trusted output.
4. **Given** all three implemented stages complete, **When** the Review is inspected, **Then** Analyst, Solution Architect, and Risk Reviewer are `COMPLETED`; Critic and Coordinator remain `PENDING`; and overall Review status remains `RUNNING`.
5. **Given** a valid zero-risk `RiskAssessment`, **When** orchestration accepts it, **Then** Risk Reviewer is `COMPLETED`; zero risks do not constitute stage failure.

---

### User Story 5 - Fail closed at the Risk Reviewer boundary (Priority: P1)

As a user, I want invalid or failed Risk Reviewer execution to make the review visibly incomplete while preserving trusted Analyst and Solution Architect work.

**Independent Test**: Drive deterministic Risk Reviewer output-validation and generic participant-execution failures after successful Analyst and Solution Architect stages.

**Acceptance Scenarios**:

1. **Given** Analyst and Solution Architect completed successfully, **When** Risk Reviewer returns structurally or contextually invalid generated output, **Then** Risk Reviewer becomes `FAILED`, contains no trusted `RiskAssessment`, and the Review becomes `INCOMPLETE`.
2. **Given** Risk Reviewer raises another ordinary exception from inside its participant call, **When** orchestration handles it, **Then** Risk Reviewer becomes `FAILED` with a provider-neutral execution failure and Review becomes `INCOMPLETE`.
3. **Given** Risk Reviewer fails, **When** the returned Review is inspected, **Then** the previously completed Analyst and Solution Architect stages and outputs remain unchanged and inspectable.
4. **Given** Risk Reviewer fails, **When** orchestration considers later stages, **Then** Critic and Coordinator remain `PENDING` and are not invoked.
5. **Given** a known Risk Reviewer output-validation failure, **When** error state is recorded, **Then** it is distinguishable from a generic participant execution failure.
6. **Given** arbitrary raw exception detail, **When** an error is stored in trusted review state, **Then** secrets, raw response content, stack traces, and provider-specific details are not copied into `ReviewError`.
7. **Given** a domain/orchestration invariant defect outside the Risk Reviewer participant call, **When** it occurs, **Then** it propagates to the caller rather than being mislabeled as a Risk Reviewer participant failure.

---

## Edge Cases and Clarifications

- Slice 4 adds only Risk Reviewer semantics and the minimum execution-state/orchestration extension required to run it after Solution Architect.
- Critic and Coordinator remain `PENDING` throughout successful Slice 4 execution.
- A valid zero-alternative `SolutionAlternatives` remains a successful upstream result. Risk Reviewer may assess overall-proposal exposure from the remaining visible review artifacts.
- A valid zero-risk `RiskAssessment` is permitted when no material risk can be justified. The participant SHALL NOT fabricate risks solely to satisfy a non-empty count.
- `overall_observations[]` may capture concise cross-cutting risk observations, limitations, or remaining uncertainty; it SHALL NOT become a hidden final recommendation or ranking field.
- Risk severity is qualitative (`LOW`, `MEDIUM`, `HIGH`) and SHALL NOT be treated as calibrated likelihood, impact probability, expected loss, or statistical confidence.
- `category` is optional. No risk category is mandatory or exhaustive.
- Risk basis must remain grounded in visible current-review artifacts. The Risk Reviewer does not browse, retrieve external policy, or introduce organization-specific facts in this slice.
- A mitigation may reduce likelihood, impact, or exposure but does not erase the underlying risk.
- A Risk Reviewer SHALL NOT redefine alternatives. If an alternative is weak or conditional, the reviewer assesses resulting exposure rather than silently replacing the alternative.
- Existing no-retry, no-timeout, no-persistence, no-concurrency, no-UI constraints remain unchanged.

---

## Requirements

### Functional Requirements

- **FR-001**: Risk Reviewer execution MUST consume the current original `ReviewInput`, trusted current `ProblemAnalysis`, and trusted current `SolutionAlternatives`.
- **FR-002**: Risk Reviewer MUST produce a structured `RiskAssessment` before any Risk Reviewer output enters trusted review state.
- **FR-003**: `RiskAssessment` MUST contain a collection of zero or more structured risks and MAY contain concise overall observations.
- **FR-004**: Every `Risk` MUST have a local identifier suitable for current-review traceability.
- **FR-005**: Every `Risk` MUST contain a non-empty description.
- **FR-006**: Every `Risk` MUST identify its affected scope as the overall proposal, one existing alternative, or multiple existing alternatives.
- **FR-007**: Any alternative reference in affected scope MUST resolve to an alternative in the current `SolutionAlternatives` input.
- **FR-008**: Every `Risk` MUST contain qualitative severity using the existing shared `LOW`, `MEDIUM`, or `HIGH` values.
- **FR-009**: Risk severity MUST NOT use unsupported numeric probabilities or imply calibrated statistical likelihood.
- **FR-010**: Every `Risk` MUST contain a non-empty structured basis identifying visible review information that makes the risk relevant.
- **FR-011**: Basis references to Analyst findings MUST resolve to items in the current `ProblemAnalysis` when explicit identifiers are used.
- **FR-012**: Risk basis MUST NOT promote an Analyst assumption into a ReviewInput fact.
- **FR-013**: A `Risk` MAY contain an optional category; categories are labels rather than an exhaustive closed taxonomy, and category use MUST NOT require every category to appear.
- **FR-014**: A `Risk` MAY contain an optional mitigation.
- **FR-015**: Presence of mitigation MUST NOT remove or invalidate the risk automatically.
- **FR-016**: A `Risk` MAY contain optional residual uncertainty explaining material unknowns remaining after mitigation or analysis.
- **FR-017**: Risk Reviewer MUST NOT fabricate a risk solely to produce non-empty output.
- **FR-018**: A valid zero-risk `RiskAssessment` MUST be accepted as successful Risk Reviewer output.
- **FR-019**: A valid zero-alternative `SolutionAlternatives` MUST NOT by itself prevent Risk Reviewer execution.
- **FR-020**: When upstream alternatives are empty, Risk Reviewer MUST NOT fabricate alternative-specific scope references.
- **FR-021**: Risk Reviewer MUST NOT make a final recommendation, rank alternatives, declare a winner, or perform Coordinator responsibilities.
- **FR-022**: Risk Reviewer MUST NOT redefine or silently replace candidate alternatives.
- **FR-023**: Risk Reviewer generated output MUST be parsed, structurally validated, and contextually validated before becoming trusted `RiskAssessment`.
- **FR-024**: Invalid generated output MUST fail closed; it MUST NOT be silently repaired, partially trusted, or propagated downstream.
- **FR-025**: The Review execution model MUST add explicit Risk Reviewer input provenance containing the current ReviewInput, current Analyst output, and current Solution Architect output.
- **FR-026**: Risk Reviewer stage MUST remain `PENDING` until both Analyst and Solution Architect are `COMPLETED` with trusted outputs.
- **FR-027**: Starting Risk Reviewer MUST transition only that stage from `PENDING` to `RUNNING` while preserving earlier completed stage records.
- **FR-028**: Completing Risk Reviewer MUST store the exact trusted `RiskAssessment` as that stage's output and leave Critic and Coordinator `PENDING`.
- **FR-029**: Successful Slice 4 orchestration MUST leave the overall Review `RUNNING`, not `COMPLETED`.
- **FR-030**: Known Risk Reviewer generated-output validation failure MUST map to `ReviewErrorKind.OUTPUT_VALIDATION` with concise stable safe error text.
- **FR-031**: Other ordinary exceptions raised by the Risk Reviewer participant invocation MUST map to `ReviewErrorKind.EXECUTION` with concise stable safe error text.
- **FR-032**: Risk Reviewer failure MUST atomically produce `Risk Reviewer FAILED + Review INCOMPLETE` with recorded inputs, no trusted output, and preserved upstream completed work.
- **FR-033**: Risk Reviewer failure MUST leave Critic and Coordinator `PENDING` and uninvoked.
- **FR-034**: Domain/orchestration exceptions outside the Risk Reviewer participant invocation boundary MUST propagate rather than being converted into participant `ReviewError`.
- **FR-035**: Risk Reviewer and Slice 4 orchestration MUST remain deterministically testable using a fake `LLMPort` with no network access or live model.
- **FR-036**: Slice 4 MUST preserve provider-neutral boundaries; `ReviewOrchestrator` MUST NOT directly call `LLMPort` or import a provider SDK.

### Qualitative Severity

Risk severity reuses the existing shared qualitative contract:

```text
LOW
MEDIUM
HIGH
```

These values represent ordinal review judgment only.

### Observable Successful Slice 4 State

```text
Review                RUNNING
Analyst               COMPLETED
Solution Architect    COMPLETED
Risk Reviewer         COMPLETED
Critic                PENDING
Coordinator           PENDING
```

### Observable Risk Reviewer Failure State

```text
Review                INCOMPLETE
Analyst               COMPLETED
Solution Architect    COMPLETED
Risk Reviewer         FAILED
Critic                PENDING
Coordinator           PENDING
```

The failed Risk Reviewer stage retains its recorded execution inputs and concise `ReviewError`, but contains no trusted output.

---

## Scope Boundaries

This increment introduces only:

- structured Risk Reviewer output semantics;
- Risk Reviewer participant behavior using the existing provider-neutral `LLMPort` boundary;
- contextual validation against current ReviewInput/ProblemAnalysis/SolutionAlternatives where required for traceability;
- the minimum execution-state extensions required for Risk Reviewer input/output provenance;
- the minimum Review lifecycle/transition extensions required to start, complete, or fail Risk Reviewer;
- extension of the explicit synchronous Review Orchestrator sequence through Risk Reviewer;
- deterministic tests for contracts, validation, orchestration, failure, and isolation/regression behavior.

This increment does not introduce:

- Critic participant behavior or `CriticalReview`;
- Coordinator participant behavior or `FinalReview`;
- ranking, preferred alternative, final recommendation, final confidence, or autonomous decision;
- execution after Risk Reviewer;
- a generic stage/participant registry or dynamic workflow engine;
- persistence, history, serialization/rehydration identity, or resume;
- RAG, embeddings, browsing, MCP, external tools, or document ingestion;
- provider-specific SDK types in domain/application contracts;
- retries, timeout/backoff, cancellation, pause/resume, or concurrency;
- telemetry infrastructure or a new logging framework;
- UI/application presentation behavior;
- numeric probability/risk scoring model;
- organization-specific policy knowledge not supplied in ReviewInput;
- a global taxonomy service or mandatory exhaustive risk categories.

Concrete Pydantic field representation, exact affected-scope structure, exact basis-reference representation, prompt wording, error class names, and internal transition method syntax belong to implementation planning/data-model refinement rather than this feature specification.

---

## Key Entities

- **RiskReviewer**: Third review participant. Receives current ReviewInput, ProblemAnalysis, and SolutionAlternatives; returns trusted RiskAssessment or raises a participant/output-validation failure.
- **RiskAssessment**: Structured Risk Reviewer result containing zero or more material risks plus optional concise overall observations.
- **Risk**: One material downside exposure with local identity, description, affected scope, qualitative severity, structured basis, optional category, optional mitigation, and optional residual uncertainty.
- **Affected Scope**: Explicit indication that a risk applies to the overall proposal, one current alternative, or multiple current alternatives.
- **Risk Basis**: Structured traceable support from visible current-review artifacts. It may refer to original input, Analyst findings, or Solution Architect characteristics but does not create new user facts.
- **RiskReviewerStageInput**: Execution provenance record for the Risk Reviewer containing the exact current ReviewInput, ProblemAnalysis, and SolutionAlternatives used by that stage.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All Risk Reviewer contract, participant, and orchestration tests execute deterministically with no live external LLM or network dependency.
- **SC-002**: A valid deterministic Risk Reviewer response produces a trusted structured `RiskAssessment` with only `LOW`, `MEDIUM`, or `HIGH` severity values.
- **SC-003**: Every alternative-specific risk accepted into trusted state references only alternatives present in the current SolutionAlternatives input.
- **SC-004**: Representative fabricated, unknown, ambiguous, or otherwise unresolvable alternative or Analyst-item references are rejected before the output becomes trusted state.
- **SC-005**: A valid zero-risk result completes Risk Reviewer successfully without fabricated risks.
- **SC-006**: A valid zero-alternative Solution Architect result does not prevent Risk Reviewer from completing an overall-proposal risk assessment.
- **SC-007**: A successful deterministic Slice 4 run invokes exactly Analyst → Solution Architect → Risk Reviewer, preserves exact same-review artifact provenance, and ends `RUNNING` with Critic/Coordinator `PENDING`.
- **SC-008**: A Risk Reviewer output-validation failure produces `Risk Reviewer FAILED + Review INCOMPLETE`, preserves completed Analyst/Solution Architect outputs, leaves later stages pending, and propagates no invalid risk output.
- **SC-009**: A generic ordinary Risk Reviewer participant exception is distinguishable from output-validation failure without exposing raw exception detail.
- **SC-010**: No implementation artifact required by Slice 4 introduces Critic/Coordinator behavior, ranking/recommendation, persistence, provider SDK coupling, RAG, tools, retries, UI, generic workflow infrastructure, or numeric risk probability scoring.

---

## Traceability to Canonical Documents

This feature specification is derived from and must remain consistent with:

- `docs/01-product-vision.md` — genuine multi-agent collaboration, inspectable intermediate work, human decision authority, and bounded MVP scope;
- `docs/02-requirements.md` — FR-007 through FR-010 dependency/information propagation, FR-021 through FR-025 Risk Reviewer requirements, plus validation/failure/traceability requirements;
- `docs/03-architecture.md` — Review Orchestrator dependency order, StageExecution lifecycle, trusted-output propagation, mandatory-stage failure semantics, and in-memory traceability;
- `docs/04-agent-model.md` — Risk Reviewer responsibility, allowed inputs, RiskAssessment/Risk semantics, qualitative severity, evidence basis, prohibited behavior, and downstream dependency;
- `docs/05-quality-security.md` — deterministic testing, validation before propagation, visible failure, preservation of completed upstream work, and role integrity;
- `.specify/memory/constitution.md` — structured contracts, explicit evidence, visible failure, provider independence, minimal architecture, deterministic testability, human authority, and incremental delivery;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md` — existing structured-contract validation policy.