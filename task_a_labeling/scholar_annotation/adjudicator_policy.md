# Task A Stage 2 internal-pilot adjudicator policy

Policy version: `internal-pilot-adjudicator-v1.0.0`  
Adjudicator: `internal_pilot_adjudicator`  
Model: `gpt-5.6-sol`  
Reasoning effort: `high`

This artifact documents a subagent simulation used for the FireResBench internal
pilot. It is not a human-domain-expert annotation and must not be described as
scholar verification. Its purpose is to test whether the proposed independent
review and adjudication workflow produces useful corrections before the team
commits to human expert review.

## Evidence boundary

The adjudicator reads only `internal_pilot/adjudication_queue.csv`. Each row
contains the current Fire-Day, explicit changes from the preceding comparable
Fire-Day, source identifiers, and the two independent reviewer records. The
adjudicator does not read the legacy `final_expert_labels.csv`, Task B targets,
later Fire-Days, model predictions, model errors, or final incident outcomes.
The supplied Reviewer A and Reviewer B decisions are considered as competing
interpretations; neither is treated as a vote that determines the outcome.

## Recomputed evidence and conflict handling

The script recomputes the guide's rapid growth, FIRMS, severe fire behavior,
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

`run_adjudicator.py` depends only on the Python standard library. It validates
the full input schema, unique `review_case_id` values, ISO dates, both reviewer
records, exact one-to-one input/output coverage and order, legal actions and
labels, nonempty rationale/evidence fields, and the frozen model metadata. The
program contains no randomness and deterministically rebuilds
`adjudicator_decisions.csv` from the adjudication queue.
