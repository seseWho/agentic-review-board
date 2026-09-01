# Slice 7.2 Live Evaluation

## Fixed configuration

- Date: 2026-09-01 (Europe/Madrid)
- Scenario: `examples/reviews/critical-desktop-migration.en.json`
- Configuration: `config/llm.vllm.json`
- Profile: `local-qwen3`
- Model: `qwen3-4b-awq` (`Qwen/Qwen3-4B-AWQ` in Compose)
- vLLM image: `vllm/vllm-openai:v0.8.5`
- Structured-output mode: `JSON_SCHEMA`
- Temperature / seed: `0 / 0`
- Maximum output tokens: `4096`
- Configured model context: `40960`
- GPU: NVIDIA GeForce RTX 3060, 12 GiB
- Driver / reported CUDA: `576.52 / 12.9`

This is a fixed compatibility and five-run evidence campaign. It is not a reliability
benchmark. A run is never retried, replaced, overwritten, or selectively deleted.

## Preconditions

Docker Desktop and `arb-vllm` must be running and healthy. Before every run, both the
aggregate output and raw-output directory listed below must be absent. Existing Slice
7.1 and earlier diagnostic artifacts are preserved and are not campaign inputs.

```powershell
$paths = 1..5 | ForEach-Object {
  $number = $_.ToString("00")
  @(
    "artifacts/slice-7.2-qwen3-4b-run-$number.json",
    "artifacts/slice-7.2-qwen3-4b-run-$number.raw"
  )
}
$paths | ForEach-Object { if (Test-Path -LiteralPath $_) { throw "Path exists: $_" } }
```

The campaign stops if the server rejects any required JSON Schema feature, including
array-valued `const`, `minItems`, or exact `oneOf` branches. It does not switch mode,
model, profile, or schema strength.

For this execution, the checked-in `arb-vllm` service remained untouched because its
Hugging Face metadata lookup was blocked by local certificate verification. The same
image, model, port, GPU, mount, and launch arguments were started as temporary
`arb-vllm-slice72` with `HF_HUB_OFFLINE=1`; this changes no checked-in profile or schema.

## Opt-in smoke command

```powershell
$env:ARB_RUN_LIVE_LLM = "1"
$env:ARB_LLM_CONFIG_PATH = (Resolve-Path "config/llm.vllm.json").Path
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe -m pytest `
  tests\live\test_llm_smoke.py `
  -m live_llm `
  --run-live-llm `
  -s
```

This executes the selected-profile static smoke, Slice 7.1 dynamic Critic smoke, and
Slice 7.2 dynamic Risk Reviewer smoke exactly once each.

## Fixed review commands

For run `NN` from `01` through `05`, after confirming both paths are absent:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_review.py `
  --config config\llm.vllm.json `
  --input examples\reviews\critical-desktop-migration.en.json `
  --output artifacts\slice-7.2-qwen3-4b-run-NN.json `
  --raw-output-dir artifacts\slice-7.2-qwen3-4b-run-NN.raw
```

Each command is initiated independently. A nonzero exit is preserved as that run's
result and does not authorize a retry.

## Results

| Run | Review | Analyst | Solution Architect | Risk Reviewer | Critic | Coordinator | Safe failure family | Seconds | Observed basis mismatch recurred? | Critic/Coordinator completed? | Preserved ignored artifacts |
|---|---|---|---|---|---|---|---|---:|---|---|---|
| 01 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | — | PENDING | PENDING | `artifacts/slice-7.2-qwen3-4b-run-01.json`, `.raw/` |
| 02 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | — | PENDING | PENDING | `artifacts/slice-7.2-qwen3-4b-run-02.json`, `.raw/` |
| 03 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | — | PENDING | PENDING | `artifacts/slice-7.2-qwen3-4b-run-03.json`, `.raw/` |
| 04 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | — | PENDING | PENDING | `artifacts/slice-7.2-qwen3-4b-run-04.json`, `.raw/` |
| 05 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | — | PENDING | PENDING | `artifacts/slice-7.2-qwen3-4b-run-05.json`, `.raw/` |

## Interpretation rules

- `COMPLETED` means the unchanged participant accepted the provider mapping; adapter
  parsing or schema acceptance alone is not trusted completion.
- A safe failure is classified by the stored stage error family and concise message,
  never by copying payloads, schemas, raw responses, credentials, or nested validation
  text into this document.
- The historical constraint-as-assumption mismatch is recorded only as recurred or not
  recurred after comparing identities; its full raw content remains in ignored artifacts.
- A different participant-validation, transport, timeout, context, or provider-schema
  failure is classified separately from the prevented basis/scope patterns.
- Completion of five preserved rows demonstrates only the stated evidence target, not
  end-to-end reliability or statistical quality.

Execution record: run 01 was preserved once with Review `INCOMPLETE` (Analyst and
Solution Architect `COMPLETED`; Risk Reviewer `FAILED`; Critic and Coordinator
`PENDING`) after 45.64 seconds. Its safe failure family was provider-schema:
vLLM logged that exact `oneOf` constraints are unsupported by guided decoding. The
five-run evidence target was not completed; runs 02–05 were intentionally not
initiated and their paths remain absent. The row above is therefore retained as the
predeclared template, with this execution record authoritative for the observed run.

## vLLM 0.11.0 compatibility diagnostic

After the fixed v0.8.5 campaign stopped, a separate, non-campaign diagnostic was
run with `vllm/vllm-openai:v0.11.0` on the same RTX 3060, model, context, and
application profile. The image loaded successfully with AWQ Marlin and exposed a
54,576-token GPU KV cache.

The dynamic Critic and Risk Reviewer smoke requests both completed. The static
selected-profile smoke reached inference but its model content failed application
validation; vLLM did not reject its schema. A separate full review completed Analyst,
Solution Architect, Risk Reviewer, and Critic. Coordinator failed closed with
`OUTPUT_VALIDATION`, leaving the review `INCOMPLETE` after 182.52 seconds.

The preserved diagnostic artifact is
`artifacts/slice-7.2-v011-diagnostic-01.json` with its `.raw/` directory. It is not
run 02 of the fixed campaign and does not alter the five-run evidence record. This
diagnostic establishes v0.11.0 as the supported candidate for the RTX 3060 and the
current dynamic schemas; it does not establish five-participant semantic reliability.

## Dynamic Coordinator follow-up

A second full diagnostic with prompt-only Coordinator guidance again completed the
first four participants but failed Coordinator validation. The preserved raw output
showed two independent contextual errors across attempts: disposition ids copied from
non-criticism Critic collections, and paraphrased Problem Analysis id-and-text pairs.
This demonstrated that instructions alone could not reliably enforce the existing
Coordinator resolver contract.

Coordinator now receives a detached, typed five-artifact payload snapshot and a
request-local JSON Schema. The schema enumerates only exact resolvable unresolved-item
references and only ids from `critical_review.criticisms`. It also encodes the
`REFLECTED`/non-empty `reflected_in` and `DISMISSED`/empty `reflected_in` shapes. The
provider schema intentionally omits `uniqueItems`, which vLLM 0.11.0 xgrammar rejected;
the unchanged trusted domain model still rejects duplicate sections after generation.

An isolated Coordinator probe against the four already validated upstream artifacts
completed with `RECOMMENDED`, preferred `ALT-001`, one exact criticism disposition,
and one exact unresolved question. The subsequent independent full diagnostic reached
Review `COMPLETED` with Analyst, Solution Architect, Risk Reviewer, Critic, and
Coordinator all `COMPLETED` after 201.12 seconds. Evidence is preserved in ignored
artifacts:

- `artifacts/slice-7.2-v011-coordinator-probe-03.json`
- `artifacts/slice-7.2-v011-diagnostic-03.json`
- `artifacts/slice-7.2-v011-diagnostic-03.raw/`

These are compatibility diagnostics, not replacement rows in the stopped fixed
v0.8.5 five-run campaign and not a statistical reliability claim.

## vLLM 0.11.0 five-run repeatability campaign

This is a new fixed campaign using the checked-in vLLM 0.11.0 configuration and
dynamic Critic, Risk Reviewer, and Coordinator schemas. All five aggregate and raw
artifact paths were confirmed absent before execution. Each run is initiated once;
failures are preserved and are not retried, replaced, or selectively deleted.

| Run | Review | Analyst | Solution Architect | Risk Reviewer | Critic | Coordinator | Seconds | Preserved ignored artifacts |
|---|---|---|---|---|---|---|---:|---|
| 01 | INCOMPLETE | COMPLETED | COMPLETED | COMPLETED | FAILED | PENDING | 192.83 | `artifacts/slice-7.2-v011-run-01.json`, `.raw/` |
| 02 | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 162.65 | `artifacts/slice-7.2-v011-run-02.json`, `.raw/` |
| 03 | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 148.83 | `artifacts/slice-7.2-v011-run-03.json`, `.raw/` |
| 04 | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 205.94 | `artifacts/slice-7.2-v011-run-04.json`, `.raw/` |
| 05 | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 209.55 | `artifacts/slice-7.2-v011-run-05.json`, `.raw/` |

The fixed campaign completed all five initiated executions without retry. Four reviews
completed all five participants, for an observed end-to-end completion rate of 4/5
(80%). Mean elapsed time was 183.96 seconds across all runs and 181.74 seconds across
completed reviews.

Run 01 failed closed at Critic structural validation. Its criticism repeated the exact
`target_reference` object inside `basis_references`, which the authoritative
`CriticalReview` contract forbids. Analyst, Solution Architect, and Risk Reviewer had
already completed; Coordinator correctly remained pending. Runs 02–05 completed
Coordinator with its dynamic schema. No run failed because of provider schema support,
transport, timeout, context length, GPU memory, or Coordinator reference resolution.
This five-run result is compatibility and repeatability evidence for the fixed scenario,
not a general reliability guarantee for Qwen3-4B-AWQ.

After the campaign, the Critic instruction was made explicit that a criticism's
`target_reference` must not be repeated in `basis_references`. An isolated probe using
the exact run-01 upstream artifacts still produced the same forbidden duplicate and
failed closed. The probe is preserved as
`artifacts/slice-7.2-v011-critic-probe-01.json`; it does not replace run 01 or change
the 4/5 result. Prompt-only guidance is therefore not considered a reliable remedy for
this cross-field constraint. No automatic repair, retry, schema weakening, or fallback
mode was introduced.
