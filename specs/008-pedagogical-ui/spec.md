# Feature Specification: Pedagogical Review UI v0.1

**Branch:** `008-pedagogical-ui`  
**Date:** 2026-09-03  
**Status:** Draft — pending joint review  
**Depends on:** Slices 1–7.2 and the validated five-participant runtime baseline  
**Canonical sources:** `docs/01-product-vision.md`, `docs/02-requirements.md`,
`docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`,
`docs/06-reference-scenarios.md`, and `.specify/memory/constitution.md`

## 1. Purpose

Slice 8 introduces the first user interface for Agentic Review Board.

The UI SHALL make the multi-agent review understandable as a visible process rather
than presenting only a final answer. A user SHALL be able to provide a review problem,
explicitly start one isolated review, observe the five participants progress through
their real dependency order, inspect each successfully validated intermediate artifact,
understand a visible failure or incomplete review, and read the final advisory result
when one exists.

The principal pedagogical question answered by this slice is:

> What did each specialized agent receive and produce, how did those artifacts flow to
> later agents, and why did the review complete or stop?

The UI is a presentation and interaction adapter over the existing review application.
It SHALL NOT become a second orchestrator, repair model output, or replace the explicit
domain and participant contracts.

## 2. Current Baseline

The approved implementation already provides:

- one immutable `ReviewInput` contract;
- five specialized participants in fixed dependency order;
- one `ReviewOrchestrator` that owns workflow progression;
- immutable `Review` and `StageExecution` state with `PENDING`, `RUNNING`,
  `COMPLETED`, and `FAILED` stage states;
- explicit validated outputs for Analyst, Solution Architect, Risk Reviewer, Critic,
  and Coordinator;
- fail-closed behavior that leaves dependent stages pending after mandatory failure;
- a distinct complete or incomplete review outcome;
- typed proposed-versus-evidenced and contradiction-support states;
- provider-neutral model access plus runtime-selected OpenAI-compatible profiles;
- deterministic substitutes and real local-vLLM execution evidence;
- command-line scripts that preserve aggregate and raw diagnostic artifacts.

There is no product UI. The current synchronous entry path exposes the final returned
`Review`, but it does not yet provide a UI-facing stream of authentic intermediate
application-state transitions while the review is running.

## 3. Scope

### 3.1 In Scope

Slice 8 SHALL add the minimum user-visible behavior required to:

1. enter every current `ReviewInput` field, with only description mandatory;
2. validate input and explicitly start one review;
3. show all five participants in their real dependency order;
4. update the process view from authentic application execution state as stages move
   between `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`;
5. identify the active stage without simulating progress through timers or animations;
6. explain each participant's responsibility, permitted upstream inputs, and output
   artifact type in concise pedagogical language;
7. allow inspection of each completed stage's validated structured output in a
   human-readable form;
8. show the explicit upstream artifacts associated with a stage so that information
   propagation is inspectable;
9. distinguish the final Coordinator result from intermediate outputs;
10. present rankings, validation status, principal risks, unresolved questions,
    qualitative confidence, and the decision-support notice when a final review exists;
11. show failed and incomplete review states without fabricating missing outputs;
12. preserve completed upstream results for inspection after a later failure;
13. allow the user to clear the active review and begin a fresh isolated review without
    restarting the application;
14. remain usable with deterministic participant substitutes so the primary UI
    behavior can be tested without a live model;
15. keep concrete UI concerns outside domain, participant, and provider-adapter code.

### 3.2 Out of Scope

Slice 8 SHALL NOT introduce:

- LangGraph, LangChain, another agent framework, or a second workflow engine;
- persistence, saved review history, user accounts, authentication, authorization,
  multi-user sessions, or collaborative editing;
- retries, resume-from-stage, cancellation, pause/approval gates, manual stage replay,
  or editing of completed participant artifacts;
- concurrent or parallel participant execution;
- RAG, browsing, external tools, autonomous actions, or execution of the Coordinator's
  suggested next step;
- model routing, fallback, provider discovery, or editing provider credentials in the
  UI;
- changes to participant responsibilities, orchestration order, or trusted output
  semantics solely for display convenience;
- silent output repair, inferred missing fields, or presentation of untrusted raw model
  output as validated stage output;
- private chain-of-thought, hidden reasoning, complete prompts, authorization headers,
  API keys, or raw provider error bodies;
- a production telemetry platform, distributed tracing system, analytics service, or
  operational dashboard;
- production deployment, responsive mobile optimization, localization, theming system,
  or a general-purpose design system;
- importing diagnostic artifacts as if they were a live active review;
- exporting, downloading, or permanently storing reviews as a required workflow.

## 4. User Stories

### US1 — Start one structured review

As a user, I want to enter a problem and optional decision context and explicitly start
a review so that I remain in control of when model execution begins.

#### Acceptance criteria

1. Description is visibly mandatory; title, objective, constraints, context, and stated
   facts are visibly optional.
2. Collection fields support zero or more distinct text entries without requiring the
   user to author JSON.
3. Submitted values are validated through the current trusted input boundary.
4. Empty or invalid mandatory input is rejected before review execution, with a concise
   field-level or form-level message.
5. Valid user text is preserved exactly by the accepted `ReviewInput`.
6. Starting execution requires an explicit user action.
7. The same user action cannot accidentally start duplicate concurrent reviews.
8. Input becomes non-editable, or changes are otherwise prevented from affecting the
   active review, once execution has started.

### US2 — Observe the real multi-agent process

As a learner or demonstrator, I want to see all five agents and their actual execution
states so that I can understand specialization, ordering, and dependency enforcement.

#### Acceptance criteria

1. The process view always identifies Analyst, Solution Architect, Risk Reviewer,
   Critic, and Coordinator as five distinct participants.
2. Participants appear in the canonical dependency order.
3. Every participant displays one exact current stage state: `PENDING`, `RUNNING`,
   `COMPLETED`, or `FAILED`.
4. Status is communicated through text or another non-color-only signal; color MAY be
   supplementary.
5. At most one stage is shown as `RUNNING` under the current sequential orchestrator.
6. Progress changes are driven by actual application state transitions, not a
   predetermined animation or estimated timer.
7. Pending stages are not presented as started.
8. The view remains visibly active during model latency rather than appearing frozen.
9. Completion of a stage becomes inspectable before or when the next stage is visibly
   active.
10. The process view identifies the overall Review as not started, running, completed,
    or incomplete using the closest current trusted application state.

### US3 — Learn what each agent contributes

As a learner, I want to select a participant and inspect its responsibility, inputs,
and validated output so that I can understand genuine information propagation rather
than seeing five unrelated answers.

#### Acceptance criteria

1. Each participant has a concise role description consistent with the Agent Model.
2. Each participant identifies the upstream artifact types it consumes.
3. For a reached stage, the user can inspect the actual stage input snapshot or explicit
   current-review references retained by `StageExecution`.
4. A completed stage exposes its validated output in role-specific, human-readable
   sections.
5. A pending stage exposes no fabricated output.
6. A running stage does not expose partial model output as a trusted result.
7. A failed stage exposes no trusted output and clearly distinguishes its concise error
   from a successful artifact.
8. The presentation preserves material IDs, provenance, references, assumptions,
   uncertainty, validation status, and support status needed to understand downstream
   use.
9. The UI does not label an alternative `EVIDENCED` or a contradiction `EVIDENCED`
   unless that exact state exists in the trusted artifact.
10. Optional technical detail MAY show a faithful serialization of trusted application
    state, but it SHALL be visually secondary to the pedagogical representation.

### US4 — Understand success and the final decision support

As a user, I want a completed review summarized separately from the process detail so
that I can understand the recommendation without losing its evidence and uncertainty.

#### Acceptance criteria

1. A final-result view is available only when a trusted `FinalReview` exists.
2. The final-result view is clearly distinguishable from intermediate agent panels.
3. Every ranked alternative shows its explicit position, identifier, justification,
   considerations, ranking-change conditions, and copied validation status.
4. A preferred alternative is shown only when the trusted final outcome includes one.
5. `INSUFFICIENT_EVIDENCE` is presented as a valid conclusion, not as a technical error.
6. Principal risks and unresolved questions remain visible.
7. Qualitative confidence is not rendered as a numeric probability or precision score.
8. The next validation step is visibly advisory and is not executable from this UI.
9. The fixed decision-support notice is prominent enough that the result cannot
   reasonably be mistaken for autonomous decision authority.
10. The user can navigate from the final result back to relevant intermediate stage
    outputs without starting another review.

### US5 — Understand failure and dependency blocking

As a learner or operator, I want a failed review to show where and why it stopped so
that fail-closed behavior is visible rather than resembling an application malfunction.

#### Acceptance criteria

1. The failed stage is visibly marked `FAILED`.
2. The overall review is visibly marked incomplete.
3. A concise sanitized error explains the available failure category, including output
   validation versus participant/provider execution when the application knows it.
4. Completed upstream stages and their trusted outputs remain inspectable.
5. Every dependent stage remains visibly `PENDING` and is explained as not executed
   because an upstream dependency failed.
6. No missing stage result, ranking, recommendation, or completion indicator is
   fabricated.
7. Invalid or raw untrusted output is not presented as a completed artifact.
8. Provider secrets, headers, sensitive endpoint parameters, complete prompts, complete
   responses, and raw nested exception details are not exposed.

### US6 — Start a clean new review

As a user, I want to start another review after a complete or incomplete execution so
that demonstrations can continue without restarting the application or contaminating
the next result.

#### Acceptance criteria

1. New-review action is available after complete and incomplete outcomes.
2. The action clearly communicates that the current in-memory review will leave the
   active view.
3. A new review begins with a fresh input form and five pending stages only after the
   next valid input is submitted.
4. No prior facts, assumptions, alternatives, risks, criticisms, ranking, errors, or
   visual selection implicitly carry into the new execution.
5. Starting a new review does not require application restart.
6. Review history is not implied when the prior review is cleared.

## 5. Functional Requirements

### UI-FR-001 — Presentation Boundary

The UI SHALL depend on an application-facing review entry point and trusted domain
state. It SHALL NOT directly invoke Analyst, Solution Architect, Risk Reviewer, Critic,
Coordinator, an LLM adapter, or a provider endpoint.

### UI-FR-002 — One Active Review

The UI SHALL represent at most one active review. It SHALL prevent accidental duplicate
execution while that review is running.

### UI-FR-003 — Complete Review Input

The UI SHALL collect the current conceptual `ReviewInput` fields:

- optional title;
- required description;
- optional objective;
- zero or more constraints;
- zero or more context items;
- zero or more stated facts.

UI-specific placeholder or help text SHALL NOT become submitted review content.

### UI-FR-004 — Trusted Input Validation

The UI MAY perform presentation-level required-field checks for immediate feedback, but
accepted review input SHALL still pass through the existing `ReviewInput` validation
boundary. The UI SHALL NOT maintain a weaker alternative input contract.

### UI-FR-005 — Explicit Start

No participant call SHALL occur until the user explicitly starts the review. Merely
editing a field, changing focus, opening a panel, or loading the page SHALL NOT start
model execution.

### UI-FR-006 — Canonical Process Topology

The process view SHALL show exactly the five mandatory stages in this order:

```text
Analyst
  → Solution Architect
  → Risk Reviewer
  → Critic
  → Coordinator
```

The view SHALL communicate dependency flow and SHALL NOT imply parallelism, optional
stages, agent-to-agent invocation, or participant-owned orchestration.

### UI-FR-007 — Authentic Progress Source

Visible progress SHALL be derived from application execution state. If the current
application entry point cannot expose intermediate transitions while executing, Slice 8
MAY add the smallest provider-neutral application observation boundary needed to expose
immutable Review snapshots or equivalent trusted transition events.

Such a boundary SHALL NOT:

- transfer orchestration decisions to the UI;
- allow the UI to mutate Review state;
- expose partial provider output;
- alter failure semantics;
- introduce persistence or a workflow framework.

The exact observation mechanism is deferred to plan and data-model review.

### UI-FR-008 — Stage Status Presentation

Each stage SHALL render its exact trusted state. The presentation SHALL provide readable
labels independent of color and SHALL use a consistent visual vocabulary across all
participants.

### UI-FR-009 — Stage Responsibility

Each stage view SHALL provide a short static responsibility description derived from the
canonical Agent Model. This description SHALL remain distinct from generated output.

### UI-FR-010 — Stage Inputs

For each reached stage, the UI SHALL make its recorded current-review inputs or explicit
input references inspectable. It SHALL distinguish user-provided input from generated
upstream artifacts.

### UI-FR-011 — Role-Specific Output Presentation

Validated stage outputs SHALL be presented using role-specific concepts:

- Analyst: objective, facts, constraints, assumptions, missing information, and
  uncertainties;
- Solution Architect: alternatives, trade-offs, assumptions, complexity, constraint
  references, validation status, and generation blockers when present;
- Risk Reviewer: risks, affected scope, severity, basis, mitigation, and residual
  uncertainty;
- Critic: criticisms, validated points, missing alternatives, contradictions with
  support status, and unresolved issues;
- Coordinator: situation summary, ranked alternatives, recommendation outcome,
  principal risks, unresolved questions, criticism dispositions, next validation step,
  confidence, and decision-support notice.

Empty valid collections SHALL be represented honestly and SHALL NOT be confused with an
unreached or failed stage.

### UI-FR-012 — No Partial Trust

Only trusted output attached to a `COMPLETED` `StageExecution` SHALL be presented as a
validated participant result. Raw provider observations or partial streaming text SHALL
not be elevated to this view.

### UI-FR-013 — Final Result Separation

The final Coordinator result SHALL have a dedicated presentation distinct from the
process and intermediate detail views. The process view SHALL remain accessible after
completion.

### UI-FR-014 — Incomplete Review Presentation

When a mandatory stage fails, the UI SHALL show:

- overall incomplete outcome;
- the failed stage and sanitized error;
- completed upstream stages;
- pending dependent stages;
- absence of a trusted final recommendation.

### UI-FR-015 — Dependency Explanation

For a pending stage downstream of failure, the UI SHALL explain that the stage did not
execute because a mandatory upstream stage failed. It SHALL NOT imply that the pending
agent failed independently.

### UI-FR-016 — No Chain-of-Thought Surface

The UI SHALL display only explicit structured artifacts, execution metadata, concise
approved errors, and static role explanations. It SHALL NOT request, derive, label, or
display private chain-of-thought.

### UI-FR-017 — Human Authority

The final view SHALL display the existing decision-support notice and SHALL not provide
an action that automatically accepts, deploys, sends, applies, or executes the generated
recommendation or validation step.

### UI-FR-018 — Safe Configuration Surface

The UI MAY display non-secret profile names or model labels already resolved by runtime
composition when safely available. It SHALL NOT display, edit, persist, or transmit API
keys, authorization headers, or sensitive endpoint query parameters.

Model/profile display is informational and SHALL NOT be required to understand the
agent process in v0.1.

### UI-FR-019 — New Review Isolation

New-review behavior SHALL create a fresh execution and clear presentation state tied to
the preceding Review. UI widget/session state SHALL NOT cause prior review artifacts to
be submitted as new input.

### UI-FR-020 — No Required Persistence

The UI SHALL function without a database or review-history repository. Loss of the
active review after browser refresh, process termination, or server restart is acceptable
for this slice and SHALL NOT be presented as durable storage.

### UI-FR-021 — Deterministic UI Verification

Primary UI behaviors SHALL be testable with deterministic review execution or trusted
fixtures, including complete, insufficient-evidence, output-validation failure, and
participant-execution failure outcomes. Normal UI tests SHALL not require vLLM, network
access, or credentials.

### UI-FR-022 — Core Independence

Domain, participant, orchestration, and provider-neutral contract tests SHALL remain
runnable without importing or initializing the concrete UI framework. UI framework
types SHALL not enter domain or participant contracts.

### UI-FR-023 — Framework Decision Gate

This specification does not select a UI framework. The technical plan SHALL compare the
smallest credible options and the selected framework SHALL be recorded in an ADR because
the canonical architecture explicitly defers that material dependency choice.

## 6. Process-View Semantics

### 6.1 Visible Stage States

| Stage state | Pedagogical meaning | Output presentation |
|---|---|---|
| `PENDING` | The agent has not executed | No generated output |
| `RUNNING` | The orchestrator is currently executing the agent | No partial output |
| `COMPLETED` | Generated output passed the participant trust boundary | Validated output is inspectable |
| `FAILED` | The agent did not produce a trusted result | Sanitized error only |

### 6.2 Visible Review Outcomes

| Review condition | Required presentation |
|---|---|
| Not started | Editable input and no claim of agent execution |
| Running | Active process view with actual stage state |
| Completed | Five completed stages plus a separate final-result view |
| Incomplete | Reached stage history, explicit failure, blocked pending stages, no final recommendation |

### 6.3 Dependency Explanation

The process view SHALL teach dependency without inventing causal reasoning. It MAY show
that a stage consumes named artifact types and that a pending stage is blocked by a
failed prerequisite. It SHALL NOT claim that a particular generated sentence caused a
later conclusion unless an explicit trusted reference supports that relationship.

### 6.4 Timing and Counts

Elapsed time, token usage, and compact item counts are not required by this slice. They
MAY be shown only when derived from reliable runtime data and clearly separated from
semantic confidence or evidence strength. Estimated progress percentages SHALL NOT be
shown as measured completion.

## 7. Error and Empty-State Behavior

### 7.1 Invalid Input

Invalid input SHALL leave the review not started. No agent SHALL appear `RUNNING` or
`FAILED` because user input validation failed before execution.

### 7.2 Startup or Composition Failure

If runtime configuration cannot create the review application, the UI SHALL show one
sanitized application-startup error and SHALL not present a Review as started. It SHALL
not expose secrets or fabricate agent-stage failure.

### 7.3 Participant Output Validation Failure

The failed stage SHALL be distinguishable as an output-validation failure when that
category is present in trusted Review state. Invalid raw output SHALL not be displayed
as if it were the stage result.

### 7.4 Participant or Provider Execution Failure

The failed stage SHALL use the available sanitized execution-failure category. The UI
SHALL not infer a more specific provider cause from absent information.

### 7.5 Empty Valid Collections

An empty valid collection SHALL be labelled as no findings/items of that type. It SHALL
not be rendered identically to unavailable output. Zero alternatives with valid
generation notes and an insufficient-evidence final result SHALL remain a valid
pedagogical path.

### 7.6 Repeated Start Interaction

Repeated clicks, framework reruns, or equivalent duplicate UI events SHALL not create a
second overlapping execution for the active review.

### 7.7 Browser or Process Loss

Because persistence is out of scope, refresh or process loss MAY discard the active
review. The UI SHALL not promise recovery or history that it does not implement.

## 8. Non-Functional Requirements

### UI-NFR-001 — Demonstration Clarity

An observer unfamiliar with the code SHOULD be able to identify the five agents, the
active or failed stage, and whether a final recommendation exists without presenter
explanation.

### UI-NFR-002 — Concise Default Presentation

The default view SHOULD favor headings, short structured fields, badges, and expandable
detail over uninterrupted serialized JSON or long prose walls.

### UI-NFR-003 — Honest Latency

The UI SHALL remain visibly responsive enough to communicate that execution continues
during local-model latency. It SHALL not invent percentage completion or guaranteed
remaining time.

### UI-NFR-004 — Basic Accessibility

Core status and outcome meaning SHALL not depend on color alone. Interactive controls
SHOULD have readable labels, and generated content SHOULD remain selectable and readable
at common desktop demonstration sizes.

### UI-NFR-005 — Security by Minimization

The UI SHALL display only the active review information required for the pedagogical
workflow. Secrets and sensitive transport details SHALL never be rendered.

### UI-NFR-006 — Provider Independence

The same UI behavior SHALL work with deterministic substitutes and any compatible
configured `LLMPort` composition. Provider-specific response shapes SHALL not affect
presentation behavior.

### UI-NFR-007 — Test Isolation

Core tests SHALL remain independent of the UI framework. UI behavior tests SHALL remain
independent of live model quality and external network availability.

### UI-NFR-008 — Bounded Scope

The UI SHALL optimize for a clear desktop PoC demonstration, not production product
completeness or framework generality.

## 9. Acceptance Scenarios

### UI-AC-001 — Complete review walkthrough

**Given** valid review input and deterministic valid participant responses,  
**when** the user explicitly starts the review,  
**then** all five stages SHALL visibly progress in dependency order,  
**and** every completed output SHALL be inspectable,  
**and** the final result SHALL be displayed separately as advisory decision support.

### UI-AC-002 — Genuine propagation walkthrough

**Given** a completed deterministic review,  
**when** the user inspects each stage,  
**then** the UI SHALL expose its recorded upstream artifact types and validated output,  
**and** the visible sequence SHALL demonstrate that downstream agents consume prior
work rather than unrelated prompts.

### UI-AC-003 — Failure walkthrough

**Given** deterministic output-validation failure at Critic,  
**when** the review runs,  
**then** Analyst, Solution Architect, and Risk Reviewer SHALL remain completed and
inspectable,  
**and** Critic SHALL be visibly failed with a concise output-validation message,  
**and** Coordinator SHALL remain pending and identified as blocked,  
**and** the Review SHALL be visibly incomplete,  
**and** no final recommendation SHALL be displayed.

### UI-AC-004 — Insufficient evidence walkthrough

**Given** a trusted completed review whose Coordinator outcome is
`INSUFFICIENT_EVIDENCE`,  
**when** the final result is displayed,  
**then** the outcome SHALL appear as valid decision support,  
**and** no preferred alternative SHALL be invented,  
**and** unresolved information and the next validation step SHALL remain visible.

### UI-AC-005 — Evidence-state preservation

**Given** alternatives marked `PROPOSED` and a contradiction marked `UNVERIFIED`,  
**when** Architect, Critic, and Coordinator outputs are presented,  
**then** those exact states SHALL remain visible and SHALL not be relabelled as
validated, confirmed, proven, or evidenced by presentation copy.

### UI-AC-006 — New review isolation

**Given** a completed or incomplete active review,  
**when** the user starts a new review and submits different valid input,  
**then** no previous input, output, error, stage selection, or result SHALL implicitly
influence the new execution.

### UI-AC-007 — No live model dependency in UI tests

**Given** the normal deterministic test environment,  
**when** UI behavior tests execute,  
**then** complete, incomplete, and insufficient-evidence views SHALL be verifiable
without vLLM, network access, credentials, or nondeterministic generation.

## 10. Assumptions and Dependencies

1. The existing five-stage dependency order remains canonical for Slice 8.
2. The UI consumes one locally composed review application and supports one active
   review at a time.
3. Runtime LLM configuration remains external to the review form.
4. Current trusted domain models remain the semantic source for display.
5. A small read-only observation boundary may be needed to expose intermediate Review
   transitions; its necessity and exact shape require plan and data-model review.
6. A UI-specific presentation/view-state model is likely to apply, but it SHALL remain
   derived from trusted Review state and SHALL not duplicate domain truth. The decision
   to create `data-model.md` is deferred until plan review as agreed.
7. One framework dependency and a corresponding ADR are expected, but the framework is
   deliberately not selected in this specification.

## 11. Success Criteria

Slice 8 is successful when:

1. a user can complete the primary workflow from problem entry through final result
   without using a CLI;
2. all five participant roles and exact execution states are visible;
3. authentic stage progression is observable during a deterministic delayed execution;
4. every completed participant artifact is inspectable in human-readable form;
5. a later failure preserves earlier completed outputs and visibly blocks dependents;
6. a completed final review is unmistakably separate from an incomplete review;
7. `PROPOSED`, `EVIDENCED`, `UNVERIFIED`, uncertainty, and insufficient evidence are
   presented without semantic promotion;
8. no private chain-of-thought, secrets, full prompts, or untrusted failed output are
   exposed;
9. a new review begins without inherited state;
10. deterministic UI tests cover complete, incomplete, insufficient-evidence, and reset
    behavior without a live model;
11. the full existing suite, strict typing, lint, and architecture checks remain green;
12. an observer can explain what each agent contributed and why execution completed or
    stopped by inspecting the UI alone.

## 12. Specification Review Checklist

### 12.1 Author Review

- [x] User value and observable behavior are specified without selecting a framework.
- [x] The process view is a first-class pedagogical capability, not decorative progress.
- [x] Authentic progress is required without moving orchestration into the UI.
- [x] Complete, incomplete, failed, empty, and insufficient-evidence paths are covered.
- [x] Intermediate outputs and upstream information flow remain inspectable.
- [x] No private chain-of-thought or invalid-output repair is introduced.
- [x] Evidence and support statuses cannot be promoted by presentation.
- [x] Human decision authority and advisory next steps are preserved.
- [x] No persistence, LangGraph, retry, or production-platform scope is introduced.
- [x] Deterministic verification remains mandatory.
- [x] UI framework selection is deferred to plan plus ADR as required by architecture.

### 12.2 Joint Review Decisions

The following proposed decisions require explicit user review before planning begins:

1. The process view is the primary view while execution is active.
2. The final result has a separate view, while process and intermediate outputs remain
   accessible after completion.
3. All current `ReviewInput` fields are supported; users do not author JSON.
4. Stage progress must be authentic and observable during execution, even if this
   requires a minimal read-only application observation boundary.
5. Raw trusted serialization is optional secondary detail, not the main experience.
6. Timing, token use, export, scenario templates, persistence, retries, and cancellation
   are not required for UI v0.1.
7. Framework selection is deferred to `plan.md` and an ADR.

## 13. Approval Gate

Planning SHALL NOT begin until:

1. the user has reviewed the purpose, scope, stories, process semantics, acceptance
   scenarios, and joint review decisions;
2. requested changes have been incorporated;
3. this document's status is changed from `Draft — pending joint review` to `Approved`;
4. the author has performed one final cross-check against the canonical sources and
   constitution.
