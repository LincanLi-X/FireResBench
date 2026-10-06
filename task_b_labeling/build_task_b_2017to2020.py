#!/usr/bin/env python3
"""Build the core 2017--2020 FireResBench Task B data files.

This self-contained builder implements the Task B construction protocol for the
complete model-ready CONUS cohort. It restores as-reported ICS-209 cumulative
cost and area values, collapses same-day reports, derives backward-looking
features, creates strict next-calendar-day personnel and cost targets, and
writes only the feature table, target table, feature allowlist, and
incident-disjoint splits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


TASK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TASK_DIR.parents[1]

DEFAULT_CLEANED_SITREPS = (
    PROJECT_ROOT / "ics209plus-wildfire" / "ics209-plus-wf_sitreps_1999to2020.csv"
)
DEFAULT_ALIGNED_FEATURES = (
    PROJECT_ROOT
    / "processed"
    / "processed_fire_day_features_2017to2020.csv"
)
DEFAULT_RULES = TASK_DIR / "task_b_target_rules_v1.yaml"
DEFAULT_RAW_SNAPSHOT = (
    TASK_DIR / "source" / "ics209_as_reported_report_fields_2017to2020.csv"
)


ICS_COLUMNS = [
    "acres",
    "addntl_fuel_model",
    "area_closure_flag",
    "cause",
    "complex",
    "complex_name",
    "curr_incident_area",
    "curr_inc_area_uom",
    "cy",
    "discovery_date",
    "dispatch_priority",
    "est_im_cost_to_date",
    "evacuation_in_progress",
    "fatalities",
    "fb_active",
    "fb_backing",
    "fb_creeping",
    "fb_crowning",
    "fb_extreme",
    "fb_flanking",
    "fb_minimal",
    "fb_moderate",
    "fb_running",
    "fb_smoldering",
    "fb_spotting",
    "fb_torching",
    "fb_wind_driven",
    "fire_behavior_1",
    "fire_behavior_2",
    "fire_behavior_3",
    "fire_event_id",
    "fod_poo_latitude",
    "fod_poo_longitude",
    "fuel_model",
    "gacc_priority",
    "gen_fire_behavior",
    "growth_potential",
    "imt_mgmt_org_desc",
    "inc209r_identifier",
    "incident_jurisdiction",
    "incident_name",
    "incident_number",
    "inc_identifier",
    "injuries",
    "injuries_to_date",
    "irwin_id",
    "ll_confidence",
    "ll_update",
    "local_timezone",
    "num_evacuated",
    "nwcg_identifier",
    "pct_contained_completed",
    "pct_perim_to_be_contained",
    "percent_c",
    "percent_fs",
    "percent_m",
    "percent_pzp",
    "poo_county",
    "poo_latitude",
    "poo_longitude",
    "poo_state",
    "poo_state_name",
    "potential",
    "proj_incident_area",
    "prot_unit_id",
    "prot_unit_name",
    "prot_unit_type",
    "report_from_date",
    "road_closure_flag",
    "rpt_evacuations",
    "secndry_fuel_model",
    "start_year",
    "status",
    "str_damaged",
    "str_damaged_comm",
    "str_damaged_res",
    "str_destroyed",
    "str_destroyed_comm",
    "str_destroyed_res",
    "str_threatened",
    "str_threatened_comm",
    "str_threatened_res",
    "suppression_method",
    "suppression_method_fullname",
    "terrain",
    "total_aerial",
    "total_evacuations",
    "total_personnel",
    "trail_closure_flag",
    "unified_command_flag",
    "inctyp_desc",
    "inctyp_abbreviation",
]

EXTERNAL_COLUMNS = [
    "firms_count_1km",
    "firms_frp_sum_1km",
    "firms_frp_mean_1km",
    "firms_confidence_mean_1km",
    "firms_has_detection_1km",
    "firms_count_5km",
    "firms_frp_sum_5km",
    "firms_frp_mean_5km",
    "firms_confidence_mean_5km",
    "firms_has_detection_5km",
    "firms_match_status",
    "gridmet_lat",
    "gridmet_lon",
    "gridmet_match_status",
    "bi",
    "vs",
    "tmmx",
    "tmmn",
    "fm100",
    "fm1000",
    "bi_3d_mean",
    "bi_7d_mean",
    "vs_3d_mean",
    "tmmx_7d_mean",
    "fm100_7d_mean",
    "fm1000_7d_mean",
    "tmmx_c",
    "tmmn_c",
    "tmmx_7d_mean_c",
    "evt_1km_mode",
    "evt_1km_top1_prop",
    "evt_1km_valid_pixel_weight",
    "evt_1km_class_count",
    "evc_1km_mode",
    "evc_1km_top1_prop",
    "evc_1km_valid_pixel_weight",
    "evc_1km_class_count",
    "evh_1km_mode",
    "evh_1km_top1_prop",
    "evh_1km_valid_pixel_weight",
    "evh_1km_class_count",
    "evt_5km_mode",
    "evt_5km_top1_prop",
    "evt_5km_valid_pixel_weight",
    "evt_5km_class_count",
    "evc_5km_mode",
    "evc_5km_top1_prop",
    "evc_5km_valid_pixel_weight",
    "evc_5km_class_count",
    "evh_5km_mode",
    "evh_5km_top1_prop",
    "evh_5km_valid_pixel_weight",
    "evh_5km_class_count",
]

IDENTIFIER_METADATA = {
    "incident_id",
    "incident_name",
    "incident_number",
    "complex_name",
    "inc_identifier",
    "inc209r_identifier",
    "fire_event_id",
    "irwin_id",
    "nwcg_identifier",
    "prot_unit_id",
    "source_row_id",
    "source_row_ids",
    "source_report_ids",
    "personnel_source_report_id",
    "cost_source_report_id",
    "aerial_source_report_id",
    "report_to_timestamp",
    "report_from_date",
    "discovery_date",
}

FORBIDDEN_FEATURE_COLUMNS = {
    "projected_final_im_cost",
    "processed_cumulative_cost_usd",
    "processed_cost_at_raw_source_usd",
    "event_final_acres",
    "target_date",
    "next_fire_day_date",
    "days_to_target",
    "days_to_next_report",
    "next_day_personnel",
    "daily_personnel",
    "daily_cost_usd",
    "target_next_day_personnel",
    "target_next_day_daily_cost_usd",
    "eligible_next_day_personnel",
    "eligible_daily_personnel",
    "eligible_daily_cost",
    "personnel_target_status",
    "cost_target_status",
    "resource_action",
    "target_next_day_resource_action",
}

def normalize_identifier(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").astype("Int64").astype("string")

def require_columns(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")

def parse_rules(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        rules = json.load(handle)
    if rules["personnel"]["use_difference"] is not False:
        raise ValueError("Task B personnel target must be the next-day level")
    if rules["daily_cost"]["allow_future_repair"] is not False:
        raise ValueError("Future-repaired cost is forbidden")
    return rules

def load_raw_snapshot(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, low_memory=False)
    require_columns(
        raw,
        [
            "source_report_id",
            "raw_report_to_date",
            "as_reported_current_area",
            "as_reported_cumulative_cost_usd",
        ],
        "raw provenance snapshot",
    )
    raw["source_report_id"] = raw["source_report_id"].astype("string")
    return raw

def _pipe(values: pd.Series) -> str:
    return "|".join(values.dropna().astype(str).tolist())

def collapse_reports(reports: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collapse report rows to one row per incident-date.

    Reports must already contain restored ``as_reported_*`` fields. Pandas
    ``groupby.last`` resolves every column independently to its latest non-null
    same-day value after deterministic sorting.
    """
    personnel_min = rules["personnel"]["minimum"]
    personnel_max = rules["personnel"]["maximum"]

    frame = reports.copy()
    frame["report_to_timestamp"] = pd.to_datetime(
        frame["REPORT_TO_DATE"], format="mixed", errors="coerce"
    )
    frame["report_from_timestamp"] = pd.to_datetime(
        frame["REPORT_FROM_DATE"], format="mixed", errors="coerce"
    )
    if frame["report_to_timestamp"].isna().any():
        raise ValueError("Unparseable REPORT_TO_DATE values found")
    frame["fire_day_date"] = frame["report_to_timestamp"].dt.normalize()
    frame["source_row_id"] = pd.to_numeric(frame["source_row_id"], errors="raise").astype(int)
    frame["source_report_id"] = normalize_identifier(frame["INC209R_IDENTIFIER"])

    frame = frame.sort_values(
        [
            "INCIDENT_ID",
            "fire_day_date",
            "report_to_timestamp",
            "report_from_timestamp",
            "source_row_id",
        ],
        kind="mergesort",
        na_position="first",
    )
    keys = ["INCIDENT_ID", "fire_day_date"]

    for column in ["TOTAL_PERSONNEL", "TOTAL_AERIAL", "as_reported_cumulative_cost_usd"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["_valid_personnel"] = frame["TOTAL_PERSONNEL"].where(
        frame["TOTAL_PERSONNEL"].between(personnel_min, personnel_max)
    )
    frame["_valid_aerial"] = frame["TOTAL_AERIAL"].where(frame["TOTAL_AERIAL"].ge(0))
    frame["_valid_cost"] = frame["as_reported_cumulative_cost_usd"].where(
        frame["as_reported_cumulative_cost_usd"].ge(0)
    )
    frame["_personnel_source"] = frame["source_report_id"].where(
        frame["_valid_personnel"].notna()
    )
    frame["_aerial_source"] = frame["source_report_id"].where(frame["_valid_aerial"].notna())
    frame["_cost_source"] = frame["source_report_id"].where(frame["_valid_cost"].notna())
    frame["_processed_cost_at_raw_source"] = frame["processed_cumulative_cost_usd"].where(
        frame["_valid_cost"].notna()
    )

    rename_to_lower = {column: column.lower() for column in frame.columns if column.isupper()}
    working = frame.rename(columns=rename_to_lower)
    # Replace processed values with temporally causal, as-reported values.
    working["total_personnel"] = working["_valid_personnel"]
    working["total_aerial"] = working["_valid_aerial"]
    working["est_im_cost_to_date"] = working["_valid_cost"]
    working["curr_incident_area"] = pd.to_numeric(
        working["as_reported_current_area"], errors="coerce"
    )
    working["acres"] = working["curr_incident_area"].where(
        working["curr_inc_area_uom"].eq("Acres")
    )
    working["personnel_source_report_id"] = working["_personnel_source"]
    working["aerial_source_report_id"] = working["_aerial_source"]
    working["cost_source_report_id"] = working["_cost_source"]
    working["processed_cost_at_raw_source_usd"] = working[
        "_processed_cost_at_raw_source"
    ]

    keep = [column for column in ICS_COLUMNS if column in working.columns]
    value_columns = keep + [
        "report_to_timestamp",
        "source_row_id",
        "source_report_id",
        "personnel_source_report_id",
        "aerial_source_report_id",
        "cost_source_report_id",
        "processed_cumulative_cost_usd",
        "processed_cost_at_raw_source_usd",
    ]
    collapsed = working.groupby(["incident_id", "fire_day_date"], sort=False)[value_columns].last()
    collapsed = collapsed.reset_index()

    grouped = working.groupby(["incident_id", "fire_day_date"], sort=False)
    audit = grouped.agg(
        source_report_count=("source_report_id", "size"),
        source_report_ids=("source_report_id", _pipe),
        source_row_ids=("source_row_id", _pipe),
        report_timestamps=("report_to_timestamp", _pipe),
        personnel_values=("total_personnel", _pipe),
        aerial_values=("total_aerial", _pipe),
        as_reported_cost_values=("est_im_cost_to_date", _pipe),
    ).reset_index()
    collapsed = collapsed.merge(
        audit[
            [
                "incident_id",
                "fire_day_date",
                "source_report_count",
                "source_report_ids",
                "source_row_ids",
            ]
        ],
        on=["incident_id", "fire_day_date"],
        how="left",
        validate="one_to_one",
    )
    collapsed["same_day_collapse_status"] = np.where(
        collapsed["source_report_count"].eq(1), "single_report", "latest_valid_fieldwise"
    )

    selected = collapsed[
        [
            "incident_id",
            "fire_day_date",
            "source_row_id",
            "personnel_source_report_id",
            "aerial_source_report_id",
            "cost_source_report_id",
        ]
    ]
    same_day = audit.loc[audit["source_report_count"].gt(1)].merge(
        selected, on=["incident_id", "fire_day_date"], how="left", validate="one_to_one"
    )
    return collapsed, same_day

def derive_history_features(fire_days: pd.DataFrame, rules: dict) -> pd.DataFrame:
    frame = fire_days.sort_values(["incident_id", "fire_day_date"], kind="mergesort").copy()
    group = frame.groupby("incident_id", sort=False)
    previous_date = group["fire_day_date"].shift(1)
    frame["days_since_previous_report"] = (frame["fire_day_date"] - previous_date).dt.days

    previous_personnel = group["total_personnel"].shift(1)
    frame["personnel_delta"] = frame["total_personnel"] - previous_personnel
    frame["personnel_delta_per_day"] = frame["personnel_delta"] / frame["days_since_previous_report"]
    frame["personnel_pct_change"] = frame["personnel_delta"] / previous_personnel.replace(0, np.nan)

    previous_cost = group["est_im_cost_to_date"].shift(1)
    candidate_cost_increment = frame["est_im_cost_to_date"] - previous_cost
    daily_rate = candidate_cost_increment / frame["days_since_previous_report"]
    max_cost = rules["daily_cost"]["maximum_per_day"]
    status_conditions = [
        previous_date.isna(),
        previous_cost.isna(),
        frame["est_im_cost_to_date"].isna(),
        frame["days_since_previous_report"].le(0),
        candidate_cost_increment.lt(0),
        daily_rate.gt(max_cost),
        frame["days_since_previous_report"].eq(1),
    ]
    status_values = [
        "first_fire_day",
        "missing_previous_endpoint",
        "missing_current_endpoint",
        "invalid_calendar_gap",
        "negative_revision",
        "out_of_range",
        "valid_1d",
    ]
    frame["cost_interval_status"] = np.select(
        status_conditions, status_values, default="valid_multiday"
    )
    valid_cost_interval = frame["cost_interval_status"].isin(["valid_1d", "valid_multiday"])
    frame["cost_increment_usd"] = candidate_cost_increment.where(valid_cost_interval)
    frame["average_daily_cost_usd"] = daily_rate.where(valid_cost_interval)

    previous_acres = group["acres"].shift(1)
    acreage_change = frame["acres"] - previous_acres
    valid_acre_interval = (
        frame["acres"].notna()
        & previous_acres.notna()
        & frame["days_since_previous_report"].gt(0)
        & acreage_change.ge(0)
    )
    frame["new_acres"] = acreage_change.where(valid_acre_interval)
    frame["wf_fsr"] = (acreage_change / frame["days_since_previous_report"]).where(
        valid_acre_interval
    )
    frame["acres_interval_status"] = np.select(
        [
            previous_date.isna(),
            previous_acres.isna(),
            frame["acres"].isna(),
            acreage_change.lt(0),
        ],
        ["first_fire_day", "missing_previous", "missing_current", "negative_revision"],
        default="valid",
    )

    discovery = pd.to_datetime(frame["discovery_date"], format="mixed", errors="coerce").dt.normalize()
    frame["fire_age_days"] = (frame["fire_day_date"] - discovery).dt.days
    frame["report_hour_local"] = pd.to_datetime(frame["report_to_timestamp"]).dt.hour
    frame["calendar_month"] = frame["fire_day_date"].dt.month
    frame["calendar_day_of_year"] = frame["fire_day_date"].dt.dayofyear
    frame["invalid_personnel_flag"] = frame["total_personnel"].isna().astype(int)
    frame["invalid_cost_flag"] = frame["est_im_cost_to_date"].isna().astype(int)
    frame["invalid_acres_flag"] = (~frame["acres"].ge(0)).astype(int)
    frame["invalid_containment_flag"] = (
        frame["pct_contained_completed"].notna()
        & ~pd.to_numeric(frame["pct_contained_completed"], errors="coerce").between(0, 100)
    ).astype(int)
    frame["cost_provenance_status"] = np.where(
        frame["est_im_cost_to_date"].notna(), "as_reported", "missing_as_reported"
    )

    trailing_columns = [
        "acres",
        "average_daily_cost_usd",
        "pct_contained_completed",
        "total_personnel",
        "wf_fsr",
    ]
    for days in (3, 7):
        for column in trailing_columns:
            mean_name = f"{column}_mean_{days}d"
            max_name = f"{column}_max_{days}d"
            support_name = f"{column}_support_{days}d"
            frame[mean_name] = np.nan
            frame[max_name] = np.nan
            frame[support_name] = 0
        for _, incident in frame.groupby("incident_id", sort=False):
            ordered = incident.sort_values("fire_day_date")
            values = ordered.set_index("fire_day_date")[trailing_columns].apply(
                pd.to_numeric, errors="coerce"
            )
            roll = values.rolling(f"{days}D", min_periods=1)
            means = roll.mean()
            maxima = roll.max()
            counts = roll.count()
            for column in trailing_columns:
                frame.loc[ordered.index, f"{column}_mean_{days}d"] = means[column].to_numpy()
                frame.loc[ordered.index, f"{column}_max_{days}d"] = maxima[column].to_numpy()
                frame.loc[ordered.index, f"{column}_support_{days}d"] = counts[column].to_numpy()

    core = [
        "acres",
        "pct_contained_completed",
        "total_personnel",
        "total_aerial",
        "est_im_cost_to_date",
    ]
    frame["core_observed_fraction"] = frame[core].notna().mean(axis=1)
    return frame

def construct_targets(fire_days: pd.DataFrame, rules: dict) -> pd.DataFrame:
    frame = fire_days.sort_values(["incident_id", "fire_day_date"], kind="mergesort").copy()
    group = frame.groupby("incident_id", sort=False)
    next_date = group["fire_day_date"].shift(-1)
    days_to_next = (next_date - frame["fire_day_date"]).dt.days
    strict = days_to_next.eq(rules["strict_next_day_gap_days"])

    next_personnel = group["total_personnel"].shift(-1)
    next_cost = group["est_im_cost_to_date"].shift(-1)
    next_personnel_source = group["personnel_source_report_id"].shift(-1)
    next_cost_source = group["cost_source_report_id"].shift(-1)
    next_source_rows = group["source_row_ids"].shift(-1)
    next_source_count = group["source_report_count"].shift(-1)

    pmin = rules["personnel"]["minimum"]
    pmax = rules["personnel"]["maximum"]
    current_personnel_valid = frame["total_personnel"].between(pmin, pmax)
    target_personnel_valid = next_personnel.between(pmin, pmax)
    personnel_status = np.select(
        [
            next_date.isna(),
            ~strict,
            ~current_personnel_valid,
            ~target_personnel_valid,
        ],
        [
            "excluded_no_next_fire_day",
            "excluded_nonconsecutive_report",
            "excluded_invalid_current_personnel",
            "excluded_invalid_target_personnel",
        ],
        default="eligible",
    )
    eligible_personnel = pd.Series(personnel_status, index=frame.index).eq("eligible")

    candidate_cost = next_cost - frame["est_im_cost_to_date"]
    max_cost = rules["daily_cost"]["maximum_per_day"]
    cost_status = np.select(
        [
            next_date.isna(),
            ~strict,
            frame["est_im_cost_to_date"].isna(),
            next_cost.isna(),
            candidate_cost.lt(0),
            candidate_cost.gt(max_cost),
        ],
        [
            "excluded_no_next_fire_day",
            "excluded_nonconsecutive_report",
            "excluded_missing_current_cost",
            "excluded_missing_target_cost",
            "excluded_negative_cost_revision",
            "excluded_cost_above_maximum",
        ],
        default="eligible_valid_1d",
    )
    eligible_cost = pd.Series(cost_status, index=frame.index).eq("eligible_valid_1d")

    result = pd.DataFrame(
        {
            "incident_id": frame["incident_id"],
            "fire_day_date": frame["fire_day_date"].dt.strftime("%Y-%m-%d"),
            "target_date": next_date.where(strict).dt.strftime("%Y-%m-%d"),
            "next_fire_day_date": next_date.dt.strftime("%Y-%m-%d"),
            "days_to_target": days_to_next.where(strict),
            "days_to_next_report": days_to_next,
            "current_personnel": frame["total_personnel"],
            "next_day_personnel": next_personnel.where(eligible_personnel),
            "eligible_next_day_personnel": eligible_personnel.astype(int),
            "personnel_target_status": personnel_status,
            "current_cumulative_cost_usd": frame["est_im_cost_to_date"],
            "target_cumulative_cost_usd": next_cost.where(eligible_cost),
            "daily_cost_usd": candidate_cost.where(eligible_cost),
            "eligible_daily_cost": eligible_cost.astype(int),
            "cost_target_status": cost_status,
            "current_personnel_valid": current_personnel_valid.astype(int),
            "target_personnel_valid": target_personnel_valid.fillna(False).astype(int),
            "cost_increment_usd": candidate_cost.where(strict),
            "cost_interval_status": cost_status,
            "current_cost_provenance_status": frame["cost_provenance_status"],
            "target_cost_provenance_status": group["cost_provenance_status"].shift(-1),
            "source_report_count": frame["source_report_count"],
            "target_source_report_count": next_source_count.where(strict),
            "current_source_report_id": frame["source_report_id"],
            "target_source_report_id": next_cost_source.where(strict),
            "current_personnel_source_report_id": frame["personnel_source_report_id"],
            "target_personnel_source_report_id": next_personnel_source.where(strict),
            "same_day_collapse_status": frame["same_day_collapse_status"],
            "current_source_row_ids": frame["source_row_ids"],
            "target_source_row_ids": next_source_rows.where(strict),
        }
    )
    return result

def make_incident_splits(incident_ids: pd.Series, rules: dict) -> pd.DataFrame:
    unique = np.array(sorted(incident_ids.dropna().astype(str).unique()))
    rng = np.random.default_rng(rules["split"]["seed"])
    shuffled = unique[rng.permutation(len(unique))]
    n_train = int(np.floor(len(shuffled) * rules["split"]["train_fraction"]))
    n_validation = int(np.floor(len(shuffled) * rules["split"]["validation_fraction"]))
    split = np.full(len(shuffled), "test", dtype=object)
    split[:n_train] = "train"
    split[n_train : n_train + n_validation] = "validation"
    return pd.DataFrame({"incident_id": shuffled, "split": split}).sort_values("incident_id")

def validate_release(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    allowlist: dict,
    splits: pd.DataFrame,
    rules: dict,
) -> None:
    keys = ["incident_id", "fire_day_date"]
    if features.duplicated(keys).any() or targets.duplicated(keys).any():
        raise ValueError("Duplicate incident-date keys in release")
    if set(map(tuple, features[keys].astype(str).to_numpy())) != set(
        map(tuple, targets[keys].astype(str).to_numpy())
    ):
        raise ValueError("Feature/target key mismatch")

    dates = pd.to_datetime(features["fire_day_date"], errors="raise")
    start = pd.Timestamp(rules["date_range"]["start"])
    end = pd.Timestamp(rules["date_range"]["end"])
    if not dates.between(start, end).all():
        raise ValueError("Date outside the frozen 2017--2020 Task B scope")
    if dates.min() != start or dates.max() != end:
        raise ValueError("Released date endpoints do not match the frozen scope")

    if targets.loc[
        targets["eligible_next_day_personnel"].eq(1), "days_to_target"
    ].ne(1).any():
        raise ValueError("Eligible personnel target is not strict next-day")
    if targets.loc[targets["eligible_daily_cost"].eq(1), "days_to_target"].ne(1).any():
        raise ValueError("Eligible cost target is not strict next-day")
    if targets.loc[
        targets["eligible_next_day_personnel"].eq(0), "next_day_personnel"
    ].notna().any():
        raise ValueError("Ineligible personnel target contains a value")
    if targets.loc[
        targets["eligible_daily_cost"].eq(0), "daily_cost_usd"
    ].notna().any():
        raise ValueError("Ineligible cost target contains a value")

    eligible_costs = targets.loc[targets["eligible_daily_cost"].eq(1), "daily_cost_usd"]
    if not eligible_costs.between(0, rules["daily_cost"]["maximum_per_day"]).all():
        raise ValueError("Eligible daily cost outside the frozen range")
    if targets.loc[
        targets["cost_target_status"].eq("excluded_negative_cost_revision"),
        "daily_cost_usd",
    ].notna().any():
        raise ValueError("Negative cost revision was exposed as a target")

    forbidden = FORBIDDEN_FEATURE_COLUMNS.intersection(
        allowlist["feature_columns"]
    )
    forbidden |= {
        column
        for column in allowlist["feature_columns"]
        if column.startswith("target_") or column.startswith("next_")
    }
    if forbidden:
        raise ValueError(
            f"Forbidden future/label fields in feature allowlist: {sorted(forbidden)}"
        )
    if set(splits["incident_id"].astype(str)) != set(
        features["incident_id"].astype(str)
    ):
        raise ValueError("Incident split coverage mismatch")
    if splits["incident_id"].duplicated().any():
        raise ValueError("Incident appears in more than one split")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaned-sitreps", type=Path, default=DEFAULT_CLEANED_SITREPS)
    parser.add_argument("--aligned-features", type=Path, default=DEFAULT_ALIGNED_FEATURES)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--raw-snapshot", type=Path, default=DEFAULT_RAW_SNAPSHOT)
    args = parser.parse_args()

    rules = parse_rules(args.rules)
    start = pd.Timestamp(rules["date_range"]["start"])
    end = pd.Timestamp(rules["date_range"]["end"])
    for directory in [TASK_DIR / name for name in ("processed", "labels", "metadata")]:
        directory.mkdir(parents=True, exist_ok=True)

    cleaned = pd.read_csv(args.cleaned_sitreps, low_memory=False)
    require_columns(
        cleaned,
        [
            "Unnamed: 0",
            "INCIDENT_ID",
            "INC209R_IDENTIFIER",
            "REPORT_FROM_DATE",
            "REPORT_TO_DATE",
            "TOTAL_PERSONNEL",
            "TOTAL_AERIAL",
            "EST_IM_COST_TO_DATE",
            "CURR_INC_AREA_UOM",
        ],
        "ICS-209-PLUS wildfire sitreps",
    )
    report_dates = pd.to_datetime(
        cleaned["REPORT_TO_DATE"], format="mixed", errors="coerce"
    ).dt.normalize()
    # Filter by local calendar date. Comparing full timestamps with a midnight
    # endpoint would otherwise discard reports later on 2020-12-31.
    cleaned = cleaned.loc[report_dates.between(start, end)].copy()
    cleaned["source_row_id"] = pd.to_numeric(
        cleaned["Unnamed: 0"], errors="raise"
    ).astype(int)
    cleaned["source_report_id"] = normalize_identifier(
        cleaned["INC209R_IDENTIFIER"]
    )
    cleaned["processed_cumulative_cost_usd"] = pd.to_numeric(
        cleaned["EST_IM_COST_TO_DATE"], errors="coerce"
    )
    report_ids = set(cleaned["source_report_id"].dropna())

    if not args.raw_snapshot.exists():
        raise FileNotFoundError(
            "The as-reported ICS-209 snapshot is required to construct Task B "
            f"targets: {args.raw_snapshot}"
        )
    raw_snapshot = load_raw_snapshot(args.raw_snapshot)
    snapshot_ids = set(raw_snapshot["source_report_id"].dropna())
    if snapshot_ids != report_ids:
        missing = sorted(report_ids - snapshot_ids)[:10]
        extra = sorted(snapshot_ids - report_ids)[:10]
        raise ValueError(
            f"Raw snapshot/report-ID mismatch; missing={missing}, extra={extra}"
        )

    cleaned = cleaned.merge(raw_snapshot, on="source_report_id", how="left", validate="one_to_one")
    if cleaned["raw_record_id"].isna().any():
        raise ValueError("Raw report provenance mapping is incomplete")
    raw_dates = pd.to_datetime(
        cleaned["raw_report_to_date"], format="mixed", errors="coerce"
    ).dt.date
    processed_dates = pd.to_datetime(
        cleaned["REPORT_TO_DATE"], format="mixed", errors="coerce"
    ).dt.date
    raw_date_observed = cleaned["raw_report_to_date"].notna()
    if not raw_dates.loc[raw_date_observed].eq(
        processed_dates.loc[raw_date_observed]
    ).all():
        raise ValueError("Raw and processed report dates disagree")

    fire_days, _ = collapse_reports(cleaned, rules)
    if fire_days.duplicated(["incident_id", "fire_day_date"]).any():
        raise ValueError("Same-day collapse failed to create unique keys")

    aligned = pd.read_csv(args.aligned_features, low_memory=False)
    require_columns(
        aligned,
        ["incident_id", "fire_day_date", *EXTERNAL_COLUMNS],
        "aligned features",
    )
    aligned["fire_day_date"] = pd.to_datetime(aligned["fire_day_date"], errors="coerce")
    aligned = aligned.loc[
        aligned["fire_day_date"].between(start, end),
        ["incident_id", "fire_day_date", *EXTERNAL_COLUMNS],
    ]
    if aligned.duplicated(["incident_id", "fire_day_date"]).any():
        raise ValueError("Duplicate keys in aligned external features")

    cohort_check = fire_days[["incident_id", "fire_day_date"]].merge(
        aligned[["incident_id", "fire_day_date"]],
        on=["incident_id", "fire_day_date"],
        how="outer",
        indicator=True,
    )
    if cohort_check["_merge"].eq("right_only").any():
        raise ValueError("Aligned model-ready cohort contains keys absent from ICS-209 Fire-Days")
    kept_keys = aligned[["incident_id", "fire_day_date"]]
    fire_days = fire_days.merge(
        kept_keys,
        on=["incident_id", "fire_day_date"],
        how="inner",
        validate="one_to_one",
    )
    fire_days = derive_history_features(fire_days, rules)
    fire_days = fire_days.merge(
        aligned,
        on=["incident_id", "fire_day_date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not fire_days["_merge"].eq("both").all():
        raise ValueError("External feature alignment is incomplete")
    fire_days = fire_days.drop(columns="_merge")

    targets = construct_targets(fire_days, rules)
    splits = make_incident_splits(fire_days["incident_id"], rules)

    metadata_columns = [
        "incident_id",
        "fire_day_date",
        "source_row_id",
        "source_row_ids",
        "source_report_id",
        "source_report_ids",
        "source_report_count",
        "personnel_source_report_id",
        "cost_source_report_id",
        "aerial_source_report_id",
        "same_day_collapse_status",
        "report_to_timestamp",
    ]
    ordered_feature_columns = metadata_columns + [
        column
        for column in fire_days.columns
        if column not in metadata_columns
        and column not in FORBIDDEN_FEATURE_COLUMNS
    ]
    features = fire_days[ordered_feature_columns].copy()
    features["fire_day_date"] = features["fire_day_date"].dt.strftime("%Y-%m-%d")
    features["report_to_timestamp"] = pd.to_datetime(
        features["report_to_timestamp"]
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    non_model_metadata = IDENTIFIER_METADATA | {
        "fire_day_date",
        "source_report_count",
        "source_report_ids",
        "source_row_ids",
        "same_day_collapse_status",
    }
    model_feature_columns = [
        column
        for column in features.columns
        if column not in non_model_metadata
        and column not in FORBIDDEN_FEATURE_COLUMNS
    ]
    allowlist = {
        "benchmark_name": rules["benchmark_name"],
        "subset_name": rules["subset_name"],
        "key_columns": ["incident_id", "fire_day_date"],
        "metadata_columns": [
            column for column in features.columns if column not in model_feature_columns
        ],
        "feature_columns": model_feature_columns,
        "excluded_columns": {
            "projected_final_im_cost": "retrospective/final estimate",
            "processed_cumulative_cost_usd": "audit-only cleaned value; replaced by as-reported cost",
            "event_final_acres": "final incident outcome",
            "all target/eligibility fields": "future-derived label leakage",
            "incident/report identifiers and names": "provenance metadata, not predictive inputs",
            "resource_action and escalate/maintain/drawdown": "outside the current Task B scope",
        },
    }
    validate_release(features, targets, allowlist, splits, rules)

    paths = {
        "features": TASK_DIR / "processed" / "fire_res_bench_task_b_features_2017to2020.csv",
        "targets": TASK_DIR / "labels" / "task_b_targets_2017to2020.csv",
        "allowlist": TASK_DIR / "metadata" / "task_b_feature_allowlist.json",
        "splits": TASK_DIR / "metadata" / "incident_disjoint_splits.csv",
    }

    features.to_csv(paths["features"], index=False)
    targets.to_csv(paths["targets"], index=False)
    splits.to_csv(paths["splits"], index=False)
    paths["allowlist"].write_text(
        json.dumps(allowlist, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"FireResBench Task B core data built at: {TASK_DIR}")
    print("Outputs:")
    for path in paths.values():
        print(f"- {path.relative_to(TASK_DIR)}")
    print(f"Fire-Days: {len(features):,}")
    print(f"Incidents: {features['incident_id'].nunique():,}")
    print(
        "Eligible next-day personnel: "
        f"{int(targets['eligible_next_day_personnel'].sum()):,}"
    )
    print(f"Eligible daily cost: {int(targets['eligible_daily_cost'].sum()):,}")


if __name__ == "__main__":
    main()
