# Review scenarios

These inputs exercise the five-agent review pipeline with different decision shapes.
They contain only scenario-provided facts; agents are expected to preserve uncertainty
and must not invent external evidence.

| Scenario | Primary functional pressure |
|---|---|
| `critical-desktop-migration.en.json` | Offline architecture, incremental modernization, and platform compatibility |
| `critical-desktop-migration.json` | Spanish localization of the critical desktop migration scenario |
| `regional-saas-data-platform-migration.en.json` | Zero-downtime migration, recovery objectives, data residency, and ambiguous regional rules |
| `manufacturing-edge-maintenance-pilot.en.json` | Weak historical labels, intermittent connectivity, pilot design, and evidence-based go/no-go criteria |
| `municipal-electric-bus-charging.en.json` | Capacity planning, uncertain infrastructure lead time, phased construction, and operational resilience |
| `customer-support-ai-assistant.en.json` | Human control, source traceability, privacy, knowledge quality, and evaluation design |
| `cold-chain-monitoring-modernization.en.json` | Edge buffering, legacy interoperability, auditability, alert quality, and inconsistent inventories |

Run one scenario against a configured local provider:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_review.py `
  --config config\llm.vllm.json `
  --input examples\reviews\regional-saas-data-platform-migration.en.json `
  --output artifacts\regional-saas-data-platform-migration.local.json `
  --raw-output-dir artifacts\regional-saas-data-platform-migration.local.raw
```

Use fresh output paths for every evaluation. Preserve incomplete and failed runs; do
not replace them with retries when measuring reliability.
