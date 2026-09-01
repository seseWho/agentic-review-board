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
