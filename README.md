# FireResBench

**FireResBench** is an event-centered benchmark for connecting
evolving wildfire conditions with real-world emergency-response histories. It
organizes heterogeneous wildfire records into temporally ordered
**Fire-Day** sequences and supports reproducible study of two complementary
problems:

1. **Task A -- Wildfire Lifecycle State Understanding:** classify the current
   Fire-Day into one of five operational lifecycle states.
2. **Task B -- Next-Day Operational-Response Forecasting:** independently
   forecast next-day personnel and next-day incident cost.

NOTE: This benchmark should not be treated as a real-time wildfire incident-command or automated resource-allocation system.

## Benchmark at a glance

### *Source cohort and coverage*

| Statistic               |                        Value |
| ----------------------- | ---------------------------: |
| Temporal coverage       |          Jan. 2017–Dec. 2020 |
| Spatial coverage        | CONUS; 48 states represented |
| Source-cohort Fire-Days |                       36,061 |

### *Model-ready dataset*

| Statistic                |  Value |
| ------------------------ | -----: |
| Fire-Day instances       | 33,303 |
| Unique incidents         |  5,728 |
| Data and metadata fields |    216 |

### *Task A lifecycle-label distribution*

| Lifecycle state   | Share of labeled Fire-Days |
| ----------------- | -------------------------: |
| Initial attack    |                     14.24% |
| Rapid escalation  |                     22.13% |
| Extended attack   |                     24.47% |
| Containment       |                     21.72% |
| Mop-up/monitoring |                     17.44% |

### *Task B target distribution*

| Target             | Median |   P90 |   P99 |
| ------------------ | -----: | ----: | ----: |
| Next-day personnel |     57 |   306 |     — |
| Daily cost (USD)   |  $100K | $1.1M | $5.2M |

### *Incident history length*

| Statistic                             | Median |  P75 | Maximum |
| ------------------------------------- | -----: | ---: | ------: |
| Fire-Days per incident                |      4 |    7 |     117 |


```text
Fire-Day = (incident_id, fire_day_date)
```

Each Fire-Day represents one wildfire incident on one calendar day. Records
from the same incident remain chronologically linked rather than being treated
as independent observations. Prediction-time features use only the current
Fire-Day and information observed on earlier Fire-Days from the same incident.

## Data sources

FireResBench integrates four public data-source families into a unified Fire-Day representation. ICS-209-PLUS provides the raw incident-level wildfire situation reports (which can be used to extract operational-response history). NASA FIRMS supplies date-aligned observations of active-fire activity. gridMET and LANDFIRE contribute meteorological and landscape covariates, respectively. For supervision construction, Task A uses evidence from ICS-209-PLUS and FIRMS, whereas the targets in Task B are derived from consecutive ICS-209 reports. gridMET and LANDFIRE are used as data features and do not define Task A labels or Task B targets.

| Source       | Information used                                             | Role in FireResBench                                         |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| ICS-209-PLUS | Incident identifiers and timestamps; reported area, containment, fire behavior, impacts, personnel, and cumulative incident cost | Provides the incident-centered Fire-Day timeline, current and historical operational evidence, evidence for Task A lifecycle supervision, and the sole source of Task B next-day personnel and daily-cost targets |
| NASA FIRMS   | Date-aligned VIIRS active-fire detections, detection counts, confidence, and fire radiative power within incident-centered spatial buffers | Provides satellite evidence of current fire activity for model inputs and Task A lifecycle-supervision construction; it does not define Task B targets |
| gridMET      | Daily fire-danger, wind, temperature, and fuel-moisture variables, together with backward-looking summaries | Provides time-varying meteorological and environmental covariates for model inputs; it is not used to construct lifecycle labels or operational-response targets |
| LANDFIRE     | Existing vegetation type, vegetation cover, and vegetation height summarized around each incident location | Provides static landscape and vegetation covariates for model inputs; it is not used to construct lifecycle labels or operational-response targets |



## Benchmark tasks

### Task A: Wildfire Lifecycle State Understanding

Given observations for incident `i` on day `t` and its available history
through day `t`, Task A predicts one of five lifecycle states:

```text
initial_attack
rapid_escalation
extended_attack
containment
mop_up_monitoring
```

The original data source does not contain the wildfire lifecycle state labels, we therefore develop a **two-stage labeling framework** to give each Fire-Day instance a robust lifecycle state label. 

**`Stage 1.`** **Deterministic pre-annotation.** Domain scholars and researchers define the lifecycle taxonomy, evidence thresholds, rule priority, and temporal constraints. The verified program derives evidence from fire age, area and growth, containment, FIRMS activity, reported fire behavior, personnel, and cost history, and then assigns a provisional state. 

**`Stage 2.`** **Human scholar team review.** Two reviewer teams inspect Fire-Days in incident-level chronological context. A third team adjudicates every disagreement or deferral. Outputs retain the reviewer models, actions, rationales, agreement, adjudication, and evaluation-eligibility fields.

The Stage 1 implementation preserves the activated rules, evidence signals,
confidence, transition status, missingness, and review-routing reasons for
every annotation. It also enforces temporal consistency: lifecycle sequences
normally remain in the current phase or advance, while renewed escalation is
permitted only when supporting evidence is observed.

Primary Task A metrics are **Macro-F1**, **balanced accuracy**, and mean
**Phase Distance**. Transition accuracy, per-class F1, calibration error, and
the row-normalized confusion matrix support finer-grained diagnosis.

### Task B: Next-Day Operational-Response Forecasting

Task B contains two regression targets. For consecutive Fire-Days from the same incident, let $P(i,t)$ be reported total personnel and
$C(i,t)$ be the as-reported cumulative incident-cost estimate. The targets are:

```text
next_day_personnel(i,t) = P(i,t+1)
daily_cost_usd(i,t) = C(i,t+1) - C(i,t)
```

The personnel target is the next-day resource level and is **not** differenced.
The cost target is the one-day increment between cumulative cost estimates. Personnel and cost eligibility are evaluated independently.

Missing endpoints are not imputed. Negative cost revisions, increments above USD 50 million, and invalid values are retained with
explicit status and provenance fields but are excluded from eligible target sets. 

Primary Task B metrics are personnel **MAE** and daily-cost **MAE** in their original units. **NMAE** and **RMSE** measure normalized and large-error behavior, while peak-personnel error, peak-timing error, and cumulative-cost error evaluate complete incident trajectories.


## Repository structure

```text
FireResBench Tree File Structure
TO BE COMPLETED
```


## Quick start

### Load Task A artifacts

```python
from pathlib import Path
import pandas as pd

root = Path("FireResBench")
keys = ["incident_id", "fire_day_date"]

task_a_features = pd.read_csv(
    root / "task_a_labeling/processed/fire_day_features_2017to2020.csv",
    low_memory=False,
)
task_a_labels = pd.read_csv(
    root / "task_a_labeling/labels/final_expert_labels.csv",
    low_memory=False,
)

task_a = task_a_features.merge(
    task_a_labels.loc[
        task_a_labels["supervised_evaluation_eligible"].eq(1),
        keys + ["final_lifecycle_label"],
    ],
    on=keys,
    how="inner",
    validate="one_to_one",
)
```

### Load Task B features, targets, and splits

```python
from pathlib import Path
import pandas as pd

root = Path("FireResBench")
keys = ["incident_id", "fire_day_date"]

task_b_features = pd.read_csv(
    root / "task_b_labeling/processed/fire_res_bench_task_b_features_2017to2020.csv",
    low_memory=False,
)
task_b_targets = pd.read_csv(
    root / "task_b_labeling/labels/task_b_targets_2017to2020.csv",
    low_memory=False,
)
splits = pd.read_csv(
    root / "task_b_labeling/metadata/incident_disjoint_splits.csv"
)

task_b = (
    task_b_features
    .merge(task_b_targets, on=keys, how="inner", validate="one_to_one")
    .merge(splits, on="incident_id", how="left", validate="many_to_one")
)

personnel_cases = task_b.loc[task_b["eligible_next_day_personnel"].eq(1)]
cost_cases = task_b.loc[task_b["eligible_daily_cost"].eq(1)]
```

For model inputs, use only fields listed in the corresponding
`task_*_feature_allowlist.json`. Identifiers, target-construction metadata,
eligibility indicators, future outcomes, and annotation metadata are not
prediction features.

## Rebuilding and verification

Run commands from the project root.

### Task A automatic pre-annotation artifacts

```bash
python FireResBench/task_a_labeling/build_task_a_stage1.py
python -m unittest discover -s FireResBench/task_a_labeling/tests -v
(cd FireResBench/task_a_labeling && \
  shasum -a 256 -c metadata/checksums.sha256)
```

The default build expects the ICS-209-PLUS SitRep table, annual 2017--2020
FIRMS VIIRS files, and the frozen labeling guide at the paths documented in
`task_a_labeling/README.md` and `task_a_labeling/DATA_SOURCES.md`.

### Task B

```bash
python FireResBench/task_b_labeling/build_task_b_2017to2020.py
python -m unittest discover -s FireResBench/task_b_labeling/tests -v
(cd FireResBench/task_b_labeling && \
  shasum -a 256 -c metadata/checksums.sha256)
```

By default, Task B uses the included compact snapshot of as-reported ICS-209
fields. It can also regenerate that snapshot from the official ICS-209 source
archive described in `task_b_labeling/DATA_SOURCES.md`.

The current full-range Task B builder retains a compatibility dependency on
the audited core in `FireAgentBench/TaskB-2020/build_task_b_2020.py` and the
frozen aligned Fire-Day table under `FireAgentBench/processed/`. These
dependencies must remain available when rebuilding this repository snapshot.

## Evaluation and leakage prevention

- Split data by `incident_id`, never by individual Fire-Days. Different days
  from one incident must not appear in both training and evaluation sets.
- The released Task B split uses a deterministic 80%/10%/10%
  train/validation/test partition with seed 2027.
- Construct temporal inputs only after sorting within each incident. All
  lagged and rolling windows must end no later than the prediction Fire-Day.
- Exclude next-day targets, final incident outcomes, label-construction fields,
  expert-review metadata, eligibility flags, and all future-derived variables
  from model inputs.
- Treat missing evidence as missing. Do not silently convert failed source
  alignment or unavailable observations into observed zeros.
- Report task-specific sample counts together with evaluation results.

## Provenance and quality assurance

FireResBench retains source-report identifiers, same-day collapse decisions,
field-level status, anomaly records, feature allowlists, data dictionaries,
construction versions, input hashes, and output checksums. Automated tests
cover lifecycle-rule behavior, temporal constraints, target semantics,
incident-disjoint splitting, and key leakage controls.

The Task B release restores cumulative cost directly from the official
as-reported ICS-209 archive. Cleaned or repaired cost values are retained only
for provenance comparison and do not serve as released target endpoints.

## Limitations and responsible use

FireResBench inherits reporting gaps, corrections, spatial uncertainty, and
institutional biases from its source systems. ICS-209 primarily covers
significant reported incidents rather than every wildfire. FIRMS activity is
affected by satellite overpass timing, cloud cover, and sensor properties;
gridMET describes gridded rather than on-scene weather; and LANDFIRE provides
landscape-scale context. Personnel and cost fields record reported operational
responses and should not be interpreted as uniquely optimal decisions.

The benchmark is intended for research, education, retrospective analysis,
and reproducible comparison. Predictions must not replace incident commanders,
dispatch systems, local observations, agency procedures, or expert judgment.

## Citation

If you use FireResBench, cite the accompanying paper and acknowledge the
upstream datasets listed above. A release-specific BibTeX entry and archival
identifier will be added when the benchmark publication record is available.
