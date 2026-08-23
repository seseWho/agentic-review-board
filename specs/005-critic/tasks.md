# Tasks: Critic v0.1

**Input**: Approved design documents from `specs/005-critic/`  
**Prerequisites**: approved `spec.md`, approved `plan.md`, approved `data-model.md`, accepted `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`, and merged Slice 1–4 contracts on `main`  
**Branch**: `005-critic`  
**Status**: Approved — implementation may proceed tests-first in reviewed blocks

Tests are mandatory because Slice 5 introduces a generated critical-review contract, Critic-specific cross-artifact references, contextual resolution across four current-review artifacts, a fourth execution-stage provenance boundary, and a mandatory participant failure boundary. All behavior must remain deterministic, inspectable, provider-neutral, and fail-closed.

## Format

Every implementation task follows:

```text
- [ ] Txxx [P?] [US?] Action with exact file path
```

- `[P]` means the task can be executed in parallel because it changes a different file and all prerequisites are complete.
- `[US1]`–`[US6]` map directly to the approved user stories in `spec.md`.
- Tests are written before the corresponding production behavior.
- A task is complete only when its tests and the approved Slice 5 contracts are satisfied.
- Do not start a later phase merely because an earlier production file compiles; complete the phase checkpoint first.

---

## Phase 1: Critic Domain Contracts

**Purpose**: Establish the intrinsic immutable Critic output contracts and bounded reference shapes before introducing LLM behavior or current-review contextual resolution.

**Independent test**: Construct Critic-domain objects directly and verify Pydantic structure and intrinsic invariants without invoking `Critic`, `Review`, or `LLMPort`.

### Tests first

- [ ] T001 [US2] Create `tests/unit/test_critics.py` with exact-value tests for `CriticReferenceSource` and every approved `CriticReferenceKind`; verify all unsupported and obsolete kinds are rejected.
- [ ] T002 [US2] Extend `tests/unit/test_critics.py` with legal `source × kind` tests and intrinsic reference-shape coverage for value-only, optional-finding-ID, ID-primary, and parent-ID + value kinds; verify the approved whitespace stripping and blank-after-strip rejection behavior; reject illegal combinations, missing required fields, and forbidden fields without introducing a stricter coercion policy than the approved data model.
- [ ] T003 [US1] Extend `tests/unit/test_critics.py` with `CriticismImportance` and `CriticismTargetType` exact vocabulary tests, including rejection of numeric importance/confidence/probability values.
- [ ] T004 [US1] Extend `tests/unit/test_critics.py` with `Criticism` tests: required non-blank ID/issue/rationale; optional non-blank correction-or-question; at least one target or basis reference; duplicate basis rejection; target/basis duplication rejection; frozen and extra-forbid behavior.
- [ ] T005 [US3] Extend `tests/unit/test_critics.py` with `ValidatedPoint` tests proving its explicit target reference is mandatory, rationale is non-blank, assumption validation does not change its semantics, and generic unreferenced praise is invalid.
- [ ] T006 [US4] Extend `tests/unit/test_critics.py` with `MissingAlternative` tests: non-blank ID/category/rationale, at least one basis reference, exact duplicate basis rejection, boolean `weakens_later_recommendation`, and rejection of replacement-alternative fields.
- [ ] T007 [US4] Extend `tests/unit/test_critics.py` with `ContradictionSide` and `Contradiction` intrinsic tests: required reference/statement/rationale, rejection of two identical `(reference, statement)` sides within one contradiction, and no automatic truth/winner field; defer cross-contradiction unordered-pair duplication to the `CriticalReview` aggregate tests.
- [ ] T008 [US1] Extend `tests/unit/test_critics.py` with `UnresolvedIssue` tests: required non-blank fields, at least one basis reference, and exact duplicate basis rejection.
- [ ] T009 [US1] Extend `tests/unit/test_critics.py` with `CriticalReview` aggregate tests: all five collections default to immutable empty tuples; a fully empty review is valid; IDs are unique within each collection but may repeat across different collections; duplicate validated-point target references, duplicate missing-alternative categories after configured whitespace stripping without case folding, and duplicate contradiction unordered side pairs are rejected; unresolved issues use only unique IDs plus exact structural validation, with no fuzzy semantic duplicate detection.
- [ ] T010 [US1] Extend `tests/unit/test_critics.py` with role-integrity tests proving closed contracts reject ranking, winner, preferred alternative, recommendation, replacement portfolio, numeric scoring, provider metadata, hidden reasoning, and mutable upstream artifact copies.

### Implementation

- [ ] T011 [US1] Create `src/agentic_review_board/domain/critics.py` with the approved enums, `CriticReference`, `Criticism`, `ValidatedPoint`, `MissingAlternative`, `ContradictionSide`, `Contradiction`, `UnresolvedIssue`, and `CriticalReview`, using frozen/extra-forbid Pydantic v2 contracts and immutable tuples.
- [ ] T012 [US1] Complete intrinsic validators in `src/agentic_review_board/domain/critics.py` for exact reference shapes, non-blank text, required target/basis presence, duplicate references, local ID uniqueness, and deterministic structural duplicate findings without adding contextual current-review lookups.

**Checkpoint**: `tests/unit/test_critics.py` passes with no participant, execution aggregate, network, provider SDK, or current-review contextual validation.

---

## Phase 2: Critic Structural Boundary and Contextual Reference Validation

**Purpose**: Convert untrusted structured model output into a trusted `CriticalReview` only when every nested reference and finding-specific contextual rule resolves against the exact four current inputs.

**Independent test**: Call `Critic.review(...)` with deterministic fake/recording `LLMPort` responses and validate only participant-level parsing/context behavior; no Review orchestration yet.

### Tests first

- [ ] T013 [US1] Create `tests/unit/test_critic.py` with a deterministic fake/recording `LLMPort` and a valid empty-review test proving exact role `critic`, JSON-compatible serialization of `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives`, and `RiskAssessment`, structural parsing, and trusted `CriticalReview` return.
- [ ] T014 [US2] Extend `tests/unit/test_critic.py` with value-only `ReviewInput` resolution for DESCRIPTION, TITLE, REVIEW_OBJECTIVE, REVIEW_CONSTRAINT, CONTEXT, and STATED_FACT; reject absent optional scalars, unknown values, ambiguous duplicate collection values, and any item ID.
- [ ] T015 [US2] Extend `tests/unit/test_critic.py` with `ProblemAnalysis` resolution for PROBLEM_OBJECTIVE and every optional-finding-ID kind: exact ID+text match; unique text-only fallback; rejection of unknown IDs, mismatched text, and ambiguous text-only references.
- [ ] T016 [US2] Extend `tests/unit/test_critic.py` with Solution Architect resolution for ALTERNATIVE, ALTERNATIVE_NAME, ALTERNATIVE_DESCRIPTION, ADVANTAGE, DISADVANTAGE, ALTERNATIVE_ASSUMPTION, and IMPLEMENTATION_COMPLEXITY; verify ALTERNATIVE compatibility value means exact `name`; reject unknown parents, mismatched fields, and ambiguous nested values.
- [ ] T017 [US4] Extend `tests/unit/test_critic.py` with GENERATION_EXPLANATION, BLOCKING_MISSING_INFORMATION, and BLOCKING_UNCERTAINTY resolution, including valid zero-alternative generation notes, optional blocker IDs, missing notes, mismatched IDs/text, and ambiguous text-only blockers.
- [ ] T018 [US2] Extend `tests/unit/test_critic.py` with Risk Assessment resolution for RISK, RISK_CATEGORY, RISK_DESCRIPTION, RISK_SEVERITY, MITIGATION, RESIDUAL_UNCERTAINTY, and OVERALL_OBSERVATION; verify RISK compatibility value means exact `description`; reject absent optional fields, unknown parent IDs, mismatched values, and ambiguous observations.
- [ ] T019 [US2] Extend `tests/unit/test_critic.py` with explicit tests proving structured `relevant_constraints`, `affected_scope`, and `risk.basis` cannot be referenced through invented string serialization; a finding about them must target the owning alternative/risk and may use direct original-artifact basis references.
- [ ] T020 [US1] Extend `tests/unit/test_critic.py` with finding-specific contextual rules: explicit target required when unambiguous; CROSS_ARTIFACT_CONCLUSION requires at least two distinct resolved upstream targets, not merely two structurally different reference encodings; OMISSION may omit a single target but requires visible basis; each `ContradictionSide.statement` must equal the exact resolved visible value, using `SolutionAlternative.name` and `Risk.description` for ID-primary references whose optional compatibility value is omitted; all references resolve atomically.
- [ ] T021 [US3] Extend `tests/unit/test_critic.py` with validated-point resolution tests, including solid upstream facts/arguments and assumptions that remain assumptions; prove an all-empty review and a review containing only validated points are both trusted.
- [ ] T022 [US4] Extend `tests/unit/test_critic.py` with missing-alternative, contradiction-side statement compatibility, unordered contradiction duplication, and unresolved-issue basis scenarios; add explicit traceable Criticism examples for a weak argument, underestimated risk, unjustified optimism, and unsupported conclusion; include zero-alternative and zero-risk upstream inputs without forcing artificial findings or attempting to test subjective LLM quality.
- [ ] T023 [US6] Extend `tests/unit/test_critic.py` with malformed output, extra fields, unsupported references, zero-match, multi-match, cross-kind mismatch, and one-invalid-nested-reference cases in each of the five `CriticalReview` collections; prove every structural/contextual failure raises dedicated `CriticOutputError`, returns no partial review, and performs no repair, case folding, fuzzy matching, semantic normalization, or normalization beyond the explicitly approved Pydantic whitespace stripping.

### Implementation

- [ ] T024 [US1] Create `src/agentic_review_board/participants/critic.py` with `Critic`, dedicated `CriticOutputError`, provider-neutral `LLMPort.generate_structured(role="critic", payload=...)`, structural `CriticalReview.model_validate(...)`, and no provider SDK dependency.
- [ ] T025 [US2] Implement Critic-specific explicit resolver dispatch in `src/agentic_review_board/participants/critic.py` for all approved `source × kind` combinations and four reference shapes; use exact comparisons only and do not introduce a generic artifact/reference resolver framework.
- [ ] T026 [US1] Implement recursive atomic validation of every nested reference and finding-specific contextual rules in `src/agentic_review_board/participants/critic.py`, including statement compatibility and cross-artifact distinctness; return the exact parsed review only after the complete validation succeeds.
- [ ] T027 [US3] Complete participant behavior for fully empty, validation-only, zero-alternative, and zero-risk reviews without requiring artificial criticism or disagreement; verify `Critic.review(...)` leaves the exact four upstream input objects and their content unchanged and returns `CriticalReview` only as a separate coexisting artifact.

**Checkpoint**: Critic independently transforms deterministic untrusted model output into a trusted `CriticalReview`, with complete exact current-input traceability and no Review lifecycle changes.

---

## Phase 3: Extend StageExecution Through Critic

**Purpose**: Add the fourth executable stage to the explicit execution contracts while preserving identity-based semantics and keeping Coordinator pending-only.

**Independent test**: Construct `StageExecution` and `Review` snapshots directly with Critic states; no participant invocation or orchestrator.

### Tests first

- [ ] T028 [US5] Extend `tests/unit/test_review_execution.py` with `CriticStageInput`, `StageInput`, and `StageOutput` typing tests; verify Critic PENDING/RUNNING/COMPLETED/FAILED local shapes, completed Critic requires `CriticalReview`, and Coordinator remains PENDING-only.
- [ ] T029 [US5] Extend `tests/unit/test_review_execution.py` with all nine exact Slice 5 RUNNING Analyst/Solution Architect/Risk Reviewer/Critic prefixes and all four exact INCOMPLETE single-failure shapes; reject skipped stages, multiple failures, and later-stage execution after failure.
- [ ] T030 [US5] Extend `tests/unit/test_review_execution.py` with assertions that Coordinator is PENDING in every valid Slice 5 state and `ReviewStatus.COMPLETED` remains unreachable.
- [ ] T031 [US2] Extend `tests/unit/test_review_execution.py` with Critic same-execution provenance tests for every non-PENDING local shape (RUNNING, COMPLETED, and FAILED), proving `is` identity for current `ReviewInput`, Analyst `ProblemAnalysis`, Architect `SolutionAlternatives`, and Risk Reviewer `RiskAssessment`; reject equal-but-independent copies for each artifact independently.
- [ ] T032 [US5] Extend `tests/unit/test_review_execution.py` with regression tests proving lifecycle validation and lookup use `StageIdentity`, directly constructed noncanonical valid tuples remain valid, `Review.create()` emits canonical order, and replacements preserve existing valid order.

### Implementation

- [ ] T033 [US5] Extend `src/agentic_review_board/domain/execution.py` with `CriticStageInput`, `CriticalReview` in `StageOutput`, Critic identity/type validation, and Coordinator PENDING-only behavior while preserving explicit unions.
- [ ] T034 [US5] Extend Review aggregate lifecycle validation in `src/agentic_review_board/domain/execution.py` to exactly the nine RUNNING and four INCOMPLETE Slice 5 shapes using `StageIdentity`, not tuple position.
- [ ] T035 [US2] Extend same-execution provenance validation in `src/agentic_review_board/domain/execution.py` so every non-PENDING Critic stage carries the exact four current Review artifact instances; keep this identity rule separate from generated `CriticReference` resolution.

**Checkpoint**: Domain execution snapshots reject impossible Critic states, Coordinator activity, skipped stages, and cross-review/equal-but-independent provenance.

---

## Phase 4: Critic Review Transitions

**Purpose**: Add only the three explicit immutable Critic transitions required by Slice 5.

**Independent test**: Drive a Review through Critic start/complete/fail without invoking a participant.

### Tests first

- [ ] T036 [US5] Extend `tests/unit/test_review_transitions.py` with `start_critic()` happy path and preconditions: Review RUNNING, first three stages COMPLETED, Critic PENDING, Coordinator PENDING, exact four upstream objects captured, premature/repeated start rejected.
- [ ] T037 [US5] Extend `tests/unit/test_review_transitions.py` with `complete_critic(...)`: Critic must be RUNNING; exact previous `CriticStageInput` preserved; exact supplied `CriticalReview` reused; Review remains RUNNING; prior stages and Coordinator remain unchanged.
- [ ] T038 [US6] Extend `tests/unit/test_review_transitions.py` with `fail_critic(...)`: atomically produce Review INCOMPLETE + Critic FAILED; preserve exact input and upstream stages; store no output; keep Coordinator PENDING; reject failure before start or after a terminal state.
- [ ] T039 [US5] Extend `tests/unit/test_review_transitions.py` with valid noncanonical stage tuple order proving Critic transitions locate/replace by `StageIdentity` and preserve tuple order.

### Implementation

- [ ] T040 [US5] Implement `start_critic()`, `complete_critic(critical_review)`, and `fail_critic(error)` in `src/agentic_review_board/domain/execution.py` using complete validated immutable Review reconstruction and no generic transition engine.

**Checkpoint**: All Critic lifecycle transitions are explicit, immutable, identity-based, and atomically valid before orchestration is extended.

---

## Phase 5: Extend Review Orchestrator Through Critic

**Purpose**: Execute Critic only after exact trusted upstream success and preserve the approved narrow failure boundary.

**Independent test**: Execute deterministic Slice 5 reviews using real participant wrappers and fake `LLMPort`; verify role order, exact artifact handoff, final states, failures, and isolation.

### Tests first

- [ ] T041 [US5] Extend `tests/unit/test_review_orchestrator.py` with successful four-stage orchestration and update helpers/fixtures to construct `ReviewOrchestrator` with Critic while preserving prior-stage failure regressions: exact role order `analyst → solution_architect → risk_reviewer → critic`; exact four-artifact handoff; exact trusted `CriticalReview` object reused as Critic output; Critic COMPLETED; Coordinator PENDING; final Review RUNNING. For Analyst, Solution Architect, and Risk Reviewer failure paths, explicitly prove Critic remains PENDING and `Critic.review(...)` is never invoked.
- [ ] T042 [US1] Extend `tests/unit/test_review_orchestrator.py` with fully empty `CriticalReview`, validation-only review, zero-alternative, and zero-risk success scenarios proving Critic still completes without artificial findings.
- [ ] T043 [US6] Extend `tests/unit/test_review_orchestrator.py` with an end-to-end structural or contextual Critic-output failure using the real participant; verify `CriticOutputError` maps to Critic FAILED + Review INCOMPLETE, exact input is retained, no trusted output is stored, upstream stages remain completed, Coordinator remains PENDING, kind is `OUTPUT_VALIDATION`, and the exact safe message is `Critic output validation failed`.
- [ ] T044 [US6] Extend `tests/unit/test_review_orchestrator.py` with an ordinary provider-style `Exception` during the Critic call; verify `EXECUTION`, exact safe message `Critic execution failed`, no raw exception text in trusted state, preserved upstream work/input, and Coordinator PENDING.
- [ ] T045 [US6] Extend `tests/unit/test_review_orchestrator.py` with internal invariant/misuse cases proving errors outside the Critic participant-call boundary propagate and `BaseException` control signals are not swallowed.
- [ ] T046 [US6] Extend `tests/unit/test_review_orchestrator.py` with sequential success→success and Critic-failure→fresh-review cases proving reused orchestrator/participant objects retain no Review state or cross-review artifacts.

### Implementation

- [ ] T047 [US5] Extend `src/agentic_review_board/application/orchestrator.py` constructor with `critic: Critic` and append the explicit synchronous Critic sequence after Risk Reviewer completion: start stage, retrieve upstream outputs by `StageIdentity`, narrow exact trusted types outside the participant try/except, invoke `Critic.review(...)`, and complete stage; do not add a loop, registry, graph, or workflow engine.
- [ ] T048 [US6] Add the Critic participant failure boundary in `src/agentic_review_board/application/orchestrator.py`: catch `CriticOutputError` only around `Critic.review(...)` as `OUTPUT_VALIDATION`; catch other ordinary participant-call `Exception` as `EXECUTION`; use exact approved safe messages; call `fail_critic(...)`; return immediately; leave domain/invariant errors unsuppressed.

**Checkpoint**: Deterministic Slice 5 execution reaches exactly Review RUNNING with the first four stages COMPLETED and Coordinator PENDING; Critic failures fail closed without contaminating trusted upstream work.

---

## Phase 6: Cross-Cutting Regression and Architecture Verification

**Purpose**: Prove Slice 5 satisfies its approved scope without weakening Slices 1–4 or expanding architecture accidentally.

- [ ] T049 Run the full deterministic `python -m pytest` suite with no live LLM/network dependency and confirm all Slice 1–5 tests pass.
- [ ] T050 Run `python -m ruff check .` and resolve only Slice 5-introduced violations without weakening repository lint rules.
- [ ] T051 Run `python -m mypy` under the repository strict configuration and resolve typing issues for Critic reference kinds, nested immutable models, `StageInput`/`StageOutput`, stage lookup, and Orchestrator narrowing without adding a new dependency/plugin unless separately justified and approved.
- [ ] T052 Run `python -m pip check` and confirm no production dependency change is required.
- [ ] T053 Inspect `src/agentic_review_board/` and `pyproject.toml` to confirm Slice 5 adds no provider SDK, direct Orchestrator→`LLMPort` dependency, Coordinator implementation, final ranking/recommendation, replacement portfolio, numeric scoring, persistence/RAG/UI/tools, retries/timeouts/concurrency, generic workflow/stage registry, or generic artifact/reference framework.
- [ ] T054 Review final implementation against `specs/005-critic/spec.md`, `plan.md`, `data-model.md`, `docs/02-requirements.md`, `docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`, the Constitution, and ADR-0001; confirm Critic only criticizes/validates, assumptions remain assumptions, references resolve fail-closed, generated references remain separate from same-execution provenance, empty output remains valid, and only Coordinator may rank/recommend.

**Final checkpoint**: T001–T054 complete, deterministic suite green, Ruff/mypy/pip checks green, architecture reviewed, and Slice 5 remains limited to Critic v0.1 plus the minimum fourth-stage execution/orchestration extension.

---

## Dependencies

### Completion order

```text
Critic domain contracts (T001–T012)
        ↓
Participant + contextual validation (T013–T027)
        ↓
StageExecution + Review invariants (T028–T035)
        ↓
Critic transitions (T036–T040)
        ↓
Four-stage orchestration + failures (T041–T048)
        ↓
Cross-cutting verification (T049–T054)
```

### Task dependencies

- T001–T010 sequentially establish `tests/unit/test_critics.py`; T011–T012 follow the complete intrinsic test surface.
- T013–T023 sequentially establish one participant/context-validation test file; T024 follows structural tests, and T025–T027 complete contextual and edge behavior.
- T028–T032 extend execution-domain tests before T033–T035 production changes.
- T036–T039 are tests-first for Critic transitions; T040 follows them and the completed aggregate invariants.
- T041–T046 extend orchestration tests after participant/domain transitions are stable; T047–T048 implement only the behavior demanded by those tests.
- T049–T054 run only after all production behavior is complete.

No production task begins before its corresponding tests exist and fail for the expected missing behavior.

---

## Parallel Execution Guidance

Slice 5 is intentionally mostly sequential because contextual resolution, execution invariants, transitions, and orchestration are dependency ordered.

Safe parallelism is limited. Once Phase 1 contracts are stable, participant test-fixture preparation may proceed independently from read-only review of execution regression coverage, provided neither stream begins production work whose prerequisite contract is still changing.

Do not label tasks parallel merely because concerns differ when they modify the same file or depend on an incomplete contract.

---

## Implementation Strategy

Implement in small verified increments:

1. **Intrinsic Critic contracts** — no current context, participant, or orchestration.
2. **Participant trust boundary** — structural parsing followed by exact four-artifact contextual resolution.
3. **Execution truth** — fourth-stage typing, exact lifecycle matrix, and same-execution provenance.
4. **Transitions** — explicit immutable Critic start/complete/fail operations.
5. **Orchestration** — explicit fourth participant and narrow safe failure mapping.
6. **Regression and isolation** — Slices 1–4 remain intact and reviews do not leak state.
7. **Verification** — full suite, lint, typing, dependencies, architecture, and responsibility boundaries.

Do not implement Coordinator, FinalReview, ranking/recommendation, automatic upstream rewriting, replacement alternatives, provider adapters, retries/timeouts, persistence, RAG, tools, UI, generic workflow/reference abstractions, or numeric Critic scoring in this slice.

---

## Implementation Gate

Before any production implementation begins:

- review this `tasks.md` against the approved spec, plan, and data model;
- confirm task ordering remains tests-first;
- confirm each reference kind has explicit deterministic coverage;
- confirm no task introduces Coordinator behavior, ranking/recommendation, or generic reference/workflow infrastructure;
- confirm checkpoints are independently verifiable;
- obtain explicit approval for this task breakdown.

Only after `tasks.md` is reviewed and explicitly approved should implementation start.
