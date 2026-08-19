# Agentic Review Board — Architecture

**Status:** Canonical MVP architecture  
**Version:** 0.1  
**Related documents:**

- `docs/01-product-vision.md`
- `docs/02-requirements.md`

## 1. Purpose

This document defines the minimum architecture required to satisfy the Agentic Review Board MVP requirements.

It establishes the stable architectural boundaries, responsibilities, dependency rules, execution flow, and extension points that implementation work must respect.

It intentionally avoids premature technology choices. Concrete frameworks, libraries, providers, packaging choices, retry policies, and similar implementation decisions SHALL be introduced later through Architecture Decision Records (ADRs) when evidence or implementation needs justify them.

## 2. Architectural Goals

The architecture SHALL prioritize the following qualities, in this order:

1. **Clear demonstration of genuine multi-agent collaboration.**
2. **Traceability of explicit information from input to recommendation.**
3. **Correct dependency and failure handling between review stages.**
4. **Provider-independent review logic.**
5. **Deterministic testability without a real LLM.**
6. **Minimal implementation complexity.**
7. **Ability to evolve incrementally through explicit ADRs.**

The architecture SHALL NOT optimize prematurely for production scale, distributed execution, high availability, persistence, multi-tenancy, or generic agent-platform reuse.

---

# 3. Architectural Context

Agentic Review Board has one primary human actor and one external technical dependency category: an LLM capability.

```text
┌──────────────────┐
│      User        │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────┐
│   Agentic Review Board      │
│                             │
│  Structured multi-agent     │
│  review and recommendation  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│       LLM Capability        │
│ provider/model independent  │
└─────────────────────────────┘
```

The MVP SHALL NOT depend on external document systems, databases, web search, collaboration platforms, enterprise identity systems, or autonomous tool execution.

---

# 4. Architectural Style

The MVP SHALL use a small **core-and-adapters** architecture.

The review domain and orchestration logic form the application core.

External concerns such as user interaction and LLM communication SHALL remain behind explicit boundaries so that the core does not depend on a specific UI framework or model provider.

Conceptually:

```text
                 ┌───────────────────┐
                 │    UI Adapter     │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Review Application│
                 │   / Orchestrator  │
                 └─────────┬─────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   ┌────────────┐   ┌──────────────┐  ┌──────────────┐
   │Review Model│   │Agent Contracts│  │Validation    │
   └────────────┘   └──────┬───────┘  └──────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   LLM Port    │
                    └──────┬────────┘
                           │
                           ▼
                    ┌───────────────┐
                    │ LLM Adapter   │
                    └───────────────┘
```

This diagram defines responsibility boundaries, not concrete packages or libraries.

---

# 5. Core Architectural Components

## 5.1 Review Application

The Review Application represents the use-case boundary through which the UI starts, inspects, and resets a review.

It SHALL be responsible for:

- accepting validated user review input;
- creating an isolated review execution;
- delegating review progression to the Review Orchestrator;
- exposing the current review state to the presentation layer;
- exposing completed intermediate outputs and final results;
- resetting the current review when requested.

The Review Application SHALL NOT contain provider-specific LLM code or presentation-specific rendering logic.

## 5.2 Review Orchestrator

The Review Orchestrator SHALL be the single component responsible for controlling review execution.

It SHALL:

- enforce the mandatory stage dependency order;
- invoke each review participant only when its prerequisites are valid;
- pass explicit upstream outputs to downstream participants;
- validate stage results before accepting them;
- update stage execution status;
- stop dependent execution when a mandatory stage fails;
- ensure the Coordinator runs only after all required upstream stages succeed;
- produce an incomplete review state when mandatory execution cannot continue.

The Orchestrator SHALL NOT fabricate missing outputs, bypass failed dependencies, or contain provider-specific model communication logic.

For the MVP, the logical dependency graph is:

```text
Review Input
     │
     ▼
  Analyst
     │
     ▼
Solution Architect
     │
     ▼
Risk Reviewer
     │
     ▼
   Critic
     │
     ▼
Coordinator
     │
     ▼
 Final Review
```

The implementation MAY later optimize independent work if the requirements change, but the MVP SHALL preserve the dependency semantics defined above.

## 5.3 Review Participants

The architecture SHALL expose five distinct review participant responsibilities:

- Analyst;
- Solution Architect;
- Risk Reviewer;
- Critic;
- Coordinator.

Each participant SHALL have:

- an explicit input contract;
- an explicit output contract;
- a single primary responsibility;
- no direct control over global workflow progression;
- no direct dependency on a concrete LLM provider SDK;
- no authority to execute external actions.

Detailed participant contracts and semantic responsibilities SHALL be defined in `docs/04-agent-model.md`.

## 5.4 Review Domain Model

The core SHALL represent review information explicitly rather than passing only unstructured strings between components.

At minimum, the conceptual domain SHALL contain representations for:

- **ReviewInput** — original user-provided problem and optional context;
- **Review** — one isolated review execution;
- **StageExecution** — execution state and result of one review stage;
- **StageStatus** — pending, running, completed, or failed;
- **ProblemAnalysis** — validated Analyst result;
- **SolutionAlternatives** — validated Solution Architect result;
- **RiskAssessment** — validated Risk Reviewer result;
- **CriticalReview** — validated Critic result;
- **FinalReview** — validated Coordinator result;
- **ReviewStatus** — overall review state, including complete or incomplete outcomes;
- **ReviewError** — structured failure information when execution cannot continue.

The exact class names, serialization mechanism, and validation library are implementation decisions and MAY be refined through ADRs.

## 5.5 Structured Validation Boundary

All model-generated output SHALL cross a validation boundary before becoming trusted application data.

Conceptually:

```text
LLM raw response
      │
      ▼
Parse / Decode
      │
      ▼
Schema Validation
      │
  ┌───┴────┐
 valid   invalid
  │         │
  ▼         ▼
Stage     Stage
Result    Failure
```

Invalid or incomplete required output SHALL NOT enter the trusted review state and SHALL NOT be propagated to downstream participants.

Validation belongs to the application boundary between generated model content and trusted review contracts.

## 5.6 LLM Port

The core SHALL depend on an abstract model-access capability rather than a specific model provider.

The LLM Port SHALL provide only the capability required by review participants to request model-generated structured results.

The port SHALL hide provider-specific concerns such as:

- endpoint shape;
- authentication headers;
- SDK types;
- provider-specific request objects;
- provider-specific response envelopes.

The port MAY expose provider-neutral generation parameters when genuinely needed by application behavior.

Review participants SHALL depend on this port, not on a concrete OpenAI-compatible, Anthropic, local-model, or other provider client.

## 5.7 LLM Adapter

A concrete LLM Adapter SHALL translate between the provider-neutral LLM Port and the selected runtime model endpoint.

The adapter SHALL be responsible for:

- provider-specific request construction;
- authentication integration;
- communication with the model endpoint;
- provider-specific response extraction;
- normalization of transport-level failures into application-recognizable errors.

Provider selection and concrete adapter technology SHALL be decided by ADR.

## 5.8 UI Adapter

The UI Adapter SHALL be responsible only for interaction and presentation.

It SHALL:

- collect review input;
- start a review through the Review Application;
- show stage identity and status;
- display validated intermediate outputs;
- display failures and incomplete-review state;
- display the final review when available;
- allow the user to start a new review.

The UI SHALL NOT:

- orchestrate stage dependencies;
- call individual review participants directly;
- validate model responses as a substitute for the application layer;
- depend on provider-specific LLM behavior.

The concrete UI framework SHALL be deferred to an ADR.

---

# 6. Dependency Rules

The following dependency direction is mandatory:

```text
UI Adapter
    │
    ▼
Review Application / Orchestrator
    │
    ├────────► Review Domain Contracts
    │
    └────────► Review Participants
                    │
                    ▼
                 LLM Port
                    ▲
                    │
                LLM Adapter
```

The following dependencies are forbidden in the MVP:

```text
Review Domain      ─X─► UI framework
Review Domain      ─X─► provider SDK
Review Participant ─X─► concrete provider client
UI Adapter         ─X─► provider SDK
UI Adapter         ─X─► individual stage orchestration
LLM Adapter        ─X─► UI concerns
```

The core SHALL remain usable and testable without initializing a concrete UI or real external LLM service.

---

# 7. Review State and Lifecycle

The MVP SHALL maintain one active Review state for the duration of the current execution.

Persistent storage is not required.

The conceptual lifecycle is:

```text
CREATED
   │
   ▼
RUNNING
   │
   ├──────── mandatory stage failure ───────► INCOMPLETE
   │
   └──────── all mandatory stages succeed ─► COMPLETED
```

Each stage SHALL independently transition through:

```text
PENDING → RUNNING → COMPLETED
                  └→ FAILED
```

A downstream stage SHALL remain unexecuted when any mandatory prerequisite has failed.

Starting a new review SHALL create a fresh review state with no inherited agent outputs or assumptions from the prior execution.

---

# 8. End-to-End Data Flow

## 8.1 Review Creation

```text
User Input
   │
   ▼
UI Adapter
   │
   ▼
Input Validation
   │
   ▼
Review Application
   │
   ▼
New Review State
```

The original input SHALL be preserved unchanged for traceability during the review.

## 8.2 Stage Execution

For every stage:

```text
Trusted upstream data
        │
        ▼
Review Orchestrator
        │
        ▼
Review Participant
        │
        ▼
LLM Port
        │
        ▼
LLM Adapter
        │
        ▼
Raw model result
        │
        ▼
Structured Validation
        │
        ▼
Trusted Stage Output
        │
        ▼
Review State
```

Only trusted validated stage output MAY become input for subsequent stages.

## 8.3 Final Recommendation

The Coordinator SHALL receive:

- original ReviewInput;
- ProblemAnalysis;
- SolutionAlternatives;
- RiskAssessment;
- CriticalReview.

Its validated FinalReview SHALL be stored in the active Review state and exposed to the UI as decision support.

---

# 9. Traceability Architecture

The architecture SHALL make traceability an explicit property of Review state rather than an emergent property of logs.

Each StageExecution SHALL retain, for the duration of the active review:

- participant/stage identity;
- status;
- relevant input references or structured input snapshot;
- validated output when successful;
- concise error information when failed.

The final recommendation SHALL therefore be traceable through explicit stored review artifacts:

```text
ReviewInput
   ↓
ProblemAnalysis
   ↓
SolutionAlternatives
   ↓
RiskAssessment
   ↓
CriticalReview
   ↓
FinalReview
```

This traceability MUST NOT depend on storing or exposing private chain-of-thought.

---

# 10. Failure Architecture

Failures SHALL be explicit domain/application outcomes.

The architecture SHALL distinguish, where practical, between:

- invalid user input;
- model transport/provider failure;
- malformed or schema-invalid model output;
- unexpected internal application failure.

A mandatory stage failure SHALL cause:

1. the stage to become `FAILED`;
2. dependent stages to remain unexecuted;
3. the Review to become `INCOMPLETE`;
4. previously completed results to remain inspectable;
5. no complete FinalReview to be presented.

The MVP SHALL NOT require automatic retry behavior. Retry policy, if later introduced, SHALL be decided through an ADR because it affects latency, cost, determinism, and failure semantics.

---

# 11. Security Boundaries

The architecture SHALL maintain the following minimum security boundaries:

## 11.1 Secret Boundary

Secrets SHALL be external to source code and SHALL enter only the infrastructure/runtime configuration needed by concrete adapters.

Review participants and domain contracts SHALL not contain credentials.

## 11.2 Data Boundary

The MVP SHALL process only review data supplied for the current execution.

No persistent review-history store is part of the architecture.

## 11.3 External Action Boundary

No review participant or Coordinator SHALL have a capability to execute external business or technical actions.

The architecture therefore ends at decision support:

```text
Analysis → Recommendation → Human Decision
```

and not:

```text
Analysis → Recommendation → Autonomous Action
```

---

# 12. Testability Architecture

The LLM Port SHALL be the primary substitution seam for deterministic tests.

Core tests SHALL be able to run with a fake or deterministic implementation:

```text
Review Participants
       │
       ▼
     LLM Port
      ▲    ▲
      │    │
 Fake LLM  Real Adapter
 tests      integration
```

This SHALL allow independent verification of:

- orchestration order;
- dependency enforcement;
- structured data propagation;
- validation behavior;
- failure propagation;
- incomplete-review semantics;
- Coordinator preconditions;
- final result composition.

Real-model tests SHALL remain integration tests and SHALL NOT be required for deterministic core test execution.

---

# 13. Observability for the MVP

The architecture SHALL expose sufficient execution state for the UI to show review progress.

Required observable information is application state, not a full production telemetry platform.

At minimum, the application SHALL be able to expose:

- active stage;
- status of every stage;
- completed structured outputs;
- failure information;
- overall review status;
- final review when available.

Detailed logging frameworks, distributed tracing, metrics platforms, token accounting, and production monitoring SHALL be deferred unless implementation evidence justifies them.

---

# 14. Minimal Deployment Assumptions

The MVP architecture assumes a single application process is sufficient unless a future requirement proves otherwise.

The architecture SHALL NOT require:

- microservices;
- message brokers;
- distributed workers;
- containers or orchestration platforms;
- persistent databases;
- distributed state;
- multiple backend services.

A later deployment ADR MAY introduce additional infrastructure if the demonstrator evolves beyond the MVP.

---

# 15. Explicitly Deferred Decisions

The following decisions are intentionally **not** fixed by this architecture document and SHOULD be made through ADRs when implementation reaches them:

1. UI framework and rendering technology.
2. Concrete LLM provider, model, and endpoint protocol.
3. Concrete implementation of the LLM Port and adapter.
4. Structured-output validation library and serialization mechanism.
5. Synchronous versus asynchronous application execution mechanism.
6. Prompt storage, templating, and versioning approach.
7. Retry and timeout policy for model calls.
8. Concrete package/module layout.
9. Dependency injection mechanism, if any.
10. Logging framework and level of runtime telemetry.
11. Packaging and local execution method.
12. CI configuration.
13. Whether an agent/orchestration framework is ever justified.

An ADR SHALL explain the observed need, alternatives considered, chosen option, consequences, and conditions that could cause the decision to be revisited.

---

# 16. Architecture Evolution Rules

Future architecture changes SHALL follow these rules:

### AR-001 — Requirement Before Infrastructure

New infrastructure SHALL solve an explicit requirement or an observed implementation limitation.

### AR-002 — Preserve Core Boundaries

Provider-specific and UI-specific concerns SHALL remain outside the review core.

### AR-003 — Preserve Structured Contracts

New capabilities SHALL not replace explicit validated contracts with opaque unstructured data flows.

### AR-004 — Preserve Human Authority

Architecture changes SHALL not introduce autonomous execution without an explicit product and requirements change.

### AR-005 — ADR for Material Decisions

A material architectural choice that introduces a new dependency, framework, runtime mechanism, persistence model, external integration, or execution pattern SHOULD be captured in an ADR.

### AR-006 — Evidence-Driven Complexity

The preferred evolution is the smallest change that resolves the demonstrated need.

---

# 17. MVP Architectural Completion Criteria

The architecture is correctly implemented when all of the following are true:

1. The UI can start and inspect a review without owning orchestration logic.
2. One Review Orchestrator controls mandatory stage dependencies.
3. All five review responsibilities have explicit contracts.
4. Downstream stages consume validated upstream outputs.
5. Model-generated data is validated before entering trusted Review state.
6. Review logic does not depend directly on a concrete LLM provider SDK.
7. Core workflow tests can execute using a deterministic fake LLM capability.
8. Mandatory stage failures stop dependent execution and produce an incomplete review.
9. Final recommendations remain traceable to explicit intermediate outputs.
10. No persistence, RAG, external tools, enterprise integrations, or distributed infrastructure are required for the MVP.

---

# 18. Next Architectural Document

The next canonical document SHALL be `docs/04-agent-model.md`.

It will refine the five review participants by defining, for each one:

- responsibility;
- allowed inputs;
- required structured output;
- invariants;
- prohibited behavior;
- upstream dependencies;
- downstream consumers.

That document SHALL refine agent semantics without changing the architectural dependency rules established here.
