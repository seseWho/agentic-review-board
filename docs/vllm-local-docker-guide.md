# Run Agentic Review Board Locally with vLLM and Docker

This guide starts a reproducible vLLM server for live tests and a complete review. Everything
required by the service is declared in the repository's `compose.yaml`. The model is stored in
a persistent Docker volume and does not depend on directories from another project. To validate
the UI as well, follow the [`local UI test runbook`](local-ui-test-runbook.md).

## Included Configuration

The reference configuration is tuned for an NVIDIA RTX 3060 with 12 GiB:

- image: `vllm/vllm-openai:v0.11.0`;
- model: `Qwen/Qwen3-4B-AWQ`;
- served name: `qwen3-4b-awq`;
- context: 40,960 tokens;
- quantization: AWQ Marlin;
- local port: `127.0.0.1:8000`;
- cache: Docker volume `agentic-review-board-huggingface-cache` by default, or
  the directory specified through `HF_HOME`;
- application configuration: `config/llm.vllm.json`.

The port is published only on `127.0.0.1`; the server is not exposed to the local
network. The configuration contains no credentials. The first run downloads the
model and image, so it requires an Internet connection and enough Docker storage.

### Where the Model Is Stored

Without any configuration, Compose uses the Docker-managed volume
`agentic-review-board-huggingface-cache`. Its files live inside Docker Desktop's
data disk and do not appear as a normal repository folder. You can inspect its
logical location with:

```powershell
docker volume inspect agentic-review-board-huggingface-cache
```

To reuse an existing host cache, set `HF_HOME` before starting. On the reference
machine:

```powershell
$env:HF_HOME = "D:\_models\huggingface"
docker compose up -d vllm
```

Compose then mounts `D:\_models\huggingface` at `/root/.cache/huggingface`.
Qwen3-4B-AWQ is reused if it is already present, and new models are downloaded
to the same path. `HF_HOME` affects only the current command and processes
launched from that PowerShell session.

To persist the setting between sessions without versioning a machine-specific
path, create a `.env` file in the repository root:

```dotenv
HF_HOME=D:/_models/huggingface
```

`.env` is ignored by Git. On another machine, omit it to use the Docker volume or
create another `.env` with the appropriate local path.

## 1. Requirements

You need:

1. Python 3.12 or later.
2. Docker Desktop with the WSL 2 backend on Windows, or Docker Engine on Linux.
3. Modern Docker Compose (`docker compose`).
4. A compatible NVIDIA GPU and the NVIDIA container runtime.
5. At least 12 GiB of VRAM for the reference configuration.

Check the versions and GPU access:

```powershell
python --version
docker version
docker compose version
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu22.04 nvidia-smi
```

In Docker Desktop, review **Settings > Resources > Advanced > Disk image location**
before downloading the image. The vLLM image and model may occupy several dozen
GB. Do not run `docker system prune` without first checking which resources belong
to other projects.

## 2. Set Up the Python Project

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

First verify the deterministic suite, which does not use the network or models:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 3. Avoid Conflicts with Other Servers

Only one process can publish port 8000. Check whether another container is using
it:

```powershell
docker ps --filter publish=8000
```

If one appears, stop it from its own project or change this Compose port. For
example, to publish on port 8001:

```powershell
$env:VLLM_PORT = "8001"
docker compose up -d vllm
```

In that case, copy `config/llm.vllm.json` to a `*.local.json` file ignored by Git
and change `base_url` to `http://localhost:8001/v1`.

Do not rename a container created by another repository's Compose: its Compose file
may recreate it with the original name. This project uses its own `arb-vllm` service
and its own cache volume.

## 4. Download and Start vLLM

```powershell
docker compose pull vllm
docker compose up -d vllm
docker compose ps
docker compose logs -f vllm
```

The first load may take a while because it downloads the model, converts the AWQ
Marlin kernels, and allocates the KV cache. Stop following the logs with `Ctrl+C`;
the container will continue running.

When `docker compose ps` shows the service as `healthy`, query the catalog:

```powershell
Invoke-RestMethod http://localhost:8000/v1/models |
  ConvertTo-Json -Depth 6
```

The response must contain `qwen3-4b-awq` and `max_model_len: 40960`.

You can also inspect resource usage:

```powershell
docker stats arb-vllm --no-stream
nvidia-smi
```

## 5. Test the JSON Contract Directly

```powershell
$requestBody = @{
  model = "qwen3-4b-awq"
  messages = @(
    @{
      role = "user"
      content = "Return exclusively a JSON object with the status property and the value ok."
    }
  )
  response_format = @{ type = "json_object" }
} | ConvertTo-Json -Depth 6

$response = Invoke-RestMethod `
  -Uri http://localhost:8000/v1/chat/completions `
  -Method Post `
  -ContentType "application/json" `
  -Body $requestBody

$response.choices[0].message.content
```

The expected content is an object equivalent to:

```json
{"status":"ok"}
```

## 6. Run the Application Live Smoke Test

The live test requires explicit authorization through an environment variable, option, and marker:

```powershell
$env:ARB_RUN_LIVE_LLM = "1"
$env:ARB_LLM_CONFIG_PATH = (Resolve-Path "config\llm.vllm.json").Path
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe -m pytest `
  -m live_llm `
  --run-live-llm `
  -s
```

The smoke test contains three checks:

1. a synthetic request using Analyst's static contract for each selected profile;
2. a minimal Critic request built through the real Slice 7.1 path, with its catalog,
  `oneOf`, `const` values, delimited dynamic section, and dynamic `response_format`;
3. a minimal Risk Reviewer request built through the real Slice 7.2 path, with
  `oneOf`, `const`, `minItems`, `maxItems`, and the exact dynamic scope.

The two dynamic tests demonstrate that the server accepts the JSON Schema subset
used by Slice 7.1 and Slice 7.2 and returns direct JSON objects. They do not
demonstrate semantic quality or replace participant validation.

Compatibility result validated with vLLM 0.11.0 on the reference RTX 3060:

```text
live LLM profile: local-qwen3
live dynamic Critic profile: local-qwen3
live dynamic Risk Reviewer profile: local-qwen3
1 failed, 2 passed
```

Both dynamic contracts were accepted and completed. The static check failed because
model content did not pass application validation, not because vLLM rejected the
JSON Schema. Therefore, this result validates provider compatibility with dynamic
schemas, but not the semantic reliability of Qwen3-4B-AWQ.

If a dynamic test fails because vLLM rejects `oneOf`, `const`, `minItems`, or
`maxItems`, preserve the error as evidence and stop the evaluation. Do not switch
to `JSON_OBJECT`, weaken the schema, or retry until it succeeds.

The minimal smoke test may pass even when a large scenario exceeds the context. In
that case, the vLLM logs show the requested tokens and configured limit. Do not
truncate the catalog or remove the delimited schema: stop the campaign and later
use a profile/model with an explicitly sufficient context.

## 7. Run a Complete Review

Start with the English scenario, which makes it easier to compare results with the
reference tests:

```powershell
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe scripts\run_live_review.py `
  --config config\llm.vllm.json `
  --input examples\reviews\critical-desktop-migration.en.json `
  --output artifacts\critical-desktop-migration.en.local.json
```

To preserve every unvalidated response and diagnose a contract failure:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_review.py `
  --config config\llm.vllm.json `
  --input examples\reviews\critical-desktop-migration.en.json `
  --output artifacts\critical-desktop-migration.en.diagnostic.json `
  --raw-output-dir artifacts\critical-desktop-migration.en.raw
```

`artifacts/` is ignored by Git. Raw outputs may include sensitive data from the
reviewed case; use them only for diagnosis.

The runner always attempts to save the confidence aggregate. It returns code 0 if
the review is `COMPLETED` and code 1 if it is `INCOMPLETE`. Code 1 may mean that
vLLM responded correctly but the model violated a semantic contract.

## 8. Reference Result and Pre-UI Criteria

Validation on August 29, 2026, with an RTX 3060 and 12 GiB:

- deterministic suite: 1,038 passed tests and 1 skipped;
- vLLM smoke test: passed;
- Analyst: completed;
- Solution Architect: completed;
- Risk Reviewer: completed;
- Critic: rejected by output validation;
- Coordinator: pending by fail-closed design;
- end-to-end duration: 212.26 seconds.

Critic produced structurally valid JSON but mixed references, for example
`PROBLEM_ANALYSIS / ALTERNATIVE_ASSUMPTION / ALT-001`, where that reference belongs
to `SOLUTION_ALTERNATIVES`. Qwen3-8B-AWQ is useful for validating integration and
error states, but it has not demonstrated enough semantic reliability to always
complete all five participants.

Before building the UI, verify these behaviors:

1. The live smoke test is stable.
2. A complete or incomplete review is persisted correctly.
3. The `COMPLETED`, `FAILED`, and `PENDING` states are clearly distinguished.
4. Contract failures do not silently activate dependent stages.
5. Decide whether the product needs dynamic schemas, bounded retries, or a more
  capable model for the most demanding roles.

### Slice 7.1 Evaluation

Slice 7.1 requires exactly five independent invocations of the same scenario,
without automatic retry, substitution, or selective deletion. Use separate paths:

```powershell
1..5 | ForEach-Object {
  $run = $_.ToString("00")
  .\.venv\Scripts\python.exe scripts\run_live_review.py `
    --config config\llm.vllm.json `
    --input examples\reviews\critical-desktop-migration.en.json `
    --output "artifacts\slice-7.1-run-$run.json" `
    --raw-output-dir "artifacts\slice-7.1-run-$run.raw"
}
```

PowerShell continues the loop even if a run returns code 1. Do not rerun only the
failed numbers. Record all five results, configuration, image, GPU, and timings in
`specs/007.1-dynamic-critic-schema/live-evaluation.md`. Los archivos bajo
`artifacts/` permanecen ignorados y pueden contener información sensible.

With the current reference scenario, the observed dynamic Critic request needs
34,227 tokens (30,131 message tokens and 4,096 output tokens). That is why Compose
uses 40,960; the historical 16,384 profile was suitable only for the minimal smoke
test, not this complete review.

## 9. Daily Operation

Start and wait until it is ready:

```powershell
docker compose up -d vllm
docker compose ps
```

View logs:

```powershell
docker compose logs -f vllm
```

Stop while preserving the model and image:

```powershell
docker compose down
```

Update only the configured image:

```powershell
docker compose pull vllm
docker compose up -d vllm
```

## 10. Reclaim Storage

`docker compose down` does not delete the model. To view the volume:

```powershell
docker volume inspect agentic-review-board-huggingface-cache
```

To also delete the model cache, request it explicitly:

```powershell
docker compose down --volumes
```

The latter command forces the model to be downloaded again on the next startup.
Do not use it if you want to preserve the cache.

## Settings for Other GPUs

The values can be changed temporarily without editing `compose.yaml`:

```powershell
$env:VLLM_MAX_MODEL_LEN = "8192"
$env:VLLM_GPU_MEMORY_UTILIZATION = "0.90"
$env:VLLM_KV_CACHE_DTYPE = "auto"
docker compose up -d vllm
```

If loading fails because of insufficient VRAM, first reduce `VLLM_MAX_MODEL_LEN` to
`12288`, and then to `8192`. Keep `max-num-seqs=1`, since the current flow is
sequential. Changing the model repository or served name requires keeping
`VLLM_MODEL`, `VLLM_SERVED_MODEL_NAME`, and the application's JSON `model` field
in sync.

Running the complete Slice 7.1 scenario requires at least 34,227 input and output
tokens. The reference configuration uses `Qwen/Qwen3-4B-AWQ`, 40,960 tokens, and
`auto` KV cache; it does not need FP8, FlashInfer, or offload on the 12 GiB RTX 3060.

The 8B model investigation is retained as diagnostic context: vLLM 0.8.5 had
only 2.96 GiB available for KV versus the 5.62 GiB required; FP8 E5M2 forced the
V0 engine and exceeded the timeout while compiling the dynamic schema; V1 offload
required UVA, which is unavailable under WSL; and vLLM 0.11.0 encountered FP8
kernel incompatibilities on Ampere. These combinations are not the project's
supported configuration.

If you change the model or GPU, always preserve enough context for the combined
prompt and output. Do not reduce the schema, truncate the catalog, or substitute
failed runs to make the evaluation pass.
