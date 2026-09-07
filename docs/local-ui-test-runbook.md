# Local UI Test Runbook

This runbook validates the Agentic Review Board educational UI on Windows with PowerShell. It
includes a deterministic model-free run and a full run with the reference configuration for
vLLM and an NVIDIA RTX 3060 with 12 GiB.

Run all commands from the repository root. The expected path on the reference machine is:

```powershell
Set-Location "D:\DEVELOP\GitHub\SeseWho\agentic-review-board"
```

## What Each Run Validates

| Run | Real model | GPU | Purpose |
|---|---:|---:|---|
| Automated suite | No | No | Regression coverage for the domain, agents, orchestration, and UI |
| Deterministic UI | No | No | Form, states, agent details, and final result |
| Production UI | Yes | Yes | Full browser integration with the five agents and vLLM |

The deterministic UI does not replace the production test. The production test alone also does
not prove that the model will always satisfy the semantic contracts.

## 1. Prerequisites

- Python 3.12 o posterior.
- Project dependencies installed in `.venv`.
- Docker Desktop with WSL 2 for the live test.
- NVIDIA driver and Docker access to the GPU.
- Port 8501 available for Streamlit.
- Port 8000 available for vLLM.
- Enough Docker storage for the image and model.

Check the environment:

```powershell
py -3.12 --version
docker version
docker compose version
nvidia-smi
Test-Path .\.venv\Scripts\python.exe
```

If the Python environment does not exist yet:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

If `.venv` exists but its interpreter no longer starts after upgrading Python, keep the
directory for diagnosis, create a new environment, and reinstall the project. Do not delete
the old environment until the replacement has been verified.

## 2. Preflight Automated Verification

Run the tests that do not use the network, Docker, or models first:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip check
```

Pass criteria:

- no failed tests or errors;
- live tests are skipped unless explicitly authorized;
- mypy and Ruff exit with code 0;
- `pip check` finds no incompatible dependencies.

The latest accepted baseline is recorded in
[`../specs/008-pedagogical-ui/acceptance.md`](../specs/008-pedagogical-ui/acceptance.md).

## 3. Quick Model-Free UI Run

Start the deterministic composition used by the functional tests:

```powershell
.\.venv\Scripts\python.exe -m streamlit run `
  tests\ui\fixtures\deterministic_streamlit_app.py `
  --server.address localhost `
  --server.port 8501
```

Open <http://localhost:8501>. If Streamlit does not open the browser automatically, copy the
address manually.

Perform the following run:

1. Confirm that the case editor appears in the sidebar.
2. Import `examples\reviews\critical-desktop-migration.en.md` or enter a description.
3. Review the six fields; importing the file must not start any agent.
4. Confirm that Coordinator appears at the top and the specialists appear in a 2x2 grid.
5. Press **Start Review** once and verify that the editor is replaced by the collapsed summary.
6. Wait for the global **Completed** state and open the participant cards.
7. Confirm that the independent **Decision workspace** with its tabs appears.
8. Press **New Review** and verify that the form, import, states, and result are cleared.

The visible order must be Analyst, Solution Architect, Risk Reviewer, Critic, and Coordinator.
Each completed participant must have a trustworthy artifact. Stop Streamlit with `Ctrl+C`.

## 4. Start vLLM for the Live Test

The versioned configuration uses:

- `vllm/vllm-openai:v0.11.0`;
- `Qwen/Qwen3-4B-AWQ` servido como `qwen3-4b-awq`;
- AWQ Marlin and FP16 quantization;
- a 40,960-token context;
- a single concurrent sequence;
- local port `127.0.0.1:8000`.

First check that no other service is using the port:

```powershell
docker ps --filter publish=8000
```

Start the service declared by the repository:

```powershell
docker compose config
docker compose up -d vllm
docker compose ps
docker compose logs -f vllm
```

The first run may download several gigabytes and take a while. When the logs indicate that the
application is ready, stop following the logs with `Ctrl+C`; this does not stop the container.

Check its status and catalog:

```powershell
docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' arb-vllm

Invoke-RestMethod http://localhost:8000/v1/models |
  ConvertTo-Json -Depth 6
```

The container must be `healthy` and the catalog must contain `qwen3-4b-awq`. If a system proxy
exists, `localhost` and `127.0.0.1` must be excluded.

## 5. Run the Production UI

In a terminal separate from the Docker terminal:

```powershell
$env:ARB_LLM_CONFIG_PATH = (Resolve-Path ".\config\llm.vllm.json").Path
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py `
  --server.address localhost `
  --server.port 8501
```

Open <http://localhost:8501>. Loading the page does not call the model; execution starts only
when **Start Review** is pressed.

Import this reference input directly from the sidebar:

[`../examples/reviews/critical-desktop-migration.en.md`](../examples/reviews/critical-desktop-migration.en.md)

The accepted format is:

```markdown
# Optional title

## Description

Required problem statement.

## Objective

Optional objective.

## Constraints

- One flat item per line

## Context

- One flat item per line

## Stated facts

- One flat item per line
```

The Spanish headings `Descripción`, `Objetivo`, `Restricciones`, `Contexto`, and
`Hechos declarados` are also accepted. The file must use UTF-8 and must not exceed 1 MiB.
Unknown or duplicate headings and malformed lists are rejected without changing the current
draft.

Alternatively, inspect the JSON values and fill in the editor manually:

```powershell
$scenario = Get-Content `
  ".\examples\reviews\critical-desktop-migration.en.json" `
  -Raw | ConvertFrom-Json

$scenario | Format-List
$scenario.constraints
$scenario.context
$scenario.stated_facts
```

Copy `title`, `description`, and `objective` into their fields. Copy each item from
`constraints`, `context`, and `stated_facts` onto a separate line in its corresponding area.

Before starting:

- confirm that all five agents are in the **Pending** state;
- confirm that importing or editing has not run the model;
- record the start time;
- press **Start Review** once;
- do not reload or close the tab while it is running.

The reference run takes approximately two minutes, although a cold load may take longer. The
flow is sequential and does not retry, fall back, repair output, or automatically change the
model.

## 6. Manual Acceptance Criteria

A complete run passes when:

- the global state ends in **Completed**;
- all five agents end in **Completed** and in canonical order;
- each completed stage shows its trustworthy artifact;
- Coordinator produces the **Decision workspace** with the **Final result** section;
- the result preserves risks, uncertainties, and evidence status;
- the UI does not show prompts, raw responses, credentials, or internal error details.

An **Incomplete** run can also be a valid model observation. In that case, verify that:

- the stage that violates the contract ends in **Failed** and does not present trustworthy output;
- earlier stages remain inspectable;
- required later stages are shown as not executed;
- no fabricated final result appears;
- the failed run is retained without retrying only the problematic stage.

## 7. Minimum Evidence to Record

To make a run reproducible, record:

```powershell
git rev-parse HEAD
docker compose images
docker compose ps
nvidia-smi
```

Also record:

- date and time;
- scenario used;
- vLLM version, image, model, and configuration;
- GPU, VRAM, and driver version;
- approximate duration;
- final Review and per-agent states;
- presence or absence of **Final result**;
- public message shown by the UI if a failure occurs.

Do not record keys, internal prompts, or raw responses unless there is an explicit diagnostic
need. Files in `artifacts/` are ignored by Git but may contain sensitive information.

## 8. Quick Troubleshooting

### Streamlit does not start

Check the interpreter and installation:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show streamlit
.\.venv\Scripts\python.exe -m pip check
```

### Port 8501 is occupied

```powershell
Get-NetTCPConnection -LocalPort 8501 -State Listen
```

Stop the previous instance or start Streamlit on another port, such as 8502, and open the
corresponding URL.

### vLLM does not become `healthy`

```powershell
docker compose ps
docker compose logs --tail 200 vllm
docker stats arb-vllm --no-stream
nvidia-smi
```

Look for insufficient VRAM, an incomplete download, an NVIDIA runtime error, or a port
conflict. The reference review requires the configured 40,960-token context; reducing it may
allow a small smoke test, but it no longer validates the complete scenario.

### The UI does not connect to vLLM

```powershell
$env:ARB_LLM_CONFIG_PATH
$env:NO_PROXY
Invoke-RestMethod http://localhost:8000/v1/models
```

Confirm that `ARB_LLM_CONFIG_PATH` points to an existing file and that the name served by vLLM
matches `qwen3-4b-awq` in `config/llm.vllm.json`.

### An agent fails even though vLLM responds

This usually indicates that the model output violated a structural or semantic contract.
Preserve the **Incomplete** state, each stage's state, and the logs. Do not silently switch to
`JSON_OBJECT`, weaken the schema, or retry until you get a success.

## 9. Safe Shutdown

Stop Streamlit with `Ctrl+C` in its terminal. Then stop the service while preserving the image
and model cache:

```powershell
docker compose down
```

Confirm that no runbook processes remain:

```powershell
docker compose ps
Get-NetTCPConnection -LocalPort 8501,8000 -State Listen -ErrorAction SilentlyContinue
```

Do not use `docker compose down --volumes` or `docker system prune`: both can remove data that
is expensive to download again.

## References

- [vLLM and Docker Guide](vllm-local-docker-guide.md)
- [Slice 8 deterministic and live acceptance](../specs/008-pedagogical-ui/acceptance.md)
- [Reference scenarios](../examples/reviews/README.md)
- [Local vLLM configuration](../config/llm.vllm.json)
