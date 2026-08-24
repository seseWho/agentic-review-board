# Slice 7 — Configurable OpenAI-Compatible LLM Adapter v0.1

**Status:** Draft  
**Branch:** `007-llm-adapter`  
**Depends on:** Slices 1–6  
**Canonical sources:** `docs/01-product-vision.md`, `docs/02-requirements.md`, `docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`

## 1. Purpose

Slice 7 introduces the first production LLM adapter for Agentic Review Board.

The adapter SHALL allow the existing five-participant pipeline to call configured local or remote OpenAI-compatible Chat Completions endpoints through the existing provider-neutral `LLMPort`. One adapter instance SHALL represent one immutable endpoint/model profile. Composition SHALL be able to inject the same instance, equivalent instances, or differently configured instances into the five participants, allowing one model or an explicit local/remote combination without introducing a runtime router. Each adapter SHALL convert application-controlled roles and payloads into provider requests and return only an untrusted JSON object for the existing participant boundaries to validate.

This slice connects the completed domain/application workflow to a real model. It does not change participant responsibilities, trusted domain contracts, contextual validation, lifecycle rules, or human decision authority.

## 2. Current Baseline

Slices 1–6 already provide:

- the provider-neutral `LLMPort.generate_structured(*, role, payload)` contract;
- Analyst, Solution Architect, Risk Reviewer, Critic, and Coordinator participants;
- explicit role-specific payloads;
- structural and contextual validation at every participant boundary;
- a complete five-stage lifecycle and orchestration;
- deterministic fakes and tests that require no live model;
- safe participant failure mapping that prevents provider details from entering trusted Review state.

No production adapter, runtime LLM configuration, provider HTTP dependency, or live-model execution path currently exists.

## 3. Scope

### 3.1 In Scope

Slice 7 SHALL:

1. implement one synchronous infrastructure adapter satisfying the existing `LLMPort`;
2. target one OpenAI-compatible `/chat/completions` HTTP contract usable through local or remote endpoints;
3. represent each endpoint/model choice as an immutable named configuration profile containing base URL, model name, optional API key, finite request timeout, and explicit structured-output mode;
4. build application-controlled instructions for exactly the five approved roles;
5. serialize each current participant payload as untrusted review data;
6. request a JSON-object response without requesting or exposing private chain-of-thought;
7. extract exactly one assistant message content value from a successful provider response;
8. parse that content as one JSON object and return it as `Mapping[str, object]`;
9. reject unknown roles, malformed responses, non-object JSON, transport failures, HTTP failures, and invalid configuration;
10. expose provider-neutral adapter/configuration errors without secrets, authorization headers, full prompts, or full responses;
11. preserve deterministic unit and contract tests without live network access;
12. allow explicit composition-time assignment of one configured adapter instance to each of the five participants;
13. provide an explicitly opt-in smoke-test path for every selected configuration profile;
14. document the minimum runtime configuration required to run one-model and mixed-model compositions.

### 3.2 Out of Scope

Slice 7 SHALL NOT introduce:

- changes to `LLMPort`, participant method signatures, domain models, contextual validators, Review lifecycle, or orchestration order;
- UI, CLI product workflow, public API, persistence, review history, RAG, browsing, tools, or external actions;
- automatic retries, backoff, fallback providers, dynamic model routing, load balancing, concurrency, async execution, streaming, or response caching;
- provider discovery, automatic capability detection, a generic provider registry, a generic prompt framework, or an agent framework;
- model-quality scoring, latency service-level guarantees, token-budget optimization, or cost accounting;
- automatic connection checks or network calls during configuration or adapter construction;
- silent JSON repair, Markdown-fence stripping, substring extraction, fuzzy parsing, or provider-response normalization;
- logging of credentials, authorization headers, complete review payloads, complete prompts, or complete model responses;
- provider SDK types in domain, application, participant, or domain-facing contracts;
- loading secrets from committed files or embedding default credentials.

## 4. User Stories

### US1 — Run the existing pipeline with a real model

As a demonstrator operator, I want the existing participants to use a configured OpenAI-compatible endpoint so that the complete Review can execute against a real LLM without changing core business logic.

#### Acceptance criteria

1. The adapter satisfies the existing `LLMPort` structurally.
2. All five approved role values are supported.
3. Each call uses its adapter instance's configured endpoint, model, optional API key, timeout, and structured-output mode.
4. The adapter returns one parsed JSON object to the calling participant.
5. The participant remains responsible for structural and contextual validation of that object.
6. No provider-specific response type crosses the adapter boundary.

### US2 — Keep role instructions under application control

As a product owner, I want each participant request to use explicit application-controlled instructions so that user content cannot redefine participant responsibility or orchestration policy.

#### Acceptance criteria

1. Exactly these role values are accepted: `analyst`, `solution_architect`, `risk_reviewer`, `critic`, and `coordinator`.
2. Unknown role values fail before any network call.
3. Every supported role has an explicit instruction builder or template owned by the adapter layer.
4. The review payload is clearly delimited and represented as data, not concatenated into trusted instructions.
5. Instructions require JSON output compatible with the current participant contract.
6. Instructions do not request hidden chain-of-thought.
7. The adapter does not add a sixth participant or alter upstream responsibilities.

### US3 — Configure secrets and endpoint safely

As an operator, I want runtime configuration to be explicit and validated so that the adapter can run without committing credentials or failing later for avoidable configuration errors.

#### Acceptance criteria

1. Base URL and model name have no misleading usable defaults; API key has no source default.
2. Missing or blank required values fail with a provider-neutral configuration error.
3. API key is optional so that unauthenticated local endpoints are supported.
4. Bearer authentication is sent only when a non-empty API key is configured.
5. The timeout is finite and positive.
6. Structured-output mode is selected explicitly per profile and is never detected automatically.
7. Base URL composition produces exactly one `/chat/completions` target without accidental duplicate separators.
8. Constructing configuration or the adapter performs no network request.
9. Error text and object representations do not reveal the API key.
10. Example configuration contains placeholders only.

### US4 — Fail closed on malformed provider output

As a user, I want malformed provider responses rejected so that untrusted or ambiguously repaired content cannot enter participant validation as if it were a reliable structured response.

#### Acceptance criteria

1. Non-success HTTP responses raise a sanitized adapter error.
2. Invalid response-envelope JSON raises a sanitized adapter error.
3. Missing, empty, duplicated, or wrong-typed assistant content is rejected.
4. Assistant content must parse directly as JSON.
5. The parsed top-level value must be an object.
6. Markdown-wrapped JSON, explanatory prefix/suffix text, arrays, scalars, and null are rejected without repair.
7. Raw response bodies and provider exception details are not included in the public error message.
8. Participant/orchestrator failure mapping continues to produce the already approved stage-safe messages.

### US5 — Preserve deterministic verification

As a maintainer, I want adapter behavior tested without a live provider so that CI remains fast, repeatable, and independent of credentials or model variability.

#### Acceptance criteria

1. Default tests perform no real network calls.
2. Request construction is verified through a deterministic injected HTTP boundary or equivalent controlled substitute.
3. Tests cover every approved role and rejection of an unknown role.
4. Tests cover success, configuration failure, transport failure, HTTP failure, malformed envelopes, malformed content JSON, and non-object JSON.
5. Tests assert that secrets and full payloads do not appear in sanitized errors.
6. Existing fake-`LLMPort` orchestration tests remain valid.
7. Live smoke tests are opt-in, excluded from normal CI, and assert connectivity/contract shape rather than subjective answer quality or fixed latency.
8. Smoke verification covers each selected profile independently, including profiles without credentials.

### US6 — Combine local and remote models explicitly

As a demonstrator operator, I want to assign a configured model endpoint to each logical participant so that I can run all participants on one model or combine local and remote models within the same Review.

#### Acceptance criteria

1. One immutable adapter configuration represents one endpoint/model profile.
2. Every participant receives exactly one `LLMPort` instance at composition time.
3. The same adapter instance or configuration MAY be reused by multiple participants.
4. Different participants MAY receive differently configured adapter instances.
5. Local and remote profiles MAY coexist in one Review execution.
6. Assignments are complete and validated before the Review starts.
7. An assignment does not change silently during the execution.
8. Selection is explicit composition, not dynamic routing, automatic fallback, or participant-controlled model choice.

## 5. Functional Requirements

### LLM-FR-001 — Existing Port Is the Boundary

The production adapter SHALL implement the existing signature:

```python
generate_structured(
    *,
    role: str,
    payload: Mapping[str, object],
) -> Mapping[str, object]
```

Slice 7 SHALL NOT widen this port with provider options, temperature, raw messages, schemas, model names, credentials, timeout values, or transport types.

### LLM-FR-002 — Infrastructure Isolation

Concrete HTTP, authentication, endpoint, and provider-envelope behavior SHALL live in infrastructure. Domain, application, and participant modules SHALL remain free of provider SDK and HTTP client imports.

### LLM-FR-003 — Supported Roles

The adapter SHALL recognize exactly:

- `analyst`;
- `solution_architect`;
- `risk_reviewer`;
- `critic`;
- `coordinator`.

Role comparison SHALL be exact. There SHALL be no case folding, aliasing, whitespace repair, or fallback role.

### LLM-FR-004 — Explicit Role Instructions

Each supported role SHALL map to an explicit instruction definition suitable for its existing output contract.

The role definitions SHALL preserve the responsibilities and prohibitions approved in Slices 1–6. A shared helper MAY cover mechanical JSON/request formatting, but role semantics SHALL remain explicit and independently inspectable.

### LLM-FR-005 — Payload as Untrusted Data

The adapter SHALL serialize the supplied payload as JSON data. User and upstream generated text inside the payload SHALL NOT replace system/developer instructions, select a role, alter the endpoint, add tools, or change request configuration.

### LLM-FR-006 — Request Contract

Each generation call SHALL issue one synchronous POST request to the configured Chat Completions endpoint with conceptually:

- optional bearer authentication, included only when a non-empty API key is configured;
- JSON content type;
- configured model;
- application-controlled instruction message;
- one user/data message containing the serialized payload;
- a JSON-object response-format request only when the profile explicitly selects `JSON_OBJECT`; no response-format field when it selects `PROMPT_ONLY`.

The exact infrastructure representation is deferred to plan review.

### LLM-FR-007 — No Constructor I/O

Configuration loading and adapter construction SHALL be side-effect free with respect to the network. Connectivity SHALL be established only when `generate_structured` is invoked or through an explicitly invoked smoke test.

### LLM-FR-008 — Finite Timeout

Every network request SHALL use one configured finite positive timeout. Slice 7 SHALL NOT add retry behavior. Timeout failure SHALL be reported as a sanitized provider-neutral adapter error.

### LLM-FR-009 — Successful Envelope

A successful provider response SHALL contain exactly one usable assistant message content value at the expected Chat Completions location. Missing, empty, ambiguous, or wrong-typed content SHALL fail closed.

### LLM-FR-010 — Direct JSON Parsing

Assistant content SHALL parse directly as JSON with no repair step. The resulting top-level value SHALL be a JSON object.

The adapter validates only transport/envelope/JSON-object shape. Semantic model validation remains exclusively in the existing participant boundary.

### LLM-FR-011 — Error Categories

The adapter layer SHALL distinguish at least:

- invalid runtime configuration;
- unsupported role;
- transport/timeout failure;
- non-success HTTP response;
- malformed provider envelope;
- malformed or non-object structured content.

Exact public exception types and messages are deferred to data-model/design review, but they SHALL remain provider-neutral and safe.

### LLM-FR-012 — Error Sanitization

Public adapter errors SHALL NOT contain:

- API keys or authorization headers;
- complete endpoint query strings containing sensitive data;
- complete prompts or payloads;
- complete provider response bodies;
- raw nested exception text when it may contain any of the above.

Technical causes MAY be retained through exception chaining for local debugging only when their normal representation is not intentionally surfaced or logged by the product.

### LLM-FR-013 — No Default Full-Content Logging

The adapter SHALL NOT log full instructions, payloads, assistant content, authorization material, or raw response bodies. Logging infrastructure is not required by this slice.

### LLM-FR-014 — Runtime Configuration

Each immutable named runtime configuration profile SHALL support conceptually:

- profile name;
- base URL;
- model;
- optional API key;
- finite timeout;
- structured-output mode.

Base URL and model are required. API key is optional. The approved external representation, environment-variable strategy, and default policy SHALL be fixed during data-model/design review. A local `.env` loader is not required and SHALL NOT be introduced merely because the supplied prototype uses one.

### LLM-FR-015 — One Endpoint Contract

Slice 7 SHALL support one OpenAI-compatible Chat Completions contract. A profile MAY point to OpenAI or another remote compatible service, or to a local server such as Ollama, vLLM, or LM Studio when that server exposes the required compatible contract. Native non-compatible provider APIs and differences requiring provider-specific request/response branches are outside scope.

Compatibility means contract compatibility; it does not imply dependency on the OpenAI Python SDK or endorsement of a particular hosted or local provider.

### LLM-FR-016 — Deterministic Test Boundary

HTTP behavior SHALL be substitutable in tests without monkey-patching global network state or performing real requests. The smallest explicit adapter-specific transport boundary SHALL be preferred over a generic networking framework.

### LLM-FR-017 — Optional Live Smoke Test

A live smoke test MAY be provided only when explicitly selected by the operator. It SHALL:

- require runtime configuration;
- remain outside default unit/contract/CI execution;
- use non-sensitive synthetic input;
- verify every selected profile independently;
- identify the failing profile safely without exposing credentials or sensitive endpoint data;
- verify request success and returned JSON-object shape;
- avoid executing a complete Review merely to establish connectivity;
- avoid subjective checks for intelligence, multilingual quality, code quality, reasoning style, temperature variation, or a hard-coded response-time threshold.

### LLM-FR-018 — Explicit Participant Assignment

Composition SHALL assign exactly one `LLMPort` instance to each approved participant before Review execution. It SHALL support reuse of one adapter and explicit mixtures of differently configured adapter instances. The assignment SHALL not be selected by ReviewInput, generated content, or a participant.

### LLM-FR-019 — Immutable Execution Selection

Endpoint/model assignments SHALL remain fixed for the duration of one Review. Slice 7 SHALL NOT perform automatic fallback, capability detection, load-based selection, or mid-review replacement.

### LLM-FR-020 — Structured-Output Modes

Each profile SHALL choose exactly one mode:

- `JSON_OBJECT`: include the compatible JSON-object response-format request;
- `PROMPT_ONLY`: omit the response-format property and rely on the same explicit role instruction requiring direct JSON.

The adapter SHALL NOT probe capabilities, retry in another mode, or silently downgrade. Both modes remain subject to the same direct JSON-object parsing and participant validation.

### LLM-FR-021 — Provider-Neutral Prompt Definitions

The five explicit role instructions SHALL remain shared across local and remote profiles and separate from HTTP transport mechanics within infrastructure. This separation SHALL remain small and role-specific and SHALL NOT become a generic prompt framework.

### LLM-FR-022 — Core Behavior Is Unchanged

All existing participant structural/contextual validation, same-execution provenance, stage transitions, safe lifecycle messages, and Review completion rules SHALL remain authoritative and unchanged.

## 6. Configuration and Trust Boundaries

The Slice 7 flow SHALL preserve these separate boundaries:

```text
Runtime environment
        ↓ untrusted configuration input
validated named adapter profiles
        ↓ explicit immutable participant assignment
configured LLMPort instance + role + payload
        ↓ untrusted review data
OpenAI-compatible HTTP endpoint
        ↓ untrusted provider envelope/content
direct JSON-object parsing
        ↓ still untrusted
existing participant structural/contextual validation
        ↓ trusted participant artifact
```

Parsing a provider response into a Python mapping does not make it trusted domain data.

## 7. Failure Semantics

Adapter failures occur inside the existing participant-call boundary.

Therefore:

1. the adapter raises a safe provider-neutral exception;
2. the active participant call fails;
3. the existing orchestrator maps that failure to the participant's approved execution-failure category and message;
4. the failed stage stores no partial trusted artifact;
5. all previously completed stages remain unchanged and inspectable;
6. dependent stages do not execute;
7. Review becomes `INCOMPLETE`.

Output that is valid JSON but violates a participant model or contextual reference rule continues to follow that participant's existing output-validation failure path, not an adapter transport failure path.

## 8. Edge Cases

The implementation SHALL define and test at least:

1. each of the five exact roles;
2. unknown, differently cased, or whitespace-padded role;
3. Unicode review content;
4. empty payload mapping where mechanically permitted by the port;
5. payload serialization failure;
6. missing, blank, or whitespace-only required configuration;
7. absent API key for a local unauthenticated profile;
8. blank API key normalized only to absence and never sent as a bearer credential;
9. zero, negative, non-finite, or wrong-typed timeout;
10. each structured-output mode and an unknown mode;
11. base URL with and without a trailing slash;
12. transport connection failure;
13. request timeout;
14. HTTP authentication failure without credential disclosure;
15. another non-success HTTP status with a non-JSON body;
16. success status with malformed envelope JSON;
17. missing `choices`;
18. zero choices;
19. multiple choices;
20. missing message or content;
21. empty or non-string content;
22. direct valid JSON object;
23. JSON array, scalar, or null;
24. fenced JSON;
25. prose followed by JSON;
26. valid JSON object that later fails participant validation;
27. all participants sharing one adapter;
28. explicit local/remote mixed assignment;
29. incomplete participant assignment rejected before Review start;
30. adapter reuse across sequential calls without retained review data;
31. constructor/configuration creation without network activity.

## 9. Supplied Prototype Assessment

The supplied `llm_client.py`, `config.py`, and test files are reference material, not production-ready project code.

Useful inputs retained by this specification:

- externally supplied endpoint, optional key, and model configuration;
- bearer-authenticated Chat Completions requests;
- JSON response handling;
- an explicit live connectivity check as an optional operator action.

Behavior intentionally not adopted:

- network validation during construction;
- automatic retries and sleeps;
- raw provider dictionaries crossing the application boundary;
- default temperature variation;
- catch-all exception conversion containing raw error text;
- tests dependent on live latency, linguistic behavior, code generation, visible reasoning phrases, or stochastic response differences;
- implicit `.env` dependency;
- a placeholder default endpoint or model that appears usable.

## 10. Success Criteria

Slice 7 is complete when:

1. one infrastructure adapter conforms to the unchanged `LLMPort`;
2. one or more immutable profiles can configure compatible local and remote endpoint/model pairs;
3. all five existing participants can use one shared model or an explicit mixed assignment without participant/domain/application provider coupling;
4. supported role requests are explicit and payloads remain data;
5. optional authentication and both explicit structured-output modes behave deterministically;
6. successful provider content returns exactly one JSON object for existing participant validation;
7. malformed or ambiguous responses fail closed without repair;
8. runtime secrets remain external and absent from source, errors, fixtures, and default logs;
9. constructor/configuration creation performs no network call;
10. one finite timeout is applied and no retries occur;
11. deterministic tests cover request construction, profile assignment, and all material failure classes with no live network;
12. optional per-profile smoke verification is separated from CI and subjective quality assertions;
13. the entire Slice 1–7 suite, Ruff, mypy strict, and dependency checks pass;
14. no UI, persistence, dynamic router, generic provider framework, agent framework, or other prohibited expansion is introduced.

## 11. Decisions Requiring Review Before Approval

Specification review SHALL confirm:

1. whether OpenAI-compatible Chat Completions is the correct single v0.1 contract for both remote and compatible local servers;
2. whether the adapter should use a small direct HTTP dependency or a provider SDK, while preserving infrastructure isolation and broad compatibility;
3. the exact external representation of named profiles and participant-to-profile assignments;
4. the timeout representation and default policy;
5. the exact enum/type names for `JSON_OBJECT` and `PROMPT_ONLY`;
6. the smallest testable HTTP boundary;
7. the exact infrastructure module boundary between the five shared role instructions and HTTP transport;
8. whether profile construction and participant assignment require a small composition factory in this slice;
9. whether this material provider/SDK and multi-profile composition decision requires an ADR during planning.

No `plan.md`, `data-model.md`, `tasks.md`, or implementation SHALL be created until this specification is reviewed, corrected where necessary, and explicitly approved.
