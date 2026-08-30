# Slice 7.1 Live Evaluation — Local vLLM

**Date:** 2026-08-30  
**Status:** Stopped — configured vLLM context is too small for the full dynamic Critic request  
**Scenario:** `examples/reviews/critical-desktop-migration.en.json`  
**Configuration:** `config/llm.vllm.json`  
**Automatic retries:** None

## Environment

| Property | Recorded value |
|---|---|
| Model | `Qwen/Qwen3-8B-AWQ` |
| vLLM image | `vllm/vllm-openai:v0.8.5` |
| Served model name | `qwen3-8b-awq` |
| GPU | NVIDIA GeForce RTX 3060, 12,288 MiB, driver 576.52 |
| Context length | 16,384 tokens |
| Temperature / seed | `0 / 0` |
| Structured output mode | `JSON_SCHEMA` |

## Compatibility Smoke

| Check | Result | Elapsed | Safe failure, if any |
|---|---|---:|---|
| Static selected-profile smoke | Passed | Combined smoke ≈38 s | — |
| Slice 7.1 dynamic Critic schema | Passed | Combined smoke ≈38 s | — |

## Five Fixed-Scenario Runs

| Run | Review | Analyst | Architect | Risk | Critic | Coordinator | Safe failure family | Elapsed | Prevented pattern recurred | Ignored artifacts |
|---:|---|---|---|---|---|---|---|---:|---|---|
| 01 | INCOMPLETE | COMPLETED | COMPLETED | COMPLETED | FAILED | PENDING | EXECUTION (`HTTP 400` internally) | 115.86 s | Not evaluable: no Critic output | `artifacts/slice-7.1-run-01*` |
| 02 | INCOMPLETE | COMPLETED | COMPLETED | COMPLETED | FAILED | PENDING | EXECUTION (`HTTP 400` internally) | 113.82 s | Not evaluable: no Critic output | `artifacts/slice-7.1-run-02*` |
| 03 | Not completed; campaign interrupted immediately after mandatory stop was confirmed | — | — | — | — | — | — | — | — | No artifact created |
| 04 | Not executed after mandatory stop | — | — | — | — | — | — | — | — | No artifact created |
| 05 | Not executed after mandatory stop | — | — | — | — | — | — | — | — | No artifact created |

## Interpretation

The real minimal Slice 7.1 schema is accepted by vLLM, so the selected `oneOf`/`const`
subset is compatible. In both completed full runs, Analyst, Solution Architect, and Risk
Reviewer completed. Before Critic generation, vLLM rejected the request because it required
34,227 tokens: 30,131 prompt tokens plus 4,096 completion tokens, against the configured
16,384-token context. The application mapped the HTTP failure safely to Critic EXECUTION,
left Coordinator PENDING, and preserved the INCOMPLETE aggregate.

The repeated failure is a provider/profile request-size limitation, not a participant output
validation result. No Critic raw output exists, so recurrence of the previously prevented
reference patterns cannot be evaluated. The continuous five-run campaign was stopped after
run 02 confirmed the same deterministic limit; runs were not retried, replaced, or selected.

T058 remains incomplete. Continuing requires an explicit compatible profile/model context
large enough for at least 34,227 tokens (with operational headroom), followed by a fresh
five-run campaign numbered independently. The adapter must not truncate the catalog, remove
the required untrusted schema section, downgrade the output mode, or reduce validation.
