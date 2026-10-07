#!/usr/bin/env python3
"""Create a human review queue for Task A lifecycle-sequence anomalies.

The script joins deterministic anomaly flags with the current label audit trail
and available Fire-Day evidence. It does not infer, change, or approve labels,
and it does not emit sequence-adjudication decision fields. Human decisions are
stored separately from this evidence queue.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parent.parent
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from build_task_a_stage2 import canonical_date, write_csv


SEQUENCE_AUDIT_FIELDS = (
    "final_lifecycle_label",
    "final_label_source",
    "primary_review_action",
    "primary_review_label",
    "primary_reason_code",
    "primary_rationale",
    "secondary_review_action",
    "secondary_review_label",
    "secondary_reason_code",
    "secondary_rationale",
    "reviewer_agreement_flag",
    "adjudication_required",
    "adjudication_action",
    "adjudicated_label",
    "adjudication_reason_code",
    "adjudication_rationale",
)


def read_keyed(
    path: Path,
    *,
    required_fields: set[str],
) -> tuple[list[str], dict[tuple[str, str], dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        missing = required_fields - set(fields)
        if missing:
            raise ValueError(f"{path} is missing required fields: {sorted(missing)}")

        rows: dict[tuple[str, str], dict[str, str]] = {}
        for source in reader:
            row = dict(source)
            row["fire_day_date"] = canonical_date(row["fire_day_date"])
            key = (row["incident_id"].strip(), row["fire_day_date"])
            if not key[0]:
                raise ValueError(f"{path} contains a blank incident_id")
            if key in rows:
                raise ValueError(f"Duplicate Fire-Day in {path}: {key}")
            rows[key] = row
    return fields, rows


def read_anomalies(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        required = {
            "review_case_id",
            "incident_id",
            "fire_day_date",
            "sequence_anomaly_type",
        }
        missing = required - set(fields)
        if missing:
            raise ValueError(f"{path} is missing required fields: {sorted(missing)}")

        seen: set[tuple[str, str]] = set()
        rows: list[dict[str, str]] = []
        for source in reader:
            row = dict(source)
            row["fire_day_date"] = canonical_date(row["fire_day_date"])
            if row.get("previous_fire_day_date", "").strip():
                row["previous_fire_day_date"] = canonical_date(
                    row["previous_fire_day_date"]
                )
            key = (row["incident_id"].strip(), row["fire_day_date"])
            if key in seen:
                raise ValueError(f"Duplicate sequence anomaly in {path}: {key}")
            seen.add(key)
            rows.append(row)
    return fields, rows


def unique_fields(*groups: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for field in group:
            if field not in seen:
                seen.add(field)
                result.append(field)
    return result


def build_queue(
    anomalies_path: Path,
    final_labels_path: Path,
    features_path: Path,
    output_path: Path,
) -> int:
    anomaly_fields, anomalies = read_anomalies(anomalies_path)
    _, final_rows = read_keyed(
        final_labels_path,
        required_fields={"incident_id", "fire_day_date", "final_lifecycle_label"},
    )
    feature_fields, feature_rows = read_keyed(
        features_path,
        required_fields={"incident_id", "fire_day_date"},
    )

    missing_audit_fields = set(SEQUENCE_AUDIT_FIELDS) - set(
        next(iter(final_rows.values())).keys() if final_rows else []
    )
    if missing_audit_fields:
        raise ValueError(
            f"{final_labels_path} is missing required audit fields: "
            f"{sorted(missing_audit_fields)}"
        )
    evidence_fields = [
        f"evidence_{field}"
        for field in feature_fields
        if field not in {"incident_id", "fire_day_date"}
    ]
    output_fields = unique_fields(
        anomaly_fields,
        SEQUENCE_AUDIT_FIELDS,
        evidence_fields,
    )

    output_rows: list[dict[str, str]] = []
    for anomaly in anomalies:
        key = (anomaly["incident_id"].strip(), anomaly["fire_day_date"])
        if key not in final_rows:
            raise ValueError(f"Missing final-label record for sequence anomaly {key}")
        if key not in feature_rows:
            raise ValueError(f"Missing Fire-Day evidence for sequence anomaly {key}")

        row = dict(anomaly)
        final = final_rows[key]
        feature = feature_rows[key]
        row.update({field: final.get(field, "") for field in SEQUENCE_AUDIT_FIELDS})
        row.update(
            {
                f"evidence_{field}": feature.get(field, "")
                for field in feature_fields
                if field not in {"incident_id", "fire_day_date"}
            }
        )
        output_rows.append(row)

    write_csv(output_path, output_fields, output_rows)
    return len(output_rows)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    task_root = root.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anomalies", type=Path, default=root / "sequence_anomalies.csv")
    parser.add_argument(
        "--final-labels",
        type=Path,
        default=task_root / "labels" / "final_expert_labels.csv",
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=task_root / "processed" / "fire_day_features_2017to2020.csv",
    )
    parser.add_argument("--output", type=Path, default=root / "sequence_review_queue.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = build_queue(args.anomalies, args.final_labels, args.features, args.output)
    print(f"Wrote {count} sequence-review cases to {args.output}")


if __name__ == "__main__":
    main()
