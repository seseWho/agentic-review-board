# Tasks: Pedagogical Review UI v0.1

**Input:** Approved design documents from `specs/008-pedagogical-ui/`
**Prerequisites:** approved `spec.md`, approved `plan.md`, approved `data-model.md`,
accepted `docs/adr/ADR-0003-streamlit-for-pedagogical-review-ui.md`, and the validated
five-participant Slice 1–7.2 runtime baseline
**Branch:** `008-pedagogical-ui`
**Status:** Approved — implementation may proceed tests-first in reviewed phases

The implementation is functionality-first. Authentic orchestration observations and
deterministic five-agent scenarios are proven before browser presentation. Visual work is
limited to what makes agent roles, propagation, trusted results, and fail-closed behavior
understandable.

## Format and Execution Rules

Every implementation task follows:

```text
- [ ] Txxx [TEST|DOC|LIVE?] [US?] Action with exact file path
```

- `[US1]`–`[US6]` map directly to the approved user stories in `spec.md`.
- `[TEST]` identifies a test-first or verification task.
- `[DOC]` identifies documentation or recorded acceptance evidence.
- `[LIVE]` identifies explicitly authorized local-vLLM validation, never a default test.
- Complete tasks in identifier order. Tasks sharing production or fixture boundaries are
  deliberately not marked parallel.
- Each test block must fail for the expected missing behavior before its production tasks
  begin, unless it is a regression test that already passes by design.
- No phase is complete until its checkpoint passes.
- Do not weaken an existing domain, participant, evidence, or failure contract to simplify
  presentation.
- Do not prioritize cosmetic styling over the functional scenario gates.

---

## Phase 1: Framework Dependency and Architecture Guards

**Purpose:** Admit exactly the approved UI framework while keeping it outside core and LLM
infrastructure.

**Independent test:** Static dependency/import checks distinguish the UI adapter and root
composition entry from core application code.

### Tests first

- [ ] T001 [TEST] Update `tests/architecture/test_infrastructure_boundaries.py` so the exact
  runtime dependency set includes constrained Streamlit, `streamlit` imports are permitted
  only under `src/agentic_review_board/ui/`, and domain, application, participants, and LLM
  infrastructure continue to reject UI/web imports; add an explicit inverse guard proving
  the UI package cannot import HTTPX, provider adapters, LLM configuration, or concrete
  infrastructure; refine the existing executable-token guard so UI-named definitions are
  allowed only inside the approved UI package rather than disabling the guard globally.

### Configuration

- [ ] T002 Add `streamlit>=1.63,<2` to the normal runtime dependencies in `pyproject.toml`
  without adding charting, component, web-server, workflow, or persistence packages.
- [ ] T003 [TEST] Synchronize the editable development environment from `pyproject.toml` and
  run the focused dependency and architecture checks; record no lockfile because the
  repository has no approved lockfile convention.

**Checkpoint:** Current core imports still pass, Streamlit is an explicit constrained
dependency, and only the future UI adapter/root entry may own presentation-framework code.

---

## Phase 2: Authentic Review Observation Boundary

**Purpose:** Expose real validated workflow transitions without changing orchestration
authority or participant semantics.

**Independent test:** Execute the existing orchestrator with deterministic participants and
inspect observer snapshots without importing Streamlit.

### Tests first

- [ ] T004 [TEST] [US2] Extend `tests/unit/test_review_orchestrator.py` with a no-observer
  regression proving identical participant order, object propagation, terminal Review, and
  call counts to the current execution path.
- [ ] T005 [TEST] [US2] Extend `tests/unit/test_review_orchestrator.py` with the exact
  eleven-snapshot successful sequence: Review start, each of five stage starts, and each of
  five completions; prove every value is a frozen validated `Review` and the last emitted
  object is the exact returned object.
- [ ] T006 [TEST] [US2] [US5] Add parameterized failure-observation tests to
  `tests/unit/test_review_orchestrator.py` for Analyst through Coordinator, proving exact
  `2k + 1` snapshot counts, preserved completed upstream work, one failed reached stage,
  pending downstream stages, and identity between the final emission and returned
  incomplete Review.
- [ ] T007 [TEST] [US2] Extend `tests/unit/test_review_orchestrator.py` with observers that
  raise at Review start, stage start, successful completion, and failure notification;
  prove propagation is immediate, no observer error becomes `ReviewError`, and no later
  participant is called.
- [ ] T008 [TEST] [US2] Extend
  `tests/unit/infrastructure/llm/test_composition.py` with exact observer forwarding,
  `observer=None` compatibility, closed-runtime rejection before observation, and resource
  lifecycle regressions.

### Implementation

- [ ] T009 [US2] Create `src/agentic_review_board/application/observation.py` with only the
  provider-neutral `ReviewObserver` alias and export it from
  `src/agentic_review_board/application/__init__.py`.
- [ ] T010 [US2] Extend `src/agentic_review_board/application/orchestrator.py` with the
  optional keyword-only observer and synchronous notification after every validated
  transition, keeping notifications outside participant exception handlers and preserving
  the explicit five-stage orchestration.
- [ ] T011 [US2] Extend
  `src/agentic_review_board/infrastructure/llm/composition.py` to forward the optional
  observer without exposing its orchestrator/client or changing close behavior.

**Checkpoint:** The observer tests prove authentic complete and failed agent progression
independently of Streamlit; all pre-Slice-8 orchestration tests remain green.

---

## Phase 3: Pure UI State, Input, and Presentation Mapping

**Purpose:** Establish deterministic presentation logic before creating interactive
widgets.

**Independent test:** Convert drafts and trusted Reviews into UI-local immutable state and
stage presentation values without starting a Streamlit application or model runtime.

### Tests first

- [ ] T012 [TEST] [US1] Create `tests/unit/ui/test_app_state.py` with draft normalization
  cases for required description, optional scalar empty-to-`None`, CRLF/LF repeated values,
  whitespace-only absence/rejection, exact outer-whitespace preservation for every
  non-empty value, Unicode, preserved order and duplicates, discarded blank lines, and no
  comma/JSON interpretation.
- [ ] T013 [TEST] [US1] [US6] Extend `tests/unit/ui/test_app_state.py` with all allowed
  `ReviewUiState` phases, duplicate-start guard, observer snapshot replacement, terminal
  return, startup/application error, selected-stage, and complete reset transitions; reject
  or fail safely on inconsistent phase/Review combinations.
- [ ] T014 [TEST] [US5] Extend `tests/unit/ui/test_app_state.py` with fixed sanitized error
  messages containing no injected exception, secret, endpoint, prompt, or raw-output marker
  and proving UI errors never construct a domain `ReviewError`.
- [ ] T015 [TEST] [US2] [US3] Create `tests/unit/ui/test_presentation.py` with exhaustive
  `StageIdentity`, `StageStatus`, and `ReviewStatus` mapping tests for canonical order,
  readable non-color-only labels, responsibilities, input artifact labels, and output type
  labels.
- [ ] T016 [TEST] [US3] [US5] Extend `tests/unit/ui/test_presentation.py` with
  `StagePresentation` tests proving it references the exact `StageExecution`, uses the
  descriptor selected by that execution identity, derives `blocked_by` only for downstream
  pending stages after a trusted failure, and never writes blocked state into the Review.
- [ ] T017 [TEST] [US3] Extend `tests/unit/ui/test_presentation.py` with completed-only output
  dispatch for all five exact output types; distinguish pending/running/failed/unavailable
  from valid empty collections and preserve material IDs, provenance, assumptions,
  uncertainties, validation status, and contradiction support status.
- [ ] T018 [TEST] [US4] Extend `tests/unit/ui/test_presentation.py` with final-result
  availability, preferred-alternative presence/absence, ranked data, principal risks,
  unresolved questions, qualitative confidence, `INSUFFICIENT_EVIDENCE`, next validation
  step, and decision-support notice; prove no numeric probability or executable action is
  derived.

### Implementation

- [ ] T019 Create `src/agentic_review_board/ui/__init__.py` with a narrow public rendering
  entry and no import-time runtime construction.
- [ ] T020 [US1] [US6] Create `src/agentic_review_board/ui/app.py` with the approved
  `ReviewExecutor`, `ReviewInputDraft`, normalization, `UiPhase`, `UiError`, immutable
  `ReviewUiState`, guarded transitions, and reset helpers; keep concrete LLM infrastructure
  outside this module.
- [ ] T021 [US2] [US3] Create `src/agentic_review_board/ui/presentation.py` with exhaustive
  static descriptors, exact status labels, derived blocked-stage mapping, and trusted
  completed-output dispatch.
- [ ] T022 [US3] [US4] Complete pure role-specific and final-result presentation helpers in
  `src/agentic_review_board/ui/presentation.py`, preserving evidence semantics and returning
  no HTML, provider values, actions, or replacement domain artifacts.

**Checkpoint:** Pure tests prove input preservation, UI-state isolation, all five role
mappings, failure blocking, evidence labels, and final-result gating with no live model.

---

## Phase 4: Deterministic Five-Agent Functional Scenarios

**Purpose:** Make UI verification exercise genuine participants and the real orchestrator,
not a collection of unrelated fabricated screen values.

**Independent test:** Run each scenario outside Streamlit and prove participant calls,
artifact handoff, observer history, and terminal state.

### Test infrastructure and contracts

- [ ] T023 [TEST] Create `tests/ui/fixtures/review_scenarios.py` with deterministic scripted
  `LLMPort` substitutes and valid structured mappings for the five existing participants;
  build executors through the real `Analyst`, `SolutionArchitect`, `RiskReviewer`, `Critic`,
  `Coordinator`, and `ReviewOrchestrator`.
- [ ] T024 [TEST] [US2] [US3] Create `tests/ui/test_review_scenarios.py` with a complete
  scenario proving exact five-role call order, exact current-review/upstream-artifact
  propagation, eleven observer snapshots, five trusted outputs, and terminal completion.
- [ ] T025 [TEST] [US4] Extend `tests/ui/test_review_scenarios.py` with a trusted completed
  `INSUFFICIENT_EVIDENCE` scenario that produces no invented preference and retains
  unresolved information and next validation step.
- [ ] T026 [TEST] [US5] Extend `tests/ui/test_review_scenarios.py` with Critic
  output-validation failure and participant/provider execution failure scenarios, proving
  their distinct trusted categories, upstream preservation, Coordinator non-invocation,
  and absence of final output.
- [ ] T027 [TEST] [US6] Extend `tests/ui/test_review_scenarios.py` with two sequential fresh
  inputs through a reused deterministic executor, proving no Review, prompt payload,
  output, error, observer history, or participant-call data crosses executions.
- [ ] T028 [TEST] Create
  `tests/ui/fixtures/deterministic_streamlit_app.py` as a test-only Streamlit composition
  entry using those real-participant deterministic scenarios, selected only through
  test-injected session state and never through production UI controls.

**Checkpoint:** All pedagogical UI outcomes are backed by deterministic execution through
the real agent collaboration path, with no vLLM, network, credentials, or hand-built
terminal Review shortcut.

---

## Phase 5: Review Form and Authentic Process View

**Purpose:** Implement explicit start and the primary five-agent process surface.

**Independent test:** Drive the deterministic Streamlit app with `AppTest`, submit input,
and inspect execution count, captured snapshots, ordered stages, and trusted process state.

### Tests first

- [ ] T029 [TEST] [US1] Create `tests/ui/test_streamlit_app.py` with `AppTest` coverage for
  initial form labels, required/optional distinction, no execution on load or ordinary
  widget edits, field validation, line-based collections, and exact accepted
  `ReviewInput` values.
- [ ] T030 [TEST] [US1] Extend `tests/ui/test_streamlit_app.py` with explicit Start behavior,
  form isolation after start, an execution call counter, repeated script reruns, and
  repeated interaction proving exactly one non-overlapping Review execution.
- [ ] T031 [TEST] [US2] Extend `tests/ui/test_streamlit_app.py` with exactly five ordered
  participant cards, readable stage and overall statuses, one-running-stage invariant from
  captured observer history, and canonical dependency direction with no parallelism claim.
- [ ] T032 [TEST] [US2] [US3] Extend `tests/ui/test_streamlit_app.py` to prove every
  completion snapshot is observed before the next stage-start snapshot, completed output
  becomes inspectable, static responsibility stays distinct from generated content, and
  recorded input artifact types are visible.

### Implementation

- [ ] T033 [US1] Implement initial state, labelled form controls, normalization/validation,
  explicit Start, and disabled/hidden active input behavior in
  `src/agentic_review_board/ui/app.py` using standard Streamlit components only.
- [ ] T034 [US2] Implement synchronous observer-driven status containers and overall Review
  status in `src/agentic_review_board/ui/app.py`; create all stage surfaces before invoking
  the executor and update them from exact snapshots without timers, percentages, polling,
  threads, queues, or partial model text.
- [ ] T035 [US2] [US3] Implement the canonical process overview and stage selection/detail
  surface in `src/agentic_review_board/ui/app.py`, delegating all semantic mappings to
  `presentation.py` and preserving the process view after terminal return.

**Checkpoint:** AppTest proves explicit one-shot execution and a truthful, ordered process
view driven by the real deterministic five-agent observer sequence.

---

## Phase 6: Role-Specific Artifacts and Final Result

**Purpose:** Make genuine artifact propagation and Coordinator decision support teachable
without relying on serialized JSON as the primary output.

**Independent test:** Inspect every completed participant and final result through AppTest
using the complete and insufficient-evidence scenarios.

### Tests first

- [ ] T036 [TEST] [US3] Extend `tests/ui/test_streamlit_app.py` with role-specific rendered
  sections for Analyst, Solution Architect, Risk Reviewer, and Critic, including their IDs,
  upstream references, assumptions, missing information, trade-offs, complexity, risks,
  mitigations, contradictions, support status, and unresolved issues.
- [ ] T037 [TEST] [US3] Extend `tests/ui/test_streamlit_app.py` with valid empty-collection
  states and optional trusted JSON detail, proving empty means “No items,” JSON remains
  secondary, and only trusted `StageExecution` serialization is exposed.
- [ ] T038 [TEST] [US4] Extend `tests/ui/test_streamlit_app.py` with a separately identified
  final-result surface containing ordered rankings, copied validation status, conditional
  preference, principal risks, unresolved questions, criticism dispositions, qualitative
  confidence, advisory next step, and the fixed human decision-support notice.
- [ ] T039 [TEST] [US4] Extend `tests/ui/test_streamlit_app.py` with the
  `INSUFFICIENT_EVIDENCE` scenario, proving it remains a valid completed result, has no
  invented preferred alternative, and links back to inspectable process artifacts.
- [ ] T040 [TEST] [US3] [US4] Add evidence-state regression assertions to
  `tests/ui/test_streamlit_app.py` proving `PROPOSED` and `UNVERIFIED` remain exact and no
  UI copy promotes them to validated, confirmed, proven, or evidenced.

### Implementation

- [ ] T041 [US3] Implement the five role-specific trusted-output renderers in
  `src/agentic_review_board/ui/app.py`, using native text/layout components, explicit empty
  states, and no raw HTML or partial/untrusted output.
- [ ] T042 [US3] Implement stage-input provenance and the optional secondary trusted JSON
  expander in `src/agentic_review_board/ui/app.py` without displaying prompts, raw provider
  observations, runtime configuration, or exception objects.
- [ ] T043 [US4] Implement the distinct Coordinator final-result view and return-to-process
  navigation in `src/agentic_review_board/ui/app.py`, with no accept, deploy, send, apply,
  or execute action.

**Checkpoint:** Complete and insufficient-evidence reviews expose all five trusted
contributions and a clearly advisory final result while preserving exact evidence states.

---

## Phase 7: Failure, Security, and Clean Reset

**Purpose:** Make fail-closed collaboration and review isolation visible without leaking
unsafe diagnostic data.

**Independent test:** Run deterministic failure/startup scenarios and then begin a new
Review in the same AppTest session.

### Tests first

- [ ] T044 [TEST] [US5] Extend `tests/ui/test_streamlit_app.py` with Critic
  output-validation failure: Review incomplete, first three outputs inspectable, Critic
  failed with trusted category/message, Coordinator pending and blocked by Critic, and no
  final-result surface.
- [ ] T045 [TEST] [US5] Extend `tests/ui/test_streamlit_app.py` with participant/provider
  execution failure, proving it is distinguishable from output validation while exposing no
  fabricated provider cause, raw body, prompt, response, endpoint query, header, or secret.
- [ ] T046 [TEST] [US1] [US5] Extend `tests/ui/test_streamlit_app.py` with an executor that
  fails before its first observation and one that fails after a trusted snapshot; prove
  fixed sanitized startup/application errors, no fabricated failed agent, no started Review
  claim for startup failure, deterministic cleanup, and absence of injected secret markers.
- [ ] T047 [TEST] [US6] Extend `tests/ui/test_streamlit_app.py` with New Review after both
  complete and incomplete outcomes, proving all six widget values, Review/output/error,
  selected detail, and execution guard are cleared before a different input executes and no
  prior scenario artifact appears in the second Review.
- [ ] T048 [TEST] [US5] Add a rendered-content denylist regression to
  `tests/ui/test_streamlit_app.py` for private reasoning/chain-of-thought labels, complete
  prompts, raw-output markers, credentials, authorization values, and autonomous-action
  controls.

### Implementation

- [ ] T049 [US5] Implement incomplete Review, failed-stage, trusted error-category, and
  derived downstream-blocking presentation in `src/agentic_review_board/ui/app.py`, keeping
  upstream completed details available and the final view absent.
- [ ] T050 [US1] [US5] Implement outer startup/application error handling in
  `src/agentic_review_board/ui/app.py` using fixed public messages and no exception-string
  interpolation or domain failure fabrication.
- [ ] T051 [US6] Implement New Review confirmation/reset in
  `src/agentic_review_board/ui/app.py`, replacing the immutable UI state and deleting every
  review/form/detail widget key without retaining history.

**Checkpoint:** AppTest proves honest failure, safe errors, no trust-boundary leakage, and
complete same-session isolation for a subsequent Review.

---

## Phase 8: Real Composition Entry and Operator Documentation

**Purpose:** Connect the verified UI adapter to the existing configured runtime with one
deterministically closed execution scope.

**Independent test:** Exercise the root executor with substituted configuration/runtime
construction and run the production Streamlit entry without starting a model call on page
load.

### Tests first

- [ ] T052 [TEST] [US1] Create `tests/ui/test_streamlit_composition.py` with substituted
  configuration/runtime collaborators proving the root executor copies the current
  environment, loads the existing `ARB_LLM_CONFIG_PATH`, forwards the exact created Review
  and observer once, returns the exact terminal Review, requests no raw-output observer, and
  closes runtime resources on success or exception.
- [ ] T053 [TEST] [US1] Extend `tests/ui/test_streamlit_composition.py` with a production-root
  import/page-load regression proving no runtime, HTTP client, participant, or model request
  is created before explicit Start.

### Implementation and documentation

- [ ] T054 [US1] Create root `streamlit_app.py` with an import-safe `main()`, one concrete
  `ReviewExecutor` using `load_llm_runtime_config(dict(os.environ))` and a context-managed
  `ConfiguredReviewRuntime`, and one call to the public UI render entry; add no raw-output
  capture, cache, global runtime, profile editor, or provider-specific behavior.
- [ ] T055 [DOC] Update `README.md` with the approved dependency installation, local
  `ARB_LLM_CONFIG_PATH` setup, `streamlit run streamlit_app.py` command, six input-field
  conventions, process/final/failure explanation, New Review behavior, and explicit no
  persistence/resume/history guarantees.

**Checkpoint:** The production entry is inert until Start, composes the existing runtime
once per Review, always closes it, and can be launched from documented local configuration.

---

## Phase 9: Functional Acceptance and Cross-Cutting Verification

**Purpose:** Prove the complete Slice 8 behavior and preserve every prior functional
contract.

- [ ] T056 [TEST] Run the full deterministic `python -m pytest` suite with no live endpoint,
  credentials, or network requirement; all prior agent/domain/adapter tests and new UI
  scenarios must pass.
- [ ] T057 [TEST] Run `python -m ruff check .` without weakening rules or adding suppressions
  solely for UI convenience.
- [ ] T058 [TEST] Run strict `python -m mypy` over `src` and `tests`, preserving exhaustive
  role/status dispatch and avoiding untyped presentation escape hatches.
- [ ] T059 [TEST] Run `python -m pip check` and the focused architecture suite; confirm the
  only new runtime dependency is the approved Streamlit range and core imports do not
  initialize it.
- [ ] T060 [TEST] Review `src/agentic_review_board/ui/`, `streamlit_app.py`, and rendered test
  content for no LangGraph/workflow engine, API service, persistence, retry, polling,
  threads, queue, provider SDK, raw HTML, chain-of-thought, autonomous action, or secret
  surface.
- [ ] T061 [DOC] Create `specs/008-pedagogical-ui/acceptance.md` and record one delayed
  deterministic complete walkthrough plus one Critic-failure walkthrough, answering which
  agent ran, what it received/produced, why execution continued/stopped, whether a final
  result exists, and which uncertainty/evidence states remain.
- [ ] T062 [LIVE] After deterministic acceptance passes and only with explicit operator
  authorization, launch the documented local vLLM candidate/configuration and execute one
  UI walkthrough without automatic retry, fallback, mode downgrade, or output repair;
  record actual model, vLLM version, GPU, terminal Review/stage statuses, and observed UI
  result in `specs/008-pedagogical-ui/acceptance.md`, including an honest incomplete outcome
  if that is what occurs.
- [ ] T063 [TEST] Re-run `git diff --check` and review all Slice 8 changes against the
  approved specification, plan, data model, ADR-0003, Constitution, canonical architecture,
  and five-agent role model.

**Checkpoint:** Deterministic functional acceptance is complete, existing agent behavior
regresses cleanly, and any live evidence is recorded as observation rather than a quality
guarantee.

---

## Requirement Traceability

| Requirement | Primary tasks |
|---|---|
| UI-FR-001 Presentation boundary | T001, T020, T052–T054, T060 |
| UI-FR-002 One active Review | T013, T030, T033, T047, T051 |
| UI-FR-003 Complete Review input | T012, T029, T033 |
| UI-FR-004 Trusted input validation | T012, T029, T033 |
| UI-FR-005 Explicit Start | T029–T030, T033, T053–T054 |
| UI-FR-006 Canonical topology | T015, T024, T031, T035 |
| UI-FR-007 Authentic progress | T004–T011, T024, T031–T034 |
| UI-FR-008 Stage status presentation | T015–T016, T031, T034–T035 |
| UI-FR-009 Stage responsibility | T015, T032, T035 |
| UI-FR-010 Stage inputs | T016–T017, T024, T032, T042 |
| UI-FR-011 Role-specific outputs | T017, T022, T036–T043 |
| UI-FR-012 No partial trust | T005–T007, T017, T034, T041–T042 |
| UI-FR-013 Final separation | T018, T038–T039, T043 |
| UI-FR-014 Incomplete Review | T006, T026, T044–T050 |
| UI-FR-015 Dependency explanation | T016, T026, T044, T049 |
| UI-FR-016 No chain-of-thought | T017, T022, T048, T060 |
| UI-FR-017 Human authority | T018, T038–T043 |
| UI-FR-018 Safe configuration | T001, T052–T055, T060 |
| UI-FR-019 New Review isolation | T013, T027, T047, T051 |
| UI-FR-020 No required persistence | T013, T051, T055, T060 |
| UI-FR-021 Deterministic UI verification | T023–T048, T056 |
| UI-FR-022 Core independence | T001–T003, T059–T060 |
| UI-FR-023 Framework decision gate | Approved ADR-0003, T002, T059 |

## Non-Functional and Acceptance Traceability

| Requirement | Primary tasks |
|---|---|
| UI-NFR-001 Demonstration clarity | T015–T018, T031–T043, T061 |
| UI-NFR-002 Concise default presentation | T021–T022, T035–T043 |
| UI-NFR-003 Honest latency | T005, T031–T034, T061 |
| UI-NFR-004 Basic accessibility | T015, T031, T033–T043 |
| UI-NFR-005 Security by minimization | T014, T045–T050, T052–T060 |
| UI-NFR-006 Provider independence | T004–T011, T023–T028, T052–T054 |
| UI-NFR-007 Test isolation | T023–T028, T056–T059 |
| UI-NFR-008 Bounded scope | T001–T003, T060, explicit scope guard |
| UI-AC-001 Complete walkthrough | T024, T029–T043, T061 |
| UI-AC-002 Genuine propagation | T024, T032, T036, T042, T061 |
| UI-AC-003 Failure walkthrough | T026, T044–T050, T061 |
| UI-AC-004 Insufficient evidence | T025, T039, T043 |
| UI-AC-005 Evidence-state preservation | T017–T018, T040–T043 |
| UI-AC-006 New Review isolation | T027, T047, T051 |
| UI-AC-007 No live model in UI tests | T023–T048, T056 |

## User-Story Completion Gates

### US1 — Start one structured Review

Complete only after T012–T014, T029–T030, T033, T046–T047, and T052–T055 pass.

### US2 — Observe the real multi-agent process

Complete only after T004–T011, T015–T016, T024, and T031–T035 pass.

### US3 — Learn what each agent contributes

Complete only after T015–T017, T021–T024, T032, and T036–T042 pass.

### US4 — Understand success and final decision support

Complete only after T018, T025, T038–T043, and the complete acceptance walkthrough pass.

### US5 — Understand failure and dependency blocking

Complete only after T006–T007, T014, T016–T017, T026, and T044–T050 pass.

### US6 — Start a clean new Review

Complete only after T013, T027, T047, and T051 pass for both complete and incomplete prior
Reviews.

## Explicit Scope Guard

No task authorizes:

- changes to participant or domain output contracts;
- changes to role instructions or orchestration order;
- LangGraph, LangChain, workflow engines, event buses, background workers, or API services;
- database/history/session persistence;
- retry, fallback, repair, cancellation, pause, resume, or concurrent execution;
- raw model streaming or partial-output trust;
- model/profile editing or credential display;
- autonomous execution of Coordinator advice;
- private chain-of-thought presentation; or
- styling libraries, custom JavaScript, or a general design system.

## Author Review Checklist

- [x] Every approved functional requirement maps to implementation and verification tasks.
- [x] Every approved user story has an independent completion gate.
- [x] Observer functionality is proven before Streamlit rendering.
- [x] UI fixtures exercise real participants and the real orchestrator.
- [x] Complete, insufficient-evidence, validation-failure, and execution-failure scenarios
  are deterministic and offline.
- [x] Tests precede corresponding production behavior in every functional phase.
- [x] Dependency, trust, failure, security, reset, and cleanup boundaries are covered.
- [x] Cosmetic work cannot bypass a functional checkpoint.
- [x] Live-vLLM work is isolated, opt-in, no-retry, and evidence-only.
- [x] No unresolved clarification marker remains.

**Author review result:** READY FOR JOINT REVIEW.

## Approval Gate

Implementation SHALL NOT begin until:

1. the user reviews this `tasks.md`;
2. requested changes are incorporated;
3. this document is marked approved; and
4. the author performs one final cross-artifact consistency check.
