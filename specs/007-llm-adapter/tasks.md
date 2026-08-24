# Tasks: Configurable OpenAI-Compatible LLM Adapter v0.1

**Branch**: `007-llm-adapter`  
**Specification**: `specs/007-llm-adapter/spec.md` — Approved  
**Plan**: `specs/007-llm-adapter/plan.md` — Approved  
**Data model**: `specs/007-llm-adapter/data-model.md` — Approved  
**Status**: Approved — reviewed against specification, plan, and data model; implementation authorized by reviewed blocks

## 1. Execution Rules

- Complete tasks in identifier order unless marked `[P]` within the same tests-first group.
- Every behavior block begins with failing deterministic tests.
- Confirm the intended red failure before adding production behavior.
- Implement only enough production code to make the approved block green.
- Run the focused tests after every small implementation step.
- Run the full existing suite at every block review gate.
- Do not begin the next block until the current block is reviewed.
- Live endpoints, local models, credentials, and network access are never required by default tests or CI.
- Do not create UI, persistence, retries, fallbacks, routing, provider registries, native provider adapters, or generic prompt/transport frameworks.
- Do not modify `LLMPort`, existing participant signatures, domain outputs, Review lifecycle, or orchestration behavior.

Task notation:

- `[P]`: may be completed in parallel with other `[P]` tasks in the same group after their shared prerequisites.
- `[TEST]`: test or verification task that must precede corresponding production behavior.
- `[DOC]`: documentation or decision record.
- `[GATE]`: mandatory review/checkpoint; stop before the next block.

---

## 2. Phase 1 — Architectural Decision and Baseline

**Goal:** Record the approved integration decision before introducing the runtime dependency or infrastructure code.

- [X] T001 [DOC] Create `docs/adr/ADR-0002-direct-http-openai-compatible-model-access.md` covering direct synchronous HTTPX versus provider SDKs, local/remote compatibility, JSON metadata plus environment credentials, immutable profiles, static composition, runtime client ownership, prompt schemas, explicit output modes, proxy/certificate behavior, and rejected routing/retry alternatives.
- [X] T002 [DOC] Cross-check ADR-0002 against `docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`, and the three approved Slice 7 artifacts; remove any scope expansion.
- [X] T003 [TEST] Run and record the existing full pytest suite before Slice 7 production changes.
- [X] T004 [TEST] Run and record existing Ruff, mypy strict, and `pip check` baselines.
- [X] T005 [GATE] Review ADR-0002 and baseline results; stop before configuration implementation.

### Phase 1 evidence

- Initial ADR commit: `dbc02bf800e46e9a90bbedaf13a6e63261daebe1`.
- Review corrections commit: `7fe42f94aca9ece531580d01811e4b7ba51deeaa`.
- ADR acceptance commit: `f9528c2ce7d026cfd086c196b2ee8b70b6a967ac`.
- ADR status: **Accepted**; T005 approved on 2026-08-24.
- Canonical cross-check: no change to `LLMPort`, participant responsibilities, Review lifecycle, human authority, or core provider independence; no retry, fallback, routing, persistence, tool, UI, or framework expansion.
- Baseline source: Slice 6 final head `6941753b1d0e00e9df7825ee6bc885f27bd63010`, inherited by `main` before the documentation-only Slice 7 commits.
- GitHub Actions: CI run 145, completed successfully.
- Python 3.12: install, `pip check`, pytest, Ruff, and mypy all successful.
- Python 3.13: install, `pip check`, pytest, Ruff, and mypy all successful.
- No Slice 7 production code or runtime dependency exists at this gate.


---

## 3. Phase 2 — Safe Errors and Raw Configuration Contracts

**Goal:** Define the closed safe error family and deterministic non-secret configuration parsing.

### 3.1 Tests first

- [X] T006 [TEST] Add failing tests for the exact `StructuredOutputMode` values and rejection of aliases, different case, blanks, and unknown modes in `tests/unit/infrastructure/llm/test_config.py`.
- [X] T007 [P] [TEST] Add failing tests for exact `LLMRole` values and rejection without normalization in `tests/unit/infrastructure/llm/test_config.py`.
- [X] T008 [P] [TEST] Add failing tests for `RawLLMProfile` required fields, forbidden extras, model normalization, finite positive timeout, and boolean/non-numeric rejection.
- [X] T009 [P] [TEST] Add failing base-URL tests covering HTTP/HTTPS, loopback, ports, `/v1`, one trailing slash, missing host/scheme, credentials, query, fragment, unsupported scheme, control characters, and pre-appended `/chat/completions`.
- [X] T010 [P] [TEST] Add failing `api_key_env` identity tests covering valid names, absent authentication, blanks, whitespace, invalid first character, punctuation, and exact preservation.
- [X] T011 [P] [TEST] Add failing `ParticipantLLMAssignment` tests for five mandatory exact references, forbidden extras, invalid identity grammar, and no whitespace/case repair.
- [X] T012 [P] [TEST] Add failing `RawLLMRuntimeConfig` tests for at least one profile, exact profile-name grammar, forbidden top-level extras, complete assignments, exact cross-reference resolution, and declared-but-unselected profiles.
- [X] T013 [P] [TEST] Add failing JSON-loader tests for absent/blank path, unreadable file, non-UTF-8, malformed/non-object JSON, duplicate keys at every nesting level, and safe errors.
- [X] T014 [P] [TEST] Add failing fixed-message and inheritance tests for all approved adapter error classes, including `LLMRuntimeClosedError`.
- [X] T015 [TEST] Run the Phase 2 tests and confirm failure is caused only by missing Slice 7 contracts.

#### Phase 2 red evidence

- Contract-test commit: `d14ef90192ba1b441ca9690e7ad89658cb1c9f96`.
- Focused collection stops with exactly one expected error: `ModuleNotFoundError: No module named 'agentic_review_board.infrastructure'`.
- The failure is caused by the intentionally absent Slice 7 infrastructure package; no production behavior has been added.
- T016 is aligned with accepted ADR-0002 at `httpx>=0.28,<0.29`.

### 3.2 Minimal implementation

- [X] T016 Add the constrained `httpx>=0.28,<0.29` runtime dependency to `pyproject.toml`.
- [X] T017 Create infrastructure package initializers under `src/agentic_review_board/infrastructure/llm/`.
- [X] T018 Implement the closed safe error family and exact messages in `src/agentic_review_board/infrastructure/llm/errors.py`.
- [X] T019 Implement `StructuredOutputMode`, `LLMRole`, and strict raw profile models in `src/agentic_review_board/infrastructure/llm/config.py`.
- [X] T020 Implement exact five-field assignment and top-level configuration cross-validation.
- [X] T021 Implement UTF-8 JSON loading with duplicate-key rejection at all nesting levels and `ARB_LLM_CONFIG_PATH` boundary validation.
- [X] T022 Map every public loader/validation failure to exact safe `LLMConfigurationError` without dynamic detail.
- [X] T023 Run focused Phase 2 tests to green.
- [X] T024 Run full pytest, Ruff, mypy strict, and `pip check`.
- [X] T025 [GATE] Review configuration scope, exact identity behavior, URL policy, error safety, dependency diff, and regression results; stop before secret resolution.

### Phase 2 implementation evidence

- Runtime dependency: `httpx>=0.28,<0.29`; HTTPX is not imported outside infrastructure.
- Production contracts: `infrastructure/llm/errors.py` and `infrastructure/llm/config.py`, plus package initializers.
- Focused configuration suite after gate corrections: **132 passed**.
- Full repository suite after gate corrections: **814 passed**.
- Ruff: **passed**.
- Strict mypy: **passed** over 39 source files.
- `pip check`: **passed**, no broken requirements.
- Configuration loading performs file/UTF-8/JSON/Pydantic validation only; no network, credential resolution, adapter construction, retry, routing, or provider SDK behavior exists.
- Every public loader failure maps to fixed `LLM configuration invalid`; the other approved error classes also expose only their fixed message.
- T025 review corrections: immutable copied profile mapping with explicit safe serialization; rejection of invalid/out-of-range ports, whitespace, backslashes, malformed percent escapes, and multiple trailing slashes; deterministic unreadable-file error coverage.
- Review-correction tests commit: `f4f49920f4b644e709b79fc727fdd2cae47ae4f9`.
- Final correction head: `55615ec53546f3efcdad151da2a4399a371f306a`.
- T025 approved on 2026-08-24; Phase 3 tests-first work authorized.

---

## 4. Phase 3 — Selected Profiles, Secret Resolution, and Assignments

**Goal:** Resolve only selected profiles into safe immutable runtime values.

### 4.1 Tests first

- [X] T026 [TEST] Add failing tests that determine the exact selected profile-name set from five assignments while structurally retaining unselected profiles.
- [X] T027 [P] [TEST] Add failing tests for unauthenticated selected profiles and selected profiles using an explicit in-memory environment mapping.
- [X] T028 [P] [TEST] Add failing tests for missing, blank, leading-space, and trailing-space credentials referenced by selected profiles.
- [X] T029 [P] [TEST] Add failing tests proving credentials referenced only by unselected profiles are never read and do not block resolution.
- [X] T030 [P] [TEST] Add failing tests proving credential values never appear in repr, safe errors, or configuration serialization.
- [X] T031 [P] [TEST] Add failing tests for scalar timeout expansion into equal connect/read/write/pool HTTPX phases.
- [X] T032 [P] [TEST] Add failing identity tests proving repeated assignments reuse the exact resolved profile object while different profile names produce distinct resolved objects.
- [X] T033 [TEST] Run Phase 3 tests and confirm the intended red state.

#### Phase 3 red evidence

- Contract-test commit: `c6f24aa5fc3f5c354da74d62fc911f0c9b63b796`.
- Focused collection stops with the expected missing contract: `ImportError: cannot import name 'ResolvedLLMProfile'`.
- The red state is caused exclusively by the intentionally absent Phase 3 resolved-profile and resolution contracts.
- No secret resolution, HTTP timeout object, resolved assignment, adapter, or network behavior has been added.

### 4.2 Minimal implementation

- [X] T034 Implement immutable `ResolvedLLMProfile` with protected `SecretStr`, normalized base URL, exact model, `httpx.Timeout`, and output mode.
- [X] T035 Implement selected-profile discovery and credential resolution from an explicit read-only environment mapping.
- [X] T036 Reject selected-profile credentials with missing, blank, or boundary-whitespace values without repair.
- [X] T037 Implement immutable `ResolvedParticipantLLMAssignment` with exact resolved-object reuse.
- [X] T038 Ensure resolved runtime values provide no ordinary secret-bearing serialization or repr.
- [X] T039 Run focused Phase 3 tests to green.
- [X] T040 Run full pytest, Ruff, mypy strict, and `pip check`.
- [X] T041 [GATE] Review selected/unselected semantics, secret handling, timeout construction, identity reuse, and regressions; stop before prompts.

### Phase 3 implementation evidence

- Production commit: `ea00d49ca03c28fe71f699ab73af5b5b45194174`.
- Focused configuration/resolution suites after gate corrections: **154 passed**.
- Full repository suite after gate corrections: **836 passed**.
- Ruff: **passed**.
- Strict mypy: **passed** over 40 source files.
- `pip check`: **passed**, no broken requirements.
- Resolved profiles and assignments are frozen slotted dataclasses, not Pydantic input models and expose no ordinary secret-bearing serialization API.
- Only exact selected profile names resolve credentials and produce one resolved object each; repeated assignments reuse that exact object.
- Unselected profiles remain in raw validated configuration and cause no environment reads.
- Scalar timeouts populate finite connect/read/write/pool phases equally.
- T041 review corrections: timeout is reconstructed from a private immutable scalar on every access, preventing nested mutation from degrading the profile; all environment-mapping read failures map to fixed `LLMConfigurationError`.
- Review-correction tests commit: `c254c659a95a3aeec82b5d61f72e3b0f8aef73ad`.
- Review-correction production commit: `fb183a6440109ca14cefbf4f77af2cf1025de750`.
- T041 approved on 2026-08-24; Phase 4 tests-first work authorized.

---

## 5. Phase 4 — Role Semantics and Authoritative Output Schemas

**Goal:** Build five explicit prompt definitions without duplicating structural domain contracts.

### 5.1 Tests first

- [X] T042 [TEST] Add failing tests for the closed role-to-output-model mapping: Analyst/ProblemAnalysis, Solution Architect/SolutionAlternatives, Risk Reviewer/RiskAssessment, Critic/CriticalReview, and Coordinator/FinalReview.
- [X] T043 [P] [TEST] Add failing tests that each role has distinct non-blank semantic instructions preserving its approved responsibility and prohibitions.
- [X] T044 [P] [TEST] Add failing tests for shared requirements: payload as untrusted data, direct JSON object, no Markdown/prose, no private chain-of-thought request, and no external action.
- [X] T045 [P] [TEST] Add failing tests proving JSON Schema is generated from the exact existing Pydantic model and deterministically serialized once per role definition.
- [X] T046 [P] [TEST] Add failing tests proving cached prompt/schema definitions contain no Review data, model endpoint, credential, or provider response.
- [X] T047 [P] [TEST] Add failing unknown-role tests proving failure occurs before payload serialization.
- [X] T048 [TEST] Run Phase 4 tests and confirm the intended red state.

#### Phase 4 red evidence

- Contract-test commit: `3c9b8f5b5d0f15fa7691e122c7e71c13bb904676`.
- Focused collection stops with the expected missing module: `ModuleNotFoundError: No module named 'agentic_review_board.infrastructure.llm.prompts'`.
- The red state is caused exclusively by the intentionally absent Phase 4 prompt-definition contracts.
- No prompt module, schema cache, HTTP request, adapter, or network behavior has been added.

### 5.2 Minimal implementation

- [X] T049 Implement immutable `RolePromptDefinition` and the closed role/model mapping in `src/agentic_review_board/infrastructure/llm/prompts.py`.
- [X] T050 Implement five explicit semantic instruction constants with only approved role behavior.
- [X] T051 Generate and deterministically serialize each output model's `model_json_schema()` once when prompt definitions are constructed.
- [X] T052 Implement exact role lookup raising `UnsupportedLLMRoleError`.
- [X] T053 Run focused Phase 4 tests to green.
- [X] T054 Run full pytest, Ruff, mypy strict, and `pip check`.
- [X] T055 [GATE] Review role separation, schema source of truth, prompt-injection boundary, absence of duplicate model hierarchy, and regressions; stop before HTTP requests.

### Phase 4 implementation evidence

- Production commit: `8da078a362a5e1ff1a49283241897bfa9e99fbea`.
- Focused prompt suite: **36 passed**.
- Full repository suite: **872 passed**.
- Ruff: **passed**.
- Strict mypy: **passed** over 42 source files.
- `pip check`: **passed**, no broken requirements.
- Exactly five frozen role definitions are constructed once; schemas derive directly from the five existing Pydantic output models and are serialized deterministically.
- Lookup is exact and fail-closed; no fallback role, provider/model-specific prompt, payload state, credential, endpoint, HTTP behavior, prompt framework, or duplicate output model exists.
- T055 approved on 2026-08-24; Phase 5 tests-first work authorized.

---

## 6. Phase 5 — HTTP Request Construction

**Goal:** Implement one exact synchronous request per adapter call with no network-dependent tests.

### 6.1 Tests first

- [X] T056 [TEST] Add failing MockTransport tests for POST target construction from base URLs with and without normalized trailing slash.
- [X] T057 [P] [TEST] Add failing tests for exact `Content-Type`, `Accept`, and conditional `Authorization` headers, including absence of an empty bearer.
- [X] T058 [P] [TEST] Add failing tests for the exact two-message order separating system-controlled instruction/schema from serialized untrusted payload.
- [X] T059 [P] [TEST] Add failing tests for exact configured model and `n: 1`.
- [X] T060 [P] [TEST] Add failing tests for exact `response_format: {"type": "json_object"}` in `JSON_OBJECT`.
- [X] T061 [P] [TEST] Add failing tests proving `response_format` is absent in `PROMPT_ONLY`.
- [X] T062 [P] [TEST] Add failing tests for one explicit per-request timeout with equal connect/read/write/pool extension values.
- [X] T063 [P] [TEST] Add failing tests for Unicode payload serialization and deterministic separation/delimiting.
- [X] T064 [P] [TEST] Add failing tests for non-serializable payload mapping to exact `LLMPayloadSerializationError` before any request.
- [X] T065 [P] [TEST] Add failing tests proving no temperature, max tokens, tools, streaming, seed, retry metadata, cookies, or provider-specific options are sent.
- [X] T066 [TEST] Run Phase 5 tests and confirm the intended red state and zero accidental live requests.

#### Phase 5 red evidence

- Request-contract commits: `df9d05887a4ed2dea2d0aa0b2a38b447a439c689`, `261730731775f70556979f6dcfef29eb2349d062`.
- Focused collection stops with the expected missing module: `ModuleNotFoundError: No module named 'agentic_review_board.infrastructure.llm.openai_compatible'`.
- MockTransport handlers are the only HTTP boundary in the tests; no live request, endpoint, credential, or installed model is used.
- Response processing remains intentionally outside this block: successful request capture stops inside the mock handler before any Phase 6 behavior.

### 6.2 Minimal implementation

- [X] T067 Implement `OpenAICompatibleLLMAdapter` construction with one resolved profile, shared HTTPX client, and immutable prompt definitions.
- [X] T068 Implement exact role-first validation and deterministic payload/schema rendering.
- [X] T069 Implement headers, target, two-message body, model, and `n=1`.
- [X] T070 Implement exact structured-output-mode request branching without probing, fallback, or retry.
- [X] T071 Issue exactly one synchronous client POST with the resolved profile timeout.
- [X] T072 Map payload serialization failures safely before network activity.
- [X] T073 Run focused Phase 5 tests to green.
- [X] T074 Run full pytest, Ruff, mypy strict, and `pip check`.
- [X] T075 [GATE] Review captured requests, authentication isolation, schema/payload separation, timeout, forbidden fields, request count, and regressions; stop before response processing.

### Phase 5 implementation evidence

- Production commit: `d1c62f2fdfe8c2cb1fb3973478aae8355227344d`.
- Focused request-construction suite after gate corrections: **16 passed**.
- Full repository suite after gate corrections: **888 passed**.
- Ruff: **passed**.
- Strict mypy: **passed** over 44 source files.
- `pip check`: **passed**, no broken requirements.
- Every tested generation performs exactly one MockTransport-captured POST with explicit per-request timeout; unsupported roles and unserializable payloads fail before the handler.
- System instruction/schema and deterministically serialized Unicode payload occupy separate messages with explicit untrusted-data delimiters.
- Authentication is per request and omitted for unauthenticated profiles; no global client auth, retry, fallback, tool, streaming, temperature, or provider option is introduced.
- Until Phase 6, a returned HTTP response is deliberately rejected with fixed `LLMResponseEnvelopeError`; no raw or placeholder mapping can cross the port.
- T075 review correction: the adapter snapshots every valid `Mapping[str, object]` into a plain per-call dictionary inside the safe serialization boundary; mapping iteration/snapshot failures are sanitized before network activity.
- Review-correction tests commit: `0e24b4485cf8a8b2a3777d79b79d204a782dcce5`.
- Review-correction production commit: `e2eb445573b00f64a0a6048f14ac35e3ee27c76b`.
- T075 approved on 2026-08-24; Phase 6 tests-first work authorized.

---

## 7. Phase 6 — Provider Response and Safe Failure Processing

**Goal:** Return only one directly parsed JSON object while preserving existing participant validation ownership.

### 7.1 Tests first

- [X] T076 [TEST] Add failing success tests for the accepted minimum envelope and ignored unrelated provider-envelope extras.
- [X] T077 [P] [TEST] Add failing tests for timeout subclasses mapping to exact `LLMRequestTimeoutError`.
- [X] T078 [P] [TEST] Add failing tests proving HTTPX `RequestError` failures—including connection, proxy, protocol, and HTTP content-decoding failures—map to exact `LLMTransportError`; keep response-body `json.JSONDecodeError` under T080.
- [X] T079 [P] [TEST] Add failing tests for 3xx/4xx/5xx statuses mapping to exact `LLMHTTPStatusError` with redirects disabled.
- [X] T080 [P] [TEST] Add failing envelope tests for response-body `json.JSONDecodeError`, non-object envelope JSON, absent/wrong `choices`, zero/multiple choices, wrong choice/message, and absent/blank/non-string content.
- [X] T081 [P] [TEST] Add failing structured-content tests for malformed JSON, array, string, number, boolean, null, fenced JSON, and prefix/suffix prose.
- [X] T082 [P] [TEST] Add failing sanitization tests using secret, endpoint, model, payload, prompt, response-body, and provider-error markers.
- [X] T083 [P] [TEST] Add failing tests proving exactly one attempted request and no JSON repair, second request, mode downgrade, or fallback.
- [X] T084 [P] [TEST] Add failing tests proving a valid JSON object is returned unchanged for participant validation even when semantically invalid.
- [X] T085 [TEST] Run Phase 6 tests and confirm the intended red state.

#### Phase 6 red evidence

- Response-contract commit: `1107615cd4f61d724487641e2fc3c4e2708ab299`.
- Focused result against the Phase 5 fail-closed placeholder: **32 failed, 17 passed**.
- Failures are the intended missing Phase 6 behaviors: success parsing, timeout/transport/status taxonomy, structured-content classification, sanitized mapping, and unchanged valid-object return.
- Passing cases are envelope shapes already rejected by the Phase 5 placeholder; they do not indicate response-processing implementation.
- All HTTP interactions use MockTransport and each retry/no-repair assertion observes at most one attempted request.

### 7.2 Minimal implementation

- [X] T086 Implement ordered timeout, transport, and HTTP-status exception mapping without copying nested text.
- [X] T087 Implement strict provider-envelope shape validation with tolerated unrelated envelope extras.
- [X] T088 Implement one direct JSON parse and top-level object requirement.
- [X] T089 Preserve valid mapping content unchanged and retain no call-specific state.
- [X] T090 Ensure adapter errors use only fixed safe messages while optionally chaining causes.
- [X] T091 Run focused Phase 6 tests to green.
- [X] T092 Run full pytest, Ruff, mypy strict, and `pip check`.
- [X] T093 [GATE] Review failure taxonomy, sanitization, direct parsing, no-repair behavior, state retention, and regressions; stop before composition.

### Phase 6 implementation evidence

- Production commit: `a203f29f112b84c9131a79f67add015941d0f4ac`.
- Focused response suite: **49 passed**; combined request/response suites: **65 passed**.
- Full repository suite: **937 passed**.
- Ruff: **passed**.
- Strict mypy: **passed** over 45 source files.
- `pip check`: **passed**, no broken requirements.
- Failure mapping is ordered timeout → other RequestError → non-2xx status → envelope → structured content, with only fixed public messages.
- Envelope extras are ignored while the required one-choice/message/content path remains strict.
- Content receives one direct `json.loads`; fences, prose, arrays, scalars, booleans, and null fail without repair or a second request.
- A valid top-level object is returned unchanged and remains untrusted for existing participant validation; the adapter retains no call-specific state.
- T093 review correction rejects non-standard `NaN`, `Infinity`, and `-Infinity` at both request serialization and structured-content parsing boundaries.\n- Review tests commits: `10d5e8eb0044b0ac6680df22322ea31c217c5903`, `bece17f51433f1e561baf1fa61a3159ba61201a4`.\n- Review production commit: `56d80760fa564decfed4eeeeef41bf5794c51858`.\n- Final focused request/response suites: **71 passed**; full repository suite: **943 passed**.\n- Ruff, strict mypy over 45 source files, and `pip check`: **passed**.\n- T093 approved on 2026-08-24; Phase 7 tests-first work authorized.

---

## 8. Phase 7 — Runtime Composition and Lifecycle

**Goal:** Wire selected profiles into the existing five participants behind one resource-safe execution gate.

### 8.1 Tests first

- [X] T094 [TEST] Add failing tests for the small HTTP-client constructor's explicit arguments (`trust_env=True`, `follow_redirects=False`, optional MockTransport, no global auth/base URL/cookies) plus observable redirect behavior; do not inspect private HTTPX attributes.
- [X] T095 [P] [TEST] Add failing tests for one adapter per selected profile and exact adapter reuse across repeated participant assignments.
- [X] T096 [P] [TEST] Add failing tests for all-five-shared, five-distinct, and mixed local/no-key plus remote/key compositions.
- [X] T097 [P] [TEST] Add failing tests matching the actual five-argument `ReviewOrchestrator` constructor without modifying it.
- [X] T098 [P] [TEST] Add failing ordering tests proving every naturally fallible configuration, credential, and assignment step completes before client creation; verify the implementation closes the client defensively on an unexpected later exception without adding an injectable participant/orchestrator factory solely for this test.
- [X] T099 [P] [TEST] Add failing `OPEN` context-entry, idempotent close, automatic context exit, and `CLOSED.__enter__` tests.
- [X] T100 [P] [TEST] Add failing public-API tests proving `runtime.execute(review)` is the only documented/public execution path and that no public properties or exports expose the orchestrator, client, or adapters; do not claim absolute inaccessibility of underscore-prefixed Python internals.
- [X] T101 [P] [TEST] Add failing tests proving closed-runtime execution raises exact `LLMRuntimeClosedError` before Review transition or request.
- [X] T102 [P] [TEST] Add failing sequential-Review tests proving fixed assignments and no retained Review/prompt/response data.
- [X] T103 [P] [TEST] Add failing safe-public-surface tests for profile names, participant/profile mapping, lifecycle state, and absence of credentials.
- [X] T104 [TEST] Run Phase 7 tests and confirm the intended red state.

#### Phase 7 red evidence

- Composition-contract commits: `cdf70c7fc28ff24a96d936d4b5b0e6a018a307a8` through `af2f3a8fcf136417dba08575f26dea53eaeabba9`.
- The focused Phase 7 file defines **20 deterministic tests** covering client policy, adapter identity/reuse, supported topologies, exact orchestrator wiring, construction atomicity, lifecycle, public surface, closed execution, sequential statelessness, and safe metadata.
- Focused collection stops with exactly one expected error: `ModuleNotFoundError: No module named 'agentic_review_board.infrastructure.llm.composition'`.
- The failure is caused exclusively by the intentionally absent Phase 7 composition module; no runtime composition or lifecycle production behavior has been added.
- The Phase 7 test file passes Ruff and formatting checks.
- All HTTP behavior remains MockTransport-backed; no live endpoint, credential, or installed model is required.

### 8.2 Minimal implementation

- [X] T105 Implement `ConfiguredReviewRuntime.from_config` with atomic validation, selected-profile secret resolution, and exact assignment.
- [X] T106 Create the policy-controlled shared client and close it on any later construction failure.
- [X] T107 Construct/reuse selected-profile adapters and inject them into the five existing participant classes.
- [X] T108 Construct and retain the existing `ReviewOrchestrator` privately.
- [X] T109 Implement `OPEN/CLOSED`, context management, idempotent `close`, and safe public metadata.
- [X] T110 Implement `execute(review)` state guard and private orchestrator delegation.
- [X] T111 Prevent public exposure of credential-bearing profiles, client, adapter mapping, mutable assignment, and orchestrator.
- [X] T112 Run focused Phase 7 tests to green.
- [X] T113 Run full pytest, Ruff, mypy strict, and `pip check`.
- [X] T114 [GATE] Review construction atomicity, resource ownership, mixed composition, execution gating, statelessness, public surface, and regressions; stop before integration/architecture tests.

### Phase 7 implementation evidence

- Hermetic-test correction commit: `4671626f90224325eedfe9ff8476bab3d391ebbb`; every runtime test supplies MockTransport while production retains `trust_env=True`.
- Production composition commit: `2c7cfb1d53f00e376e71a465c7c8a36c74cf4f42`.
- Focused composition suite after review correction: **21 passed**.
- Full repository suite after review correction: **964 passed**.
- Ruff: **passed**.
- Strict mypy: **passed** over 47 source files.
- `pip check`: **passed**, no broken requirements.
- One client is created after complete selected-profile resolution, one adapter per selected profile name is reused across fixed participant assignments, and the existing five-argument orchestrator is retained privately.
- Construction closes the client on every later exception; lifecycle is exactly OPEN/CLOSED with idempotent close, guarded enter/execute, and context-exit cleanup.
- Public runtime operations are limited to `from_config`, `execute`, and `close`; safe immutable metadata exposes only selected names, participant/name mapping, and lifecycle state.
- Sequential execution retains fixed composition but no Review, prompt, or response objects.
- T114 review correction preserves the primary construction exception when defensive client cleanup also fails; cleanup is still attempted exactly once and its dynamic detail is not promoted.\n- Review test commit: `8c2c2794f32737f9cf32c72ba1910704da13a918`; production correction commit: `a4846a7946d5e82540aafe87b31892603ab67741`.\n- T114 approved on 2026-08-24; Phase 8 tests-first work authorized.

---

## 9. Phase 8 — Port, Participant, and Architecture Verification

**Goal:** Prove that the production adapter integrates without leaking infrastructure into core layers.

### 9.1 Tests first

- [X] T115 [TEST] Add a production-adapter structural contract test against unchanged `LLMPort` in `tests/contract/test_production_llm_adapter_contract.py`.
- [ ] T116 [P] [TEST] Add one deterministic adapter-to-participant success test for each of the five existing participants.
- [ ] T117 [P] [TEST] Add deterministic tests proving adapter-valid but semantically invalid JSON is rejected by each existing participant's output boundary.
- [ ] T118 [P] [TEST] Add orchestrator tests using different MockTransport-backed profiles for local/remote mixed success and a selected-provider failure.
- [ ] T119 [P] [TEST] Extend architecture tests proving domain, application, and participants do not import HTTPX or infrastructure.
- [ ] T120 [P] [TEST] Extend architecture tests proving only infrastructure owns endpoint/auth/envelope behavior and production code never imports `tests/`.
- [ ] T121 [P] [TEST] Add scoped production checks over `src/`, runtime dependencies, and new executable modules for provider SDKs, retry/fallback/router/registry, native provider adapters, persistence, RAG, external-action tools, and UI additions; exclude canonical documentation and legitimate test vocabulary.
- [ ] T122 [TEST] Run Phase 8 tests and confirm any red state reflects missing verification support only.

### 9.2 Minimal completion

- [ ] T123 Add only the smallest exports/type annotations required for the approved contract and architecture tests.
- [ ] T124 Correct any infrastructure-to-core leakage without changing existing domain/application/participant semantics.
- [ ] T125 Run focused Phase 8 tests to green.
- [ ] T126 Run full pytest, Ruff, mypy strict, and `pip check`.
- [ ] T127 [GATE] Review unchanged core boundaries, mixed orchestration behavior, failure mapping, dependency direction, and regressions; stop before smoke/documentation.

---

## 10. Phase 9 — Opt-In Live Smoke Path and Operator Documentation

**Goal:** Make real local/remote profile verification explicit, safe, and impossible to trigger in default CI.

### 10.1 Tests/documentation first

- [ ] T128 [TEST] Add failing tests for registered `live_llm` marker and dual authorization: skip before configuration/network unless both explicit `--run-live-llm` and exact `ARB_RUN_LIVE_LLM=1` are present; also skip safely when the opt-in is enabled but `ARB_LLM_CONFIG_PATH` is absent.
- [ ] T129 [P] [TEST] Add failing smoke-runner tests proving only selected profiles are checked once each with one documented canonical synthetic role/payload contract and no complete Review.
- [ ] T130 [P] [TEST] Add failing tests for safe profile-name diagnostics, no credential/endpoint/body leakage, runtime closure after success or failure, selected-profile missing/invalid credential failure, and irrelevance of unselected-profile credentials.
- [ ] T131 [P] [TEST] Add failing checks proving smoke verification does not run a complete Review or assert latency/model quality.
- [ ] T132 [DOC] Draft `config/llm.example.json` with local and remote placeholders, exact assignments, and credential-variable names only.
- [ ] T133 [DOC] Draft README sections for one-model, mixed local/remote, environment credentials, proxy/certificate variables, default tests, and explicit smoke command.
- [ ] T134 [TEST] Add a test loading `config/llm.example.json` through the real parser with a synthetic environment mapping, asserting valid mixed composition and absence of credential values; then run Phase 9 non-live tests and confirm the intended red state without any real request.

### 10.2 Minimal implementation

- [ ] T135 Register the `live_llm` marker and `--run-live-llm` through `pytest_addoption`; require both the explicit option and exact `ARB_RUN_LIVE_LLM=1`, without treating marker expressions or global `addopts` as authorization.
- [ ] T136 Implement the dual-authorized per-selected-profile smoke test/runner using the documented canonical synthetic role/payload, failing on invalid selected-profile configuration once explicitly enabled.
- [ ] T137 Ensure smoke execution closes the runtime on every path and reports only safe profile identities.
- [ ] T138 Finalize the non-secret example configuration and README commands.
- [ ] T139 Run default pytest and prove live tests perform no configuration loading or network access and report skipped.
- [ ] T140 Run live smoke only with `ARB_RUN_LIVE_LLM=1 pytest -m live_llm --run-live-llm` and explicit suitable configuration; absence of the opt-in or config path may skip, but invalid selected-profile credentials after activation must fail.
- [ ] T141 Run Ruff, mypy strict, and `pip check`.
- [ ] T142 [GATE] Review opt-in behavior, example hygiene, operator instructions, diagnostic safety, and regressions; stop before final closure.

---

## 11. Phase 10 — Final Quality, CI, and Architectural Review

**Goal:** Close Slice 7 with deterministic evidence and no prohibited expansion.

- [ ] T143 Run the complete default pytest suite on the supported local Python version with no credentials or live endpoints.
- [ ] T144 Run `ruff check .`.
- [ ] T145 Run strict `mypy`.
- [ ] T146 Run `pip check`.
- [ ] T147 Verify GitHub Actions passes on all configured Python versions without secrets.
- [ ] T148 Review dependency diff and confirm HTTPX is the only new justified runtime dependency.
- [ ] T149 Search changed production code, runtime dependencies, and executable modules—not canonical docs—for credentials, secret values, full prompt/response logging, raw provider-error interpolation, retries, sleeps, fallback, routing, provider SDKs, and test imports.
- [ ] T150 Verify every adapter error message exactly matches the approved safe table.
- [ ] T151 Verify all declared profiles validate structurally while only selected profiles resolve secrets, instantiate adapters, and smoke-test; verify the committed example through the real loader.
- [ ] T152 Verify one-model and mixed-model deterministic end-to-end paths preserve existing participant validation and Review failure semantics.
- [ ] T153 Verify runtime construction/close/use-after-close behavior and absence of retained Review data.
- [ ] T154 Verify no modification to `LLMPort`, participant signatures, domain outputs, lifecycle shapes, or orchestrator execution order.
- [ ] T155 Update completed task checkboxes and reconcile implementation against spec, plan, data model, ADR-0002, and actual changed files.
- [ ] T156 [GATE] Perform final architectural review and stop for explicit approval before PR readiness or merge.

---

## 12. Block Review Evidence

At every `[GATE]`, record:

1. tasks completed in the block;
2. initial red-test evidence;
3. focused green-test result;
4. full regression result;
5. Ruff result;
6. mypy result;
7. `pip check` result after dependency introduction;
8. files changed;
9. architecture/scope observations;
10. unresolved decisions or blockers.

A block is not complete merely because tests pass. It must remain consistent with all approved artifacts and introduce no prohibited architecture.

---

## 13. Dependency Order

```text
Phase 1  ADR and baseline
    ↓
Phase 2  errors + raw configuration
    ↓
Phase 3  selected profiles + secrets
    ↓
Phase 4  role prompts + generated schemas
    ↓
Phase 5  request construction
    ↓
Phase 6  response/failure processing
    ↓
Phase 7  runtime composition/lifecycle
    ↓
Phase 8  port/participant/architecture verification
    ↓
Phase 9  opt-in smoke + documentation
    ↓
Phase 10 final gates
```

No phase may bypass an earlier review gate.

---

## 14. Completion Criteria

Slice 7 implementation is complete only when:

- T001–T156 are checked;
- ADR-0002 is present and consistent;
- deterministic tests cover every approved configuration, request, response, error, composition, and lifecycle invariant;
- default CI requires no secrets or live model;
- local, remote, and mixed assignments are representable and deterministically verified;
- optional live smoke checks only selected profiles;
- all tests, Ruff, mypy strict, `pip check`, and CI pass;
- final architecture review finds no blocking issue;
- the user explicitly approves PR readiness/merge.

No implementation starts until this task list is reviewed, corrected where necessary, and explicitly approved.
