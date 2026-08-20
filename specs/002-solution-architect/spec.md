# Feature Specification: Solution Architect v0.1

**Feature Branch**: `002-solution-architect`  
**Created**: 2026-08-20  
**Status**: Draft — awaiting review  
**Input**: Second executable product increment derived from the canonical MVP documents and the completed Review Input + Analyst v0.1 slice.

## User Scenarios & Testing

### User Story 1 - Generate meaningful solution alternatives (Priority: P1)

As a professional user, I want a validated problem analysis to be transformed into a small set of meaningful candidate approaches so that later review stages can compare explicit alternatives rather than reason from an undefined solution space.

**Why this priority**: The Solution Architect is the first downstream participant that demonstrates genuine use of a validated upstream artifact. Its output is required by the Risk Reviewer, Critic, and Coordinator.

**Independent Test**: Supply a valid `ReviewInput`, a valid `ProblemAnalysis`, and a deterministic Solution Architect result containing two or three meaningful alternatives; verify that a validated `SolutionAlternatives` result is produced with alternative-specific trade-offs, assumptions, complexity, and relevant constraints.

**Acceptance Scenarios**:

1. **Given** a valid `ReviewInput` and valid `ProblemAnalysis` that support multiple meaningful approaches, **When** the Solution Architect produces a structurally valid result, **Then** the system produces validated `SolutionAlternatives` containing between two and three alternatives.
2. **Given** multiple returned alternatives, **When** they are inspected, **Then** each alternative is represented as a distinct candidate approach rather than a superficial wording variation of another alternative.
3. **Given** an alternative, **When** it is inspected, **Then** its concise description, principal advantages, principal disadvantages, important assumptions, implementation complexity, and materially relevant constraints remain explicit.
4. **Given** Analyst assumptions and new solution-specific assumptions, **When** alternatives are produced, **Then** assumptions remain explicitly represented as assumptions and are not promoted into user-provided facts.
5. **Given** known constraints that materially shape an alternative, **When** the alternative is produced, **Then** those constraints are not silently ignored and remain traceable to the upstream review artifacts.
6. **Given** a valid Solution Architect result, **When** it is inspected, **Then** no alternative is ranked, declared the winner, or presented as the final recommendation.

---

### User Story 2 - Preserve an honest no-alternative outcome (Priority: P1)

As a professional user, I want the Solution Architect to state when the available problem frame does not support multiple meaningful alternatives so that the review does not manufacture artificial choice or false completeness.

**Why this priority**: The canonical Agent Model explicitly treats inability to generate genuine alternatives as a valid outcome. Preserving that limitation is necessary for uncertainty, traceability, and later decision quality.

**Independent Test**: Supply a valid but underspecified `ReviewInput` and `ProblemAnalysis`, then provide a deterministic Solution Architect result that produces no alternatives and explicitly identifies why meaningful alternatives cannot yet be formed and which missing information or uncertainty blocks useful comparison.

**Acceptance Scenarios**:

1. **Given** the current problem frame cannot responsibly support two meaningful alternatives, **When** the Solution Architect produces its result, **Then** it does not fabricate superficial alternatives merely to satisfy a count.
2. **Given** no meaningful alternative set can yet be formed, **When** the result is inspected, **Then** it explicitly states why alternatives cannot responsibly be generated.
3. **Given** missing information or unresolved uncertainty blocks useful alternative generation, **When** the no-alternative result is produced, **Then** those blockers remain explicit and traceable to the current review artifacts where applicable.
4. **Given** a no-alternative outcome, **When** it is validated, **Then** it remains a valid Solution Architect outcome rather than being silently repaired into fabricated alternatives.

---

### User Story 3 - Fail closed on invalid Solution Architect output (Priority: P1)

As a user, I want malformed or role-invalid Solution Architect output to fail explicitly so that untrusted generated alternatives cannot silently become trusted input for later stages.

**Independent Test**: Provide deterministic malformed Solution Architect results and verify that contract or participant-boundary validation rejects them before they can be treated as valid `SolutionAlternatives`.

**Acceptance Scenarios**:

1. **Given** generated output missing required alternative content, **When** it is validated, **Then** the Solution Architect result is rejected explicitly.
2. **Given** generated output with an unsupported implementation-complexity value, **When** it is validated, **Then** the result is rejected.
3. **Given** multiple alternatives with ambiguous or duplicate required local identifiers, **When** the result is validated, **Then** the result is rejected.
4. **Given** generated content that introduces ranking, a preferred alternative, or a final recommendation as Solution Architect output, **When** the closed contract is validated, **Then** that role leakage is rejected rather than accepted silently.
5. **Given** invalid generated data, **When** validation fails, **Then** no trusted `SolutionAlternatives` is returned or propagated.

## Edge Cases

- The Solution Architect requires both the original `ReviewInput` and a valid `ProblemAnalysis`; this slice does not define global workflow orchestration.
- When meaningful alternatives exist, the valid result contains two or three alternatives; a single-alternative result is not treated as the normal multiple-alternative outcome.
- When two or three meaningful alternatives cannot responsibly be formed, the valid outcome is an explicit no-alternative result rather than fabricated variants.
- Alternative identifiers are review-local and need not be globally persistent, but required identifiers within one `SolutionAlternatives` result must not be ambiguous.
- Alternatives may introduce solution-specific assumptions, but those assumptions remain assumptions even when repeated by later stages.
- Implementation complexity is qualitative (`LOW`, `MEDIUM`, `HIGH`) and is not a duration estimate, cost estimate, probability, or calibrated measurement.
- A known constraint may affect one alternative, several alternatives, or all alternatives; only materially relevant constraints need to be attached to each alternative.
- Structural validation can prove contract shape and reference validity where deterministic; it does not prove that two generated approaches are semantically optimal or objectively exhaustive.
- The Solution Architect may produce a partial or conditional approach when appropriate, but it must make that limitation explicit rather than presenting it as unconditional satisfaction of the objective.

## Requirements

### Functional Requirements

- **FR-001**: The Solution Architect MUST consume the current original `ReviewInput` and a valid `ProblemAnalysis` and MUST NOT require outputs from later review stages.
- **FR-002**: This increment MUST NOT mutate or rewrite the accepted `ReviewInput` or trusted `ProblemAnalysis` supplied to the Solution Architect.
- **FR-003**: The Solution Architect MUST produce a structured `SolutionAlternatives` result.
- **FR-004**: When the current problem frame supports meaningful alternatives, `SolutionAlternatives` MUST contain between two and three alternatives.
- **FR-005**: Each returned alternative MUST contain a review-local identifier, distinguishing name, concise description, principal advantages, principal disadvantages, important assumptions, qualitative implementation complexity, and materially relevant constraints.
- **FR-006**: Returned alternatives MUST represent meaningfully distinct approaches rather than superficial wording variations.
- **FR-007**: Implementation complexity MUST use only qualitative `LOW`, `MEDIUM`, or `HIGH` values in this increment.
- **FR-008**: Solution-specific assumptions MUST remain explicitly distinguishable from user-provided facts and MUST NOT silently replace or rewrite upstream Analyst findings.
- **FR-009**: Known constraints that materially shape or limit an alternative MUST remain explicit and traceable to the supplied upstream review artifacts.
- **FR-010**: If two or three meaningful alternatives cannot responsibly be produced, the Solution Architect MUST return an explicit no-alternative outcome stating why useful alternatives cannot yet be formed and identifying material missing information or uncertainty that blocks comparison when applicable.
- **FR-011**: The Solution Architect MUST NOT fabricate artificial variants merely to satisfy the normal alternative count.
- **FR-012**: The Solution Architect MUST NOT rank alternatives, declare a preferred alternative, produce the final recommendation, or make the final decision.
- **FR-013**: Model-generated Solution Architect output MUST be treated as untrusted until validated against the expected Solution Architect contract and applicable upstream-reference invariants.
- **FR-014**: Missing mandatory content, unsupported qualitative values, ambiguous required identifiers, invalid upstream references, or structurally invalid generated values MUST cause explicit validation failure.
- **FR-015**: Invalid Solution Architect output MUST NOT be returned or propagated as valid `SolutionAlternatives`.
- **FR-016**: Core Solution Architect behavior MUST be testable using deterministic model-output substitution without requiring network access or a live external LLM.

### Scope Boundaries

This increment does not introduce:

- the Review Orchestrator or global stage lifecycle/status handling;
- Risk Reviewer, Critic, or Coordinator behavior;
- ranking or final recommendation behavior;
- UI behavior;
- a concrete LLM provider or adapter;
- prompt/versioning policy unless later implementation planning proves it necessary;
- retries or timeout policy;
- persistence or review history;
- RAG or document ingestion;
- external tool execution or autonomous actions;
- organization-specific integration.

Concrete implementation classes, package layout, validation syntax, reference encoding, provider SDKs, prompt representation, and serialization details belong to implementation planning or ADRs, not to this feature specification.

### Key Entities

- **ReviewInput**: Immutable original user-provided problem and optional context established by the previous slice.
- **ProblemAnalysis**: Trusted validated Analyst output used as explicit upstream evidence by the Solution Architect.
- **SolutionAlternatives**: Validated Solution Architect result representing either two to three meaningful alternatives or an explicit no-alternative limitation.
- **SolutionAlternative**: One candidate approach with its own identity, description, trade-offs, assumptions, complexity, and relevant constraints.
- **No-Alternative Outcome**: Explicit representation that the current review artifacts do not support responsible generation of two or three meaningful alternatives, together with the reason and material blockers.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All acceptance scenarios in this specification can be exercised with deterministic substitutes and no live external LLM.
- **SC-002**: A valid deterministic multiple-alternative result produces one trusted `SolutionAlternatives` containing exactly two or three structurally complete alternatives.
- **SC-003**: Every alternative in the valid multiple-alternative scenario exposes its own description, advantages, disadvantages, assumptions, qualitative complexity, and relevant constraints without ranking semantics.
- **SC-004**: A deterministic underspecified scenario can produce a valid explicit no-alternative outcome without manufacturing artificial variants.
- **SC-005**: Every representative structurally invalid or role-invalid Solution Architect result in the feature test suite fails before becoming trusted `SolutionAlternatives` data.
- **SC-006**: The Solution Architect receives and preserves the current `ReviewInput` and trusted `ProblemAnalysis` as explicit upstream artifacts, demonstrating the first direct downstream consumption of the Analyst result.
- **SC-007**: No valid `SolutionAlternatives` contract produced by this increment contains final ranking, preferred-alternative, or final-recommendation semantics.

## Traceability to Canonical Documents

This feature specification is derived from and must remain consistent with:

- `docs/01-product-vision.md` — genuine multi-agent collaboration, structured information, visible trade-offs, and human decision authority;
- `docs/02-requirements.md` — FR-008, FR-016 through FR-020, FR-049 through FR-053, LLM-independent core testability, and provider independence;
- `docs/03-architecture.md` — explicit participant contracts, validated upstream propagation, provider-neutral LLM boundary, and validation before trusted Review state;
- `docs/04-agent-model.md` — Solution Architect responsibility, allowed inputs, `SolutionAlternatives`, `SolutionAlternative`, no-alternative behavior, invariants, and prohibited behavior;
- `docs/05-quality-security.md` — alternative distinctness, contract tests, deterministic substitution, fail-closed validation, assumption preservation, and no unsupported quantification;
- `.specify/memory/constitution.md` — genuine collaboration, role integrity, explicit validated contracts, traceability, provider independence, deterministic testability, minimal architecture, and incremental delivery.
