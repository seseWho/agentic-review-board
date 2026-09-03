# Data Model: Pedagogical Review UI v0.1

**Branch:** `008-pedagogical-ui`
**Date:** 2026-09-03
**Specification:** `specs/008-pedagogical-ui/spec.md` — Approved
**Plan:** `specs/008-pedagogical-ui/plan.md` — Approved
**ADR:** `docs/adr/ADR-0003-streamlit-for-pedagogical-review-ui.md` — Accepted
**Status:** Approved — jointly reviewed on 2026-09-03, including dashboard/import revision

**Approved amendment:** During `tasks.md` consistency review, input normalization was corrected to
preserve every non-empty user value exactly, as required by US1. Whitespace is inspected
only to reject or omit values that contain no meaningful text.

## 1. Purpose

Define the smallest data and observation contracts required to present one authentic
five-agent review in Streamlit.

This document does not replace or restate participant output schemas. Existing immutable
domain contracts remain the only semantic source of truth. New types are limited to:

1. one application-level Review observer;
2. one UI-local execution boundary;
3. one normalized form draft;
4. one small UI session-state model;
5. one bounded Markdown import projection;
6. one derived stage-presentation model; and
7. one sanitized UI-error model.

No database schema, persistence DTO, API payload, event store, workflow graph, provider
response type, or duplicate Review aggregate is introduced.

## 2. Sources of Truth

### 2.1 Existing trusted domain state

| Contract | Authority | UI use |
|---|---|---|
| `ReviewInput` | User input after domain validation | Display submitted problem and provenance |
| `Review` | Complete immutable workflow snapshot | Sole source for review and process state |
| `ReviewStatus` | Review lifecycle | Overall outcome label |
| `StageExecution` | Immutable per-stage execution record | Stage status, inputs, output, and error |
| `StageIdentity` | Canonical participant identity | Order, renderer dispatch, and static metadata lookup |
| `StageStatus` | Stage lifecycle | Exact visible stage state |
| `ReviewError` | Sanitized trusted stage failure | Failed-stage message and category |
| `ProblemAnalysis` | Analyst output | Analyst renderer |
| `SolutionAlternatives` | Solution Architect output | Architect renderer |
| `RiskAssessment` | Risk Reviewer output | Risk renderer |
| `CriticalReview` | Critic output | Critic renderer |
| `FinalReview` | Coordinator output | Coordinator process detail and final-result view |

All listed contracts already use frozen Pydantic models. Slice 8 changes none of their
fields, validators, transition methods, or serialization semantics.

### 2.2 Presentation-only state

Presentation-only state may label or arrange trusted values, but it has no authority to:

- change an enum value;
- manufacture stage output or evidence;
- turn a failed or running output into a trusted result;
- infer a recommendation;
- alter the canonical stage order; or
- persist a Review beyond the current Streamlit session.

## 3. Application Observation Contract

### 3.1 Location and type

Add `src/agentic_review_board/application/observation.py` containing a public Python 3.12
type alias:

```python
from collections.abc import Callable

from agentic_review_board.domain.execution import Review

type ReviewObserver = Callable[[Review], None]
```

Export `ReviewObserver` from `agentic_review_board.application`. It is provider-neutral
and contains no Streamlit, HTTPX, model-profile, prompt, or raw-output type.

`ReviewOrchestrator.execute` and `ConfiguredReviewRuntime.execute` accept it as an optional
keyword-only argument:

```python
def execute(
    self,
    created_review: Review,
    *,
    observer: ReviewObserver | None = None,
) -> Review: ...
```

### 3.2 Snapshot rule

After every successful domain transition, the orchestrator assigns the resulting validated
`Review` as its current state and then invokes `observer(current_review)` before beginning
the next operation.

The originally supplied `CREATED` Review is not emitted because the caller already owns it.
No notification occurs before a transition validates successfully.

### 3.3 Successful sequence

| Emission | Review status | Changed stage | Stage status |
|---:|---|---|---|
| 1 | `RUNNING` | none | all remain `PENDING` |
| 2 | `RUNNING` | Analyst | `RUNNING` |
| 3 | `RUNNING` | Analyst | `COMPLETED` |
| 4 | `RUNNING` | Solution Architect | `RUNNING` |
| 5 | `RUNNING` | Solution Architect | `COMPLETED` |
| 6 | `RUNNING` | Risk Reviewer | `RUNNING` |
| 7 | `RUNNING` | Risk Reviewer | `COMPLETED` |
| 8 | `RUNNING` | Critic | `RUNNING` |
| 9 | `RUNNING` | Critic | `COMPLETED` |
| 10 | `RUNNING` | Coordinator | `RUNNING` |
| 11 | `COMPLETED` | Coordinator | `COMPLETED` |

The eleventh snapshot is the exact terminal Review returned by `execute`.

### 3.4 Failure sequence

For a failure at one-based stage position `k`, the observer receives `2k + 1` snapshots:

1. Review start;
2. start and completion for each preceding stage;
3. start of stage `k`; and
4. failure of stage `k`, with Review status `INCOMPLETE`.

The final failure snapshot is the exact terminal Review returned by `execute`. Downstream
stages remain `PENDING`; no synthetic blocked transition is added to the domain.

### 3.5 Authority and exception semantics

- Observer return values have no meaning.
- An observer cannot replace current Review state or control stage execution.
- The observer receives only frozen, validated Review values.
- The orchestrator publishes no partial participant output or exception object.
- Observer calls occur outside participant exception handlers so an observer exception
  cannot be classified as participant execution failure.
- An observer exception propagates immediately.
- An observer exception is not caught as a participant failure and creates no
  `ReviewError` or `FAILED` stage.
- `observer=None` preserves existing behavior exactly.

## 4. UI Execution Boundary

### 4.1 Injected callable

The Streamlit application accepts one UI-local protocol, defined beside the app entry
function in `ui/app.py`:

```python
from typing import Protocol

class ReviewExecutor(Protocol):
    def __call__(
        self,
        created_review: Review,
        *,
        observer: ReviewObserver,
    ) -> Review: ...
```

The root `streamlit_app.py` supplies the concrete callable. It loads configuration, creates
and deterministically closes `ConfiguredReviewRuntime`, and forwards both the created
Review and observer. The UI package never imports concrete LLM infrastructure.

`ReviewExecutor` is a local adapter seam, not a new application use case or domain port.
It therefore is not exported from the package root.

### 4.2 Executor invariants

The injected callable:

- accepts only a valid `CREATED` Review;
- invokes the existing sequential orchestrator once;
- forwards every observer notification synchronously;
- returns the exact terminal `Review` produced by orchestration;
- returns only `COMPLETED` or `INCOMPLETE` Review state;
- closes runtime resources on success, incomplete result, or exception; and
- does not retain the Review, observer, runtime, or HTTP client globally.

A non-terminal return is an execution-boundary defect. The UI reports a sanitized
application error and does not reinterpret it as a participant failure.

### 4.3 Profile metadata decision

Participant profile names are intentionally omitted from the v0.1 UI execution result and
session model. UI-FR-018 makes them optional, and they are not needed to explain agent
collaboration. Omitting them avoids broadening the execution contract. A future approved
slice may add safe labels without changing Review semantics.

## 5. Input Draft and Normalization

### 5.1 Draft model

Use one frozen UI-local dataclass for deterministic form-to-domain mapping:

```python
@dataclass(frozen=True, slots=True)
class ReviewInputDraft:
    description: str = ""
    title: str = ""
    objective: str = ""
    constraints_text: str = ""
    context_text: str = ""
    stated_facts_text: str = ""
```

This is transient form data, not a second `ReviewInput`. It exists only long enough to
build the domain value or report input validation. Streamlit widget keys may hold the same
six strings during form editing.

### 5.2 Normalization rules

`to_review_input(draft)` applies these deterministic rules:

| Field | Rule |
|---|---|
| `description` | Reject when `value.strip()` is empty; otherwise preserve the exact value |
| `title` | Convert empty or whitespace-only input to `None`; otherwise preserve the exact value |
| `objective` | Convert empty or whitespace-only input to `None`; otherwise preserve the exact value |
| repeated fields | Use `splitlines()`, discard whitespace-only lines, and preserve each remaining line exactly |

Repeated-field order, duplicates, outer whitespace on non-empty values, interior
characters, and Unicode are preserved. Line separators delimit repeated items and are not
part of those item values. No comma splitting, JSON parsing, sorting, deduplication,
semantic cleanup, or placeholder submission occurs.

The resulting values are passed to the existing `ReviewInput` constructor. Any domain
validation failure keeps the UI in form state and does not create or start a Review.

### 5.3 Markdown import projection

`MarkdownReviewCase` is one frozen transient projection with the same six conceptual values
as the editor. `decode_markdown_case` accepts at most 1 MiB, requires UTF-8 (with an
optional BOM), and parses only the documented level-one title, level-two semantic sections,
and flat collection bullets. It returns a complete value or raises `MarkdownCaseError`; no
partial projection exists.

The projection populates widget strings before those widgets are rendered. It never creates
a `Review`, starts an executor, or enters trusted domain state. A SHA-256 content digest in
widget session state prevents an unchanged upload from overwriting subsequent manual edits;
the imported bytes and digest are cleared with New Review.

## 6. UI Session State

### 6.1 Types

Use UI-local frozen dataclasses and enums, stored as one value in Streamlit session state:

```python
class UiPhase(StrEnum):
    FORM = "FORM"
    EXECUTING = "EXECUTING"
    RESULT = "RESULT"
    APPLICATION_ERROR = "APPLICATION_ERROR"


class UiErrorKind(StrEnum):
    STARTUP = "STARTUP"
    APPLICATION = "APPLICATION"


@dataclass(frozen=True, slots=True)
class UiError:
    kind: UiErrorKind
    public_message: str


@dataclass(frozen=True, slots=True)
class ReviewUiState:
    phase: UiPhase = UiPhase.FORM
    review: Review | None = None
    error: UiError | None = None
```

One `review` slot holds the latest trusted snapshot while executing and the terminal Review
after return. Separate latest/terminal copies are unnecessary and could diverge.

`UiPhase.EXECUTING` is also the duplicate-start guard; no independent boolean or lock is
stored.

### 6.2 State invariants

| Phase | `review` | `error` |
|---|---|---|
| `FORM` | `None` | `None` |
| `EXECUTING` | latest trusted Review; normally `CREATED` or `RUNNING`, briefly terminal after the final notification | `None` |
| `RESULT` | `COMPLETED` or `INCOMPLETE` | `None` |
| `APPLICATION_ERROR` before first observation | `None` | `STARTUP` |
| `APPLICATION_ERROR` after observation | latest trusted Review or `None` | `APPLICATION` |

Additional invariants:

- A `FinalReview` view exists only for a `COMPLETED` Review whose Coordinator stage is
  `COMPLETED`; existing domain validation guarantees the output type.
- An `INCOMPLETE` Review never exposes a final-result view.
- Widget values are not copied into `ReviewUiState`; after start, submitted input is
  available through `review.review_input`.
- Raw exceptions, model output, prompts, credentials, clients, runtimes, and configuration
  objects never enter session state.

### 6.3 Sanitized UI errors

`UiError` is separate from domain `ReviewError`:

| Kind | When used | Public-message rule |
|---|---|---|
| `STARTUP` | Executor fails before any observed `RUNNING` Review | Fixed safe message; no Review appears started |
| `APPLICATION` | Observer/presentation fails or executor violates its return contract | Fixed safe message; never marks an agent failed |

`public_message` is selected from application-owned constants. It is never built from
`str(exception)`, response bodies, URLs, headers, environment values, prompts, or raw
model output.

Input validation messages remain form feedback and are not stored as `UiError`.

## 7. Derived Presentation Model

### 7.1 Static stage descriptor

Define one frozen UI-local `StageDescriptor`:

```python
@dataclass(frozen=True, slots=True)
class StageDescriptor:
    display_name: str
    responsibility: str
    input_artifact_labels: tuple[str, ...]
    output_artifact_label: str
```

Store an exhaustive mapping keyed by `StageIdentity`:

| Identity | Display name | Responsibility | Inputs | Output |
|---|---|---|---|---|
| `ANALYST` | Analyst | Structure the problem, facts, assumptions, gaps, and uncertainty | `ReviewInput` | `ProblemAnalysis` |
| `SOLUTION_ARCHITECT` | Solution Architect | Propose alternatives and explicit trade-offs within the known constraints | `ReviewInput`, `ProblemAnalysis` | `SolutionAlternatives` |
| `RISK_REVIEWER` | Risk Reviewer | Identify evidence-based risks, mitigations, and residual uncertainty | `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives` | `RiskAssessment` |
| `CRITIC` | Critic | Challenge prior work, alternatives, contradictions, and unresolved issues | `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives`, `RiskAssessment` | `CriticalReview` |
| `COORDINATOR` | Coordinator | Synthesize validated artifacts into advisory decision support | `ReviewInput`, `ProblemAnalysis`, `SolutionAlternatives`, `RiskAssessment`, `CriticalReview` | `FinalReview` |

Descriptors are static explanatory metadata. They never contain generated output.

### 7.2 Dynamic stage presentation

Define one frozen derived wrapper:

```python
@dataclass(frozen=True, slots=True)
class StagePresentation:
    execution: StageExecution
    descriptor: StageDescriptor
    blocked_by: StageIdentity | None = None
```

`StagePresentation` references the exact trusted `StageExecution`; it does not copy its
status, inputs, output, or error.

It is created only through the presentation mapper, which always selects
`descriptor = STAGE_DESCRIPTORS[execution.identity]`; descriptor and execution identities
therefore cannot diverge.

`blocked_by` is derived only when:

1. the Review is `INCOMPLETE`;
2. this stage is `PENDING`; and
3. an earlier stage is `FAILED`.

Because the domain enforces one sequential failure, the first failed stage is the only
valid blocker. No blocked value is written back to the domain.

### 7.3 Exact readable labels

| Trusted value | Visible label |
|---|---|
| Review `CREATED` | Not started |
| Review `RUNNING` | Review running |
| Review `COMPLETED` | Review completed |
| Review `INCOMPLETE` | Review incomplete |
| Stage `PENDING` | Pending — not started |
| Stage `RUNNING` | Running |
| Stage `COMPLETED` | Completed — trusted output |
| Stage `FAILED` | Failed — no trusted output |

Color and icons may reinforce these labels but never replace their text.

### 7.4 Output dispatch and trust

The renderer dispatches by `StageIdentity` and then requires the domain-guaranteed output
type. A generated result is rendered only when `StageExecution.status` is `COMPLETED`.

| Stage | Required completed output |
|---|---|
| Analyst | `ProblemAnalysis` |
| Solution Architect | `SolutionAlternatives` |
| Risk Reviewer | `RiskAssessment` |
| Critic | `CriticalReview` |
| Coordinator | `FinalReview` |

For `PENDING` and `RUNNING`, the output region says that no trusted output is available.
For `FAILED`, it renders only the trusted `ReviewError` category/message. A valid empty
collection is rendered as an explicit “No items” state inside a completed output, never as
unavailable or failed.

An optional technical-detail expander may serialize the trusted `StageExecution` with
Pydantic JSON-mode serialization. It does not show raw provider observations or exception
objects and is never the primary presentation.

### 7.5 Evidence and decision labels

Existing evidence-related values are displayed verbatim or through a one-to-one readable
label. In particular:

- `PROPOSED` is never renamed validated, confirmed, or evidenced;
- `UNVERIFIED` is never renamed resolved or disproven;
- `INSUFFICIENT_EVIDENCE` is a valid completed Coordinator outcome;
- no preferred alternative is shown when the trusted result has none; and
- the existing decision-support notice is shown without an acceptance/execution action.

## 8. UI State Transitions

```text
FORM
  ├─ invalid submit ────────────────> FORM
  ├─ valid submit ──────────────────> EXECUTING (CREATED Review)
  │                                    │
  │                                    ├─ observer snapshot -> EXECUTING
  │                                    ├─ terminal return ---> RESULT
  │                                    └─ application fault -> APPLICATION_ERROR
  └─ startup fault before snapshot ---> APPLICATION_ERROR (no Review)

RESULT or APPLICATION_ERROR
  └─ New Review ────────────────────> FORM (fresh state and widget keys)
```

Transition rules:

1. Start is accepted only while phase is `FORM`.
2. A valid draft creates exactly one fresh `Review.create(review_input)`.
3. State changes to `EXECUTING` before the injected executor is called.
4. Each observer call replaces `state.review` with that exact trusted snapshot before
   attempting visual refresh.
5. A terminal return replaces `state.review` and changes phase to `RESULT`.
6. A second Start event while not in `FORM` performs no execution.
7. New Review replaces the entire `ReviewUiState` with its default and removes all six
   form-widget keys plus Markdown upload, digest, and feedback keys.
8. No transition reuses the prior Review, error, imported case, or draft values.

## 9. Data Lifecycle and Trust Matrix

| Data | Created by | Stored where | Lifetime | Trusted for semantic display |
|---|---|---|---|---|
| Form strings | User/Streamlit widgets | Session widget state | Until start/reset/session loss | No |
| Markdown upload bytes and digest | User/Streamlit uploader | Session widget state | Until upload replacement/reset/session loss | No |
| `MarkdownReviewCase` | Pure bounded parser | Local call stack | Import projection only | No |
| `ReviewInputDraft` | UI mapping | Local call stack | Input conversion only | No |
| `ReviewInput` | Existing domain validation | Inside Review | Active Review/session | Yes |
| `Review` snapshot | Existing domain transitions | One UI session-state slot | Active Review/session | Yes |
| `StagePresentation` | Pure UI mapping | Local render call | One render | Only through referenced `StageExecution` |
| `UiError` | UI boundary | UI session state | Until reset/session loss | UI status only, never domain truth |
| Raw provider output | LLM adapter trust boundary | Never UI/session | Adapter call only | No |
| Runtime/client/config | Root composition | Local execution scope | One execution | Not displayed or stored |

Browser refresh or server/process termination may discard every UI value. No recovery,
history, durable identity, or cross-session lookup is modeled.

## 10. Implementation Placement

```text
src/agentic_review_board/
├── application/
│   ├── __init__.py              # export ReviewObserver
│   ├── observation.py           # ReviewObserver only
│   └── orchestrator.py          # optional observer notifications
├── infrastructure/llm/
│   └── composition.py           # observer forwarding
└── ui/
    ├── __init__.py              # public render entry only
    ├── app.py                   # ReviewExecutor, draft/session/error state, Streamlit shell
    ├── markdown_case.py         # bounded dependency-free Markdown import projection
    └── presentation.py          # descriptors, StagePresentation, pure mappings/render helpers

streamlit_app.py                 # concrete executor composition and deterministic cleanup
```

The UI state and presentation dataclasses stay inside the UI adapter. Domain and
application modules never import them.

## 11. Validation Matrix

| Contract or invariant | Primary verification |
|---|---|
| Observer optionality and exact success sequence | Orchestrator unit tests |
| Failure snapshot count and terminal identity | Parameterized orchestrator unit tests |
| Observer exception propagation | Orchestrator unit test |
| Runtime forwarding and close behavior | Composition unit tests |
| Draft normalization and duplicate/order preservation | Pure UI unit tests |
| Markdown encoding, structure, atomicity, and widget projection | Pure parser tests plus `AppTest` |
| Exhaustive descriptors and status labels | Pure presentation unit tests |
| Blocked-stage derivation | Pure presentation unit tests |
| Completed-only output dispatch | Pure presentation unit tests |
| Session phase invariants and reset | Pure state tests plus `AppTest` |
| No duplicate execution | `AppTest` call counter |
| Startup error has no started Review | `AppTest` throwing executor |
| Complete, incomplete, and insufficient-evidence views | Deterministic `AppTest` fixtures |
| No provider/framework leakage across layers | Architecture tests |

## 12. Explicit Non-Models

Slice 8 deliberately defines none of the following:

- Review identifier or history record;
- persisted session or database entity;
- graph node, edge, checkpoint, or LangGraph state;
- progress percentage, duration, token, or cost model;
- retry, cancellation, pause, or resume command;
- queue or concurrent-job status;
- provider error/body DTO;
- raw participant response model;
- UI-owned alternative, risk, criticism, or final-review schema; or
- editable profile/configuration model.

## 13. Author Review Checklist

- [x] Every new type has a single UI-observation or presentation purpose.
- [x] Existing Review and participant-output contracts remain unchanged.
- [x] Snapshot counts match the five-stage lifecycle transitions.
- [x] Failure and observer-exception semantics do not fabricate agent state.
- [x] Form normalization is deterministic and preserves repeated-value order.
- [x] One session Review slot prevents latest/terminal divergence.
- [x] Final-result availability is derived only from trusted terminal state.
- [x] Blocked status is presentation-only and derived from canonical failure state.
- [x] Reset removes prior Review, input, Markdown import, and error state.
- [x] Secrets, runtime objects, raw output, and exception text cannot enter UI state.
- [x] No unresolved clarification marker remains.

**Author review result:** READY FOR JOINT REVIEW.

## 14. Joint Review Decisions

Approval of this document confirms:

1. `ReviewObserver` location and exact synchronous snapshot contract;
2. the injected `ReviewExecutor` shape;
3. omission of profile metadata from v0.1;
4. line-based repeated-input normalization;
5. one immutable `ReviewUiState` value with one Review snapshot slot;
6. `UiPhase` and sanitized UI-error distinctions;
7. minimal descriptor/presentation wrappers that reference rather than copy trusted state;
8. exact readable status labels and blocked-stage derivation; and
9. the absence of persistence, workflow graph, background execution, and duplicate domain
   models.

## 15. Approval Gate

`tasks.md` SHALL NOT begin until:

1. the user reviews this data model;
2. requested changes are incorporated;
3. this document is marked approved; and
4. the author performs a final consistency check against the approved specification, plan,
   ADR, canonical domain contracts, and current execution code.
