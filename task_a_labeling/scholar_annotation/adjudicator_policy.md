# Task A Stage 2 adjudicator policy

Adjudicator: `adjudicator_c`

This policy defines the independent adjudication procedure for FireResBench
Stage 2. Its purpose is to ensure that reviewer disagreements and deferrals are
resolved consistently under the same evidence boundary used for expert review.

## Evidence boundary

The adjudicator reads only `scholar_annotation/adjudication_queue.csv`. Each row
contains the current Fire-Day, explicit changes from the preceding comparable
Fire-Day, source identifiers, and the two independent reviewer records. The
adjudicator does not read the legacy `final_expert_labels.csv`, Task B targets,
later Fire-Days, model predictions, model errors, or final incident outcomes.
The supplied Reviewer A and Reviewer B decisions are considered as competing
interpretations; neither is treated as a vote that determines the outcome.

## Recomputed evidence and conflict handling

The adjudicator rechecks the guide's rapid growth, FIRMS, severe fire behavior,
resource surge, low activity, and drawdown signals from the evidence packet.
Cost is a surge only when `cost_interval_status=valid`. Fire behavior is matched
against the frozen vocabulary: crown/crowning, extreme, running/runs, spotting,
torching, and wind-driven.

When `same_day_conflict_fields` names a field, that field and changes derived
from it are excluded from the decision. In particular:

- an `acres` conflict makes `new_acres` and relative growth untrusted;
- a `containment` conflict makes containment and containment gain untrusted;
- a `total_personnel` conflict makes personnel changes untrusted;
- a `cumulative_cost_usd` conflict makes cost changes untrusted;
- conflicted behavior fields and `wf_fsr` are not used as positive or negative
  activity evidence.

A missing or conflicted containment value can still be resolved to
`rapid_escalation` when an independent physical signal survives conflict
screening: trusted rapid growth, intense FIRMS, or severe fire behavior. This
implements the guide's allowance for strong observed escalation under missing
containment. Otherwise, a material containment conflict is deferred because
the 80% and 95% phase thresholds cannot be checked.

## Decision hierarchy

1. Missing core evidence is assessed for materiality. Missing fire age does not
   block a decision supported by independent escalation or control evidence;
   missing containment does not block strong physical escalation. If the
   missing field is necessary to distinguish the remaining phases, the case is
   deferred.
2. A return to `rapid_escalation` is resolved when previous containment was at
   least 80% and trusted current evidence shows meaningful new growth, active
   FIRMS, severe behavior, or a resource surge.
3. `mop_up_monitoring` requires trusted containment of at least 95%, fully
   observed low activity, and drawdown, low personnel, or fire age of at least
   seven days.
4. `rapid_escalation` is resolved when trusted current containment is below 80%
   and rapid growth, intense FIRMS, severe behavior, or a valid resource surge
   is present.
5. High containment together with trusted physical activity is deferred when
   the backward evidence does not establish the re-escalation exception. This
   avoids inventing a phase from contradictory current evidence.
6. `containment` requires containment of at least 80% or a gain of at least 20
   percentage points, without trusted rapid growth, intense FIRMS, or severe
   behavior.
7. `initial_attack` requires age at most three days, area at most 1,000 acres,
   containment below 80%, and no trusted escalation signal.
8. `extended_attack` is the residual phase only when no unresolved activity,
   area, or containment conflict could change that conclusion.

Each resolved or deferred record cites concrete field values and the fields
used. A deferred record has no lifecycle label and is intended to be excluded
from supervised evaluation until a human reviewer can inspect the original
source reports or obtain the missing evidence.

## Reproducibility contract

The human adjudicator records one decision for every case in
`adjudication_queue.csv`. Each record uses a legal action and label, includes the
required rationale, and identifies the supporting evidence fields. Validation
and integration code may check the schema, unique `review_case_id` values,
dates, reviewer records, one-to-one coverage, legal values, and required
metadata. It does not populate, infer, or regenerate the adjudicator's
decisions.
