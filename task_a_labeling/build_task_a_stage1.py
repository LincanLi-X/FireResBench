#!/usr/bin/env python3
"""Build FireResBench Task A Stage 1 lifecycle annotations.
The implementation follows FireRespBench_TaskA_Labeling_Guide.md version 1.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_ICS = PROJECT_ROOT / "ics209plus-wildfire" / "ics209-plus-wf_sitreps_1999to2020.csv"
DEFAULT_FIRMS_DIR = PROJECT_ROOT / "FIRMS"
DEFAULT_GUIDE = "docs/FireRespBench_TaskA_Labeling_Guide.md"
DEFAULT_CONFIG = PACKAGE_ROOT / "lifecycle_rules_v1.yaml"

SOURCE_FIELDS = {
    "INCIDENT_NAME": "incident_name",
    "INCTYP_DESC": "incident_type",
    "POO_STATE": "poo_state",
    "POO_STATE_NAME": "poo_state_name",
    "POO_LATITUDE": "poo_latitude",
    "POO_LONGITUDE": "poo_longitude",
    "FOD_POO_LATITUDE": "fod_poo_latitude",
    "FOD_POO_LONGITUDE": "fod_poo_longitude",
    "DISCOVERY_DATE": "discovery_date",
    "REPORT_FROM_DATE": "report_from_timestamp",
    "ACRES": "acres",
    "PCT_CONTAINED_COMPLETED": "containment",
    "TOTAL_PERSONNEL": "total_personnel",
    "EST_IM_COST_TO_DATE": "cumulative_cost_usd",
    "WF_FSR": "wf_fsr",
    "GEN_FIRE_BEHAVIOR": "gen_fire_behavior",
    "FIRE_BEHAVIOR_1": "fire_behavior_1",
    "FIRE_BEHAVIOR_2": "fire_behavior_2",
    "FIRE_BEHAVIOR_3": "fire_behavior_3",
    "FB_CROWNING": "fb_crowning",
    "FB_EXTREME": "fb_extreme",
    "FB_RUNNING": "fb_running",
    "FB_SPOTTING": "fb_spotting",
    "FB_TORCHING": "fb_torching",
    "FB_WIND_DRIVEN": "fb_wind_driven",
}

NUMERIC_FIELDS = {
    "poo_latitude",
    "poo_longitude",
    "fod_poo_latitude",
    "fod_poo_longitude",
    "acres",
    "containment",
    "total_personnel",
    "cumulative_cost_usd",
    "wf_fsr",
}

PROVENANCE_FIELDS = [
    "acres",
    "containment",
    "total_personnel",
    "cumulative_cost_usd",
    "wf_fsr",
    "gen_fire_behavior",
    "fire_behavior_1",
    "fire_behavior_2",
    "fire_behavior_3",
]

EVIDENCE_COLUMNS = [
    "incident_id",
    "fire_day_date",
    "incident_name",
    "incident_type",
    "poo_state",
    "poo_state_name",
    "latitude",
    "longitude",
    "discovery_date",
    "fire_age_days",
    "report_to_timestamp",
    "report_from_timestamp",
    "source_report_count",
    "source_report_ids",
    "source_row_ids",
    "primary_source_report_id",
    "same_day_core_conflict",
    "same_day_conflict_fields",
    "previous_fire_day_date",
    "calendar_gap_days",
    "acres",
    "previous_acres",
    "new_acres",
    "relative_area_growth",
    "area_interval_status",
    "containment",
    "previous_containment",
    "containment_gain",
    "total_personnel",
    "previous_total_personnel",
    "personnel_delta",
    "personnel_pct_change",
    "personnel_interval_status",
    "cumulative_cost_usd",
    "previous_cumulative_cost_usd",
    "cost_increment_usd",
    "average_daily_cost_usd",
    "cost_interval_status",
    "wf_fsr",
    "gen_fire_behavior",
    "fire_behavior_1",
    "fire_behavior_2",
    "fire_behavior_3",
    "fb_crowning",
    "fb_extreme",
    "fb_running",
    "fb_spotting",
    "fb_torching",
    "fb_wind_driven",
    "matched_behavior_evidence",
    "firms_count_5km",
    "firms_frp_sum_5km",
    "firms_frp_observation_count_5km",
    "firms_nearest_detection_km",
    "firms_match_status",
]

AUTOMATIC_COLUMNS = [
    "incident_id",
    "fire_day_date",
    "stage1_eligible",
    "stage1_ineligibility_reason",
    "raw_rule_label",
    "provisional_lifecycle_label",
    "rule_confidence",
    "transition_flag",
    "previous_provisional_label",
    "raw_stage_delta",
    "triggered_rule",
    "triggered_signals",
    "missing_core_evidence",
    "missing_core_fields",
    "conflicting_evidence",
    "conflict_reasons",
    "rapid_growth",
    "intense_firms",
    "active_firms",
    "high_severity_behavior",
    "resource_surge",
    "low_activity",
    "low_activity_unknown",
    "resource_drawdown",
    "escalation_signal",
    "review_required",
    "review_queue_reason",
    "review_sampling_stratum",
    "labeling_timestamp",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ics", type=Path, default=DEFAULT_ICS)
    parser.add_argument("--firms-dir", type=Path, default=DEFAULT_FIRMS_DIR)
    parser.add_argument("--guide", type=Path, default=DEFAULT_GUIDE)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--labeling-timestamp", default=None)
    return parser.parse_args()


def read_config(path: Path) -> dict[str, Any]:
    # JSON is valid YAML; using the JSON subset avoids an unnecessary PyYAML
    # dependency and keeps the frozen configuration portable.
    return json.loads(path.read_text(encoding="utf-8"))


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_identifier(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def clean_text_series(series: pd.Series) -> pd.Series:
    result = series.astype("string").str.strip()
    return result.mask(result.eq(""))


def last_valid(
    group: pd.DataFrame, source_column: str, canonical_column: str
) -> tuple[Any, str]:
    values = group[source_column]
    if canonical_column in NUMERIC_FIELDS:
        valid = pd.to_numeric(values, errors="coerce").notna()
    else:
        valid = clean_text_series(values).notna()
    if not valid.any():
        return (np.nan, "")
    row = group.loc[valid].iloc[-1]
    value = row[source_column]
    if canonical_column in NUMERIC_FIELDS:
        value = float(pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0])
    else:
        value = str(value).strip()
    return value, normalize_identifier(row["INC209R_IDENTIFIER"])


def distinct_valid_values(
    group: pd.DataFrame, source_column: str, canonical_column: str
) -> list[Any]:
    if canonical_column in NUMERIC_FIELDS:
        values = pd.to_numeric(group[source_column], errors="coerce").dropna().tolist()
        normalized = sorted({round(float(v), 10) for v in values})
    else:
        values = clean_text_series(group[source_column]).dropna().tolist()
        normalized = sorted(set(str(v) for v in values))
    return normalized


def load_and_collapse_ics(
    path: Path,
    start_date: str,
    end_date: str,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    required = {
        "INCIDENT_ID",
        "INC209R_IDENTIFIER",
        "REPORT_TO_DATE",
        *SOURCE_FIELDS.keys(),
    }
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing = sorted(required - set(header))
    if missing:
        raise ValueError(f"ICS-209-PLUS schema is missing required fields: {missing}")

    raw = pd.read_csv(path, usecols=sorted(required), low_memory=False)
    raw["_source_row_id"] = np.arange(len(raw), dtype=np.int64)
    raw["_report_to"] = pd.to_datetime(raw["REPORT_TO_DATE"], format="mixed", errors="coerce")
    raw["_fire_day_date"] = raw["_report_to"].dt.normalize()
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    raw = raw.loc[raw["_fire_day_date"].between(start, end)].copy()
    if raw.empty:
        raise RuntimeError("No ICS-209-PLUS reports fall within the requested date range")

    raw["_report_from"] = pd.to_datetime(raw["REPORT_FROM_DATE"], format="mixed", errors="coerce")
    raw["_incident_id"] = clean_text_series(raw["INCIDENT_ID"])
    invalid_identity = raw["_incident_id"].isna()
    if invalid_identity.any():
        raw = raw.loc[~invalid_identity].copy()

    raw = raw.sort_values(
        ["_incident_id", "_fire_day_date", "_report_to", "_report_from", "_source_row_id"],
        kind="mergesort",
        na_position="first",
    )

    records: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    conflict_fields = {
        "ACRES",
        "PCT_CONTAINED_COMPLETED",
        "TOTAL_PERSONNEL",
        "EST_IM_COST_TO_DATE",
        "WF_FSR",
        "GEN_FIRE_BEHAVIOR",
        "FIRE_BEHAVIOR_1",
        "FIRE_BEHAVIOR_2",
        "FIRE_BEHAVIOR_3",
    }

    for (incident_id, fire_day), group in raw.groupby(
        ["_incident_id", "_fire_day_date"], sort=False, dropna=False
    ):
        report_ids = [
            normalize_identifier(v)
            for v in group["INC209R_IDENTIFIER"].tolist()
            if normalize_identifier(v)
        ]
        source_rows = [int(v) for v in group["_source_row_id"].tolist()]
        latest = group.iloc[-1]
        record: dict[str, Any] = {
            "incident_id": str(incident_id),
            "fire_day_date": pd.Timestamp(fire_day).strftime("%Y-%m-%d"),
            "report_to_timestamp": latest["_report_to"].isoformat(sep=" "),
            "source_report_count": int(len(group)),
            "source_report_ids": stable_json(report_ids),
            "source_row_ids": stable_json(source_rows),
            "primary_source_report_id": normalize_identifier(latest["INC209R_IDENTIFIER"]),
        }
        current_conflicts: list[str] = []
        for source, canonical in SOURCE_FIELDS.items():
            value, source_id = last_valid(group, source, canonical)
            record[canonical] = value
            if canonical in PROVENANCE_FIELDS:
                record[f"{canonical}_source_report_id"] = source_id
            if source in conflict_fields:
                values = distinct_valid_values(group, source, canonical)
                if len(values) > 1:
                    current_conflicts.append(canonical)
                    conflicts.append(
                        {
                            "incident_id": str(incident_id),
                            "fire_day_date": pd.Timestamp(fire_day).strftime("%Y-%m-%d"),
                            "field": canonical,
                            "distinct_values": stable_json(values),
                            "source_report_ids": stable_json(report_ids),
                            "resolution": "latest_valid_same_day_value",
                        }
                    )
        record["same_day_core_conflict"] = bool(current_conflicts)
        record["same_day_conflict_fields"] = stable_json(current_conflicts)
        records.append(record)

    collapsed = pd.DataFrame(records)
    conflict_df = pd.DataFrame(
        conflicts,
        columns=[
            "incident_id",
            "fire_day_date",
            "field",
            "distinct_values",
            "source_report_ids",
            "resolution",
        ],
    )

    collapsed["latitude"] = pd.to_numeric(collapsed["poo_latitude"], errors="coerce").fillna(
        pd.to_numeric(collapsed["fod_poo_latitude"], errors="coerce")
    )
    collapsed["longitude"] = pd.to_numeric(collapsed["poo_longitude"], errors="coerce").fillna(
        pd.to_numeric(collapsed["fod_poo_longitude"], errors="coerce")
    )
    collapsed["poo_state"] = clean_text_series(collapsed["poo_state"]).str.upper()
    conus_states = set(config["conus_states"])
    valid_state = collapsed["poo_state"].isin(conus_states)
    valid_coord = collapsed["latitude"].between(24.0, 50.0) & collapsed["longitude"].between(-125.0, -66.0)

    exclusion_reason = pd.Series("", index=collapsed.index, dtype="string")
    exclusion_reason.loc[collapsed["poo_state"].isna()] = "missing_state"
    exclusion_reason.loc[collapsed["poo_state"].notna() & ~valid_state] = "non_conus_state"
    exclusion_reason.loc[valid_state & ~valid_coord] = "missing_or_invalid_coordinate"
    included = valid_state & valid_coord

    exclusions = collapsed.loc[~included, [
        "incident_id",
        "fire_day_date",
        "poo_state",
        "latitude",
        "longitude",
        "source_report_count",
        "source_report_ids",
    ]].copy()
    exclusions["exclusion_reason"] = exclusion_reason.loc[~included].to_numpy()

    cohort = collapsed.loc[included].copy().reset_index(drop=True)
    cohort = cohort.sort_values(["incident_id", "fire_day_date"], kind="mergesort").reset_index(drop=True)
    stats = {
        "source_reports_in_date_range": int(len(raw)),
        "source_fire_days_after_same_day_collapse": int(len(collapsed)),
        "included_conus_fire_days": int(len(cohort)),
        "included_incidents": int(cohort["incident_id"].nunique()),
        "excluded_fire_days": int(len(exclusions)),
        "same_day_multi_report_fire_days": int((collapsed["source_report_count"] > 1).sum()),
        "same_day_field_conflicts": int(len(conflict_df)),
    }
    return cohort, exclusions, conflict_df, stats


def load_firms_by_date(firms_dir: Path, years: Iterable[int]) -> tuple[dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]], list[Path], dict[str, int]]:
    frames: list[pd.DataFrame] = []
    paths: list[Path] = []
    source_rows = 0
    for year in years:
        path = firms_dir / f"viirs-snpp_{year}_United_States.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing FIRMS source file: {path}")
        frame = pd.read_csv(path, usecols=["latitude", "longitude", "acq_date", "frp"], low_memory=False)
        source_rows += len(frame)
        frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
        frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
        frame["frp"] = pd.to_numeric(frame["frp"], errors="coerce")
        frame["acq_date"] = pd.to_datetime(frame["acq_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        frame = frame.dropna(subset=["latitude", "longitude", "acq_date"])
        frames.append(frame)
        paths.append(path)
    firms = pd.concat(frames, ignore_index=True)
    by_date: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for date, group in firms.groupby("acq_date", sort=False):
        by_date[str(date)] = (
            group["latitude"].to_numpy(dtype=float),
            group["longitude"].to_numpy(dtype=float),
            group["frp"].to_numpy(dtype=float),
        )
    stats = {
        "firms_source_rows": int(source_rows),
        "firms_valid_rows": int(len(firms)),
        "firms_dates_with_detections": int(firms["acq_date"].nunique()),
    }
    return by_date, paths, stats


def haversine_km(lat: float, lon: float, other_lat: np.ndarray, other_lon: np.ndarray) -> np.ndarray:
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = np.radians(other_lat)
    lon2 = np.radians(other_lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 6371.0088 * 2.0 * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def align_firms(
    fire_days: pd.DataFrame,
    firms_by_date: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    radius_km: float,
    available_years: set[int],
) -> pd.DataFrame:
    count = np.zeros(len(fire_days), dtype=np.int64)
    frp_sum = np.zeros(len(fire_days), dtype=float)
    frp_count = np.zeros(len(fire_days), dtype=np.int64)
    nearest = np.full(len(fire_days), np.nan, dtype=float)
    status = np.full(len(fire_days), "observed_no_detections", dtype=object)

    for index, row in fire_days.iterrows():
        date = str(row["fire_day_date"])
        year = int(date[:4])
        lat = row["latitude"]
        lon = row["longitude"]
        if pd.isna(lat) or pd.isna(lon):
            status[index] = "missing_coordinate"
            count[index] = -1
            frp_sum[index] = np.nan
            frp_count[index] = -1
            continue
        if year not in available_years:
            status[index] = "source_year_unavailable"
            count[index] = -1
            frp_sum[index] = np.nan
            frp_count[index] = -1
            continue
        observations = firms_by_date.get(date)
        if observations is None:
            continue
        latitudes, longitudes, frp = observations
        distances = haversine_km(float(lat), float(lon), latitudes, longitudes)
        within = distances <= radius_km
        if within.any():
            count[index] = int(within.sum())
            valid_frp = frp[within & np.isfinite(frp)]
            frp_sum[index] = float(valid_frp.sum()) if len(valid_frp) else 0.0
            frp_count[index] = int(len(valid_frp))
            nearest[index] = float(distances[within].min())
            status[index] = "matched_detections"

    result = fire_days.copy()
    result["firms_count_5km"] = pd.Series(count).mask(count < 0)
    result["firms_frp_sum_5km"] = frp_sum
    result["firms_frp_observation_count_5km"] = pd.Series(frp_count).mask(frp_count < 0)
    result["firms_nearest_detection_km"] = nearest
    result["firms_match_status"] = status
    return result


def as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def parse_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def derive_behavior_evidence(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    output = frame.copy()
    fields = ["gen_fire_behavior", "fire_behavior_1", "fire_behavior_2", "fire_behavior_3"]
    vocab = config["behavior_vocabulary"]
    matches: list[str] = []
    flags: dict[str, list[bool]] = {key: [] for key in vocab}
    for _, row in output.iterrows():
        row_matches: list[str] = []
        row_flags: dict[str, bool] = {}
        texts = [(field, "" if pd.isna(row[field]) else str(row[field])) for field in fields]
        for category, terms in vocab.items():
            explicit = parse_bool(row.get(f"fb_{category}", False))
            found = explicit
            if explicit:
                row_matches.append(f"fb_{category}=true")
            for field, text in texts:
                lower = f" {text.lower()} "
                if any(term.lower() in lower for term in terms):
                    found = True
                    row_matches.append(f"{field}:{text}")
            row_flags[category] = found
        for category in vocab:
            flags[category].append(row_flags[category])
        matches.append(stable_json(sorted(set(row_matches))))
    for category, values in flags.items():
        output[f"behavior_signal_{category}"] = values
    output["matched_behavior_evidence"] = matches
    return output


def derive_history(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    result["fire_day_date"] = pd.to_datetime(result["fire_day_date"])
    result["discovery_date"] = pd.to_datetime(
        result["discovery_date"], format="mixed", errors="coerce"
    ).dt.normalize()
    result = result.sort_values(["incident_id", "fire_day_date"], kind="mergesort").reset_index(drop=True)
    group = result.groupby("incident_id", sort=False)

    result["previous_fire_day_date"] = group["fire_day_date"].shift(1)
    result["calendar_gap_days"] = (result["fire_day_date"] - result["previous_fire_day_date"]).dt.days
    result["fire_age_days"] = (result["fire_day_date"] - result["discovery_date"]).dt.days
    result.loc[result["fire_age_days"] < 0, "fire_age_days"] = np.nan

    for field in ["acres", "containment", "total_personnel", "cumulative_cost_usd", "wf_fsr"]:
        result[field] = as_numeric(result[field])

    result["previous_acres"] = group["acres"].shift(1)
    result["new_acres"] = result["acres"] - result["previous_acres"]
    result["relative_area_growth"] = result["new_acres"] / result["previous_acres"].clip(lower=1)
    result["area_interval_status"] = np.select(
        [
            result["previous_fire_day_date"].isna(),
            result["acres"].isna(),
            result["previous_acres"].isna(),
            result["new_acres"].lt(0),
        ],
        ["first_fire_day", "missing_current_area", "missing_previous_area", "negative_area_revision"],
        default="valid",
    )

    result["previous_containment"] = group["containment"].shift(1)
    result["containment_gain"] = result["containment"] - result["previous_containment"]
    invalid_containment = ~result["containment"].between(0, 100) & result["containment"].notna()
    result.loc[invalid_containment, ["containment", "containment_gain"]] = np.nan

    result["previous_total_personnel"] = group["total_personnel"].shift(1)
    valid_personnel = result["total_personnel"].between(0, config["thresholds"]["max_personnel"])
    previous_personnel_valid = result["previous_total_personnel"].between(0, config["thresholds"]["max_personnel"])
    result["personnel_delta"] = (result["total_personnel"] - result["previous_total_personnel"]).where(
        valid_personnel & previous_personnel_valid
    )
    result["personnel_pct_change"] = (
        result["personnel_delta"] / result["previous_total_personnel"].where(result["previous_total_personnel"] > 0)
    )
    result["personnel_interval_status"] = np.select(
        [
            result["previous_fire_day_date"].isna(),
            ~valid_personnel,
            ~previous_personnel_valid,
            result["previous_total_personnel"].eq(0),
        ],
        ["first_fire_day", "invalid_current_personnel", "invalid_previous_personnel", "zero_previous_personnel"],
        default="valid",
    )

    result["previous_cumulative_cost_usd"] = group["cumulative_cost_usd"].shift(1)
    raw_cost_increment = result["cumulative_cost_usd"] - result["previous_cumulative_cost_usd"]
    valid_cost_endpoints = result["cumulative_cost_usd"].ge(0) & result["previous_cumulative_cost_usd"].ge(0)
    positive_gap = result["calendar_gap_days"].gt(0)
    nonnegative_increment = raw_cost_increment.ge(0)
    daily_rate = raw_cost_increment / result["calendar_gap_days"]
    within_rate = daily_rate.le(config["thresholds"]["max_daily_cost_usd"])
    valid_cost_interval = valid_cost_endpoints & positive_gap & nonnegative_increment & within_rate
    result["cost_increment_usd"] = raw_cost_increment.where(valid_cost_interval)
    result["average_daily_cost_usd"] = daily_rate.where(valid_cost_interval)
    result["cost_interval_status"] = np.select(
        [
            result["previous_fire_day_date"].isna(),
            result["previous_cumulative_cost_usd"].isna(),
            result["cumulative_cost_usd"].isna(),
            ~positive_gap,
            raw_cost_increment.lt(0),
            daily_rate.gt(config["thresholds"]["max_daily_cost_usd"]),
        ],
        [
            "first_fire_day",
            "missing_previous_endpoint",
            "missing_current_endpoint",
            "invalid_calendar_gap",
            "negative_revision",
            "out_of_range",
        ],
        default="valid",
    )

    result["fire_day_date"] = result["fire_day_date"].dt.strftime("%Y-%m-%d")
    result["previous_fire_day_date"] = result["previous_fire_day_date"].dt.strftime("%Y-%m-%d")
    result["discovery_date"] = result["discovery_date"].dt.strftime("%Y-%m-%d")
    return result


def observed(value: Any) -> bool:
    return not pd.isna(value)


def make_evidence(row: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    t = config["thresholds"]
    growth_valid = row.get("area_interval_status") == "valid"
    new_acres = row.get("new_acres")
    relative_growth = row.get("relative_area_growth")
    wf_fsr = row.get("wf_fsr")
    rapid_growth = bool(
        growth_valid
        and (
            (
                observed(new_acres)
                and observed(relative_growth)
                and new_acres >= t["rapid_new_acres"]
                and relative_growth >= t["rapid_growth_ratio"]
            )
            or (observed(new_acres) and new_acres >= t["extreme_new_acres"])
            or (observed(wf_fsr) and wf_fsr >= t["high_wf_fsr"])
        )
    )
    firms_observed = row.get("firms_match_status") in {"matched_detections", "observed_no_detections"}
    firms_count = row.get("firms_count_5km")
    firms_frp = row.get("firms_frp_sum_5km")
    intense_firms = bool(
        firms_observed
        and ((observed(firms_count) and firms_count >= t["intense_firms_count"]) or (observed(firms_frp) and firms_frp >= t["intense_firms_frp_sum"]))
    )
    active_firms = bool(
        firms_observed
        and ((observed(firms_count) and firms_count >= t["active_firms_count"]) or (observed(firms_frp) and firms_frp >= t["active_firms_frp_sum"]))
    )
    behavior_columns = [c for c in row.index if c.startswith("behavior_signal_")]
    high_severity_behavior = any(bool(row.get(c, False)) for c in behavior_columns)
    personnel_delta = row.get("personnel_delta")
    personnel_pct = row.get("personnel_pct_change")
    average_cost = row.get("average_daily_cost_usd")
    cost_increment = row.get("cost_increment_usd")
    resource_surge = bool(
        (observed(personnel_delta) and personnel_delta >= t["personnel_surge_abs"])
        or (observed(personnel_pct) and personnel_pct >= t["personnel_surge_ratio"])
        or (row.get("cost_interval_status") == "valid" and observed(average_cost) and average_cost >= t["high_daily_cost_usd"])
        or (row.get("cost_interval_status") == "valid" and observed(cost_increment) and cost_increment >= t["high_cost_increment_usd"])
    )
    resource_drawdown = bool(
        (observed(personnel_delta) and personnel_delta <= t["personnel_drawdown_abs"])
        or (observed(personnel_pct) and personnel_pct <= t["personnel_drawdown_ratio"])
    )
    growth_observed = growth_valid and observed(new_acres)
    low_activity_unknown = not (growth_observed and firms_observed)
    low_activity = bool(
        not low_activity_unknown
        and new_acres <= t["meaningful_new_acres"]
        and firms_count <= t["low_firms_count"]
        and firms_frp <= t["low_firms_frp_sum"]
        and not high_severity_behavior
    )
    escalation_signal = rapid_growth or intense_firms or high_severity_behavior or resource_surge
    triggered = []
    for name, value in [
        ("rapid_growth", rapid_growth),
        ("intense_firms", intense_firms),
        ("active_firms", active_firms),
        ("high_severity_behavior", high_severity_behavior),
        ("resource_surge", resource_surge),
        ("low_activity", low_activity),
        ("low_activity_unknown", low_activity_unknown),
        ("resource_drawdown", resource_drawdown),
    ]:
        if value:
            triggered.append(name)
    return {
        "rapid_growth": rapid_growth,
        "intense_firms": intense_firms,
        "active_firms": active_firms,
        "high_severity_behavior": high_severity_behavior,
        "resource_surge": resource_surge,
        "low_activity": low_activity,
        "low_activity_unknown": low_activity_unknown,
        "resource_drawdown": resource_drawdown,
        "escalation_signal": escalation_signal,
        "triggered_signals": triggered,
    }


def classify_raw(row: pd.Series, evidence: dict[str, Any], config: dict[str, Any]) -> tuple[str, str]:
    t = config["thresholds"]
    containment = row.get("containment")
    containment_gain = row.get("containment_gain")
    age = row.get("fire_age_days")
    acres = row.get("acres")
    personnel = row.get("total_personnel")

    mop_up = bool(
        observed(containment)
        and containment >= t["near_full_containment_pct"]
        and evidence["low_activity"]
        and (
            evidence["resource_drawdown"]
            or (observed(personnel) and personnel <= t["low_personnel"])
            or (observed(age) and age >= t["late_stage_age_days"])
        )
    )
    if mop_up:
        return "mop_up_monitoring", "rule_mop_up_monitoring"

    containment_rule = bool(
        ((observed(containment) and containment >= t["high_containment_pct"]) or (observed(containment_gain) and containment_gain >= t["containment_gain_pct"]))
        and not evidence["rapid_growth"]
        and not evidence["intense_firms"]
    )
    if containment_rule:
        return "containment", "rule_containment"

    rapid = bool(
        evidence["escalation_signal"]
        and ((observed(containment) and containment < t["high_containment_pct"]) or not observed(containment))
    )
    if rapid:
        return "rapid_escalation", "rule_rapid_escalation"

    initial = bool(
        observed(age)
        and age <= t["early_age_days"]
        and observed(acres)
        and acres <= t["small_fire_acres"]
        and observed(containment)
        and containment < t["high_containment_pct"]
        and not evidence["escalation_signal"]
    )
    if initial:
        return "initial_attack", "rule_initial_attack"

    operational_evidence = any(
        [
            observed(acres),
            observed(containment),
            observed(personnel),
            observed(row.get("cumulative_cost_usd")),
            bool(str(row.get("gen_fire_behavior", "")).strip()) and not pd.isna(row.get("gen_fire_behavior")),
            observed(row.get("firms_count_5km")) and row.get("firms_count_5km") > 0,
        ]
    )
    if operational_evidence:
        return "extended_attack", "rule_extended_attack"
    return "", "insufficient_operational_evidence"


def temporal_adjust(
    previous_label: str,
    raw_label: str,
    evidence: dict[str, Any],
    row: pd.Series,
    prior_high_containment: bool,
    config: dict[str, Any],
) -> tuple[str, str, Any]:
    order = config["temporal_order"]
    if not raw_label:
        return "", "not_labeled", np.nan
    if not previous_label:
        return raw_label, "start", np.nan
    delta = order[raw_label] - order[previous_label]
    if delta == 0:
        return raw_label, "same_stage", delta
    if delta == 1:
        return raw_label, "forward_transition", delta
    if delta > 1:
        inverse = {value: key for key, value in order.items()}
        return inverse[order[previous_label] + 1], "smoothed_forward", delta

    meaningful_growth = bool(
        row.get("area_interval_status") == "valid"
        and observed(row.get("new_acres"))
        and row.get("new_acres") > config["thresholds"]["meaningful_new_acres"]
    )
    renewed = meaningful_growth or evidence["active_firms"] or evidence["high_severity_behavior"] or evidence["resource_surge"]
    if raw_label == "rapid_escalation" and prior_high_containment and renewed:
        return raw_label, "confirmed_re_escalation", delta
    return previous_label, "backward_held", delta


def confidence_for(
    raw_label: str,
    transition_flag: str,
    evidence: dict[str, Any],
    row: pd.Series,
    config: dict[str, Any],
) -> float | None:
    if not raw_label:
        return None
    c = config["confidence"]
    t = config["thresholds"]
    if raw_label == "initial_attack":
        value = c["initial_attack"]
    elif raw_label == "extended_attack":
        value = c["extended_attack"]
    elif raw_label == "mop_up_monitoring":
        value = c["mop_up_monitoring"]
    elif raw_label == "rapid_escalation":
        signal_count = sum(
            int(evidence[name])
            for name in ["rapid_growth", "intense_firms", "high_severity_behavior", "resource_surge"]
        )
        if signal_count >= 3:
            value = c["rapid_escalation_three_plus_signals"]
        elif signal_count == 2:
            value = c["rapid_escalation_two_signals"]
        else:
            value = c["rapid_escalation_one_signal"]
    else:
        two_conditions = bool(
            observed(row.get("containment"))
            and row.get("containment") >= t["high_containment_pct"]
            and observed(row.get("containment_gain"))
            and row.get("containment_gain") >= t["containment_gain_pct"]
        )
        value = c["containment_two_conditions"] if two_conditions else c["containment_one_condition"]
    if transition_flag == "smoothed_forward":
        value = min(value, c["smoothed_forward_cap"])
    elif transition_flag == "backward_held":
        value = min(value, c["backward_held_cap"])
    elif transition_flag == "confirmed_re_escalation":
        value = max(value, c["confirmed_re_escalation_floor"])
    return float(value)


def missing_core_fields(row: pd.Series) -> list[str]:
    fields = ["fire_age_days", "acres", "containment", "total_personnel", "firms_count_5km", "firms_frp_sum_5km"]
    return [field for field in fields if pd.isna(row.get(field))]


def conflict_reasons(row: pd.Series, evidence: dict[str, Any], raw_label: str, config: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if bool(row.get("same_day_core_conflict", False)):
        reasons.append("same_day_core_field_conflict")
    if row.get("area_interval_status") == "negative_area_revision":
        reasons.append("negative_area_revision")
    if row.get("cost_interval_status") == "negative_revision":
        reasons.append("negative_cost_revision")
    if raw_label == "containment" and evidence["high_severity_behavior"]:
        reasons.append("containment_with_high_severity_behavior")
    containment = row.get("containment")
    if observed(containment) and containment >= config["thresholds"]["high_containment_pct"] and evidence["resource_surge"]:
        reasons.append("high_containment_with_resource_surge")
    return sorted(set(reasons))


def label_fire_days(
    features: pd.DataFrame,
    config: dict[str, Any],
    labeling_timestamp: str,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    previous_labels: dict[str, str] = {}
    prior_high: defaultdict[str, bool] = defaultdict(bool)
    for _, row in features.iterrows():
        incident = str(row["incident_id"])
        evidence = make_evidence(row, config)
        raw_label, triggered_rule = classify_raw(row, evidence, config)
        previous_label = previous_labels.get(incident, "")
        provisional, transition_flag, raw_delta = temporal_adjust(
            previous_label,
            raw_label,
            evidence,
            row,
            prior_high[incident],
            config,
        )
        missing = missing_core_fields(row)
        conflicts = conflict_reasons(row, evidence, raw_label, config)
        eligible = bool(raw_label)
        confidence = confidence_for(raw_label, transition_flag, evidence, row, config)
        record = {
            "incident_id": incident,
            "fire_day_date": row["fire_day_date"],
            "stage1_eligible": int(eligible),
            "stage1_ineligibility_reason": "" if eligible else triggered_rule,
            "raw_rule_label": raw_label,
            "provisional_lifecycle_label": provisional,
            "rule_confidence": confidence,
            "transition_flag": transition_flag,
            "previous_provisional_label": previous_label,
            "raw_stage_delta": raw_delta,
            "triggered_rule": triggered_rule,
            "triggered_signals": stable_json(evidence["triggered_signals"]),
            "missing_core_evidence": int(bool(missing)),
            "missing_core_fields": stable_json(missing),
            "conflicting_evidence": int(bool(conflicts)),
            "conflict_reasons": stable_json(conflicts),
            **{name: int(bool(evidence[name])) for name in [
                "rapid_growth",
                "intense_firms",
                "active_firms",
                "high_severity_behavior",
                "resource_surge",
                "low_activity",
                "low_activity_unknown",
                "resource_drawdown",
                "escalation_signal",
            ]},
            "review_required": 0,
            "review_queue_reason": "",
            "review_sampling_stratum": "",
            "labeling_timestamp": labeling_timestamp,
        }
        records.append(record)
        if provisional:
            previous_labels[incident] = provisional
        containment = row.get("containment")
        if observed(containment) and containment >= config["thresholds"]["high_containment_pct"]:
            prior_high[incident] = True
    labels = pd.DataFrame(records, columns=AUTOMATIC_COLUMNS)
    return labels


def near_threshold(value: Any, threshold: float, fraction: float = 0.10) -> bool:
    return observed(value) and abs(float(value) - threshold) <= max(abs(threshold) * fraction, 1e-12)


def review_boundary_reasons(row: pd.Series, config: dict[str, Any]) -> list[str]:
    t = config["thresholds"]
    reasons: list[str] = []
    containment = row.get("containment")
    if observed(containment) and (
        abs(containment - t["high_containment_pct"]) <= 5
        or abs(containment - t["near_full_containment_pct"]) <= 5
    ):
        reasons.append("containment_threshold_boundary")
    checks = [
        ("new_acres", row.get("new_acres"), t["meaningful_new_acres"]),
        ("rapid_new_acres", row.get("new_acres"), t["rapid_new_acres"]),
        ("extreme_new_acres", row.get("new_acres"), t["extreme_new_acres"]),
        ("firms_count", row.get("firms_count_5km"), t["active_firms_count"]),
        ("intense_firms_count", row.get("firms_count_5km"), t["intense_firms_count"]),
        ("firms_frp", row.get("firms_frp_sum_5km"), t["active_firms_frp_sum"]),
        ("intense_firms_frp", row.get("firms_frp_sum_5km"), t["intense_firms_frp_sum"]),
        ("personnel_surge", row.get("personnel_delta"), t["personnel_surge_abs"]),
        ("personnel_drawdown", row.get("personnel_delta"), t["personnel_drawdown_abs"]),
        ("daily_cost", row.get("average_daily_cost_usd"), t["high_daily_cost_usd"]),
        ("cost_increment", row.get("cost_increment_usd"), t["high_cost_increment_usd"]),
    ]
    for name, value, threshold in checks:
        if near_threshold(value, threshold):
            reasons.append(f"{name}_threshold_boundary")
    return reasons


def add_review_routing(features: pd.DataFrame, labels: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    merged = labels.merge(features, on=["incident_id", "fire_day_date"], how="left", validate="one_to_one")
    mandatory_reasons: list[list[str]] = []
    transition_review = {"forward_transition", "smoothed_forward", "backward_held", "confirmed_re_escalation"}
    for _, row in merged.iterrows():
        reasons: list[str] = []
        if row["stage1_eligible"] != 1:
            reasons.append("stage1_ineligible")
        if row["provisional_lifecycle_label"] == "initial_attack":
            reasons.append("all_initial_attack")
        if observed(row.get("rule_confidence")) and row["rule_confidence"] <= 0.68:
            reasons.append("low_confidence")
        if row["transition_flag"] in transition_review:
            reasons.append("phase_transition_or_temporal_adjustment")
        if row["missing_core_evidence"] == 1:
            reasons.append("missing_core_evidence")
        if row["conflicting_evidence"] == 1:
            reasons.append("conflicting_evidence")
        reasons.extend(review_boundary_reasons(row, config))
        mandatory_reasons.append(sorted(set(reasons)))

    labels = labels.copy()
    labels["_review_reasons"] = mandatory_reasons
    remaining = labels.index[labels["_review_reasons"].map(len).eq(0)]
    audit_selected: set[int] = set()
    for phase, group_indices in labels.loc[remaining].groupby("provisional_lifecycle_label").groups.items():
        indices = list(group_indices)
        n_select = int(round(len(indices) * config["review_audit_fraction"]))
        if indices and n_select == 0:
            n_select = 1
        # Interleave candidates across incidents before taking the phase quota.
        # This preserves the requested phase stratification while preventing a
        # few long incident trajectories from dominating the audit sample.
        by_incident: dict[str, list[int]] = defaultdict(list)
        for index in indices:
            by_incident[str(labels.at[index, "incident_id"])].append(index)
        for incident_indices in by_incident.values():
            incident_indices.sort(
                key=lambda idx: hashlib.sha256(
                    f"{config['review_sampling_seed']}|{labels.at[idx, 'incident_id']}|{labels.at[idx, 'fire_day_date']}".encode()
                ).hexdigest()
            )
        incident_order = sorted(
            by_incident,
            key=lambda incident: hashlib.sha256(
                f"{config['review_sampling_seed']}|{phase}|{incident}".encode()
            ).hexdigest(),
        )
        incident_diverse_order: list[int] = []
        depth = 0
        while len(incident_diverse_order) < len(indices):
            for incident in incident_order:
                candidates = by_incident[incident]
                if depth < len(candidates):
                    incident_diverse_order.append(candidates[depth])
            depth += 1
        audit_selected.update(incident_diverse_order[:n_select])
    for index in audit_selected:
        labels.at[index, "_review_reasons"] = ["phase_stratified_audit_sample"]
        labels.at[index, "review_sampling_stratum"] = (
            f"{labels.at[index, 'provisional_lifecycle_label']}|incident_diverse"
        )
    labels["review_required"] = labels["_review_reasons"].map(lambda value: int(bool(value)))
    labels["review_queue_reason"] = labels["_review_reasons"].map(lambda value: "|".join(value))
    return labels.drop(columns=["_review_reasons"])


def validate_outputs(features: pd.DataFrame, labels: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    keys = ["incident_id", "fire_day_date"]
    legal = set(config["labels"])
    anomalies: list[dict[str, Any]] = []
    if features.duplicated(keys).any() or labels.duplicated(keys).any():
        raise RuntimeError("Duplicate incident-date keys remain after Fire-Day construction")
    if len(features) != len(labels):
        raise RuntimeError("Feature and automatic-label row counts differ")
    missing_eligible_labels = labels["stage1_eligible"].eq(1) & labels[
        "provisional_lifecycle_label"
    ].eq("")
    if missing_eligible_labels.any():
        raise RuntimeError("An eligible Fire-Day is missing its provisional label")
    invalid_labels = labels.loc[
        labels["provisional_lifecycle_label"].ne("")
        & ~labels["provisional_lifecycle_label"].isin(legal)
    ]
    if len(invalid_labels):
        raise RuntimeError("An illegal provisional label was generated")
    for incident, group in labels.groupby("incident_id", sort=False):
        previous = ""
        previous_date = ""
        for _, row in group.sort_values("fire_day_date").iterrows():
            current = row["provisional_lifecycle_label"]
            flag = row["transition_flag"]
            if previous and current:
                delta = config["temporal_order"][current] - config["temporal_order"][previous]
                invalid = delta > 1 or (delta < 0 and flag != "confirmed_re_escalation")
                if invalid:
                    anomalies.append(
                        {
                            "incident_id": incident,
                            "previous_date": previous_date,
                            "current_date": row["fire_day_date"],
                            "previous_label": previous,
                            "current_label": current,
                            "transition_flag": flag,
                            "stage_delta": delta,
                        }
                    )
            if current:
                previous = current
                previous_date = row["fire_day_date"]
    anomaly_df = pd.DataFrame(
        anomalies,
        columns=[
            "incident_id",
            "previous_date",
            "current_date",
            "previous_label",
            "current_label",
            "transition_flag",
            "stage_delta",
        ],
    )
    if len(anomaly_df):
        raise RuntimeError(f"Found {len(anomaly_df)} invalid temporal transitions")
    negative_cost_surge = (
        labels["resource_surge"].eq(1)
        & features["cost_interval_status"].eq("negative_revision")
        & ~features["personnel_delta"].ge(config["thresholds"]["personnel_surge_abs"])
        & ~features["personnel_pct_change"].ge(config["thresholds"]["personnel_surge_ratio"])
    )
    forbidden_fragments = (
        "next_day",
        "nextday",
        "future_",
        "final_incident",
        "final_lifecycle",
        "expert_",
        "provisional_",
        "raw_rule_",
        "review_",
        "target_",
        "eligibility_",
    )
    future_derived_columns = sorted(
        column
        for column in features.columns
        if any(fragment in column.lower() for fragment in forbidden_fragments)
    )
    unobserved_firms_as_zero = int(
        (
            ~features["firms_match_status"].isin(
                ["matched_detections", "observed_no_detections"]
            )
            & features["firms_count_5km"].eq(0)
        ).sum()
    )
    checks = {
        "feature_rows_equal_label_rows": True,
        "unique_incident_date_keys": True,
        "chronological_order": bool(
            features.groupby("incident_id")["fire_day_date"].apply(lambda x: x.is_monotonic_increasing).all()
        ),
        "eligible_rows_have_provisional_labels": bool(~missing_eligible_labels.any()),
        "legal_provisional_labels": True,
        "invalid_transition_count": int(len(anomaly_df)),
        "negative_cost_revision_alone_triggered_resource_surge": int(negative_cost_surge.sum()),
        "unobserved_firms_silently_encoded_as_zero": unobserved_firms_as_zero,
        "future_derived_columns_in_feature_table": future_derived_columns,
    }
    if checks["negative_cost_revision_alone_triggered_resource_surge"]:
        raise RuntimeError("A negative cost revision incorrectly triggered resource surge")
    if checks["unobserved_firms_silently_encoded_as_zero"]:
        raise RuntimeError("Unavailable FIRMS evidence was silently encoded as zero")
    if future_derived_columns:
        raise RuntimeError(f"Future-derived columns entered the feature table: {future_derived_columns}")
    return anomaly_df, checks


def data_dictionary(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    definitions = {
        "fire_day_date": "Calendar date derived from the local REPORT_TO_DATE value.",
        "source_report_count": "Number of same-incident same-date SitReps collapsed into the Fire-Day.",
        "source_report_ids": "JSON list of source INC209R identifiers contributing to the Fire-Day.",
        "same_day_core_conflict": "Whether target-relevant same-day reports contained conflicting valid values.",
        "calendar_gap_days": "Calendar-day gap from the immediately preceding observed Fire-Day.",
        "new_acres": "Current reported acres minus preceding reported acres when the interval is comparable.",
        "relative_area_growth": "new_acres divided by max(previous_acres, 1).",
        "containment_gain": "Current containment minus preceding containment in percentage points.",
        "personnel_delta": "Current assigned personnel minus preceding assigned personnel.",
        "personnel_pct_change": "Personnel delta divided by preceding personnel when preceding personnel is positive.",
        "cost_increment_usd": "Non-negative change in reported cumulative estimated incident cost.",
        "average_daily_cost_usd": "Valid cost increment divided by the observed calendar gap.",
        "firms_count_5km": "Same-day VIIRS FIRMS detection count within 5 km of incident coordinates.",
        "firms_frp_sum_5km": "Sum of reported FRP for same-day VIIRS detections within 5 km.",
        "raw_rule_label": "Lifecycle state produced directly by the frozen priority rules.",
        "provisional_lifecycle_label": "Raw rule state after deterministic temporal-consistency adjustment.",
        "rule_confidence": "Rule-based review-routing confidence; not a calibrated probability.",
        "transition_flag": "Temporal relationship or adjustment applied to the provisional state.",
        "triggered_signals": "JSON list of activated evidence signals.",
        "missing_core_evidence": "Whether one or more core evidence fields are missing.",
        "conflicting_evidence": "Whether source or rule evidence is internally conflicting.",
        "review_required": "Whether the Fire-Day is routed to Stage 2 expert review.",
        "review_queue_reason": "Pipe-delimited automatic reasons for Stage 2 review routing.",
    }
    units = {
        "latitude": "decimal degrees",
        "longitude": "decimal degrees",
        "fire_age_days": "calendar days",
        "calendar_gap_days": "calendar days",
        "acres": "acres",
        "previous_acres": "acres",
        "new_acres": "acres",
        "relative_area_growth": "ratio",
        "containment": "percentage points",
        "previous_containment": "percentage points",
        "containment_gain": "percentage points",
        "total_personnel": "persons assigned",
        "previous_total_personnel": "persons assigned",
        "personnel_delta": "persons assigned",
        "personnel_pct_change": "ratio",
        "cumulative_cost_usd": "USD, as reported",
        "previous_cumulative_cost_usd": "USD, as reported",
        "cost_increment_usd": "USD per report interval",
        "average_daily_cost_usd": "USD per calendar day",
        "firms_count_5km": "VIIRS detections",
        "firms_frp_sum_5km": "MW",
        "firms_nearest_detection_km": "km",
        "rule_confidence": "unitless review-routing score",
    }
    all_fields = list(dict.fromkeys([*features.columns, *labels.columns]))
    rows: list[dict[str, Any]] = []
    for field in all_fields:
        in_features = field in features.columns
        in_labels = field in labels.columns
        if in_features and in_labels:
            table = "both"
        elif in_features:
            table = "fire_day_features_2017to2020.csv"
        else:
            table = "automatic_prelabels.csv"
        if field in {"incident_id", "fire_day_date"}:
            role = "immutable key"
        elif field in {
            "raw_rule_label",
            "provisional_lifecycle_label",
            "rule_confidence",
            "transition_flag",
            "previous_provisional_label",
            "raw_stage_delta",
            "triggered_rule",
            "triggered_signals",
        }:
            role = "automatic Stage 1 annotation"
        elif field.startswith("review_"):
            role = "expert-review routing"
        elif field.endswith("_source_report_id") or field.startswith("source_"):
            role = "source provenance"
        elif field.startswith("previous_") or field in {
            "new_acres",
            "relative_area_growth",
            "containment_gain",
            "personnel_delta",
            "personnel_pct_change",
            "cost_increment_usd",
            "average_daily_cost_usd",
            "calendar_gap_days",
            "fire_age_days",
        }:
            role = "current/backward-derived evidence"
        elif field in {
            "rapid_growth",
            "intense_firms",
            "active_firms",
            "high_severity_behavior",
            "resource_surge",
            "low_activity",
            "low_activity_unknown",
            "resource_drawdown",
            "escalation_signal",
        }:
            role = "automatic evidence signal"
        elif field in {
            "stage1_eligible",
            "stage1_ineligibility_reason",
            "missing_core_evidence",
            "missing_core_fields",
            "conflicting_evidence",
            "conflict_reasons",
            "labeling_timestamp",
        }:
            role = "annotation audit metadata"
        else:
            role = "current Fire-Day evidence"

        definition = definitions.get(field)
        if definition is None and field.endswith("_source_report_id"):
            base = field.removesuffix("_source_report_id")
            definition = f"ICS-209 source-report identifier supplying the retained `{base}` value."
        elif definition is None and field.startswith("previous_"):
            definition = f"Value of `{field.removeprefix('previous_')}` at the most recent preceding observed Fire-Day."
        elif definition is None and field.startswith("fb_"):
            definition = "Normalized ICS-209 fire-behavior indicator retained from the current report."
        elif definition is None:
            definition = field.replace("_", " ").capitalize() + "."

        if field.startswith("firms_"):
            source = "NASA FIRMS VIIRS, same acquisition date and <=5 km"
        elif field in labels.columns and field not in {"incident_id", "fire_day_date"}:
            source = "Frozen Stage 1 rules or deterministic review routing"
        elif role == "current/backward-derived evidence":
            source = "Derived from current and preceding ICS-209 Fire-Days only"
        else:
            source = "ICS-209-PLUS or deterministic Fire-Day construction"
        rows.append(
            {
                "field": field,
                "table": table,
                "role": role,
                "definition": definition,
                "unit": units.get(field, "not applicable or source-defined"),
                "missing_value_semantics": "Blank/NA means unavailable or not computable; it is never an observed zero.",
                "source_or_derivation": source,
            }
        )
    return pd.DataFrame(rows)


def feature_allowlist(features: pd.DataFrame) -> dict[str, Any]:
    forbidden_metadata = {
        "source_report_ids",
        "source_row_ids",
        "primary_source_report_id",
        "report_to_timestamp",
        "report_from_timestamp",
        "incident_name",
    }
    forbidden_suffix = "_source_report_id"
    allow = [
        column
        for column in features.columns
        if column not in forbidden_metadata
        and not column.endswith(forbidden_suffix)
        and column not in {"incident_id", "fire_day_date"}
    ]
    return {
        "version": "task-a-feature-allowlist-v1.0.0",
        "key_columns": ["incident_id", "fire_day_date"],
        "allowed_prediction_time_features": allow,
        "forbidden_categories": [
            "automatic labeling outputs",
            "expert review fields",
            "next-day targets",
            "future incident outcomes",
            "source identifiers",
        ],
    }


def write_quality_report(
    path: Path,
    features: pd.DataFrame,
    labels: pd.DataFrame,
    cohort_stats: dict[str, int],
    firms_stats: dict[str, int],
    checks: dict[str, Any],
) -> None:
    lines = [
        "# FireResBench Task A Stage 1 data-quality report",
        "",
        "## Scope",
        "",
        f"- Date range: {features['fire_day_date'].min()} to {features['fire_day_date'].max()}",
        f"- Source reports in date range: {cohort_stats['source_reports_in_date_range']:,}",
        f"- Fire-Days after same-day collapse: {cohort_stats['source_fire_days_after_same_day_collapse']:,}",
        f"- Included CONUS Fire-Days: {len(features):,}",
        f"- Included incidents: {features['incident_id'].nunique():,}",
        f"- Excluded Fire-Days: {cohort_stats['excluded_fire_days']:,}",
        f"- Same-day multi-report Fire-Days: {cohort_stats['same_day_multi_report_fire_days']:,}",
        f"- Same-day field conflicts: {cohort_stats['same_day_field_conflicts']:,}",
        "",
        "## FIRMS alignment",
        "",
        f"- FIRMS source rows: {firms_stats['firms_source_rows']:,}",
        f"- Valid FIRMS rows: {firms_stats['firms_valid_rows']:,}",
        f"- Fire-Days with one or more 5 km detections: {(features['firms_count_5km'] > 0).sum():,}",
        f"- Fire-Days with observed zero detections: {(features['firms_count_5km'] == 0).sum():,}",
        "",
        "## Automatic annotation",
        "",
        f"- Stage 1 eligible rows: {labels['stage1_eligible'].sum():,}",
        f"- Rows without a provisional label: {(labels['stage1_eligible'] == 0).sum():,}",
        f"- Rows routed to expert review: {labels['review_required'].sum():,}",
        f"- Rows with missing core evidence: {labels['missing_core_evidence'].sum():,}",
        f"- Rows with conflicting evidence: {labels['conflicting_evidence'].sum():,}",
        "",
        "### Provisional-label distribution",
        "",
    ]
    for label, count in labels["provisional_lifecycle_label"].replace("", pd.NA).value_counts(dropna=True).items():
        lines.append(f"- `{label}`: {count:,}")
    lines.extend(["", "## Hard checks", ""])
    for name, value in checks.items():
        lines.append(f"- `{name}`: `{value}`")
    lines.extend(
        [
            "",
            "## Stage boundary",
            "",
            "This release contains provisional Stage 1 annotations only. No expert",
            "review decision, adjudicated label, or final lifecycle ground truth is",
            "present.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def file_row(path: Path, project_root: Path, role: str) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(project_root.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "role": role,
    }


def main() -> None:
    args = parse_args()
    config = read_config(args.config)
    start_date = args.start_date or config["date_range"]["start"]
    end_date = args.end_date or config["date_range"]["end"]
    labeling_timestamp = args.labeling_timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output_root = args.output_root.resolve()
    for directory in ["processed", "labels", "metadata", "docs", "tests"]:
        (output_root / directory).mkdir(parents=True, exist_ok=True)

    print("[1/7] Loading and collapsing ICS-209-PLUS reports", flush=True)
    cohort, exclusions, same_day_conflicts, cohort_stats = load_and_collapse_ics(
        args.ics.resolve(), start_date, end_date, config
    )

    years = range(pd.Timestamp(start_date).year, pd.Timestamp(end_date).year + 1)
    print("[2/7] Loading NASA FIRMS annual files", flush=True)
    firms_by_date, firms_paths, firms_stats = load_firms_by_date(args.firms_dir.resolve(), years)
    print("[3/7] Aligning same-day FIRMS observations within 5 km", flush=True)
    cohort = align_firms(
        cohort,
        firms_by_date,
        float(config["thresholds"]["firms_radius_km"]),
        set(years),
    )

    print("[4/7] Deriving backward-looking evidence", flush=True)
    cohort = derive_history(cohort, config)
    cohort = derive_behavior_evidence(cohort, config)
    feature_columns = [column for column in EVIDENCE_COLUMNS if column in cohort.columns]
    provenance_columns = [column for column in cohort.columns if column.endswith("_source_report_id")]
    features = cohort[feature_columns + [c for c in provenance_columns if c not in feature_columns]].copy()
    features = features.sort_values(["incident_id", "fire_day_date"], kind="mergesort").reset_index(drop=True)
    feature_path = output_root / "processed" / "fire_day_features_2017to2020.csv"
    features.to_csv(feature_path, index=False, na_rep="")

    print("[5/7] Applying frozen lifecycle rules and temporal constraints", flush=True)
    labels = label_fire_days(features, config, labeling_timestamp)
    labels = add_review_routing(features, labels, config)
    transition_anomalies, hard_checks = validate_outputs(features, labels, config)

    automatic_path = output_root / "labels" / "automatic_prelabels.csv"
    labels.to_csv(automatic_path, index=False, na_rep="")
    review = labels.loc[labels["review_required"].eq(1)].merge(
        features, on=["incident_id", "fire_day_date"], how="left", validate="one_to_one"
    )
    review.insert(
        0,
        "review_case_id",
        "taskA::" + review["incident_id"].astype(str) + "::" + review["fire_day_date"],
    )
    history_index = features[["incident_id", "fire_day_date"]].copy()
    history_index["available_history_fire_days"] = (
        history_index.groupby("incident_id", sort=False).cumcount() + 1
    )
    history_index["history_start_date"] = history_index.groupby(
        "incident_id", sort=False
    )["fire_day_date"].transform("first")
    review = review.merge(
        history_index,
        on=["incident_id", "fire_day_date"],
        how="left",
        validate="one_to_one",
    )
    review_path = output_root / "labels" / "expert_review_queue.csv"
    review.to_csv(review_path, index=False, na_rep="")
    review_case_index = review[
        [
            "review_case_id",
            "incident_id",
            "fire_day_date",
            "history_start_date",
            "available_history_fire_days",
            "provisional_lifecycle_label",
            "review_queue_reason",
        ]
    ].copy()
    review_case_index["evidence_filter"] = review_case_index.apply(
        lambda row: (
            f"incident_id == {row['incident_id']!r} and "
            f"fire_day_date <= {row['fire_day_date']!r}"
        ),
        axis=1,
    )
    review_case_index_path = output_root / "labels" / "expert_review_case_index.csv"
    review_case_index.to_csv(review_case_index_path, index=False)
    template = review.copy()
    for column in [
        "primary_review_action",
        "primary_review_label",
        "primary_reason_code",
        "primary_rationale",
        "primary_reviewer_code",
        "secondary_review_label",
        "secondary_agreement_flag",
        "secondary_reviewer_code",
        "adjudication_required",
        "adjudicated_label",
        "adjudication_rationale",
    ]:
        template[column] = ""
    template_path = output_root / "labels" / "expert_review_template.csv"
    template.to_csv(template_path, index=False, na_rep="")

    print("[6/7] Writing audits and statistics", flush=True)
    metadata = output_root / "metadata"
    exclusions.to_csv(metadata / "candidate_cohort_exclusions.csv", index=False, na_rep="")
    same_day_conflicts.to_csv(metadata / "same_day_report_conflicts.csv", index=False, na_rep="")
    transition_anomalies.to_csv(metadata / "transition_anomalies.csv", index=False, na_rep="")
    data_dictionary(features, labels).to_csv(
        metadata / "task_a_data_dictionary.csv", index=False
    )
    (metadata / "task_a_feature_allowlist.json").write_text(
        json.dumps(feature_allowlist(features), indent=2) + "\n", encoding="utf-8"
    )
    shutil.copyfile(args.guide.resolve(), output_root / "docs" / args.guide.name)

    statistics = {
        "benchmark_name": "FireResBench",
        "task": "Task A - Wildfire Lifecycle State Understanding",
        "annotation_stage": "Stage 1 deterministic automatic pre-annotation only",
        "date_range": {"start": start_date, "end": end_date},
        "cohort": cohort_stats,
        "firms": firms_stats,
        "stage1_eligible": int(labels["stage1_eligible"].sum()),
        "stage1_ineligible": int(labels["stage1_eligible"].eq(0).sum()),
        "raw_rule_distribution": labels["raw_rule_label"].replace("", pd.NA).value_counts(dropna=True).to_dict(),
        "provisional_label_distribution": labels["provisional_lifecycle_label"].replace("", pd.NA).value_counts(dropna=True).to_dict(),
        "transition_distribution": labels["transition_flag"].value_counts(dropna=False).to_dict(),
        "review_queue_rows": int(labels["review_required"].sum()),
        "review_reason_counts": dict(
            Counter(
                reason
                for value in labels.loc[labels["review_required"].eq(1), "review_queue_reason"]
                for reason in value.split("|")
                if reason
            )
        ),
        "missing_core_evidence_rows": int(labels["missing_core_evidence"].sum()),
        "conflicting_evidence_rows": int(labels["conflicting_evidence"].sum()),
        "stage2_status": "not_started",
        "expert_accept_count": None,
        "expert_correct_count": None,
        "expert_defer_count": None,
        "inter_reviewer_agreement": None,
        "cohens_kappa": None,
        "final_label_distribution": None,
    }
    (metadata / "annotation_statistics.json").write_text(
        json.dumps(statistics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    runtime_environment = {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    (metadata / "runtime_environment.json").write_text(
        json.dumps(runtime_environment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_quality_report(
        metadata / "data_quality_report.md",
        features,
        labels,
        cohort_stats,
        firms_stats,
        hard_checks,
    )

    source_rows = [file_row(args.ics.resolve(), PROJECT_ROOT, "ICS-209-PLUS wildfire SitRep source")]
    source_rows.extend(file_row(path.resolve(), PROJECT_ROOT, "NASA FIRMS VIIRS annual source") for path in firms_paths)
    source_rows.append(file_row(args.guide.resolve(), PROJECT_ROOT, "Frozen Task A labeling guide"))
    source_rows.append(file_row(args.config.resolve(), PROJECT_ROOT, "Frozen Stage 1 rule configuration"))
    pd.DataFrame(source_rows).to_csv(metadata / "source_file_manifest.csv", index=False)

    print("[7/7] Build complete", flush=True)
    print(f"Fire-Days: {len(features):,}")
    print(f"Incidents: {features['incident_id'].nunique():,}")
    print(f"Stage 1 eligible: {labels['stage1_eligible'].sum():,}")
    print(f"Expert review queue: {labels['review_required'].sum():,}")
    print(f"Output root: {output_root}")


if __name__ == "__main__":
    main()
