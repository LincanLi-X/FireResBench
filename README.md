# FireRespBench

**FireRespBench** is an agent-ready benchmark for wildfire emergency-management research. It organizes multi-source incident, fire-activity, weather, landscape, and response data into daily wildfire cases that can be used by tabular models, time-series models, single LLM agents, and multi-agent systems.

The fundamental sample is a **Fire-Day**:

```text
Fire-Day = (incident_id, fire_day_date)
```

Each row describes one wildfire incident on one calendar day. The release covers a feature-complete, CONUS-focused subset from 2017-2020. It is intended for reproducible research and retrospective evaluation, not for live incident command or operational deployment.

## Dataset at a glance

| Item | Value |
|---|---:|
| Time span | 2017-01-01 to 2020-12-31 |
| Fire-Day samples | 33,303 |
| Wildfire incidents | 5,728 |
| Main-table columns | 216 |
| State-understanding eligible samples | 33,282 |
| Next-day personnel targets | 22,476 |
| Next-day daily-cost targets | 20,511 |
| Eligible resource-action labels | 20,803 |

The eligible resource-action subset contains 4,968 `escalate`, 8,483 `maintain`, and 7,352 `drawdown` cases. Counts and release-scope notes are also available in `processed/FireRespBench_fire_day_features_2017to2020_summary.csv`.

## Why FireRespBench?

Most wildfire datasets focus on hotspot detection, burned-area mapping, spread modeling, or remote-sensing prediction. FireRespBench instead represents the evolving operational state of an incident. It combines the current Fire-Day with recent temporal context, resource history, environmental evidence, supervised next-day targets, role-specific views, and explicit evaluation eligibility flags.

This design supports three model families under a common data interface:

- conventional tabular and time-series baselines;
- single-agent LLM systems using structured Fire-Day evidence;
- multi-agent systems with separated geographic, fire-behavior, resource-history, and critic roles.

## Data sources

| Source | Information used in this release | Role in FireRespBench |
|---|---|---|
| [ICS-209-PLUS](https://doi.org/10.1038/s41597-023-01955-0) | Incident status, location, fire behavior, containment, personnel, cumulative cost, command structure, evacuations, closures, and impacts | Core incident timeline and response supervision |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | Same-day active-fire detections, fire radiative power (FRP), and detection confidence | Daily fire-activity evidence aggregated around incident locations |
| [gridMET](https://www.climatologylab.org/gridmet.html) | Burning Index, wind speed, maximum/minimum temperature, and 100-hour/1000-hour dead-fuel moisture | Daily weather and fire-danger context from the nearest grid cell |
| [LANDFIRE](https://www.landfire.gov/) | Existing Vegetation Type (EVT), Cover (EVC), and Height (EVH) | Static landscape context summarized around each incident |

The current release contains these four source families. MTBS was considered in the broader benchmark design but is not included as a feature block in the released files.

## How the dataset was built

1. **Incident selection and normalization.** Wildfire records from ICS-209-PLUS were restricted to 2017-2020, and event identifiers, dates, coordinates, units, and incident types were standardized.
2. **Fire-Day construction.** Multiple situation reports for the same incident and date were deduplicated into a single daily record. Source-report counts and quality flags preserve information about collapsed, missing, or invalid observations.
3. **Temporal features.** Incident histories were ordered by date. Fire size, containment, personnel, cost, and fire-severity indicators were summarized with trailing 3-day and 7-day means or maxima using current and past records only.
4. **FIRMS alignment.** Same-day active-fire observations were aggregated within 1 km and 5 km of each incident location. Released features include detection counts, FRP summaries, confidence summaries, and match-status fields.
5. **gridMET alignment.** Daily meteorological and fuel-moisture variables were joined from the nearest CONUS grid cell, followed by selected 3-day and 7-day rolling summaries and Celsius temperature conversions.
6. **LANDFIRE alignment.** Dominant EVT, EVC, and EVH classes were summarized at 1 km and 5 km scales, together with dominant-class proportions and valid-pixel support.
7. **Response labels.** Consecutive next-calendar-day targets were constructed for personnel and daily cost. Because ICS-209 reports cumulative incident cost, daily cost was derived from non-negative cost increments, report intervals, and anomaly checks rather than treating cumulative cost as a daily label. Resource actions were assigned as `escalate`, `maintain`, or `drawdown` from personnel and cost signals; agreement, conflict, confidence, and eligibility are retained explicitly.
8. **Agent views.** The integrated table was projected into role-specific views. Decision-agent views exclude next-day ground truth, while the critic view retains targets and eligibility flags for scoring and error analysis.

The public subset contains only cases for which the required feature construction could be completed consistently. Events from Alaska, Hawaii, records with missing state information, and one uncovered Florida incident were excluded because a complete aligned environmental feature set was unavailable under the release pipeline.

## Benchmark tracks

FireRespBench is organized around three research tracks.

| Track | Goal | Expected output | Suggested metrics | Primary release artifacts |
|---|---|---|---|---|
| **Track 1: Wildfire State Understanding** | Infer the current operational phase and produce an evidence-grounded state assessment | `Initial attack`, `Rapid escalation`, `Extended attack`, `Containment`, or `Mop-up/monitoring`, optionally with cited evidence | Accuracy, Macro-F1, per-stage F1, evidence grounding | Main table, Geo view, Fire Behavior view, `eligible_state_understanding` |
| **Track 2: Daily Resource Recommendation** | Predict next-day resource needs and the direction of resource change | `daily_personnel`, `daily_cost_usd`, and `escalate`/`maintain`/`drawdown` | MAE/RMSE, action Macro-F1, peak-demand error, drawdown smoothness | Main table and both files in `labels/` |
| **Track 3: Error Diagnosis and Self-Evolution** | Diagnose a failed agent decision and identify how the system should improve | `failure_mode`, `responsible_module`, `suggested_update`, and supporting evidence | Diagnostic accuracy, module attribution, evidence grounding, update effectiveness | Role views, Critic view, and prompt templates |

Track 2 has direct supervised target files in this release. Track 1 supplies the feature-complete eligibility set and five-stage task protocol; a paper-specific canonical stage mapping should be reported with the experiment. Track 3 is evaluated after model predictions are available: the released critic view provides the complete case and ground truth, while failure taxonomies and update-effectiveness tests belong to the evaluated agent protocol rather than to a precomputed natural-language label file.

## Repository structure

```text
FireRespBench_main/
├── README.md
├── LICENSE.md
├── processed/
│   ├── FireRespBench_fire_day_features_2017to2020.csv
│   └── FireRespBench_fire_day_features_2017to2020_summary.csv
├── labels/
│   ├── fire_day_response_labels.csv
│   └── escalation_labels.csv
├── agent_ready/
│   ├── README.md
│   ├── geo_agent_view.csv
│   ├── fire_behavior_agent_view.csv
│   ├── resource_history_agent_view.csv
│   ├── critic_agent_view.csv
│   ├── agent_view_manifest.csv
│   ├── agent_role_registry.csv
│   ├── agent_prompt_templates.md
│   ├── configs/
│   ├── schemas/
│   ├── protocols/
│   └── examples/
└── metadata/
    ├── FireRespBench_derived_field_dictionary.csv
    └── checksums.sha256
```

### Main data files

- `processed/FireRespBench_fire_day_features_2017to2020.csv` is the complete modeling table. It contains ICS-209-derived incident fields, temporal features, response targets and eligibility flags, FIRMS aggregates, gridMET variables, and LANDFIRE summaries.
- `labels/fire_day_response_labels.csv` contains next-day personnel, daily-cost, and resource-action targets plus label evidence, confidence, status, and eligibility.
- `labels/escalation_labels.csv` is a compact action-classification table for `escalate`, `maintain`, and `drawdown` experiments.
- `metadata/FireRespBench_derived_field_dictionary.csv` documents key derived fields and their construction logic.

### Agent-ready views

FireRespBench defines a role-specific agent as `A_r = (M, V_r, I_r, S_r, P_r, C_r)`, comprising a versioned model backbone, role-specific view, instruction, private state, execution policy, and communication interface. The dataset fixes the latter five interface components while allowing researchers to compare different model backbones under identical evidence and orchestration. The complete specification is in `agent_ready/README.md`.

- **Geo Agent:** location, jurisdiction, coordinates, terrain, fuel descriptors, and LANDFIRE context.
- **Fire Behavior Agent:** fire size and growth, containment, observed behavior, FIRMS activity, gridMET conditions, and recent trends.
- **Resource History Agent:** personnel, aerial resources, cost history, command structure, suppression strategy, closures, evacuations, and impacts.
- **Critic Agent:** the complete evaluation record, including ground truth and eligibility. This view must not be exposed to a decision agent before prediction.

The release additionally provides model-configuration templates, state/message/output JSON schemas, single- and multi-agent execution protocols, Task C contamination controls, and a runnable case-preparation example. Natural-language observations are intentionally not pre-generated: researchers render them at experiment time with the selected model while preserving provenance and avoiding stale model-specific text.

## Quick start

```python
from pathlib import Path
import pandas as pd

root = Path("FireRespBench_main")

features = pd.read_csv(
    root / "processed/FireRespBench_fire_day_features_2017to2020.csv",
    low_memory=False,
)
labels = pd.read_csv(root / "labels/fire_day_response_labels.csv")

keys = ["incident_id", "fire_day_date"]
assert not features.duplicated(keys).any()
assert set(map(tuple, features[keys].to_numpy())) == set(
    map(tuple, labels[keys].to_numpy())
)

# Example: eligible next-day resource-action cases
action_cases = labels.loc[
    labels["eligible_resource_action"].eq(1),
    keys + ["resource_action", "action_label_confidence"],
]
```

## Evaluation and leakage prevention

- Split by `incident_id`, not by individual rows. Random Fire-Day splits can place different days from the same incident in both train and test sets.
- For temporal generalization, use year-held-out evaluation, such as training on 2017-2019 and testing on 2020.
- Filter each target with its corresponding `eligible_*` flag and report the resulting sample count.
- Do not expose `daily_personnel`, `daily_cost_usd`, `resource_action`, next-day target fields, or the Critic view to a decision model before inference.
- Treat missing values as missing evidence. Use the provided match-status, invalid-value, confidence, and eligibility fields rather than silently imputing them as observed zeros.

## Limitations and responsible use

FireRespBench inherits reporting gaps, corrections, spatial uncertainty, and operational biases from its source systems. FIRMS detections are affected by satellite coverage, clouds, and sensor characteristics; gridMET represents gridded rather than on-scene weather; LANDFIRE is a landscape-scale product; and daily cost is a derived estimate between irregular cumulative reports. The dataset covers large reported incidents and is not representative of every wildfire.

This benchmark is for research, education, retrospective analysis, and method comparison. It is **not** a real-time decision-support product and must not replace incident commanders, fire-behavior analysts, dispatch systems, local observations, or agency procedures.

## Integrity, citation, and license

From the repository root, verify release files with:

```bash
shasum -a 256 -c metadata/checksums.sha256
```

When using FireRespBench, cite the accompanying FireRespBench paper or repository release and acknowledge the upstream datasets listed above. The original FireRespBench curation, labels, prompt templates, and documentation are provided under the terms in `LICENSE.md`; upstream data remain subject to their respective attribution and use guidance.
