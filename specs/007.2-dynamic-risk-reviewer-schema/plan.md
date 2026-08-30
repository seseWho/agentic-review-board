# Implementation Plan: Context-Bound Risk Reviewer Output Schema v0.1

**Branch:** `007.2-dynamic-risk-reviewer-schema`  
**Specification:** `specs/007.2-dynamic-risk-reviewer-schema/spec.md` — Approved  
**Status:** Draft — self-reviewed, awaiting user approval

## 1. Objective

Extend the existing request-specific schema mechanism with the smallest explicit Risk
Reviewer path. With a compatible provider honoring `JSON_SCHEMA`, generated risk bases
and affected scopes are limited to combinations resolvable against the current Review:

```text
validated ReviewInput + ProblemAnalysis + SolutionAlternatives
                              ↓
              immutable Risk Reviewer payload snapshot
                              ↓
       exact allowed-basis catalog + current alternative IDs
                              ↓
          authoritative static RiskAssessment JSON Schema
                              ↓ narrow basis items and RiskScope
          request-specific Risk Reviewer output schema
                    ↙                         ↘
 static trusted system instruction       JSON_SCHEMA response_format
                    ↓                         ↙
 delimited user/data message containing payload + dynamic schema
                              ↓
                       provider response
                              ↓
 direct JSON parsing + existing Risk Reviewer structural/context validation
                              ↓
                    trusted RiskAssessment or visible failure
```

Provider guidance reduces invalid generation. The existing participant remains the
trust boundary and repeats every structural, scope, and basis check.

## 2. Observed Limitation

The five fixed Qwen3-4B-AWQ runs from the Slice 7.1 evaluation completed Analyst and
Solution Architect, then failed at Risk Reviewer. The raw outputs used structurally
valid Problem Analysis basis objects but combined:

- `kind=ASSUMPTION` with IDs belonging to constraint findings;
- assumption text that did not match the referenced constraint ID;
- source/kind/ID/text fields that were individually schema-valid but jointly
  unresolvable in the current `ProblemAnalysis`.

The current participant behaved correctly: no invalid `RiskAssessment` entered trusted
state, Critic and Coordinator remained `PENDING`, and the Review became `INCOMPLETE`.
The gap is therefore in request-time correlation, not in trusted validation, GPU
capacity, or the Review lifecycle.

## 3. Design Principles

### 3.1 Narrow generation; preserve authoritative validation

The dynamic schema is untrusted-boundary guidance. `RiskAssessment.model_validate`,
`RiskReviewer._validate_scope_references`, and
`RiskReviewer._validate_basis_references` remain unchanged and mandatory.

### 3.2 Keep domain and port contracts unchanged

The adapter already receives exact role and payload. `LLMPort`, Risk Reviewer inputs,
domain models, participant signatures, and orchestration require no widening.

### 3.3 Extend the established infrastructure mechanism

Reuse `RequestOutputSchema`, deterministic serialization, strict-schema normalization,
safe `LLMRequestSchemaError`, and the delimited untrusted request-schema section from
Slice 7.1. Add explicit Risk Reviewer semantics rather than a generic rule language.

### 3.4 Preserve one authoritative outer model

Begin with `RiskAssessment.model_json_schema()` and narrow only the Risk basis-item and
affected-scope portions. Do not hand-maintain a second complete RiskAssessment schema.

### 3.5 Correlate complete objects

Each basis branch binds one complete legal source-specific object. Each scope branch
binds `kind` to one exact legal alternative-ID sequence. Independent field enums are
not sufficient because they recreate invalid Cartesian products.

### 3.6 Pure deterministic construction

Snapshot, catalog, scope, and schema builders perform no I/O, read no environment or
global Review state, mutate no caller data, and use application-controlled ordering.

## 4. Technical Context

- Language: Python 3.12+
- Validation: Pydantic v2
- HTTP: existing HTTPX-based OpenAI-compatible adapter
- Schema transport: Chat Completions `response_format.type=json_schema`
- Initial live target: vLLM 0.8.5 with `Qwen/Qwen3-4B-AWQ`
- Known compatible schema subset: closed objects, `oneOf`, `const`, required fields,
  and bounded arrays as exercised by Slice 7.1
- Tests: pytest with deterministic fixtures and injected HTTPX transport
- Runtime dependency changes: none
- ADR changes: none expected; ADR-0001 and ADR-0002 remain applicable

## 5. Proposed Component Changes

### 5.1 Extend `dynamic_schemas.py`

Retain the existing module and add a focused Risk Reviewer section containing:

- an immutable three-artifact payload snapshot;
- immutable allowed-basis catalog entries with emitted identity and semantic target
  identity kept separately;
- explicit enumeration for ReviewInput, Problem Analysis, and Solution Alternative
  basis families;
- deterministic ambiguity normalization;
- deterministic current-alternative scope enumeration;
- closed basis-reference and scope schema-branch builders;
- RiskAssessment narrowing and serialization functions;
- a small closed dispatcher for the two dynamic roles: `risk_reviewer` and `critic`.

Only JSON detachment/serialization, request-schema ownership, and role dispatch are
shared. Risk Reviewer and Critic catalog/resolver semantics remain explicitly named and
separate. The module does not become a schema framework or accept externally supplied
rules.

### 5.2 Dynamic request context

Introduce one small immutable infrastructure value that owns, for a dynamic role call:

- the validated serialized payload snapshot; and
- the serialized request-specific `RequestOutputSchema`.

A closed builder returns this value for exactly `critic` or `risk_reviewer`, and no
dynamic context for the three static roles. This prevents the adapter from separately
serializing mutable payload data and rebuilding a schema from a later state.

The existing general schema helper continues returning the static strict schema for
static roles and the role-specific schema for the two approved dynamic roles. Existing
Critic behavior remains covered by regression tests.

Exact type and function names are deferred to `data-model.md`.

### 5.3 Adapter integration

`OpenAICompatibleLLMAdapter.generate_structured` will:

1. resolve the exact supported role as it does today;
2. ask the closed dynamic dispatcher for one call context;
3. use the context-owned serialized payload and request schema for Risk Reviewer or
   Critic;
4. use the existing plain payload serializer for Analyst, Solution Architect, and
   Coordinator;
5. append the dynamic schema to the user/data message only for the two dynamic roles;
6. reuse an independent document from the same serialized schema in `JSON_SCHEMA`
   response guidance;
7. preserve current system instructions, modes, headers, timeouts, credentials, HTTP
   mapping, parsing, and observer behavior.

Schema construction completes before credentials are read and before HTTP or output
observation. The downstream request-building path stays common; no second Risk Reviewer
transport path is introduced.

### 5.4 Unchanged prompt and error contracts

`RolePromptDefinition` continues owning the static semantic instruction, authoritative
output model, and cached static schema. It does not cache payload-specific values.

The existing `LLMRequestSchemaError` remains sufficient. Slice 7.2 adds no error class,
Review error kind, provider detail, or payload-bearing diagnostic.

## 6. Risk Reviewer Payload Snapshot

The builder accepts exactly:

```text
review_input
problem_analysis
solution_alternatives
```

The detached values are validated with their existing authoritative Pydantic models:

- `ReviewInput`;
- `ProblemAnalysis`;
- `SolutionAlternatives`.

The snapshot owns one deterministic JSON serialization and the three frozen validated
artifacts. Missing or extra top-level keys, wrong value types, non-JSON constants, and
contract-invalid artifacts raise the existing safe schema-construction error.

The original mapping and all nested objects remain untouched. The snapshot is not
written to Review state and cannot read artifacts from another execution.

## 7. Allowed Risk-Basis Enumeration

Enumeration mirrors the current Risk Reviewer resolvers exactly.

### 7.1 ReviewInput bases

Use `source=REVIEW_INPUT` with exact `field` and `value` for:

- `description` when non-blank;
- present, non-blank `title` and `objective`;
- each non-blank uniquely occurring value in `constraints`, `context`, and
  `stated_facts`.

Repeated text within the selected ReviewInput collection is excluded because the
current resolver requires exactly one match. Text is not trimmed, normalized,
case-folded, or moved between fields.

### 7.2 Problem Analysis bases

Use `source=PROBLEM_ANALYSIS` and the exact collection mapping:

- `FACT` → `facts`;
- `CONSTRAINT` → `constraints`;
- `ASSUMPTION` → `assumptions`;
- `MISSING_INFORMATION` → `missing_information`;
- `UNCERTAINTY` → `uncertainties`.

An ID-bearing finding uses canonical `kind + id + text` only when that exact pair has
one match in the selected collection. An ID-less finding uses `kind + text`, omits the
`id` field, and is offered only when the text has one match in that collection.

This exact mapping removes the observed possibility of pairing a constraint ID/text
with `kind=ASSUMPTION`.

### 7.3 Solution Alternative bases

Use `source=SOLUTION_ALTERNATIVE`, one exact current `alternative_id`, and one of the
approved characteristics:

- `DESCRIPTION`: exact description;
- `ADVANTAGE`: each owner-local unique advantage;
- `DISADVANTAGE`: each owner-local unique disadvantage;
- `ASSUMPTION`: each owner-local unique assumption;
- `IMPLEMENTATION_COMPLEXITY`: exact qualitative enum value;
- `RELEVANT_CONSTRAINT`: each owner-local unique exact structured
  `ConstraintReference`.

Text collection values and structured constraints repeated within the same alternative
are excluded because the participant's exact resolver would find more than one match.
Equal values in different alternatives remain legal because `alternative_id`
disambiguates them.

`generation_notes`, alternative names, and any other fields do not become bases because
the current Risk basis contract does not expose them.

## 8. Duplicate and Ambiguity Policy

Each candidate tracks:

- its exact emitted wire identity; and
- the one semantic target identity it represents in the current snapshot.

Normalization follows these rules in deterministic candidate order:

- same wire identity + same target identity → retain one branch;
- different wire identities for different resolvable targets → retain both, even when
  visible text is equal;
- same wire identity collapsing different targets → exclude that wire identity
  completely;
- source-local uniqueness rules are applied before global normalization;
- an ambiguous candidate never removes unrelated unambiguous candidates.

Wire identity includes nested structured constraint content using canonical JSON value
semantics rather than mutable object identity. Catalog order follows artifact family,
contract kind order, artifact tuple order, and characteristic order; it does not sort
user text or depend on set/dictionary iteration.

## 9. Allowed Affected-Scope Enumeration

The scope catalog is derived only from current ordered alternative IDs.

### 9.1 Overall branch

Always expose exactly:

```json
{
  "kind": "OVERALL",
  "alternative_ids": []
}
```

### 9.2 Alternatives branches

For each sequence length from one through the number of current alternatives, expose
every ordered permutation without replacement. This preserves every scope accepted by
the current tuple-based contract while preventing empty, duplicate, unknown, and stale
IDs.

Current `SolutionAlternatives` permits zero, two, or three alternatives, so this yields:

- zero alternatives: no `ALTERNATIVES` branches;
- two alternatives: four branches;
- three alternatives: fifteen branches.

Each complete scope is one closed `oneOf` branch using exact `const` values. This avoids
depending on provider support for `uniqueItems` and keeps the schema vocabulary within
the `oneOf`/`const` family already exercised with vLLM 0.8.5. Array-valued `const`
compatibility is still an explicit Slice 7.2 live-smoke check. No preferred ordering or
alternative is introduced.

## 10. Dynamic RiskAssessment Schema Strategy

### 10.1 Authoritative base and invariant checks

Create an owned strict copy of `RiskAssessment.model_json_schema()`. Before narrowing,
verify the expected authoritative locations for:

- the root `risks` array;
- the `Risk` definition and its `basis` items;
- the `Risk.affected_scope` reference; and
- the `RiskScope` definition.

Unexpected schema drift raises `LLMRequestSchemaError`; it never falls back to a broad
schema.

### 10.2 Basis-item narrowing

Replace the Risk `basis` item schema with `oneOf` over all exact allowed-basis branches.
Each branch is a closed object with required fields exactly matching its source-specific
wire representation:

- ReviewInput: `source`, `field`, `value`;
- Problem Analysis: `source`, `kind`, `text`, plus `id` only when canonical;
- Solution Alternative: `source`, `alternative_id`, `characteristic`, `value`.

String values use exact `const`. `RELEVANT_CONSTRAINT.value` is a nested closed object
whose `source`, `kind`, and `value` are each exact constants. The Risk `basis` array is
explicitly non-empty and retains the existing strict maximum of ten items.

### 10.3 Scope narrowing

Replace the `RiskScope` definition with `oneOf` over the overall branch and every legal
current alternative sequence from §9. Every branch is closed and requires exactly
`kind` and `alternative_ids`.

### 10.4 Empty basis catalog

A contract-valid current payload always supplies at least the non-blank ReviewInput
description, so normal construction has at least one legal basis. Nevertheless, the
narrowing function handles an empty catalog without widening: it constrains the root
`risks` array to zero items, preserving a fully empty or observation-only
`RiskAssessment`. It does not emit an unconstrained basis branch.

### 10.5 Preserve all other RiskAssessment semantics

No other schema area changes. In particular:

- root `risks` and `overall_observations` may remain empty;
- `category`, `mitigation`, and `residual_uncertainty` retain current optional/null
  behavior under strict provider schema normalization;
- severity remains exactly `LOW`, `MEDIUM`, or `HIGH`;
- risk IDs, descriptions, overall observations, and all prohibited extra fields retain
  the current static contract;
- outer arrays retain Slice 7 bounds.

### 10.6 Compatibility behavior

Deterministic tests verify the generated standard JSON Schema. A marked live smoke test
checks that the configured vLLM server accepts a minimal real Risk Reviewer dynamic
schema. Universal provider compatibility is not inferred, and the adapter performs no
mode fallback or constraint removal.

## 11. Trusted Instruction and Untrusted Data Message

The system message remains unchanged and application-controlled:

- Risk Reviewer's semantic instruction;
- the authoritative static RiskAssessment schema;
- the existing instruction to return one concrete schema-conforming instance.

No exact payload-derived value enters that message.

For Risk Reviewer and Critic, the user/data message contains:

```text
UNTRUSTED_PAYLOAD_JSON_BEGIN
role-specific serialized payload
UNTRUSTED_PAYLOAD_JSON_END

UNTRUSTED_REQUEST_SCHEMA_JSON_BEGIN
role-specific request schema
UNTRUSTED_REQUEST_SCHEMA_JSON_END
```

The dynamic schema is serialized once from the immutable snapshot. Embedded Unicode,
quotes, newlines, JSON-significant text, and delimiter-looking or prompt-injection-like
values remain JSON-escaped untrusted data. `JSON_SCHEMA` receives an independent parsed
document from the same serialization so provider request mutation cannot alias the data
message.

`JSON_OBJECT` and `PROMPT_ONLY` carry the dynamic schema only as untrusted guidance and
make no decoding-enforcement guarantee.

No new logging path is added. The complete payload and generated request schema remain
absent from default logs and safe public errors; the existing opt-in observer continues
to receive only the parsed provider output.

## 12. Error and Failure Flow

```text
invalid Risk Reviewer payload / catalog invariant / base-schema drift
                              ↓
                  existing LLMRequestSchemaError
                              ↓
       no credential read, HTTP request, or output observation
                              ↓
       existing participant/orchestrator EXECUTION failure mapping
                              ↓
  Risk Reviewer FAILED; Critic + Coordinator PENDING; Review INCOMPLETE
```

A compatible provider rejecting a syntactically valid schema remains an
`LLMHTTPStatusError`. Returned JSON that violates the schema still passes through direct
parsing and existing Risk Reviewer validation, producing the existing safe
`OUTPUT_VALIDATION` behavior when applicable. No partial RiskAssessment is trusted.

## 13. Testing Strategy

### 13.1 Snapshot and catalog unit tests

Use minimal/full deterministic payloads to verify exact keys, authoritative model
validation, all three basis sources, all five Problem Analysis kinds, all six Solution
Alternative characteristics, optional IDs, blank/absent values, duplicate text,
structured constraints, Unicode, JSON-significant content, deterministic order, safe
failure, and deep immutability.

### 13.2 Scope unit tests

Verify overall scope, zero alternatives, every legal sequence for two and three
alternatives, exact branch counts, stable ordering, and absence of empty, duplicate, or
unknown alternative sequences.

### 13.3 Schema unit tests

Assert branch-level correlation rather than one brittle whole-document snapshot. Prove:

- every branch is closed and contains only its exact fields;
- the observed constraint-as-assumption shapes are absent;
- optional Problem Analysis IDs are present or absent canonically;
- structured constraints remain nested and exact;
- Risk basis is non-empty when a Risk exists;
- RiskScope is replaced with exact current branches;
- fully empty and observation-only assessments remain valid;
- unrelated strict RiskAssessment definitions remain unchanged;
- equivalent payloads serialize to byte-identical schemas;
- high-cardinality fixtures are complete, untruncated, and have recorded schema size;
- unexpected authoritative schema structure fails safely.

### 13.4 Participant parity and regression tests

For every catalog basis, construct the smallest valid Risk and prove the existing Risk
Reviewer resolver accepts it against the same snapshot. For every scope branch, prove
the existing scope validator accepts it. Retain direct negative tests for the observed
kind/ID/text mismatch and for unknown scope IDs.

Critic dynamic-schema tests remain unchanged and passing. Add dispatch tests proving:

- `risk_reviewer` selects only Risk Reviewer dynamic construction;
- `critic` retains Slice 7.1 construction;
- Analyst, Solution Architect, and Coordinator retain static strict schemas;
- unknown roles retain current failure behavior.

### 13.5 Adapter request tests

Capture requests for all three modes and prove:

- Risk Reviewer payload and dynamic schema use one snapshot;
- the dynamic schema appears only in the delimited user/data message and, for
  `JSON_SCHEMA`, provider response guidance;
- both representations are logically identical but not mutably aliased;
- no payload-derived marker enters the system message;
- static roles retain Slice 7 behavior;
- Critic requests remain Slice 7.1-equivalent;
- invalid Risk Reviewer schema construction makes zero requests, reads no credential,
  and invokes no observer;
- provider output remains untrusted parsed mapping for participant validation.

### 13.6 Live compatibility and five-run evidence

Add an opt-in live smoke using a minimal valid three-artifact Risk Reviewer payload.
Then execute the fixed desktop-migration scenario at least five independently initiated
times with the approved local profile:

- use unique aggregate and raw-output paths for every run;
- assert paths do not exist before invocation;
- do not retry, replace, overwrite, or selectively delete runs;
- record profile/model/image/context, elapsed time, stage statuses, failure family, and
  whether the observed basis mismatch recurs;
- record Critic and Coordinator outcomes without requiring them to succeed for the
  evidence task to be complete.

### 13.7 Full quality gates

Run the complete deterministic pytest suite, Ruff, mypy, dependency consistency,
Compose configuration validation, and the explicitly opted-in live checks. A plausible
live response cannot replace deterministic evidence.

## 14. Requirements Traceability

| Specification requirement | Plan coverage | Verification strategy |
|---|---|---|
| RDS-FR-001 Unchanged Port | §§3.2, 5.3 | Port/import regression |
| RDS-FR-002 Exact Role Activation | §§5.1–5.3, 13.4 | Closed dispatch tests |
| RDS-FR-003 Required Context Snapshot | §6 | Exact-key/model/no-I/O tests |
| RDS-FR-004 Existing Resolver Semantics | §§7–8, 13.4 | Catalog-to-participant parity |
| RDS-FR-005 Correlated Basis Alternatives | §§3.5, 10.2 | Exact branch tests |
| RDS-FR-006 Canonical Optional IDs | §§7.2, 10.2 | ID present/absent/ambiguity tests |
| RDS-FR-007 Exact ReviewInput References | §7.1 | Field/value and duplicate tests |
| RDS-FR-008 Exact Solution References | §7.3 | Text/complexity/constraint parity |
| RDS-FR-009 Context-Bound Scope | §§9, 10.3 | Exhaustive 0/2/3 alternative tests |
| RDS-FR-010 Authoritative Outer Contract | §§3.4, 10.1, 10.5 | Schema comparison and drift failure |
| RDS-FR-011 Empty and Optional Results | §§10.4–10.5 | Empty/observation-only/optional tests |
| RDS-FR-012 One Schema Snapshot | §§5.2–5.3, 11 | Mutation and request-equivalence tests |
| RDS-FR-013 Deterministic Serialization | §§3.6, 8–11 | Byte-equivalence tests |
| RDS-FR-014 Payload Immutability | §§3.6, 6, 13.1 | Deep before/after assertions |
| RDS-FR-015 Safe Construction Failure | §§10.1, 12 | Safe message and zero-request tests |
| RDS-FR-016 No Trust Promotion | §§3.1, 12, 13.4 | Invalid provider-output regression |
| RDS-FR-017 Mode Behavior | §§5.3, 11, 13.5 | Three-mode captured requests |
| RDS-FR-018 No Silent Truncation | §§7–10, 13.3 | High-cardinality coverage/size test |
| RDS-FR-019 Data Minimization | §§6–11 | Schema-content/trust-boundary tests |
| RDS-FR-020 Observability | §§5.3–5.4, 12 | Error and observer regression |
| RDS-FR-021 Live Evaluation | §13.6 | Smoke plus five preserved runs |

Every approved specification requirement has an explicit design location and
verification path. The data model may refine internal names and immutable
representations but may not remove or weaken a row.

## 15. File Impact

Expected additions:

- `tests/unit/infrastructure/llm/test_dynamic_risk_schemas.py`;
- `tests/fixtures/risk_reviewer_2026-08-30_invalid_references.json` with a minimal
  synthetic regression case;
- `specs/007.2-dynamic-risk-reviewer-schema/live-evaluation.md` during the live-evidence
  tasks.

Expected modifications:

- `src/agentic_review_board/infrastructure/llm/dynamic_schemas.py`;
- `src/agentic_review_board/infrastructure/llm/openai_compatible.py`;
- `tests/unit/infrastructure/llm/test_dynamic_schemas.py` for shared dispatch/regression
  coverage only;
- `tests/unit/infrastructure/llm/test_openai_compatible.py`;
- `tests/live/test_llm_smoke.py`;
- local guide only if the Slice 7.2 commands or interpretation cannot be fully contained
  in its evaluation document.

Expected unchanged:

- `src/agentic_review_board/application/ports.py`;
- all files under `src/agentic_review_board/domain/`;
- all five participant implementations;
- `src/agentic_review_board/application/orchestrator.py`;
- execution-state and Review lifecycle models;
- prompt semantic instructions and role output models;
- error taxonomy and public messages;
- runtime configuration, composition, `compose.yaml`, and model profile values;
- dependency declarations.

## 16. Constitution Check

- **Role integrity:** Risk Reviewer still evaluates exposure; it does not rank,
  recommend, or control workflow.
- **Structured validation:** request guidance narrows generation while all trusted local
  validation remains mandatory.
- **Traceability:** exact current basis and alternative scope references are
  strengthened without reclassifying upstream content.
- **Human authority:** no decision or external-action authority changes.
- **Minimal architecture:** one existing focused module gains one explicit role-specific
  builder; no framework or dependency is added.
- **Provider independence:** all changes remain behind the current adapter boundary and
  use the existing provider-neutral port.
- **Deterministic testability:** snapshots, catalogs, scopes, and schemas are pure and
  testable without network or GPU.
- **Visible failure:** construction, provider, parse, and participant failures remain
  safe, distinct, and fail-closed.
- **Security minimization:** only necessary current payload values enter delimited
  untrusted data; schemas and full requests are not logged by default.
- **Incremental delivery:** one evidenced Risk Reviewer failure family and its closely
  coupled scope invariant are addressed.

No constitutional violation, production dependency change, or new ADR trigger is
identified.

## 17. Alternatives Considered

### A. Upgrade vLLM or change GPU/model first

Rejected as the primary correction: the observed output reached local validation and
failed an application contract correlation. More capacity may improve model quality but
does not encode the missing invariant.

### B. Strengthen prompt prose only

Rejected as the primary correction: prose does not make kind/ID/text or scope-ID
correlation machine-enforceable during compatible guided decoding.

### C. Relax or repair Risk Reviewer output

Rejected: reclassifying, rewriting, or guessing references violates fail-closed
validation and traceability.

### D. Automatic retry with validation feedback

Deferred: retry policy is outside this slice and can hide the frequency of invalid
generation without preventing illegal states.

### E. Change `LLMPort` to accept schemas

Rejected: the adapter already owns role definitions and receives all current payload
artifacts needed for request guidance.

### F. Use independent enums for source/kind/ID/value

Rejected: their Cartesian product is the exact failure class being corrected.

### G. Use `uniqueItems` plus an ID enum for affected scope

Not selected for the initial local profile: exact scope branches preserve all currently
valid sequences using the smaller `oneOf`/`const` vocabulary and avoid relying on the
additional `uniqueItems` keyword. The Slice 7.2 smoke must still verify array-valued
`const` with vLLM 0.8.5. Reconsider if alternative cardinality grows beyond the current
maximum of three.

### H. Generalize Critic and Risk Reviewer into a runtime rule engine

Rejected: the two roles have different domain resolvers and wire shapes. Sharing small
mechanical ownership/dispatch helpers is sufficient.

### I. Put payload-derived schema values in the system message

Rejected: user and upstream-model content remains untrusted even when JSON-escaped.
Static instructions stay privileged; exact dynamic values stay in delimited user/data
content and explicit provider guidance.

## 18. Plan Review Gate

Before approval of this plan, confirm:

1. all 21 approved RDS requirements are covered without domain or workflow expansion;
2. extending the existing module with explicit Risk Reviewer builders is preferable to
   either a second transport path or a generic framework;
3. catalog eligibility exactly mirrors current ReviewInput, Problem Analysis, and
   Solution Alternative resolver uniqueness;
4. `kind + id + text` is the canonical Problem Analysis representation when an ID
   exists;
5. structured relevant constraints remain exact nested objects;
6. exhaustive ordered scope branches preserve every currently valid 0/2/3-alternative
   behavior without relying on `uniqueItems`;
7. empty/observation-only RiskAssessment remains possible and Risk creation is never
   forced;
8. Slice 7.1 Critic behavior and the three static roles remain unchanged;
9. no retry, repair, mode downgrade, provider probing, or schema truncation is added;
10. payload-derived values remain outside the trusted system instruction;
11. five live runs are preserved evidence, not a reliability guarantee;
12. no new ADR or production dependency is required.

No `data-model.md` or `tasks.md` SHALL be created and no implementation SHALL begin
until this `plan.md` has been self-reviewed and explicitly approved by the user. After
approval, `data-model.md` will be created, self-reviewed, and presented as the next
independent Spec Kit gate.
