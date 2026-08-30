# Slice 7.1 Live Evaluation — Local vLLM

**Date:** 2026-08-30  
**Status:** Five-run evidence target completed; no end-to-end Critic execution
**Scenario:** `examples/reviews/critical-desktop-migration.en.json`  
**Configuration:** `config/llm.vllm.json`  
**Automatic retries:** None

## Campaign 1 Environment (Qwen3 8B)

| Property | Recorded value |
|---|---|
| Model | `Qwen/Qwen3-8B-AWQ` |
| vLLM image | `vllm/vllm-openai:v0.8.5` |
| Served model name | `qwen3-8b-awq` |
| GPU | NVIDIA GeForce RTX 3060, 12,288 MiB, driver 576.52 |
| Context length | 16,384 tokens |
| Temperature / seed | `0 / 0` |
| Structured output mode | `JSON_SCHEMA` |

## Campaign 1 Compatibility Smoke

| Check | Result | Elapsed | Safe failure, if any |
|---|---|---:|---|
| Static selected-profile smoke | Passed | Combined smoke ≈38 s | — |
| Slice 7.1 dynamic Critic schema | Passed | Combined smoke ≈38 s | — |

## Campaign 1 Incomplete Attempt

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

The adapter was not changed to truncate the catalog, remove the required untrusted schema
section, downgrade the output mode, or reduce validation. A new campaign was therefore run
with a smaller model and sufficient FP16 KV context.

## Campaign 2 Environment (Qwen3 4B)

| Property | Recorded value |
|---|---|
| Model | `Qwen/Qwen3-4B-AWQ` |
| vLLM image | `vllm/vllm-openai:v0.8.5` |
| Served model name | `qwen3-4b-awq` |
| GPU | NVIDIA GeForce RTX 3060, 12,288 MiB, driver 576.52 |
| Context length | 40,960 tokens |
| KV cache | `auto` / FP16; 44,864-token capacity |
| Temperature / seed | `0 / 0` |
| Structured output mode | `JSON_SCHEMA` |
| Automatic retries | None |

Both the static selected-profile smoke and the real minimal dynamic Critic smoke passed in
28.53 seconds combined. vLLM accepted the real Slice 7.1 `oneOf`/`const` schema.

## Campaign 2 Five Fixed-Scenario Runs

| Run | Review | Analyst | Architect | Risk | Critic | Coordinator | Safe failure family | Elapsed | Prevented pattern recurred | Ignored artifacts |
|---:|---|---|---|---|---|---|---|---:|---|---|
| 01 | INCOMPLETE | COMPLETED | COMPLETED | FAILED | PENDING | PENDING | OUTPUT_VALIDATION | 71.96 s | Not evaluable: Critic not invoked | `artifacts/slice-7.1-qwen3-4b-run-01*` |
| 02 | INCOMPLETE | COMPLETED | COMPLETED | FAILED | PENDING | PENDING | OUTPUT_VALIDATION | 69.38 s | Not evaluable: Critic not invoked | `artifacts/slice-7.1-qwen3-4b-run-02*` |
| 03 | INCOMPLETE | COMPLETED | COMPLETED | FAILED | PENDING | PENDING | OUTPUT_VALIDATION | 68.50 s | Not evaluable: Critic not invoked | `artifacts/slice-7.1-qwen3-4b-run-03*` |
| 04 | INCOMPLETE | COMPLETED | COMPLETED | FAILED | PENDING | PENDING | OUTPUT_VALIDATION | 69.80 s | Not evaluable: Critic not invoked | `artifacts/slice-7.1-qwen3-4b-run-04*` |
| 05 | INCOMPLETE | COMPLETED | COMPLETED | FAILED | PENDING | PENDING | OUTPUT_VALIDATION | 69.83 s | Not evaluable: Critic not invoked | `artifacts/slice-7.1-qwen3-4b-run-05*` |

## Campaign 2 Interpretation

All five runs were independently invoked once with unique paths. No run was retried,
replaced, overwritten, or selectively deleted. Every aggregate failed closed at Risk
Reviewer with the safe public message `Risk Reviewer output validation failed`; Critic and
Coordinator remained PENDING. Runs 02–05 produced byte-identical raw Risk Reviewer outputs,
while run 01 differed, so the outcome recurred despite two observed raw-output variants.
Diagnostic inspection found the same contract class in both variants: Risk Reviewer labeled
constraint-backed Problem Analysis references as assumptions and paired them with IDs/text
that did not form an exact trusted upstream reference. This is a Risk Reviewer semantic
failure outside the Critic-only scope of Slice 7.1.

T058 is complete as an evidence-execution task, but Slice 7.1 is not declared live-successful:
the 4B profile solves the context/VRAM problem yet does not reliably satisfy the Risk
Assessment contract, and consequently provides no full-scenario Critic output with which to
measure recurrence of the prevented source/kind/paraphrase patterns.
