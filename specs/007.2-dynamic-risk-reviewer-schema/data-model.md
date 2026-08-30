# Data Model: Context-Bound Risk Reviewer Output Schema v0.1

**Branch:** `007.2-dynamic-risk-reviewer-schema`  
**Specification:** `specs/007.2-dynamic-risk-reviewer-schema/spec.md` — Approved  
**Plan:** `specs/007.2-dynamic-risk-reviewer-schema/plan.md` — Approved  
**Status:** Draft — self-reviewed, awaiting user approval

## 1. Purpose

Define the exact infrastructure values, identities, eligibility rules, ordering,
schema projections, and trust-boundary invariants required to build one context-bound
Risk Reviewer output schema from one current three-artifact payload.

These values exist only during request construction. They are not new Review-domain
entities, do not change `LLMPort`, do not alter the trusted `RiskAssessment` contract,
and never make provider output trusted.

## 2. Boundary Overview

```text
LLMPort role + Mapping[str, object]
                  ↓ exact closed dynamic-role dispatch
          RiskReviewerPayloadSnapshot
                  ↓ resolver-equivalent enumeration
          tuple[AllowedRiskBasis, ...]
                  ↓ current alternative IDs
              tuple[RiskScope, ...]
                  ↓ narrow authoritative RiskAssessment schema
             RequestOutputSchema
                  ↓ pair with snapshot serialization
            DynamicRequestContext
              ↙                         ↘
delimited user/data JSON         fresh JSON_SCHEMA document
              ↘                         ↙
               provider response remains untrusted
                              ↓
          existing RiskAssessment + scope/basis validation
```

Critic follows its existing Slice 7.1 branch through the same closed dispatcher. Static
roles receive no `DynamicRequestContext` and preserve Slice 7 behavior.

## 3. Model Inventory

### 3.1 New internal immutable values

| Model | Representation | Purpose |
|---|---|---|
| `RiskReviewerPayloadSnapshot` | frozen slotted dataclass | One detached and validated three-artifact payload |
| `AllowedRiskBasis` | frozen slotted dataclass | One canonical domain-valid basis plus private semantic target identity |
| `DynamicRequestContext` | frozen slotted dataclass | One validated serialized payload paired with its request-specific schema |

### 3.2 Existing internal values reused unchanged

| Model | Purpose in Slice 7.2 |
|---|---|
| `RequestOutputSchema` | Immutable canonical schema serialization and fresh provider documents |
| `CriticPayloadSnapshot` | Existing four-artifact Critic snapshot |
| `AllowedCriticReference` | Existing Critic reference catalog value |
| `AllowedContradictionSide` | Existing Critic reference/statement pair |
| `LLMRequestSchemaError` | Existing fixed safe construction failure |

### 3.3 Existing domain models reused unchanged

- `ReviewInput`
- `ReviewInputSource`
- `ProblemAnalysis`
- `ProblemAnalysisFindingKind`
- `SolutionAlternatives`
- `ConstraintReference`
- `RiskAssessment`
- `Risk`
- `RiskScope`
- `RiskScopeKind`
- `RiskBasisReference`
- `RiskBasisSource`
- `ReviewInputBasisReference`
- `ProblemAnalysisBasisReference`
- `SolutionAlternativeBasisReference`
- `SolutionAlternativeCharacteristicKind`

`AllowedRiskBasis` contains an existing validated basis-reference variant rather than
copying all mutually exclusive source-specific fields into a new nullable structure.

## 4. Exact Payload Detachment

### 4.1 Mechanical helper

The two dynamic roles may share one private mechanical operation conceptually equivalent
to:

```python
def _detach_exact_payload(
    payload: Mapping[str, object],
    *,
    expected_keys: frozenset[str],
) -> tuple[str, dict[str, object]]:
    ...
```

This is not a public payload abstraction or rule engine. It only:

1. confirms `payload` is a `Mapping`;
2. owns a shallow top-level dictionary;
3. confirms exact key count and exact key set;
4. serializes once using the established canonical JSON settings;
5. parses that exact text with non-JSON constants rejected;
6. confirms the parsed root is an object;
7. returns immutable serialized text plus a newly owned detached dictionary.

Canonical serialization remains:

```python
json.dumps(
    owned_top_level,
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)
```

Any failure is chained into `LLMRequestSchemaError`. Critic adoption of the helper must
remain byte-equivalent to its current snapshot behavior.

### 4.2 Ownership invariant

The semantic models and provider-visible serialized payload must originate from the same
detached JSON value. No builder may validate the caller's objects and later serialize the
mapping again, or vice versa.

## 5. `RiskReviewerPayloadSnapshot`

### 5.1 Shape

```python
@dataclass(frozen=True, slots=True)
class RiskReviewerPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput
    problem_analysis: ProblemAnalysis
    solution_alternatives: SolutionAlternatives
```

### 5.2 Required keys

```text
review_input
problem_analysis
solution_alternatives
```

Aliases, missing keys, extra keys, case changes, and whitespace variants are rejected.

### 5.3 Construction

1. Detach and serialize the exact mapping once through §4.
2. Validate `detached["review_input"]` with `ReviewInput.model_validate`.
3. Validate `detached["problem_analysis"]` with
   `ProblemAnalysis.model_validate`.
4. Validate `detached["solution_alternatives"]` with
   `SolutionAlternatives.model_validate`.
5. Store the resulting frozen domain values with the same serialized text.

### 5.4 Invariants

1. Caller-owned mappings and nested values remain unchanged.
2. The three models and `serialized_payload` describe one logical snapshot.
3. Snapshot construction performs no HTTP, credential, filesystem, environment, clock,
   randomness, or global Review-state access.
4. Snapshot equality is value equality; it does not claim orchestration object identity.
5. The snapshot is local to one adapter call and is never stored in Review.
6. Trusted participant inputs remain authoritative; the snapshot is an infrastructure
   copy for untrusted request guidance only.

## 6. Risk-Basis Reference Value Type

Conceptual type alias:

```python
RiskBasisModel = (
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference
)
```

Every instance is already frozen and closed by the domain model. Its discriminator
`source` fixes the remaining legal fields:

| Source | Exact fields |
|---|---|
| `REVIEW_INPUT` | `source`, `field`, `value` |
| `PROBLEM_ANALYSIS` | `source`, `kind`, `text`, optional `id` |
| `SOLUTION_ALTERNATIVE` | `source`, `alternative_id`, `characteristic`, `value` |

The infrastructure catalog constructs these concrete variants directly. It never builds
an unvalidated loose dictionary and never stores an impossible mixture of fields.

## 7. `AllowedRiskBasis`

### 7.1 Shape

```python
@dataclass(frozen=True, slots=True)
class AllowedRiskBasis:
    reference: RiskBasisModel
    target_key: tuple[str, ...]
```

### 7.2 Field semantics

- `reference` is the exact canonical provider-output object represented as an existing
  validated frozen domain variant.
- `target_key` is a private semantic identity for ambiguity normalization and resolver
  parity. It is never emitted in payloads, prompts, schemas, output, safe errors, or logs.

### 7.3 Intrinsic invariants

1. `reference` is exactly one of the three approved basis model types.
2. Its `source` literal agrees with its concrete type.
3. Every required text value is non-blank under the existing domain validator.
4. `target_key` is non-empty and every component is a non-empty string.
5. Optional Problem Analysis ID is the actual current ID or `None`; it is never invented.
6. Solution Alternative string/constraint value shape agrees with `characteristic`.
7. No value is stripped, case-folded, normalized, paraphrased, repaired, or reclassified.

### 7.4 Wire-object projection

`as_wire_object()` returns a fresh JSON-compatible dictionary equivalent to:

```python
reference.model_dump(mode="json", exclude_none=True)
```

Thus an absent Problem Analysis ID is omitted, not serialized as `null`. A relevant
constraint remains a nested object. No returned mutable dictionary is retained by the
frozen catalog value.

### 7.5 Emitted identity

Because the wire value may contain a nested `ConstraintReference`, emitted identity is
the canonical serialized wire object:

```python
json.dumps(
    as_wire_object(),
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)
```

This immutable string is used only as a dictionary/grouping key. It is not exposed as
model output or used as semantic identity.

## 8. Target Keys

Target keys are explicit private tuples, not JSONPath, reflection paths, public IDs, or a
generic cross-stage reference system.

| Basis family | Target key |
|---|---|
| ReviewInput scalar | `("REVIEW_INPUT", field.value)` |
| ReviewInput collection value | `("REVIEW_INPUT", field.value, str(index))` |
| Problem Analysis finding | `("PROBLEM_ANALYSIS", kind.value, str(index))` |
| Alternative scalar characteristic | `("SOLUTION_ALTERNATIVE", alternative_id, characteristic.value)` |
| Alternative collection characteristic | `("SOLUTION_ALTERNATIVE", alternative_id, characteristic.value, str(index))` |

`DESCRIPTION` and `IMPLEMENTATION_COMPLEXITY` are scalar alternative characteristics.
`ADVANTAGE`, `DISADVANTAGE`, `ASSUMPTION`, and `RELEVANT_CONSTRAINT` are owner-local
collection characteristics.

Every index is the source tuple position converted with `str(index)`. Target-key order
does not affect provider output; it only distinguishes current semantic locations.

## 9. Resolver-Equivalent Eligibility

Eligibility is decided before emitted-identity normalization and mirrors the current Risk
Reviewer participant exactly.

### 9.1 ReviewInput exact scalars

- `description`: include its exact non-blank current value;
- `title` and `objective`: include only when non-`None` and non-blank;
- an absent or blank optional scalar contributes no basis.

Although current `ReviewInput` permits a blank optional title/objective, the existing
`ReviewInputBasisReference` rejects blank `value`; exclusion preserves that contract.

### 9.2 ReviewInput collection lookup

For `constraints`, `context`, and `stated_facts`:

- count exact equal strings in that one selected collection;
- include a non-blank value only when the count is exactly one;
- exclude all occurrences of a blank or duplicated value;
- preserve its tuple index only in `target_key`.

Equal text in two different ReviewInput fields remains legal because `field`
disambiguates the resolver lookup.

### 9.3 Problem Analysis finding lookup

For the selected kind's exact collection:

- ID present: include only if exactly one finding has both that ID and exact text;
- ID absent: include only if exactly one finding has that exact text;
- include the actual ID whenever present;
- omit the `id` field whenever absent;
- exclude an ID-less finding whose text is duplicated, even if an ID-bearing duplicate
  can still form its own exact branch.

The collection mapping is fixed:

| Kind | Collection |
|---|---|
| `FACT` | `facts` |
| `CONSTRAINT` | `constraints` |
| `ASSUMPTION` | `assumptions` |
| `MISSING_INFORMATION` | `missing_information` |
| `UNCERTAINTY` | `uncertainties` |

No finding may borrow an ID or text from another kind.

### 9.4 Solution Alternative scalar lookup

For each exact current alternative ID:

- `DESCRIPTION` uses exact `alternative.description`;
- `IMPLEMENTATION_COMPLEXITY` uses exact
  `alternative.implementation_complexity.value`.

Both form one owner-specific semantic target.

### 9.5 Solution Alternative text-collection lookup

For `ADVANTAGE`, `DISADVANTAGE`, and `ASSUMPTION`:

- count exact equal strings inside that characteristic collection of that alternative;
- include only a non-blank value occurring exactly once;
- exclude every owner-local duplicate;
- allow equal values in different alternatives because `alternative_id` differs.

### 9.6 Relevant-constraint lookup

For each `ConstraintReference` in `alternative.relevant_constraints`:

- compare complete frozen value equality inside that alternative's constraint tuple;
- include only when the exact object occurs once;
- preserve nested `source`, `kind`, and `value` unchanged;
- exclude every duplicate exact object within the owner alternative.

No second resolution against ReviewInput or Problem Analysis occurs here. The current
Risk Reviewer resolver checks exact membership in the already trusted Solution
Alternative, and the schema builder mirrors that boundary.

## 10. Explicit Basis Catalog Enumeration

### 10.1 Result

```python
tuple[AllowedRiskBasis, ...]
```

### 10.2 Fixed family and field order

```text
ReviewInput
  1. description
  2. title
  3. objective
  4. constraints in tuple order
  5. context in tuple order
  6. stated_facts in tuple order

ProblemAnalysis
  1. FACT findings in tuple order
  2. CONSTRAINT findings in tuple order
  3. ASSUMPTION findings in tuple order
  4. MISSING_INFORMATION findings in tuple order
  5. UNCERTAINTY findings in tuple order

SolutionAlternatives, preserving alternative tuple order
  1. DESCRIPTION for every alternative
  2. ADVANTAGE values by alternative then tuple order
  3. DISADVANTAGE values by alternative then tuple order
  4. ASSUMPTION values by alternative then tuple order
  5. IMPLEMENTATION_COMPLEXITY for every alternative
  6. RELEVANT_CONSTRAINT values by alternative then tuple order
```

Enumeration is by characteristic family across alternatives, matching the displayed
order above. It is not all characteristics of alternative 1 followed by all
characteristics of alternative 2.

No user-text, locale, hash, or set sorting is permitted.

### 10.3 Canonical Problem Analysis choice

When a finding has an ID, guidance exposes only exact `kind + text + id`. The weaker
`kind + text` representation remains accepted by the participant when it would resolve,
but it adds no target and is not offered by request guidance.

### 10.4 No unsupported families

Problem objective, generation notes, alternative name, and any RiskAssessment content
are absent because the current Risk basis union cannot represent them.

## 11. Catalog Normalization and Ambiguity

Normalization processes eligible candidates in their fixed order:

1. Group by canonical emitted-identity string.
2. If all members of a group have the same `target_key`, retain the first.
3. If a group contains different `target_key` values, retain none from that group.
4. Preserve the relative order of retained first candidates.
5. Never synthesize an ID, add a field, rewrite text, or choose one ambiguous target.
6. An ambiguous group has no effect on unrelated groups.

Unlike the Slice 7.1 Critic normalizer, the Risk basis normalizer permits an empty result
so the schema-narrowing function can preserve a zero-risk assessment without widening.
A currently valid Risk Reviewer payload will normally contain at least the exact
ReviewInput description basis.

## 12. Allowed Scope Catalog

### 12.1 Representation

No new scope wrapper is required. The catalog is:

```python
tuple[RiskScope, ...]
```

Every entry is an existing frozen, closed, already validated domain value.

### 12.2 Construction

Let current IDs be the exact tuple:

```python
alternative_ids = tuple(
    alternative.id
    for alternative in snapshot.solution_alternatives.alternatives
)
```

The first scope is always:

```python
RiskScope(kind=RiskScopeKind.OVERALL, alternative_ids=())
```

Then, for sequence length `1..len(alternative_ids)`, append each
`itertools.permutations(alternative_ids, length)` result as:

```python
RiskScope(
    kind=RiskScopeKind.ALTERNATIVES,
    alternative_ids=permutation,
)
```

### 12.3 Exact order and counts

| Current alternatives | Scope order | Total scopes |
|---:|---|---:|
| 0 | `OVERALL` only | 1 |
| 2 | `OVERALL`, 2 one-ID permutations, 2 two-ID permutations | 5 |
| 3 | `OVERALL`, 3 one-ID, 6 two-ID, 6 three-ID permutations | 16 |

The number of `ALTERNATIVES` branches is therefore 0, 4, or 15.

### 12.4 Invariants

1. IDs come only from the current validated `SolutionAlternatives`.
2. No `ALTERNATIVES` scope is empty.
3. No sequence repeats an ID.
4. Every sequence currently accepted by `RiskScope` and the participant scope resolver
   appears exactly once.
5. Ordering derives only from current alternative tuple order and permutations order.
6. No scope expresses ranking, preference, or recommendation.

## 13. Exact Basis Schema Branches

### 13.1 Top-level branch

Every `AllowedRiskBasis` produces one newly owned closed object:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "source": {"const": "PROBLEM_ANALYSIS"},
    "kind": {"const": "CONSTRAINT"},
    "text": {"const": "The solution must operate offline."},
    "id": {"const": "CON-001"}
  },
  "required": ["source", "kind", "text", "id"]
}
```

Property/required order follows the domain wire order:

- ReviewInput: `source`, `field`, `value`;
- Problem Analysis: `source`, `kind`, `text`, then `id` when present;
- Solution Alternative: `source`, `alternative_id`, `characteristic`, `value`.

Absent optional ID is omitted entirely. No branch uses independent enums, nullable
fields, defaults, or unconstrained strings.

### 13.2 String-valued properties

Enum values and exact strings become scalar `const` schemas. Python enum objects never
enter the JSON document; `mode="json"` projection supplies their exact wire strings.

### 13.3 Structured relevant constraint

For `characteristic=RELEVANT_CONSTRAINT`, `value` becomes a nested exact closed object:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "source": {"const": "PROBLEM_ANALYSIS"},
    "kind": {"const": "ID"},
    "value": {"const": "CON-001"}
  },
  "required": ["source", "kind", "value"]
}
```

The outer branch still binds the exact alternative and characteristic. A nested object
from another constraint cannot be combined with it.

### 13.4 Branch validation and ownership

Before projection, the concrete basis model is already domain-valid. Every branch call
returns fresh dictionaries/lists. No branch object is shared with a domain model,
catalog entry, static schema, earlier call, data-message document, or provider document.

Unexpected nested wire values or projection types fail safely rather than invoking a
generic recursive schema generator.

## 14. Exact Scope Schema Branches

Each `RiskScope` produces one fresh closed branch:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "kind": {"const": "ALTERNATIVES"},
    "alternative_ids": {"const": ["ALT-002", "ALT-001"]}
  },
  "required": ["kind", "alternative_ids"]
}
```

The overall branch uses `{"const": []}`. Array-valued `const` encodes exact order,
membership, non-emptiness, and uniqueness without `uniqueItems`.

The branch builder first projects the existing `RiskScope` with `mode="json"`; it does
not construct an unchecked kind/IDs dictionary.

## 15. Dynamic RiskAssessment Schema Transformation

### 15.1 Authoritative input

Start with:

```python
strict_json_schema_document(RiskAssessment.model_json_schema())
```

This yields a fresh owned strict document before role-specific narrowing. Narrowing after
strict normalization ensures tighter `minItems`/`maxItems` decisions are not overwritten
by the shared normalizer.

### 15.2 Required structural locations

The strict document must contain:

1. root `properties.risks` as an array;
2. `$defs.Risk` as an object schema;
3. `$defs.Risk.properties.basis` as an array with addressable `items`;
4. `$defs.Risk.properties.affected_scope` referencing `#/$defs/RiskScope`;
5. `$defs.RiskScope` as an object schema.

Missing, wrong-typed, unexpectedly referenced, or structurally changed locations raise
`LLMRequestSchemaError`. There is no fallback to the broad static Risk Reviewer schema.

### 15.3 Non-empty basis catalog

When allowed bases exist:

- replace `$defs.Risk.properties.basis.items` with one `oneOf` branch per normalized
  allowed basis;
- replace the complete prior item schema, including its broad discriminated-union
  `discriminator` metadata, so it cannot remain as a parallel route;
- set that basis array's `minItems` to `1`;
- retain strict `maxItems=10`;
- do not alter root `risks` minimum, so zero risks remain valid.

The three original source-variant definitions may remain unchanged but are no longer
reachable from `Risk.basis.items`. They are not rewritten into a second competing
catalog.

### 15.4 Empty basis catalog

When no allowed basis exists:

- set root `properties.risks.maxItems` to `0` after strict normalization;
- do not install an empty `oneOf`, open basis branch, fabricated fallback basis, or
  weaker static route;
- retain `overall_observations` unchanged.

The static basis item definitions may remain present but are unreachable because no Risk
item is permitted. Fully empty and observation-only assessments remain valid.

### 15.5 Scope replacement

Replace `$defs.RiskScope` with:

```json
{
  "oneOf": ["one fresh exact branch per allowed RiskScope"]
}
```

At least the overall branch always exists. The replacement contains no independent kind
enum, free string item schema, `uniqueItems`, or unknown ID route.

### 15.6 Preserved schema areas

Every unrelated definition and outer field remains deeply equal to the authoritative
strict base, including:

- `RiskAssessment` root required fields and closed-object behavior;
- `risks` and `overall_observations` ability to be empty;
- root and nested array `maxItems=10`, except `risks.maxItems=0` for an empty basis
  catalog;
- exact qualitative severity enum;
- nullable/required strict representation of optional `category`, `mitigation`, and
  `residual_uncertainty`;
- risk description and ID fields;
- overall-observation item type;
- closed-object rejection of ranking, recommendation, numeric score, and extra fields.

Provider schema guidance does not attempt to express duplicate Risk IDs, duplicate
overall observations, or duplicate basis-array entries beyond the existing static JSON
Schema. Existing Pydantic validators remain authoritative for those invariants.

### 15.7 Ownership

The base input, static prompt schema, catalog models, caller payload, Critic schema,
prior request documents, and provider documents are never mutated. Repeated narrowing
from the same semantic catalogs yields deeply equal but independently owned documents.

## 16. `RequestOutputSchema`

Slice 7.2 reuses the existing value unchanged:

```python
@dataclass(frozen=True, slots=True)
class RequestOutputSchema:
    serialized: str

    def new_document(self) -> dict[str, object]:
        ...
```

### 16.1 Construction and invariants

- canonical JSON uses `allow_nan=False`, `ensure_ascii=False`, compact separators, and
  `sort_keys=True`;
- construction verifies the serialization parses to one JSON object;
- `new_document()` returns a fresh parsed object every time;
- mutation of one returned document cannot affect later calls or serialized text;
- equivalent semantic inputs produce byte-identical serialized schemas;
- production code never logs or persists the schema by default.

No mutable mapping is added to `RequestOutputSchema`.

## 17. `DynamicRequestContext`

### 17.1 Shape

```python
@dataclass(frozen=True, slots=True)
class DynamicRequestContext:
    serialized_payload: str
    output_schema: RequestOutputSchema
```

### 17.2 Construction

For each dynamic role:

```text
Critic snapshot
  → existing Critic schema builder
  → DynamicRequestContext(snapshot.serialized_payload, schema)

Risk Reviewer snapshot
  → allowed basis + allowed scope catalogs
  → narrowed RiskAssessment schema
  → DynamicRequestContext(snapshot.serialized_payload, schema)
```

### 17.3 Invariants

1. Both fields derive from the same role-specific validated snapshot.
2. `serialized_payload` is never reconstructed from the caller after schema creation.
3. `output_schema` contains no mutable document.
4. Context lifetime is one synchronous adapter invocation.
5. Context is never retained on the adapter or written to Review state.
6. The value carries no provider profile, endpoint, credential, mode, response, or trusted
   participant result.

## 18. Closed Role Dispatch

Conceptual interface:

```python
def build_dynamic_request_context(
    *,
    definition: RolePromptDefinition,
    payload: Mapping[str, object],
) -> DynamicRequestContext | None:
    ...
```

Exact behavior:

| Exact role | Result |
|---|---|
| `risk_reviewer` | Risk Reviewer snapshot + dynamic RiskAssessment schema context |
| `critic` | existing Critic snapshot + dynamic CriticalReview schema context |
| `analyst` | `None` |
| `solution_architect` | `None` |
| `coordinator` | `None` |

Unknown roles have already failed through `get_role_prompt_definition` and are not
accepted as dispatcher extensions.

The existing general `build_request_output_schema(definition, payload)` behavior is:

- return `context.output_schema` for either dynamic role;
- return the current strict static output-model schema for any of the three static roles.

There is no registry, reflection, plugin hook, provider/model dispatch, external rule
input, or configurable dynamic-role list.

## 19. Adapter Wire Model

### 19.1 System message

Every role retains its current static application-controlled system message:

```text
static semantic instruction
static authoritative output schema
static instruction to return one concrete instance
```

No `AllowedRiskBasis`, `RiskScope`, payload value, or dynamic schema enters `system`.

### 19.2 User/data message

For exact Risk Reviewer and Critic roles:

```text
UNTRUSTED_PAYLOAD_JSON_BEGIN
<DynamicRequestContext.serialized_payload>
UNTRUSTED_PAYLOAD_JSON_END

UNTRUSTED_REQUEST_SCHEMA_JSON_BEGIN
<DynamicRequestContext.output_schema.serialized>
UNTRUSTED_REQUEST_SCHEMA_JSON_END
```

Static roles retain their current payload-only message byte-for-byte.

### 19.3 Mode matrix

| Mode | System message | Dynamic-role user/data | `response_format` |
|---|---|---|---|
| `JSON_SCHEMA` | static only | payload + dynamic schema | fresh dynamic `new_document()` |
| `JSON_OBJECT` | static only | payload + dynamic schema | `{ "type": "json_object" }` |
| `PROMPT_ONLY` | static only | payload + dynamic schema | absent |

Static roles continue using their current strict static provider schema in
`JSON_SCHEMA` and no dynamic-schema data section in any mode.

### 19.4 Data and alias safety

- both dynamic sections are already JSON before concatenation;
- Unicode, quote, slash, newline, delimiter-looking, and instruction-like payload text
  remains escaped inside JSON strings;
- provider guidance uses a fresh parsed schema document;
- no mutable schema document is shared with message text or another request;
- the existing opt-in observer receives only parsed provider output after successful
  transport/parsing.

## 20. Error Model

No new error is introduced:

```python
class LLMRequestSchemaError(LLMAdapterError):
    message = "LLM request schema construction failed"
```

### 20.1 Safe representation

- fixed exact public string;
- no payload, schema, catalog, target key, role content, endpoint, profile, model,
  credential, validation detail, or raw provider output in public fields;
- exception chaining may retain a local cause but it is not intentionally logged or
  surfaced.

### 20.2 Failure timing

Snapshot, catalog, scope, branch, dispatch, and narrowing failures occur before:

- credential extraction or authorization-header construction;
- HTTP request;
- response parsing;
- output-observer invocation;
- participant structural/context validation;
- any trusted stage output.

The existing orchestrator maps this adapter failure to the current safe Risk Reviewer
`EXECUTION` failure. Provider output that reaches the participant and fails its trusted
contract remains the existing `OUTPUT_VALIDATION` failure. No lifecycle or error enum
changes.

## 21. State, Mutation, and Concurrency

No snapshot, catalog, scope tuple, dynamic context, or schema document is retained on
`OpenAICompatibleLLMAdapter`. All values are local to one synchronous
`generate_structured` call.

Existing adapter/client reuse is unchanged. This slice adds no async execution,
cross-request cache, global registry, persistence, resume, retry, or new thread-safety
claim.

## 22. Validation Examples

### 22.1 Canonical ReviewInput constraint basis

```json
{
  "source": "REVIEW_INPUT",
  "field": "constraints",
  "value": "The solution must operate offline."
}
```

### 22.2 Canonical Problem Analysis constraint basis

```json
{
  "source": "PROBLEM_ANALYSIS",
  "kind": "CONSTRAINT",
  "text": "The solution must operate offline.",
  "id": "CON-001"
}
```

### 22.3 Observed forbidden cross-product

```json
{
  "source": "PROBLEM_ANALYSIS",
  "kind": "ASSUMPTION",
  "text": "The solution must operate offline.",
  "id": "CON-001"
}
```

No basis branch represents this object because `CON-001` and its exact text belong to
the `CONSTRAINT` collection.

### 22.4 ID-less duplicate exclusion

```text
UNCERTAINTY[0]: id=None,    text="same uncertainty"
UNCERTAINTY[1]: id=UNC-002, text="same uncertainty"
```

The first contributes no branch because text-only resolution is ambiguous. The second
may contribute exact `kind=UNCERTAINTY + text + id=UNC-002` because that pair is unique.

### 22.5 Solution Alternative disadvantage basis

```json
{
  "source": "SOLUTION_ALTERNATIVE",
  "alternative_id": "ALT-001",
  "characteristic": "DISADVANTAGE",
  "value": "Migration complexity may delay deployment."
}
```

### 22.6 Structured relevant-constraint basis

```json
{
  "source": "SOLUTION_ALTERNATIVE",
  "alternative_id": "ALT-001",
  "characteristic": "RELEVANT_CONSTRAINT",
  "value": {
    "source": "PROBLEM_ANALYSIS",
    "kind": "ID",
    "value": "CON-001"
  }
}
```

### 22.7 Overall scope

```json
{
  "kind": "OVERALL",
  "alternative_ids": []
}
```

### 22.8 All two-alternative scopes

For current IDs `(ALT-001, ALT-002)`, exact order is:

```text
OVERALL []
ALTERNATIVES [ALT-001]
ALTERNATIVES [ALT-002]
ALTERNATIVES [ALT-001, ALT-002]
ALTERNATIVES [ALT-002, ALT-001]
```

No empty, duplicate, or unknown-ID `ALTERNATIVES` scope exists.

### 22.9 Fully empty RiskAssessment

```json
{
  "risks": [],
  "overall_observations": []
}
```

It remains valid and generatable regardless of available basis or scope candidates.

## 23. Security and Privacy Invariants

1. Payload-derived values appear only in the existing untrusted payload, the delimited
   untrusted request-schema section, and explicit `JSON_SCHEMA` request configuration.
2. No payload-derived value appears in system/developer instructions.
3. Full payloads and dynamic schemas are not logged, persisted, or included in safe
   errors by default.
4. Credentials, endpoint/profile data, environment variables, hardware information, and
   previous Review data do not participate in schema construction.
5. Target keys never leave infrastructure memory.
6. Existing raw provider-output diagnostics remain explicit opt-in behavior and do not
   capture request schemas.
7. Schema guidance grants no tool, action, retry, routing, fallback, or trust capability.

## 24. Requirement Coverage

| Requirement group | Data-model sections |
|---|---|
| RDS-FR-001–RDS-FR-003 | §§4–5, 17–19 |
| RDS-FR-004–RDS-FR-008 | §§6–11, 13 |
| RDS-FR-009 | §§12, 14–15 |
| RDS-FR-010–RDS-FR-011 | §15 |
| RDS-FR-012–RDS-FR-014 | §§4–5, 16–19, 21 |
| RDS-FR-015–RDS-FR-017 | §§15–20 |
| RDS-FR-018–RDS-FR-020 | §§10–11, 15–16, 19–23 |
| RDS-FR-021 | live evidence belongs to tasks; no persistent data model is added |

## 25. Decisions Fixed by This Data Model

1. A detached three-artifact `RiskReviewerPayloadSnapshot` supplies both payload text and
   schema semantics.
2. `AllowedRiskBasis` wraps one existing validated basis subtype plus one private target
   key; it does not duplicate the discriminated union as nullable fields.
3. Canonical emitted identity is deterministic JSON so nested constraints remain
   hashable without flattening.
4. ID-bearing Problem Analysis guidance always includes exact kind, text, and actual ID.
5. ID-less findings and collection text require exact owner-local uniqueness.
6. Relevant constraints remain nested exact objects and resolve only against their
   trusted owner alternative.
7. Empty normalized basis catalog is allowed only to preserve zero-risk output; it never
   widens a Risk basis.
8. Scope catalogs reuse frozen `RiskScope` and enumerate all ordered permutations without
   replacement.
9. Array-valued `const` is the selected scope representation; live compatibility must be
   verified before claiming vLLM 0.8.5 support.
10. Strict normalization precedes Risk-specific narrowing so `minItems=1` and empty-
    catalog `risks.maxItems=0` remain effective.
11. Existing source-variant `$defs` may remain unused; the Risk basis item is the one
    narrowed route.
12. `DynamicRequestContext` is the only adapter-facing pair of snapshot payload text and
    request schema for the two closed dynamic roles.
13. `RequestOutputSchema`, `LLMRequestSchemaError`, delimiters, and Critic dynamic models
    remain unchanged.
14. Duplicate Risk IDs, observations, and basis-array entries remain enforced by existing
    trusted validation rather than new provider-schema claims.
15. No schema/catalog truncation, retry, repair, fallback, or mode downgrade is allowed.

## 26. Data-Model Review Gate

Before approval, confirm:

1. all new values are infrastructure-only and do not become Review/domain contracts;
2. exact payload detachment preserves current Critic behavior and one-snapshot ownership;
3. wrapping existing basis variants prevents invalid optional-field combinations;
4. emitted identity and private target identity remain distinct;
5. ReviewInput blank/duplicate eligibility exactly matches its basis resolver;
6. Problem Analysis optional-ID eligibility exactly matches its selected-kind lookup;
7. Solution Alternative text and constraint uniqueness remain owner-local;
8. relevant constraints remain structured and are not re-resolved beyond the current
   participant contract;
9. the 1/5/16 total scope counts preserve all valid current scope orders without ranking;
10. exact basis and scope branch ownership prevents mutable aliases;
11. empty basis catalog permits only zero-risk output rather than construction failure or
    widening;
12. strict-before-narrow ordering preserves the intended minimum/maximum array bounds;
13. Critic and static-role behavior remain unchanged under closed dispatch;
14. dynamic values remain outside the trusted system instruction and safe errors;
15. no new dependency, ADR, lifecycle, retry, fallback, repair, or persistence behavior
    is introduced.

No `tasks.md` SHALL be created and no implementation SHALL begin until this
`data-model.md` has been self-reviewed and explicitly approved by the user. After
approval, `tasks.md` will be created, self-reviewed, and presented as the next independent
Spec Kit gate.
