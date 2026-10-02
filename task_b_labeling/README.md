# FireResBench Task B labeling release (2017--2020)

This directory contains the full FireResBench Task B construction package for CONUS U.S. from 2017-01-01 to 2020-12-31.

## Released targets

- `next_day_personnel`: the `TOTAL_PERSONNEL` level on Fire-Day `t+1` (not difference);
- `daily_cost_usd`: the difference between the as-reported cumulative `EST_IM_COST_TO_DATE` values on `t+1` and `t`.

Personnel and cost eligibility are evaluated independently. Negative cost revisions, increments above USD 50 million, missing endpoints, nonconsecutive reports are retained with explicit status fields. No escalation/maintain/drawdown target is part of Task B.

## Main files

- `processed/fire_res_bench_task_b_features_2017to2020.csv`: current and  backward-looking Fire-Day inputs plus source metadata;
- `labels/task_b_targets_2017to2020.csv`: next-day personnel and daily-cost targets, eligibility flags, endpoint provenance, and exclusion statuses;
- `metadata/task_b_feature_allowlist.json`: fields permitted as predictive inputs;
- `metadata/incident_disjoint_splits.csv`: deterministic 80/10/10 split at the  incident level (seed 2027);
- `metadata/data_quality_report.md`: release counts and validation outcomes;
- `metadata/task_b_data_dictionary.csv`: column-level schema;
- `metadata/task_b_2017to2020_manifest.json` and
  `metadata/checksums.sha256`: version, lineage, counts, and file integrity;
- `source/ics209_as_reported_report_fields_2017to2020.csv`: compact snapshot of  the official raw ICS-209 fields used to restore target endpoints.


## Verification

Model training should join the feature and target tables on `(incident_id, fire_day_date)`, filter by the target-specific eligibility flag, and use only fields listed in the feature allowlist.

