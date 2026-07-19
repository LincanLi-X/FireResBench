# Agent Execution Protocol

This protocol operationalizes the role-agent tuple `A_r = (M, V_r, I_r, S_r, P_r, C_r)` while keeping model choice separate from the benchmark interface.

## Common setup

Before evaluation, freeze the dataset version, split manifest, exact model configuration, prompt version, output schema, communication rounds, and inference budget. Join records only on `(incident_id, fire_day_date)`. Each role receives a separate context and state object.

## Single-agent protocol

1. Load the task-eligible Fire-Day using the task's decision-time fields only.
2. Serialize fields deterministically and apply the task-specific instruction.
3. Commit one structured prediction before loading any target or Critic-only field.
4. Score the committed prediction against the corresponding eligible label.
5. For Task C, pass the committed prediction, its evidence citations, its reasoning summary, and the revealed ground truth to the diagnosis stage.

## Four-role multi-agent protocol

1. Load the Geo, Fire Behavior, and Resource History rows for the same Fire-Day.
2. Run the three decision agents independently. Each returns an `evidence_report` with cited fields and must not see another role's raw CSV row.
3. Deliver the three reports to the Critic Agent. In prediction mode, the Critic receives messages only and cannot load `critic_agent_view.csv`.
4. The Critic may issue one `revision_request`. The addressed agent returns a `revision` using only its original view and received messages.
5. The Critic commits the `final_decision`. All messages must conform to `schemas/agent_message.schema.json`.
6. Only after commitment may the evaluator load eligible ground truth for scoring or Task C diagnosis.

## State and memory

State is private to a role and phase. A case state contains the current key, received message identifiers, optional reflections, and an update version. Evaluation runs must state whether reflection memory is empty or development-derived. Development-derived memory is frozen before test and cannot be changed using held-out labels.

## Fair comparison

For backbone comparisons, use the same prompts, views, orchestration, communication rounds, and output schema. A homogeneous multi-agent configuration uses the same exact model for all four roles. Heterogeneous configurations must be reported separately because backbone specialization and collaboration effects cannot otherwise be disentangled. Report task metrics together with model calls, generated tokens, latency, and failures to produce schema-valid outputs.
