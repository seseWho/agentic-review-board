# Tasks: Review Orchestrator v0.1

**Input**: Approved design documents from `specs/003-review-orchestrator/`  
**Prerequisites**: approved `spec.md`, `plan.md`, `data-model.md`, accepted `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`, and merged Slice 1 + Slice 2 contracts on `main`  
**Status**: Approved — ready for implementation

Tests are mandatory because Slice 3 introduces lifecycle state, cross-stage provenance, failure propagation, and dependency ordering that must remain deterministic, inspectable, and provider-neutral.

## Format

Every implementation task follows:

```text
- [ ] Txxx [P?] [US?] Action with exact file path
```

- `[P]` means the task can be executed in parallel because it changes a different file and does not depend on an incomplete task.
- `[US1]`–`[US5]` map directly to the approved user stories in `spec.md`.
- Tests are written before the corresponding production behavior.
- A task is complete only when its tests and the approved Slice 3 semantics are satisfied.

---

## Phase 1: Execution-State Contracts and Canonical Review Creation

**Purpose**: Establish the complete in-memory lifecycle vocabulary and validated aggregate shape before orchestration behavior is introduced.

### Tests first

- [ ] T001 [US2] Create `tests/unit/test_review_execution.py` with contract tests for exact `StageIdentity`, `StageStatus`, `ReviewStatus`, and `ReviewErrorKind` values; closed/frozen `ReviewError`, `AnalystStageInput`, `SolutionArchitectStageInput`, `StageExecution`, and `Review`; immutable stage tuples; strict non-empty `ReviewError.message`; canonical `Review.create(...)`; exactly five unique canonical stage identities; `CREATED` review status; five fresh `PENDING` stages; and absence of inputs/output/error in every newly created stage.
- [ ] T002 [US3] Extend `tests/unit/test_review_execution.py` with the full local `StageExecution` state matrix and identity/type tests: valid `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED` shapes; rejection of output+error coexistence; Analyst accepting only `AnalystStageInput`/`ProblemAnalysis`; Solution Architect accepting only `SolutionArchitectStageInput`/`SolutionAlternatives`; and Risk Reviewer/Critic/Coordinator restricted to `PENDING` with no inputs/output/error in Slice 3.

### Implementation

- [ ] T003 [US2] Create `src/agentic_review_board/domain/execution.py` with the closed lifecycle enums, `ReviewError`, stage-local input contracts, `StageInput`, `StageOutput`, `StageExecution`, canonical stage ordering, and `Review.create(...)`, using Pydantic v2 closed/frozen models and tuple-backed immutable collections exactly as approved in `data-model.md`.
- [ ] T004 [US3] Complete `StageExecution` validation in `src/agentic_review_board/domain/execution.py` so every status/input/output/error combination and stage identity/type combination is fail-closed, including the pending-only restriction for the three unimplemented stages.

**Checkpoint**: `tests/unit/test_review_execution.py` passes for model construction and local stage invariants without invoking any participant or `LLMPort`.

---

## Phase 2: Review-Level Lifecycle, Dependency, and Provenance Invariants

**Goal**: A `Review` cannot represent an impossible global state even when individual stage records are locally valid.

**Independent test**: Construct representative valid/invalid review snapshots directly and verify review-level lifecycle, dependency, and same-review provenance rules without orchestration.

### Tests first

- [ ] T005 [US2] Extend `tests/unit/test_review_execution.py` with review-global lifecycle cases for every valid Slice 3 `RUNNING` prefix, both valid `INCOMPLETE` shapes, rejection of `CREATED` with non-pending stages, rejection of `RUNNING` with a failed stage, rejection of Solution Architect starting before Analyst completion, rejection of `INCOMPLETE` without exactly one failed implemented stage, rejection of both implemented stages failed, and proof that no valid Slice 3 `COMPLETED` review can be constructed while the later three stages are pending-only.
- [ ] T006 [US3] Extend `tests/unit/test_review_execution.py` with cross-stage provenance cases proving that executed Analyst/Solution Architect input records must reference the current Review's exact `ReviewInput` instance, that Solution Architect must reference the exact trusted `ProblemAnalysis` instance owned by the completed Analyst stage, and that equal-but-independent or cross-review artifacts are rejected as execution provenance.

### Implementation

- [ ] T007 [US2] Complete `Review` aggregate validation in `src/agentic_review_board/domain/execution.py` for the exact five-stage set, review-status/stage-state coherence, valid sequential prefixes, valid incomplete-review patterns, later-stage pending-only semantics, and Slice 3 `COMPLETED` impossibility.
- [ ] T008 [US3] Add same-instance provenance validation in `src/agentic_review_board/domain/execution.py` for `ReviewInput` and Analyst→Solution Architect handoff, keeping this identity rule explicitly limited to the current in-memory/no-rehydration Slice 3 model.

**Checkpoint**: The execution domain independently rejects every representative globally inconsistent or cross-review state described in `data-model.md`.

---

## Phase 3: Validated Immutable Review Transitions

**Goal**: Legal state changes produce new fully validated snapshots and no transition can expose a temporarily invalid aggregate.

**Independent test**: Drive a Review through the approved domain transitions without invoking participants and verify exact preconditions, target snapshots, preserved upstream objects, and atomic failure semantics.

### Tests first

- [ ] T009 [US2] Extend `tests/unit/test_review_execution.py` with transition tests for `start`, `start_analyst`, `complete_analyst`, `start_solution_architect`, and `complete_solution_architect`; assert original `ReviewInput` preservation, exact trusted-object reuse, unchanged unaffected stages, canonical stage order preservation, and explicit rejection of illegal/repeated/terminal transition attempts.
- [ ] T010 [US4] Extend `tests/unit/test_review_execution.py` with `fail_analyst` and `fail_solution_architect` transition tests proving one-step construction of valid `INCOMPLETE + FAILED` snapshots, preservation of recorded inputs, absence of trusted output on the failed stage, preservation of earlier completed Analyst output when Solution Architect fails, and no valid intermediate `RUNNING + FAILED` Review snapshot.

### Implementation

- [ ] T011 [US2] Implement the explicit immutable Review transition operations in `src/agentic_review_board/domain/execution.py`, rebuilding complete validated target `Review` snapshots rather than mutating models or using unchecked `model_copy(update=...)`; include identity-based `Review.stage(...)` lookup and explicit precondition failures.
- [ ] T012 [US4] Complete atomic failure transitions in `src/agentic_review_board/domain/execution.py` so failed stage state and overall `INCOMPLETE` status are constructed together, dependent stages remain `PENDING`, and prior completed artifacts remain inspectable.

**Checkpoint**: All domain lifecycle transitions are deterministic, immutable, fully validated, and require no orchestration framework.

---

## Phase 4: User Story 1 — Execute Analyst then Solution Architect

**Goal**: One orchestrated review executes the two implemented participants in dependency order and propagates the exact trusted Analyst artifact into Solution Architect.

**Independent test**: Use the existing Analyst and Solution Architect with one deterministic recording `LLMPort` fake and verify exact invocation order and trusted artifact propagation.

### Tests first

- [ ] T013 [US1] Create `tests/unit/test_review_orchestrator.py` with a successful deterministic orchestration scenario using the existing participants and a shared recording fake `LLMPort`; assert review `CREATED → RUNNING`, exact role call order `analyst` then `solution_architect`, each participant invoked once, stage inputs recorded before the corresponding invocation, exact same-instance `ReviewInput` and `ProblemAnalysis` provenance, both implemented stages `COMPLETED`, later three stages `PENDING`, final Slice 3 review status still `RUNNING`, and absence of ranking/final-review behavior.
- [ ] T014 [US1] Extend `tests/unit/test_review_orchestrator.py` with a valid zero-alternative `SolutionAlternatives` scenario proving it completes Solution Architect successfully and leaves the review `RUNNING` rather than `INCOMPLETE`.

### Implementation

- [ ] T015 [US1] Create `src/agentic_review_board/application/orchestrator.py` with `ReviewOrchestrator(analyst, solution_architect)` and an explicit synchronous `execute(created_review)` sequence: start Review, start Analyst, invoke `Analyst.analyze`, complete Analyst, start Solution Architect using the trusted Analyst output from the current Review, invoke `SolutionArchitect.propose`, complete Solution Architect, and return the still-`RUNNING` Review; do not introduce a generic stage loop/registry and do not depend on `LLMPort` directly.

**Checkpoint**: Happy-path Slice 3 orchestration succeeds with a deterministic fake, no network access, no provider SDK, and no later participant behavior.

---

## Phase 5: User Story 4 — Fail Closed and Preserve Earlier Work

**Goal**: Participant failure becomes a visible incomplete review, dependent execution stops, and existing trusted work is preserved.

**Independent test**: Deterministically drive known output-validation and generic execution failures at both implemented participant boundaries.

### Tests first

- [ ] T016 [US4] Extend `tests/unit/test_review_orchestrator.py` with Analyst failure cases for `AnalystOutputError` and an unrelated ordinary participant-call exception; assert Analyst `FAILED`, preserved Analyst input provenance, no trusted Analyst output, Solution Architect never invoked and remains `PENDING`, later stages remain `PENDING`, overall `INCOMPLETE`, `OUTPUT_VALIDATION` versus `EXECUTION` classification, and stable safe error text without copied raw exception details.
- [ ] T017 [US4] Extend `tests/unit/test_review_orchestrator.py` with Solution Architect failure cases for `SolutionArchitectOutputError` and an unrelated ordinary participant-call exception; assert completed Analyst state/output remain unchanged and inspectable, Solution Architect `FAILED` with preserved inputs and no trusted output, later stages remain `PENDING`, overall `INCOMPLETE`, and correct safe error classification/message.
- [ ] T018 [US4] Extend `tests/unit/test_review_orchestrator.py` with an application/lifecycle misuse case proving an error raised outside the actual participant invocation boundary is propagated to the caller and is not converted into a participant `ReviewError`; also prove `KeyboardInterrupt`/`SystemExit`-class control-flow signals are not intentionally swallowed by ordinary `Exception` handling.

### Implementation

- [ ] T019 [US4] Complete the participant failure boundaries in `src/agentic_review_board/application/orchestrator.py`: catch `AnalystOutputError`/`SolutionArchitectOutputError` only around their respective participant calls as `OUTPUT_VALIDATION`; map other ordinary participant-call `Exception` values to `EXECUTION`; use the four approved stable safe messages; invoke the corresponding atomic domain failure transition; return immediately after mandatory failure; and leave all domain/orchestrator errors outside those call boundaries unsuppressed.

**Checkpoint**: Every representative participant failure fails closed, preserves valid upstream evidence, stops dependent execution, and stores no raw exception diagnostics in trusted review state.

---

## Phase 6: User Story 5 — Review Isolation

**Goal**: Reusing one Orchestrator instance never reuses Review state.

**Independent test**: Execute two distinct reviews sequentially through the same `ReviewOrchestrator` instance and inspect the second review before and after execution.

### Tests first

- [ ] T020 [US5] Extend `tests/unit/test_review_orchestrator.py` with sequential success→success and incomplete→fresh-review cases proving every `Review.create(...)` starts `CREATED` with five fresh `PENDING` stage records, the second review inherits no prior inputs/outputs/errors/status, each review preserves its own original `ReviewInput` instance, and Solution Architect receives only the Analyst artifact produced in its own current review.

### Implementation/confirmation

- [ ] T021 [US5] Confirm `src/agentic_review_board/application/orchestrator.py` stores only participant dependencies and no mutable/current/previous Review state; make only the minimum production change required if T020 exposes state leakage, without introducing an active-review repository or singleton.

**Checkpoint**: Sequential reviews are isolated while sharing the same participant/orchestrator objects.

---

## Phase 7: Cross-Cutting Verification

**Purpose**: Prove Slice 3 satisfies its approved scope and did not introduce accidental architecture expansion.

- [ ] T022 Run the complete deterministic `pytest` suite with no live LLM/network dependency and confirm all Slice 1, Slice 2, and new Slice 3 tests pass.
- [ ] T023 Run `ruff check .` and resolve all violations introduced by Slice 3 without weakening repository rules.
- [ ] T024 Run `mypy` under the repository strict configuration and resolve all Slice 3 typing errors, especially `StageInput`/`StageOutput` narrowing and Review stage lookup, without adding a new plugin/dependency unless separately justified and approved.
- [ ] T025 Run `pip check`, then inspect `pyproject.toml` and `src/agentic_review_board/` to confirm Slice 3 adds no production dependency, concrete provider SDK, direct Orchestrator→`LLMPort` dependency, Risk Reviewer/Critic/Coordinator implementation, ranking/final-decision logic, persistence, RAG, UI, tools, retries/timeouts, generic workflow engine, stage registry, or artifact repository.
- [ ] T026 Review the final implementation against `specs/003-review-orchestrator/spec.md`, `plan.md`, `data-model.md`, `docs/02-requirements.md`, `docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`, the Constitution, and ADR-0001; confirm the exact successful end state remains `RUNNING + Analyst COMPLETED + Solution Architect COMPLETED + three later PENDING`, known participant failures are distinguishable from generic execution failures, and no unsupported claim of complete review is introduced.

**Final checkpoint**: T001–T026 complete, full deterministic suite green, Ruff/mypy/pip checks green, architectural scope confirmed, and Slice 3 remains limited to Review Orchestrator v0.1.

---

## Dependencies

### Completion order

```text
Execution contracts + creation (T001–T004)
        ↓
Review global invariants + provenance (T005–T008)
        ↓
Validated transitions (T009–T012)
        ↓
US1 happy-path orchestration (T013–T015)
        ↓
US4 failure handling (T016–T019)
        ↓
US5 isolation (T020–T021)
        ↓
Cross-cutting verification (T022–T026)
```

US2 and US3 are established primarily through the execution-domain phases because lifecycle truth and traceability are prerequisites for safe orchestration. US1 then exercises those contracts through real participant sequencing; US4 hardens failure behavior; US5 proves review isolation.

### Task dependencies

- T001–T002 are sequential because both establish `tests/unit/test_review_execution.py` and T002 extends T001.
- T003 follows T001–T002 so the full local contract tests exist before production execution-state code; T004 follows T003 and completes local `StageExecution` behavior against those tests.
- T005–T006 are sequential because both extend `test_review_execution.py`.
- T007 follows T005; T008 follows T006/T007 so aggregate provenance is applied on top of the globally valid Review shape.
- T009–T010 are sequential in `test_review_execution.py`.
- T011 follows T009 and the approved aggregate invariants; T012 follows T010/T011.
- T013–T014 are sequential in `test_review_orchestrator.py`.
- T015 follows T013–T014 and all domain phases.
- T016–T018 are sequential because all extend `test_review_orchestrator.py`.
- T019 follows T016–T018.
- T020 follows the successful and failure orchestration behavior; T021 follows T020.
- T022–T026 run only after all implementation/story tasks are complete.

No implementation task should be started before its corresponding tests exist and fail for the expected missing behavior.

---

## Parallel Execution Guidance

This Slice is intentionally mostly sequential because both domain tests and orchestration tests concentrate in one file each and the workflow itself is dependency-ordered.

Useful parallelism is limited to work that touches different files and has complete prerequisites. For example, after the execution-domain contract is stable, documentation/scope inspection can occur independently, but production implementation should preserve the test-first order above.

Do not mark tasks that modify the same file as parallel merely because their conceptual concerns differ.

---

## Implementation Strategy

Implement in small verified increments:

1. **State contracts first** — enums, `ReviewError`, typed stage inputs, `StageExecution`, canonical `Review` creation.
2. **Global truth next** — review lifecycle, dependency-order, and same-review provenance invariants.
3. **Transitions** — immutable validated snapshots and atomic failure state changes.
4. **Happy path** — explicit Analyst → Solution Architect orchestration with exact trusted artifact handoff.
5. **Failure path** — safe error classification, fail-closed stop, preserved upstream evidence.
6. **Isolation** — prove sequential reviews do not leak state.
7. **Verification** — full tests, Ruff, mypy, dependency and architecture scope review.

Do not implement Risk Reviewer, Critic, Coordinator, FinalReview, ranking, recommendation, real LLM adapter, retries, timeout/cancellation, persistence, RAG, tools, UI, generic workflow/stage registry, artifact repository, or distributed/async execution as part of this task set.
