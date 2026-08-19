<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Amendment: align governing language more precisely with canonical MVP requirements.
- Modified principles:
  - I. Genuine Agent Collaboration and Role Integrity
    - Added explicit user-visible participant/status/intermediate-output inspectability.
    - Corrected Coordinator ranking semantics so ranking is mandatory when multiple
      alternatives exist and preference is produced only when evidence is sufficient.
- Added principles: none
- Removed principles: none
- Added sections: none
- Removed sections: none
- Deferred items: none
-->

# Agentic Review Board Constitution

Agentic Review Board is a deliberately small multi-agent decision-support demonstrator.
This constitution defines the non-negotiable principles that govern specifications,
plans, tasks, implementation, and future architectural evolution.

The constitution is intentionally shorter than the canonical project documentation.
It establishes governing constraints; detailed product behavior and architecture remain
in the canonical documents referenced below.

## Core Principles

### I. Genuine Agent Collaboration and Role Integrity

The system MUST demonstrate real collaboration between specialized review participants.

- The five logical responsibilities — Analyst, Solution Architect, Risk Reviewer,
  Critic, and Coordinator — MUST remain semantically distinct.
- Each participant MUST consume only the upstream information permitted by the Agent
  Model and MUST produce its defined structured output.
- Downstream participants MUST consume relevant validated upstream artifacts.
- Agents MUST NOT control global workflow progression or directly invoke one another.
- Multiple independent prompts whose outputs are merely displayed together MUST NOT
  be treated as agentic collaboration.
- The user-visible experience MUST make the participating roles, their execution
  status, and the structured output of each completed stage inspectable during the
  active review.
- The Coordinator MUST be the only participant that ranks alternatives. When multiple
  alternatives exist, it MUST rank them from most suitable to least suitable as
  required by the canonical requirements, and it MUST identify a preferred alternative
  when sufficient evidence exists. It MUST NOT force a preferred alternative when
  evidence is insufficient.

Any feature that collapses these responsibilities into indistinguishable generic
reviewers or hides the collaborative process from the user violates the product purpose
and MUST be redesigned.

### II. Structured Contracts and Validation

All critical information exchanged between review stages MUST cross explicit,
validated contracts.

- Model-generated structured output MUST be treated as untrusted until parsed and
  validated.
- Invalid or incomplete required output MUST NOT enter trusted Review state.
- Invalid output MUST NOT propagate to downstream stages.
- Required values MUST NOT be silently invented to repair malformed model output.
- Facts, assumptions, constraints, alternatives, risks, criticisms, and final review
  information MUST remain structurally distinguishable where required by the canonical
  contracts.
- Presentation code MUST NOT repair invalid semantic output on behalf of the
  application core.

Structured contracts exist to make collaboration, testing, failure handling, and
traceability explicit rather than dependent on free-form prose.

### III. Traceability, Uncertainty, and Explicit Evidence

The final review MUST be traceable to explicit review artifacts rather than hidden
reasoning.

- User-provided facts MUST remain distinguishable from generated assumptions.
- Repetition by multiple participants MUST NOT promote an assumption into a fact.
- Material missing information and unresolved uncertainty MUST remain visible to
  downstream participants while unresolved.
- Material criticism SHOULD reference the artifact being challenged whenever
  practical.
- Ranking justification MUST be based on visible review artifacts and trade-offs.
- The application MUST NOT require, expose, or intentionally log private
  chain-of-thought reasoning.
- A conclusion of insufficient evidence MUST be treated as a valid outcome when the
  available artifacts do not justify a recommendation.

The system MUST prefer explicit uncertainty over unsupported confidence.

### IV. Human Decision Authority

Agentic Review Board is decision support, not an autonomous decision maker.

- The human user MUST retain final authority over every recommendation.
- The final result MUST be presented as advisory decision support.
- No participant MAY execute an external business or technical action as a consequence
  of its analysis.
- A suggested next validation step MAY be generated but MUST NOT be executed
  autonomously by the MVP.
- Generated structured output MUST NOT by itself authorize any external side effect.

Introducing autonomous execution requires an explicit product-scope change, new
requirements, security analysis, and an architectural decision before implementation.

### V. Minimal Architecture and Evidence-Driven Complexity

The MVP MUST use the smallest architecture that convincingly demonstrates the required
behavior.

- New infrastructure MUST solve an explicit requirement or an observed implementation
  limitation.
- The MVP MUST NOT require RAG, vector databases, persistent agent memory, external
  tools, MCP, enterprise authentication, microservices, distributed workers, message
  brokers, or production-scale infrastructure unless a later approved requirement
  introduces the need.
- A multi-agent framework MUST NOT be adopted merely because the application contains
  multiple logical agents.
- Unused abstractions for hypothetical future capabilities MUST NOT be introduced into
  the MVP core.
- Complexity introduced in a plan MUST be justified by the requirement or limitation
  it resolves.

When two approaches satisfy the same requirement, the simpler approach is preferred
unless documented evidence justifies the more complex one.

### VI. Provider Independence and Boundary Discipline

Product and agent semantics MUST remain independent of any specific LLM provider.

- Review participants MUST depend on a provider-neutral model-access boundary.
- Provider SDK request and response types MUST NOT leak into domain or agent contracts.
- Provider-specific behavior MUST remain behind the LLM Adapter boundary.
- UI code MUST NOT directly invoke provider SDKs or own stage orchestration.
- The review core MUST remain usable and testable without initializing a concrete UI
  or live external model service.

Changing between compatible model providers SHOULD NOT require redesigning the review
responsibilities or their contracts.

### VII. Deterministic Testability and Visible Failure

Core behavior MUST be verifiable without relying on nondeterministic external model
responses.

- Core domain, contract, and orchestration tests MUST run without a live LLM endpoint.
- Deterministic substitutes MUST support success, malformed-output, provider-failure,
  and insufficient-evidence scenarios.
- Stage sequencing, dependency enforcement, data propagation, validation, failure
  propagation, Coordinator preconditions, and new-review isolation MUST be testable.
- A mandatory stage failure MUST stop dependent execution.
- Earlier validated outputs SHOULD remain inspectable after a later failure.
- An incomplete review MUST NOT be presented as a complete recommendation.
- Integration tests requiring a real model endpoint MUST remain distinguishable from
  deterministic core tests.

Failure visibility is part of the product behavior, not merely a debugging concern.

### VIII. Security by Minimization and Least Capability

The MVP MUST minimize secrets, data exposure, privileges, persistence, and external
capabilities.

- Secrets MUST NOT be committed to source control.
- Runtime secrets MUST be supplied through external configuration or another approved
  runtime mechanism.
- Secrets MUST NOT be exposed through logs, test fixtures, or user-visible errors.
- Demonstrations SHOULD use synthetic, public, anonymized, or explicitly approved
  information.
- The MVP MUST NOT depend on confidential organizational data to demonstrate value.
- Review prompts and outputs MUST NOT require persistent storage.
- Logs MUST NOT be used as an implicit persistent store for full prompts or responses.
- User input and model output MUST be treated as untrusted content at their respective
  trust boundaries.
- A model response MUST NOT be able to grant itself new tools or privileges.

Any future persistence, confidential-data processing, external tools, or generated-code
execution requires explicit security analysis before implementation.

### IX. Incremental Delivery and Explicit Architectural Decisions

Development MUST proceed through small, independently verifiable increments.

- Each implementation increment MUST have a bounded purpose and observable outcome.
- New or changed domain/application behavior MUST have deterministic tests.
- Existing canonical project documents MUST NOT be contradicted silently.
- Material architectural choices MUST be documented through an ADR when they introduce
  a significant dependency, framework, persistence model, integration, runtime pattern,
  or security consequence.
- ADRs MUST record the motivating need, alternatives considered, selected decision,
  consequences, and conditions for reconsideration.
- Technology choices MUST serve product requirements and architectural boundaries;
  they MUST NOT become requirements merely because they are convenient or fashionable.

The preferred evolution is the smallest tested change that produces useful evidence.

## Canonical Project Sources

The constitution governs the project, while the following documents provide the
detailed canonical baseline from which it is derived:

- `docs/01-product-vision.md` — product purpose, value, scope, and non-goals.
- `docs/02-requirements.md` — functional, non-functional, security, and acceptance
  requirements.
- `docs/03-architecture.md` — stable architectural boundaries, dependencies, state,
  and extension points.
- `docs/04-agent-model.md` — participant responsibilities, contracts, invariants, and
  prohibitions.
- `docs/05-quality-security.md` — testing, validation, AI-quality, security, and demo
  readiness baseline.
- `docs/06-reference-scenarios.md` — organization-neutral behavioral examples for
  evaluation and demonstration.

Specifications and plans MUST use these documents as authoritative project context.
Reference scenarios MUST be treated as examples of expected behavior, not as fixed
answers or hidden requirements.

If a specification, plan, task, implementation choice, or ADR conflicts with a MUST in
this constitution, the conflict MUST be resolved before implementation continues.
The solution is to change the conflicting artifact or deliberately amend the
constitution; principles MUST NOT be silently bypassed.

## Development and Review Gates

All Spec Kit work MUST preserve separation between product intent and implementation
choice.

- Feature specifications MUST focus on user value, observable behavior, requirements,
  edge cases, and acceptance criteria; they MUST NOT invent architecture merely to make
  the specification concrete.
- Technical plans MUST explicitly check compliance with this constitution before
  implementation tasks are accepted.
- Plans introducing complexity MUST identify the requirement or observed limitation
  that justifies it.
- Tasks affecting domain/application behavior MUST include the tests needed to verify
  the changed behavior.
- Cross-artifact analysis SHOULD be run before implementation when a feature changes
  multiple contracts, architectural boundaries, or acceptance criteria.
- Implementation MUST NOT weaken validation, traceability, failure visibility, human
  authority, or security controls solely to make the happy path easier.
- A feature is not complete merely because a live LLM produced a plausible result;
  deterministic behavioral tests and applicable acceptance criteria MUST pass.

## Governance

This constitution supersedes ad-hoc implementation convenience when a conflict exists.
The canonical project documents remain the detailed source of product and architecture
semantics and MUST remain consistent with the constitution.

### Amendment Procedure

Any amendment MUST:

1. identify the motivating requirement, observed limitation, or governance problem;
2. describe which principles or sections change;
3. update affected canonical documentation and Spec Kit artifacts when necessary;
4. include a new Sync Impact Report;
5. apply the versioning policy below;
6. be committed as an explicit governance change rather than hidden inside unrelated
   implementation work.

### Versioning Policy

The constitution uses semantic versioning for governance:

- **MAJOR** — removal or backward-incompatible redefinition of a governing principle.
- **MINOR** — addition of a new principle or material expansion of governance.
- **PATCH** — clarification, wording improvement, or non-semantic refinement.

### Compliance Review

Every feature plan and material architectural change MUST be reviewed against this
constitution.

Unjustified violations of a MUST are blocking. They MUST be corrected in the spec,
plan, tasks, implementation, or constitution before the affected work is considered
complete.

Architecture may evolve through ADRs, but an ADR does not automatically override the
constitution. A conflicting ADR requires a constitution amendment first.

**Version:** 1.1.0  
**Ratified:** 2026-08-19  
**Last Amended:** 2026-08-19
