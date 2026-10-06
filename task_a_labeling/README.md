 # Task A lifecycle labeling

The annotation unit is one unique `(incident_id, fire_day_date)` Fire-Day. Stage 1 performs deterministic same-day report collapse, backward-looking feature derivation, 5 km FIRMS aggregation, evidence-signal construction, raw-rule assignment, temporal consistency adjustment, and confidence scoring. Stage 2 preserves two independent human scholar reviewer's decisions and an independent adjudication scholar's decision for every case that lacks reviewer consensus.


## Output semantics

- `processed/fire_day_features_2017to2020.csv` contains temporally valid
  current and backward-looking evidence only. It contains no next-day target,
  final incident outcome, or expert annotation.
- `labels/automatic_prelabels.csv` contains Stage 1 labels and audit fields.
- `labels/expert_review_queue.csv` preserves the cases selected for Stage 2
  review under the protocol plus a deterministic phase- and incident-diverse
  10% audit sample of
  the remaining cases. Each row includes current evidence and
  backward-derived changes.
- `labels/expert_review_case_index.csv` provides an immutable case identifier
  and the exact incident/date filter needed to retrieve the complete incident
  timeline truncated at the reviewed Fire-Day from the processed feature
  table; this prevents later Fire-Days from entering an expert evidence packet.
- `labels/expert_review_template.csv` preserves the 107 column and 30637 cases with the proposed human scholar review schema.
- `scholar_annotation/reviewer_a_decisions.csv` and `scholar_annotation/reviewer_b_decisions.csv` contain the two independent human reviewer teams' annotations.
- `scholar_annotation/adjudicator_decisions.csv` contains decisions for every row where either reviewer deferred or the two proposed labels differed.

- Rows lacking sufficient operational evidence remain auditable but do not receive a fabricated final label. Model inputs must be selected from `metadata/task_a_feature_allowlist.json`; labeling audit fields and review metadata must not enter prediction-time inputs.

The Stage 1 field catalog is in `metadata/task_a_data_dictionary.csv`; final fields are documented in `metadata/stage2_data_dictionary.csv`.


## Task A labeling result

Two reviewer teams independently examined all 30,637 routed cases. Among the 23,950 cases where both supplied a label, exact agreement was 94.64% and Cohen's kappa was 0.923. Row-level adjudication resolved 3,646 of 7,970 cases and deferred 4,324. Sequence review resolved 2,978 cases and deferred 173. The release therefore contains 28,814 supervised-evaluation-eligible labels and 4,497 unresolved rows with blank `final_lifecycle_label`. A final full-sequence audit found no unresolved transition anomalies among the eligible labels.