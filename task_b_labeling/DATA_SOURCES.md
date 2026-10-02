# Data sources and temporal provenance

Task B is constructed from the following workspace inputs:

1. The ICS-209-PLUS wildfire SitRep table supplies incident identifiers,
   report timestamps, response variables, and descriptive fields.
2. Official ICS-209 source files from the ICS-209-PLUS Figshare source archive
   restore the **as-reported** cumulative cost values by
   `INC209R_IDENTIFIER`. Archive article:
   <https://figshare.com/articles/dataset/19858927>; source archive file ID:
   `38772228`.
3. The frozen FireResBench multi-source Fire-Day table supplies aligned FIRMS,
   gridMET, and LANDFIRE-derived covariates for the same model-ready cohort.

The raw archive members used for reproducibility are
`excel/{2016,2017,2018,2019,2020}/SIT209_HISTORY_INCIDENT_209_REPORTS.csv`.
Although the benchmark period begins on 2017-01-01, the 2016 archive member is
included because several reports dated 2017-01-01 are stored at the archive's
year boundary.

All Task B targets are calculated only after same-day reports have been
collapsed deterministically. Target generation never uses a later-than-next-day
report, repaired future cost values, projected final costs, or final incident
outcomes.

