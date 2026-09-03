# ADR-0003: Streamlit for the Pedagogical Review UI

**Status:** Accepted — jointly reviewed on 2026-09-03
**Date:** 2026-09-03  
**Decision owners:** Agentic Review Board maintainers  
**Related specification:** `specs/008-pedagogical-ui/spec.md`  
**Related plan:** `specs/008-pedagogical-ui/plan.md`

## Context

The MVP requires a user interface that can collect `ReviewInput`, visibly show authentic
progress through five sequential agents, expose validated intermediate artifacts and
failures, distinguish a final result, and reset one in-memory active review.

The current application is a synchronous Python workflow with immutable `Review` snapshots.
It has no web server, frontend build system, persistence, async scheduler, or agent
framework. The chosen UI technology must preserve that simplicity and keep UI concerns out
of domain, application orchestration, participants, and provider adapters.

The canonical architecture explicitly defers the UI framework choice to an ADR.

## Decision Drivers

1. Fast implementation of a clear local browser demonstration.
2. Authentic status updates during long synchronous model calls.
3. Session-local active Review state without a database.
4. Structured forms, layouts, expandable details, and status presentation.
5. Deterministic pytest-compatible UI verification.
6. Python-only implementation and no frontend build toolchain.
7. No transfer of stage orchestration into the UI.
8. Minimal operational and dependency footprint consistent with the feature.

## Options Considered

### Option A — Streamlit

Streamlit provides Python-native forms and layouts, mutable status containers for
long-running tasks, per-session state across reruns, and the first-party `AppTest` API for
simulated UI interaction from pytest.

Its script-rerun execution model requires explicit guarding so a user interaction does not
repeat model execution. That risk is bounded through one Start event, session-held terminal
Review state, and no caching of execution results.

### Option B — Gradio Blocks

Gradio is well suited to ML demos and supports progress, queued execution, session state,
and generator-based streaming. For this process-centric UI, however, its natural event
model would require representing snapshot updates as generator outputs and wiring a broad
set of output components. Queue semantics would add behavior not required by the current
single-review synchronous application.

### Option C — FastAPI with server-rendered HTML or HTMX

This provides conventional web architecture and maximum control, but requires an HTTP API,
templates, session ownership, and polling or server-sent events for progress. It introduces
more architecture and testing surface than the PoC requires.

### Option D — Custom JavaScript frontend and Python API

This provides the greatest visual control but adds another language, build pipeline,
frontend state model, API contract, and deployment topology. It is disproportionate to the
MVP requirement.

### Option E — Terminal UI

This is lightweight but less effective for the intended browser-based pedagogical
demonstration and structured artifact inspection.

## Decision

Adopt Streamlit for Slice 8 using the constrained dependency:

```text
streamlit>=1.63,<2
```

Use only standard Streamlit components. Do not add a charting library, component pack,
custom JavaScript bundle, FastAPI service, or separate frontend.

The application remains synchronous. An optional read-only observer publishes validated
immutable `Review` snapshots; the Streamlit adapter updates its process view from those
snapshots on the same execution thread.

Streamlit imports are permitted only in the UI adapter and root UI composition entry point.
Core modules remain independently importable and testable without initializing Streamlit.

## Consequences

### Positive

- The pedagogical UI can be delivered with one language and one framework.
- Long-running stage status can be updated without a new API or worker.
- Session-local state satisfies the one-active-review requirement without persistence.
- `AppTest` supports deterministic UI interaction tests under pytest.
- The existing orchestrator, participants, Pydantic contracts, and provider adapter remain
  authoritative.

### Negative

- Streamlit becomes a substantial new runtime dependency.
- Its top-to-bottom rerun model requires careful state and duplicate-execution guards.
- Fine-grained visual layout and navigation are less controllable than a custom frontend.
- The UI is optimized for a local PoC rather than a production multi-user service.
- Browser refresh or server restart may lose the active review because persistence remains
  out of scope.

### Neutral or accepted constraints

- No background execution, cancellation, resume, or concurrent review support is added.
- No durable history is implied.
- The framework does not change agent semantics or model-provider selection.

## Security and Privacy Consequences

- Session state contains only current input, trusted Review state, and minimal safe UI
  metadata.
- Credentials, authorization headers, full prompts, raw failed model outputs, and raw
  provider exception bodies are not rendered or stored as UI state.
- Generated content is rendered without unsafe raw HTML.
- No Streamlit sharing/cloud feature is required; the default target is a local process.

## Verification

The decision is accepted only if implementation proves:

1. authentic visible transition updates from deterministic Review snapshots;
2. no duplicate execution across ordinary widget reruns;
3. complete, incomplete, and insufficient-evidence rendering with `AppTest`;
4. New Review isolation;
5. architecture tests restricting Streamlit imports to presentation/composition;
6. full offline core regression tests without UI initialization;
7. one manual local-vLLM walkthrough after deterministic verification.

## Reconsideration Triggers

Reconsider Streamlit if a future approved requirement introduces:

- multiple concurrent users or reviews;
- durable job execution or resume;
- public API-first operation;
- rich custom interaction unavailable through standard Streamlit components;
- independent frontend deployment;
- queued GPU workloads across users;
- production authentication/authorization;
- accessibility or responsive-layout requirements beyond the PoC baseline.

Gradio should be reconsidered first for generator-first ML demo or queue requirements.
FastAPI plus a dedicated frontend should be reconsidered for a production web application.

## References

- <https://docs.streamlit.io/develop/api-reference/status/st.status>
- <https://docs.streamlit.io/develop/concepts/architecture/session-state>
- <https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest>
- <https://pypi.org/project/streamlit/>
- <https://www.gradio.app/main/docs>
