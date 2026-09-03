# Slice 8 Deterministic Acceptance

**Date:** 2026-09-03

**Scope:** Pedagogical Streamlit UI over the existing five-participant Review workflow

**Environment:** Offline deterministic `LLMPort` substitutes; no endpoint, credential, or
network access

**Result:** PASS

## Verification baseline

- Full deterministic suite: `1267 passed, 3 skipped` including the delayed acceptance cases.
- Focused Slice 8 checkpoint: `54 passed`.
- Delayed deterministic walkthroughs: `2 passed`.
- Architecture suite: `14 passed`.
- Ruff: pass.
- `pip check`: pass.
- Slice 8 focused strict mypy: pass over 14 created or modified source/test files.
- Repository-wide mypy retains 76 pre-existing errors, all confined to
  `tests/unit/infrastructure/llm/test_dynamic_risk_schemas.py`; none is in Slice 8.

The delayed walkthrough injects a test-only five-millisecond pause after each observer
snapshot. It exercises the same observer-driven Streamlit containers used by production.
AppTest verifies state and rendered content; it does not claim to measure physical browser
paint timing.

## Complete five-agent walkthrough

**Input:** `Delayed COMPLETE walkthrough.` as the required description, with all optional
fields absent.

**Observed execution:** 11 immutable validated Review snapshots and five LLM-port calls in
the exact sequence Analyst, Solution Architect, Risk Reviewer, Critic, Coordinator. Every
stage-completion snapshot preceded the following stage-start snapshot; no snapshot had more
than one running stage.

| Agent | Received | Trusted result | Why execution continued |
|---|---|---|---|
| Analyst | Exact current `ReviewInput` | `ProblemAnalysis`, including `ASM-001` and `UNC-001` | Output passed intrinsic and current-input validation. |
| Solution Architect | Exact `ReviewInput` and Analyst output instance | Two `PROPOSED` alternatives, `ALT-001` and `ALT-002` | Output passed alternative and provenance validation. |
| Risk Reviewer | Exact input, analysis, and alternatives instances | `RiskAssessment` with `RISK-001`, mitigation, and residual uncertainty | Risk basis resolved to the current `ALT-001` disadvantage. |
| Critic | Exact input plus all three upstream output instances | `CriticalReview` with `CRIT-001` and `CONTRA-001` marked `UNVERIFIED` | References resolved to current Analyst findings; no evidence state was promoted. |
| Coordinator | Exact input plus all four upstream output instances | `FinalReview` with two ranked `PROPOSED` alternatives and `ALT-001` as the conditional preference | Ranking, risk, unresolved-question, and criticism-disposition references resolved exactly. |

**Terminal state:** Review `COMPLETED`; all five stages `COMPLETED`; a separate Final result
was rendered. The result retained qualitative `MEDIUM` confidence, `QUESTION-001`, the
Critic disposition `REFLECTED`, the next validation step, and the fixed human
decision-support notice. It exposed no autonomous action.

**Remaining uncertainty/evidence:** both alternatives remain `PROPOSED`; the contradiction
remains `UNVERIFIED`; operational effort remains explicitly unmeasured. Completion means
the five trusted artifacts were produced, not that the proposal was externally proven.

## Critic output-validation failure walkthrough

**Input:** `Delayed CRITIC_OUTPUT_VALIDATION_FAILURE walkthrough.` as the required
description, with all optional fields absent.

**Observed execution:** nine immutable validated Review snapshots and four LLM-port calls.
Analyst, Solution Architect, and Risk Reviewer received the same exact upstream artifact
chain as in the complete walkthrough and produced trusted completed outputs. Critic received
those exact three outputs but returned a reference to nonexistent `ALT-999`.

**Why execution stopped:** the real Critic rejected that mapping at its contextual trust
boundary. The orchestrator recorded the trusted category `OUTPUT_VALIDATION` and the fixed
message `Critic output validation failed`. It did not trust or expose the rejected partial
mapping. Coordinator was never called because Critic is a mandatory predecessor.

**Terminal state:** Review `INCOMPLETE`; Analyst, Solution Architect, and Risk Reviewer
`COMPLETED`; Critic `FAILED`; Coordinator `PENDING` and visibly derived as blocked by
Critic. The three upstream outputs remained inspectable and no Final result was rendered.

**Remaining uncertainty/evidence:** prior alternatives remain `PROPOSED`; risk evidence and
residual uncertainty remain inspectable. No Critic output, Coordinator synthesis, preference,
or fabricated replacement result exists.

## Security and isolation observations

- Startup and post-snapshot application faults use fixed UI messages and fabricate no
  failed domain stage.
- Execution failure is distinguishable from output-validation failure without exposing the
  injected provider secret marker.
- Rendered-content denylist checks cover private-reasoning labels, prompts, raw output/body,
  authorization material, credentials, and autonomous recommendation controls.
- New Review was verified after both complete and incomplete outcomes; it clears all six
  widget values, trusted Review/output/error state, selected detail, and the execution guard
  before a different input runs.
- No persistence, history, resume, retry, polling, thread, queue, workflow engine, API
  service, raw HTML, or provider SDK was introduced in the UI boundary.

## Live vLLM acceptance

Not executed. Task T062 remains intentionally pending until the operator explicitly
authorizes a live model run after reviewing this deterministic acceptance baseline.
