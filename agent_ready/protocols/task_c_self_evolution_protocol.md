# Task C: Failure Diagnosis and Self-Evolution Protocol

Task C begins only after a Task A or Task B prediction has been committed and its ground truth has been revealed. The diagnostic input contains the erroneous prediction, decision-time evidence, cited evidence or a concise reasoning summary, the ground truth, and the evaluated system configuration.

## Required output

Every diagnosis must conform to `schemas/task_c_output.schema.json` and provide a `failure_mode`, `responsible_module`, field-level supporting evidence, and one proposed update to the prompt, policy, memory, or routing configuration. The failure-mode and module taxonomies used in an experiment must be versioned and frozen before held-out evaluation.

## Update procedure

1. Construct or annotate diagnostic cases from train/development predictions.
2. Derive an update using development cases only and assign it an immutable `update_version`.
3. Freeze prompts, policies, routing, and reflection memory.
4. Evaluate the frozen pre-update and post-update systems once on the same held-out cases.
5. Report diagnosis performance, module attribution, field-level evidence grounding, post-update task change, and inference usage.

## Contamination controls

- Never add held-out diagnoses, labels, or Critic messages to reflection memory.
- Do not select among repeated updates using test performance.
- Keep prediction-time and post-hoc contexts in separate state objects.
- Record every update source case and verify that its incident is absent from the held-out split.

The release does not claim dense canonical failure annotations for every Fire-Day. Until an expert-validated taxonomy and labels are released, Task C should be reported as a controlled diagnostic protocol or case study rather than as a supervised benchmark equivalent to Tasks A and B.
