# Agentic Review Board — Agent Model

**Status:** Canonical MVP agent model  
**Version:** 0.1  
**Related documents:**

- `docs/01-product-vision.md`
- `docs/02-requirements.md`
- `docs/03-architecture.md`

## 1. Purpose

This document defines the semantic model for the five review participants used by the Agentic Review Board MVP.

It specifies, for each participant:

- primary responsibility;
- allowed inputs;
- required structured output;
- invariants;
- prohibited behavior;
- upstream dependencies;
- downstream consumers.

The purpose is to ensure that the MVP demonstrates genuine specialization and collaboration rather than several loosely differentiated prompts.

This document defines **what each agent role means**. It does not define concrete prompts, LLM models, temperature settings, implementation classes, libraries, or orchestration frameworks. Those decisions belong to implementation specifications or ADRs.

---

# 2. Agent Model Principles

## AM-001 — Single Primary Responsibility

Each review participant SHALL have one primary semantic responsibility.

Participants MAY observe adjacent concerns when necessary to perform their task, but SHALL NOT silently take ownership of another participant's role.

## AM-002 — Explicit Contracts

Every participant SHALL receive explicit structured inputs and SHALL produce an explicit structured output.

Critical downstream data SHALL NOT depend only on free-form narrative text.

## AM-003 — Upstream Outputs Are Evidence, Not Truth

A downstream participant SHALL treat upstream outputs as review artifacts that may contain assumptions, omissions, or weak conclusions.

A downstream participant MAY challenge upstream content when its role requires it.

## AM-004 — Facts and Assumptions Remain Distinct

A statement identified as an assumption SHALL remain an assumption unless supported by information explicitly present in the original ReviewInput.

Repetition by multiple agents SHALL NOT promote an assumption into a fact.

## AM-005 — No Hidden State Between Agents

The semantic result of one participant SHALL be communicated to downstream participants through explicit review contracts.

The MVP SHALL NOT rely on hidden conversational memory shared implicitly between agents.

## AM-006 — No Autonomous Action

No participant SHALL execute external business, technical, filesystem, network, collaboration-platform, or organizational actions as part of the MVP review workflow.

## AM-007 — No Workflow Control by Agents

Participants SHALL NOT decide which stage runs next, skip mandatory stages, or directly invoke other participants.

Workflow control belongs exclusively to the Review Orchestrator.

## AM-008 — No Private Chain-of-Thought Exposure

Participants SHALL expose conclusions, findings, assumptions, trade-offs, risks, criticisms, and rationale in explicit structured fields.

They SHALL NOT be designed to expose private chain-of-thought reasoning.

## AM-009 — Bounded Output

Participant outputs SHOULD be concise enough to support inspection during a demonstration while remaining sufficient for downstream use.

The MVP SHOULD favor structured bullets and short explanations over long essays.

## AM-010 — Provider Independence

Participant semantics SHALL NOT depend on provider-specific message types, tool formats, SDK objects, or proprietary model features.

---

# 3. Shared Concepts

The following conceptual structures are shared across participant contracts.

Exact implementation names MAY differ, but their semantics SHALL remain equivalent.

## 3.1 ReviewInput

Represents the original information supplied by the user.

Conceptual fields:

```text
ReviewInput
- title?                optional text
- description           required text
- objective?            optional text
- constraints[]         optional list
- context[]             optional list
- stated_facts[]        optional list
```

The original ReviewInput SHALL remain unchanged for the duration of the review.

## 3.2 QualitativeLevel

The MVP SHALL use the following ordered qualitative values where severity, complexity, or confidence require classification:

```text
LOW
MEDIUM
HIGH
```

These values are ordinal labels, not statistical probabilities.

## 3.3 ReferencedItem

Where practical, structured findings SHOULD contain a stable local identifier so downstream participants can refer to them explicitly.

Examples:

```text
FACT-001
ASM-002
ALT-001
RISK-003
CRIT-002
```

The identifier mechanism is intended for traceability within one Review. It does not imply persistent global identifiers.

## 3.4 Evidence Basis

When a participant makes a material statement, it SHOULD be possible to identify whether the statement is based on:

- original user-provided information;
- an explicit upstream finding;
- an explicit assumption;
- a review judgment derived from those inputs.

The MVP does not require formal probabilistic evidence scoring.

---

# 4. Analyst

## 4.1 Primary Responsibility

The Analyst SHALL transform the raw ReviewInput into a structured representation of the decision problem.

Its purpose is to establish a disciplined problem frame for all later stages.

The Analyst answers:

> What problem are we actually reviewing, what do we know, what are we assuming, what constrains the decision, and what important information is missing?

## 4.2 Upstream Dependency

The Analyst depends only on:

- `ReviewInput`.

It SHALL NOT depend on outputs produced by later review stages.

## 4.3 Allowed Input

```text
AnalystInput
- review_input: ReviewInput
```

## 4.4 Required Output

The Analyst SHALL produce a `ProblemAnalysis` containing at minimum:

```text
ProblemAnalysis
- objective
- facts[]
- constraints[]
- assumptions[]
- missing_information[]
- uncertainties[]
```

Each item SHOULD have a local reference identifier where useful.

### objective

A concise statement of the decision or outcome the review is trying to support.

### facts[]

Statements explicitly supported by ReviewInput.

A fact SHALL NOT be introduced solely because it appears plausible.

For the executable local-LLM contract, every `stated_facts` item SHALL be copied first
and every `context` item SHALL then be copied into `facts[]`, preserving the order within
each source collection. Text, provenance, and deterministic `FACT-*` identifiers SHALL
be preserved exactly. This makes quantitative and operational context visible to all
downstream participants rather than leaving it only in the raw input.

### constraints[]

Explicit restrictions, boundaries, obligations, or conditions relevant to the problem.

Constraints MAY come from user-provided facts or context.

### assumptions[]

Statements introduced because they are useful for analysis but are not explicitly established as facts by ReviewInput.

Each assumption SHOULD make its unsupported status clear.

### missing_information[]

Information that is absent and could materially affect solution comparison, risk evaluation, or recommendation quality.

### uncertainties[]

Known ambiguities or areas where available information permits more than one reasonable interpretation.

## 4.5 Analyst Invariants

The Analyst SHALL satisfy all of the following:

1. Every item in `facts[]` is traceable to ReviewInput.
2. Every explicit `stated_facts` and `context` item appears exactly once in `facts[]`.
3. Assumptions are explicitly separated from facts.
4. Missing information is not silently filled with invented content.
5. The objective is consistent with the user's stated problem.
6. The Analyst does not choose a preferred solution.

## 4.6 Prohibited Behavior

The Analyst SHALL NOT:

- generate or rank solution alternatives;
- recommend an architecture or implementation option;
- perform the final risk ranking;
- make the final decision;
- convert an inferred assumption into a fact;
- hide material ambiguity to make later analysis appear more complete.

## 4.7 Downstream Consumers

`ProblemAnalysis` SHALL be consumed by:

- Solution Architect;
- Risk Reviewer;
- Critic;
- Coordinator.

---

# 5. Solution Architect

## 5.1 Primary Responsibility

The Solution Architect SHALL generate meaningful candidate approaches for solving or addressing the structured problem.

It answers:

> What credible alternatives could satisfy the objective under the known constraints and assumptions?

The Solution Architect explores solution space; it does not select the winner.

## 5.2 Upstream Dependencies

The Solution Architect depends on:

- `ReviewInput`;
- validated `ProblemAnalysis`.

## 5.3 Allowed Input

```text
SolutionArchitectInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

## 5.4 Required Output

The Solution Architect SHALL produce `SolutionAlternatives`.

Conceptually:

```text
SolutionAlternatives
- alternatives[]
- generation_notes?
```

When meaningful alternatives exist, `alternatives[]` SHALL contain between two and three items for the MVP.

Each `SolutionAlternative` SHALL contain:

```text
SolutionAlternative
- id
- name
- description
- advantages[]
- disadvantages[]
- assumptions[]
- implementation_complexity
- relevant_constraints[]
- validation_status
```

### name

A short, distinguishing label.

### description

A concise explanation of the approach.

### advantages[]

Material benefits relative to the stated objective and constraints.

### disadvantages[]

Material weaknesses, costs, limitations, or trade-offs.

### assumptions[]

Assumptions required for the alternative to be viable.

These MAY reference existing Analyst assumptions or introduce new solution-specific assumptions, but new assumptions SHALL remain explicitly marked as assumptions.

### implementation_complexity

A qualitative `LOW`, `MEDIUM`, or `HIGH` assessment for the MVP.

It SHALL be treated as a relative engineering judgment, not a measured project estimate.

### relevant_constraints[]

References to known constraints that materially shape or limit the alternative.

### validation_status

Typed evidence state for the alternative. `PROPOSED` means that the approach is a
candidate whose claimed capabilities still require validation; `EVIDENCED` is reserved
for a future participant or process with explicit evidence authority. The Solution
Architect SHALL emit only `PROPOSED` and SHALL NOT self-promote an alternative.

## 5.5 No-Alternative Case

If the available problem frame does not support multiple meaningful alternatives, the Solution Architect SHALL NOT fabricate artificial variants merely to satisfy a count.

Instead, it SHALL return an explicit result stating:

- why meaningful alternatives cannot yet be formed;
- which missing information or uncertainty blocks useful comparison.

The Orchestrator and later stages SHALL preserve this limitation.

## 5.6 Solution Architect Invariants

The Solution Architect SHALL satisfy all of the following:

1. Alternatives are meaningfully distinct when more than one is returned.
2. Alternatives are compatible with the stated objective unless explicitly identified as partial or conditional.
3. Known constraints are not silently ignored.
4. New assumptions remain explicitly identified.
5. Advantages and disadvantages are attached to a specific alternative.
6. No alternative is declared the final winner.
7. Every generated alternative has `validation_status=PROPOSED`.

## 5.7 Prohibited Behavior

The Solution Architect SHALL NOT:

- produce the final ranking;
- declare the final recommendation;
- suppress inconvenient constraints;
- invent user facts to make an alternative viable;
- duplicate the same approach under superficial wording changes;
- treat implementation complexity as a statistically measured probability or duration estimate.
- claim `EVIDENCED` status for an alternative.

## 5.8 Downstream Consumers

`SolutionAlternatives` SHALL be consumed by:

- Risk Reviewer;
- Critic;
- Coordinator.

---

# 6. Risk Reviewer

## 6.1 Primary Responsibility

The Risk Reviewer SHALL identify and structure material downside exposure associated with the overall proposal and the candidate alternatives.

It answers:

> What could go wrong, which option is affected, how severe could the consequence be, and what mitigation is available?

The Risk Reviewer evaluates exposure; it does not choose the final solution.

## 6.2 Upstream Dependencies

The Risk Reviewer depends on:

- `ReviewInput`;
- validated `ProblemAnalysis`;
- validated `SolutionAlternatives`.

## 6.3 Allowed Input

```text
RiskReviewerInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
```

## 6.4 Required Output

The Risk Reviewer SHALL produce `RiskAssessment`.

Conceptually:

```text
RiskAssessment
- risks[]
- overall_observations[]
```

Each `Risk` SHALL contain:

```text
Risk
- id
- category?
- description
- affected_scope
- severity
- basis[]
- mitigation?
- residual_uncertainty?
```

### category

Optional classification such as:

- technical;
- security;
- privacy;
- operational;
- maintainability;
- cost;
- external dependency;
- organizational.

The Risk Reviewer SHALL NOT invent a risk merely to populate every category.

### affected_scope

The risk SHALL indicate whether it applies to:

- the overall proposal;
- one specific alternative;
- multiple identified alternatives.

### severity

A qualitative `LOW`, `MEDIUM`, or `HIGH` classification.

### basis[]

References or concise descriptions of the facts, assumptions, constraints, or solution characteristics that make the risk relevant.

### mitigation

A practical action or design consideration that could reduce likelihood, impact, or exposure.

Mitigation does not imply the risk is eliminated.

### residual_uncertainty

Optional explanation of what remains unknown even after mitigation.

## 6.5 Risk Reviewer Invariants

The Risk Reviewer SHALL satisfy all of the following:

1. Every material risk has an identifiable affected scope.
2. Severity is qualitative and not presented as calibrated probability.
3. Risks are based on explicit problem or alternative characteristics rather than arbitrary pessimism.
4. Missing information that materially affects risk assessment remains visible.
5. A mitigation does not automatically remove the underlying risk.
6. The reviewer does not convert risk analysis into a final solution ranking.

## 6.6 Prohibited Behavior

The Risk Reviewer SHALL NOT:

- make the final recommendation;
- assign unsupported numeric probabilities;
- invent organization-specific policies not present in ReviewInput;
- fabricate risks solely to demonstrate activity;
- ignore a material risk because it weakens an otherwise attractive alternative;
- redefine the alternatives rather than assess them.

## 6.7 Downstream Consumers

`RiskAssessment` SHALL be consumed by:

- Critic;
- Coordinator.

---

# 7. Critic

## 7.1 Primary Responsibility

The Critic SHALL challenge the quality and support of the analysis produced so far.

It answers:

> Where are the weak assumptions, contradictions, omissions, unsupported conclusions, or underestimated risks in the current review?

The Critic is adversarial toward weak reasoning, not adversarial for its own sake.

## 7.2 Upstream Dependencies

The Critic depends on:

- `ReviewInput`;
- validated `ProblemAnalysis`;
- validated `SolutionAlternatives`;
- validated `RiskAssessment`.

## 7.3 Allowed Input

```text
CriticInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
- risk_assessment: RiskAssessment
```

## 7.4 Required Output

The Critic SHALL produce `CriticalReview`.

Conceptually:

```text
CriticalReview
- criticisms[]
- validated_points[]
- missing_alternatives[]
- contradictions[]
- unresolved_issues[]
```

Each `Criticism` SHOULD contain:

```text
Criticism
- id
- target_type
- target_reference
- issue
- importance
- rationale
- correction_or_question?
```

### target_type

Identifies what is being challenged, for example:

- assumption;
- alternative;
- advantage;
- disadvantage;
- risk;
- mitigation;
- constraint interpretation;
- cross-stage conclusion.

### target_reference

Reference to the explicit item being challenged whenever possible.

### issue

Concise description of the weakness.

### importance

Qualitative indication of whether the criticism could materially affect the final decision.

The MVP MAY use `LOW`, `MEDIUM`, or `HIGH` for this purpose.

### rationale

Concise explanation of why the criticism is justified using visible review artifacts.

### correction_or_question

Optional proposal for how to resolve the weakness or what information is needed.

## 7.5 Validated Points

The Critic SHALL be allowed to explicitly identify findings that appear adequately supported.

This prevents artificial disagreement and provides the Coordinator with a clearer view of which conclusions survived critical review.

## 7.6 Missing Alternatives

The Critic MAY identify a genuinely material alternative class omitted by the Solution Architect.

For the MVP, the Critic SHALL NOT fully design a replacement solution set.

It SHALL instead state:

- what alternative category appears missing;
- why the omission matters;
- whether the omission is serious enough to weaken the final recommendation.

## 7.7 Contradictions

The Critic SHALL identify contradictions between explicit artifacts when present, including contradictions between:

- facts and assumptions;
- assumptions and constraints;
- alternative claims and risk findings;
- advantages and disadvantages;
- multiple upstream conclusions.

Each contradiction SHALL expose a `support_status`. `UNVERIFIED` means that the Critic
has identified a possible conflict but no evidence-authorized process has established it
as a true contradiction. `EVIDENCED` is reserved for such a future process. The Critic
SHALL emit only `UNVERIFIED`; the Coordinator SHALL treat it as a validation target, not
as an established reason to exclude an alternative.

## 7.8 Critic Invariants

The Critic SHALL satisfy all of the following:

1. Material criticisms reference an explicit review artifact whenever possible.
2. The Critic may validate strong analysis rather than being forced to object.
3. Criticism remains evidence-based and concise.
4. The Critic does not silently rewrite upstream artifacts.
5. Newly identified uncertainty remains explicit.
6. Criticism occurs before the Coordinator may produce a complete final review.
7. Every contradiction has `support_status=UNVERIFIED`.

## 7.9 Prohibited Behavior

The Critic SHALL NOT:

- invent objections merely to create conflict;
- make the final ranking;
- make the final recommendation;
- silently replace the Architect's alternatives with its own solution portfolio;
- introduce fabricated facts;
- rely on hidden reasoning not represented in the structured output;
- dismiss a valid conclusion solely because it originated from another participant.
- claim `EVIDENCED` support for a contradiction.

## 7.10 Downstream Consumer

`CriticalReview` SHALL be consumed by:

- Coordinator.

---

# 8. Coordinator

## 8.1 Primary Responsibility

The Coordinator SHALL synthesize the complete validated review into a final decision-support result.

It answers:

> Considering the original problem, proposed alternatives, risks, and critical review, how should the alternatives be ordered, why, what remains uncertain, and what should the human validate next?

The Coordinator integrates prior work; it does not independently restart the analysis from scratch.

## 8.2 Upstream Dependencies

The Coordinator depends on all mandatory validated artifacts:

- `ReviewInput`;
- `ProblemAnalysis`;
- `SolutionAlternatives`;
- `RiskAssessment`;
- `CriticalReview`.

If any mandatory upstream artifact is unavailable because of stage failure, the Coordinator SHALL NOT execute for a complete review.

## 8.3 Allowed Input

```text
CoordinatorInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
- risk_assessment: RiskAssessment
- critical_review: CriticalReview
```

## 8.4 Required Output

The Coordinator SHALL produce `FinalReview`.

Conceptually:

```text
FinalReview
- situation_summary
- ranked_alternatives[]
- preferred_alternative?
- principal_risks[]
- unresolved_questions[]
- next_validation_step
- confidence
- decision_support_notice
```

Each `RankedAlternative` SHALL contain:

```text
RankedAlternative
- alternative_reference
- validation_status
- position
- justification
- considerations[]
- conditions_that_could_change_ranking[]
```

### situation_summary

Concise summary of the decision context, preserving material uncertainty.

### ranked_alternatives[]

When multiple alternatives are available, the Coordinator SHALL rank them from most suitable to least suitable.

Every ranked item SHALL copy the exact `validation_status` of its referenced upstream
alternative. Ranking an alternative does not validate its claimed capabilities.

### justification

Every position SHALL have an explicit justification derived from visible review artifacts.

### considerations[]

Material trade-offs, dependencies, unresolved concerns, or limitations associated with that alternative.

### conditions_that_could_change_ranking[]

Where applicable, explicit information or future evidence that could reasonably change the assigned position.

### preferred_alternative

The top-ranked alternative MAY be identified as preferred only when the available evidence is sufficient.

### principal_risks[]

The most decision-relevant risks that remain after considering mitigations and critical review.

### unresolved_questions[]

Open questions or missing information that remain material to the decision.

### next_validation_step

One concrete next action for the human team to validate the recommendation or reduce uncertainty.

The step is advisory only and SHALL NOT be executed autonomously by the application.

### confidence

A qualitative `LOW`, `MEDIUM`, or `HIGH` assessment of how strongly the available review artifacts support the final result.

### decision_support_notice

A clear indication that the result supports, but does not replace, human decision authority.

## 8.5 Ranking Semantics

The Coordinator SHALL rank alternatives using the review evidence available in the current execution.

The ranking SHALL consider, as relevant:

- alignment with the objective;
- satisfaction of constraints;
- meaningful advantages;
- material disadvantages;
- implementation complexity;
- risk exposure and mitigations;
- criticisms that survived review;
- unresolved assumptions;
- missing information.

The MVP SHALL NOT require a hidden numerical scoring formula.

If a scoring model is later introduced, it SHALL require an ADR or explicit requirement defining its semantics and consequences.

## 8.6 Insufficient Evidence Case

The Coordinator SHALL NOT force a preferred alternative when evidence is insufficient.

In that case, `FinalReview` SHALL:

- state that no recommendation can yet be justified;
- preserve the most plausible alternatives if available;
- identify the blocking uncertainty or missing information;
- propose the next validation step;
- assign an appropriately low or medium confidence level.

## 8.7 Coordinator Invariants

The Coordinator SHALL satisfy all of the following:

1. It consumes all mandatory validated upstream artifacts.
2. It does not invent missing evidence.
3. It preserves material uncertainty.
4. Every ranking position has a justification.
5. Every ranked alternative has final considerations.
6. The final result remains recognizable as decision support.
7. A preferred alternative is omitted when evidence is insufficient.
8. Confidence remains qualitative unless a future validated methodology is introduced.
9. Ranked alternatives preserve their upstream validation status exactly.

## 8.8 Prohibited Behavior

The Coordinator SHALL NOT:

- fabricate facts, risks, or evidence missing from upstream artifacts;
- ignore the Critic without explaining why a criticism is not decision-relevant;
- present qualitative confidence as statistical probability;
- execute the recommended next step;
- claim final authority over the human decision;
- hide unresolved questions solely to make the recommendation appear stronger;
- silently create a new alternative that was never reviewed.
- promote an alternative from `PROPOSED` to `EVIDENCED`.

## 8.9 Downstream Consumer

`FinalReview` SHALL be consumed by:

- Review Application;
- UI Adapter;
- human user.

No autonomous execution component consumes the result in the MVP.

---

# 9. Participant Dependency Matrix

| Participant | ReviewInput | ProblemAnalysis | SolutionAlternatives | RiskAssessment | CriticalReview |
|---|---:|---:|---:|---:|---:|
| Analyst | Required | — | — | — | — |
| Solution Architect | Required | Required | — | — | — |
| Risk Reviewer | Required | Required | Required | — | — |
| Critic | Required | Required | Required | Required | — |
| Coordinator | Required | Required | Required | Required | Required |

This matrix is normative for the MVP dependency chain.

---

# 10. Responsibility Separation Matrix

| Concern | Analyst | Solution Architect | Risk Reviewer | Critic | Coordinator |
|---|---:|---:|---:|---:|---:|
| Structure the problem | Primary | Consume | Consume | Challenge | Summarize |
| Separate facts/assumptions | Primary | Preserve | Preserve | Challenge | Preserve |
| Generate alternatives | No | Primary | No | Identify omission only | No |
| Assess implementation complexity | No | Primary | Observe | Challenge | Consider |
| Identify risks | Limited to uncertainty | No | Primary | Challenge | Prioritize |
| Propose mitigations | No | No | Primary | Challenge | Consider |
| Challenge upstream reasoning | No | No | Limited | Primary | Reconcile |
| Rank alternatives | No | No | No | No | Primary |
| Recommend preferred option | No | No | No | No | Primary |
| Execute decision | No | No | No | No | No |

The table prevents role collapse while allowing downstream participants to consume and evaluate upstream work.

---

# 11. Contract Validation Rules

## CV-001 — Analyst Contract

A `ProblemAnalysis` is invalid if:

- objective is missing;
- facts and assumptions cannot be distinguished;
- required structured collections cannot be parsed;
- the output is only free-form prose with no usable contract.

## CV-002 — Solution Architect Contract

`SolutionAlternatives` is invalid if:

- alternatives lack required structured fields;
- multiple returned alternatives are effectively duplicates;
- no meaningful-alternative case is returned without explanation;
- required complexity classification is missing.

Duplicate detection MAY initially rely on deterministic structural checks plus explicit tests rather than semantic similarity infrastructure.

## CV-003 — Risk Reviewer Contract

A `RiskAssessment` is invalid if a material risk lacks:

- description;
- affected scope;
- severity.

Mitigation MAY be absent only when no credible mitigation is available, in which case that absence SHOULD be explicit.

## CV-004 — Critic Contract

A `CriticalReview` is invalid if it provides only generic criticism with no identifiable targets or if required structured sections cannot be parsed.

An empty `criticisms[]` list MAY be valid if the Critic explicitly records that no material unsupported weakness was found and still provides its validated points and unresolved issues.

## CV-005 — Coordinator Contract

A `FinalReview` is invalid if:

- alternatives exist but no ranking is provided without explanation;
- a ranking position lacks justification;
- final considerations are absent for ranked alternatives;
- confidence is missing;
- the next validation step is missing;
- a preferred alternative is asserted despite an explicit insufficient-evidence state;
- the decision-support nature of the result is absent.

---

# 12. Traceability Rules Between Agents

## TR-001 — Stable Local References

Where material for critique or ranking, upstream items SHOULD expose local identifiers that can be referenced downstream.

## TR-002 — No Implicit Evidence

A downstream participant SHOULD identify the explicit artifact that supports a material conclusion when practical.

## TR-003 — Criticism Traceability

Material Critic findings SHOULD point to the exact assumption, alternative, risk, or claim being challenged.

## TR-004 — Ranking Traceability

Coordinator justifications SHOULD refer to visible advantages, disadvantages, constraints, risks, assumptions, or criticisms rather than generic preference language.

## TR-005 — Uncertainty Propagation

Material missing information and unresolved assumptions SHALL remain available to downstream stages until resolved by information explicitly present in the same ReviewInput.

The MVP does not include an interactive clarification loop, so downstream agents SHALL not pretend unresolved information has been answered.

---

# 13. Agent Failure Semantics

Participants SHALL report failure through the application/orchestration boundary rather than constructing partial output and pretending success.

Failure categories MAY include:

- model/provider communication failure;
- malformed structured response;
- contract validation failure;
- unexpected internal processing failure.

A mandatory participant failure SHALL preserve all earlier validated artifacts and SHALL prevent dependent participants from executing.

The participant itself SHALL NOT decide to skip failure semantics and continue with fabricated placeholder content.

---

# 14. Prompting Boundary

Prompts are implementation artifacts and SHALL NOT define business semantics that contradict this document.

For every participant, future prompt templates SHALL:

- reflect the participant's primary responsibility;
- request the structured output required here;
- reinforce prohibited behaviors where important;
- provide only the upstream data permitted by this document;
- avoid asking the participant to perform another agent's responsibility.

Prompt wording, system/user message structure, prompt versioning, and prompt storage SHALL be implementation decisions and MAY be governed by ADRs.

---

# 15. Model Selection Boundary

The agent model defined here is logical, not physical.

The MVP MAY use:

- the same LLM model for all five participants;
- different models for different participants;
- local or remote models;
- any compatible provider-neutral implementation.

Using multiple logical agents does not require multiple physical models.

Model assignment SHALL be treated as a runtime/implementation decision unless later requirements demonstrate a need for participant-specific model capabilities.

---

# 16. Explicitly Deferred Agent Decisions

The following SHALL NOT be fixed by this document:

1. Exact prompt text.
2. Prompt file structure and versioning strategy.
3. Concrete Python classes or package names.
4. Pydantic, dataclass, JSON Schema, or other validation technology.
5. Exact LLM model used by each participant.
6. Temperature or sampling parameters.
7. Token limits.
8. Retry behavior.
9. Whether one participant may use more than one LLM call internally.
10. Whether future versions introduce parallel review participants.
11. Whether future versions introduce human clarification between stages.
12. Whether future versions introduce domain-specific participant profiles.

Material choices SHALL be captured by ADR when they create architectural consequences.

---

# 17. Agent Model Completion Criteria

The MVP implementation conforms to this Agent Model when all of the following are true:

1. Five distinct logical participant responsibilities exist.
2. Each participant has a validated input/output contract.
3. Analyst distinguishes facts, assumptions, constraints, missing information, and uncertainty.
4. Solution Architect generates distinct alternatives without selecting the winner.
5. Risk Reviewer assesses risks and mitigations without making the final decision.
6. Critic explicitly challenges weak artifacts and may validate strong ones.
7. Coordinator alone ranks alternatives and may recommend a preferred option.
8. Coordinator provides justification and final considerations for every ranking position.
9. Assumptions never become facts through repetition alone.
10. No participant controls workflow progression.
11. No participant executes external actions.
12. No participant depends directly on a provider-specific SDK.
13. Downstream conclusions remain traceable to explicit review artifacts.
14. A failed mandatory participant prevents dependent execution.
15. The final output remains decision support under human authority.

---

# 18. Next Canonical Document

The next canonical project document SHALL be `docs/05-quality-security.md`.

It will consolidate cross-cutting MVP expectations for:

- testing strategy;
- validation strategy;
- failure quality;
- logging and observability boundaries;
- secret handling;
- data minimization;
- demonstration-data constraints;
- AI-specific quality checks;
- minimum acceptance gates before the MVP is considered ready for demonstration.

It SHALL refine cross-cutting quality and security concerns without changing the product responsibilities defined in this Agent Model.
