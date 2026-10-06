# Reviewer B policy: Stage 2 internal pilot

**Policy version:** `internal-pilot-reviewer-b-v1.0.0`  
**Reviewer identity:** `internal_pilot_reviewer_b`  
**Role:** independent secondary reviewer in an internal pilot, simulated with `gpt-5.6-terra` at `high` reasoning effort. This record is not a human-domain-expert annotation and must not be represented as one.

## Evidence boundary

For each `review_case_id`, Reviewer B reads only that row of
`labels/expert_review_queue.csv`. The row is the frozen evidence packet: it
contains the current Fire-Day, source provenance, and features computed from
the preceding observed Fire-Day. The policy never reads later Fire-Days,
Task B targets, downstream model outputs, or any `final_expert_labels.csv`.
`previous_provisional_label` is used only as the already-available preceding
state for the guide's re-escalation exception.

## Decision policy

1. **Defer for material ambiguity.** A case is deferred when containment,
   acres, FIRMS count, or FIRMS FRP is absent, or when
   `same_day_core_conflict=True`. These conditions prevent a defensible
   current-day phase decision. A defer intentionally has an empty
   `reviewed_label`.
2. **Recompute the observable signals.** The policy recomputes rapid growth,
   intensive/active FIRMS, resource surge, drawdown, and low activity from
   the fields in the packet. A cost surge is considered only if
   `cost_interval_status=valid`; a negative revision cannot create a surge.
3. **Independently recheck fire behavior.** In addition to numeric signals,
   the policy applies the guide's frozen vocabulary to
   `gen_fire_behavior` and `fire_behavior_1/2/3`: crown, extreme, running,
   spotting, torching, and wind-driven. This is intentionally independent of
   the supplied `high_severity_behavior` flag, which is treated as an audit
   field rather than conclusive evidence.
4. **Assign one current-day lifecycle state.** The decision order is:
   `mop_up_monitoring` for near-full containment plus fully observed low
   activity and late/drawdown evidence; `rapid_escalation` for observed
   escalation below 80% containment, or renewed activity after an available
   preceding containment/mop-up state; `containment` for clear control
   progress without rapid growth or intense FIRMS; `initial_attack` for a
   small, early, non-escalating fire; and `extended_attack` for the remaining
   sustained active-response cases.
5. **Set action.** Reviewer B accepts only when this independently assigned
   label equals `provisional_lifecycle_label`; otherwise it corrects to the
   independently assigned label. Each record identifies the exact fields
   used and embeds observed values in the rationale. Temporal smoothing is
   not accepted merely because it exists: current and preceding evidence must
   support the assigned state.

The generated CSV is a reproducible simulation artifact for evaluating the
Stage 2 workflow. It is not a release-ready expert-label file.
