# Tasks: Review Input + Analyst v0.1

**Input**: Design documents from `specs/001-review-input-analyst/`  
**Prerequisites**: reviewed `spec.md`, `plan.md`, `research.md`, `data-model.md`, and accepted `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`  
**Status**: Approved — implementation in progress

Tests are mandatory for this feature because the specification, canonical Quality & Security baseline, and Constitution require deterministic verification of new domain/application behavior.

## Format

Every implementation task follows:

```text
- [ ] Txxx [P?] [US?] Action with exact file path
```

- `[P]` means the task can be executed in parallel because it changes a different file and does not depend on an incomplete task.
- `[US1]`, `[US2]`, and `[US3]` map directly to the user stories in `spec.md`.
- Existing code on this branch is provisional. A task is complete only when the current approved specification, plan, data model, research, and ADR are satisfied; previous implementation does not make a task pre-completed.

---

## Phase 1: Setup

**Purpose**: Apply the one approved production dependency before feature code is reconciled.

- [X] T001 Update `[project].dependencies` in `pyproject.toml` to include `pydantic>=2.13,<3` and add no other production dependency.

**Checkpoint**: The project dependency declaration matches ADR-0001 and the approved plan.

---

## Phase 2: User Story 2 — Reject Invalid Review Input

**Goal**: A review accepts the required non-empty description plus optional context, preserves supplied values, and rejects invalid input before Analyst execution.

**Independent test**: Construct `ReviewInput` directly with valid and invalid inputs; no LLM substitute is required.

### Tests first

- [X] T002 [US2] Replace the provisional tests in `tests/unit/test_review_input.py` with Pydantic-focused cases covering minimal valid input, all optional fields absent, blank/whitespace-only description rejection, exact preservation of valid supplied text, frozen-model reassignment rejection, and deterministic rejection of unexpected fields.

### Implementation

- [X] T003 [US2] Replace the provisional dataclass in `src/agentic_review_board/domain/review.py` with the approved Pydantic v2 `ReviewInput`, preserving the conceptual fields from `data-model.md`, rejecting only invalid required description content, preserving valid text unchanged, using closed input fields, and preventing reassignment after validation.

**Checkpoint**: `tests/unit/test_review_input.py` passes independently and demonstrates FR-001 through FR-003 without invoking Analyst or a model provider.

---

## Phase 3: User Story 1 — Structure a Review Problem

**Goal**: A valid `ReviewInput` and deterministic model result produce a trusted `ProblemAnalysis` with the six required semantic categories and valid structural provenance.

**Independent test**: A deterministic LLM substitute returns one valid Analyst result; `Analyst.analyze(...)` returns a validated `ProblemAnalysis` with facts and assumptions distinct and with no later-stage semantics.

### Tests first

- [X] T004 [P] [US1] Create `tests/unit/test_problem_analysis.py` with happy-path contract tests for `AnalysisFinding`, `FactFinding`, optional review-local identifiers, the closed `ReviewInputSource` vocabulary, all six required `ProblemAnalysis` categories, and facts remaining structurally distinct from assumptions.
- [X] T005 [P] [US1] Rewrite the happy-path portion of `tests/unit/test_analyst.py` to use a deterministic provider-neutral substitute, assert one Analyst invocation, verify propagation of the current `ReviewInput`, verify applicable fact provenance, and assert the returned value is a trusted `ProblemAnalysis` containing no solution alternatives, ranking, architecture recommendation, or final recommendation fields.

### Implementation

- [X] T006 [US1] Replace the provisional dataclasses in `src/agentic_review_board/domain/analysis.py` with Pydantic v2 `AnalysisFinding`, `FactFinding`, `ReviewInputSource`, and `ProblemAnalysis` contracts aligned with `data-model.md`, including optional local identifiers, non-empty semantic text, closed generated-output models, and immutable trusted output where appropriate.
- [X] T007 [US1] Reconcile `src/agentic_review_board/application/ports.py` into the smallest provider-neutral `LLMPort` Protocol required by the Analyst use case, keeping concrete provider SDK types, authentication, transport envelopes, and provider-specific structured-output mechanics outside the port.
- [X] T008 [US1] Refactor `src/agentic_review_board/participants/analyst.py` so `Analyst` invokes `LLMPort`, treats the returned representation as untrusted, constructs `ProblemAnalysis` through local Pydantic validation, verifies that each fact's `source_ref` is applicable to the actual current `ReviewInput`, and returns only the trusted Analyst contract.

**Checkpoint**: The US1 happy path passes with no network access or concrete LLM SDK, and the Analyst remains within the role boundaries defined by `docs/04-agent-model.md`.

---

## Phase 4: User Story 3 — Fail Closed on Invalid Analyst Output

**Goal**: Malformed or context-invalid generated Analyst content fails explicitly before it can become trusted `ProblemAnalysis` data.

**Independent test**: Deterministic invalid generated results are rejected for each representative structural/contextual failure while valid output continues to pass.

### Tests first

- [X] T009 [P] [US3] Extend `tests/unit/test_problem_analysis.py` with structural failure cases for missing mandatory fields, unexpected top-level/nested fields, wrong primitive types for strict semantic text, invalid `ReviewInputSource`, malformed nested findings, empty required finding text, and duplicate non-null review-local identifiers while allowing absent identifiers.
- [X] T010 [P] [US3] Extend `tests/unit/test_analyst.py` with contextual/error-boundary cases proving that a fact cannot reference an absent/not-applicable `ReviewInput` field, Pydantic contract failures are normalized as Analyst-output validation failures, invalid generated data is not repaired or returned, and provider-specific exceptions are not misreported as schema-validation errors.

### Implementation

- [ ] T011 [US3] Complete fail-closed contract invariants in `src/agentic_review_board/domain/analysis.py`, using Pydantic for structural validation and duplicate detection only for identifiers that are actually present; do not make local identifiers mandatory.
- [ ] T012 [US3] Complete the validation/error boundary in `src/agentic_review_board/participants/analyst.py` so Pydantic validation failures and Analyst contextual provenance failures produce the explicit Analyst-output validation error category without swallowing unrelated provider/transport failures or manufacturing replacement values.

**Checkpoint**: Every representative invalid result in US3 fails before trusted state, while the valid US1 result still succeeds.

---

## Phase 5: Cross-Cutting Verification

**Purpose**: Prove the increment satisfies the approved design and has not expanded scope.

- [ ] T013 Run the deterministic feature and package test suite in `tests/` with no live LLM or network dependency and confirm all tests pass.
- [ ] T014 Run Ruff against `src/` and `tests/` using the configuration in `pyproject.toml` and resolve all violations introduced by this increment.
- [ ] T015 Run mypy strict checks against `src/` and `tests/` using `pyproject.toml` and resolve all type errors introduced by this increment without adding the Pydantic mypy plugin.
- [ ] T016 Run `pip check` for the environment built from `pyproject.toml`, then inspect `pyproject.toml` and `src/agentic_review_board/` to confirm the increment introduced no concrete LLM SDK, UI framework, persistence, RAG/document ingestion, external tools, orchestration framework, downstream participant, or additional production dependency beyond Pydantic.

**Final checkpoint**: T001–T016 are complete, pytest/Ruff/mypy/pip-check are green, and implementation matches `spec.md`, `plan.md`, `data-model.md`, `research.md`, ADR-0001, and the canonical project documents.

---

## Dependencies

### Story completion order

```text
T001 Setup
   ↓
US2 ReviewInput (T002–T003)
   ↓
US1 Analyst happy path (T004–T008)
   ↓
US3 Fail-closed output (T009–T012)
   ↓
Cross-cutting verification (T013–T016)
```

All three stories are P1 in `spec.md`. US2 is implemented first because `ReviewInput` is a concrete dependency of the Analyst path, not because its product priority is higher than US1.

### Task dependencies

- T001 blocks feature implementation because the approved contracts use Pydantic v2.
- T002 must be written before T003; T003 must pass before Analyst tasks rely on `ReviewInput`.
- T004 and T005 may be written in parallel after T003 because they target different test files.
- T006 and T007 may begin after their corresponding tests exist, but T008 depends on T006 and T007.
- T009 and T010 may be written in parallel after the US1 happy path exists.
- T011 follows T009; T012 follows T010 and depends on the contracts finalized by T011 where applicable.
- T013–T016 run only after all story implementation tasks are complete.

---

## Parallel Execution Examples

### User Story 1

After US2 is green:

```text
Parallel test preparation:
- T004 → tests/unit/test_problem_analysis.py
- T005 → tests/unit/test_analyst.py

Then implementation:
- T006 → domain/analysis.py
- T007 → application/ports.py
- T008 → participants/analyst.py (after T006 + T007)
```

### User Story 3

After US1 is green:

```text
Parallel failure-test preparation:
- T009 → tests/unit/test_problem_analysis.py
- T010 → tests/unit/test_analyst.py

Then implementation:
- T011 → domain/analysis.py
- T012 → participants/analyst.py
```

---

## Implementation Strategy

Implement one verified slice at a time:

1. **Setup** — adopt only the approved Pydantic dependency.
2. **US2** — establish trusted immutable `ReviewInput` first.
3. **US1** — establish the valid Analyst path through the provider-neutral boundary.
4. **US3** — harden the same path with fail-closed structural and contextual validation.
5. **Verification** — run complete deterministic and static-quality gates and perform the architecture/scope check.

Do not implement the Review Orchestrator, stage lifecycle, UI, real LLM adapter, prompts/versioning, retry/timeout policy, persistence, RAG, tools, downstream participants, or an agent framework as part of this task set.
