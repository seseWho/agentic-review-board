# Cross-scenario functional evaluation

## Fixed execution

On 2026-09-02, each of the five new English scenarios was executed exactly once with
vLLM 0.11.0, `Qwen/Qwen3-4B-AWQ`, temperature `0`, seed `0`, and the RTX 3060 local
profile. Every execution used fresh aggregate and raw-output paths. No failed stage was
retried, repaired, or replaced.

| Scenario | Review | Analyst | Solution Architect | Risk Reviewer | Critic | Coordinator | Seconds |
|---|---|---|---|---|---|---|---:|
| Regional SaaS data platform | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 125.79 |
| Manufacturing maintenance pilot | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 115.66 |
| Municipal electric-bus charging | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 124.61 |
| Customer-support AI assistant | INCOMPLETE | COMPLETED | FAILED | PENDING | PENDING | PENDING | 43.57 |
| Cold-chain monitoring | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | COMPLETED | 113.42 |

The observed end-to-end completion rate was 4/5 (80%). Mean duration was 104.61
seconds across all executions and 119.87 seconds across completed reviews. The four
completed Critic outputs contained six criticisms in total, with zero exact
target/basis repetitions and zero basis arrays containing exact duplicates.

## Preserved artifacts

Each basename below has one `.json` aggregate and one `.raw/` directory containing the
participant outputs that were reached:

- `artifacts/scenario-regional-saas-data-platform-migration-v011-01`
- `artifacts/scenario-manufacturing-edge-maintenance-pilot-v011-01`
- `artifacts/scenario-municipal-electric-bus-charging-v011-01`
- `artifacts/scenario-customer-support-ai-assistant-v011-01`
- `artifacts/scenario-cold-chain-monitoring-modernization-v011-01`

## Functional observations

The successful reviews produced three domain-specific alternatives each and retained
several important uncertainties through Coordinator. Examples include unsettled UK
disaster data rules, unnormalized plant downtime cost, the uncommitted grid-upgrade
date, future parking-bay approval, and cold-chain operation during network outages.
All four completed Coordinators returned `RECOMMENDED` with `MEDIUM` confidence and an
explicit next validation step.

The support-assistant execution failed closed at Solution Architect. Its JSON passed
the `SolutionAlternatives` structural model, but a generated
`blocking_missing_information` entry combined `id="MISS-001"` with the unrelated text
`"The current knowledge estate contains outdated and unowned material."` The only
trusted `MISS-001` text was the missing evaluation benchmark. Contextual validation
therefore raised an unresolved missing-information blocker error, and Risk Reviewer,
Critic, and Coordinator correctly remained pending. This exposes the absence of a
provider-enforced dynamic reference catalog for Solution Architect generation notes.

The semantic audit also found quality issues that valid references alone cannot catch:

- In the bus scenario, Analyst duplicated the charger-loss constraint under
  `CON-009` and `CON-100`, while omitting the requirement to retain compatible existing
  chargers. Critic correctly detected the duplicate in its trusted upstream artifact,
  but the original loss occurred in Analyst.
- In the SaaS scenario, Analyst classified peak traffic and storage growth as missing
  even though the input supplied 12000 peak writes per second, a 9 TB database, and
  monthly growth. Critic and Coordinator then propagated that false uncertainty.
- SaaS Critic treated seven-year audit retention and a six-month first resilience
  improvement as mutually conflicting, although the scenario does not make them
  incompatible. Coordinator reflected the unsupported conflict into its conclusion
  and next step.
- Manufacturing Coordinator retained cost and machine-learning operations questions,
  but its final decision did not foreground the inconsistent failure labels or the
  absence of confirmed failures in the earlier sensor trial.
- Cold-chain Coordinator changed an upstream requirement that the hybrid architecture
  *must ensure* continuity and auditability into a claim that it *ensures* them, before
  validation evidence was available.

## Implementation priorities exposed by the run

1. Give Analyst a dynamic exact catalog for input constraints and stated facts so it
   cannot silently omit, duplicate, or mutate authoritative input items.
2. Give Solution Architect a dynamic exact catalog for relevant constraints and
   generation-note blockers, closing the failure observed in the support scenario at
   provider generation time.
3. Add semantic evaluation checks for known-versus-missing claims, requirement
   compatibility, and modal changes such as `must ensure` becoming `ensures`.

This is a small fixed evaluation, not a general reliability score. Its purpose is to
identify concrete agent behaviors for the next implementation slices.

## Dynamic-contract correction and focused reruns

The first two priorities above were implemented on 2026-09-02. Analyst now receives a
request-specific schema that fixes every input constraint and `stated_facts` item, including
stable IDs and input order. Its participant boundary independently rejects omitted,
duplicated, mutated, reordered, or reclassified authoritative items. Solution Architect now
receives exact request-specific catalogs for relevant constraints and separate catalogs for
missing-information and uncertainty blockers. Existing contextual validation remains in
place as a second fail-closed layer.

Two fresh, non-retry diagnostic executions used vLLM 0.11.0, `Qwen/Qwen3-4B-AWQ`,
temperature `0`, seed `0`, and the same RTX 3060 profile:

| Scenario | Review | All five agents | Constraints exact | Stated facts exact | Blocker catalogs exact | Seconds |
|---|---|---|---|---|---|---:|
| Customer-support AI assistant | COMPLETED | Yes | 10/10, ordered | 5/5, ordered | Yes | 107.63 |
| Municipal electric-bus charging | COMPLETED | Yes | 10/10, ordered and distinct | 5/5, ordered | Yes | 115.83 |

The support scenario that previously stopped at Solution Architect now completed all five
stages with three alternatives. Every emitted blocker matched the exact `id` and `text` pair
in its own upstream collection. The bus scenario retained the previously omitted existing-
charger compatibility constraint and emitted no duplicate charger-loss constraint.

The preserved diagnostic basenames are:

- `artifacts/scenario-customer-support-ai-assistant-v011-dynamic-contracts-01`
- `artifacts/scenario-municipal-electric-bus-charging-v011-dynamic-contracts-01`

These focused reruns demonstrate correction of the two observed contract failures. They do
not revise the original fixed 4/5 reliability measurement and do not address the broader
semantic-quality observations in priority 3.
