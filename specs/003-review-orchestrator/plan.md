# Implementation Plan: Review Orchestrator v0.1

**Branch**: `003-review-orchestrator`  
**Date**: 2026-08-21  
**Spec**: `specs/003-review-orchestrator/spec.md`  
**Status**: Draft — internally reviewed, awaiting user approval

## 1. Summary

Implement the smallest review execution slice that turns the existing Analyst and Solution Architect participants into one real dependency-driven workflow without implementing later review roles.

The increment introduces:

- `StageIdentity` for the five canonical review stages;
- `StageStatus` for `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`;
- `ReviewStatus` for `CREATED`, `RUNNING`, `INCOMPLETE`, and `COMPLETED`;
- `ReviewErrorKind` and `ReviewError` for concise stage-failure information;
- stage-local typed input records for Analyst and Solution Architect execution provenance;
- `StageExecution` as the validated immutable state snapshot for one canonical stage;
- `Review` as one isolated immutable review-state snapshot containing the original `ReviewInput` and exactly five stage records;
- cross-stage Review invariants that keep overall status, dependency order, and stage states mutually consistent;
- `ReviewOrchestrator` as the application component that executes Analyst then Solution Architect, accepts only trusted participant outputs, records lifecycle transitions, stops on mandatory failure, and leaves later stages pending;
- deterministic domain and orchestration tests covering state invariants, sequencing, propagation, failure, zero-alternative success, and review isolation.

The successful Slice 3 outcome is deliberately not a complete review:

```text
ReviewStatus = RUNNING

ANALYST             = COMPLETED
SOLUTION_ARCHITECT  = COMPLETED
RISK_REVIEWER       = PENDING
CRITIC              = PENDING
COORDINATOR         = PENDING
```

`COMPLETED` exists in the review lifecycle enum but remains unreachable for valid Slice 3 `Review` state because all five mandatory stages cannot yet complete.

The increment reuses the existing Pydantic v2 dependency, `Analyst`, `SolutionArchitect`, their trusted output contracts, and the existing provider-neutral model boundary. It introduces no new production dependency, provider adapter, workflow framework, persistence, UI, or later-stage contract.

---

## 2. Technical Context

**Language/Version**: Python >=3.12  
**Production Dependency**: existing `pydantic>=2.13,<3`; no new production dependency  
**Development Dependencies**: existing pytest, Ruff, and mypy configuration  
**Storage**: none; review state is in-memory only  
**Target Platform**: single local Python process and CI  
**External Model Access**: unchanged; only existing participants know `LLMPort`  
**Execution Model**: synchronous and sequential  
**Security Scope**: no credentials, persistent history, full raw-model-output storage, external tools, autonomous actions, or confidential-data dependency

Existing contracts/components reused unchanged:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
Analyst
AnalystOutputError
SolutionArchitect
SolutionArchitectOutputError
LLMPort
```

The Orchestrator depends on participant objects, not on `LLMPort`.

---

## 3. Constitution Check

### I. Genuine Agent Collaboration and Role Integrity — PASS

Slice 3 establishes the first real workflow progression across multiple participants:

```text
ReviewInput
    ↓
Analyst
    ↓ trusted ProblemAnalysis
Solution Architect
    ↓ trusted SolutionAlternatives
```

The Orchestrator owns progression. Analyst and Solution Architect remain semantically distinct and do not invoke each other. Risk Reviewer, Critic, and Coordinator are represented only as pending stage identities and receive no fabricated behavior or output.

### II. Structured Contracts and Validation — PASS

The Orchestrator accepts only already validated participant return values into `StageExecution.output`.

`StageExecution` and `Review` enforce lifecycle invariants so impossible combinations such as `COMPLETED + error`, `FAILED + trusted output`, `PENDING + execution inputs`, `RUNNING review + failed stage`, or `COMPLETED review + pending stages` are invalid review state.

Generated-output validation remains inside the existing participant boundaries; orchestration does not duplicate or weaken those checks.

### III. Traceability, Uncertainty, and Explicit Evidence — PASS

Each executed stage retains explicit structured provenance for the trusted inputs supplied to it:

```text
AnalystStageInput
- review_input: ReviewInput

SolutionArchitectStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

The Solution Architect input references the same logical trusted `ProblemAnalysis` produced by the completed Analyst stage. No hidden conversational memory or log reconstruction is required.

Trusted stage output has one logical owner: its completed `StageExecution`. `Review` does not maintain independently mutable duplicate `problem_analysis` or `solution_alternatives` fields.

### IV. Human Decision Authority — PASS

Slice 3 produces no ranking, preferred alternative, final recommendation, decision, or autonomous action. A successful Slice 3 execution remains an unfinished review.

### V. Minimal Architecture and Evidence-Driven Complexity — PASS

The increment adds only:

- one small execution-state domain module;
- one application-level orchestrator;
- deterministic tests.

It does not add a generic workflow engine, agent superclass, event bus, artifact repository, persistent reference registry, async scheduler, retries, or state store.

Stage-local typed input records are preferred over a generic `Artifact` abstraction because only two concrete participant input shapes currently exist.

### VI. Provider Independence and Boundary Discipline — PASS

`ReviewOrchestrator` receives `Analyst` and `SolutionArchitect` instances and invokes their public methods. It does not import, receive, configure, or call `LLMPort` or any concrete provider SDK.

Provider-specific exception classification is not invented in this slice.

### VII. Deterministic Testability and Visible Failure — PASS

Orchestration tests use the existing participants with a deterministic fake `LLMPort` to control:

- successful Analyst output;
- successful Solution Architect output;
- zero-alternative Solution Architect output;
- malformed participant output;
- arbitrary participant/model execution exception.

This proves sequencing and actual structured propagation without network access.

### VIII. Security by Minimization and Least Capability — PASS

`ReviewError` stores only a stable concise failure summary and category. It does not store full prompts, full raw model responses, credentials, private chain-of-thought, or stack traces as domain state.

### IX. Incremental Delivery and Explicit Architectural Decisions — PASS

The slice implements only the lifecycle/orchestration concepts already required by canonical architecture. Pydantic remains governed by ADR-0001. No new technology, runtime pattern, persistence model, integration, or security capability is introduced, so no new ADR is required.

**Constitution gate result**: PASS.

---

## 4. Architectural and Contract Decisions

### 4.1 Separate execution state from original review input

Keep the existing `domain/review.py` focused on the already accepted `ReviewInput` contract.

Introduce a dedicated execution-state module for workflow concepts rather than overloading `ReviewInput` with lifecycle behavior.

Proposed structure:

```text
src/agentic_review_board/domain/execution.py
```

This module owns only review-execution state contracts and transitions; it is not a workflow framework.

### 4.2 Immutable validated state snapshots

Use Pydantic v2 frozen models for `Review`, `StageExecution`, stage-input records, and `ReviewError`.

Lifecycle transitions return new validated snapshots rather than mutating fields in place.

Conceptually:

```text
Review(CREATED)
    ↓ start
Review(RUNNING)
    ↓ start Analyst
Review(RUNNING, Analyst=RUNNING)
    ↓ complete Analyst
Review(RUNNING, Analyst=COMPLETED)
    ...
```

Benefits for this MVP:

- every observable state satisfies the contract at construction time;
- previous snapshots cannot be accidentally mutated;
- trusted upstream artifacts remain stable;
- tests can exercise transition invariants deterministically;
- no assignment-validation or generic state-machine infrastructure is needed.

Do not use unchecked model-copy updates that bypass validation. Transition helpers must construct validated target state.

### 4.3 Closed lifecycle enums

Define:

```text
StageIdentity
- ANALYST
- SOLUTION_ARCHITECT
- RISK_REVIEWER
- CRITIC
- COORDINATOR

StageStatus
- PENDING
- RUNNING
- COMPLETED
- FAILED

ReviewStatus
- CREATED
- RUNNING
- INCOMPLETE
- COMPLETED
```

Do not add `BLOCKED`, `CANCELLED`, `PAUSED`, retry state, or timeout state in Slice 3.

### 4.4 Stage-local typed input provenance

Represent the inputs for the two executable stages explicitly:

```text
AnalystStageInput
- review_input: ReviewInput

SolutionArchitectStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

These records hold trusted immutable domain objects directly. No serialization round-trip, textual ID convention, generic `Artifact`, or persistent reference registry is required.

For Risk Reviewer, Critic, and Coordinator, `inputs` remains absent while the stages remain `PENDING`. Their stage-input contracts must be introduced only when those participants are specified.

### 4.5 Stage output typing

For Slice 3, a trusted stage output can be one of the two already implemented participant results:

```text
ProblemAnalysis
SolutionAlternatives
```

`StageExecution` may therefore use a small explicit union for current trusted stage input/output shapes, together with identity/type consistency validation.

The model must enforce at least:

```text
ANALYST + RUNNING/COMPLETED/FAILED
    → AnalystStageInput

ANALYST + COMPLETED
    → ProblemAnalysis output

SOLUTION_ARCHITECT + RUNNING/COMPLETED/FAILED
    → SolutionArchitectStageInput

SOLUTION_ARCHITECT + COMPLETED
    → SolutionAlternatives output

RISK_REVIEWER / CRITIC / COORDINATOR in Slice 3
    → PENDING only
    → no inputs, output, or error
```

This is intentionally not generalized into a plugin registry or generic stage schema map.

### 4.6 StageExecution invariants and transitions

`StageExecution` enforces the spec's observable state matrix:

```text
PENDING
- inputs: absent
- output: absent
- error: absent

RUNNING
- inputs: present
- output: absent
- error: absent

COMPLETED
- inputs: present
- output: present
- error: absent

FAILED
- inputs: present
- output: absent
- error: present
```

Allowed execution transitions in this slice are:

```text
PENDING → RUNNING
RUNNING → COMPLETED
RUNNING → FAILED
```

No transition returns from a terminal stage state to `RUNNING`.

Small domain transition methods or functions may provide these transitions, but no reusable finite-state-machine framework is introduced.

### 4.7 Review invariants and creation

`Review` contains:

```text
Review
- review_input: ReviewInput
- status: ReviewStatus
- stages: collection[StageExecution]
```

Creation produces:

```text
status = CREATED
five canonical stage identities
all stages = PENDING
```

The `Review` contract validates:

- exactly five stage records;
- each canonical stage identity appears exactly once;
- no unexpected stage identity exists;
- the original `ReviewInput` remains immutable;
- stage state remains internally valid;
- overall `ReviewStatus` is consistent with the stage states and Slice 3 dependency order.

A small domain creation helper or `Review` factory may construct this canonical initial state. Creation is domain state construction, not orchestration of participants.

### 4.8 Review lifecycle and cross-stage coherence

The Review contract must make global lifecycle state truthful rather than trusting the Orchestrator to assemble arbitrary combinations.

For Slice 3, enforce these review-level invariants:

```text
CREATED
- all five stages are PENDING

RUNNING
- no stage is FAILED
- Risk Reviewer, Critic, Coordinator remain PENDING
- Solution Architect may be non-PENDING only if Analyst is COMPLETED
- valid sequential-prefix states are allowed, including:
    all PENDING immediately after review start,
    Analyst RUNNING,
    Analyst COMPLETED + Solution Architect PENDING/RUNNING/COMPLETED

INCOMPLETE
- at least one implemented mandatory stage is FAILED
- if Analyst is FAILED, Solution Architect and all later stages are PENDING
- if Solution Architect is FAILED, Analyst is COMPLETED and all later stages are PENDING

COMPLETED
- requires all five mandatory stages COMPLETED
- therefore no valid Slice 3 Review can reach this state because the three later stages are restricted to PENDING
```

This prevents direct construction of states such as:

```text
ReviewStatus.RUNNING + Analyst FAILED
ReviewStatus.INCOMPLETE + no failed stage
ReviewStatus.COMPLETED + pending later stages
Solution Architect RUNNING before Analyst COMPLETED
```

Slice 3 uses these lifecycle transitions:

```text
CREATED → RUNNING
RUNNING → INCOMPLETE
```

`RUNNING → COMPLETED` remains part of the canonical future lifecycle but is not available through Slice 3 orchestration.

Calling Slice 3 execution on a review that is not `CREATED` is an invalid application/lifecycle invocation. It must fail explicitly rather than being recorded as an ordinary participant failure.

### 4.9 Atomic Review transitions where global invariants span stage + review status

Because `Review` validates cross-stage/global consistency, transitions that alter both a stage terminal state and the overall review status must construct the target state atomically.

In particular, participant failure must not create an intermediate invalid snapshot such as:

```text
ReviewStatus.RUNNING
+ StageStatus.FAILED
```

Instead, the domain transition should produce one validated target snapshot equivalent to:

```text
failed stage → FAILED with ReviewError
review status → INCOMPLETE
```

in the same Review construction.

Successful stage start/completion keeps ReviewStatus `RUNNING` and replaces only the relevant stage snapshot, provided all cross-stage invariants remain satisfied.

No transaction manager or event-sourcing mechanism is required; atomic here means one validated in-memory Review snapshot.

### 4.10 Single logical owner for trusted stage output

Do not add mutable stored fields such as:

```text
Review.problem_analysis
Review.solution_alternatives
```

alongside the same values in `StageExecution.output`.

The corresponding completed stage owns the trusted artifact. If typed review-level convenience access is later useful, it must derive from the stage record and expose the same logical artifact rather than maintain another independently writable value.

The Solution Architect must receive the trusted Analyst result accepted into the current review execution, not a separately regenerated or repaired analysis.

### 4.11 Orchestrator location and dependency direction

Introduce:

```text
src/agentic_review_board/application/orchestrator.py
```

with an application-level `ReviewOrchestrator`.

The constructor receives the already built participants:

```text
ReviewOrchestrator
- analyst: Analyst
- solution_architect: SolutionArchitect
```

The Orchestrator does not construct participants, depend on provider configuration, or receive `LLMPort`.

Dependency direction remains:

```text
ReviewOrchestrator
    ├── domain execution contracts
    ├── Analyst
    └── SolutionArchitect
            ↓
          LLMPort
```

### 4.12 Explicit synchronous orchestration sequence

Implement the sequence directly rather than creating a generic stage loop or registry before later participants exist.

Conceptually:

```text
execute(created_review):
    review → RUNNING

    analyst stage → RUNNING with AnalystStageInput
    invoke Analyst.analyze(review_input)
    on success:
        analyst stage → COMPLETED with ProblemAnalysis
    on participant failure:
        atomically:
            analyst stage → FAILED
            review → INCOMPLETE
        return review

    solution architect stage → RUNNING with SolutionArchitectStageInput
    invoke SolutionArchitect.propose(review_input, problem_analysis)
    on success:
        solution architect stage → COMPLETED with SolutionAlternatives
    on participant failure:
        atomically:
            solution architect stage → FAILED
            review → INCOMPLETE
        return review

    return review still RUNNING
```

Risk Reviewer, Critic, and Coordinator are never invoked in Slice 3.

A generic participant registry, stage handler map, dynamic graph, recursive workflow, or plugin architecture is deferred until actual repetition justifies it.

### 4.13 Participant failure boundary

Catch exceptions only around the actual participant invocation boundary.

Known participant output-validation exceptions:

```text
AnalystOutputError
SolutionArchitectOutputError
```

map to:

```text
ReviewErrorKind.OUTPUT_VALIDATION
```

Any other ordinary `Exception` raised by the invoked participant is classified only as:

```text
ReviewErrorKind.EXECUTION
```

because Slice 3 has no provider-neutral transport exception contract that would justify finer classification.

Use stable concise messages such as:

```text
"Analyst output validation failed"
"Analyst execution failed"
"Solution Architect output validation failed"
"Solution Architect execution failed"
```

Do not copy arbitrary raw exception text into trusted review state.

Orchestrator/domain errors occurring outside the participant call boundary must propagate rather than being mislabeled as participant failures.

### 4.14 Zero-alternative result remains success

The Orchestrator must treat any trusted `SolutionAlternatives` returned by `SolutionArchitect.propose(...)` as a successful stage result, including:

```text
alternatives == ()
```

provided the participant already validated the required generation notes and blocker references.

The Orchestrator does not reinterpret valid Solution Architect semantics.

### 4.15 Review isolation

`ReviewOrchestrator` stores participant dependencies but no previous review state.

Each new `Review` is created independently from its own `ReviewInput`. Executing two reviews through the same Orchestrator instance must not carry stage state, artifacts, errors, or assumptions from one review into another.

This avoids introducing an active-review repository or application singleton before the Review Application/UI slice requires one.

---

## 5. Project Structure

Proposed minimal change:

```text
src/agentic_review_board/
├── application/
│   ├── ports.py                    # existing, unchanged
│   └── orchestrator.py             # new ReviewOrchestrator
├── domain/
│   ├── analysis.py                 # existing, unchanged
│   ├── execution.py                # new review/stage lifecycle contracts
│   ├── review.py                   # existing ReviewInput, unchanged unless import organization requires no semantic change
│   ├── shared.py                   # existing
│   └── solutions.py                # existing, unchanged
└── participants/
    ├── analyst.py                  # existing behavior unchanged
    └── solution_architect.py       # existing behavior unchanged

tests/
└── unit/
    ├── test_review_execution.py    # new domain/lifecycle tests
    └── test_review_orchestrator.py # new orchestration tests
```

No new `framework/`, `workflow/`, `artifacts/`, persistence, infrastructure, integration, or UI package is required.

---

## 6. Dependency Change

None.

The slice reuses:

```text
pydantic>=2.13,<3
```

and the existing development dependencies.

No orchestration library or multi-agent framework is introduced.

---

## 7. Verification Strategy

### 7.1 Review creation and global-consistency tests

Verify:

- canonical enum values are closed and exact;
- new review status is `CREATED`;
- exactly five canonical stages are present;
- every new stage is `PENDING`;
- no new stage has inputs, output, or error;
- original `ReviewInput` is preserved unchanged;
- duplicate/missing canonical stage identities are rejected where the public contract permits direct construction;
- `CREATED` with any non-PENDING stage is rejected;
- `RUNNING` with a failed stage is rejected;
- `INCOMPLETE` without a failed implemented stage is rejected;
- Solution Architect non-PENDING before Analyst completion is rejected;
- `COMPLETED` with any pending stage is rejected;
- in Slice 3, direct valid construction of `COMPLETED` is impossible because later roles cannot leave `PENDING`.

### 7.2 StageExecution invariant tests

Verify all valid state shapes:

- `PENDING` with no inputs/output/error;
- `RUNNING` with typed inputs and no output/error;
- `COMPLETED` with typed inputs + correct trusted output and no error;
- `FAILED` with typed inputs + error and no output.

Reject representative invalid combinations:

- `PENDING` with inputs;
- `RUNNING` without inputs;
- `RUNNING` with output or error;
- `COMPLETED` without output;
- `COMPLETED` with error;
- `FAILED` without error;
- `FAILED` with trusted output;
- Analyst identity with Solution Architect input/output types;
- Solution Architect identity with Analyst-only input/output types;
- later unimplemented stage in a non-`PENDING` state.

Verify trusted models/collections cannot be mutated after validation.

### 7.3 Transition tests

Verify:

```text
Stage:
PENDING → RUNNING
RUNNING → COMPLETED
RUNNING → FAILED

Review:
CREATED → RUNNING
RUNNING + participant failure → INCOMPLETE atomically
```

Reject invalid lifecycle use such as executing a non-`CREATED` review or terminal stage transition back to running.

Verify a failure transition never exposes an intermediate valid Review snapshot with `RUNNING + FAILED stage`.

No Slice 3 transition helper should produce overall `COMPLETED`.

### 7.4 Successful orchestration test

Use the existing `Analyst` and `SolutionArchitect` with a shared deterministic fake `LLMPort` that records role calls.

Verify:

- role invocation order is exactly `analyst`, then `solution_architect`;
- each participant executes exactly once;
- Solution Architect is never invoked before trusted Analyst success;
- the exact current ReviewInput is represented in both stage input records;
- the Solution Architect input record contains the trusted ProblemAnalysis produced by the current Analyst stage;
- Analyst and Solution Architect finish `COMPLETED`;
- Risk Reviewer, Critic, Coordinator remain `PENDING`;
- final Slice 3 review status is `RUNNING`;
- no `FinalReview`, ranking, or preferred alternative exists.

### 7.5 Analyst failure test

Drive Analyst output validation failure and generic execution failure separately.

Verify:

- Analyst was moved through execution and ends `FAILED`;
- Analyst input provenance remains inspectable;
- no trusted Analyst output exists;
- Solution Architect was never invoked and remains `PENDING`;
- all later stages remain `PENDING`;
- review becomes `INCOMPLETE` in the same target Review snapshot as the Analyst failure;
- output-validation failure uses `OUTPUT_VALIDATION`;
- generic invoked-participant failure uses `EXECUTION`;
- stored error message is concise and stable rather than arbitrary exception text.

### 7.6 Solution Architect failure test

After valid Analyst completion, drive Solution Architect output-validation and generic execution failures.

Verify:

- completed Analyst stage and trusted `ProblemAnalysis` remain unchanged and inspectable;
- Solution Architect ends `FAILED` with its input provenance and no trusted output;
- later stages remain `PENDING`;
- review becomes `INCOMPLETE` atomically with the Solution Architect failure;
- error classification follows the same minimal boundary.

### 7.7 Zero-alternative success test

Provide a valid deterministic no-alternative `SolutionAlternatives` response through the existing Solution Architect participant.

Verify:

- Solution Architect remains `COMPLETED`;
- its trusted zero-alternative output is retained;
- review remains `RUNNING` rather than `INCOMPLETE`;
- no artificial alternatives are introduced by orchestration.

### 7.8 Review isolation test

Create and execute two distinct reviews sequentially through the same `ReviewOrchestrator`.

Verify the second review:

- begins `CREATED` with fresh pending stage records;
- preserves only its own ReviewInput;
- contains no previous execution inputs, outputs, or errors;
- receives only the ProblemAnalysis produced for its own current execution.

### 7.9 Internal-error boundary test

Verify lifecycle/application misuse outside participant invocation is raised to the caller rather than converted into `ReviewError` participant failure state.

The test need not invent a broad internal exception framework; one representative invalid execute/precondition path is sufficient to prove the catch boundary is not global.

### 7.10 Regression quality gates

The complete deterministic suite must pass with no network access:

```text
pytest
ruff check .
mypy
pip check
```

Also inspect production source to confirm Slice 3 adds no:

- provider SDK;
- direct Orchestrator → `LLMPort` dependency;
- Risk Reviewer/Critic/Coordinator implementation;
- ranking/final-decision logic;
- persistence/RAG/tools/UI;
- generic workflow/agent framework.

---

## 8. Deliberately Deferred

This plan does not implement or decide:

- Risk Reviewer or `RiskAssessment`;
- Critic or `CriticalReview`;
- Coordinator or `FinalReview`;
- ranking, preferred alternative, final recommendation, or confidence;
- Review Application/UI presentation behavior;
- concrete LLM provider/adapter;
- provider-neutral transport exception taxonomy beyond current evidence;
- retries, backoff, timeout, cancellation, pause/resume, or recovery;
- async/concurrent stage scheduling;
- persistence, history, resumability, database IDs, or cross-review memory;
- timestamps, duration metrics, telemetry, or observability framework;
- generic workflow engine, stage registry, participant plugin system, or multi-agent framework;
- generic artifact repository/reference registry;
- RAG, embeddings, document ingestion, MCP, external tools, or autonomous actions.

---

## 9. ADR Status

ADR-0001 — **Use Pydantic v2 for Structured Contracts and Validation** — remains accepted and applicable to the new structured execution-state contracts.

No new ADR is required for Slice 3:

- no new dependency is introduced;
- execution remains one synchronous local process;
- immutable snapshot transitions are a local domain-modeling choice rather than a new runtime architecture;
- stage-local typed inputs avoid introducing a generic artifact/reference architecture;
- provider, persistence, retry, async, and UI strategies remain unchanged/deferred.

Reconsider an ADR only if a later slice needs live event streaming, concurrent stages, persistence/resume, a generic participant registry, or another runtime pattern that materially changes execution architecture.

---

## 10. Planning Follow-up

Before implementation tasks are generated, `data-model.md` must refine:

- exact Pydantic fields and enum representations;
- exact stage-local input union;
- exact stage-output union;
- `ReviewErrorKind` values and safe messages;
- `StageExecution` structural/identity invariants;
- `Review` five-stage and review-status/stage-coherence invariants;
- validated immutable stage and Review transition operations;
- atomic failure transition construction;
- the exact mechanism for replacing one stage snapshot inside a Review without bypassing validation;
- typing/narrowing needed for the Orchestrator to retrieve the trusted Analyst result safely.

Only after `data-model.md` is reviewed and approved should `tasks.md` be generated and implementation begin.
