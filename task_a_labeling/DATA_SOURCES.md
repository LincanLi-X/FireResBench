# Data sources and scope

## ICS-209-PLUS

The pipeline reads the harmonized wildfire situation-report table
`ics209-plus-wf_sitreps_1999to2020.csv`. It uses report identifiers,
`REPORT_TO_DATE`, incident location, discovery date, area, containment,
personnel, estimated cumulative cost, fire-spread-rate indicator, and reported
fire-behavior fields. Source-report identifiers and field-level provenance are
retained after same-day collapse.

ICS-209-PLUS reference: St. Denis et al., *Scientific Data* (2023),
https://doi.org/10.1038/s41597-023-01955-0.

## NASA FIRMS

The pipeline reads the annual VIIRS-SNPP United States CSV files for
2017--2020. For each Fire-Day with valid coordinates, it counts same-day FIRMS
detections within 5 km and sums their reported fire radiative power (FRP).
An observed zero is distinct from missing coordinates or unavailable source
coverage.

NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/

## Excluded source families

gridMET and LANDFIRE are not read by the Task A Stage 1 pipeline and do not
contribute to provisional lifecycle labels.

Upstream datasets remain governed by their respective attribution and use
terms. This package does not alter or supersede those terms.

