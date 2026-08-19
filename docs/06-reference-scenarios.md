# Agentic Review Board — Reference Scenarios

**Status:** Canonical MVP reference scenarios  
**Version:** 0.1  
**Related documents:**

- `docs/01-product-vision.md`
- `docs/02-requirements.md`
- `docs/03-architecture.md`
- `docs/04-agent-model.md`
- `docs/05-quality-security.md`

## 1. Purpose

This document defines a small set of concrete reference scenarios used to validate the Agentic Review Board MVP.

The scenarios are intentionally generic and organization-neutral. They are designed to:

- make expected multi-agent behavior concrete;
- provide stable examples for product reviews and demonstrations;
- support future prompt, test, and UI design;
- verify that the system remains generic rather than overfitted to a single domain;
- validate process properties without prescribing one exact LLM answer.

These scenarios are examples, not additional product requirements.

The system SHALL NOT be considered correct only when it produces the same alternative names, wording, or final ranking shown here.

The important outcome is that the observable behavior remains consistent with the Product Vision, Requirements, Architecture, Agent Model, and Quality & Security baseline.

---

# 2. Evaluation Principle

Reference scenarios SHALL be evaluated primarily through **behavioral properties**, not exact generated prose.

For example, a scenario may expect that:

- the Analyst identifies missing information;
- alternatives are materially distinct;
- risks are tied to specific alternatives;
- unsupported assumptions remain visible;
- the Critic challenges weak reasoning;
- the Coordinator explains ranking decisions;
- uncertainty survives into the final review when unresolved.

The scenario SHALL NOT require that one specific alternative always wins unless a later deterministic test explicitly defines such behavior.

---

# 3. Scenario 1 — Internal Technical Knowledge Assistant

## 3.1 Scenario Intent

Validate the complete happy-path review for a well-defined technical proposal with multiple plausible solution approaches.

This is the primary reference scenario for demonstrating the full workflow.

## 3.2 Review Input

### Title

Internal Technical Knowledge Assistant

### Description

A medium-sized engineering organization wants to introduce an internal AI assistant that helps technical staff find and understand information contained in internal technical documentation.

The initial version should be small enough to demonstrate quickly and should avoid creating excessive operational overhead.

### Objective

Identify the most suitable initial approach for delivering a useful internal technical assistant while maintaining reasonable control over data, complexity, and operational effort.

### Constraints

- Internal documentation may contain sensitive technical information.
- The initial implementation should remain deliberately small.
- The team has limited capacity to operate complex infrastructure.
- The solution should be easy to demonstrate and evaluate incrementally.
- Human users remain responsible for engineering decisions.

### Known Context

- The organization already has internal technical documentation.
- The proposal is for decision support and information access, not autonomous engineering action.

## 3.3 Expected Analyst Behavior

The Analyst SHOULD:

- identify the objective of providing controlled technical knowledge assistance;
- preserve the explicit constraints around sensitive information, team capacity, and MVP size;
- distinguish known facts from assumptions about document volume, formats, update frequency, model availability, or infrastructure;
- identify missing information that could materially affect architecture choice.

Examples of useful missing information MAY include:

- expected document volume;
- document formats;
- update frequency;
- expected number of users;
- latency expectations;
- available local compute;
- approved external model services;
- required access-control behavior.

The Analyst SHALL NOT silently assume answers to these questions.

## 3.4 Expected Solution Architect Behavior

The Solution Architect SHOULD generate two or three materially distinct approaches.

Possible classes of alternatives MAY include, but are not limited to:

- predominantly local model/infrastructure approach;
- managed external model service with controlled integration;
- hybrid approach combining local data handling with managed model capability.

The exact alternatives are not prescribed.

Each alternative SHOULD have clearly different trade-offs in areas such as:

- operational complexity;
- model capability;
- data exposure;
- deployment effort;
- scalability;
- vendor dependency.

The Solution Architect SHALL NOT automatically assume that "local" means "secure" or that "managed" means "insecure".

## 3.5 Expected Risk Reviewer Behavior

The Risk Reviewer SHOULD identify risks that differ meaningfully between alternatives.

Relevant categories MAY include:

- sensitive information leaving controlled boundaries;
- operational burden of hosting models locally;
- insufficient model quality;
- vendor dependency;
- document freshness;
- incorrect or hallucinated responses;
- user over-reliance on generated answers;
- access-control limitations.

Risks SHOULD identify affected alternatives or overall proposal scope where practical.

## 3.6 Expected Critic Behavior

The Critic SHOULD challenge unsupported claims or simplistic reasoning.

Useful criticisms MAY include:

- assuming a local deployment is automatically safer without considering operational security;
- assuming external model usage is acceptable without knowing data-handling constraints;
- understating maintenance effort for locally hosted models;
- overstating solution quality when document ingestion requirements remain unknown;
- failing to distinguish demonstration needs from production needs.

The Critic MAY also explicitly validate well-supported findings.

## 3.7 Expected Coordinator Behavior

The Coordinator SHOULD:

- rank available alternatives when sufficient information exists;
- explain the position assigned to every alternative;
- identify the most decision-relevant trade-offs;
- preserve unresolved security or infrastructure questions;
- propose one concrete next validation step.

A reasonable next validation step might involve a small proof of concept using synthetic or approved sample documentation, but the exact recommendation is not prescribed.

## 3.8 Behavioral Success Criteria

The scenario is successful when:

- the five roles are visibly distinct;
- alternatives are materially different;
- sensitive-data concerns appear in the analysis;
- operational complexity is considered rather than ignored;
- at least one assumption or weak conclusion is critically reviewed when present;
- ranking rationale is explicit;
- the final result remains decision support rather than autonomous action.

---

# 4. Scenario 2 — Automated Opportunity Screening

## 4.1 Scenario Intent

Validate that the same multi-agent model works in a project/innovation context rather than only in software architecture decisions.

The scenario should demonstrate domain generality.

## 4.2 Review Input

### Title

Automated Opportunity Screening

### Description

A small research and innovation organization is considering building an AI-assisted capability that periodically reviews publicly available funding opportunities and helps staff identify which opportunities deserve further human evaluation.

The organization wants visible value quickly and has limited time for maintaining complex systems.

### Objective

Determine the most suitable initial approach for reducing manual screening effort while preserving human review of eligibility and strategic fit.

### Constraints

- The team is small.
- Budget and operational capacity are limited.
- Information about opportunities changes over time.
- Incorrect eligibility conclusions could waste significant staff effort.
- Final decisions about whether to pursue an opportunity must remain human-controlled.
- The first version should demonstrate value quickly.

### Known Context

- Opportunity information is publicly available.
- Human staff currently perform screening manually.

## 4.3 Expected Analyst Behavior

The Analyst SHOULD identify:

- reduction of screening effort as the primary objective;
- limited team capacity as a key constraint;
- human eligibility review as mandatory;
- information freshness as an important consideration;
- missing information such as number of sources, screening volume, frequency, language requirements, or criteria used for strategic fit.

The Analyst SHALL NOT assume that all opportunities have standardized formats or reliable metadata.

## 4.4 Expected Solution Architect Behavior

The Solution Architect SHOULD identify materially different levels of automation.

Possible classes MAY include:

- manual discovery with AI-assisted evaluation;
- automated opportunity collection followed by AI-assisted screening;
- incremental hybrid workflow where automation is introduced only after screening criteria are validated.

The exact implementation technologies SHALL NOT be assumed by the scenario.

The alternatives SHOULD expose trade-offs between:

- speed to value;
- maintenance effort;
- automation breadth;
- data freshness;
- false-positive/false-negative exposure;
- complexity.

## 4.5 Expected Risk Reviewer Behavior

Relevant risks MAY include:

- stale opportunity information;
- incorrect eligibility interpretation;
- missing relevant opportunities;
- false-positive recommendations;
- source format changes;
- maintenance overhead;
- excessive automation before screening criteria are stable;
- users treating AI output as authoritative.

The reviewer SHOULD differentiate between risks introduced by broader automation and risks already present in manual screening.

## 4.6 Expected Critic Behavior

The Critic SHOULD challenge assumptions such as:

- more automation necessarily producing more value;
- public availability implying stable or easy-to-process data;
- automated screening being reliable before explicit human criteria exist;
- the organization having enough volume to justify a complex ingestion system;
- using generated relevance scores as objective measurements without a defined methodology.

The Critic MAY conclude that a simpler alternative is better supported by current evidence without itself making the final ranking.

## 4.7 Expected Coordinator Behavior

The Coordinator SHOULD:

- rank the alternatives by suitability for the stated constraints;
- justify each ranking position;
- explicitly discuss the speed-to-value versus automation trade-off;
- retain uncertainty around criteria quality and information freshness;
- suggest one next experiment that can generate evidence quickly.

The exact preferred alternative is intentionally unspecified.

## 4.8 Behavioral Success Criteria

The scenario is successful when:

- the system demonstrates usefulness outside a purely technical architecture domain;
- limited organizational capacity materially influences the alternatives;
- freshness and eligibility risks are visible;
- the Critic questions unjustified automation assumptions;
- the Coordinator ranks alternatives rather than simply listing them;
- human review remains explicitly required.

---

# 5. Scenario 3 — Proposed Migration to Microservices

## 5.1 Scenario Intent

Validate that the system can recognize insufficient evidence and avoid producing an unjustifiably confident recommendation.

This scenario intentionally provides very little context.

## 5.2 Review Input

### Title

Migration to Microservices

### Description

We should replace our current application architecture with microservices.

### Objective

Determine whether migrating to microservices is an appropriate next architectural step.

## 5.3 Deliberately Missing Context

The input does not specify:

- current architecture;
- actual problems with the existing system;
- deployment model;
- scale or performance limitations;
- team size;
- operational capabilities;
- release frequency;
- coupling problems;
- reliability requirements;
- organizational boundaries;
- cost constraints;
- reason the migration was proposed.

These omissions are intentional.

## 5.4 Expected Analyst Behavior

The Analyst SHOULD identify the lack of evidence supporting the proposed migration.

It SHOULD explicitly surface material missing information, including the reason for architectural change.

The phrase "we should migrate" SHALL NOT be converted into evidence that microservices are required.

The Analyst SHOULD distinguish:

- fact: a migration has been proposed;
- assumption: microservices would improve the current situation;
- missing evidence: what current limitation they are expected to solve.

## 5.5 Expected Solution Architect Behavior

The Solution Architect SHOULD avoid inventing several detailed microservice architectures solely to satisfy the request.

Reasonable behavior MAY include presenting conditional high-level alternatives such as:

- retain and improve the current architecture;
- modularize incrementally;
- consider selective service extraction;
- consider broader microservice migration only if specific scaling or organizational constraints are demonstrated.

Alternatively, it MAY state that meaningful alternatives cannot yet be compared responsibly without more context.

The scenario SHALL be considered unsuccessful if the Architect confidently prescribes technologies or infrastructure unsupported by the input.

## 5.6 Expected Risk Reviewer Behavior

The Risk Reviewer SHOULD identify risks associated with making a major architectural migration without a demonstrated problem.

Relevant risks MAY include:

- increased operational complexity;
- distributed-system failure modes;
- deployment and observability overhead;
- team capability mismatch;
- migration cost;
- unnecessary architectural fragmentation;
- solving a problem that has not been defined.

The reviewer SHOULD also recognize that insufficient information limits risk assessment quality.

## 5.7 Expected Critic Behavior

The Critic SHOULD strongly challenge the central unsupported assumption:

> Microservices are the appropriate solution even though the underlying architectural problem has not been established.

It SHOULD identify if upstream alternatives or claims have become overly specific despite missing evidence.

It MAY validate conclusions that recommend gathering evidence before committing to migration.

## 5.8 Expected Coordinator Behavior

The Coordinator SHOULD NOT force a confident preferred architecture when the available evidence is insufficient.

A valid final outcome SHOULD include:

- explicit statement that a migration recommendation is not currently justified;
- key missing information;
- explanation of why the evidence gap materially affects the decision;
- a concrete next validation step.

A suitable next validation step MAY be to identify and document the actual architectural limitations motivating the proposed migration.

The exact wording is not prescribed.

## 5.9 Behavioral Success Criteria

The scenario is successful when:

- the system resists the framing bias contained in the proposal;
- the Analyst identifies substantial missing information;
- assumptions remain assumptions;
- the Architect avoids unjustified detailed solution design;
- the Critic challenges the unsupported premise;
- the Coordinator can return an insufficient-evidence outcome;
- no unsupported technology recommendation is presented as authoritative.

---

# 6. Cross-Scenario Expectations

Across all three reference scenarios, the following properties SHOULD remain consistent.

## RS-001 — Role Separation

Each participant performs its defined semantic responsibility rather than collapsing into a generic reviewer.

## RS-002 — Explicit Information Flow

Downstream outputs reflect relevant upstream artifacts.

## RS-003 — No Assumption Laundering

Repeated assumptions remain visibly unsupported unless the original input establishes them as facts.

## RS-004 — Critical Review

Critic findings are specific to visible artifacts and are not manufactured merely to create disagreement.

## RS-005 — Ranking Quality

When ranking is appropriate, every position has a justification and final considerations.

## RS-006 — Valid Abstention

The system can conclude that available evidence is insufficient rather than always choosing a winner.

## RS-007 — Human Authority

No scenario ends with autonomous execution of the recommendation.

## RS-008 — Organization Neutrality

No scenario requires organization-specific systems, policies, confidential data, or proprietary processes.

---

# 7. Use During Development

These scenarios SHOULD be reused during future development in several ways.

## 7.1 Product Review

Use them to verify that a proposed feature remains aligned with intended product behavior.

## 7.2 Prompt Development

Use them as representative inputs when evaluating participant prompt quality.

Prompts SHALL NOT include hard-coded answers derived from these scenarios.

## 7.3 Deterministic Tests

Simplified versions MAY be represented as deterministic test fixtures for orchestration and contract validation.

## 7.4 Real-Model Evaluation

The complete scenario text MAY be used in manual or automated integration evaluations against selected models.

Evaluation SHOULD focus on behavioral properties rather than exact wording.

## 7.5 Demonstration

Scenario 1 is the preferred default end-to-end demonstration candidate.

Scenario 2 demonstrates domain generality.

Scenario 3 demonstrates uncertainty handling and responsible refusal to over-recommend.

---

# 8. Explicit Non-Goals

These reference scenarios SHALL NOT:

- define the only supported use cases;
- require exact model wording;
- prescribe a fixed winning alternative;
- introduce organization-specific requirements;
- introduce new infrastructure requirements;
- serve as hidden prompt templates;
- replace formal acceptance criteria;
- become a benchmark claiming statistical model quality.

Additional scenarios MAY be added later when a new feature, failure mode, or domain requires evidence that the existing set does not provide.

---

# 9. Reference Scenario Completion Criteria

The reference-scenario baseline is sufficient for the MVP when:

1. At least one scenario supports a full multi-alternative review.
2. At least one scenario demonstrates generality outside software architecture.
3. At least one scenario requires preservation of uncertainty and allows no recommendation.
4. No scenario depends on a named organization or confidential information.
5. Expected behavior is defined in terms of process properties rather than exact generated answers.
6. The scenarios can later serve as prompt-evaluation, integration-test, and demonstration inputs without changing canonical product requirements.

With these scenarios in place, the canonical conceptual documentation set is complete enough to proceed to the Spec Kit Constitution.
