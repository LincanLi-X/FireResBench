# Reviewer A policy for the Task A internal pilot

Policy version: `reviewer-a-pilot-v1.0.0`  
Reviewer: `reviewer_a` (`primary_reviewer`)  
Model: `gpt-5.6-luna`  
Reasoning effort: `high`

This is a synthetic Stage 2 primary-review policy for the FireResBench internal pilot. Reviewer A is a subagent simulating the primary-review role and does not represent a human domain scholar. The policy is intentionally frozen in the companion script so that the complete decision file can be regenerated from the review queue.

## Evidence boundary

The only input is `labels/expert_review_queue.csv`. For each row, the reviewer uses the current Fire-Day fields and backward-looking fields already supplied for the same incident: `previous_*`, `previous_fire_day_date`, `calendar_gap_days`, and the current incident history summary. The reviewer does not read `final_expert_labels.csv`, Reviewer B artifacts, Task B targets, model predictions, final incident outcomes, or any report after the current Fire-Day. `provisional_lifecycle_label`, `raw_rule_label`, and their audit fields are treated as Stage 1 claims to be checked, not as evidence of the final answer.

The five allowed lifecycle labels, in operational order, are `initial_attack`, `rapid_escalation`, `extended_attack`, `containment`, and `mop_up_monitoring`.

## Recomputed evidence

The script recomputes evidence from the current and previous fields rather than trusting the Stage 1 signal flags.

* Direct growth is present when `new_acres >= 2,000`, or when `new_acres >= 500` and `relative_area_growth >= 0.20`, or when `wf_fsr >= 0.20`.
* Intense satellite activity is present when `firms_count_5km >= 30` or `firms_frp_sum_5km >= 500`. Active satellite activity uses the lower thresholds of 10 detections or 100 summed FRP.
* Severe behavior is independently detected in the current `gen_fire_behavior`, `fire_behavior_1/2/3`, and `matched_behavior_evidence` fields. The frozen vocabulary is crown/crowning, extreme, running/runs, spotting, torching, and wind-driven. This catches cases where the Stage 1 `high_severity_behavior` flag is inconsistent with the retained source text.
* A personnel surge is `personnel_delta >= 25` or `personnel_pct_change >= 0.50`. A cost surge is considered only when `cost_interval_status=valid` and `cost_increment_usd >= 250,000` or `average_daily_cost_usd >= 250,000`; negative revisions never trigger it.
* Low activity requires a comparable prior area (`area_interval_status` is not `first_fire_day`), observed current FIRMS values, `new_acres <= 25`, at most one detection, summed FRP at most 5, and no severe behavior. Missing growth evidence is not treated as zero.
* Drawdown is `personnel_delta <= -15` or `personnel_pct_change <= -0.20`.

## Decision hierarchy

The reviewer resolves each queue row in this order. A later rule is considered only when the earlier rule does not decide the row.

1. **Defer for missing core evidence.** If `missing_core_evidence=1`, the label is left blank and the rationale names `missing_core_fields`.
2. **Mop-up.** Assign `mop_up_monitoring` when containment is at least 95%, low activity is observed, and at least one of drawdown, current personnel at most 20, or fire age at least 7 is present.
3. **Rapid escalation.** Assign `rapid_escalation` when containment is below 80% and direct growth, intense FIRMS, severe behavior, or a corroborated personnel surge is present. A return after prior containment at least 80% is also rapid when active FIRMS, severe behavior, or a personnel surge is observed. A cost-only surge during low activity is not treated as rapid escalation.
4. **Defer for unresolved high-containment conflict.** If current containment is at least 80% while direct growth, intense FIRMS, severe behavior, or a personnel surge is also present, and neither the mop-up nor renewed-escalation rule decides the row, the evidence is contradictory and the row is deferred.
5. **Containment.** Assign `containment` when containment is at least 80% or containment gain is at least 20 percentage points, with no direct growth, intense FIRMS, severe behavior, or renewed escalation.
6. **Initial attack.** Assign `initial_attack` when fire age is at most 3 days, area is at most 1,000 acres, containment is below 80%, and no escalation evidence is present.
7. **Extended attack.** Assign `extended_attack` when the incident remains operationally active but none of the stronger phase rules is supported.

Same-day core conflicts are deferred unless a decisive current signal supports mop-up, rapid escalation, or initial attack. This keeps a fieldwise same-day disagreement from being silently converted into a confident label. A decision equal to the Stage 1 provisional label is `accept`; a different five-class label is `correct`; a defer has an empty `reviewed_label`.

## Audit contract

`run_reviewer_a.py` reads only the queue and writes only `reviewer_a_decisions.csv`. It checks the required schema, one row per `review_case_id`, exact row-count preservation, ISO dates, chronological order within incident, legal actions and labels, and valid reviewer metadata. The output rationale includes concrete current or previous field values and the `evidence_fields` column records the fields used for that row. The script is deterministic and has no random sampling or network dependency.
