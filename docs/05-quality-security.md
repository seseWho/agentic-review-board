# Agentic Review Board — Quality & Security

**Status:** Canonical MVP quality and security baseline  
**Version:** 0.1  
**Related documents:**

- `docs/01-product-vision.md`
- `docs/02-requirements.md`
- `docs/03-architecture.md`
- `docs/04-agent-model.md`

## 1. Purpose

This document defines the minimum cross-cutting quality and security baseline for the Agentic Review Board MVP.

It establishes the conditions under which the application can be considered reliable enough for development, testing, and demonstration.

It focuses on observable guarantees rather than specific tooling. Test frameworks, validation libraries, logging libraries, CI products, secret-management products, model providers, and other implementation technologies SHALL be selected later through implementation planning or ADRs when necessary.

The document is intentionally scoped to the MVP. It does not attempt to define production-grade enterprise security, compliance, availability, or operational controls that are not required by the current Product Vision and Requirements.

---

# 2. Quality Objectives

The MVP SHALL optimize for the following quality objectives, in priority order:

1. **Correct orchestration behavior** — stages execute only when their dependencies are valid.
2. **Contract integrity** — only validated structured outputs enter trusted review state.
3. **Traceability** — final conclusions can be related to explicit review artifacts.
4. **Failure transparency** — errors and incomplete reviews are visible and never disguised as success.
5. **Deterministic testability** — core behavior can be verified without a live LLM.
6. **Agent-role integrity** — participants preserve the responsibilities and prohibitions defined in the Agent Model.
7. **Security by minimization** — the MVP handles the minimum data, privileges, secrets, and external capabilities necessary.
8. **Demonstration clarity** — the user can understand what happened without reading source code.

The MVP SHALL NOT sacrifice these properties merely to make a generated recommendation look more confident or polished.

---

# 3. Quality Model

Quality for this project is evaluated across four distinct layers:

```text
┌────────────────────────────────────┐
│  Demonstration / User Experience   │
├────────────────────────────────────┤
│  Review Workflow & Agent Behavior  │
├────────────────────────────────────┤
│  Contracts & Validation            │
├────────────────────────────────────┤
│  External LLM Integration          │
└────────────────────────────────────┘
```

A failure in a lower layer SHALL NOT be hidden by a higher layer.

For example, malformed LLM output SHALL become an explicit stage failure rather than being reformatted by the UI into a plausible-looking result.

---

# 4. Testing Strategy

## 4.1 Test Categories

The MVP SHALL distinguish at least the following test categories:

### A. Domain / Contract Tests

Verify structured review concepts and invariants independently of a real LLM.

Examples include:

- valid and invalid ReviewInput;
- allowed StageStatus transitions;
- required fields in ProblemAnalysis;
- facts and assumptions remaining distinguishable;
- valid and invalid SolutionAlternative structures;
- valid and invalid Risk structures;
- valid and invalid CriticalReview structures;
- FinalReview ranking invariants.

### B. Orchestration Tests

Verify workflow progression using deterministic participant or LLM substitutes.

These tests SHALL cover:

- mandatory execution order;
- upstream-to-downstream propagation;
- prevention of execution when prerequisites fail;
- preservation of completed upstream artifacts;
- incomplete-review semantics;
- Coordinator preconditions;
- reset/new-review isolation.

### C. Agent Contract Tests

Verify that each logical participant receives only the allowed upstream information and returns data conforming to its defined contract.

These tests SHOULD validate role boundaries such as:

- Analyst does not produce a final recommendation;
- Solution Architect does not rank alternatives;
- Risk Reviewer does not become the final decision maker;
- Critic can validate strong findings and is not forced to manufacture disagreement;
- Coordinator provides justification and considerations for each ranked alternative.

### D. Adapter / Integration Tests

Verify communication between the provider-neutral LLM Port and a concrete LLM Adapter.

These MAY require a real or representative endpoint and SHALL remain separate from deterministic core tests.

### E. End-to-End Demonstration Tests

Verify the user-visible workflow with representative scenarios.

The purpose is not to prove that every LLM answer is objectively correct. It is to prove that the application:

- performs the complete workflow;
- exposes stage progression;
- validates outputs;
- preserves traceability;
- handles uncertainty and failure correctly;
- produces a structurally complete final review when appropriate.

---

# 5. Deterministic Test Baseline

## QT-001 — No Live LLM Required for Core Tests

The full core unit/orchestration test suite SHALL run without access to a real LLM endpoint.

## QT-002 — Deterministic Substitution

The architecture SHALL provide a deterministic substitute for the LLM Port or participant responses.

The substitute SHALL allow tests to control:

- valid structured responses;
- malformed responses;
- explicit provider failures;
- missing required fields;
- stage-specific outputs;
- insufficient-evidence scenarios.

## QT-003 — Repeatability

Deterministic tests SHALL produce the same pass/fail result across repeated runs when source code and test inputs are unchanged.

## QT-004 — No Network Dependency for Core Tests

Core tests SHALL NOT require internet connectivity or access to external model services.

## QT-005 — Integration Tests Clearly Marked

Tests that require a real LLM or external endpoint SHALL be distinguishable from deterministic tests so that external availability does not make the core suite unreliable.

---

# 6. Minimum Required Test Coverage by Behavior

The MVP test suite SHALL include explicit tests for at least the following behaviors.

## 6.1 Input

- Empty description is rejected.
- Valid minimal ReviewInput is accepted.
- Optional context does not become mandatory.
- Starting a new review does not inherit previous review state.

## 6.2 Orchestration

- Analyst executes first.
- Solution Architect cannot execute without valid ProblemAnalysis.
- Risk Reviewer cannot execute without valid alternatives.
- Critic cannot execute without all required upstream artifacts.
- Coordinator cannot execute before successful Critic completion.
- Successful outputs are propagated to the correct downstream participants.

## 6.3 Failure

- Model/provider failure marks the current stage failed.
- Invalid structured output marks the current stage failed.
- A failed mandatory stage prevents dependent execution.
- Earlier successful outputs remain inspectable after later failure.
- An incomplete review cannot expose a complete FinalReview.

## 6.4 Contracts

- Facts and assumptions remain distinguishable.
- Alternative IDs/references are valid within the review.
- Risk scope is explicit.
- Criticism can reference upstream artifacts.
- Ranking positions are unique and ordered.
- Every ranked alternative has justification.
- Every ranked alternative has final considerations.
- Preferred alternative may be absent when evidence is insufficient.

## 6.5 Human Authority

- Final result contains or exposes a decision-support indication.
- No application component automatically executes the recommended next validation step.

---

# 7. Structured Output Validation

## QV-001 — Generated Data Is Untrusted

All LLM-generated structured content SHALL be considered untrusted until successfully parsed and validated against the expected participant contract.

## QV-002 — Validation Before Propagation

Validation SHALL occur before generated output is written into trusted Review state or supplied to a downstream stage.

## QV-003 — Required Fields

Missing mandatory contract fields SHALL cause validation failure.

The application SHALL NOT silently manufacture required values to repair model output.

## QV-004 — Enum / Qualitative Values

Qualitative fields defined by the MVP SHALL accept only the supported semantic values where the contract requires them, for example:

```text
LOW
MEDIUM
HIGH
```

Unexpected values SHALL be rejected or explicitly normalized by a deterministic rule defined in implementation documentation.

## QV-005 — Unknown Fields

Handling of unknown model-generated fields SHALL be deterministic.

Whether they are rejected or ignored is an implementation choice, but that behavior SHALL be consistent and testable.

## QV-006 — No Semantic Repair by UI

The UI SHALL NOT repair invalid participant output.

## QV-007 — Validation Errors Are Observable

A schema/contract validation error SHALL be distinguishable from a transport/provider error whenever the application can determine the cause.

---

# 8. AI Output Quality Rules

The application cannot guarantee factual correctness from a generative model. The MVP SHALL instead enforce quality through explicit constraints, structured artifacts, critique, and visible uncertainty.

## AQ-001 — Fact Provenance

Items represented as user-provided facts SHALL be traceable to the original ReviewInput.

## AQ-002 — Assumption Preservation

An assumption SHALL remain explicitly marked as an assumption throughout the review unless the original ReviewInput already contains evidence that establishes it as fact.

## AQ-003 — No Repetition-Based Promotion

Repeated mention by multiple participants SHALL NOT count as new evidence.

## AQ-004 — Alternative Distinctness

When multiple alternatives are required, they SHOULD differ materially in approach, trade-offs, or implementation characteristics.

Superficial wording changes SHALL NOT count as distinct alternatives.

## AQ-005 — Risk Basis

Material risks SHOULD identify the fact, assumption, constraint, or alternative property that makes them relevant.

## AQ-006 — Critic Specificity

Material criticism SHOULD target explicit review artifacts rather than provide generic statements such as "more analysis is needed" without explaining why.

## AQ-007 — No Forced Conflict

A valid CriticalReview MAY contain no material criticisms when the existing review is sufficiently supported.

The Critic SHALL still preserve unresolved issues and may record validated points.

## AQ-008 — Ranking Justification

Every Coordinator ranking position SHALL have a justification based on visible review artifacts.

## AQ-009 — Ranking Sensitivity

When material unresolved information could change the order of alternatives, the FinalReview SHOULD identify that condition.

## AQ-010 — No Unsupported Quantification

Model-generated percentages SHALL NOT be presented as calibrated probabilities unless a separate validated methodology explicitly defines them.

## AQ-011 — Qualitative Confidence Meaning

`LOW`, `MEDIUM`, and `HIGH` confidence SHALL communicate strength of support in the current review artifacts, not statistical certainty.

## AQ-012 — Insufficient Evidence Is Valid

A result stating that no recommendation can yet be justified SHALL be considered a valid and potentially high-quality outcome when evidence is insufficient.

The system SHALL NOT optimize for always producing a winner.

---

# 9. Representative Evaluation Scenarios

Before the MVP is declared ready for demonstration, it SHALL be evaluated with a small fixed set of representative scenarios.

The initial evaluation set SHOULD contain at least the following classes.

## EV-001 — Well-Specified Technical Proposal

A problem with enough context to produce multiple meaningful alternatives.

Expected observable behavior:

- facts and constraints are extracted;
- alternatives are distinct;
- risks differ by alternative;
- Critic challenges or validates specific claims;
- Coordinator ranks alternatives with explicit rationale.

## EV-002 — Underspecified Proposal

A deliberately vague problem with important missing information.

Expected observable behavior:

- Analyst exposes missing information;
- downstream stages preserve uncertainty;
- Coordinator avoids unjustified certainty;
- recommendation may be withheld.

## EV-003 — Attractive but Risky Alternative

A scenario where the simplest or most appealing option has a significant risk.

Expected observable behavior:

- Risk Reviewer exposes the downside;
- Critic verifies whether mitigation is sufficient;
- Coordinator visibly considers the risk in the ranking.

## EV-004 — Weak Upstream Assumption

A scenario containing a plausible but unsupported assumption.

Expected observable behavior:

- assumption does not become fact;
- Critic can explicitly challenge it;
- Coordinator preserves the uncertainty.

## EV-005 — No Genuine Alternative

A scenario where two or three meaningful solution approaches cannot responsibly be generated from the available information.

Expected observable behavior:

- Solution Architect does not invent superficial alternatives;
- limitation remains visible;
- final outcome requests validation or more information.

## EV-006 — Controlled Failure

A deterministic test/demo path where one stage returns malformed data or fails.

Expected observable behavior:

- failure state is visible;
- dependent stages do not run;
- previous valid outputs remain inspectable;
- no complete recommendation appears.

These scenarios MAY initially use synthetic data and deterministic LLM substitutes for repeatability.

---

# 10. Security Principles

## SP-001 — Least Capability

The MVP SHALL expose only the capabilities required to perform structured review.

Agents SHALL NOT receive external action tools, filesystem mutation tools, email tools, collaboration-platform tools, or enterprise-system credentials.

## SP-002 — Data Minimization

The application SHALL process only data required for the active review.

## SP-003 — No Required Persistence

Review input and generated outputs SHALL NOT require persistent storage for the MVP.

## SP-004 — Explicit Trust Boundaries

At minimum, the architecture SHALL treat the following as trust boundaries:

- user input entering the application;
- generated output entering trusted Review state;
- application calls leaving through the LLM Adapter;
- runtime secrets entering infrastructure configuration.

## SP-005 — Fail Closed on Invalid Generated Data

When generated output does not satisfy the expected contract, the application SHALL fail the stage rather than continue with unvalidated content.

## SP-006 — Human Approval Boundary

The final recommendation SHALL terminate at presentation to the human user.

No downstream autonomous executor SHALL exist in the MVP.

---

# 11. Secret Management

## SECQ-001 — No Secrets in Source

API keys, tokens, passwords, certificates containing private material, and other credentials MUST NOT be committed to the repository.

## SECQ-002 — Runtime Configuration

Secrets SHALL be obtained from environment variables or another explicit runtime secret mechanism.

The concrete mechanism MAY evolve through ADR.

## SECQ-003 — Example Configuration

If example configuration files are added, they SHALL contain placeholders rather than real credentials.

## SECQ-004 — Logging Redaction

Secrets SHALL NOT appear in application logs, trace output, exception messages intentionally rendered to the UI, or committed test fixtures.

## SECQ-005 — Error Sanitization

Provider errors exposed to the user SHOULD be normalized so they do not reveal authentication headers, tokens, sensitive endpoint query parameters, or other secret material.

## SECQ-006 — Repository Hygiene

A secret accidentally committed SHALL be treated as compromised and SHALL be rotated rather than considered safe merely because the commit was later removed.

---

# 12. Review Data Handling

## DH-001 — Demonstration Data

Default demonstrations SHOULD use:

- synthetic information;
- public information;
- anonymized information;
- or information explicitly approved for the demonstration context.

## DH-002 — No Confidential Data Dependency

The demonstration SHALL NOT require confidential Airbus, ISAAAC, customer, employee, research-participant, partner, or other organizational data to prove the product concept.

## DH-003 — No Hidden Data Reuse

One review SHALL NOT implicitly reuse user data from a previous review.

## DH-004 — No Persistent History Requirement

The MVP SHALL NOT maintain a persistent review history unless a future explicit requirement and ADR introduce it.

## DH-005 — Minimum Provider Disclosure

Only information required for the current participant request SHOULD be sent through the LLM Port.

The implementation SHOULD avoid including unrelated application state in prompts.

## DH-006 — Prompt Data Is Application Data

Prompt content SHALL be treated with the same sensitivity as the review data from which it is constructed.

## DH-007 — Logs Are Not a Data Store

Application logs SHALL NOT be used as an implicit persistent store for complete prompts or model outputs.

---

# 13. Prompt and Model Security Boundary

## PMS-001 — User Input Is Untrusted Content

User-supplied review text SHALL be treated as content to analyze, not as trusted application instructions capable of overriding orchestration or security rules.

## PMS-002 — Agent Responsibilities Are Application-Controlled

Role definitions, contract requirements, and orchestration order SHALL be controlled by the application, not by instructions contained inside ReviewInput.

## PMS-003 — No Tool Escalation

A model response SHALL NOT be able to grant itself new application capabilities.

## PMS-004 — Structured Output Does Not Authorize Action

Even valid generated structured output SHALL only become review data. It SHALL NOT by itself authorize an external side effect.

## PMS-005 — Model Output Is Content

Generated textual content SHALL NOT be interpreted as executable code, configuration, shell commands, or trusted markup by default.

Any future capability that executes generated artifacts SHALL require a separate requirement, threat analysis, and ADR.

---

# 14. Logging and Observability

The MVP requires execution visibility, but not a production observability platform.

## OBS-001 — Required Application-State Visibility

The system SHALL expose enough state to determine:

- current Review status;
- current or last stage;
- status of each stage;
- whether validation succeeded or failed;
- whether a FinalReview exists;
- concise failure category when available.

## OBS-002 — No Chain-of-Thought Logging

The application SHALL NOT request or intentionally log private chain-of-thought reasoning.

## OBS-003 — Structured Event Preference

Where runtime logging is implemented, important workflow events SHOULD be identifiable structurally, for example:

```text
review_started
stage_started
stage_completed
stage_failed
review_completed
review_incomplete
```

The concrete logging schema is deferred.

## OBS-004 — No Secret or Full-Prompt Default Logging

Secrets, authentication headers, and full prompts/responses SHOULD NOT be logged by default.

## OBS-005 — Demonstration Progress

The UI SHALL use application execution state to provide visible progress rather than relying on log output as the user experience.

---

# 15. Error Quality

## EQ-001 — Explicit Error Categories

Where practical, the application SHALL distinguish:

- invalid user input;
- provider/transport failure;
- structured-output parsing failure;
- contract validation failure;
- unexpected internal failure.

## EQ-002 — Actionable User Message

The user-facing error SHOULD communicate what stage failed and whether the review is incomplete without exposing unnecessary internal or secret details.

## EQ-003 — Preserve Evidence

A later-stage failure SHALL NOT erase earlier validated review artifacts from the active review.

## EQ-004 — No Fake Fallback Output

The application SHALL NOT fabricate a placeholder participant result in order to preserve the appearance of a successful end-to-end review.

## EQ-005 — Retry Is Not Implicit

Automatic retries are not required by the MVP.

If later added, retry policy SHALL be explicit and tested because it affects cost, latency, determinism, and user-visible behavior.

---

# 16. Dependency and Supply-Chain Baseline

The MVP SHOULD minimize third-party dependencies.

## DEP-001 — Dependency Justification

A new runtime dependency SHOULD solve a concrete need that cannot be met reasonably by the standard runtime or existing project dependencies.

## DEP-002 — No Agent Framework by Default

A multi-agent/orchestration framework SHALL NOT be introduced merely because the product contains multiple logical agents.

Its introduction SHALL require evidence of an implementation limitation and an ADR.

## DEP-003 — Provider SDK Isolation

If a provider SDK is used, it SHALL remain behind the LLM Adapter boundary.

## DEP-004 — Version Control

Runtime and test dependencies SHOULD be version-constrained or otherwise made reproducible according to the packaging approach later selected.

## DEP-005 — Dependency Review

Before the MVP is declared demo-ready, unnecessary dependencies SHOULD be removed and security-sensitive dependencies SHOULD be reviewed for known issues using the development ecosystem's available tooling.

The concrete scanner/tool is not fixed by this document.

---

# 17. Code Quality Baseline

This document does not prescribe a programming language style toolchain, but the implementation SHALL preserve the following properties.

## CQ-001 — Clear Boundaries

Code structure SHALL make it possible to distinguish:

- domain/review contracts;
- application/orchestration logic;
- participant logic;
- LLM port/adapter;
- UI/presentation concerns.

## CQ-002 — No Provider Leakage

Provider-specific request/response types SHALL NOT leak into domain contracts or participant semantic outputs.

## CQ-003 — No UI Orchestration

UI code SHALL NOT become the source of truth for stage dependency logic.

## CQ-004 — Small Units

Core units SHOULD remain small enough to test independently.

## CQ-005 — Explicit Failure Paths

Expected failure states SHOULD be represented explicitly rather than depending on broad exception swallowing.

## CQ-006 — No Dead Future Architecture

The MVP SHALL NOT add unused persistence, RAG, tool, plugin, event-bus, distributed-execution, or enterprise-integration abstractions solely for anticipated future use.

---

# 18. Security Non-Goals for the MVP

The following are not required for the initial demonstrator unless the product scope changes:

- enterprise SSO;
- role-based access control;
- multi-tenant isolation;
- encrypted persistent review databases;
- key-management-service integration;
- formal compliance certification;
- production SIEM integration;
- distributed audit logging;
- data-retention policies for persisted reviews;
- network segmentation architecture;
- zero-trust production deployment;
- autonomous tool sandboxing;
- execution isolation for generated code.

The absence of these controls is acceptable only because the MVP explicitly avoids the product capabilities that would require them.

If those capabilities are introduced, corresponding security requirements SHALL be added before implementation.

---

# 19. Demonstration Readiness Gates

The MVP SHALL NOT be considered ready for demonstration until all mandatory gates below are satisfied.

## Gate 1 — Core Workflow

- [ ] A valid input can start a review.
- [ ] All five mandatory stages can complete in dependency order.
- [ ] Downstream stages demonstrably receive relevant validated upstream artifacts.
- [ ] A FinalReview is produced only after successful Critic completion.

## Gate 2 — Contract Quality

- [ ] Every participant output is structurally validated.
- [ ] Invalid output cannot propagate downstream.
- [ ] Facts and assumptions remain distinguishable.
- [ ] Ranking positions contain justification and considerations.

## Gate 3 — Failure Behavior

- [ ] A controlled participant failure is visibly demonstrated in testing.
- [ ] Dependent stages do not execute after mandatory failure.
- [ ] Earlier valid outputs remain inspectable.
- [ ] No incomplete review is displayed as complete.

## Gate 4 — Deterministic Tests

- [ ] Core tests run without a live LLM.
- [ ] Orchestration tests cover success and failure paths.
- [ ] Contract validation tests cover representative invalid outputs.
- [ ] New-review isolation is tested.

## Gate 5 — Security Baseline

- [ ] No real secret is committed to the repository.
- [ ] Runtime secrets are externalized.
- [ ] Logs/UI do not expose credentials.
- [ ] Demo does not require confidential organizational data.
- [ ] Agents have no autonomous external-action capability.

## Gate 6 — AI Quality

- [ ] One underspecified scenario preserves uncertainty.
- [ ] One weak-assumption scenario demonstrates Critic behavior.
- [ ] One scenario demonstrates meaningful ranking rationale.
- [ ] The system can validly return "insufficient evidence" rather than forcing a winner.
- [ ] No unsupported numeric confidence is displayed.

## Gate 7 — Demonstration Clarity

- [ ] An observer can identify the five logical participants.
- [ ] Stage status is visible.
- [ ] Intermediate outputs are inspectable.
- [ ] Final review is clearly distinguished from intermediate analysis.
- [ ] Human decision authority is visible in the final experience.

---

# 20. Definition of Done for an Implementation Increment

Until Spec Kit produces feature-specific acceptance criteria, every implementation increment SHOULD satisfy the following minimum Definition of Done:

1. The increment implements one clearly bounded behavior.
2. Existing canonical documents are not contradicted.
3. New or changed domain/application behavior has deterministic tests.
4. Error behavior is explicit where applicable.
5. No secrets or sensitive demonstration data are introduced.
6. The increment does not introduce unjustified infrastructure.
7. Relevant tests pass before the increment is considered complete.
8. If a material architectural choice was necessary, an ADR is created or explicitly identified as required.

---

# 21. ADR Triggers from Quality or Security

An ADR SHOULD be created before making a material decision involving any of the following:

1. Concrete structured-output validation library.
2. Concrete LLM provider or provider SDK strategy when it affects architecture.
3. Retry, timeout, or resilience policy.
4. Persistent review storage.
5. Logging of prompts or model responses.
6. Authentication or user identity.
7. Addition of external tools or autonomous actions.
8. RAG or document ingestion.
9. Agent/orchestration framework adoption.
10. Execution of model-generated code or commands.
11. Storage or processing of confidential organizational information.
12. Major observability or audit infrastructure.
13. Security-sensitive deployment topology.

The ADR SHALL document the motivating need, alternatives, chosen option, consequences, and security/quality implications.

---

# 22. Quality & Security Completion Criteria

The MVP conforms to this baseline when:

1. Core behavior is deterministically testable without a live LLM.
2. Generated structured data is validated before entering trusted Review state.
3. Mandatory failures stop downstream execution visibly.
4. Agent-role boundaries defined in the Agent Model are testable and preserved.
5. Facts, assumptions, uncertainty, and criticism remain traceable across the review.
6. Secrets are externalized and absent from repository/log output.
7. No persistent confidential-data store is required.
8. No participant can autonomously execute external actions.
9. Representative evaluation scenarios demonstrate both successful recommendation and insufficient-evidence behavior.
10. All mandatory Demonstration Readiness Gates are satisfied before the MVP is presented as complete.

---

# 23. Next Project Step

With Product Vision, Requirements, Architecture, Agent Model, and Quality & Security established, the canonical MVP design baseline is complete enough to begin Spec Kit initialization.

The recommended next sequence is:

```text
Canonical project documents
        ↓
Spec Kit Constitution
        ↓
First implementation feature
        ↓
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement
```

The Constitution SHOULD distill the non-negotiable engineering principles from the canonical documents rather than duplicate all requirements.

The first implementation feature SHOULD be deliberately small and produce observable evidence quickly.
