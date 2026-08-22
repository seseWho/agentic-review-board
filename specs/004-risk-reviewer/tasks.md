# Tasks: Risk Reviewer v0.1

**Input**: Approved design documents from `specs/004-risk-reviewer/`  
**Prerequisites**: approved `spec.md`, approved `plan.md`, user-approved `data-model.md`, accepted `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`, and merged Slice 1–3 contracts on `main`  
**Branch**: `004-risk-reviewer`  
**Status**: Completed — implementation and cross-cutting verification passed

**Verification**: GitHub Actions CI #61 passed on Python 3.12 and 3.13. Each matrix job completed dependency check, the full deterministic test suite (`258 passed`), Ruff, and strict mypy successfully. Final architectural review T043–T044 also passed with no Slice 4 scope expansion.

Tests are mandatory because Slice 4 introduces a generated risk contract, contextual cross-artifact references, a third execution-stage provenance boundary, and a new mandatory participant failure boundary. All behavior must remain deterministic, inspectable, provider-neutral, and fail-closed.

## Format

Every implementation task follows:

```text
- [ ] Txxx [P?] [US?] Action with exact file path
```

- `[P]` means the task can be executed in parallel because it changes a different file and all prerequisites are already complete.
- `[US1]`–`[US5]` map directly to the approved user stories in `spec.md`.
- Tests are written before the corresponding production behavior.
- A task is complete only when its tests and the approved Slice 4 contracts are satisfied.
- Do not start a later phase merely because an earlier production file compiles; complete the phase checkpoint first.

---

## Phase 1: Risk Domain Contracts

**Purpose**: Establish the intrinsic immutable Risk Reviewer output contract before any LLM or current-review contextual validation is introduced.

**Independent test**: Construct risk-domain objects directly and verify Pydantic structure/invariants without invoking `RiskReviewer`, `Review`, or `LLMPort`.

### Tests first

- [X] T001 [US1] Create `tests/unit/test_risks.py` with tests for `RiskScopeKind` and `RiskScope`: `OVERALL` requires no alternative IDs; `ALTERNATIVES` requires one or more non-blank unique IDs; models are frozen/extra-forbid; tuple-backed collections remain immutable.
- [X] T002 [US1] Extend `tests/unit/test_risks.py` with `RiskBasisSource`, `ProblemAnalysisFindingKind`, and `SolutionAlternativeCharacteristicKind` contract tests, including exact enum values and rejection of unsupported values.
- [X] T003 [US2] Extend `tests/unit/test_risks.py` with discriminated-union construction tests proving each basis variant uses a literal `source` tag and that `RiskBasisReference` selects `ReviewInputBasisReference`, `ProblemAnalysisBasisReference`, or `SolutionAlternativeBasisReference` deterministically.
- [X] T004 [US2] Extend `tests/unit/test_risks.py` with intrinsic basis-reference tests: required strings non-blank; optional IDs non-blank when present; `SolutionAlternativeBasisReference` requires `ConstraintReference` only for `RELEVANT_CONSTRAINT` and `StrictStr` for every other characteristic; extra fields rejected.
- [X] T005 [US1] Extend `tests/unit/test_risks.py` with `Risk` and `RiskAssessment` tests: every Risk-domain Pydantic model is frozen and extra-forbid; non-blank IDs/descriptions/category/mitigation/residual uncertainty; optional category/mitigation/residual uncertainty may be omitted; non-empty basis; exact duplicate basis rejection; unique Risk IDs; non-blank unique observations; zero-risk and fully empty assessments valid; arbitrary non-blank category labels accepted.
- [X] T006 [US1] Extend `tests/unit/test_risks.py` with role-integrity tests proving generated `ranking`, `preferred_alternative`, `recommendation`, `winner`, numeric `probability`, `likelihood`, `risk_score`, `alternatives`, `replacement_alternative`, and `replacement_alternatives` fields are rejected by the closed contracts, so Risk Reviewer cannot rank, recommend, redefine, or silently replace candidate alternatives.

### Implementation

- [X] T007 [US1] Create `src/agentic_review_board/domain/risks.py` with `RiskScopeKind`, `RiskScope`, `RiskBasisSource`, `ProblemAnalysisFindingKind`, `SolutionAlternativeCharacteristicKind`, the three basis-reference models with `Literal[...]` discriminator tags, the discriminated `RiskBasisReference` union, `Risk`, and `RiskAssessment`, exactly as approved in `data-model.md`.
- [X] T008 [US1] Complete intrinsic validators in `src/agentic_review_board/domain/risks.py` for non-blank text, scope shape, characteristic/value compatibility, duplicate basis entries, unique Risk IDs, and duplicate/non-blank observations without adding contextual current-review lookups to the domain model.

**Checkpoint**: `tests/unit/test_risks.py` passes with no participant, execution aggregate, network, provider SDK, or current-review contextual validation.

---

## Phase 2: Risk Reviewer Structural Boundary and Contextual Reference Validation

**Purpose**: Convert untrusted structured model output into a trusted `RiskAssessment` only when every scope and basis reference resolves against the explicit current inputs.

**Independent test**: Call `RiskReviewer.assess(...)` with deterministic fake `LLMPort` responses and validate only participant-level parsing/contextual behavior; no Review orchestration yet.

### Tests first

- [X] T009 [US1] Create `tests/unit/test_risk_reviewer.py` with a deterministic fake/recording `LLMPort` and a valid assessment test proving role `risk_reviewer`, JSON-compatible `model_dump(mode="json")` payloads for all three inputs, structural parsing, and trusted `RiskAssessment` return.
- [X] T010 [US2] Extend `tests/unit/test_risk_reviewer.py` with `ReviewInputBasisReference` resolution tests for every existing `ReviewInputSource`: exact scalar resolution for description/title/objective, unique collection-member resolution for constraints/context/stated facts, and fail-closed rejection of absent or ambiguous duplicate text.
- [X] T011 [US2] Extend `tests/unit/test_risk_reviewer.py` with `ProblemAnalysisBasisReference` resolution tests for FACT, CONSTRAINT, ASSUMPTION, MISSING_INFORMATION, and UNCERTAINTY: exact ID+text match; unique text-only fallback; rejection of unknown, mismatched, or ambiguous references; explicit preservation of assumption-derived support.
- [X] T012 [US2] Extend `tests/unit/test_risk_reviewer.py` with `SolutionAlternativeBasisReference` tests for DESCRIPTION, ADVANTAGE, DISADVANTAGE, ASSUMPTION, IMPLEMENTATION_COMPLEXITY, and structured `RELEVANT_CONSTRAINT`; reject unknown alternatives, characteristic/value mismatches, ambiguous duplicate text, non-resolving `ConstraintReference` values, and duplicated identical `ConstraintReference` entries that make a relevant-constraint basis ambiguous rather than exactly resolvable.
- [X] T013 [US1] Extend `tests/unit/test_risk_reviewer.py` with affected-scope contextual tests: overall scope accepted without lookup; one/multiple current alternative IDs accepted; unknown IDs rejected; alternative scope rejected against valid zero-alternative `SolutionAlternatives`.
- [X] T014 [US3] Extend `tests/unit/test_risk_reviewer.py` with zero-risk and zero-alternative scenarios proving zero risks are trusted, Risk Reviewer accepts and evaluates valid zero-alternative input, overall risks/observations remain valid, and no alternative-specific scope/basis can be fabricated when alternatives are empty.
- [X] T015 [US5] Extend `tests/unit/test_risk_reviewer.py` with malformed/extra-field/contextual-failure cases proving all structural or contextual generated-output failures raise dedicated `RiskReviewerOutputError`, expose no partially trusted output, and do not silently repair references.

### Implementation

- [X] T016 [US1] Create `src/agentic_review_board/participants/risk_reviewer.py` with `RiskReviewer`, dedicated `RiskReviewerOutputError`, provider-neutral `LLMPort.generate_structured(role="risk_reviewer", payload=...)`, structural `RiskAssessment.model_validate(...)`, and no provider SDK dependency.
- [X] T017 [US2] Implement `_validate_scope_references(...)` and Risk Reviewer-specific contextual resolvers for `ReviewInputBasisReference`, `ProblemAnalysisBasisReference`, and `SolutionAlternativeBasisReference`; resolve only against the three explicit current inputs; ambiguity/no-match fails closed; do not introduce a generic `ArtifactReference`/resolver framework.
- [X] T018 [US3] Complete participant behavior for zero-risk/zero-alternative inputs and ensure structural/contextual validation returns the exact trusted `RiskAssessment` object only after every reference succeeds.

**Checkpoint**: Risk Reviewer can independently transform deterministic untrusted model output into trusted risk analysis, with full current-input traceability and no Review lifecycle changes yet.

---

## Phase 3: Extend StageExecution Through Risk Reviewer

**Purpose**: Add the third executable stage to the existing explicit execution contracts while preserving Slice 3 identity-based semantics.

**Independent test**: Construct `StageExecution` and `Review` snapshots directly with Risk Reviewer states; no participant invocation or orchestrator.

### Tests first

- [X] T019 [US4] Extend `tests/unit/test_review_execution.py` with `RiskReviewerStageInput`, `StageInput`, and `StageOutput` typing tests; Risk Reviewer PENDING/RUNNING/COMPLETED/FAILED local shapes; completed Risk Reviewer requires `RiskAssessment`; Critic/Coordinator remain PENDING-only.
- [X] T020 [US4] Extend `tests/unit/test_review_execution.py` with all seven exact Slice 4 RUNNING `(Analyst, Solution Architect, Risk Reviewer)` prefixes and all three exact INCOMPLETE failure shapes; reject skipped-stage, multiple-failure, and later-stage non-PENDING combinations; confirm Review `COMPLETED` remains unreachable in Slice 4.
- [X] T021 [US2] Extend `tests/unit/test_review_execution.py` with Risk Reviewer same-execution provenance tests proving exact identity for current `ReviewInput`, completed Analyst `ProblemAnalysis`, and completed Solution Architect `SolutionAlternatives`; equal-but-independent copies are rejected.
- [X] T022 [US4] Extend `tests/unit/test_review_execution.py` with regression tests proving semantic validation and lookup continue to use `StageIdentity`, reordered directly constructed valid stage tuples remain valid, `Review.create()` still emits canonical order, and replacements preserve an existing valid order.

### Implementation

- [X] T023 [US4] Extend `src/agentic_review_board/domain/execution.py` with `RiskReviewerStageInput`, `RiskAssessment` in `StageOutput`, Risk Reviewer identity/type validation, and Critic/Coordinator PENDING-only behavior while preserving explicit unions rather than introducing generic payload envelopes.
- [X] T024 [US4] Extend Review aggregate lifecycle validation in `src/agentic_review_board/domain/execution.py` to the exact Slice 4 RUNNING/INCOMPLETE matrices using identity-based stage lookup, not tuple positions.
- [X] T025 [US2] Extend same-execution provenance validation in `src/agentic_review_board/domain/execution.py` so a non-PENDING Risk Reviewer stage references the exact current ReviewInput, Analyst output, and Architect output instances; keep generated textual-reference semantics separate from this identity rule.

**Checkpoint**: Domain execution snapshots independently reject impossible Risk Reviewer states and cross-review/equal-but-independent execution provenance.

---

## Phase 4: Risk Reviewer Review Transitions

**Purpose**: Add only the three explicit immutable Risk Reviewer transitions required by Slice 4.

**Independent test**: Drive a Review through Risk Reviewer start/complete/fail without invoking any participant.

### Tests first

- [X] T026 [US4] Extend `tests/unit/test_review_transitions.py` with `start_risk_reviewer()` happy-path and precondition tests: Review RUNNING, Analyst+Architect completed, Risk Reviewer pending, Critic/Coordinator pending, exact upstream objects captured, premature/repeated start rejected.
- [X] T027 [US4] Extend `tests/unit/test_review_transitions.py` with `complete_risk_reviewer(...)`: Risk Reviewer must be RUNNING; exact previous `RiskReviewerStageInput` preserved; exact supplied `RiskAssessment` reused as output; Review remains RUNNING; earlier stages and later PENDING stages unchanged.
- [X] T028 [US5] Extend `tests/unit/test_review_transitions.py` with `fail_risk_reviewer(...)`: atomically produce Review INCOMPLETE + Risk Reviewer FAILED, preserve exact recorded inputs and upstream completed stages, store no output, keep Critic/Coordinator PENDING, reject failure before start or after terminal state.
- [X] T029 [US4] Extend `tests/unit/test_review_transitions.py` with a valid noncanonical stage tuple order to prove `start/complete/fail_risk_reviewer` locate and replace stages by `StageIdentity` and preserve tuple order.

### Implementation

- [X] T030 [US4] Implement `start_risk_reviewer()`, `complete_risk_reviewer(risk_assessment)`, and `fail_risk_reviewer(error)` in `src/agentic_review_board/domain/execution.py` using complete validated immutable Review reconstruction and no generic transition engine.

**Checkpoint**: All Risk Reviewer lifecycle transitions are explicit, immutable, identity-based, and atomically valid before orchestration is extended.

---

## Phase 5: Extend Review Orchestrator Through Risk Reviewer

**Purpose**: Execute the third participant only after exact trusted upstream success and preserve the approved failure boundary.

**Independent test**: Execute complete deterministic Slice 4 reviews using real participant wrappers and fake `LLMPort`; verify role order, exact artifact handoff, final states, and failure behavior.

### Tests first

- [X] T031 [US4] Extend `tests/unit/test_review_orchestrator.py` with successful three-stage orchestration and update existing orchestrator helpers/fixtures to construct `ReviewOrchestrator` with the Risk Reviewer while preserving Analyst/Solution Architect failure-regression coverage: exact role order `analyst → solution_architect → risk_reviewer`; each stage input recorded before invocation; exact current ReviewInput/ProblemAnalysis/SolutionAlternatives passed; all three implemented stages COMPLETED; Critic/Coordinator PENDING; final Review RUNNING.
- [X] T032 [US3] Extend `tests/unit/test_review_orchestrator.py` with valid zero-risk and valid zero-alternative scenarios proving both still complete Risk Reviewer and preserve the approved final Slice 4 RUNNING state.
- [X] T033 [US5] Extend `tests/unit/test_review_orchestrator.py` with an end-to-end generated-output validation failure using the real `RiskReviewer` and a deterministic recording `LLMPort` response that is structurally or contextually invalid; verify the participant raises `RiskReviewerOutputError`, the Orchestrator maps it to Risk Reviewer FAILED + Review INCOMPLETE, retains exact inputs, stores no trusted `RiskAssessment`, preserves Analyst/Architect, leaves later stages pending, records `OUTPUT_VALIDATION`, and uses exact safe message `Risk Reviewer output validation failed`.
- [X] T034 [US5] Extend `tests/unit/test_review_orchestrator.py` with an end-to-end ordinary execution failure using the real `RiskReviewer` and a deterministic recording `LLMPort` that raises an ordinary provider-style `Exception` during the Risk Reviewer call; verify Risk Reviewer FAILED + Review INCOMPLETE, preserved upstream work/inputs, no trusted RiskAssessment, `EXECUTION`, exact safe message `Risk Reviewer execution failed`, and no raw exception text in trusted state.
- [X] T035 [US5] Extend `tests/unit/test_review_orchestrator.py` with internal invariant/misuse cases proving failures outside the Risk Reviewer participant call propagate rather than being converted into `ReviewError`; prove `KeyboardInterrupt`/`SystemExit`-class `BaseException` signals are not swallowed.
- [X] T036 [US5] Extend `tests/unit/test_review_orchestrator.py` with sequential success→success and Risk-failure→fresh-review cases proving the same orchestrator/participant objects do not retain Review state or cross-review risk artifacts.

### Implementation

- [X] T037 [US4] Extend `src/agentic_review_board/application/orchestrator.py` constructor with `risk_reviewer: RiskReviewer` and extend the explicit synchronous sequence after Solution Architect completion: start Risk Reviewer, retrieve Analyst/Architect outputs by `StageIdentity`, narrow exact trusted types outside the participant try/except, invoke Risk Reviewer, and complete the stage; do not add a stage loop/registry/graph engine.
- [X] T038 [US5] Add the Risk Reviewer participant failure boundary in `src/agentic_review_board/application/orchestrator.py`: catch `RiskReviewerOutputError` only around `RiskReviewer.assess(...)` as `OUTPUT_VALIDATION`; catch other ordinary participant-call `Exception` as `EXECUTION`; use the two approved stable safe messages; invoke `fail_risk_reviewer(...)`; return immediately; leave domain/invariant errors unsuppressed.

**Checkpoint**: A complete deterministic Slice 4 execution reaches exactly `RUNNING + Analyst COMPLETED + Solution Architect COMPLETED + Risk Reviewer COMPLETED + Critic/Coordinator PENDING`, and mandatory Risk Reviewer failure fails closed without contaminating trusted upstream work.

---

## Phase 6: Cross-Cutting Regression and Architecture Verification

**Purpose**: Prove Slice 4 satisfies its approved scope and did not weaken prior slices or expand architecture accidentally.

- [X] T039 Run the full deterministic `python -m pytest` suite with no live LLM/network dependency and confirm all Slice 1–4 tests pass, including Analyst/Solution Architect regression behavior.
- [X] T040 Run `python -m ruff check .` and resolve only Slice 4-introduced violations without weakening repository lint rules.
- [X] T041 Run `python -m mypy` under the repository strict configuration and resolve typing issues for discriminated unions, `StrictStr | ConstraintReference`, `StageInput`/`StageOutput`, stage lookup, and Orchestrator narrowing without adding a new dependency/plugin unless separately justified and approved.
- [X] T042 Run `python -m pip check` and confirm no production dependency change is required.
- [X] T043 Inspect `src/agentic_review_board/` and `pyproject.toml` to confirm Slice 4 adds no provider SDK, direct Orchestrator→`LLMPort` dependency, Critic/Coordinator implementation, ranking/final recommendation, numeric risk probability/scoring, persistence/RAG/UI/tools, retries/timeouts/concurrency, generic workflow/stage registry, generic artifact/reference framework, or organization-wide taxonomy infrastructure.
- [X] T044 Review final implementation against `specs/004-risk-reviewer/spec.md`, `plan.md`, `data-model.md`, `docs/02-requirements.md`, `docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`, the Constitution, and ADR-0001; confirm every material risk basis is inspectable/current-input grounded, assumptions remain assumptions, generated-reference resolution is not confused with StageExecution provenance, candidate alternatives are never redefined/replaced, and only Coordinator remains authorized to rank/recommend.

**Final checkpoint**: T001–T044 complete, full deterministic suite green, Ruff/mypy/pip checks green, architectural scope confirmed, and Slice 4 remains limited to Risk Reviewer v0.1 plus the minimum third-stage execution/orchestration extension.

---

## Dependencies

### Completion order

```text
Risk domain contracts (T001–T008)
        ↓
Participant + contextual validation (T009–T018)
        ↓
StageExecution + Review invariants (T019–T025)
        ↓
Risk Reviewer transitions (T026–T030)
        ↓
Three-stage orchestration + failures (T031–T038)
        ↓
Cross-cutting verification (T039–T044)
```

### Task dependencies

- T001–T006 are sequential because they all establish `tests/unit/test_risks.py`; T007–T008 follow the complete intrinsic test surface.
- T009–T015 are sequential because they build one participant/context-validation test file; T016 follows structural tests and T017–T018 complete contextual/edge behavior.
- T019–T022 extend existing execution-domain tests and should be completed before T023–T025 production changes.
- T026–T029 are tests-first for `tests/unit/test_review_transitions.py`; T030 follows them and the completed aggregate invariants.
- T031–T036 extend the orchestration tests after participant/domain transitions are stable; T037–T038 implement only the behavior demanded by those tests.
- T039–T044 run only after all story/implementation tasks are complete.

No production task should begin before its corresponding tests exist and fail for the expected missing behavior.

---

## Parallel Execution Guidance

Slice 4 is intentionally mostly sequential because contextual validation, execution invariants, and orchestration are dependency ordered.

Safe parallelism is limited. For example, once Phase 1 contracts are stable, a developer may prepare participant test fixtures in `test_risk_reviewer.py` while another reviews execution regression tests, provided neither begins production work whose prerequisite contract is still changing.

Do not mark tasks parallel merely because conceptual concerns differ when they modify the same file or depend on an unapproved/incomplete contract.

---

## Implementation Strategy

Implement in small verified increments:

1. **Intrinsic Risk contracts** — no context, participant, or orchestration.
2. **Participant trust boundary** — structural parsing then explicit current-input contextual validation.
3. **Execution truth** — third-stage typing, lifecycle matrix, and same-execution provenance.
4. **Transitions** — exact immutable Risk Reviewer start/complete/fail operations.
5. **Orchestration** — explicit Analyst → Solution Architect → Risk Reviewer path and safe mandatory failure handling.
6. **Regression/isolation** — prior behavior remains intact and reviews do not leak state.
7. **Verification** — full suite, lint, typing, dependency, architecture, and role-integrity checks.

Do not implement Critic, Coordinator, FinalReview, ranking/recommendation, provider adapters, retries/timeouts, persistence, RAG, tools, UI, generic workflow/reference abstractions, or numeric risk scoring in this slice.

---

## Implementation Gate

Before any production implementation begins:

- review this `tasks.md` against the approved spec/plan/data-model;
- confirm task ordering remains tests-first;
- confirm no task smuggles future Critic/Coordinator behavior or a generic reference/workflow abstraction;
- confirm checkpoints are independently verifiable;
- obtain explicit approval for this task breakdown.

Only after `tasks.md` is reviewed and explicitly approved should implementation start.
