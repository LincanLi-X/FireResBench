# FireResBench Task B Response-Target Construction Guide

**Scope:** FireResBench Task B - Next-Day Personnel and Daily-Cost Forecasting  
**Observation unit:** one `Fire-Day = (incident_id, fire_day_date)`  
**Forecast origin:** Fire-Day $t$  
**Target date:** the strictly consecutive next calendar day $t+1$  
**Construction workflow:** deterministic target derivation + automated validation + provenance audit

> The filename retains the legacy `FireRespBench` prefix for workspace
> compatibility. The benchmark name used in this guide is the current name,
> **FireResBench**.

---

## 1. Purpose and supervision philosophy

Task B evaluates whether a model can forecast the operational response observed
on the next calendar day. It contains two continuous targets:

1. `next_day_personnel`: the total personnel assigned on the next Fire-Day;
2. `daily_cost_usd`: the estimated incident-cost increment accrued between the
   current Fire-Day and the strictly consecutive next Fire-Day.

The two targets are constructed differently because the underlying ICS-209-PLUS
fields have different semantics:

| ICS-209-PLUS field | Meaning | Construction consequence |
|---|---|---|
| `TOTAL_PERSONNEL` | Personnel assigned at the report time/operational period; a current resource level, not a cumulative count | Shift the valid level to the next calendar day; do not difference it |
| `TOTAL_AERIAL` | Aerial resources assigned at the report time/operational period; not aircraft sorties, aerial personnel, or a cumulative count | Retain the current-day value as an optional input feature; do not difference it; it is not a Task B target in the current release |
| `EST_IM_COST_TO_DATE` | Estimated cumulative incident cost through the report time | Difference consecutive cumulative values to derive the daily-cost target |

Task B target construction is deterministic. Domain experts may audit source
semantics, anomaly policies, and ambiguous records, but they must not manually
invent or adjust numerical target values. A row is either assigned a target by
the frozen construction rules or marked ineligible with an explicit reason.

The task is retrospective forecasting and benchmark evaluation. It does not
prescribe staffing levels, authorize expenditures, or replace operational
incident-command decisions.

---

## 2. Data sources and their roles

### 2.1 Target source

ICS-209-PLUS is the sole authoritative source used to derive the two Task B
targets:

| Source field | Target role |
|---|---|
| `TOTAL_PERSONNEL` | Source of the next-day assigned-personnel level |
| `EST_IM_COST_TO_DATE` | Source of the next-day daily-cost increment |
| incident identifier and report timestamp | Establish incident chronology and strict calendar-day adjacency |

### 2.2 Contextual input sources

The following sources may provide prediction-time features, but they do not
define Task B ground truth:

| Source | Permitted role |
|---|---|
| ICS-209-PLUS | Current and historical incident status, containment, personnel, aerial resources, management, impacts, and other temporally valid report fields |
| NASA FIRMS / VIIRS | Same-day active-fire detections and fire radiative power available for Fire-Day $t$ |
| gridMET | Same-day and backward-looking meteorological context |
| LANDFIRE | Static landscape and vegetation context |

Human experts may verify field meaning, source anomalies, and audit samples.
They are not an additional numerical-label source for Task B.

---

## 3. Formal task definition

For incident $i$ on observation day $t$, let:

- $P_{i,t}$ be `TOTAL_PERSONNEL` on Fire-Day $t$;
- $C_{i,t}$ be `EST_IM_COST_TO_DATE` on Fire-Day $t$;
- $x_{i,t}$ contain only evidence available through day $t$.

When the next valid Fire-Day for the same incident occurs exactly on $t+1$,
the targets are:

\[
y^{(P)}_{i,t+1}=P_{i,t+1},
\]

and

\[
y^{(C)}_{i,t+1}=C_{i,t+1}-C_{i,t}.
\]

The benchmark prediction mapping is:

\[
f_B(\mathbf{x}_{i,t})
    =
    \left[
        \widehat{y}^{(P)}_{i,t+1},
        \widehat{y}^{(C)}_{i,t+1}
    \right].
\]

The personnel target is a next-day resource **level**. The cost target is a
next-day estimated **increment**. They must not be interpreted as two instances
of the same differencing operation.

The two targets have independent eligibility flags. A Fire-Day may be valid for
personnel forecasting but invalid for cost forecasting, or vice versa.

---

## 4. Evidence boundary and anti-leakage rule

For each incident, Fire-Days must be ordered chronologically. At prediction
time for Fire-Day $t$, model inputs may use only:

- observations recorded on or before $t$;
- backward-looking changes computed from the current and preceding Fire-Days;
- trailing summaries whose windows end on $t$;
- same-day external observations whose timestamps satisfy the published
  availability policy;
- static geographic and landscape context.

The target-construction program may access Fire-Day $t+1$ only to construct
and store the supervised outcomes. It must never copy those values into the
prediction-time feature table.

The following must not enter $x_{i,t}$:

- `next_day_personnel` or `daily_personnel` target values;
- `daily_cost_usd` for the target interval;
- any `target_*`, `next_*`, or future-shifted field;
- target eligibility or target-status fields when they reveal whether a future
  report or valid future value exists;
- final incident size, final containment outcome, final total cost, or other
  retrospectively known outcomes;
- future Fire-Days, centered windows, or backward filling from future reports;
- label-construction metadata that directly encodes a target value or future
  availability.

Train/validation/test splits must be incident-disjoint so that different days
from the same wildfire cannot cross split boundaries.

---

## 5. Fire-Day construction before target derivation

### 5.1 Unique key

Each modeling row must be uniquely identified by:

```text
(incident_id, fire_day_date)
```

No duplicate incident-date rows are permitted in the model-ready table.

### 5.2 Calendar date and timezone

`fire_day_date` must be derived from the selected report timestamp using the
incident's documented local timezone when available. The pipeline must not mix
UTC dates and local dates silently. The timezone rule and any fallback must be
documented with the construction policy.

### 5.3 Multiple reports on the same date

If an incident has multiple ICS-209-PLUS reports on one calendar date:

1. order reports by the most reliable submission/report timestamp;
2. retain the latest valid same-day value for dynamic fields;
3. preserve `source_report_count` and source-report identifiers;
4. record which source row supplied each target-relevant field when fields are
   resolved independently;
5. do not treat same-day reports as separate next-day targets.

The same-day collapse must occur before shifting to the next Fire-Day.

### 5.4 Incident chronology

After same-day collapse:

1. sort by `incident_id`, `fire_day_date`, and the deterministic tie-breaker;
2. calculate the previous and next Fire-Day within each incident;
3. calculate the actual calendar gaps;
4. never link records across incident identifiers;
5. retain missing calendar dates as unobserved days rather than synthesizing
   Fire-Day rows through interpolation.

### 5.5 Strict next-day requirement

Task B supervision is assigned only when:

```text
next_fire_day_date == fire_day_date + 1 calendar day
```

A simple row-wise `shift(-1)` is insufficient because it produces the next
available report, which may occur several days later. Non-consecutive reports
must not be called next-day targets.

---

## 6. Required source and processed fields

The implementation should map the source schema to the following canonical
variables. Source ICS-209-PLUS fields are shown in uppercase; FireResBench
processed fields use lowercase names.

| Canonical variable | Source/processed field | Meaning | Requirement |
|---|---|---|---|
| `incident_id` | normalized incident identifier | Unique incident key | Required |
| `fire_day_date` | derived from report timestamp | Observation-day calendar date | Required |
| `source_report_id` | report identifier | Audit link to the original SitRep | Required for provenance |
| `source_report_count` | derived | Number of same-day reports collapsed | Required |
| `total_personnel` | `TOTAL_PERSONNEL` | Current assigned-personnel level | Required for personnel target |
| `total_aerial` | `TOTAL_AERIAL` | Current assigned aerial-resource level | Optional input; not a target |
| `cumulative_cost_usd` | `EST_IM_COST_TO_DATE` | Estimated cumulative cost at the report time | Required for cost target |
| `containment` | `PCT_CONTAINED_COMPLETED` | Current reported containment percentage | Optional input and quality flag |
| `previous_fire_day_date` | derived | Most recent preceding Fire-Day | Required for audit |
| `next_fire_day_date` | derived | Next available Fire-Day | Required for target construction |
| `days_since_previous_report` | derived | Calendar gap from the preceding Fire-Day | Required for interval audit |
| `days_to_next_report` | derived | Calendar gap to the next Fire-Day | Required for eligibility |
| `cost_increment_usd` | derived | Current cumulative cost minus preceding cumulative cost | Required for current cost history |
| `average_daily_cost_usd` | derived | Valid cost increment divided by preceding interval length | Optional historical input |

The code must fail with a clear schema error when an identifier, date, or
target-source column is absent. A missing target-source value must remain
missing; it must not be silently converted to zero.

---

## 7. Source-value validation

### 7.1 Personnel validation

`TOTAL_PERSONNEL` represents the personnel assigned at that Fire-Day. It is
valid for Task B when it is numeric and within the frozen admissible range:

```text
0 <= total_personnel <= 10,000
```

Personnel may increase, remain unchanged, or decrease across Fire-Days. A
decrease is not automatically an error and must not be clipped to zero.

The following values are invalid:

- missing or non-numeric values;
- negative values;
- values above 10,000 under the current benchmark policy.

### 7.2 Cumulative-cost validation

`EST_IM_COST_TO_DATE` is an estimated cumulative value. A source value is
candidate-valid when it is numeric, non-negative, and linked to an auditable
source report.

For two chronologically adjacent Fire-Days $t^{-}$ and $t$, define:

\[
\Delta C_{i,t}=C_{i,t}-C_{i,t^{-}}.
\]

The cost interval is invalid when:

- either endpoint is missing or non-numeric;
- the calendar gap is zero or negative;
- the cumulative difference is negative;
- either endpoint was filled using information recorded after the endpoint
  date under a non-causal repair procedure;
- the derived daily rate exceeds the frozen upper bound.

A negative difference usually reflects a revised estimate or source anomaly.
It must be flagged as `negative_revision`; it must not be converted to a zero
daily cost.

### 7.3 Provenance audit for processed cost fields

Before release, the team must verify whether the selected ICS-209-PLUS cost
column contains forward filling, backward filling, smoothing, or corrections
that use reports later than the target date. A value reconstructed using
information after $t+1$ is not valid for leakage-controlled forecasting,
even if it appears in a processed table.

The preferred Task B target source is the as-reported cumulative estimate at
each endpoint. If a processed cost value is retained, the release must document
why its construction is temporally causal and preserve the source-report
provenance. Records that fail this audit must be marked ineligible rather than
silently retained.

### 7.4 Containment and other input checks

Containment outside `[0, 100]`, invalid coordinates, impossible dates, and
other malformed input values must be flagged. Such flags do not automatically
invalidate both Task B targets unless the target itself is affected, but they
must be available for model-input eligibility and data-quality analysis.

---

## 8. Derived current-day history variables

Historical variables may be derived for use in $x_{i,t}$, provided
they use only current and preceding Fire-Days.

### 8.1 Personnel history

For a valid preceding personnel value:

\[
\Delta P_{i,t}=P_{i,t}-P_{i,t^{-}},
\]

\[
\text{personnel\_delta\_per\_day}_{i,t}
=
\frac{\Delta P_{i,t}}
{\text{days}(t-t^{-})}.
\]

These variables describe historical change through day $t$. They are model
inputs, not replacements for the next-day personnel target.

### 8.2 Current daily-cost history

When the cumulative-cost interval ending at $t$ is valid:

\[
\text{average\_daily\_cost}_{i,t}
=
\frac{C_{i,t}-C_{i,t^{-}}}
{\text{days}(t-t^{-})}.
\]

For a one-day interval this reduces to the simple cumulative difference. For a
multi-day interval, the value is an interval-average historical feature; it
must not be represented as an observed cost for each unreported day.

Recommended interval-status values are:

```text
first_fire_day
valid_1d
valid_multiday
missing_previous_endpoint
missing_current_endpoint
invalid_calendar_gap
negative_revision
noncausal_source_repair
out_of_range
```

### 8.3 Trailing summaries

Trailing 3-day and 7-day summaries may include Fire-Day observations available
through $t$. Windows must:

- end on $t$;
- use observed Fire-Days only;
- preserve the distinction between calendar span and number of reports;
- avoid centered or forward-looking windows;
- retain support counts and missingness when practical.

---

## 9. Target construction rules

### 9.1 Shared adjacency condition

For each Fire-Day $t$, define:

```text
strict_next_day = (
    next_fire_day_date == fire_day_date + 1 calendar day
)
```

If `strict_next_day` is false, both Task B targets are unavailable for that
forecast origin. The row may remain in the feature table but must be excluded
from the corresponding supervised evaluation.

### 9.2 Next-day personnel

When `strict_next_day` is true and both the current and next personnel values
pass validation:

```text
next_day_personnel = total_personnel at target_date
eligible_next_day_personnel = 1
personnel_target_status = eligible
```

No differencing is performed. In particular:

```text
total_personnel[t+1] - total_personnel[t]
```

is the net personnel change, not the next-day assigned-personnel target.

### 9.3 Daily cost

When `strict_next_day` is true, both cumulative-cost endpoints are valid, the
source values pass the temporal-provenance audit, and the increment is within
range:

```text
daily_cost_usd = cumulative_cost_usd[t+1] - cumulative_cost_usd[t]
eligible_daily_cost = 1
cost_target_status = eligible_valid_1d
```

Because the interval is exactly one calendar day, no additional division is
required. The equivalent general expression is:

```text
daily_rate = (cumulative_cost[next] - cumulative_cost[current])
             / days_to_next_report
```

with `days_to_next_report == 1` required for Task B eligibility.

`daily_cost_usd` is an increment in the reported cumulative estimate. It must
not be described as audited expenditure or exact accounting expenditure.

### 9.4 Independent target eligibility

Eligibility is target-specific:

```text
eligible_next_day_personnel != eligible_daily_cost  # allowed
```

Do not discard a valid personnel target because the cost endpoints are missing,
and do not discard a valid cost target solely because personnel is missing.

### 9.5 Aerial resources

`TOTAL_AERIAL` is not part of the current Task B output vector. The current-day
value may be included in $x_{i,t}$ as an operational-context feature.
It must not be differenced unless a separate, explicitly named net-change
feature is desired.

If a future release introduces next-day aerial forecasting, its level target
should be constructed analogously to personnel:

```text
next_day_aerial = total_aerial at target_date
```

That extension is outside the current Task B scope.

### 9.6 Excluded legacy action labels

Legacy artifacts may contain `escalate`, `maintain`, and `drawdown` labels
derived from personnel and cost changes. These action labels are not Task B
targets in the current FireResBench scope. They may be retained in a legacy or
auxiliary file, but they must not:

- appear in the primary Task B target table as required outputs;
- be reported as a third Task B target;
- enter model inputs;
- determine eligibility for personnel or cost regression.

---

## 10. Frozen thresholds and eligibility definitions

The following values define the FireResBench Task B specification. Any change
requires regeneration of all labels, splits, statistics, and benchmark results.

| Parameter | Frozen value |
|---|---:|
| Required target interval | exactly `1 calendar day` |
| Minimum personnel | `0` |
| Maximum personnel | `10,000` |
| Minimum cumulative cost | `0 USD` |
| Minimum daily-cost increment | `0 USD/day` |
| Maximum daily-cost increment | `50,000,000 USD/day` |
| Negative cumulative-cost revision | invalid; do not clip |
| Missing target endpoint | ineligible; do not impute |
| Non-causal repaired endpoint | ineligible unless a temporally valid source value is restored |

Personnel eligibility is:

```text
eligible_next_day_personnel = (
    strict_next_day
    AND current_personnel_is_valid
    AND target_personnel_is_valid
)
```

Cost eligibility is:

```text
eligible_daily_cost = (
    strict_next_day
    AND current_cumulative_cost_is_valid
    AND target_cumulative_cost_is_valid
    AND cost_increment_usd >= 0
    AND cost_increment_usd <= 50_000_000
    AND both_endpoints_pass_temporal_provenance_audit
)
```

---

## 11. Ineligibility status vocabulary

Every ineligible value must have a machine-readable status. Recommended
personnel-target statuses are:

```text
eligible
excluded_no_next_fire_day
excluded_nonconsecutive_next_report
excluded_invalid_current_personnel
excluded_invalid_target_personnel
excluded_ambiguous_same_day_collapse
```

Recommended cost-target statuses are:

```text
eligible_valid_1d
excluded_no_next_fire_day
excluded_nonconsecutive_next_report
excluded_missing_current_cost
excluded_missing_target_cost
excluded_negative_cost_revision
excluded_cost_out_of_range
excluded_noncausal_source_repair
excluded_ambiguous_same_day_collapse
```

Unknown, missing, invalid, and inapplicable must remain distinguishable. An
ineligible target must be stored as missing rather than numeric zero.

---

## 12. Deterministic-construction implementation contract

### 12.1 Separation of roles

1. Researchers and domain experts approve source-field semantics, thresholds,
   and anomaly policies.
2. A coding agent or developer translates the frozen specification into
   deterministic code.
3. A researcher reviews the implementation and runs synthetic unit tests.
4. The verified program constructs targets over the complete release cohort.
5. Automated validation checks target values, keys, chronology, provenance,
   and leakage boundaries.
6. Human reviewers may flag source errors but must not hand-edit numerical
   labels without a documented source-data correction.

### 12.2 Required primary output columns

The primary Task B target table should contain at least:

```text
incident_id
fire_day_date
target_date
days_to_target
current_personnel
next_day_personnel
eligible_next_day_personnel
personnel_target_status
current_cumulative_cost_usd
target_cumulative_cost_usd
daily_cost_usd
eligible_daily_cost
cost_target_status
source_report_count
current_source_report_id
target_source_report_id
```

If compatibility with legacy column names is required, publish an explicit
mapping:

```text
daily_personnel            -> next_day_personnel
eligible_daily_personnel   -> eligible_next_day_personnel
```

The preferred semantic name is `next_day_personnel`. If `daily_personnel` is
retained in a released CSV, its Data Dictionary must state that it is the next
day's assigned-personnel level, not a personnel difference or cumulative count.

### 12.3 Recommended audit columns

```text
next_fire_day_date
days_to_next_report
current_personnel_valid
target_personnel_valid
cost_increment_usd
cost_interval_status
current_cost_provenance_status
target_cost_provenance_status
same_day_collapse_status
current_source_row_ids
target_source_row_ids
construction_timestamp
```

### 12.4 High-level pseudocode

```python
load frozen Task B configuration
validate required schema and units
construct one auditable Fire-Day per incident-date

for each incident:
    sort Fire-Days chronologically

    for current, next_record in adjacent_pairs(incident_timeline):
        days_to_target = calendar_days(next_record.date - current.date)
        strict_next_day = days_to_target == 1

        personnel_status = validate_personnel_pair(
            current.total_personnel,
            next_record.total_personnel,
            strict_next_day,
        )
        if personnel_status == "eligible":
            next_day_personnel = next_record.total_personnel
        else:
            next_day_personnel = missing

        cost_status = validate_cost_pair(
            current.cumulative_cost,
            next_record.cumulative_cost,
            strict_next_day,
            current.cost_provenance,
            next_record.cost_provenance,
        )
        if cost_status == "eligible_valid_1d":
            daily_cost_usd = (
                next_record.cumulative_cost - current.cumulative_cost
            )
        else:
            daily_cost_usd = missing

        write_target_and_audit_record(...)
```

The final Fire-Day of each incident has no next-day target and must be retained
with an explicit `excluded_no_next_fire_day` status when the full feature table
is released.

---

## 13. Mandatory automated checks

The construction program must stop or emit an explicit failure report when any
hard check fails:

- duplicate `(incident_id, fire_day_date)` keys exist;
- dates are not strictly increasing after same-day collapse;
- a target links two different incident identifiers;
- `target_date <= fire_day_date`;
- an eligible target has `days_to_target != 1`;
- `next_day_personnel` differs from the source `TOTAL_PERSONNEL` on the target
  Fire-Day;
- a personnel difference is accidentally stored as `next_day_personnel`;
- `daily_cost_usd` differs from the two audited cumulative-cost endpoints;
- a negative cumulative-cost revision is clipped to zero and marked eligible;
- an out-of-range value is marked eligible;
- an ineligible target contains a numeric ground-truth value in the public
  evaluation column;
- a missing source value is silently converted to zero;
- a future-derived target or eligibility field appears in model inputs;
- a final incident outcome or non-causal repaired value enters the feature set;
- incident identifiers cross train/validation/test split boundaries;

Soft checks should report, but not silently modify:

- unusually large personnel or cost values;
- zero daily cost after a changed cumulative-cost reporting pattern;
- repeated cumulative-cost values across many reports;
- sharp personnel changes;
- unusually long reporting gaps;
- same-day reports with conflicting target-source values.

---

## 14. Required unit tests

Before full execution, create synthetic tests covering at least:

1. consecutive dates with valid personnel -> next-day level is retained;
2. personnel decrease -> lower next-day level remains valid;
3. personnel difference is not used as the target;
4. consecutive cumulative costs (100{,}000\rightarrow150{,}000) -> daily cost
   is `50,000`;
5. equal cumulative costs -> valid zero daily cost;
6. negative cost revision -> missing target with
   `excluded_negative_cost_revision`;
7. two-day report gap -> no next-day targets;
8. missing current personnel -> personnel target ineligible;
9. missing next-day personnel -> personnel target ineligible;
10. missing cumulative-cost endpoint -> cost target ineligible;
11. personnel valid but cost missing -> personnel remains eligible;
12. cost valid but personnel missing -> cost remains eligible;
13. personnel above 10,000 -> personnel target ineligible;
14. daily cost above USD 50 million -> cost target ineligible;
15. two same-day SitReps -> one deterministic Fire-Day before shifting;
16. next row belongs to another incident -> no cross-incident target;
17. final Fire-Day -> explicit no-next-day status;
18. future-repaired cumulative cost -> cost target ineligible;
19. `TOTAL_AERIAL` remains an input level and is never treated as cumulative;
20. forbidden target columns are rejected by the model-input schema.

---

## 15. Model-input construction and leakage exclusions

### 15.1 Permitted input categories

Subject to temporal provenance, $x_{i,t}$ may contain:

- current ICS-209-PLUS incident status and operational fields;
- current `total_personnel`, `total_aerial`, and cumulative cost;
- backward-looking personnel and cost changes through $t$;
- current fire size, growth, containment, behavior, management, impacts, and
  closures;
- same-day FIRMS and gridMET observations;
- static LANDFIRE and geographic context;
- trailing 3-day and 7-day summaries ending on $t$;
- missingness, match-status, and source-quality indicators known on $t$.

### 15.2 Forbidden input columns

At minimum, exclude:

```text
target_date
next_fire_day_date
days_to_target
days_to_next_report
next_day_personnel
daily_personnel
daily_cost_usd                 # target interval ending at t+1
target_next_day_personnel
target_next_day_daily_cost_usd
eligible_next_day_personnel
eligible_daily_personnel
eligible_daily_cost
personnel_target_status
cost_target_status
resource_action
target_next_day_resource_action
event_final_acres
final containment/outcome fields
critic-only fields
```

Whether `projected_final_im_cost` or another reported forecast can be retained
depends on provenance. It may be used only if it is demonstrably the value
available on Fire-Day $t$, without later backfilling or final-outcome repair.
The default leakage-controlled feature list should exclude it unless that audit
has been completed.

### 15.3 Input schema freeze

Publish an allowlist of prediction-time features for each model family.
A denylist alone is insufficient because new future-derived columns may be
added later without appearing in the original exclusions.

---

## 16. Human audit and source correction

Task B does not require subjective human labeling. Human audit is limited to:

- verifying that source fields have the stated semantics and units;
- reviewing conflicting same-day source reports;
- checking extreme values and negative cost revisions against source records;
- verifying temporal provenance of repaired or smoothed cost values;
- confirming that implementation code matches the frozen specification.

An auditor may select one of the following actions:

| Action | Meaning |
|---|---|
| `accept_source` | Source value and provenance are adequate |
| `exclude_target` | Source evidence is insufficient or non-causal |
| `correct_source_link` | The pipeline linked the wrong source report, without changing the source value |
| `request_source_correction` | A documented source-data correction is required before reconstruction |

Manual replacement of personnel or cost with an expert guess is prohibited.
Every source correction must be documented, preserve the original value, cite
the source record, and trigger complete target regeneration.

---

## 17. Final target record and release freezing

The final target table must preserve both target values and their construction
evidence. Recommended release order is:

1. freeze the Fire-Day construction policy;
2. freeze Task B source-field mappings, thresholds, and status vocabulary;
3. audit cumulative-cost temporal provenance;
4. execute deterministic target construction;
5. run automated validation and synthetic tests;
6. resolve source-link errors through documented corrections;
7. freeze the target table;
8. generate incident-disjoint train/validation/test splits;
9. run model development and evaluation only after the target table is final.

Any later modification to a source value, adjacency rule, upper bound,
eligibility rule, same-day collapse policy, or cost-provenance decision requires
regeneration of benchmark results.

---

## 18. Statistics that must be reported

The manuscript and Data Card should report at least:

- total source-cohort and model-ready Fire-Days;
- number of unique incidents;
- date and geographic coverage;
- number and percentage of strict next-calendar-day pairs;
- eligible counts for personnel and cost separately;
- overlap between the two eligible subsets;
- personnel median, mean, standard deviation, P90, P99, maximum, and zero rate;
- daily-cost median, mean, standard deviation, P90, P99, maximum, and zero rate;
- counts for every personnel and cost target-status category;
- count and magnitude distribution of negative cumulative-cost revisions;
- missing endpoint counts;
- count of cost values excluded by temporal-provenance audit;
- number of same-day multi-report collapses and conflicts;
- target distributions in each incident-disjoint split;
- random split seed and split-specific sample counts.

When reporting cost statistics, use `USD/day` and state explicitly that the
values are increments in reported estimated cumulative cost.

---

## 19. Recommended release files

```text
task_b_labeling/
├── FireRespBench_TaskB_Labeling_Guide.md
├── task_b_target_rules.yaml
├── build_task_b_targets.py
├── tests/
│   └── test_task_b_targets.py
├── task_b_targets.csv
├── task_b_target_status_summary.csv
├── cost_provenance_audit.csv
├── same_day_report_conflicts.csv
├── source_anomalies.csv
├── data_quality_report.md
├── task_b_feature_allowlist.json
└── incident_disjoint_splits.csv
```

---

## 20. Final pre-release checklist

### Fire-Day construction checklist

- [ ] Every row has a unique `(incident_id, fire_day_date)` key.
- [ ] Calendar dates follow a frozen timezone policy.
- [ ] Same-day multiple reports are collapsed deterministically.
- [ ] Source-report counts and identifiers are retained.
- [ ] Incident dates are strictly increasing after collapse.
- [ ] Missing calendar days are not synthesized.

### Personnel-target checklist

- [ ] The source is `TOTAL_PERSONNEL`.
- [ ] The target is the next-day level, not a difference.
- [ ] Both current and target values pass the frozen range check.
- [ ] Only strict next-calendar-day pairs are eligible.
- [ ] Personnel increases and decreases remain valid levels.
- [ ] Ineligible values remain missing rather than zero-filled.

### Daily-cost checklist

- [ ] The source is `EST_IM_COST_TO_DATE`.
- [ ] Both cumulative-cost endpoints are retained for audit.
- [ ] The target equals the next cumulative value minus the current value.
- [ ] Only strict one-day intervals are eligible.
- [ ] Negative revisions are excluded rather than clipped.
- [ ] Missing endpoints are not imputed.
- [ ] The USD 50 million/day upper bound is applied.
- [ ] Cost-field repairs and smoothing pass the temporal-provenance audit.
- [ ] The target is described as an estimated cost increment, not audited
      expenditure.

### Leakage and benchmark checklist

- [ ] Target and eligibility fields are excluded from prediction-time inputs.
- [ ] Final outcomes and non-causal repaired values are excluded.
- [ ] A feature allowlist is published.
- [ ] Personnel and cost eligibility are evaluated independently.
- [ ] Legacy action labels are not treated as current Task B targets.
- [ ] Splits are incident-disjoint.
- [ ] Construction rules and targets are frozen before model development.
- [ ] The manuscript, Data Card, code, and released files describe the same
      Task B protocol.

---

## 21. Relationship to the current workspace

The current workspace contains legacy FireAgentBench/FireRespBench Task B
artifacts that informed this guide:

```text
FireAgentBench/README.md
FireAgentBench/labels/fire_day_response_labels.csv
FireAgentBench/TaskB-2020/README.md
FireAgentBench/TaskB-2020/labels/fire_day_response_labels_2020.csv
FireAgentBench/TaskB-2020/labels/escalation_labels_2020.csv
FireAgentBench/TaskB-2020/make_taskb_2020_subset.py
scripts/build_step2_response_labels.py
experiments/Task_B_new/README.md
iclr_benchmark_FireRespBench_08170210.tex
```

The legacy response-label files use `daily_personnel` for the next-day assigned
personnel level and retain auxiliary `escalate`, `maintain`, and `drawdown`
labels. Under the current FireResBench scope:

- `daily_personnel` should be documented or renamed as
  `next_day_personnel`;
- `daily_cost_usd` remains the one-day cumulative-cost increment;
- resource-action labels are legacy auxiliary artifacts, not Task B targets;
- the primary Task B output contains two regression targets only.

Before the final FireResBench release, the implementation and release artifacts
should be regenerated under a dedicated FireResBench directory so that the
benchmark name, field definitions, target files, feature allowlist, and
manuscript are mutually consistent.
