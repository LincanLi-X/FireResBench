# Task A sequence-level adjudication policy

This policy defines the sequence-level adjudication procedure used after
Fire-Day corrections. It ensures that corrected labels remain consistent with
the available incident history and the Task A lifecycle definitions.

## Evidence boundary

The sole input is `scholar_annotation/sequence_review_queue.csv`. For each
anomaly, the adjudicator may use only:

- the candidate current Fire-Day label and its provenance;
- the previous valid lifecycle label and previous Fire-Day date;
- current Fire-Day measurements;
- explicitly supplied changes from the preceding comparable Fire-Day;
- same-day conflict and source-audit fields.

The policy never reads any later Fire-Day, Task B target, downstream model
result, final incident outcome, or evidence outside the queue row. Earlier
review decisions are context, while current and backward-looking observations
remain the basis of the sequence decision.

## Evidence recomputation

The sequence adjudicator independently rechecks rapid growth, active and
intense FIRMS, severe fire behavior, resource surge, low activity, drawdown,
and renewed activity using the frozen Task A thresholds. A cost increase counts only when
`evidence_cost_interval_status=valid`. Severe behavior is matched in current
source text with the frozen crown/crowning, extreme, running/runs, spotting,
torching, and wind-driven vocabulary.

Fields named by `evidence_same_day_conflict_fields` are not trusted. Changes
derived from a conflicted area, containment, personnel, or cumulative-cost
field are also excluded. A physical escalation signal that remains independent
of a containment conflict may still support `rapid_escalation`; otherwise a
material conflict is deferred.

## Sequence decisions

The normal semantic order is:

`initial_attack -> rapid_escalation -> extended_attack -> containment -> mop_up_monitoring`

Sequence review does not mechanically force a one-step transition. A candidate
forward skip is retained when current evidence directly supports it. This is
necessary because incident reports can be separated by several calendar days
and the labeling guide forbids automatically overwriting an expert decision
with temporal smoothing.

The current phase is evaluated in this order:

1. `mop_up_monitoring` requires containment of at least 95%, observed low
   activity, and drawdown, low personnel, or incident age of at least seven
   days.
2. Explicit renewed activity after an already advanced phase supports a return
   to `rapid_escalation`. Meaningful growth, active FIRMS, severe behavior, or a
   valid resource surge can establish the exception. Clear reignition evidence
   is never erased merely to smooth the sequence.
3. Below 80% containment, a current escalation signal supports
   `rapid_escalation`.
4. `containment` requires containment of at least 80% or a gain of at least 20
   percentage points without trusted rapid growth, intense FIRMS, or severe
   behavior.
5. `initial_attack` requires an early, small, below-80%-contained incident with
   no escalation signal.
6. `extended_attack` is the residual current active-response phase when no
   stronger rule or material evidence conflict applies.

When current evidence supports the candidate, the result is resolved to that
candidate even if it skips an unobserved intermediate phase. When another
same-or-later phase is directly supported, the candidate is corrected to that
phase. A row that resembles `initial_attack` after a previous
`rapid_escalation` is corrected to `extended_attack`, because the incident
cannot return to onset and no current control evidence exists.

A regression from `containment` or `mop_up_monitoring` to a non-rapid earlier
phase is deferred when there is no trusted renewed-activity signal. In that
situation, accepting the regression violates sequence semantics, while simply
holding the prior control label would contradict current evidence. The queue
does not contain enough information for a unique correction.

## Reproducibility contract

The human sequence adjudicator records one decision for every case in the
sequence-review queue. Each record uses a legal action and label, includes a
nonempty rationale, and identifies the supporting evidence fields. Validation
and integration code may check the schema, unique `review_case_id` values,
dates, incident chronology, legal values, exact coverage, and required decision
metadata. It does not populate, infer, or regenerate the sequence adjudicator's
decisions.
