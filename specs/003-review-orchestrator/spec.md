# Feature Specification: Review Orchestrator v0.1

**Feature Branch**: `003-review-orchestrator`  
**Created**: 2026-08-21  
**Status**: Draft — awaiting user review  
**Input**: Third executable product increment derived from the canonical MVP documents and the completed Review Input + Analyst v0.1 and Solution Architect v0.1 slices.

## User Scenarios & Testing

### User Story 1 - Execute the implemented review stages in dependency order (Priority: P1)

As a professional user, I want one review execution to run the implemented participants in the required dependency order so that the output of the Analyst genuinely becomes input to the Solution Architect rather than the two participants behaving as unrelated prompts.

**Why this priority**: This is the smallest increment that turns the two implemented participants into a real multi-agent workflow and provides direct evidence for the product's central collaboration claim.

**Independent Test**: Supply a valid `ReviewInput` and deterministic successful Analyst and Solution Architect substitutes; verify that the Analyst executes first, the Solution Architect executes only after a trusted `ProblemAnalysis` exists, the exact trusted upstream artifacts are propagated, and the resulting review state preserves both validated outputs.

**Acceptance Scenarios**:

1. **Given** a valid `ReviewInput`, **When** a review execution starts, **Then** the Analyst is the first participant invoked.
2. **Given** the Analyst completes successfully with a trusted `ProblemAnalysis`, **When** execution continues, **Then** the Solution Architect is invoked with the original `ReviewInput` and that trusted `ProblemAnalysis`.
3. **Given** both currently implemented stages complete successfully, **When** the review state is inspected, **Then** both stage executions are `COMPLETED` and both validated outputs remain inspectable.
4. **Given** both currently implemented stages complete successfully, **When** the overall review state is inspected, **Then** the review remains `RUNNING` rather than being falsely marked `COMPLETED`, because Risk Reviewer, Critic, and Coordinator have not yet executed.
5. **Given** a valid zero-alternative `SolutionAlternatives` result, **When** the Solution Architect stage completes, **Then** the stage is still `COMPLETED` because the zero-alternative outcome is a valid trusted result rather than a stage failure.

---

### User Story 2 - Expose truthful stage and review lifecycle state (Priority: P1)

As a user, I want each review stage and the overall review to expose explicit execution status so that I can tell what has run, what succeeded, what remains pending, and whether execution became incomplete.

**Why this priority**: Visible, truthful workflow state is required for multi-agent demonstration clarity and for preventing an incomplete execution from appearing successful.

**Independent Test**: Create a review execution with all five canonical stage identities; drive the implemented stages through their lifecycle using deterministic participants and verify stage and review statuses at each observable checkpoint.

**Acceptance Scenarios**:

1. **Given** a newly created review, **When** its stages are inspected before execution, **Then** Analyst, Solution Architect, Risk Reviewer, Critic, and Coordinator are all represented and each is `PENDING`.
2. **Given** a stage is about to execute, **When** its participant is invoked, **Then** that stage transitions from `PENDING` to `RUNNING` before a terminal stage status is recorded.
3. **Given** a stage returns a valid trusted result, **When** the result is accepted, **Then** the stage transitions to `COMPLETED` and retains that validated result.
4. **Given** Analyst and Solution Architect have completed in this slice, **When** later stages are inspected, **Then** Risk Reviewer, Critic, and Coordinator remain `PENDING` and are not simulated or fabricated.
5. **Given** an implemented mandatory stage fails, **When** the review state is updated, **Then** the failed stage becomes `FAILED`, the overall review becomes `INCOMPLETE`, and no stage depending on the failed stage executes.
6. **Given** a review is `INCOMPLETE`, **When** it is inspected, **Then** it cannot expose or imply a complete `FinalReview`.

---

### User Story 3 - Preserve completed work and stop dependent execution on failure (Priority: P1)

As a user, I want a mandatory-stage failure to stop downstream execution while preserving earlier successful results so that failures are visible and useful evidence is not discarded or replaced with fabricated recovery data.

**Independent Test**: Run deterministic failure scenarios for the Analyst and Solution Architect and verify the exact stage statuses, preserved upstream results, error information, and absence of downstream participant invocation.

**Acceptance Scenarios**:

1. **Given** the Analyst fails before producing trusted `ProblemAnalysis`, **When** orchestration handles the failure, **Then** Analyst is `FAILED`, Solution Architect remains `PENDING`, the review is `INCOMPLETE`, and no `ProblemAnalysis` or `SolutionAlternatives` is fabricated.
2. **Given** the Analyst completed successfully but the Solution Architect fails, **When** orchestration handles the failure, **Then** the trusted `ProblemAnalysis` remains inspectable, Solution Architect is `FAILED`, later stages remain `PENDING`, and the review is `INCOMPLETE`.
3. **Given** a known participant output-validation failure, **When** the stage error is recorded, **Then** the review exposes a concise structured error that identifies an output-validation failure without copying private reasoning or full model output.
4. **Given** a participant raises another execution exception whose cause cannot be classified more specifically at this boundary, **When** the stage error is recorded, **Then** it is represented as an execution failure rather than being falsely labeled as a schema-validation failure.
5. **Given** a mandatory stage has failed, **When** orchestration reaches a dependent stage, **Then** that dependent participant is not invoked and its stage remains `PENDING`.

---

### User Story 4 - Keep separate review executions isolated (Priority: P1)

As a user, I want each review invocation to create fresh in-memory review state so that outputs, errors, and statuses from a previous review cannot implicitly influence a new review.

**Independent Test**: Run two deterministic reviews sequentially through the same orchestrator instance and verify that the second execution starts with fresh stage records and contains only its own input and generated artifacts.

**Acceptance Scenarios**:

1. **Given** one review has completed the two implemented stages, **When** another review starts, **Then** the second review starts with fresh `PENDING` stage records and contains none of the first review's outputs or errors.
2. **Given** a previous review ended `INCOMPLETE`, **When** another review starts, **Then** the second review is not born incomplete and does not inherit the previous failure.
3. **Given** two distinct `ReviewInput` values, **When** they are run sequentially, **Then** each returned review state preserves its own original input unchanged.

## Edge Cases

- This slice implements orchestration only for the two participants that already exist: Analyst and Solution Architect.
- All five canonical stage identities are represented in review state from creation, but Risk Reviewer, Critic, and Coordinator remain `PENDING` because their participant contracts and implementations belong to later slices.
- Successful execution of Analyst and Solution Architect MUST NOT mark the overall review `COMPLETED`; the canonical complete review requires all five mandatory stages.
- A valid zero-alternative `SolutionAlternatives` result is a successful Solution Architect result and MUST NOT be converted into a stage failure merely because no alternatives are present.
- An output-validation exception raised by an existing participant is a known stage output failure; unrelated exceptions MUST NOT be guessed to be provider failures unless a later approved boundary provides reliable provider-error classification.
- A failed stage has no trusted output. The orchestrator MUST NOT preserve a partially parsed or invalid generated object as the stage result.
- Downstream stages blocked by a failure remain `PENDING` in this increment; no additional `BLOCKED` status is introduced because the canonical MVP minimum status set is `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.
- Stage lifecycle records are in-memory review state only. This slice introduces no persistence, timestamps, database identifiers, resumability, retries, cancellation, concurrency, or distributed execution.
- The orchestrator controls progression but does not call the `LLMPort` directly; participant-specific model communication remains inside the existing participant boundaries.
- No UI behavior is introduced. The structured review state is designed to be inspectable by a future Review Application/UI adapter without coupling this slice to presentation technology.

## Requirements

### Functional Requirements

- **FR-001**: Starting a review MUST create a fresh isolated in-memory `Review` that preserves the supplied validated `ReviewInput` unchanged.
- **FR-002**: Every `Review` MUST represent exactly the five canonical stage identities: Analyst, Solution Architect, Risk Reviewer, Critic, and Coordinator.
- **FR-003**: Every newly created stage execution MUST begin in `PENDING` state and MUST NOT contain a trusted output or error.
- **FR-004**: The Review Orchestrator MUST be the component that controls progression between participants; participants MUST NOT directly invoke one another or update global workflow progression.
- **FR-005**: In this increment, the Orchestrator MUST execute Analyst before Solution Architect and MUST NOT invoke Solution Architect unless Analyst has completed with a trusted `ProblemAnalysis`.
- **FR-006**: The Solution Architect invocation MUST receive the original current `ReviewInput` and the exact trusted `ProblemAnalysis` accepted from the current Analyst stage.
- **FR-007**: Immediately before an implemented participant is invoked, its stage MUST transition from `PENDING` to `RUNNING`.
- **FR-008**: A valid participant result MUST be accepted into review state only after the participant's existing validation boundary has returned a trusted contract, after which the stage MUST become `COMPLETED` and expose that trusted output.
- **FR-009**: A valid zero-alternative `SolutionAlternatives` result MUST complete the Solution Architect stage successfully.
- **FR-010**: A mandatory participant failure MUST mark the current stage `FAILED`, record concise structured `ReviewError` information, stop dependent execution, and make the overall review `INCOMPLETE`.
- **FR-011**: When a later implemented stage fails, all earlier trusted completed outputs MUST remain inspectable in the current review state.
- **FR-012**: A failed stage MUST NOT expose invalid or partial generated content as trusted stage output.
- **FR-013**: Stages that have not executed because an upstream mandatory stage failed MUST remain `PENDING` in this increment and their participant logic MUST NOT be invoked.
- **FR-014**: The overall review status MUST support at least `RUNNING`, `INCOMPLETE`, and `COMPLETED` semantics consistent with the canonical lifecycle; a newly started execution becomes `RUNNING`.
- **FR-015**: The overall review MUST become `INCOMPLETE` when an implemented mandatory stage fails.
- **FR-016**: The overall review MUST NOT become `COMPLETED` merely because Analyst and Solution Architect have succeeded; `COMPLETED` remains reserved for the future state in which all five mandatory canonical stages have completed successfully.
- **FR-017**: Risk Reviewer, Critic, and Coordinator stage records MUST remain `PENDING` throughout successful Slice 3 execution and MUST NOT contain fabricated outputs.
- **FR-018**: Known Analyst or Solution Architect output-validation failures MUST be distinguishable in structured review error information from otherwise-unclassified execution failures.
- **FR-019**: Error information MUST be concise and suitable for user-visible diagnosis without requiring or exposing private chain-of-thought, full prompts, full raw model responses, credentials, or secrets.
- **FR-020**: Starting a subsequent review MUST create fresh stage state and MUST NOT inherit outputs, errors, status, or assumptions from a previous review execution.
- **FR-021**: Core orchestration behavior MUST be deterministically testable without network access or a live external LLM.
- **FR-022**: This increment MUST preserve the existing provider-neutral participant and `LLMPort` boundaries; the Orchestrator MUST NOT contain provider-specific model communication logic.

### Scope Boundaries

This increment introduces the minimum review execution/lifecycle behavior needed to orchestrate the already implemented Analyst and Solution Architect.

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
- concurrency, asynchronous stage scheduling, parallel execution, queues, workers, or distributed orchestration;
- generic workflow engines, multi-agent frameworks, generic artifact repositories, or generic cross-project reference abstractions.

Concrete package layout, exact Pydantic syntax, exception mapping mechanics, type parameters, and internal orchestration method names belong to implementation planning, not this feature specification.

### Key Entities

- **Review**: One isolated in-memory review execution containing the original `ReviewInput`, overall review status, the five canonical stage execution records, and trusted outputs produced during that execution.
- **StageIdentity**: Closed identity of one canonical review stage: Analyst, Solution Architect, Risk Reviewer, Critic, or Coordinator.
- **StageStatus**: Closed stage lifecycle state: `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`.
- **StageExecution**: Inspectable in-memory record for one canonical stage containing its identity, status, trusted output when completed, and concise error information when failed.
- **ReviewStatus**: Overall review lifecycle state with `RUNNING`, `INCOMPLETE`, and `COMPLETED` semantics. Slice 3 can produce `RUNNING` and `INCOMPLETE`; `COMPLETED` is defined for lifecycle completeness but is not reachable until future slices implement all mandatory stages.
- **ReviewError**: Concise structured stage failure information distinguishing known output-validation failures from otherwise-unclassified execution failures without storing private reasoning or unsafe raw model content.
- **ProblemAnalysis**: Existing trusted Analyst output retained by the review and supplied to Solution Architect.
- **SolutionAlternatives**: Existing trusted Solution Architect output retained by the review, including the valid zero-alternative outcome.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All acceptance scenarios in this specification can be exercised using deterministic substitutes with no live LLM or network dependency.
- **SC-002**: A successful deterministic run invokes Analyst exactly once before Solution Architect and passes the exact current `ReviewInput` and trusted `ProblemAnalysis` required by the Solution Architect.
- **SC-003**: After a successful Slice 3 run, Analyst and Solution Architect are `COMPLETED`, Risk Reviewer/Critic/Coordinator are `PENDING`, both trusted outputs are inspectable, and the review status is `RUNNING` rather than falsely `COMPLETED`.
- **SC-004**: An Analyst failure prevents Solution Architect invocation, leaves all downstream stages `PENDING`, records a visible stage error, and produces an `INCOMPLETE` review with no fabricated outputs.
- **SC-005**: A Solution Architect failure preserves the already trusted `ProblemAnalysis`, leaves Risk Reviewer/Critic/Coordinator `PENDING`, records a visible stage error, and produces an `INCOMPLETE` review without `SolutionAlternatives`.
- **SC-006**: A valid zero-alternative Solution Architect outcome completes the Solution Architect stage and remains inspectable as trusted `SolutionAlternatives`.
- **SC-007**: Two sequential review executions are demonstrably isolated: the second starts with fresh stage state and contains no output or error inherited from the first.
- **SC-008**: No implementation artifact required by this feature needs persistence, a provider SDK, retry infrastructure, a workflow framework, a UI framework, RAG, external tools, or later-agent contracts.

## Traceability to Canonical Documents

This feature specification is derived from and must remain consistent with:

- `docs/01-product-vision.md` — genuine multi-agent collaboration, visible intermediate work, and human decision authority;
- `docs/02-requirements.md` — FR-005 through FR-010, FR-041 through FR-047, FR-049 through FR-057, NFR-005 through NFR-010, and NFR-013 through NFR-016;
- `docs/03-architecture.md` — Review Orchestrator responsibility, five-stage dependency order, Review/StageExecution lifecycle, trusted-output propagation, in-memory traceability, and mandatory-stage failure semantics;
- `docs/04-agent-model.md` — Analyst and Solution Architect input/output boundaries and the fixed five-role sequence;
- `docs/05-quality-security.md` — orchestration tests, deterministic substitution, validation-before-propagation, visible failure, and preservation of role integrity;
- `.specify/memory/constitution.md` — genuine collaboration, validated contracts, traceability, visible failure, minimal architecture, provider independence, deterministic testability, and incremental delivery.
