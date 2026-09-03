# Implementation Plan: Pedagogical Review UI v0.1

**Branch:** `008-pedagogical-ui`  
**Date:** 2026-09-03  
**Specification:** `specs/008-pedagogical-ui/spec.md` — Approved  
**Status:** Approved — jointly reviewed on 2026-09-03
**Companion decision:** `docs/adr/ADR-0003-streamlit-for-pedagogical-review-ui.md`

## 1. Objective

Implement the smallest local web UI that makes the existing five-agent review visibly
and pedagogically inspectable:

```text
Review input
    ↓ explicit start
ReviewOrchestrator
    ↓ immutable trusted Review snapshots
Process view
    Analyst → Solution Architect → Risk Reviewer → Critic → Coordinator
       ↓              ↓                ↓              ↓            ↓
    analysis      alternatives       risks         review       decision
    ↓
Separate final-result view when and only when FinalReview exists
```

The implementation will retain the current synchronous sequential orchestrator, add a
minimal read-only snapshot observation seam, and use Streamlit to render input, authentic
progress, role-specific trusted artifacts, failures, and the final decision-support result.

No workflow framework, background worker, database, API service, custom frontend, retry,
or persistence layer is introduced.

## 2. Technical Context

**Language:** Python >=3.12  
**Existing runtime dependencies:** Pydantic and HTTPX  
**Proposed UI dependency:** `streamlit>=1.63,<2`  
**Application execution:** synchronous and sequential  
**Storage:** one in-memory active review per browser session; no durable storage  
**Provider access:** unchanged OpenAI-compatible `LLMPort` composition  
**Primary target:** local desktop-browser demonstration  
**Testing:** pytest, Streamlit `AppTest`, existing deterministic participant substitutes,
Ruff, and strict mypy  
**Network in normal tests:** none

Existing trusted contracts remain the semantic source of truth:

```text
ReviewInput
Review
ReviewStatus
StageExecution
StageIdentity
StageStatus
ReviewError
ProblemAnalysis
SolutionAlternatives
RiskAssessment
CriticalReview
FinalReview
```

## 3. Constitution Check

### I. Genuine Agent Collaboration and Role Integrity — PASS

The UI exposes the existing five distinct participants, their real dependency order,
their current stage state, and their trusted outputs. It does not execute independent
prompts, combine outputs itself, or call participants directly.

### II. Structured Contracts and Validation — PASS

Only immutable `Review` snapshots and trusted `COMPLETED` stage outputs reach the primary
presentation. The UI neither parses raw provider output into domain objects nor repairs
failed content.

### III. Traceability, Uncertainty, and Explicit Evidence — PASS

The process and detail views render explicit stage inputs, outputs, identifiers,
references, assumptions, uncertainties, `validation_status`, and `support_status`.
Private chain-of-thought is neither requested nor displayed.

### IV. Human Decision Authority — PASS

The final result remains advisory, includes the existing decision-support notice, and
offers no action that executes the recommendation or next validation step.

### V. Minimal Architecture and Evidence-Driven Complexity — PASS

One UI framework addresses explicit MVP requirements for interaction, progress, and
inspectability. A single optional observer callback exposes existing state transitions.
No event bus, workflow engine, frontend build system, database, API layer, or generic
presentation framework is added.

### VI. Provider Independence and Boundary Discipline — PASS

The UI renders trusted domain/application state and receives an injected review-execution
callable from the composition root. UI package modules do not import provider adapters,
HTTPX, or provider-specific configuration/envelope types.

### VII. Deterministic Testability and Visible Failure — PASS

Snapshot emission, presentation mapping, complete/incomplete flows, insufficient evidence,
and reset behavior are tested with deterministic substitutes. Live vLLM remains optional.

### VIII. Security by Minimization and Least Capability — PASS

The UI does not display credentials, authorization material, raw provider bodies, full
prompts, or untrusted failed output. Session state contains only current UI input and trusted
review/application display state required for the active session.

### IX. Incremental Delivery and Explicit Architectural Decisions — PASS

The framework choice is recorded in proposed ADR-0003. The only core change is the
smallest observed requirement: a read-only way to publish authentic immutable execution
snapshots. Existing execution remains backward compatible when no observer is supplied.

**Constitution gate result:** PASS, subject to joint approval of this plan and ADR-0003.

## 4. Framework Decision

### 4.1 Selected option: Streamlit

Use Streamlit as the concrete UI adapter framework.

The decision is based on four Slice 8 needs:

1. a compact Python-only form and dashboard;
2. mutable status containers for long-running synchronous tasks;
3. per-browser-session state across script reruns;
4. a first-party simulated-app testing API usable from pytest.

Streamlit's documented `st.status` API supports updating a running container's label and
state. `st.session_state` retains session-local values across reruns. `AppTest` can run,
inspect, and manipulate the app without a browser. These capabilities match the current
single-process synchronous workflow without requiring a separate API or frontend runtime.

Reference documentation:

- <https://docs.streamlit.io/develop/api-reference/status/st.status>
- <https://docs.streamlit.io/develop/concepts/architecture/session-state>
- <https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest>
- <https://pypi.org/project/streamlit/>

### 4.2 Alternatives considered

| Option | Advantages | Why not selected for v0.1 |
|---|---|---|
| Gradio Blocks | Strong ML-demo components, queueing, generator streaming, session state | Authentic updates would naturally push the execution boundary toward generator outputs and queue semantics; the process-centric dashboard and role-specific artifact inspection need more component-output wiring |
| FastAPI plus server-rendered HTML/HTMX | Maximum control, conventional HTTP boundary | Requires routes, templates, event streaming or polling, explicit session state, frontend behavior, and broader integration tests |
| Custom JavaScript SPA plus API | Maximum visual flexibility | Adds a second language, build toolchain, API contract, client state, and deployment complexity without an MVP requirement |
| Terminal UI | Low dependency cost | Does not satisfy the intended browser-based pedagogical demonstration as clearly |

Gradio remains a credible reconsideration candidate if later requirements prioritize
public model endpoints, queued multi-user execution, or generator-first streaming over a
process dashboard.

### 4.3 Dependency policy

Add one constrained production dependency:

```text
streamlit>=1.63,<2
```

Rationale for a normal runtime dependency rather than an optional extra:

- Slice 8 makes the UI part of the MVP product rather than an auxiliary developer tool;
- one standard editable install should run both tests and the demonstrator;
- the Python core remains independently importable and executable because only the new
  UI package and root composition entry point import Streamlit.

No chart, graph, component, styling, or frontend package will be added. The process flow
will use standard Streamlit layout and status primitives.

## 5. Target Architecture

### 5.1 Dependency flow

```text
streamlit_app.py                         composition root
    ├── loads existing safe LLM configuration
    ├── creates ConfiguredReviewRuntime only on explicit start
    └── injects one review-execution callable
                 ↓
agentic_review_board.ui.app             interaction + rendering only
    ├── builds ReviewInput through current contract
    ├── creates Review(CREATED)
    ├── receives immutable Review snapshots
    └── renders trusted state
                 ↓
ReviewOrchestrator.execute(..., observer=...)
    ├── owns every transition and dependency decision
    ├── invokes participants in the current order
    └── publishes each resulting immutable Review snapshot
                 ↓
Existing participants → LLMPort → configured adapter
```

The composition root may import UI and infrastructure because wiring is its sole purpose.
Modules inside `agentic_review_board.ui` shall not import concrete LLM adapters or HTTPX.

### 5.2 Single-page interaction model

Use one Streamlit page with three conditional surfaces rather than a multipage router:

1. **New review** — input form before execution;
2. **Process** — primary view during execution and first view after completion/failure;
3. **Final result** — separate section/tab available only with trusted `FinalReview`.

Completed agent detail remains reachable from the Process view. A separate application
route or browser URL is not needed.

### 5.3 No background execution

The explicit Start action invokes the synchronous review on the Streamlit script thread.
The observer updates already-created page containers between model calls. This preserves:

- the current single-review sequential runtime;
- one model request at a time for the RTX 3060 profile;
- straightforward resource cleanup;
- absence of thread synchronization and cancellation semantics;
- direct mapping between visible progress and real transitions.

Streamlit reruns do not cache or repeat review execution. The active trusted result is
placed in session state only for subsequent display interactions.

## 6. Application Observation Boundary

### 6.1 Minimal contract

Introduce one provider-neutral read-only observer type at the application boundary,
provisionally:

```python
ReviewObserver = Callable[[Review], None]
```

Extend orchestration without breaking current callers:

```python
def execute(
    self,
    created_review: Review,
    *,
    observer: ReviewObserver | None = None,
) -> Review: ...
```

`ConfiguredReviewRuntime.execute` forwards the same optional observer to the orchestrator.

The exact alias/protocol location and public export are deferred to `data-model.md`.

### 6.2 Emission semantics

When an observer is present, the orchestrator publishes the newly validated immutable
`Review` immediately after each successful lifecycle transition:

1. Review `CREATED → RUNNING`;
2. each stage `PENDING → RUNNING`;
3. each stage `RUNNING → COMPLETED`; or
4. the reached stage `RUNNING → FAILED`, with Review `INCOMPLETE`.

A successful five-stage execution therefore emits eleven snapshots: Review start, five
stage starts, and five stage completions. A failure emits all preceding transitions plus
the final failure snapshot. The originally supplied `CREATED` Review need not be emitted
because the caller already owns it.

Every observed snapshot has already passed `Review` validation. No partial provider
content, untrusted participant mapping, prompt, or exception object is published.

### 6.3 Observer authority and failure

The observer is notification-only:

- it returns no orchestration instruction;
- it cannot replace the current Review;
- it cannot skip, retry, pause, reorder, or complete a stage;
- mutating a snapshot is prevented by existing frozen contracts.

An observer exception SHALL propagate to the outer caller and SHALL NOT be converted into
an agent `FAILED` stage. The UI boundary catches its own outermost presentation failure and
shows a generic sanitized application error. This keeps UI failure distinct from agent or
provider failure and prevents silent suppression.

### 6.4 Backward compatibility

With `observer=None`, `ReviewOrchestrator.execute(review)` and
`ConfiguredReviewRuntime.execute(review)` retain their existing return values, sequencing,
participant payloads, validation, and failure behavior.

## 7. UI Session and Execution Design

### 7.1 Session-owned state

Streamlit session state will hold only the minimum presentation state:

- accepted current `ReviewInput` or created `Review` while executing;
- latest trusted `Review` snapshot;
- terminal trusted `Review` when execution returns;
- current selected stage/detail panel if needed;
- a boolean or equivalent guard preventing duplicate start interaction;
- non-secret participant profile-name mapping when safely available;
- one sanitized UI-level startup/presentation error when applicable.

No raw model output, complete prompt, credential, HTTP client, persistent repository, or
cross-session global Review cache is stored.

The exact view/session types and reset invariants will be specified in `data-model.md`.

### 7.2 Runtime lifetime

On explicit Start:

1. validate and create `ReviewInput`;
2. load existing runtime configuration from the existing external mechanism;
3. create `ConfiguredReviewRuntime`;
4. expose only safe participant profile names when available;
5. execute with the Streamlit snapshot observer;
6. close the runtime deterministically after completion, incomplete result, or exception;
7. retain only trusted terminal Review and safe UI state.

The runtime and HTTP client are not cached globally and are not retained in session state.

### 7.3 New-review reset

The New Review action clears all review-specific widget/session keys and renders a fresh
form. It does not mutate or reuse the previous immutable Review. No history list is kept.

### 7.4 Input representation

Use ordinary labelled Streamlit controls:

- title: single-line optional text;
- description: required multi-line text;
- objective: optional multi-line text;
- constraints, context, and stated facts: human-editable repeated text values without
  requiring JSON.

The exact repeated-field interaction—dynamic rows versus a documented one-item-per-line
control—will be finalized in data-model/presentation design after verifying preservation
and reset behavior. Placeholder/help text is never submitted.

## 8. Presentation Design

### 8.1 Process overview

Render five ordered stage cards using standard layout primitives. Each card includes:

- canonical agent name;
- concise static responsibility;
- exact textual state;
- supplementary status icon/color;
- output summary only after `COMPLETED`;
- concise error only after `FAILED`;
- blocked explanation for pending dependents after failure.

No estimated percentage is displayed.

### 8.2 Agent detail

Role-specific renderers consume trusted domain types directly or through a small pure
presentation mapping. They show structured sections rather than defaulting to raw JSON:

| Participant | Primary sections |
|---|---|
| Analyst | Objective, facts with provenance, constraints, assumptions, missing information, uncertainties |
| Solution Architect | Alternatives, advantages/disadvantages, assumptions, complexity, relevant constraints, validation status, generation notes |
| Risk Reviewer | Risk, scope, severity, basis, mitigation, residual uncertainty, observations |
| Critic | Criticisms, validated points, missing alternatives, contradictions with support status, unresolved issues |
| Coordinator | Summary, ranked alternatives, recommendation outcome, principal risks, unresolved questions, dispositions, next step, confidence, notice |

The detail layer preserves IDs and exact evidence-state labels. Empty valid collections use
an explicit “No items reported” representation distinct from unavailable output.

### 8.3 Inputs and propagation

Each reached stage detail lists the names of its actual recorded input artifact types and
allows those immutable inputs to be inspected in compact structured sections. The UI does
not claim sentence-level causality unless an explicit trusted reference supports it.

### 8.4 Final result

When Coordinator is completed, render a separate final-result surface containing:

- recommendation outcome;
- ranked alternatives with copied validation status;
- preferred alternative only when present;
- conclusion rationale;
- principal risks;
- unresolved questions;
- next validation step;
- qualitative confidence;
- decision-support notice.

When the Review is incomplete, the final-result surface is absent and a clear incomplete
summary points back to the failed process stage.

### 8.5 Technical detail

A secondary expander may show faithful JSON serialization of trusted `Review` or completed
stage output. It is never the primary display and is never populated from raw failed model
observations.

## 9. Error and Trust-Boundary Design

### 9.1 User input errors

Catch `ReviewInput` validation failure before runtime construction and show concise safe
feedback. No Review is started and all agent states remain unclaimed.

### 9.2 Review failures

Participant output-validation and execution failures are rendered exclusively from trusted
`ReviewError.kind` and `ReviewError.message` in the returned incomplete Review.

### 9.3 Startup/composition errors

The root composition callable catches configuration/runtime-construction failures at the
outer UI boundary and returns or raises only one fixed sanitized UI-safe failure. The page
does not render raw nested exceptions, config content, endpoints, or environment values.

The exact small result/error shape is deferred to `data-model.md`.

### 9.4 Unexpected presentation errors

An unexpected UI/rendering exception is not mapped to a participant. The page displays a
generic presentation failure where possible; development diagnostics remain outside
trusted Review state and shall not be deliberately rendered to the user.

### 9.5 HTML and generated content

Prefer native Streamlit text/layout components. Generated content is rendered as text or
framework-managed Markdown with raw HTML disabled. No generated field is interpolated into
unsafe HTML, CSS, JavaScript, or executable links.

## 10. Proposed Repository Changes

Expected production/application changes:

```text
streamlit_app.py                              # composition entry point
src/agentic_review_board/
├── application/
│   ├── orchestrator.py                      # optional Review observer emissions
│   └── ports.py or observation.py           # exact observer type, if separately named
├── infrastructure/llm/
│   └── composition.py                       # forward optional Review observer
└── ui/
    ├── __init__.py
    ├── app.py                               # Streamlit interaction/session rendering
    └── presentation.py                      # pure role/status/view mapping
```

The final observer type location and whether `presentation.py` needs explicit view models
will be decided in `data-model.md`. No domain participant-output model is expected to
change.

Expected tests:

```text
tests/
├── unit/
│   ├── test_review_orchestrator.py           # exact success/failure snapshot sequence
│   ├── infrastructure/llm/
│   │   └── test_composition.py              # observer forwarding and closed runtime
│   └── ui/
│       └── test_presentation.py             # pure mappings for all five outputs/states
├── ui/
│   ├── test_streamlit_app.py                # AppTest interactions and rendered outcomes
│   └── fixtures/
│       └── deterministic_streamlit_app.py   # injected fake execution entry point
└── architecture/
    └── test_infrastructure_boundaries.py     # UI-only framework import allowance
```

Expected documentation/configuration changes:

```text
docs/adr/ADR-0003-streamlit-for-pedagogical-review-ui.md
README.md                                     # installation and local launch
pyproject.toml                                # constrained Streamlit dependency
.github/workflows/...                        # only if launch/test dependency setup changes
specs/008-pedagogical-ui/
├── spec.md
├── plan.md
├── data-model.md
└── tasks.md
```

Final filenames remain subject to data-model and task review; dependency direction does not.

## 11. Architectural Guard Updates

Existing architecture tests currently prohibit all UI framework imports and the token
`ui` across production code because UI was out of scope in prior slices. Slice 8 will
refine, not delete, those protections:

1. allow `streamlit` imports only under `agentic_review_board.ui` and the root composition
   entry point;
2. continue forbidding Streamlit, Gradio, FastAPI, Flask, and other UI/web frameworks in
   domain, application, and participant modules;
3. continue forbidding UI imports from domain, application, participants, and LLM
   infrastructure;
4. continue forbidding provider SDK/HTTP imports from the UI package;
5. update the exact runtime-dependency assertion to include the approved Streamlit range;
6. retain all existing prohibitions for persistence, retries, routing, RAG, tools, and
   out-of-scope frameworks.

## 12. Verification Strategy

### 12.1 Application observer tests

Deterministically verify:

- no-observer behavior is unchanged;
- exact eleven-snapshot successful sequence;
- exact failure sequence at each participant;
- each snapshot is a valid immutable Review;
- the emitted snapshot is the exact current snapshot used for subsequent progression;
- no raw output is emitted;
- observer exceptions propagate and are not converted into stage failure;
- `ConfiguredReviewRuntime` forwards the observer and preserves close behavior.

### 12.2 Pure presentation tests

Verify mapping for:

- all stage and review statuses;
- all five role labels and responsibilities;
- completed output type per role;
- pending/running/unavailable versus valid empty collections;
- `PROPOSED`, `EVIDENCED`, and `UNVERIFIED` exact labels;
- insufficient-evidence final output;
- blocked dependent-stage explanation;
- fixed decision-support notice;
- no accidental numeric confidence or evidence promotion.

### 12.3 Streamlit AppTest coverage

Use an injected deterministic entry point to verify:

- form labels and mandatory description;
- invalid input does not call execution;
- explicit start executes exactly once;
- five stage cards and textual statuses;
- complete final result;
- Critic failure with Coordinator pending/blocked;
- upstream outputs remain inspectable after failure;
- insufficient-evidence presentation;
- New Review clears prior state;
- no raw exception or secret-like fixture value is rendered;
- optional trusted JSON detail contains only trusted serialized state.

`AppTest` is not expected to prove browser painting timing. The authentic transition
sequence is proven at the observer boundary; one manual delayed deterministic demo confirms
that the browser visibly updates between transitions.

### 12.4 Regression and static checks

Run:

```text
python -m pytest
python -m ruff check .
python -m mypy
python -m pip check
```

The default suite remains offline and deterministic. A real-vLLM UI walkthrough is a
separate operator-authorized validation, not a CI requirement.

### 12.5 Manual pedagogical acceptance

Using one successful and one deterministic failed scenario, verify that an observer can
answer without source-code access:

1. Which agent is active or failed?
2. What did that agent receive?
3. What trusted artifact did it produce?
4. Why did the next stage run or remain pending?
5. Is there a final recommendation?
6. What uncertainty or validation state remains?
7. Does the human retain decision authority?

## 13. Data-Model Phase Applicability

`data-model.md` **does apply**, but it will remain narrow.

It shall specify:

- the observer callable/protocol and exact snapshot emission contract;
- the distinction between trusted domain Review state and UI session/view state;
- any small immutable presentation model needed for pure mapping tests;
- UI execution/startup failure representation, if one is required;
- repeated-input normalization and preservation rules;
- reset invariants;
- status and role-label mappings;
- explicit confirmation that participant/domain output contracts do not change.

It shall not introduce a second Review domain model, persisted entity, generic event bus,
workflow command, or frontend API schema.

## 14. Implementation Sequence Direction

Detailed tasks are deferred to `tasks.md`, but implementation shall follow this dependency
order:

1. approve ADR-0003 and dependency boundaries;
2. define and test the read-only observation contract;
3. implement snapshot emission and runtime forwarding;
4. define and test pure presentation mapping;
5. implement the deterministic Streamlit shell and session reset;
6. connect the real composition root;
7. add AppTest and architecture coverage;
8. document launch and validate one manual complete and failed walkthrough;
9. run all regression/static/dependency checks.

No UI implementation begins before its corresponding observer/presentation tests exist.

## 15. Risks and Mitigations

### R1 — Streamlit reruns accidentally repeat expensive execution

**Mitigation:** execute only inside the explicit Start event path, guard with session state,
store the terminal Review, and never cache the execution function or model response.

### R2 — UI becomes a second orchestrator

**Mitigation:** one injected execution callable starts the existing orchestrator; observer
return values have no control meaning; UI never invokes participants.

### R3 — Progress is cosmetic rather than authentic

**Mitigation:** render only emitted immutable Review snapshots and test the exact transition
sequence independently of visual timing.

### R4 — Presentation duplicates or changes semantic truth

**Mitigation:** pure mappings derive from exact trusted enums/models, preserve identifiers
and evidence labels, and never create replacement artifacts.

### R5 — Full Review snapshots increase session memory

**Mitigation:** retain only the latest and terminal immutable snapshots, not all transitions;
the five-stage MVP state is bounded and no cross-review history exists.

### R6 — UI exception is mistaken for agent failure

**Mitigation:** observer/presentation errors propagate outside orchestration and use a
separate sanitized UI error surface; no `ReviewError` is fabricated.

### R7 — Framework internals leak into core

**Mitigation:** Streamlit imports are restricted by architecture tests to the UI adapter and
root composition; application observer contracts use only domain/application types.

### R8 — Generated Markdown introduces unsafe rendering

**Mitigation:** prefer native text components and disable raw HTML for generated fields.

### R9 — Local vLLM latency makes the page look frozen

**Mitigation:** create all stage cards before execution and update the active stage from the
observer after every transition; do not wait for the terminal Review to render progress.

### R10 — Framework dependency expands the minimal installation

**Mitigation:** accept one constrained dependency justified by the mandatory UI slice, add
no component libraries, and keep all non-UI imports independent of Streamlit initialization.

## 16. Author Review Checklist

- [x] The plan covers every approved functional requirement and acceptance scenario.
- [x] The process view is driven by authentic validated workflow transitions.
- [x] Agent roles, dependencies, outputs, and failure semantics remain unchanged.
- [x] UI, application, participant, and provider boundaries remain explicit.
- [x] Streamlit-specific behavior is isolated to presentation and composition.
- [x] The proposal adds no persistence, workflow engine, API service, or background worker.
- [x] Security, deterministic verification, runtime cleanup, and duplicate execution are
  addressed.
- [x] The next `data-model.md` phase has a bounded purpose and will not duplicate domain
  contracts.
- [x] ADR-0003 records the framework decision and its reconsideration triggers.
- [x] No unresolved clarification marker remains.

**Author review result:** READY FOR JOINT REVIEW.

## 17. Plan Review Decisions

The following decisions require joint approval before `data-model.md` begins:

1. Select Streamlit with `streamlit>=1.63,<2` and approve ADR-0003.
2. Keep one synchronous page and avoid background threads, polling, SSE, or queues.
3. Add one optional read-only `ReviewObserver` callback to existing execution.
4. Emit exactly after each validated Review/stage transition.
5. Let observer exceptions propagate without fabricating agent failure.
6. Keep the composition root outside the UI package and inject one execution callable.
7. Store only latest/terminal trusted Review and minimal safe session state.
8. Use role-specific structured renderers with optional trusted JSON as secondary detail.
9. Treat `data-model.md` as applicable but prohibit a duplicate Review model.
10. Keep scenario templates, timing, tokens, cancellation, persistence, and export outside
    v0.1.

## 18. Approval Gate

`data-model.md` SHALL NOT begin until:

1. the user reviews this plan and proposed ADR-0003;
2. requested changes are incorporated;
3. both documents are marked approved;
4. the author performs a final consistency check against the approved spec, constitution,
   canonical architecture, and current code boundaries.
