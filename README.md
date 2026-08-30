# Agentic Review Board

Multi-agent demonstrator for structured collaborative review and decision support.

## Development setup

Python 3.12 or newer is required.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
```

### Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
```

Runtime dependencies are constrained in `pyproject.toml` to Pydantic and HTTPX. Development
tooling is provided through the `dev` optional dependency group.

## LLM configuration

The runtime accepts OpenAI-compatible local and remote endpoints. Copy
`config/llm.example.json` outside version control when adapting it for an environment, and
set `ARB_LLM_CONFIG_PATH` to that file.

The JSON file contains only non-secret profile metadata and the five exact participant
assignments. A profile that needs authentication uses `api_key_env` to name an environment
variable; the credential itself must never be written into the JSON file.

### One model for all participants

Declare one profile and assign its exact name to `analyst`, `solution_architect`,
`risk_reviewer`, `critic`, and `coordinator`. The runtime creates one adapter for that
selected profile and reuses it for all five participants.

### Mixed local and remote models

The committed example assigns a local profile to Analyst and Risk Reviewer, and a remote
profile to Solution Architect, Critic, and Coordinator. Any supported mixture is configured
only through the five assignments. Declared profiles that are not assigned are structurally
validated but do not resolve credentials or make requests.

For the example remote profile, provide the referenced credential at runtime:

```powershell
$env:REMOTE_LLM_API_KEY = "<set-outside-source-control>"
$env:ARB_LLM_CONFIG_PATH = "C:\path\to\llm.json"
```

```bash
export REMOTE_LLM_API_KEY='<set-outside-source-control>'
export ARB_LLM_CONFIG_PATH='/path/to/llm.json'
```

Local profiles may omit `api_key_env`. A selected authenticated profile fails closed when
its referenced credential is absent, blank, or surrounded by whitespace. Credentials
referenced only by unselected profiles are not read.

### Proxy and certificate environment

The shared HTTPX client uses `trust_env=True`. Configure the process with standard
environment variables when required:

- `HTTP_PROXY` and `HTTPS_PROXY` for proxies;
- `NO_PROXY` for endpoints that must bypass a proxy, such as an approved local endpoint;
- `SSL_CERT_FILE` or `SSL_CERT_DIR` for the trusted certificate bundle or directory.

Do not place proxy credentials, API keys, or certificate contents in the LLM JSON file.

## Tests and optional live smoke

For a reusable local Docker/vLLM setup and its validation log, see
[`docs/vllm-local-docker-guide.md`](docs/vllm-local-docker-guide.md).

The default suite is deterministic and requires no configuration file, credential, installed
local model, hosted API, or network access:

```bash
pytest
```

Live smoke verification is operator-only. It checks every selected profile once with the
synthetic Analyst payload `{"description":"Live LLM connectivity smoke check."}`. It checks
connectivity and that a direct JSON object is returned; it does not execute a complete Review
or assess latency, reasoning, or answer quality.

A live run requires all of the following:

1. select the `live_llm` tests with `-m live_llm`;
2. pass the explicit `--run-live-llm` option;
3. set `ARB_RUN_LIVE_LLM` to exactly `1`;
4. set `ARB_LLM_CONFIG_PATH` to the intended configuration file.

Linux/macOS:

```bash
ARB_RUN_LIVE_LLM=1 ARB_LLM_CONFIG_PATH=/path/to/llm.json \
  pytest -m live_llm --run-live-llm
```

Windows PowerShell:

```powershell
$env:ARB_RUN_LIVE_LLM = "1"
$env:ARB_LLM_CONFIG_PATH = "C:\path\to\llm.json"
pytest -m live_llm --run-live-llm
```

Without both explicit authorizations, live tests skip before configuration loading or network
access. When live execution is authorized but the configuration path is absent, they also
skip safely. Once activated with a configuration, invalid configuration or a missing selected
credential fails rather than silently skipping or falling back.
