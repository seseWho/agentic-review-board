# Tasks: Solution Architect v0.1

**Input**: Approved design documents from `specs/002-solution-architect/`  
**Prerequisites**: approved `spec.md`, `plan.md`, `data-model.md`, accepted `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`, and merged Slice 1 contracts on `main`  
**Status**: Approved — implementation in progress

Tests are mandatory because the specification, Quality & Security baseline, Constitution, and ADR require deterministic verification of generated-contract validation, contextual traceability, role integrity, and fail-closed behavior.

## Format

Every implementation task follows:

```text
- [ ] Txxx [P?] [US?] Action with exact file path
```

- `[P]` means the task can be executed in parallel because it changes a different file and does not depend on an incomplete task.
- `[US1]`, `[US2]`, and `[US3]` map directly to the approved user stories in `spec.md`.
- A task is complete only when its tests and the approved feature semantics are satisfied; existing/provisional code does not make a task pre-completed.

---

## Phase 1: Shared Solution Contracts

**Purpose**: Establish the shared qualitative enum and the complete structural Solution Architect output contract before participant behavior is implemented.

### Tests first

- [X] T001 [P] [US1] Create `tests/unit/test_solution_alternatives.py` with happy-path structural tests for `QualitativeLevel`, `ConstraintSource`, `ConstraintReferenceKind`, `ConstraintReference`, `FindingReference`, `GenerationNotes`, `SolutionAlternative`, and `SolutionAlternatives`, including exact `LOW`/`MEDIUM`/`HIGH` acceptance, allowed constraint source/kind combinations, required strict non-empty semantic text, optional review-local finding IDs, 2- and 3-alternative valid cardinalities, optional generation notes when alternatives exist, unique alternative IDs, closed generated-output schemas, tuple-backed immutable collections, and post-validation immutability.

### Implementation

- [X] T002 [US1] Create `src/agentic_review_board/domain/shared.py` with the closed `QualitativeLevel` enum containing only `LOW`, `MEDIUM`, and `HIGH`, without quantitative semantics or provider-specific behavior.
- [X] T003 [US1] Create `src/agentic_review_board/domain/solutions.py` implementing Pydantic v2 `ConstraintSource`, `ConstraintReferenceKind`, `ConstraintReference`, `FindingReference`, `GenerationNotes`, `SolutionAlternative`, and `SolutionAlternatives` exactly as approved in `data-model.md`, including closed/frozen generated contracts, strict non-empty semantic text, immutable validated collections, `REVIEW_INPUT + ID` rejection, alternative cardinality `0 | 2 | 3`, required `GenerationNotes` when alternatives are empty, and unique alternative IDs.

**Checkpoint**: `tests/unit/test_solution_alternatives.py` passes independently for all normal structural contract behavior without invoking `LLMPort`.

---

## Phase 2: User Story 1 — Generate Meaningful Solution Alternatives

**Goal**: A valid `ReviewInput`, trusted `ProblemAnalysis`, and deterministic valid Solution Architect result produce trusted `SolutionAlternatives` containing two or three structured candidate approaches.

**Independent test**: A deterministic provider-neutral model substitute returns two materially different structured alternatives; `SolutionArchitect.propose(...)` returns trusted `SolutionAlternatives` and consumes both required upstream artifacts.

### Tests first

- [X] T004 [US1] Create the happy-path portion of `tests/unit/test_solution_architect.py` using a deterministic `LLMPort` fake to assert exactly one Solution Architect invocation, explicit propagation of both `ReviewInput` and trusted `ProblemAnalysis`, absence of later-stage artifacts from the payload, acceptance of a valid two-alternative result, acceptance of a valid three-alternative result, preservation of upstream input objects, and no ranking/preferred/final-recommendation fields in trusted output.
- [X] T005 [US1] Extend `tests/unit/test_solution_architect.py` with contextual constraint-reference success cases proving that `REVIEW_INPUT + TEXT` resolves against original `ReviewInput.constraints` even when the Analyst omitted that constraint, identical duplicate `ReviewInput.constraints` text still resolves as one textual target, `PROBLEM_ANALYSIS + ID` resolves by a supplied finding ID, and `PROBLEM_ANALYSIS + TEXT` resolves by exact finding text when unambiguous.

### Implementation

- [X] T006 [US1] Create `src/agentic_review_board/participants/solution_architect.py` with `SolutionArchitect` and a dedicated Solution Architect output-validation error category; invoke the existing unchanged `LLMPort`, send only provider-neutral `review_input` and `problem_analysis` payload sections, treat the generated mapping as untrusted, construct `SolutionAlternatives` through local Pydantic validation, perform contextual constraint-reference validation against the current trusted upstream artifacts, and return only trusted `SolutionAlternatives`.

**Checkpoint**: US1 succeeds deterministically with no network access, no concrete provider SDK, no orchestration layer, and no downstream participant implementation.

---

## Phase 3: User Story 2 — Preserve an Honest No-Alternative Result

**Goal**: When two or three meaningful alternatives cannot responsibly be formed, the Solution Architect returns a valid zero-alternative `SolutionAlternatives` result with structured generation notes and explicit upstream blockers rather than fabricated variants.

**Independent test**: A deterministic underspecified scenario returns `alternatives=[]` plus `GenerationNotes` whose blocker references resolve to the current `ProblemAnalysis.missing_information` and/or `.uncertainties`.

### Tests first

- [ ] T007 [P] [US2] Extend `tests/unit/test_solution_alternatives.py` with zero-alternative structural cases proving that `alternatives=[]` requires `GenerationNotes`, `GenerationNotes.explanation` must be non-empty, blocker collections are explicit immutable `FindingReference` collections, and no separate `NoAlternativeOutcome` contract exists.
- [ ] T008 [P] [US2] Extend `tests/unit/test_solution_architect.py` with a deterministic no-alternative scenario proving that valid blocker references resolve against `ProblemAnalysis.missing_information` and `ProblemAnalysis.uncertainties`, that ID+text references must identify the same finding, that text-only references work when unique, and that the trusted result contains no fabricated alternatives; also prove that whenever `GenerationNotes` is present alongside a valid two- or three-alternative result, its blocker references are still contextually validated rather than bypassed.

### Implementation

- [ ] T009 [US2] Complete `GenerationNotes` contextual validation in `src/agentic_review_board/participants/solution_architect.py` so whenever `generation_notes` is present every `blocking_missing_information` reference resolves only against current `ProblemAnalysis.missing_information` and every `blocking_uncertainties` reference resolves only against current `ProblemAnalysis.uncertainties`; ID+text references must match the same finding, text-only references must be unambiguous, and no unresolved blocker can enter trusted output. Preserve the separate structural rule that `GenerationNotes` is mandatory when `alternatives=[]` but optional when two or three alternatives exist.

**Checkpoint**: The underspecified deterministic scenario produces a valid, inspectable zero-alternative `SolutionAlternatives` result with structured blockers and without invented variants, while any `GenerationNotes` supplied on a normal alternatives result receives the same contextual reference validation.

---

## Phase 4: User Story 3 — Fail Closed on Invalid Solution Architect Output

**Goal**: Structurally invalid, context-invalid, ambiguous, or role-leaking generated Solution Architect content fails explicitly before trusted `SolutionAlternatives` is returned.

**Independent test**: Deterministic malformed/generated fixtures trigger the expected output-validation failure category while provider/transport failures remain distinguishable.

### Tests first

- [ ] T010 [P] [US3] Extend `tests/unit/test_solution_alternatives.py` with structural failure cases for missing mandatory nested fields, unexpected top-level/nested fields, unsupported qualitative complexity, strict-text type violations, blank required text, invalid `REVIEW_INPUT + ID`, one alternative, more than three alternatives, duplicate alternative IDs, zero alternatives without generation notes, blank generation explanation, malformed `FindingReference`, and explicit structured ranking/preferred/final-recommendation role leakage.
- [ ] T011 [US3] Extend `tests/unit/test_solution_architect.py` with contextual failure cases for unresolved `REVIEW_INPUT + TEXT`, unresolved `PROBLEM_ANALYSIS + ID`, unresolved `PROBLEM_ANALYSIS + TEXT`, ambiguous repeated Analyst constraint text referenced through `TEXT`, unresolved blocker references whether generation notes accompany zero or multiple alternatives, ambiguous text-only blockers, mismatched blocker ID+text pairs, and confirmation that no fuzzy/trimmed/lowercased reference matching is performed.
- [ ] T012 [US3] Extend `tests/unit/test_solution_architect.py` with error-boundary cases proving Pydantic contract failures and contextual reference failures are normalized into the dedicated Solution Architect output-validation category, invalid generated data is never repaired/returned, and provider/transport exceptions from the fake `LLMPort` are not swallowed or mislabeled as schema failures.

### Implementation

- [ ] T013 [US3] Complete fail-closed structural invariants in `src/agentic_review_board/domain/solutions.py`, keeping Pydantic responsibility limited to candidate-output-only rules and avoiding semantic heuristics for alternative distinctness, objective compatibility, blocker completeness, or prose-based ranking detection.
- [ ] T014 [US3] Complete the contextual validation/error boundary in `src/agentic_review_board/participants/solution_architect.py`, rejecting unresolved/ambiguous typed constraint references and blocker references before return, normalizing generated structural/contextual failures consistently, and allowing unrelated provider/transport failures to propagate distinctly.

**Checkpoint**: Every representative invalid generated result fails before trusted state while the valid US1 and US2 paths remain green.

---

## Phase 5: Cross-Cutting Verification

**Purpose**: Prove the increment satisfies its approved scope and has not introduced accidental architecture or role expansion.

- [ ] T015 Run the complete deterministic test suite in `tests/` with no live LLM/network dependency and confirm all Slice 1 regression tests plus the new Solution Architect tests pass.
- [ ] T016 Run Ruff using the repository configuration and resolve all violations introduced by Slice 2 without weakening rules.
- [ ] T017 Run mypy strict checks using the repository configuration and resolve all type errors introduced by Slice 2 without adding the Pydantic mypy plugin unless separately justified and approved.
- [ ] T018 Run `pip check`, then inspect `pyproject.toml` and `src/agentic_review_board/` to confirm Slice 2 adds no production dependency, concrete LLM SDK, Orchestrator, Risk Reviewer, Critic, Coordinator, ranking/final-decision logic, persistence, RAG, UI, tools, semantic-similarity engine, generic reference framework, or new external capability.
- [ ] T019 Review the final implementation against `specs/002-solution-architect/spec.md`, `plan.md`, `data-model.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`, the Constitution, and ADR-0001; confirm semantic-quality properties that cannot be proven structurally remain explicitly outside the contract-validation claim.

**Final checkpoint**: T001–T019 complete, deterministic suite green, static checks green, dependency check green, and Slice 2 remains limited to Solution Architect v0.1.

---

## Dependencies

### Story completion order

```text
Shared contracts (T001–T003)
        ↓
US1 Alternatives happy path (T004–T006)
        ↓
US2 No-alternative path (T007–T009)
        ↓
US3 Fail-closed hardening (T010–T014)
        ↓
Cross-cutting verification (T015–T019)
```

All three stories are P1. The order follows implementation dependency rather than story priority: US1 establishes the normal participant path, US2 extends the same contract/path with the explicit limitation outcome, and US3 hardens both paths.

### Task dependencies

- T001 must exist before T002/T003 implementation is complete because the tests define the approved domain contract behavior.
- T002 and T003 are sequential implementation work even though `shared.py` and `solutions.py` are separate files; `solutions.py` depends on `QualitativeLevel`.
- T004 and T005 are sequential because both modify `tests/unit/test_solution_architect.py`.
- T006 depends on T003 and on the happy-path/context tests T004–T005 being present.
- T007 and T008 may be prepared in parallel after US1 is green because they modify different test files.
- T009 follows T008 and applies GenerationNotes contextual validation whenever generation notes are present, independently of alternative cardinality.
- T010 may be prepared in parallel with the `test_solution_architect.py` US3 work because it modifies `tests/unit/test_solution_alternatives.py`.
- T011 and T012 are sequential because both modify `tests/unit/test_solution_architect.py`.
- T013 follows T010; T014 follows T011–T012 and depends on the contract behavior finalized by T013 where applicable.
- T015–T019 run only after all story implementation tasks are complete.

---

## Parallel Execution Examples

### US1

```text
Sequential test preparation:
- T004 → tests/unit/test_solution_architect.py happy path
- T005 → tests/unit/test_solution_architect.py reference-resolution cases

Then:
- T006 → participants/solution_architect.py
```

### US2

```text
Parallel test preparation:
- T007 → tests/unit/test_solution_alternatives.py
- T008 → tests/unit/test_solution_architect.py

Then:
- T009 → participants/solution_architect.py
```

### US3

```text
Parallel workstreams:
- T010 → tests/unit/test_solution_alternatives.py
- T011 → tests/unit/test_solution_architect.py contextual failures

Then, sequentially in test_solution_architect.py:
- T012 → error-boundary cases

Then:
- T013 → domain/solutions.py
- T014 → participants/solution_architect.py
```

Tasks sharing one file are deliberately not marked `[P]`.

---

## Implementation Strategy

Implement in small verified increments:

1. **Contracts first** — define strict immutable domain contracts and structural invariants.
2. **US1** — implement direct Solution Architect consumption of ReviewInput + ProblemAnalysis and normal 2–3 alternative output.
3. **US2** — add the structured zero-alternative limitation path and blocker traceability, validating `GenerationNotes` references whenever notes are present.
4. **US3** — add fail-closed structural/contextual validation and explicit error separation.
5. **Verification** — run complete deterministic/static/dependency/scope checks.

Do not implement the Review Orchestrator, lifecycle/status, Risk Reviewer, Critic, Coordinator, ranking, final recommendation, real provider adapter, prompt/versioning system, retry/timeout policy, persistence, RAG, tools, UI, semantic judge, embeddings, or generic multi-agent/reference framework as part of this task set.
