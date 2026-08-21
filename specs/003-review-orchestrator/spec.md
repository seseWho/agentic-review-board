# Feature Specification: Review Orchestrator v0.1

**Feature Branch**: `003-review-orchestrator`  
**Created**: 2026-08-21  
**Status**: Draft — internally reviewed, awaiting user approval  
**Input**: Third executable product increment derived from the canonical MVP documents and the completed Review Input + Analyst v0.1 and Solution Architect v0.1 slices.

## Purpose

This increment introduces the minimum review execution state and orchestration behavior needed to turn the already implemented Analyst and Solution Architect into a genuine dependency-driven review workflow.

It does not attempt to complete the five-stage review. Risk Reviewer, Critic, and Coordinator remain represented but unexecuted until their own later slices provide approved contracts and participant behavior.

The increment must therefore make two truths visible at the same time:

1. Analyst and Solution Architect can execute successfully in dependency order and exchange trusted structured artifacts.
2. A review that has executed only those two mandatory stages is not yet complete.

---

## User Scenarios & Testing

### User Story 1 - Execute implemented stages in dependency order (Priority: P1)

As a professional user, I want one review execution to run the implemented participants in the required dependency order so that the Analyst result genuinely becomes input to the Solution Architect rather than the two participants behaving as unrelated prompts.

**Why this priority**: This is the smallest increment that demonstrates real multi-agent information propagation and gives the Review Orchestrator an observable product responsibility.

**Independent Test**: Supply a valid `ReviewInput` and deterministic successful Analyst and Solution Architect behavior; verify that the Analyst executes first, the Solution Architect executes only after a trusted `ProblemAnalysis` exists, the exact trusted upstream artifacts are supplied, and the review preserves both successful stage records.

**Acceptance Scenarios**:

1. **Given** a valid newly created review, **When** execution starts, **Then** the review transitions from `CREATED` to `RUNNING` before the Analyst is invoked.
2. **Given** a running review with Analyst `PENDING`, **When** Analyst execution begins, **Then** the Analyst stage becomes `RUNNING` and records the current `ReviewInput` as its execution input.
3. **Given** the Analyst returns a trusted `ProblemAnalysis`, **When** the result is accepted, **Then** the Analyst stage becomes `COMPLETED` and exposes that trusted output.
4. **Given** a completed Analyst stage, **When** Solution Architect execution begins, **Then** the Solution Architect stage becomes `RUNNING` and records the original current `ReviewInput` plus the exact trusted `ProblemAnalysis` accepted from the Analyst stage as its execution inputs.
5. **Given** the Solution Architect returns trusted `SolutionAlternatives`, **When** the result is accepted, **Then** the Solution Architect stage becomes `COMPLETED` and exposes that trusted output.
6. **Given** both implemented stages complete successfully, **When** the review is inspected, **Then** Risk Reviewer, Critic, and Coordinator remain `PENDING` and the overall review remains `RUNNING`, because the canonical five-stage review is not yet complete.
7. **Given** a valid zero-alternative `SolutionAlternatives` result, **When** the Solution Architect stage accepts it, **Then** the stage is `COMPLETED`; a valid insufficient-alternatives outcome is not a stage failure.

---

### User Story 2 - Expose truthful stage and review lifecycle state (Priority: P1)

As a user, I want the review and every canonical stage to expose truthful lifecycle state so that I can distinguish what has not started, what is executing, what succeeded, what failed, and whether the overall review became incomplete.

**Why this priority**: Visible stage progression and truthful incomplete-review semantics are required for demonstration clarity and for preventing partial execution from appearing to be a successful final review.

**Independent Test**: Create a review containing all five canonical stage identities, inspect it before execution, then drive the implemented stages through deterministic success and failure transitions and verify the allowed observable states.

**Acceptance Scenarios**:

1. **Given** a newly created review before execution starts, **When** it is inspected, **Then** its overall status is `CREATED` and Analyst, Solution Architect, Risk Reviewer, Critic, and Coordinator are all `PENDING`.
2. **Given** execution has started, **When** the Analyst is about to be invoked, **Then** the overall review is `RUNNING` and Analyst is `RUNNING`.
3. **Given** a stage returns a trusted result, **When** that result is accepted, **Then** the stage becomes `COMPLETED` with a trusted output and without an error.
4. **Given** an implemented mandatory stage fails, **When** the failure is recorded, **Then** that stage becomes `FAILED`, the review becomes `INCOMPLETE`, and no dependent participant executes.
5. **Given** Analyst and Solution Architect both complete in Slice 3, **When** the review is inspected after the currently implemented workflow has no more executable stages, **Then** the review still reports `RUNNING` to mean "not yet terminal/complete", while the three later mandatory stages remain `PENDING`.
6. **Given** a review is `INCOMPLETE`, **When** it is inspected, **Then** it cannot expose or imply a complete `FinalReview`.
7. **Given** the `COMPLETED` review status exists in the lifecycle contract, **When** Slice 3 executes, **Then** no Slice 3 success path can reach it because three mandatory canonical stages remain unimplemented.

---

### User Story 3 - Preserve traceability and enforce StageExecution invariants (Priority: P1)

As a user, I want every executed stage record to show which trusted inputs it received and to represent success or failure consistently so that review progression is inspectable without relying on hidden conversational memory or logs.

**Why this priority**: The canonical architecture requires stage execution records to preserve relevant inputs or input references, validated output when successful, and error information when failed.

**Independent Test**: Inspect stage records across `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED` cases and verify input provenance, terminal output/error consistency, and absence of duplicated independent trusted-output state.

**Acceptance Scenarios**:

1. **Given** a `PENDING` stage that has never executed, **When** it is inspected, **Then** it contains no execution input record, trusted output, or error.
2. **Given** an implemented stage has transitioned to `RUNNING`, **When** it is inspected, **Then** its relevant execution inputs are recorded before participant invocation and it contains neither trusted output nor terminal error.
3. **Given** a stage is `COMPLETED`, **When** it is inspected, **Then** its execution inputs remain inspectable, its trusted output is present, and its error is absent.
4. **Given** a stage is `FAILED`, **When** it is inspected, **Then** its execution inputs remain inspectable, its trusted output is absent, and concise structured error information is present.
5. **Given** a trusted `ProblemAnalysis` or `SolutionAlternatives` result, **When** the review exposes that artifact, **Then** it is the same logical trusted artifact owned by the corresponding completed stage record rather than an independently mutable duplicate stored elsewhere in review state.
6. **Given** stage input provenance is required, **When** Slice 3 models it, **Then** it does not require a generic repository-wide artifact/reference framework; direct structured snapshots, typed stage-local input records, or equivalent minimal representation remain valid implementation choices for planning.

---

### User Story 4 - Preserve completed work and stop dependent execution on failure (Priority: P1)

As a user, I want a mandatory-stage failure to stop downstream execution while preserving earlier successful results so that failures remain visible and useful evidence is not discarded or replaced with fabricated recovery data.

**Independent Test**: Run deterministic Analyst-failure and Solution-Architect-failure scenarios and verify exact stage statuses, preserved input provenance, preserved earlier trusted outputs, error information, review status, and absence of dependent participant invocation.

**Acceptance Scenarios**:

1. **Given** the Analyst participant fails before producing trusted `ProblemAnalysis`, **When** orchestration handles that participant failure, **Then** Analyst is `FAILED`, its recorded input remains inspectable, Solution Architect and all later stages remain `PENDING`, the review becomes `INCOMPLETE`, and no `ProblemAnalysis` or `SolutionAlternatives` is fabricated.
2. **Given** Analyst completed successfully but Solution Architect fails, **When** orchestration handles that participant failure, **Then** the Analyst stage and trusted `ProblemAnalysis` remain inspectable, Solution Architect is `FAILED` with its recorded inputs and no trusted output, later stages remain `PENDING`, and the review is `INCOMPLETE`.
3. **Given** an existing participant raises a known output-validation exception, **When** the stage error is recorded, **Then** the error identifies an output-validation failure without storing private reasoning, full prompts, or full raw model output.
4. **Given** an invoked participant raises another exception whose cause is not more specifically classified at this boundary, **When** the stage error is recorded, **Then** it is represented as an execution failure rather than being falsely labeled as schema validation or a specific provider failure.
5. **Given** orchestration itself encounters an invariant violation or internal application defect outside the invoked participant boundary, **When** that defect occurs, **Then** it must not be silently hidden as an ordinary participant failure.
6. **Given** a mandatory stage has failed, **When** orchestration considers a dependent stage, **Then** the dependent participant is not invoked and the dependent stage remains `PENDING`.

---

### User Story 5 - Keep separate review executions isolated (Priority: P1)

As a user, I want each review invocation to create fresh in-memory review state so that outputs, errors, statuses, and stage input records from a previous review cannot implicitly influence a new review.

**Independent Test**: Run two deterministic reviews sequentially through the same orchestrator instance and verify that the second review starts in `CREATED` with fresh `PENDING` stages and contains only its own input and subsequent artifacts.

**Acceptance Scenarios**:

1. **Given** one review has completed the two implemented stages, **When** another review is created, **Then** the second review begins `CREATED` with five fresh `PENDING` stage records and no inherited inputs, outputs, or errors.
2. **Given** a previous review ended `INCOMPLETE`, **When** another review is created, **Then** the second review is not born incomplete and does not inherit the previous failure.
3. **Given** two distinct `ReviewInput` values, **When** they are executed sequentially, **Then** each returned review preserves its own original input unchanged and its stage input provenance references only artifacts from that review execution.

---

## Edge Cases and Clarifications

- Slice 3 executes only the participants already implemented: Analyst and Solution Architect.
- All five canonical stage identities exist in every review from creation. Risk Reviewer, Critic, and Coordinator remain `PENDING` because their contracts and participant behavior belong to later slices.
- `ReviewStatus.RUNNING` means the review has started and has not yet reached a terminal review outcome. In Slice 3 it may therefore remain `RUNNING` even when no participant is actively executing, because later mandatory stages are still pending and unimplemented.
- `ReviewStatus.COMPLETED` is part of the canonical lifecycle contract but is intentionally unreachable in Slice 3.
- A valid zero-alternative `SolutionAlternatives` result is a trusted Solution Architect output and completes the stage successfully.
- A failed stage has no trusted output. Partially parsed, invalid, or rejected generated content must not be preserved as trusted stage output.
- Downstream stages blocked by a mandatory failure remain `PENDING`; Slice 3 does not introduce `BLOCKED` because the canonical MVP minimum stage states are `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`.
- Relevant stage inputs are retained in-memory for the active review. Slice 3 does not require persistent identifiers, a generic artifact store, or a generic cross-project reference system.
- The orchestrator controls progression but does not call `LLMPort` directly. Participant-specific model communication and generated-output validation remain inside the existing participant boundaries.
- No UI behavior is introduced. Review and stage state must be structurally inspectable so a later Review Application/UI adapter can present it without owning orchestration.
- No retry, timeout, cancellation, pause/resume, concurrency, persistence, or distributed execution behavior is introduced.

---

## Requirements

### Functional Requirements

- **FR-001**: Creating a review MUST produce a fresh isolated in-memory `Review` that preserves the supplied validated `ReviewInput` unchanged.
- **FR-002**: A newly created `Review` MUST begin with overall status `CREATED`.
- **FR-003**: Every `Review` MUST represent exactly the five canonical stage identities: Analyst, Solution Architect, Risk Reviewer, Critic, and Coordinator.
- **FR-004**: Every newly created stage execution MUST begin `PENDING` and MUST contain no execution-input record, trusted output, or error.
- **FR-005**: Starting review execution MUST transition the overall review from `CREATED` to `RUNNING` before the Analyst participant is invoked.
- **FR-006**: The Review Orchestrator MUST control progression between participants; participants MUST NOT directly invoke one another or update global workflow progression.
- **FR-007**: In Slice 3, the Orchestrator MUST execute Analyst before Solution Architect and MUST NOT invoke Solution Architect unless Analyst has completed with trusted `ProblemAnalysis`.
- **FR-008**: Immediately before an implemented participant is invoked, its stage MUST transition from `PENDING` to `RUNNING` and record the relevant trusted inputs supplied to that invocation.
- **FR-009**: Analyst execution input provenance MUST identify the current original `ReviewInput` supplied to Analyst.
- **FR-010**: Solution Architect execution input provenance MUST identify the current original `ReviewInput` and the exact trusted `ProblemAnalysis` accepted from the Analyst stage.
- **FR-011**: A valid participant result MUST enter trusted review state only after the participant's existing validation boundary has returned its trusted contract.
- **FR-012**: A completed stage MUST contain its recorded execution inputs and trusted output, MUST contain no error, and MUST have status `COMPLETED`.
- **FR-013**: A failed stage MUST retain its recorded execution inputs, MUST contain concise structured error information, MUST contain no trusted output, and MUST have status `FAILED`.
- **FR-014**: A `PENDING` stage MUST contain no execution input record, trusted output, or error; a `RUNNING` stage MUST contain recorded execution inputs but no trusted output or terminal error.
- **FR-015**: Trusted participant output MUST have one logical owner in review state: the corresponding completed stage execution. Any review-level convenience access MUST expose that same logical artifact rather than maintain an independently diverging duplicate.
- **FR-016**: A valid zero-alternative `SolutionAlternatives` result MUST complete the Solution Architect stage successfully.
- **FR-017**: A mandatory participant failure MUST mark the current stage `FAILED`, stop dependent execution, and make the overall review `INCOMPLETE`.
- **FR-018**: When a later implemented stage fails, all earlier completed stage records, their input provenance, and their trusted outputs MUST remain inspectable in the current review.
- **FR-019**: Stages that have not executed because an upstream mandatory stage failed MUST remain `PENDING` and their participant logic MUST NOT be invoked.
- **FR-020**: The overall review lifecycle MUST support `CREATED`, `RUNNING`, `INCOMPLETE`, and `COMPLETED` semantics consistent with the canonical architecture.
- **FR-021**: Slice 3 success MUST NOT transition the review to `COMPLETED`; `COMPLETED` remains reserved for the future state in which all five mandatory canonical stages have completed successfully.
- **FR-022**: Risk Reviewer, Critic, and Coordinator stage records MUST remain `PENDING` throughout successful Slice 3 execution and MUST NOT contain fabricated inputs or outputs.
- **FR-023**: Known Analyst or Solution Architect output-validation failures MUST be distinguishable in `ReviewError` information from otherwise-unclassified participant execution failures.
- **FR-024**: Error information MUST be concise and suitable for user-visible diagnosis without requiring or exposing private chain-of-thought, full prompts, full raw model responses, credentials, or secrets.
- **FR-025**: Participant exceptions handled as stage failures MUST NOT cause dependent execution to continue or fabricate recovery outputs.
- **FR-026**: Internal orchestrator invariant violations or application defects MUST NOT be silently suppressed or deliberately mislabeled as ordinary participant failures.
- **FR-027**: Creating a subsequent review MUST create fresh review/stage state and MUST NOT inherit inputs, outputs, errors, status, assumptions, or execution-input provenance from a previous review.
- **FR-028**: Core orchestration behavior MUST be deterministically testable without network access or a live external LLM.
- **FR-029**: Slice 3 MUST preserve the existing provider-neutral participant and `LLMPort` boundaries; the Orchestrator MUST NOT contain provider-specific model communication logic.
- **FR-030**: Stage input traceability MUST be achieved without requiring a generic workflow engine, generic artifact repository, persistent reference registry, or cross-project reference abstraction.

### StageExecution State Invariants

The observable stage-state contract is:

```text
PENDING
- execution inputs: absent
- trusted output: absent
- error: absent

RUNNING
- execution inputs: present
- trusted output: absent
- error: absent

COMPLETED
- execution inputs: present
- trusted output: present
- error: absent

FAILED
- execution inputs: present
- trusted output: absent
- error: present
```

No valid stage execution may simultaneously expose a trusted output and terminal error.

### Review Lifecycle

```text
CREATED
   │ start execution
   ▼
RUNNING
   │
   ├── implemented mandatory stage failure ──► INCOMPLETE
   │
   └── all five mandatory stages succeed ────► COMPLETED
```

In Slice 3, the success path remains `RUNNING` after Solution Architect because Risk Reviewer, Critic, and Coordinator remain `PENDING`.

---

## Scope Boundaries

This increment introduces only the review execution/lifecycle behavior needed to orchestrate the already implemented Analyst and Solution Architect.

This increment does not introduce:

- Risk Reviewer participant behavior or `RiskAssessment` contract;
- Critic participant behavior or `CriticalReview` contract;
- Coordinator participant behavior, ranking, preferred alternative, `FinalReview`, or final recommendation;
- execution of any stage after Solution Architect;
- a UI or concrete Review Application presentation flow;
- a concrete LLM provider or adapter;
- provider-specific exception classes solely for orchestration;
- automatic retries, backoff, timeout policy, cancellation, pause/resume, or checkpoint recovery;
- timestamps, duration measurement, telemetry, tracing platform, or logging framework;
- persistence, review history, database storage, or cross-review memory;
- RAG, embeddings, document ingestion, external tools, MCP, or autonomous actions;
- concurrency, asynchronous scheduling, parallel execution, queues, workers, or distributed orchestration;
- generic workflow engines, multi-agent frameworks, generic artifact repositories, or generic cross-project reference abstractions.

Concrete package layout, exact Pydantic/dataclass syntax, exact stage-input representation, exception-mapping mechanics, type parameters, and internal orchestration method names belong to implementation planning, not this feature specification.

---

## Key Entities

- **Review**: One isolated in-memory review execution containing the original `ReviewInput`, overall lifecycle status, and exactly five canonical `StageExecution` records. Trusted stage outputs are logically owned by their completed stage records; review-level artifact access must not create an independently diverging second source of truth.
- **StageIdentity**: Closed identity of one canonical review stage: Analyst, Solution Architect, Risk Reviewer, Critic, or Coordinator.
- **StageStatus**: Closed stage lifecycle state: `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`.
- **StageExecution**: Inspectable in-memory record for one canonical stage containing its identity, lifecycle status, relevant execution-input provenance once execution begins, trusted output only when completed, and concise error information only when failed.
- **ReviewStatus**: Overall review lifecycle state: `CREATED`, `RUNNING`, `INCOMPLETE`, or `COMPLETED`. Slice 3 can create `CREATED`, transition to `RUNNING`, and produce `INCOMPLETE`; `COMPLETED` is defined but unreachable until later slices implement all mandatory stages.
- **ReviewError**: Concise structured stage failure information distinguishing known output-validation failures from otherwise-unclassified participant execution failures without storing private reasoning or unsafe raw model content.
- **ProblemAnalysis**: Existing trusted Analyst output, logically owned by the completed Analyst stage and supplied explicitly to Solution Architect.
- **SolutionAlternatives**: Existing trusted Solution Architect output, logically owned by the completed Solution Architect stage, including the valid zero-alternative outcome.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All acceptance scenarios can be exercised with deterministic substitutes and no live external LLM or network dependency.
- **SC-002**: A newly created review is `CREATED` with exactly five `PENDING` stage records and no inherited execution data.
- **SC-003**: A successful deterministic Slice 3 run transitions the review to `RUNNING`, invokes Analyst exactly once before Solution Architect, and passes the exact current `ReviewInput` and trusted `ProblemAnalysis` required by Solution Architect.
- **SC-004**: After successful Slice 3 execution, Analyst and Solution Architect are `COMPLETED`, Risk Reviewer/Critic/Coordinator are `PENDING`, both completed stages expose their execution-input provenance and trusted outputs, and the review remains `RUNNING` rather than falsely `COMPLETED`.
- **SC-005**: An Analyst failure prevents Solution Architect invocation, leaves all downstream stages `PENDING`, records the Analyst input provenance and visible stage error, and produces an `INCOMPLETE` review with no fabricated output.
- **SC-006**: A Solution Architect failure preserves the completed Analyst stage and trusted `ProblemAnalysis`, retains the Solution Architect execution-input provenance, leaves later stages `PENDING`, records a visible stage error, and produces an `INCOMPLETE` review without trusted `SolutionAlternatives`.
- **SC-007**: A valid zero-alternative Solution Architect outcome completes the stage and remains inspectable as trusted `SolutionAlternatives`.
- **SC-008**: Every valid `StageExecution` satisfies the state/output/error invariants defined by this specification.
- **SC-009**: Two sequential review executions are demonstrably isolated; the second starts `CREATED` with fresh stage state and contains no input provenance, output, or error inherited from the first.
- **SC-010**: No implementation artifact required by Slice 3 needs persistence, a provider SDK, retry infrastructure, workflow framework, UI framework, RAG, external tools, or later-agent contracts.

---

## Traceability to Canonical Documents

This feature specification is derived from and must remain consistent with:

- `docs/01-product-vision.md` — genuine multi-agent collaboration, visible intermediate work, and human decision authority;
- `docs/02-requirements.md` — FR-005 through FR-010, FR-041 through FR-047, FR-049 through FR-057, NFR-005 through NFR-010, and NFR-013 through NFR-016;
- `docs/03-architecture.md` — Review Orchestrator responsibility, five-stage dependency order, `CREATED → RUNNING → INCOMPLETE/COMPLETED` review lifecycle, StageExecution lifecycle, relevant input retention, trusted-output propagation, in-memory traceability, and mandatory-stage failure semantics;
- `docs/04-agent-model.md` — Analyst and Solution Architect allowed inputs/outputs, explicit artifact propagation, no hidden agent state, no participant workflow control, and the fixed five-role sequence;
- `docs/05-quality-security.md` — orchestration tests, deterministic substitution, validation-before-propagation, visible failure, preservation of completed upstream artifacts, and role integrity;
- `.specify/memory/constitution.md` — genuine collaboration, validated contracts, traceability, visible failure, minimal architecture, provider independence, deterministic testability, and incremental delivery.
