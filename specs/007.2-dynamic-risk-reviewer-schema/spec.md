# Slice 7.2 — Context-Bound Risk Reviewer Output Schema v0.1

**Status:** Draft — awaiting user review  
**Branch:** `007.2-dynamic-risk-reviewer-schema`  
**Depends on:** Slices 1–7.1  
**Observed evidence:** local vLLM campaign recorded on 2026-08-30  
**Canonical sources:** `docs/01-product-vision.md`, `docs/02-requirements.md`,
`docs/03-architecture.md`, `docs/04-agent-model.md`,
`docs/05-quality-security.md`, `.specify/memory/constitution.md`, ADR-0001,
ADR-0002, and the approved Slice 7.1 specification

## 1. Purpose

Slice 7.2 reduces a demonstrated Risk Reviewer failure mode without weakening the
trusted `RiskAssessment` contract or changing the provider-neutral `LLMPort`.

The current static JSON Schema constrains the individual shapes of risk-basis
references, but it cannot express that a generated reference must be one exact
reference resolvable against the current `ReviewInput`, `ProblemAnalysis`, and
`SolutionAlternatives`. In five fixed local Qwen3-4B-AWQ runs, the Risk Reviewer
returned structurally plausible output that labeled constraint-backed Problem Analysis
references as assumptions and paired them with IDs and text that did not identify an
exact trusted finding. The participant correctly rejected every result, left Critic and
Coordinator pending, and made each Review visibly `INCOMPLETE`.

This slice SHALL build a request-specific Risk Reviewer output schema from the current
three-artifact payload. It SHALL expose only exact, unambiguous risk-basis references
that the existing contextual validator can resolve and SHALL constrain alternative-
specific risk scopes to current alternative identifiers. The existing structural and
contextual participant validation remains authoritative and fail-closed.

This is a request-guidance correction at the untrusted model boundary. It does not
assert that the model, hardware, or vLLM version caused the contract gap, and it does
not make schema conformance equivalent to good risk analysis.

## 2. Current Baseline

Slices 4 and 7 already provide:

- an authoritative frozen `RiskAssessment` domain contract;
- three discriminated risk-basis reference families for `ReviewInput`,
  `ProblemAnalysis`, and `SolutionAlternatives`;
- exact contextual resolution of every generated basis reference;
- exact validation of alternative IDs used by `affected_scope`;
- rejection of ambiguous, fabricated, mistyped, or mismatched references;
- valid zero-risk and zero-alternative behavior;
- an unchanged provider-neutral `LLMPort.generate_structured(role, payload)`;
- `JSON_OBJECT`, `JSON_SCHEMA`, and `PROMPT_ONLY` modes;
- direct JSON parsing with no repair or automatic retry;
- deterministic adapter tests and opt-in live evaluation.

Slice 7.1 additionally provides request-specific schema construction for Critic while
keeping local participant validation authoritative. That behavior is an approved
precedent, not permission to weaken or generalize the trusted domain contracts.

The baseline MUST continue rejecting all invalid Risk Reviewer output when a provider
ignores, only partially supports, or cannot enforce request-time schema guidance.

## 3. Scope

### 3.1 In Scope

Slice 7.2 SHALL:

1. recognize the exact current Risk Reviewer payload containing `review_input`,
   `problem_analysis`, and `solution_alternatives`;
2. expose at least one canonical legal representation for every current risk-basis
   target that the existing contextual validator can resolve unambiguously;
3. preserve the exact source-specific fields of each basis reference, including
   `field`, `kind`, optional `id`, `alternative_id`, `characteristic`, and the exact
   text or structured constraint value;
4. correlate each complete basis-reference object rather than independently
   enumerating its fields;
5. constrain `OVERALL` and `ALTERNATIVES` scope shapes without permitting unknown,
   empty, or duplicate alternative identifiers;
6. preserve every current valid alternative subset for `ALTERNATIVES` scope and omit
   that scope branch when the current artifact contains no alternatives;
7. construct a deterministic request-specific `RiskAssessment` JSON Schema;
8. carry that request-specific schema as clearly delimited untrusted request data for
   all structured-output modes, without placing payload-derived values in the trusted
   system instruction;
9. use the same logical schema as the provider
   `response_format.json_schema.schema` in `JSON_SCHEMA` mode;
10. keep the authoritative static output model, semantic role instruction, participant
    contract, and three-artifact payload unchanged;
11. preserve all current parsing, participant validation, stage-failure, and
    orchestration behavior;
12. fail safely before network I/O when the Risk Reviewer payload cannot produce a
    trustworthy request schema;
13. provide deterministic tests proving exact catalog coverage, exclusion, scope
    narrowing, correlation, immutability, request construction, and regression safety;
14. provide an opt-in local evaluation procedure that records whether Risk Reviewer,
    Critic, and Coordinator complete without treating a selected successful generation
    as proof of reliability.

### 3.2 Out of Scope

Slice 7.2 SHALL NOT:

- change `LLMPort`, participant signatures, domain models, Review lifecycle, or stage
  order;
- relax, bypass, duplicate-repair, or replace `RiskReviewer._validate_structure`, scope
  validation, or basis-reference validation;
- silently rewrite a source, field, kind, ID, characteristic, value, scope, or model
  output;
- reinterpret an upstream Analyst constraint as an assumption or correct the semantic
  quality of already trusted upstream artifacts;
- require the Risk Reviewer to produce a risk, mitigation, category, residual
  uncertainty, or overall observation;
- constrain descriptions, severity judgments, mitigations, or other free risk content
  to predetermined conclusions;
- add retries, fallback models, provider routing, schema-mode downgrade, or prompt
  repair;
- make provider-side schema conformance sufficient for trusted Review state;
- generate new dynamic schemas for Analyst, Solution Architect, or Coordinator;
- alter the approved Slice 7.1 Critic schema semantics;
- introduce a generic rules engine, JSONPath system, provider SDK, agent framework, or
  new runtime dependency;
- add UI, persistence, history, RAG, tools, autonomous action, or production telemetry;
- log full request payloads or generated schemas by default.

## 4. User Stories

### US1 — Prevent invalid Risk Reviewer basis combinations

As an operator, I want a guided Risk Reviewer request to offer only basis references
valid for the current Review so that a capable compatible model cannot combine the
source, classification, identifier, and value of different upstream items.

#### Acceptance criteria

1. Every offered basis reference is accepted by the current Risk Reviewer resolver for
   the same three-artifact snapshot.
2. `REVIEW_INPUT` offers only present, non-blank, unambiguously resolvable values from
   its six approved fields, with each complete reference binding the exact field and
   value.
3. `PROBLEM_ANALYSIS` offers only findings from the five approved collections, with
   exact `kind`, text, and canonical optional-ID semantics.
4. `SOLUTION_ALTERNATIVE` offers only current alternatives and their approved
   description, advantage, disadvantage, assumption, implementation-complexity, and
   relevant-constraint characteristics.
5. A relevant-constraint basis preserves its exact structured constraint reference;
   it is not flattened into an ID or text string.
6. Complete reference objects are correlated; fields from two legal references cannot
   form a third illegal Cartesian-product combination.
7. Empty or absent optional collections contribute no fabricated basis alternative.
8. When the current contract accepts more than one representation of the same target,
   guidance may expose one stricter canonical representation, such as retaining an
   available disambiguating finding ID.

### US2 — Constrain affected scope to current alternatives

As a reviewer, I want alternative-specific risk scope to name only alternatives in the
current Review so that a valid-looking risk cannot point to an invented or stale option.

#### Acceptance criteria

1. `OVERALL` scope permits no alternative IDs.
2. `ALTERNATIVES` scope requires at least one unique ID and permits only identifiers
   present in the current `SolutionAlternatives`.
3. One, several, or all current alternatives remain selectable; the schema does not
   force one preferred alternative or a canonical ordering.
4. With zero current alternatives, `OVERALL` remains valid and `ALTERNATIVES` scope is
   not offered.
5. The existing participant repeats scope validation after generation.

### US3 — Preserve Risk Reviewer semantics and provider neutrality

As a maintainer, I want this reliability correction isolated behind the adapter
boundary so that the Risk Reviewer remains a replaceable participant with unchanged
domain responsibilities.

#### Acceptance criteria

1. `LLMPort` and the Risk Reviewer participant signature remain unchanged.
2. Risk Reviewer sends the same three payload keys and consumes the same three trusted
   upstream artifacts.
3. `RiskAssessment`, `Risk`, `RiskScope`, and all basis-reference domain models remain
   authoritative and unchanged.
4. Critic continues using its approved Slice 7.1 dynamic schema; Analyst, Solution
   Architect, and Coordinator retain their current static-schema behavior.
5. `JSON_OBJECT` and `PROMPT_ONLY` receive the dynamic schema only as delimited
   untrusted data; `JSON_SCHEMA` additionally sends it to the compatible provider.
6. No provider-specific type crosses into participants, application, or domain.
7. A fully empty `RiskAssessment`, a zero-risk result with observations, and a risk with
   any currently optional prose field absent remain representable.

### US4 — Fail closed during request-schema construction

As a user, I want invalid or ambiguous Risk Reviewer request context to fail visibly
before provider invocation so that schema construction cannot guess or silently widen
the allowed evidence.

#### Acceptance criteria

1. Missing, extra, malformed, or wrong-typed required payload artifacts are rejected.
2. Exact duplicate alternatives that identify the same already-resolved semantic target
   are deterministically deduplicated.
3. An emitted reference shape that could identify different current targets, or any
   other candidate the trusted resolver would consider ambiguous, is excluded
   completely; schema construction does not guess which target was intended.
4. An ambiguous candidate does not prevent other unambiguous basis references from
   remaining available.
5. If no resolvable basis reference exists, zero-risk output remains valid, but the
   schema cannot produce a `Risk` whose required basis would be ungrounded.
6. Construction failure performs no HTTP request.
7. The public error is fixed, provider-neutral, and contains no payload values, schema,
   raw response, credentials, or provider details.
8. Existing orchestration maps the adapter exception through current safe failure
   behavior; this slice adds no Review error category.

### US5 — Verify the correction deterministically and live

As a maintainer, I want deterministic schema tests plus controlled local evidence so
that contract guidance is evaluated separately from model judgment and hardware limits.

#### Acceptance criteria

1. Default tests require no endpoint, GPU, credentials, downloaded model, or network.
2. Tests cover every allowed source, field, kind, characteristic, constraint-value
   shape, and scope family.
3. Tests cover the exact invalid Problem Analysis kind/ID/text combinations observed in
   the five-run Slice 7.1 campaign.
4. Tests prove deterministic byte-equivalent schemas for semantically equivalent
   payloads and prove that inputs and nested values are not mutated.
5. Adapter request tests assert that the delimited data-message schema and provider
   schema are the same logical snapshot and that payload-derived values never enter the
   system instruction.
6. Live evaluation records stage outcomes and raw diagnostic output only when
   explicitly authorized.
7. Live results are reported as a fixed repeated-run distribution; retry-until-success,
   replacement, or selective deletion is not accepted as evidence.

## 5. Functional Requirements

### RDS-FR-001 — Unchanged Port

The feature SHALL operate through the existing `generate_structured` signature.
Payload-dependent Risk Reviewer schema generation is an adapter implementation detail.

### RDS-FR-002 — Exact Role Activation

Risk Reviewer schema generation SHALL activate only when `role` is exactly
`risk_reviewer`. Critic SHALL retain its approved dynamic behavior, unknown roles SHALL
retain existing failure behavior, and the remaining supported roles SHALL retain their
current static behavior.

### RDS-FR-003 — Required Context Snapshot

Request-constraint construction SHALL consume one snapshot of the supplied Risk
Reviewer payload and SHALL require exactly the three approved artifact keys. It SHALL
not read mutable global Review state, perform network I/O, or resolve data from another
Review execution.

### RDS-FR-004 — Existing Resolver Semantics Are Canonical

Every exposed canonical basis SHALL match current risk-basis shape and resolution
semantics. Every current target for which at least one reference resolves exactly and
unambiguously SHALL have at least one exposed canonical reference. Targets that cannot
be named unambiguously under the current trusted contract SHALL not be guessed. Tests
SHALL detect drift between generated constraints and participant validation.

### RDS-FR-005 — Correlated Basis Alternatives

Each allowed basis SHALL be represented as one atomic closed-object alternative
containing only its exact legal fields. Source, field, kind, ID, alternative ID,
characteristic, and value SHALL NOT be modeled as independent enums that permit an
invalid Cartesian product.

### RDS-FR-006 — Canonical Optional Finding IDs

For a Problem Analysis finding with an ID, the canonical guided reference SHALL retain
that exact ID and text. For a finding without an ID, an ID field SHALL be absent and the
text-only reference SHALL be offered only when it resolves to exactly one finding of
the selected kind.

### RDS-FR-007 — Exact ReviewInput References

Each ReviewInput alternative SHALL pair one approved field with one exact value from
that field. Absent or blank optional scalars, blank collection values, and ambiguous
repeated collection values SHALL produce no alternative. Text SHALL not be trimmed,
case-folded, paraphrased, or copied between fields.

### RDS-FR-008 — Exact Solution-Alternative References

Each Solution Alternative alternative SHALL bind one existing alternative ID, one
approved characteristic, and its exact corresponding value. Repeated collection values
or structured constraints that do not resolve uniquely within that alternative SHALL
not be offered. Structured relevant constraints SHALL preserve their full exact object
shape.

### RDS-FR-009 — Context-Bound Scope

The request schema SHALL correlate the two legal scope shapes. `OVERALL` SHALL require
an empty `alternative_ids` collection. `ALTERNATIVES` SHALL require one or more unique
IDs drawn only from the current alternatives. When there are no alternatives, only
`OVERALL` SHALL be representable.

### RDS-FR-010 — Authoritative Outer Contract

The request-specific constraint SHALL derive from the authoritative `RiskAssessment`
contract and SHALL narrow only current basis-reference selection and affected-scope
selection. Every other field, enum, requiredness, closed-object behavior, optionality,
collection cardinality, and bounded-output behavior SHALL remain equivalent to Slice 7.
The exact schema-transformation strategy is deferred to the plan and data model.

### RDS-FR-011 — Preserve Empty and Optional Results

The request constraint SHALL preserve a fully empty `RiskAssessment`, a zero-risk
assessment with observations, and risks whose optional `category`, `mitigation`, or
`residual_uncertainty` is absent. Available basis references or alternatives SHALL not
force risk creation or artificial completeness.

### RDS-FR-012 — One Schema Snapshot per Call

Request construction SHALL create one logical schema from one immutable semantic
snapshot per Risk Reviewer call and use it in the delimited data message and, in
`JSON_SCHEMA` mode, provider guidance. It SHALL not rebuild from a later or mutated
payload state.

### RDS-FR-013 — Deterministic Serialization

Equivalent semantic catalogs and current alternative sets SHALL produce byte-equivalent
serialized schemas. Ordering SHALL be application-controlled and independent of hash
iteration.

### RDS-FR-014 — Payload Immutability

Schema and request construction SHALL not mutate the caller's mapping, nested
collections, structured constraint references, or artifact values.

### RDS-FR-015 — Safe Construction Failure

Invalid dynamic-schema input or an unsatisfied internal narrowing invariant SHALL
produce a distinguishable provider-neutral construction failure with a fixed safe
public message. Exact error representation is deferred to the plan and data model.

### RDS-FR-016 — No Trust Promotion

Provider conformance to the request-specific schema SHALL not bypass direct JSON
parsing, `RiskAssessment` structural validation, scope validation, or basis-reference
validation against current trusted artifacts.

### RDS-FR-017 — Mode Behavior

- `JSON_SCHEMA`: the untrusted data message includes the dynamic schema and
  `response_format` carries its strict form.
- `JSON_OBJECT`: the untrusted data message includes the dynamic schema and response
  format remains `{ "type": "json_object" }`.
- `PROMPT_ONLY`: the untrusted data message includes the dynamic schema and response
  format remains absent.

No fallback, provider probing, or automatic mode downgrade is permitted. Only a
compatible provider honoring `JSON_SCHEMA` guidance is expected to prevent invalid
combinations during decoding; existing local validation remains mandatory in every
mode.

### RDS-FR-018 — Bounded Size Without Silent Truncation

The constraint SHALL include at least one canonical legal basis for every unambiguous
current target and every current alternative ID required for scope. It SHALL not
silently truncate the catalog to reduce prompt size. Deterministic tests SHALL record
schema size for high-cardinality contract-valid fixtures. A provider-specific request
limit causes visible failure or requires an explicitly selected compatible profile or
mode; the adapter does not weaken constraints automatically.

### RDS-FR-019 — Data Minimization and Instruction Isolation

Only values already present in the three-artifact Risk Reviewer payload and necessary
to express a legal basis or scope may appear in the request-specific schema. Secrets,
endpoint details, unrelated environment values, hidden reasoning, and previous-Review
data SHALL not appear. Payload-derived text SHALL remain escaped in the untrusted data
message and SHALL NOT enter the trusted system instruction.

### RDS-FR-020 — Observability Policy

The generated schema and full request payload SHALL not be logged by default. Existing
opt-in raw-output observation continues to capture provider output, not the complete
request or schema.

### RDS-FR-021 — Live Evaluation

The documented local evaluation SHALL run one fixed scenario at least five times with
no automatic retries. Each invocation SHALL use unique output paths and SHALL not
replace or overwrite another run. The evaluation SHALL record model/image/profile,
relevant context limits, elapsed time, each stage outcome, the failed contract family
when known, whether Critic and Coordinator completed, and whether any observed Slice
7.1 Risk Reviewer kind/ID/text mismatch recurred.

## 6. Edge Cases

1. Minimal ReviewInput with absent or blank optional title/objective and empty or
   blank-valued collections.
2. Duplicate ReviewInput collection text that cannot be resolved uniquely.
3. Problem Analysis findings with and without optional IDs.
4. Duplicate Problem Analysis text within one kind, including a mixture of identified
   and unidentified findings.
5. The same text appearing legally under different Problem Analysis kinds.
6. Zero alternatives with required generation notes.
7. Two or three alternatives with repeated characteristic text.
8. Duplicate text within one alternative characteristic collection.
9. Identical text or constraint objects in different alternatives.
10. A relevant constraint represented by structured `source`, `kind`, and `value`.
11. A duplicated relevant constraint that the current exact resolver treats as
    ambiguous.
12. `OVERALL` scope, every non-empty subset of current alternative IDs, reordered IDs,
    duplicate IDs, and unknown IDs.
13. No resolvable basis candidates while zero-risk output remains valid.
14. Fully empty `RiskAssessment` and absent optional Risk prose fields.
15. Unicode, JSON-significant characters, and prompt-injection-like text in exact
    upstream values.
16. Payload mappings supplied in different key orders.
17. Caller mutation after schema snapshot creation.
18. Provider ignores or cannot enforce `JSON_SCHEMA` and returns invalid output.
19. Dynamic schema exceeds a provider-specific request or context limit.

## 7. Success Criteria

### SC-001 — Deterministic basis parity

Every basis alternative emitted from deterministic fixtures is accepted by the
existing Risk Reviewer resolver for the same snapshot. Every observed constraint-as-
assumption and mismatched kind/ID/text combination is absent.

### SC-002 — Deterministic scope parity

Every guided `affected_scope` accepted by deterministic fixtures passes the current
scope validator; `ALTERNATIVES` cannot contain an unknown or duplicate ID and is absent
when there are no current alternatives.

### SC-003 — Observed failure prevention

With a compatible provider honoring `JSON_SCHEMA`, the exact Slice 7.1 campaign failure
class is not permitted by the guided Risk Reviewer schema: a Problem Analysis
constraint cannot be emitted as an assumption, and an ID/text pair cannot be combined
unless it identifies one exact finding of that kind.

### SC-004 — Regression safety

The complete deterministic suite, Ruff, mypy, dependency checks, and applicable
Compose/configuration checks pass without changing trusted Risk Reviewer or Critic
semantics.

### SC-005 — Local evidence

At least five explicitly initiated fixed-scenario local runs are recorded without
retry-until-success selection. A run may still be incomplete, but any remaining failure
is classified separately from the prevented Risk Reviewer basis/scope patterns and no
live result replaces deterministic acceptance evidence.

## 8. Assumptions

1. OpenAI-compatible providers support different JSON Schema subsets; Slice 7.2
   guarantees deterministic request construction and local validation, not universal
   provider acceptance.
2. vLLM 0.8.5 with the current local Qwen3-4B-AWQ profile is the initial live evaluation
   target because it fits the available GPU and already accepts the Slice 7.1 schema
   subset.
3. Current participant payloads originate from already validated domain artifacts.
4. Static Pydantic schemas remain the source of outer output-shape truth.
5. Exact basis copying is intentional review-local traceability, not a request for
   hidden chain-of-thought.
6. Upstream artifacts may be semantically imperfect while structurally trusted. This
   slice constrains references to those artifacts but does not reassess or correct
   their content.
7. Provider compliance with request-time guidance is an optimization aid; local trusted
   validation remains the security and correctness boundary.

## 9. Dependencies and Constraints

- No production dependency change is expected.
- Pydantic v2 and standard-library JSON remain sufficient.
- ADR-0001 remains authoritative for local structured validation and the non-trust
  status of provider schema enforcement.
- ADR-0002 remains valid; no provider access pattern, retry behavior, or transport
  abstraction changes.
- Slice 7.1 Critic request-specific schema behavior must remain intact.
- The Constitution's role integrity, validation, traceability, visible failure,
  provider independence, minimal architecture, deterministic testing, security
  minimization, and incremental-delivery requirements are mandatory.

## 10. Review Gate

Before approval of this specification, confirm:

1. the observed five-run failure is correctly treated as a request-contract gap, not
   proof of a model, vLLM, or GPU defect;
2. request-specific narrowing belongs at the adapter boundary and does not redefine
   trusted domain truth;
3. the three-artifact payload is sufficient to enumerate every unambiguous canonical
   Risk Reviewer basis and current alternative scope ID;
4. complete correlated basis alternatives are preferable to independent field enums;
5. dynamic scope narrowing preserves every valid current alternative subset and valid
   overall-only behavior with zero alternatives;
6. zero-risk and optional Risk shapes remain valid even when no basis can be offered;
7. no retry, silent repair, mode downgrade, or validation relaxation enters this slice;
8. Slice 7.1 Critic behavior and the other roles remain semantically unchanged;
9. live five-run evidence is not treated as a reliability guarantee or a substitute
   for deterministic tests;
10. enforcement claims remain limited to compatible providers honoring `JSON_SCHEMA`;
11. payload-derived exact values remain confined to untrusted request data.

No `plan.md`, `data-model.md`, or `tasks.md` SHALL be created and no implementation
SHALL begin until this `spec.md` has been reviewed and explicitly approved by the user.
After approval, the plan will be created, self-reviewed, and presented as the next
independent Spec Kit gate.
