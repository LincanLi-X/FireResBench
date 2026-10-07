# FireResBench

**FireResBench** is an event-centered benchmark for connecting evolving wildfire conditions with real-world emergency-response histories. It is built from reported wildfire incident records and aligned environmental observations. FireResBench organizes heterogeneous wildfire records into temporally ordered **Fire-Day** sequences and supports reproducible study of two complementary problems:

1. **Task A -- Wildfire Lifecycle State Understanding:** classify the current
   Fire-Day into one of five operational lifecycle states.
2. **Task B -- Next-Day Operational-Response Forecasting:** independently
   forecast next-day personnel and next-day incident cost.

> **NOTE:** FireResBench is intended for research, education, and reproducible comparison. It is not a real-time incident-command, dispatch, resource-allocation, fire-spread simulation, or prescriptive decision-support system.


This repository releases FireResBench dataset artifacts and the code used for dataset construction, Task A pre-labeling and scholar-review integration, Task B target construction, incident-disjoint data splitting, and feature-allowlist generation. Its primary purpose is to support transparent dataset inspection, consistent task construction, and independent model development. This repository should not be interpreted as a complete reproduction package for every baseline result reported in the manuscript. The benchmark tasks, released splits, permitted input features, target definitions, and recommended evaluation metrics are documented so that users can implement and evaluate models within their own experimental frameworks.


## Benchmark at a glance

### *Source cohort and coverage*

| Statistic | Value |
|---|---:|
| Temporal coverage | Jan. 2017–Dec. 2020 |
| Spatial coverage | CONUS; 48 states represented |
| Source-cohort Fire-Days | 36,061 |

### *Model-ready dataset*

| Statistic | Value |
|---|---:|
| Fire-Day instances | 33,303 |
| Unique incidents | 5,728 |
| Data and metadata fields | 216 |

### *Task A lifecycle-label distribution*

| Lifecycle state | Share of labeled Fire-Days |
|---|---:|
| Initial attack | 14.24% |
| Rapid escalation | 22.13% |
| Extended attack | 24.47% |
| Containment | 21.72% |
| Mop-up/monitoring | 17.44% |

### *Task B target distribution*

| Target | Median | P90 | P99 |
|---|---:|---:|---:|
| Next-day personnel | 57 | 306 | — |
| Daily cost (USD) | $100K | $1.1M | $5.2M |

### *Incident history length*

| Statistic | Median | P75 | Maximum |
|---|---:|---:|---:|
| Fire-Days per incident | 4 | 7 | 117 |
The fundamental sample is a Fire-Day:

```text
Fire-Day = (incident_id, fire_day_date)
```

Each Fire-Day represents one wildfire incident on one calendar day. Records
from the same incident remain chronologically linked rather than being treated
as independent observations. Prediction-time features use only the current
Fire-Day and information observed on earlier Fire-Days from the same incident.

## Data sources

FireResBench integrates four public data-source families into a unified Fire-Day representation. ICS-209-PLUS provides the raw incident-level wildfire situation reports (which can be used to extract operational-response history). NASA FIRMS supplies date-aligned observations of active-fire activity. gridMET and LANDFIRE contribute meteorological and landscape covariates, respectively. For supervision construction, Task A uses evidence from ICS-209-PLUS and FIRMS, whereas the targets in Task B are derived from consecutive ICS-209 reports. gridMET and LANDFIRE are used as data features and do not define Task A labels or Task B targets.

| Source | Information used | Role in FireResBench |
|---|---|---|
| ICS-209-PLUS | Incident identifiers and timestamps; reported area, containment, fire behavior, impacts, personnel, and cumulative incident cost | Provides the incident-centered Fire-Day timeline, current and historical operational evidence, evidence for Task A lifecycle supervision, and the sole source of Task B next-day personnel and daily-cost targets |
| NASA FIRMS | Date-aligned VIIRS active-fire detections, detection counts, confidence, and fire radiative power within incident-centered spatial buffers | Provides satellite evidence of current fire activity for model inputs and Task A lifecycle-supervision construction; it does not define Task B targets |
| gridMET | Daily fire-danger, wind, temperature, and fuel-moisture variables, together with backward-looking summaries | Provides time-varying meteorological and environmental covariates for model inputs; it is not used to construct lifecycle labels or operational-response targets |
| LANDFIRE | Existing vegetation type, vegetation cover, and vegetation height summarized around each incident location | Provides static landscape and vegetation covariates for model inputs; it is not used to construct lifecycle labels or operational-response targets |



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

**`Stage 2.`** **Human scholar team review.** Two reviewer teams inspect Fire-Days in incident-level chronological context. A third team adjudicates every disagreement or deferral. Outputs retain the review and adjudication actions, labels, rationales, confidence values, agreement status, and evaluation-eligibility fields.

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
FireResBench/
├── README.md
├── LICENSE
├── task_a_labeling/
│   ├── README.md
│   ├── DATA_SOURCES.md
│   ├── build_task_a_stage1.py
│   ├── build_task_a_stage2.py
│   ├── lifecycle_rules_v1.yaml
│   ├── docs/
│   │   └── FireResBench_TaskA_Labeling_Guide.md
│   ├── processed/
│   │   └── fire_day_features_2017to2020.csv
│   ├── labels/
│   │   ├── automatic_prelabels.csv
│   │   ├── expert_review_case_index.csv
│   │   ├── expert_review_queue.csv
│   │   ├── expert_review_template.csv
│   │   └── final_expert_labels.csv
│   ├── metadata/
│   │   ├── incident_disjoint_splits.csv
│   │   ├── stage2_data_dictionary.csv
│   │   ├── task_a_data_dictionary.csv
│   │   └── task_a_feature_allowlist.json
│   └── scholar_annotation/
│       ├── reviewer_a_decisions.csv
│       ├── reviewer_b_decisions.csv
│       ├── adjudication_queue.csv
│       ├── adjudicator_decisions.csv
│       ├── sequence_review_queue.csv
│       ├── sequence_adjudicator_decisions.csv
│       ├── sequence_review_queue_round2.csv
│       ├── sequence_adjudicator_decisions_round2.csv
│       ├── reviewer_agreement_statistics.json
│       ├── reviewer_a_policy.md
│       ├── reviewer_b_policy.md
│       ├── adjudicator_policy.md
│       ├── sequence_adjudicator_policy.md
│       ├── build_expert_review_template.py
│       ├── build_adjudication_queue.py
│       └── build_sequence_review_queue.py
└── task_b_labeling/
    ├── README.md
    ├── DATA_SOURCES.md
    ├── build_task_b_2017to2020.py
    ├── task_b_target_rules_v1.yaml
    ├── docs/
    │   └── FireResBench_TaskB_Labeling_Guide.md
    ├── processed/
    │   └── fire_res_bench_task_b_features_2017to2020.csv
    ├── labels/
    │   └── task_b_targets_2017to2020.csv
    ├── metadata/
    │   ├── incident_disjoint_splits.csv
    │   ├── task_b_data_dictionary.csv
    │   ├── task_b_feature_allowlist.json
    │   ├── task_b_2017to2020_summary.csv
    │   ├── task_b_target_status_summary.csv
    │   └── cost_provenance_audit.csv
    └── source/
        └── ics209_as_reported_report_fields_2017to2020.csv
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

Run the following commands from the repository root, the directory containing
`task_a_labeling/` and `task_b_labeling/`.

### Task A automatic pre-annotation artifacts

Task A Stage 1 reads the ICS-209-PLUS SitRep table and annual 2017--2020 FIRMS
VIIRS files from the surrounding workspace. Build into a staging directory so
that existing release artifacts are not overwritten before inspection:

```bash
python task_a_labeling/build_task_a_stage1.py \
  --ics ../ics209plus-wildfire/ics209-plus-wf_sitreps_1999to2020.csv \
  --firms-dir ../FIRMS \
  --guide task_a_labeling/docs/FireResBench_TaskA_Labeling_Guide.md \
  --config task_a_labeling/lifecycle_rules_v1.yaml \
  --output-root build/task_a_labeling
```

The builder performs same-day report collapse, FIRMS alignment, backward-looking
feature construction, deterministic lifecycle pre-annotation, temporal checks,
and review routing. Its principal outputs are the Fire-Day feature table,
automatic prelabels, expert-review queue, review-case index, and blank expert
review template. Source details are documented in
`task_a_labeling/DATA_SOURCES.md`.

Task A Stage 2 validates and combines the files and annotations from two
independent reviewer teams, the required row-level adjudications, and any
sequence-adjudication decisions. Place the completed human-review files under
`task_a_labeling/scholar_annotation/`, or pass their locations explicitly. An initial
integration pass that writes the candidate labels and sequence-anomaly queue is:

```bash
python task_a_labeling/build_task_a_stage2.py \
  --prelabels build/task_a_labeling/labels/automatic_prelabels.csv \
  --review-queue build/task_a_labeling/labels/expert_review_queue.csv \
  --reviewer-a task_a_labeling/scholar_annotation/reviewer_a_decisions.csv \
  --reviewer-b task_a_labeling/scholar_annotation/reviewer_b_decisions.csv \
  --adjudicator task_a_labeling/scholar_annotation/adjudicator_decisions.csv \
  --output build/task_a_labeling/labels/final_expert_labels.csv \
  --sequence-anomalies build/task_a_labeling/scholar_annotation/sequence_anomalies.csv \
  --skip-sequence-decisions
```

After experts complete the sequence decisions, rerun the Stage 2 command with
`--sequence-decisions` pointing to the completed decision file and without
`--skip-sequence-decisions`. If the first sequence pass creates new anomalies,
the script supports a second expert sequence-review round. The integration
fails rather than silently continuing when reviewer coverage, reviewer
independence, adjudication coverage, label semantics, or sequence consistency
is invalid.

### Task B

Task B is rebuilt by the self-contained repository script:

```bash
python task_b_labeling/build_task_b_2017to2020.py \
  --cleaned-sitreps ../ics209plus-wildfire/ics209-plus-wf_sitreps_1999to2020.csv \
  --aligned-features ../processed/processed_fire_day_features_2017to2020.csv \
  --rules task_b_labeling/task_b_target_rules_v1.yaml \
  --raw-snapshot task_b_labeling/source/ics209_as_reported_report_fields_2017to2020.csv
```

The builder restores as-reported ICS-209 cost and area fields, collapses
same-day reports, derives backward-looking features, constructs strict
next-calendar-day personnel and cost targets, creates incident-disjoint splits,
and validates key coverage, target eligibility, date range, and feature
leakage. It writes only these core artifacts:

- `processed/fire_res_bench_task_b_features_2017to2020.csv`;
- `labels/task_b_targets_2017to2020.csv`;
- `metadata/task_b_feature_allowlist.json`;
- `metadata/incident_disjoint_splits.csv`.

The included compact ICS-209 snapshot supplies the as-reported fields required
for target construction. Its relationship to the official archive is described
in `task_b_labeling/DATA_SOURCES.md`. The Task B builder does not import code or
data from `FireAgentBench`.


## Evaluation protocol and leakage prevention

- Split data by `incident_id`, never by individual Fire-Days. Different days
  from one incident must not appear in both training and evaluation sets.
- The Task B split uses a deterministic 80%/10%/10% train/validation/test
  partition with seed 2027.
- Sort records within each incident before constructing temporal inputs. Every
  lagged or rolling feature must end no later than the prediction Fire-Day.
- Select model inputs from the task-specific feature allowlist. Treat incident
  and report identifiers, names, source-row references, and review fields as
  metadata rather than predictive inputs.
- Exclude next-day targets, final incident outcomes, lifecycle-construction
  fields, expert-review records, eligibility flags, and every future-derived
  variable from model inputs.
- Evaluate Task B personnel and cost on their respective eligible subsets; the
  two subsets need not contain the same Fire-Days.
- Report the evaluated Fire-Day and incident counts with every result.


## Limitations and responsible use

FireResBench inherits reporting gaps, retrospective corrections, spatial
uncertainty, and institutional biases from its source systems. ICS-209 mainly
covers significant reported incidents rather than every wildfire. FIRMS
activity depends on satellite overpass timing, cloud cover, and sensor
properties. gridMET provides gridded conditions rather than on-scene weather,
and LANDFIRE supplies landscape-scale summaries rather than incident-specific
field observations.

Task A lifecycle states are expert-reviewed operational abstractions rather
than directly observed physical states. Task B personnel and cost targets
describe reported responses under historical constraints and should not be
interpreted as uniquely optimal decisions or prescriptive resource plans.

The benchmark is intended for research, education, retrospective analysis,
and reproducible comparison. Predictions must not replace incident commanders,
dispatch systems, local observations, agency procedures, or expert judgment.

## Citation

If you find FireResBench useful, please consider citing our work:
```
@inproceedings{anonymous2026fireresbench,
  title     = {FireResBench: An Event-Centered Benchmark for Wildfire Lifecycle Understanding and Operational-Response Forecasting},
  author    = {Anonymous Authors},
  booktitle = {Under Review},
  year      = {2026}
}
```
