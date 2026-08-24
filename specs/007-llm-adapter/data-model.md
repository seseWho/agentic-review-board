# Data Model: Configurable OpenAI-Compatible LLM Adapter v0.1

**Branch**: `007-llm-adapter`  
**Specification**: `specs/007-llm-adapter/spec.md` — Approved  
**Plan**: `specs/007-llm-adapter/plan.md` — Approved  
**Status**: Draft — pending review and approval before task decomposition

## 1. Purpose

This document defines the Slice 7 infrastructure configuration, assignment, prompt, adapter-error, and runtime-lifecycle models.

Slice 7 adds no trusted Review-domain artifact and changes no existing participant output model. The new models configure how the existing `LLMPort` reaches one or more local or remote OpenAI-compatible endpoints and how those configured adapters are assigned explicitly to the five participants.

The model keeps four concerns separate:

1. non-secret configuration read from JSON or constructed programmatically;
2. runtime secret resolution from the environment;
3. immutable participant-to-profile composition;
4. untrusted HTTP/provider response processing before existing participant validation.

---

## 2. Boundary Overview

```text
JSON metadata / programmatic values
        ↓ untrusted
RawLLMRuntimeConfig
        ↓ structural + cross-reference validation
environment credential lookup
        ↓
ResolvedLLMProfile[]
        ↓ exact assignment resolution
ConfiguredReviewRuntime
        ├── one owned httpx.Client
        ├── configured LLMPort adapters
        └── existing five-participant ReviewOrchestrator
                ↓
OpenAI-compatible endpoint
                ↓ untrusted
provider envelope + assistant content
                ↓ direct JSON-object parsing
Mapping[str, object]
                ↓ still untrusted
existing participant structural/contextual validation
                ↓
existing trusted Review artifact
```

Configuration validation does not call the network. JSON parsing does not make model output trusted.

---

## 3. Model Inventory

### 3.1 New configuration and composition models

```text
StructuredOutputMode
LLMRole
RawLLMProfile
ParticipantLLMAssignment
RawLLMRuntimeConfig
ResolvedLLMProfile
ResolvedParticipantLLMAssignment
```

### 3.2 New infrastructure runtime objects

```text
RolePromptDefinition
OpenAICompatibleLLMAdapter
ConfiguredReviewRuntime
```

### 3.3 New safe error family

```text
LLMAdapterError
├── LLMConfigurationError
├── LLMRuntimeClosedError
├── UnsupportedLLMRoleError
├── LLMPayloadSerializationError
├── LLMRequestTimeoutError
├── LLMTransportError
├── LLMHTTPStatusError
├── LLMResponseEnvelopeError
└── LLMStructuredContentError
```

### 3.4 Existing models reused unchanged

```text
LLMPort
ProblemAnalysis
SolutionAlternatives
RiskAssessment
CriticalReview
FinalReview
Analyst
SolutionArchitect
RiskReviewer
Critic
Coordinator
ReviewOrchestrator
```

No existing domain or application model receives provider, endpoint, model, credential, prompt, or HTTP fields.

---

## 4. `StructuredOutputMode`

### 4.1 Shape

A closed string enum with exactly:

```text
JSON_OBJECT
PROMPT_ONLY
```

### 4.2 Semantics

| Value | Request behavior |
|---|---|
| `JSON_OBJECT` | Include `"response_format": {"type": "json_object"}` |
| `PROMPT_ONLY` | Omit `response_format` completely |

Both modes:

- use the same role semantic instruction;
- include the same generated output-model JSON Schema;
- require direct JSON with no Markdown or surrounding prose;
- use the same response-envelope and direct JSON-object validation;
- remain subject to existing participant validation.

### 4.3 Invariants

- exact case-sensitive value;
- no aliases;
- no blank/default fallback after invalid input;
- no capability detection;
- no automatic mode change;
- no retry using the other mode.

---

## 5. `LLMRole`

### 5.1 Shape

A closed string enum with exactly:

```text
analyst
solution_architect
risk_reviewer
critic
coordinator
```

### 5.2 Purpose

`LLMRole` is an infrastructure configuration/prompt key. It mirrors the exact strings already passed through `LLMPort`; it does not replace `StageIdentity` and does not enter Review state.

### 5.3 Invariants

- matching is exact and case-sensitive;
- no stripping, case folding, aliases, or default;
- unsupported role fails before payload serialization or network activity;
- the role cannot be selected from ReviewInput or generated content.

---

## 6. `RawLLMProfile`

### 6.1 Purpose

Represents one non-secret endpoint/model definition parsed from JSON or built programmatically before credential resolution.

The containing `profiles` mapping key supplies the profile name; the JSON object does not duplicate it.

### 6.2 Fields

| Field | Type | Required | Rules |
|---|---|---:|---|
| `base_url` | string | yes | Valid HTTP(S) API base; normalized as specified below |
| `model` | string | yes | Non-blank after boundary whitespace stripping |
| `api_key_env` | string or null | no | Valid environment-variable name when present |
| `timeout_seconds` | finite float | yes | Greater than zero |
| `structured_output_mode` | `StructuredOutputMode` | yes | Exact enum value |

Extra fields are forbidden.

### 6.3 Base URL validation

Accepted:

- `http://` and `https://`;
- loopback and local hostnames;
- optional port;
- an API base path such as `/v1`;
- one trailing slash, normalized away.

Rejected:

- blank values;
- missing scheme or host;
- schemes other than HTTP(S);
- embedded username/password;
- query string;
- fragment;
- a path already ending with `/chat/completions`;
- control characters or an otherwise unparsable URL.

Examples:

| Input | Result |
|---|---|
| `http://localhost:11434/v1/` | stored as `http://localhost:11434/v1` |
| `https://api.openai.com/v1` | accepted unchanged |
| `localhost:11434/v1` | rejected |
| `https://user:pass@example.test/v1` | rejected |
| `https://example.test/v1?token=x` | rejected |
| `https://example.test/v1/chat/completions` | rejected |

The final request target is always:

```text
{normalized_base_url}/chat/completions
```

### 6.4 Model validation

- string only;
- strip boundary whitespace once;
- result must be non-empty;
- internal whitespace and provider-specific punctuation remain unchanged;
- no provider/model allowlist;
- no implicit default.

### 6.5 Credential-variable validation

When `api_key_env` is present:

- preserve and validate the supplied identity exactly with no stripping;
- value must match `[A-Za-z_][A-Za-z0-9_]*`;
- it identifies a process environment variable, not a credential value.

Absent `api_key_env` means unauthenticated profile.

An empty or whitespace-only `api_key_env` is invalid rather than silently treated as absent.

### 6.6 Timeout validation

- integer or float input accepted by Pydantic strict numeric validation, excluding booleans;
- finite;
- greater than zero;
- no default;
- no `None`;
- no separate connect/read/write/pool values in v0.1.

The same value later initializes all four HTTPX timeout phases.

### 6.7 Representation

`RawLLMProfile` contains no secret. It may be safely represented or serialized after normal care for endpoint metadata. Complete configuration is still not logged by default.

---

## 7. `ParticipantLLMAssignment`

### 7.1 Purpose

Represents the complete explicit mapping from each logical participant to one named profile before profile resolution.

### 7.2 Fields

| Field | Type | Required |
|---|---|---:|
| `analyst` | profile-name string | yes |
| `solution_architect` | profile-name string | yes |
| `risk_reviewer` | profile-name string | yes |
| `critic` | profile-name string | yes |
| `coordinator` | profile-name string | yes |

Extra fields are forbidden.

### 7.3 Profile-reference rules

Each value:

- is not stripped, normalized, or rewritten;
- must match the same profile-name grammar `[A-Za-z][A-Za-z0-9_-]*` exactly;
- resolves by exact equality against one key in `RawLLMRuntimeConfig.profiles`;
- receives no alias, case folding, fuzzy match, or default.

All five fields are mandatory. Reusing one profile for all five is valid. Any combination of existing profiles is valid.

---

## 8. `RawLLMRuntimeConfig`

### 8.1 Purpose

Represents the complete validated non-secret JSON document.

### 8.2 Fields

| Field | Type | Required | Rules |
|---|---|---:|---|
| `profiles` | mapping of profile name to `RawLLMProfile` | yes | At least one entry |
| `assignments` | `ParticipantLLMAssignment` | yes | All references resolve |

Extra top-level fields are forbidden.

### 8.3 Profile-name rules

Every mapping key:

- is a string;
- is not normalized or rewritten;
- must match `[A-Za-z][A-Za-z0-9_-]*`;
- is unique by JSON object/Python mapping semantics;
- is safe to expose as a non-secret operational identifier.

Profile identity is exact. Names differing only in case remain distinct, though examples should use lowercase names for clarity.

### 8.4 Cross-reference invariant

After intrinsic parsing, every assignment value must belong to the exact set of profile names. The set of selected profile names is the exact set referenced by the five assignments. Declared but unselected profiles remain structurally validated but are not credential-resolved, instantiated, or smoke-tested for this runtime.

Failure rejects the complete configuration before:

- environment credential lookup;
- HTTP client construction;
- adapter construction;
- participant construction;
- Review creation or execution.

### 8.5 JSON shape

```json
{
  "profiles": {
    "local": {
      "base_url": "http://localhost:11434/v1",
      "model": "local-model",
      "timeout_seconds": 60.0,
      "structured_output_mode": "PROMPT_ONLY"
    },
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "model": "configured-openai-model",
      "api_key_env": "OPENAI_API_KEY",
      "timeout_seconds": 60.0,
      "structured_output_mode": "JSON_OBJECT"
    }
  },
  "assignments": {
    "analyst": "local",
    "solution_architect": "openai",
    "risk_reviewer": "local",
    "critic": "openai",
    "coordinator": "openai"
  }
}
```

---

## 9. Configuration Loading

### 9.1 Loader input

The documented environment loader reads exactly:

```text
ARB_LLM_CONFIG_PATH
```

The value:

- is required when the environment loader is explicitly invoked;
- is stripped once;
- must identify a readable regular JSON file;
- is not interpreted as a URL;
- receives no fallback search path;
- causes no network activity.

Embedding code and tests may bypass this loader by constructing `RawLLMRuntimeConfig` directly.

### 9.2 JSON parsing

Reject safely:

- absent/blank path;
- missing or unreadable file;
- non-UTF-8 content;
- invalid JSON;
- non-object top-level JSON;
- duplicate object keys;
- schema/field validation failure;
- unresolved assignment reference.

Duplicate keys must be detected during JSON decoding rather than silently accepting the last value.

### 9.3 Environment access

Credential resolution receives an explicit read-only `Mapping[str, str]`, normally `os.environ`, so deterministic tests do not mutate global environment state.

The loader/resolver does not call `load_dotenv()` and does not modify the environment.

### 9.4 Safe configuration errors

All load, parse, field, cross-reference, and credential-resolution failures exposed through the public loader use:

```text
LLM configuration invalid
```

Underlying causes may be chained but their text is not copied into the safe message.

---

## 10. `ResolvedLLMProfile`

### 10.1 Purpose

Represents one validated runtime-ready profile after environment credential lookup.

It is an immutable infrastructure value, not a Pydantic JSON input model and not Review state.

### 10.2 Fields

| Field | Type | Rules |
|---|---|---|
| `name` | string | Exact validated profile key |
| `base_url` | string | Normalized validated base |
| `model` | string | Validated model value |
| `api_key` | `SecretStr` or null | Resolved runtime secret, protected representation |
| `timeout` | `httpx.Timeout` | Same finite scalar for all four phases |
| `structured_output_mode` | enum | Exact validated mode |

### 10.3 Credential resolution

If raw `api_key_env` is absent:

- `api_key=None`;
- request has no `Authorization` header.

If present:

1. look up exact variable name in the supplied environment mapping;
2. require the variable to exist;
3. require a non-blank value;
4. require `value == value.strip()` so accidental leading/trailing whitespace fails rather than being repaired or transmitted;
5. preserve permitted internal characters exactly;
6. wrap it in `SecretStr`.

A referenced missing, blank, or boundary-whitespace credential for any selected profile rejects complete runtime resolution. Credentials named only by unselected profiles are not read. There is no partially composed runtime.

### 10.4 Secret representation

`ResolvedLLMProfile` shall implement or inherit a safe representation in which the credential never appears. It shall not expose an ordinary serialization method that returns the secret.

The adapter accesses the secret only at request-header construction.

### 10.5 Timeout construction

Given validated scalar `t`:

```python
httpx.Timeout(
    connect=t,
    read=t,
    write=t,
    pool=t,
)
```

No phase may be `None`.

### 10.6 Equality and identity

Profile name is the composition identity. Two independently resolved profiles with equal fields are equivalent configuration values but need not share object identity.

Composition creates one adapter per selected profile name and reuses that adapter for every participant assigned to the name. Unselected profiles create no resolved value or adapter.

---

## 11. `ResolvedParticipantLLMAssignment`

### 11.1 Purpose

Represents the complete assignment after exact profile resolution.

### 11.2 Fields

| Field | Type |
|---|---|
| `analyst` | `ResolvedLLMProfile` |
| `solution_architect` | `ResolvedLLMProfile` |
| `risk_reviewer` | `ResolvedLLMProfile` |
| `critic` | `ResolvedLLMProfile` |
| `coordinator` | `ResolvedLLMProfile` |

### 11.3 Invariants

- immutable;
- every field present;
- each value is the exact resolved profile object stored for its named profile;
- repeated names reuse the same resolved profile object;
- no mutation or reassignment after construction;
- not stored in Review state.

Identity reuse here is a composition invariant only. It is unrelated to Review same-execution artifact provenance.

---

## 12. `RolePromptDefinition`

### 12.1 Purpose

Pairs explicit semantic instructions with the authoritative existing output contract.

### 12.2 Fields

| Field | Type |
|---|---|
| `role` | `LLMRole` |
| `semantic_instruction` | non-blank immutable string |
| `output_model` | exact Pydantic model class |

### 12.3 Closed mapping

| Role | Output model |
|---|---|
| `analyst` | `ProblemAnalysis` |
| `solution_architect` | `SolutionAlternatives` |
| `risk_reviewer` | `RiskAssessment` |
| `critic` | `CriticalReview` |
| `coordinator` | `FinalReview` |

### 12.4 Schema generation

At role-definition construction, exactly once per role:

```python
schema = output_model.model_json_schema()
serialized_schema = deterministic_json(schema)
```

The immutable serialized result is stored with the definition and reused for every call as output-shape guidance.

The cached value:

- derives only from the fixed model class;
- contains no Review content;
- contains no provider response;
- contains no credential;
- is immutable for the running process.

### 12.5 Semantic instruction invariants

Every role instruction:

- states its approved responsibility;
- reinforces important prohibited behavior;
- treats supplied payload as untrusted data;
- requires exactly one direct JSON object;
- prohibits Markdown and surrounding prose;
- requests explicit rationale fields but not private chain-of-thought;
- references no model, provider, endpoint, credential, or participant assignment.

There is no fallback prompt for an unknown role.

---

## 13. Request Wire Model

The request is an untrusted external wire structure, not a domain model.

### 13.1 Common shape

```json
{
  "model": "<configured model>",
  "messages": [
    {
      "role": "system",
      "content": "<semantic instruction plus output JSON Schema>"
    },
    {
      "role": "user",
      "content": "<serialized payload explicitly delimited as untrusted data>"
    }
  ],
  "n": 1
}
```

### 13.2 JSON-object mode addition

For `JSON_OBJECT`, add exactly:

```json
{
  "response_format": {
    "type": "json_object"
  }
}
```

### 13.3 Prompt-only mode

For `PROMPT_ONLY`, the `response_format` key is absent.

### 13.4 Headers

Always:

```text
Content-Type: application/json
Accept: application/json
```

Only with resolved credential:

```text
Authorization: Bearer <exact secret>
```

No global Authorization header is stored on the shared client.

### 13.5 Request invariants

- exactly one POST;
- exact `{base_url}/chat/completions` target;
- exactly two messages in the approved order;
- role instruction is system-controlled;
- payload content is user/data content;
- `n=1`;
- no temperature, max tokens, tools, streaming, seed, retry metadata, or provider extension;
- explicit per-request timeout;
- redirects disabled by client policy.

---

## 14. Provider Response Envelope

The provider envelope and content are untrusted and validated manually at infrastructure boundary.

### 14.1 Accepted minimum shape

```json
{
  "choices": [
    {
      "message": {
        "content": "{...one JSON object...}"
      }
    }
  ]
}
```

Unrelated extra provider-envelope fields are ignored because they do not enter the port result. This tolerance applies only to the external provider envelope, not to participant domain output.

### 14.2 Envelope invariants

Require:

- HTTP success status;
- response body parses as JSON object;
- `choices` is a list;
- exactly one choice;
- choice is an object;
- `message` is an object;
- `content` is a non-blank string.

Reject zero or multiple choices even though the request specifies `n=1`.

### 14.3 Content parsing

Apply one direct standard JSON parse.

Require top-level object. Reject:

- invalid JSON;
- array;
- string;
- number;
- boolean;
- null;
- Markdown fence;
- prefix or suffix text.

Return a mapping still considered untrusted.

### 14.4 No repair

No trimming beyond what the JSON parser itself permits around a complete JSON document. No fence stripping, substring extraction, correction call, schema coercion, provider-specific content-part normalization, or retry.

---

## 15. Safe Adapter Errors

### 15.1 Base class

```python
class LLMAdapterError(RuntimeError)
```

All adapter/configuration public failures inherit from it.

### 15.2 Closed error table

| Error | Safe public message | Trigger |
|---|---|---|
| `LLMConfigurationError` | `LLM configuration invalid` | File, JSON, profile, assignment, URL, timeout, credential resolution |
| `LLMRuntimeClosedError` | `LLM runtime is closed` | Entering or executing through a closed runtime |
| `UnsupportedLLMRoleError` | `LLM role unsupported` | Unknown/non-exact role |
| `LLMPayloadSerializationError` | `LLM payload serialization failed` | Payload cannot serialize directly |
| `LLMRequestTimeoutError` | `LLM request timed out` | Any HTTPX timeout |
| `LLMTransportError` | `LLM transport failed` | Other request/transport failure |
| `LLMHTTPStatusError` | `LLM HTTP request failed` | Non-success HTTP status |
| `LLMResponseEnvelopeError` | `LLM response envelope invalid` | Invalid envelope/body/choice/message/content shape |
| `LLMStructuredContentError` | `LLM structured content invalid` | Assistant content not direct top-level JSON object |

### 15.3 Sanitization

Safe messages contain no dynamic detail.

Errors must not interpolate:

- profile base URL;
- model;
- credential variable value;
- API key;
- request headers;
- payload;
- prompt;
- response body;
- provider error text;
- nested exception text.

A safe non-secret profile name may be reported separately by the smoke-test runner, not appended by the error object itself.

### 15.4 Chaining

Underlying exceptions may be used as `__cause__`. Application/UI logging must not automatically render chained tracebacks to end users.

The existing orchestrator catches these as ordinary `Exception` values and preserves the already approved participant-specific execution-failure messages.

### 15.5 Output-validation separation

If adapter content is a JSON object and a participant later raises its existing output error, the orchestrator maps it as `OUTPUT_VALIDATION`.

The adapter must not import, catch, wrap, or reinterpret participant output errors.

---

## 16. `OpenAICompatibleLLMAdapter`

### 16.1 Purpose

Synchronous infrastructure implementation of the unchanged `LLMPort`.

### 16.2 Construction

Conceptually:

```python
OpenAICompatibleLLMAdapter(
    profile: ResolvedLLMProfile,
    client: httpx.Client,
)
```

### 16.3 Stored state

- immutable resolved profile reference;
- shared client reference;
- immutable/cached role prompt definitions;
- no Review or call-specific data.

### 16.4 `generate_structured`

Conceptual sequence:

1. resolve exact `LLMRole`;
2. select exact `RolePromptDefinition`;
3. obtain authoritative output JSON Schema;
4. serialize schema and payload;
5. create complete per-request headers and body;
6. issue one POST with profile timeout;
7. map timeout, transport, and status failures safely;
8. validate response envelope;
9. parse direct JSON object;
10. return mapping.

### 16.5 Statelessness

After a call the adapter retains no:

- payload;
- rendered prompt;
- response envelope;
- assistant content;
- parsed result;
- Review artifact;
- error body.

Sharing an adapter across participants or Reviews shares only immutable configuration and the HTTP client's connection pool.

---

## 17. `ConfiguredReviewRuntime`

### 17.1 Purpose

Owns the resource lifecycle and complete fixed participant composition needed to run real-model Reviews.

### 17.2 Construction inputs

Conceptually:

```python
ConfiguredReviewRuntime.from_config(
    config: RawLLMRuntimeConfig,
    environ: Mapping[str, str],
    transport: httpx.BaseTransport | None = None,
)
```

The optional transport exists for deterministic tests. Production leaves it absent.

### 17.3 Stored state

| Field | Purpose |
|---|---|
| shared `httpx.Client` | One owned synchronous connection pool |
| resolved profiles | Exact immutable selected profile objects by name |
| adapters | One adapter per selected profile name |
| resolved assignment | Exact five-profile assignment |
| private orchestrator | Existing fully wired `ReviewOrchestrator`, never exposed directly |
| closed state | Prevent use after closure |

Credentials are not exposed through a public runtime representation.

### 17.4 Client policy

```python
httpx.Client(
    trust_env=True,
    follow_redirects=False,
    transport=transport_if_supplied,
)
```

The client has:

- no global base URL;
- no global Authorization header;
- no application cookies;
- no disabled/infinite timeout;
- no retry transport;
- standard environment proxy/certificate behavior.

### 17.5 Construction atomicity

Runtime construction is all-or-nothing:

1. validate every declared raw profile and the complete assignment;
2. determine the exact selected profile-name set;
3. resolve credentials only for selected profiles;
4. resolve all five assignments to selected profile objects;
5. create client;
6. create selected-profile adapters;
7. create five participants;
8. create and retain the private orchestrator;
9. expose runtime.

If any step fails after client construction, close the client before propagating the safe failure.

No Review is created or executed during construction.

### 17.6 Lifecycle states

Exactly:

```text
OPEN
CLOSED
```

Transitions:

```text
construct → OPEN
OPEN.close() → CLOSED
CLOSED.close() → CLOSED
```

`close()` is idempotent.

### 17.7 Context manager

```python
with ConfiguredReviewRuntime.from_config(...) as runtime:
    completed_review = runtime.orchestrator.execute(review)
```

- `OPEN.__enter__()` returns the runtime;
- `CLOSED.__enter__()` raises `LLMRuntimeClosedError` before network activity;
- `__exit__` always closes the client;
- `execute(review)` checks `OPEN` and only then delegates to the private orchestrator;
- `CLOSED.execute(review)` raises `LLMRuntimeClosedError` before Review transition or network activity.

### 17.8 Assignment immutability

The runtime assignment cannot change while open. A different assignment requires a separately constructed runtime.

### 17.9 Safe public surface

May expose:

- `execute(review)` as the only Review execution method;
- non-secret selected profile names;
- participant-to-profile-name mapping;
- open/closed status.

Must not expose:

- raw API keys;
- Authorization headers;
- mutable adapter mapping;
- mutable assignment;
- HTTP client for arbitrary external use;
- the private `ReviewOrchestrator` reference.

---

## 18. Composition Mapping

Given resolved profiles and assignment:

| Assignment field | Participant construction |
|---|---|
| `analyst` | `Analyst(adapter_for(profile))` |
| `solution_architect` | `SolutionArchitect(adapter_for(profile))` |
| `risk_reviewer` | `RiskReviewer(adapter_for(profile))` |
| `critic` | `Critic(adapter_for(profile))` |
| `coordinator` | `Coordinator(adapter_for(profile))` |

Then construct and retain privately:

```python
ReviewOrchestrator(
    analyst,
    solution_architect,
    risk_reviewer,
    critic,
    coordinator,
)
```

`ConfiguredReviewRuntime.execute(review)` checks the runtime state and delegates to this private instance. This matches the actual existing constructor and requires no orchestrator modification.

---

## 19. Validation Matrix

| Invalid condition | Failure | Network call? |
|---|---|---:|
| Missing/blank config path | Configuration | No |
| Unreadable/non-UTF-8 file | Configuration | No |
| Duplicate JSON key | Configuration | No |
| Extra JSON/config field | Configuration | No |
| Empty profiles | Configuration | No |
| Invalid profile name | Configuration | No |
| Invalid URL/model/mode/timeout | Configuration | No |
| Invalid `api_key_env` name | Configuration | No |
| Missing/blank/boundary-whitespace credential referenced by a selected profile | Configuration | No |
| Missing credential referenced only by an unselected profile | No failure; not resolved | No |
| Missing assignment field | Configuration | No |
| Unknown assigned profile | Configuration | No |
| Unsupported runtime role | Unsupported role | No |
| Non-serializable payload | Payload serialization | No |
| Timeout | Request timeout | Attempted once |
| Other transport error | Transport | Attempted once |
| HTTP non-success | HTTP status | Attempted once |
| Invalid envelope body/shape | Response envelope | Attempted once |
| Zero/multiple choices | Response envelope | Attempted once |
| Invalid/non-object content JSON | Structured content | Attempted once |
| Valid JSON object violating role contract | Existing participant output error | Attempted once |
| Runtime entered or executed after close | Runtime closed | No |

---

## 20. Test Fixtures and Equality

### 20.1 Safe raw fixtures

Tests use synthetic endpoints and credential-variable names only.

### 20.2 Secret fixtures

Credential values are synthetic markers supplied through an in-memory environment mapping. Tests assert markers are absent from:

- repr/string values;
- exceptions;
- serialized configuration;
- captured logs, if any;
- smoke diagnostic output.

### 20.3 MockTransport requests

Tests inspect captured HTTPX requests for exact:

- method and target;
- content/accept headers;
- optional Authorization;
- model;
- two-message order;
- `n=1`;
- response-format presence or absence;
- payload delimiting;
- timeout extension values;
- exactly one request.

### 20.4 Runtime identity expectations

For a repeated selected-profile assignment:

```python
resolved.analyst is resolved.risk_reviewer
adapter_for_analyst is adapter_for_risk_reviewer
```

For different profile names, adapters are distinct even if their profile fields happen to be equal.

These identities are composition implementation guarantees, not persisted domain provenance.

---

## 21. Default and Optional Values

| Value | Default |
|---|---|
| API key | absent |
| `api_key_env` | absent |
| base URL | none |
| model | none |
| timeout | none |
| structured-output mode | none |
| profile assignment | none |
| retries | none / forbidden |
| redirects | false |
| temperature | omitted |
| max tokens | omitted |
| streaming | omitted |
| tools | omitted |

Required operational choices remain explicit.

---

## 22. Explicit Non-Models

Slice 7 does not add:

- Provider;
- ProviderRegistry;
- ModelRouter;
- FallbackPolicy;
- RetryPolicy;
- CapabilityProbe;
- PromptTemplate hierarchy;
- Conversation;
- ChatHistory;
- TokenUsage;
- CostEstimate;
- persisted Review configuration;
- domain-level model assignment;
- generic transport port;
- native Ollama/OpenAI provider classes.

`httpx.Client` is an infrastructure dependency, not an application port.

---

## 23. Resolved Data-Model Decisions

This draft proposes:

1. exact enums `LLMRole` and `StructuredOutputMode`;
2. Pydantic frozen, extra-forbidden raw JSON configuration models;
3. profile identity supplied by the `profiles` mapping key;
4. explicit five-field assignment rather than arbitrary role mapping;
5. exact non-secret JSON plus environment-referenced credentials;
6. `SecretStr` only in resolved runtime profiles;
7. one scalar timeout expanded into all four HTTPX phases;
8. role prompts paired with existing Pydantic output model classes;
9. a closed safe adapter-error family with fixed messages, including runtime-closed state;
10. structural validation for every declared profile but credential resolution/adapters only for selected profiles;
11. one adapter per selected profile name;
12. one context-managed runtime owning one shared HTTP client and a private orchestrator;
13. `runtime.execute(review)` as the only execution gate;
14. idempotent close and deterministic rejection of enter/execute after close;
15. role schemas generated and serialized once at definition construction;
16. tolerant external envelope extras but strict expected path/content;
17. no trusted domain or Review-model changes.

---

## 24. Decisions Requiring Review Before Approval

Data-model review shall confirm:

1. whether profile names should remain case-sensitive while examples prefer lowercase;
2. whether model text alone may strip boundary whitespace while all configuration identities remain exact;
3. whether validating all declared profiles but resolving credentials only for selected profiles is the correct balance;
4. whether a missing referenced credential for any selected profile must invalidate the complete runtime;
5. whether `SecretStr` plus a non-serializable resolved dataclass is sufficient for secret safety;
6. whether exact fixed safe error messages, including `LLM runtime is closed`, are appropriately separated;
7. whether external provider-envelope extra fields should remain tolerated;
8. whether duplicate JSON object keys must fail at every nesting level;
9. whether schema generation and deterministic serialization once per role is sufficient;
10. whether one shared client for all selected profiles remains correct when all request-specific auth and timeout values are supplied per call;
11. whether keeping the orchestrator private and exposing only `runtime.execute(review)` is the correct lifecycle boundary.

No `tasks.md`, ADR, configuration example, dependency change, test, or implementation shall be created until this data model is reviewed, corrected where necessary, and explicitly approved.
