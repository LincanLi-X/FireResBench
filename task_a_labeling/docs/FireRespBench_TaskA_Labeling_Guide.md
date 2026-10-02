# FireResBench Task A Wildfire Lifecycle Labeling Guide

**Document version:** 1.4-internal-pilot

**Scope:** FireResBench Task A - Wildfire Lifecycle State Understanding 

**Annotation unit:** one `Fire-Day = (incident_id, fire_day_date)` 

**Annotation workflow:** completed Step 1 rule-guided automatic pre-labeling + subagent-reviewed Step 2 internal pilot

---

## 1. Purpose and annotation philosophy

Task A assigns every eligible Fire-Day to one of five wildfire lifecycle states:

1. `initial_attack`
2. `rapid_escalation`
3. `extended_attack`
4. `containment`
5. `mop_up_monitoring`

The source datasets do not provide these five labels directly. FireResBench therefore defines a two-stage annotation process:

- **Step 1 - Automatic pre-labeling:** the research team freezes an explicit rule specification, and a deterministic program applies it to all eligible Fire-Days.
- **Step 2 - Verification and correction:** reviewers inspect the evidence available at each Fire-Day, accept or correct the pre-label, and adjudicate disagreements. The current repository contains a subagent simulation of this stage for internal evaluation; it does not contain completed human domain-scholar labels.

The Stage 1 autolabeling output is treated as a **provisional annotation**. The current pilot labels are explicitly versioned as internal-pilot outputs. A future human-verified release, if conducted, must receive a distinct annotation version.



---

## 2. Data sources used for Task A labeling

Task A labeling uses the following evidence sources:

| Source | Role in labeling |
|---|---|
| ICS-209-PLUS | Incident age, reported area, area growth, containment, fire behavior, personnel, cost, and incident chronology |
| NASA FIRMS / VIIRS | Active-fire count and summed fire radiative power (FRP) within the 5 km incident buffer |
| Stage 2 reviewer annotations | Verification, correction, deferral, and adjudication of automatic pre-labels; currently simulated by subagents for the internal pilot |



---

## 3. Evidence boundary and anti-leakage rule

For incident $i$, Fire-Days are sorted chronologically. When labeling Fire-Day \(t\), the automatic program and reviewers use only:

- the current Fire-Day $t$;
- preceding Fire-Days from the same incident;
- derived changes computed from the most recent preceding comparable Fire-Day, denoted by $t^-$.

They were not given access to:

- reports after Fire-Day $t$;
- next-day personnel or cost targets;
- final incident size or final containment;
- model predictions or model errors;
- labels inferred retrospectively from how the incident ultimately ended.

The review evidence packet therefore truncates the incident timeline at Fire-Day $t$.

---

## 4. Fire-Day construction before labeling

### 4.1 Unique annotation key

Each annotation row must be uniquely identified by:

```text
(incident_id, fire_day_date)
```

No duplicate incident-date rows are allowed.

### 4.2 Multiple reports on the same date

If an incident has multiple ICS-209-PLUS reports on the same calendar date:

1. order them by the most reliable report timestamp;
2. retain the latest valid same-day value for dynamic fields;
3. retain `source_report_count` and source identifiers for auditing;
4. never treat same-day duplicate reports as separate lifecycle transitions.

### 4.3 Chronology and missing values

- Sort by `incident_id`, `fire_day_date`, and the source report timestamp.
- Preserve missingness explicitly; missing is not equal to zero.
- Do not interpolate lifecycle evidence using later Fire-Days.
- Only compute a change when the current and preceding values are comparable and valid.
- Record the actual calendar gap between $t^-$ and $t$.

---

## 5. Required input fields

The implementation should map the source schema to the following canonical variables.

| Canonical variable | Current processed column | Meaning |
|---|---|---|
| `incident_id` | `incident_id` | Unique incident identifier |
| `date` | `fire_day_date` | Calendar date of Fire-Day |
| `fire_age_days` | `fire_age_days` | Days since incident discovery/start |
| `acres` | `acres` | Current reported incident area |
| `new_acres` | `new_acres` | Increase in reported area since \(t^-\) |
| `containment` | `pct_contained_completed` | Reported containment percentage |
| `containment_gain` | derived | Containment at \(t\) minus containment at \(t^-\) |
| `total_personnel` | `total_personnel` | Personnel assigned at the current Fire-Day |
| `personnel_delta` | `personnel_delta` | Current personnel minus previous personnel |
| `personnel_pct_change` | `personnel_pct_change` | Relative personnel change from \(t^-\) |
| `average_daily_cost_usd` | `average_daily_cost_usd` | Cost increment divided by report interval |
| `cost_increment_usd` | `cost_increment_usd` | Non-negative cumulative-cost increase since \(t^-\) |
| `firms_count_5km` | `firms_count_5km` | Same-day active-fire detections within 5 km |
| `firms_frp_sum_5km` | `firms_frp_sum_5km` | Same-day summed FRP within 5 km |
| `wf_fsr` | `wf_fsr` | Available fire-spread-rate indicator |
| `general_fire_behavior` | `gen_fire_behavior` | General reported fire-behavior description |
| `fire_behavior_text` | `fire_behavior_1/2/3` | Reported behavior descriptors |
| `fire_behavior_flags` | `fb_*` columns | Crowning, extreme, running, spotting, torching, and wind-driven flags |

The code must fail with a clear schema error when a required identifier or date field is absent. Optional evidence may be missing, but its missingness must be retained in the audit fields.

---

## 6. Frozen threshold configuration for Step 1

The following values reproduce the current FireRespBench rule specification. Any change requires a new rule version and a complete relabeling run.

| Parameter | Threshold |
|---|---:|
| Early incident age | `3 days` |
| Sustained late-stage age | `7 days` |
| Small-fire area | `1,000 acres` |
| Meaningful new area | `25 acres` |
| Rapid new area | `500 acres` |
| Extreme new area | `2,000 acres` |
| Rapid relative growth | `20%` |
| High containment | `80%` |
| Near-full containment | `95%` |
| Containment gain | `20 percentage points` |
| Low FIRMS count | `<= 1` |
| Active FIRMS count | `>= 10` |
| Intense FIRMS count | `>= 30` |
| Low summed FRP | `<= 5` |
| Active summed FRP | `>= 100` |
| Intense summed FRP | `>= 500` |
| Absolute personnel surge | `>= 25` |
| Relative personnel surge | `>= 50%` |
| Absolute personnel drawdown | `<= -15` |
| Relative personnel drawdown | `<= -20%` |
| Low personnel | `<= 20` |
| High average daily cost | `>= $250,000/day` |
| High cost increment | `>= $250,000` |
| High fire-spread-rate indicator | `>= 0.20` |

These thresholds are operational rules for reproducible pre-annotation, not universal scientific constants. The internal pilot examines their application through independent subagent review and adjudication.

---

## 7. Derived evidence signals

### 7.1 Rapid growth

`rapid_growth = true` when a preceding comparable Fire-Day exists and at least one condition holds:

```text
(new_acres >= 500 AND relative_area_growth >= 0.20)
OR new_acres >= 2,000
OR wf_fsr >= 0.20
```

where:

```text
relative_area_growth = new_acres / max(previous_acres, 1)
```

### 7.2 Intense satellite activity

```text
intense_firms = (firms_count_5km >= 30)
                OR (firms_frp_sum_5km >= 500)
```

### 7.3 Active satellite activity for re-escalation

```text
active_firms = (firms_count_5km >= 10)
               OR (firms_frp_sum_5km >= 100)
```

### 7.4 High-severity fire behavior

`high_severity_behavior = true` when any current report field indicates:

- crowning;
- extreme behavior;
- running;
- spotting;
- torching;
- wind-driven fire.

Matching must use normalized categorical flags when available. Text matching may supplement flags but must use a frozen vocabulary and preserve the matched source phrase.

### 7.5 Resource surge

```text
resource_surge = personnel_delta >= 25
                  OR personnel_pct_change >= 0.50
                  OR average_daily_cost_usd >= 250,000
                  OR cost_increment_usd >= 250,000
```

Cost evidence must be based on a valid cumulative-cost interval. Negative cumulative-cost revisions must be flagged and must not trigger a surge.

### 7.6 Low current fire activity

```text
low_activity = new_acres <= 25
               AND firms_count_5km <= 1
               AND firms_frp_sum_5km <= 5
               AND NOT high_severity_behavior
```

Low activity may be declared only when the required growth and FIRMS evidence is observed. Missing FIRMS or growth values must produce `low_activity_unknown`, not automatic low activity.

### 7.7 Resource drawdown

```text
resource_drawdown = personnel_delta <= -15
                    OR personnel_pct_change <= -0.20
```

### 7.8 Escalation evidence set

```text
escalation_signal = rapid_growth
                    OR intense_firms
                    OR high_severity_behavior
                    OR resource_surge
```

The program must retain every activated signal rather than only a single Boolean result.

---

## 8. Step 1: deterministic automatic pre-labeling

### 8.1 Rule priority

Evaluate provisional phase rules in this fixed order:

```text
mop_up_monitoring
-> containment
-> rapid_escalation
-> initial_attack
-> extended_attack
```

The priority allows strong late-stage evidence to override weak early-stage cues.

### 8.2 Provisional phase rules

#### Rule 1 - `mop_up_monitoring`

Assign when all conditions hold:

```text
containment >= 95%
AND low_activity
AND (
    resource_drawdown
    OR total_personnel <= 20
    OR fire_age_days >= 7
)
```

#### Rule 2 - `containment`

Assign when:

```text
(containment >= 80% OR containment_gain >= 20 percentage points)
AND NOT rapid_growth
AND NOT intense_firms
```

High-severity behavior is retained as an auditable conflict flag even when the above rule produces a containment pre-label.

#### Rule 3 - `rapid_escalation`

Assign when:

```text
containment < 80%
AND escalation_signal
```

If containment is missing, `rapid_escalation` may be provisionally assigned only when at least one strong observed escalation signal exists; the row is marked with `missing_core_evidence` for auditability.

#### Rule 4 - `initial_attack`

Assign when all conditions hold:

```text
fire_age_days <= 3
AND acres <= 1,000
AND containment < 80%
AND NOT escalation_signal
```

The first Fire-Day is not automatically `initial_attack`; it must satisfy the evidence rule.

#### Rule 5 - `extended_attack`

Assign to the remaining operationally active Fire-Days that do not satisfy the preceding four rules.

`extended_attack` is a legitimate lifecycle state, not merely a missing-value fallback. Rows with insufficient evidence to establish operational activity are explicitly flagged rather than silently forced into this class.

---

## 9. Temporal consistency layer

The raw rule label must be generated before temporal adjustment and retained permanently.

### 9.1 Normal lifecycle order

```text
initial_attack
-> rapid_escalation
-> extended_attack
-> containment
-> mop_up_monitoring
```

### 9.2 Forward transitions

- A label may remain unchanged.
- A label may advance by one phase.
- If the raw rule output skips more than one phase, advance only one phase and set:

```text
transition_flag = smoothed_forward
```

### 9.3 Backward transitions

Ordinary backward transitions are held at the preceding final phase:

```text
transition_flag = backward_held
```

### 9.4 Re-escalation exception

A return to `rapid_escalation` is allowed after prior high containment when at least one renewed signal is observed:

```text
meaningful new growth after containment >= 80%
OR active_firms
OR high_severity_behavior
OR resource_surge
```

Set:

```text
transition_flag = confirmed_re_escalation
```

The code must retain both the raw rule label and the temporally adjusted provisional label.

---

## 10. Confidence score and audit prioritization

Confidence is a review-priority indicator, not a calibrated probability.

| Provisional state or transition | Routing confidence |
|---|---:|
| `initial_attack` | `0.82` |
| `extended_attack` | `0.68` |
| `mop_up_monitoring` | `0.90` |
| `rapid_escalation`, one escalation signal | `0.81` |
| `rapid_escalation`, two escalation signals | `0.86` |
| `rapid_escalation`, three or more signals | `0.91` |
| `containment`, one qualifying condition | `0.82` |
| `containment`, high containment plus containment gain | `0.86` |
| `smoothed_forward` | cap at `0.65` |
| `backward_held` | cap at `0.60` |
| `confirmed_re_escalation` | at least `0.80` |

Rows with missing or conflicting core evidence retain an audit-priority flag regardless of their numerical confidence.

---

## 11. Automatic-labeling implementation contract

### 11.1 Separation of roles

1. The research team and domain experts approve this rule document.
2. A coding agent or developer translates the frozen specification into deterministic code.
3. A researcher reviews the implementation line by line and tests synthetic cases.
4. Only the verified program is executed on the full dataset.
5. Neither the coding agent nor a free-form LLM directly assigns final labels.

### 11.2 Required output columns

At minimum, the automatic output must contain:

```text
incident_id
fire_day_date
raw_rule_label
provisional_lifecycle_label
rule_confidence
transition_flag
triggered_rule
triggered_signals
missing_core_evidence
conflicting_evidence
previous_fire_day_date
calendar_gap_days
source_report_ids
rule_version
labeling_timestamp
```

The evidence values used by the rules should either be retained in the same table or linked by an immutable row identifier.

### 11.3 High-level pseudocode

```python
load frozen configuration
validate schema
construct unique Fire-Day rows

for each incident:
    sort Fire-Days chronologically
    previous = None

    for current in incident_timeline:
        features = derive_current_and_backward_looking_evidence(current, previous)
        signals = compute_frozen_signals(features)
        raw_label = apply_priority_rules(features, signals)
        provisional_label, transition_flag = enforce_temporal_rules(
            previous_final_label, raw_label, features, signals
        )
        confidence = compute_routing_confidence(
            provisional_label, signals, transition_flag
        )
        write_audit_record(...)
        previous = current
```

### 11.4 Mandatory automated checks

The program must stop or emit an explicit failure report when any hard check fails:

- row count differs unexpectedly from the eligible input;
- duplicate `(incident_id, fire_day_date)` keys exist;
- dates are not monotonic within an incident;
- any label is missing or outside the five-label vocabulary;
- any unpermitted transition remains after the temporal layer;
- a future-derived column enters the labeling inputs;
- a negative cost revision activates a cost surge;
- missing evidence is silently converted to zero;
- output rule version or input checksum is missing.

### 11.5 Unit tests

Before full execution, create synthetic tests covering at least:

1. early small incident without escalation -> `initial_attack`;
2. rapid area growth -> `rapid_escalation`;
3. intense FIRMS activity -> `rapid_escalation`;
4. severe fire behavior -> `rapid_escalation`;
5. active incident without a current spike -> `extended_attack`;
6. containment >= 80% without renewed growth -> `containment`;
7. containment >= 95%, low activity, and drawdown -> `mop_up_monitoring`;
8. skipped raw transition -> one-stage smoothed transition;
9. unsupported backward transition -> `backward_held`;
10. renewed activity after high containment -> confirmed re-escalation;
11. missing FIRMS values -> not automatically `low_activity`;
12. negative cumulative-cost revision -> no cost-surge trigger.

---

## 12. Stage 2 internal pilot: verification and correction

### 12.1 Reviewer roles

The internal pilot uses three independent roles:

- **Reviewer A:** reviews each queued Fire-Day and records an independent decision using `gpt-5.6-luna` with `high` reasoning effort.
- **Reviewer B:** independently reviews each queued Fire-Day using `gpt-5.6-terra` with `high` reasoning effort.
- **Adjudicator:** resolves reviewer disagreements and deferrals using `gpt-5.6-sol` with `high` reasoning effort, without seeing model results.

Each role is executed by a separate subagent. These roles simulate a review team and must not be represented as people or human experts.

### 12.2 Review queue

The review queue contains:

- all `initial_attack` pre-labels;
- all rows with confidence `<= 0.68`;
- all `smoothed_forward`, `backward_held`, and `confirmed_re_escalation` cases;
- all phase-changing transitions;
- all rows with missing or conflicting core evidence;
- containment within 5 percentage points of the 80% or 95% thresholds;
- growth, FIRMS, personnel, or cost values within 10% of a rule threshold;
- a fixed 10% audit sample from the remaining rows, stratified by provisional phase and incident.

The random sample was generated reproducibly from the frozen sampling seed.

### 12.3 Evidence packet

For each queued Fire-Day, reviewers received:

- the current and preceding Fire-Day observations;
- the incident timeline truncated at the current date;
- original values, units, missingness, and match-status fields;
- ICS-209 source-report identifiers;
- FIRMS count, summed FRP, spatial buffer, and match status;
- derived changes and calendar gaps;
- activated rule clauses and evidence signals;
- raw rule label and temporally adjusted provisional label;
- confidence score and transition flag.

Reviewers did not receive model predictions, next-day targets, later Fire-Days, or final incident outcomes.

### 12.4 Expert phase distinctions

- **Initial attack:** early and comparatively small, without strong escalation evidence.
- **Rapid escalation:** currently increasing in physical fire activity, operational intensity, or resource demand.
- **Extended attack:** sustained active response without a current escalation spike.
- **Containment:** clear control progress without dominant renewed growth.
- **Mop-up/monitoring:** near-complete containment with low activity and late-stage or drawdown evidence.

### 12.5 Allowed review decisions

Each reviewer selects exactly one action:

| Action | Meaning |
|---|---|
| `accept` | Evidence supports the provisional label |
| `correct` | Evidence supports another lifecycle state |
| `defer` | Available evidence is insufficient or internally contradictory |

Every correction and deferral included a concise rationale and one reason code:

```text
threshold_boundary
conflicting_evidence
missing_evidence
temporal_inconsistency
source_error
other
```

Reviewers cited observable Fire-Day evidence rather than inferring unreported conditions.

### 12.6 Independent verification and adjudication

- Reviewer B independently reviews every queued case without access to Reviewer A's output.
- Agreement before adjudication was summarized using raw agreement and Cohen's kappa.
- Every disagreement and any case deferred by either reviewer is sent to the adjudicator using the same evidence boundary and phase definitions.
- The adjudicator documented the final rationale without inspecting downstream model performance.

### 12.7 Sequence revalidation after correction

After each correction, the annotation team:

1. re-checked the complete incident label sequence;
2. identified skipped phases, unsupported backward transitions, and inconsistencies around the corrected row;
3. records any new inconsistency in the sequence review queue;
4. excludes unresolved sequence inconsistencies from supervised evaluation rather than silently overwriting reviewer decisions.

### 12.8 Unresolved cases

Unresolved `defer` cases were excluded from supervised evaluation rather than assigned speculative lifecycle labels merely to achieve full dataset coverage.

---

## 13. Final annotation record

The final annotation schema contains:

```text
incident_id
fire_day_date
raw_rule_label
provisional_lifecycle_label
final_lifecycle_label
rule_confidence
transition_flag
primary_review_action
primary_review_label
primary_reason_code
primary_rationale
secondary_review_label
secondary_agreement_flag
adjudication_required
adjudicated_label
adjudication_rationale
supervised_evaluation_eligible
rule_version
annotation_version
```

Personally identifying reviewer information is stored separately from the public benchmark release.

---

## 14. Version freezing and data splitting

1. The rule specification and automatic-labeling code were frozen.
2. Step 1 was executed with input/output checksums retained.
3. The Step 2 internal pilot was run with three recorded subagent configurations and a distinct pilot annotation version.
4. Pilot annotation counts and agreement statistics were recorded separately from Stage 1 metadata.
5. Incident-disjoint train/validation/test splits were generated after label freezing.
6. Rule and pilot-label versions are kept independent of test-set model performance.

Any later correction must create a new annotation version and require the benchmark results to be regenerated.

---

## 15. Annotation statistics

The annotation record tracks the following release statistics:

- total input and eligible Fire-Days;
- number of unique incidents;
- raw-rule and final-label class distributions;
- number and percentage routed to expert review;
- numbers of `accept`, `correct`, and `defer` decisions;
- correction rates by provisional phase;
- number of re-escalation and temporally smoothed cases;
- number of adjudicated and unresolved cases;
- raw inter-reviewer agreement;
- Cohen's kappa with confidence interval;
- label distribution in each incident-disjoint split;
- rule version, annotation version, random seeds, and file checksums.

### 15.1 Current internal-pilot statistics

The current subagent pilot reviewed 30,637 routed Fire-Days. Among 23,950
cases where both independent reviewers supplied a label, exact agreement was
94.64% and Cohen's kappa was 0.923. Row-level adjudication processed 7,970
cases, resolving 3,646 and deferring 4,324. Sequence adjudication processed
3,151 decisions over two rounds, resolving 2,978 and deferring 173. The final
full-sequence audit found zero unresolved transition anomalies among eligible
labels. Of 33,311 total Fire-Days, 28,814 are eligible for supervised
evaluation and 4,497 remain unresolved with no final label.

These statistics describe a subagent simulation. They must not be presented
as inter-annotator agreement among human domain scholars.
