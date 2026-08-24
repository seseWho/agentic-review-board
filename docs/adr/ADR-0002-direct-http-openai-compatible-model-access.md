# ADR-0002 — Direct HTTP for OpenAI-Compatible Model Access

**Status:** Proposed  
**Date:** 2026-08-24  
**Decision owners:** Agentic Review Board maintainers  
**Related feature:** `specs/007-llm-adapter/`  
**Related plan:** `specs/007-llm-adapter/plan.md`

## 1. Context

Slices 1–6 complete the provider-neutral five-participant Review pipeline and validate all generated output locally before it enters trusted Review state. The application exposes one deliberately small model capability:

```python
LLMPort.generate_structured(
    *,
    role: str,
    payload: Mapping[str, object],
) -> Mapping[str, object]
```

Until now, deterministic test doubles have implemented this port. Slice 7 must add the first real model connection.

The demonstrator must support:

- one model for all participants;
- different models for different participants;
- local OpenAI-compatible servers;
- remote OpenAI-compatible APIs;
- explicit mixtures of local and remote models;
- environments using standard HTTP proxy and certificate variables.

The integration must preserve provider-neutral core contracts, runtime secret isolation, deterministic CI, fail-closed output handling, and the absence of retries, fallback routing, tools, persistence, or agent frameworks.

A concrete transport strategy and resource lifecycle are therefore required.

## 2. Decision Drivers

The selected approach should:

1. preserve the unchanged `LLMPort`;
2. keep HTTP and provider-envelope types out of domain, application, and participants;
3. work with both local and remote compatible endpoints;
4. avoid coupling the MVP to one hosted provider SDK;
5. support exact optional bearer authentication per configured profile;
6. support explicit `JSON_OBJECT` and `PROMPT_ONLY` modes;
7. provide deterministic request/response tests without live network access;
8. honor standard proxy and certificate environment behavior;
9. use one finite timeout and one request per participant invocation;
10. manage the shared HTTP connection pool explicitly;
11. prevent full prompts, responses, credentials, and provider details from entering safe errors;
12. avoid dynamic routing, fallback, discovery, retries, or generic provider abstractions.

## 3. Decision

Adopt direct synchronous HTTP through **HTTPX** for the first production `LLMPort` adapter.

The dependency policy is:

```text
httpx>=0.28,<0.29
```

The adapter targets one narrow OpenAI-compatible Chat Completions contract:

```text
POST {base_url}/chat/completions
```

Compatibility is defined by the wire contract, not by provider identity. A configured profile may point to OpenAI, another remote compatible service, or a local compatible server such as Ollama, vLLM, or LM Studio.

Provider-native APIs requiring different request or response shapes are outside this decision.

### 3.1 One immutable profile per adapter instance

Each adapter instance has one resolved immutable profile containing:

- exact profile name;
- validated base URL;
- configured model;
- optional runtime API key;
- finite HTTPX timeout;
- explicit structured-output mode.

An adapter does not select another model or endpoint at call time.

### 3.2 Composition instead of routing

The same adapter instance may be injected into all five participants, or different configured instances may be injected explicitly.

Participant assignment is resolved before Review execution and remains fixed for the runtime lifetime.

No router, provider registry, fallback policy, load-based selection, cost-based selection, or model choice from ReviewInput/model output is introduced.

### 3.3 Non-secret JSON and environment credentials

Non-secret profile metadata and the exact five participant assignments may be loaded from one JSON file selected by:

```text
ARB_LLM_CONFIG_PATH
```

The JSON contains `api_key_env` names, never credential values. Selected credentials are resolved from an explicit environment mapping at runtime. Profiles without `api_key_env` are unauthenticated.

All declared profiles are structurally validated. Only profiles selected by the five assignments resolve credentials, create adapters, and participate in smoke checks.

### 3.4 Explicit structured-output modes

Each profile selects exactly:

```text
JSON_OBJECT
PROMPT_ONLY
```

`JSON_OBJECT` adds:

```json
"response_format": {
  "type": "json_object"
}
```

`PROMPT_ONLY` omits `response_format`.

Both use explicit role instructions and the authoritative output model's Pydantic-generated JSON Schema. There is no capability probe, silent downgrade, or retry in another mode.

### 3.5 Request policy

Every call:

- validates the exact approved role first;
- serializes payload as untrusted data;
- uses exactly two messages;
- requests the configured model;
- sets `n=1`;
- applies one finite scalar timeout to connect, read, write, and pool;
- sends bearer authentication only when the selected profile has a non-empty resolved credential;
- follows no redirects;
- performs exactly one POST.

Temperature, token limits, tools, streaming, seed, retries, and provider-specific options are omitted in v0.1.

### 3.6 Response policy

The adapter requires:

- a success HTTP status;
- a JSON-object provider envelope;
- exactly one choice;
- one response message with non-blank string content;
- content that parses directly as one top-level JSON object.

It does not strip fences, extract substrings, repair JSON, normalize content parts, make a correction call, or retry.

The returned mapping remains untrusted until the existing participant structural and contextual validation succeeds.

### 3.7 Runtime lifecycle

A context-managed `ConfiguredReviewRuntime` owns:

- one policy-controlled synchronous `httpx.Client`;
- one adapter per selected profile;
- the five existing participants;
- a private existing `ReviewOrchestrator`.

The shared client uses:

```python
httpx.Client(
    trust_env=True,
    follow_redirects=False,
)
```

It has no global authorization, base URL, application cookies, or disabled timeout. Authentication, complete URL, and timeout are supplied per request.

`ConfiguredReviewRuntime.execute(review)` is the public execution gate. Closing the runtime closes the client. Entering or executing after closure fails before Review transition or network activity.

### 3.8 Proxy and certificate behavior

`trust_env=True` deliberately permits standard HTTPX environment behavior for:

- `HTTP_PROXY`;
- `HTTPS_PROXY`;
- `ALL_PROXY`;
- `NO_PROXY`;
- `SSL_CERT_FILE`;
- `SSL_CERT_DIR`.

Slice 7 adds no custom proxy abstraction, certificate store, per-profile CA field, or corporate-network integration.

### 3.9 Prompt and schema boundary

Five explicit semantic instructions remain infrastructure artifacts, separate from HTTP mechanics.

Each is paired with the existing Pydantic output model:

| Role | Output model |
|---|---|
| Analyst | `ProblemAnalysis` |
| Solution Architect | `SolutionAlternatives` |
| Risk Reviewer | `RiskAssessment` |
| Critic | `CriticalReview` |
| Coordinator | `FinalReview` |

JSON Schema is generated and deterministically serialized once per role definition. It guides the model but never replaces local participant validation.

### 3.10 Testing boundary

Default tests use `httpx.MockTransport` and require no network, endpoint, credential, or installed local model.

The `live_llm` marker classifies and filters live smoke tests; it is not an authorization gate by itself.

Live smoke access requires both:

- explicit `--run-live-llm` command-line authorization, registered through `pytest_addoption`;
- exact `ARB_RUN_LIVE_LLM=1`.

The canonical invocation is:

```text
ARB_RUN_LIVE_LLM=1 pytest -m live_llm --run-live-llm
```

Without both authorizations, live tests skip before loading the configuration, resolving credentials, constructing runtime HTTP resources, or making network requests. Absence of the config path also skips before those actions. Once both authorizations and a config path are present, invalid configuration or selected-profile credentials fail rather than skip.

## 4. Alternatives Considered

### Alternative A — Direct HTTPX against one compatible contract

**Advantages**

- works with local and remote compatible deployments;
- no hosted-provider SDK coupling;
- exact request and response ownership;
- deterministic `MockTransport` tests;
- standard synchronous API and explicit timeouts;
- standard proxy/certificate environment support;
- one small justified infrastructure dependency.

**Disadvantages**

- application infrastructure owns envelope parsing;
- compatible servers may differ in unsupported edge behavior;
- future native provider APIs require separate adapters;
- resource lifecycle must be managed explicitly.

**Assessment:** Selected. It satisfies the demonstrated multi-model requirement with the smallest concrete boundary.

### Alternative B — OpenAI Python SDK

**Advantages**

- convenient OpenAI API models and error handling;
- official support for OpenAI-specific features;
- built-in request construction.

**Disadvantages**

- stronger coupling to one provider's SDK semantics;
- local compatible endpoints may behave differently from SDK assumptions;
- provider-specific types can leak unless carefully contained;
- structured-output and error behavior may vary by SDK version;
- adds capabilities not required by the MVP.

**Assessment:** Rejected for v0.1. The product needs a compatible wire contract across local and remote endpoints, not OpenAI-specific capabilities.

### Alternative C — Multiple provider SDKs

**Advantages**

- native support for each provider;
- access to proprietary features;
- potentially richer provider-specific diagnostics.

**Disadvantages**

- multiple runtime dependencies;
- multiple request/response and error models;
- substantial configuration and test matrix;
- encourages provider registry/routing abstractions;
- exceeds current evidence and MVP needs.

**Assessment:** Rejected. No demonstrated native-provider requirement justifies this complexity.

### Alternative D — Standard-library HTTP only

**Advantages**

- no new runtime dependency;
- complete implementation control.

**Disadvantages**

- more handwritten request, TLS, proxy, error, and test-support code;
- less convenient deterministic transport injection;
- greater maintenance burden for no product benefit.

**Assessment:** Rejected. HTTPX provides the needed HTTP boundary and testability with less custom infrastructure.

### Alternative E — Generic model router/framework

**Advantages**

- dynamic provider/model selection;
- possible fallback, balancing, and policy extension.

**Disadvantages**

- unnecessary workflow and configuration abstraction;
- hidden model switching weakens traceability;
- introduces fallback/retry semantics not approved;
- increases tests and failure modes substantially;
- contradicts simplicity-first and evidence-driven architecture.

**Assessment:** Rejected. Static composition already supports all approved one-model and mixed-model scenarios.

## 5. Consequences

### Positive consequences

- the same adapter supports compatible local and remote deployments;
- each participant can use an explicitly selected model;
- core layers remain provider neutral;
- configuration and credentials remain separated;
- deterministic CI covers exact HTTP behavior;
- standard proxy/certificate variables remain usable;
- output remains fail-closed and locally validated;
- one shared client avoids per-call connection-pool construction.

### Negative consequences

- HTTPX becomes a runtime dependency;
- infrastructure must maintain the narrow compatible envelope;
- endpoints without the selected compatible contract cannot be used;
- JSON-object support must be configured manually;
- operators must manage JSON metadata and environment credentials;
- the runtime must be closed explicitly or through its context manager.

### Accepted trade-offs

- provider-envelope extras are tolerated while the required path remains strict;
- one scalar timeout is applied to all four phases;
- the same shared HTTP client serves different endpoints with per-request auth and timeout;
- prompt-only mode may produce more invalid model responses, which fail closed rather than trigger repair;
- unselected profiles may remain in configuration without requiring their credentials.

## 6. Security and Failure Consequences

- no credential appears in committed JSON;
- no bearer header is sent for unauthenticated profiles;
- credentials with boundary whitespace are rejected rather than repaired;
- errors use fixed provider-neutral messages;
- full prompts, payloads, bodies, provider messages, endpoints, models, and credentials are absent from safe error text;
- raw nested causes may be chained for local diagnosis but are not copied into user-facing messages;
- no complete prompt or response is logged by default;
- no response authorizes an action;
- no model output changes endpoint, profile, credential, role, or orchestration.

## 7. Testing and Compliance Requirements

Implementation governed by this ADR must deterministically demonstrate:

- exact raw configuration and assignment validation;
- selected-only secret resolution;
- optional authentication;
- exact role-to-output-schema mapping;
- `n=1`;
- both structured-output modes;
- one request and no retry;
- equal finite timeout phases;
- strict envelope/content parsing;
- fixed sanitized error classes;
- one adapter per selected profile and reuse by assignment;
- one shared owned client;
- context-managed close and closed-runtime rejection;
- unchanged participant output validation;
- no infrastructure imports in domain, application, or participants;
- no live-network requirement in default tests.

Quality gates remain:

```text
pytest
ruff check .
mypy
pip check
```

## 8. Reconsideration Conditions

Revisit this decision if evidence shows:

- a required provider or local runtime cannot expose the compatible contract;
- compatible-envelope differences require accumulating provider-specific branches;
- HTTPX cannot satisfy a required proxy, certificate, or deployment constraint;
- synchronous execution prevents an approved product requirement;
- a provider-native structured-output feature provides material value unavailable through the compatible contract;
- retry, fallback, routing, streaming, or cost/usage requirements are explicitly approved;
- the dependency version family becomes unsupported or insecure;
- connection lifecycle cannot be owned cleanly by the application composition boundary.

Any reconsideration requires a new or superseding ADR. It must not silently expand this adapter.

## 9. Relationship to Existing Decisions

ADR-0001 remains authoritative for trusted Pydantic contracts and local structural validation.

ADR-0002 uses Pydantic JSON Schema only as provider guidance. It does not move the trust boundary to the model provider and does not change any domain contract.

This decision implements the LLM Adapter boundary intentionally deferred by the canonical architecture while preserving:

- explicit five-role semantics;
- provider-independent core code;
- deterministic testing;
- visible fail-closed participant failures;
- human decision authority;
- no autonomous external action.
