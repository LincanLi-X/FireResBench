#!/usr/bin/env python3
"""Build final FireResBench Task A labels from human expert review records.

The script performs deterministic integration only. It does not assign or
change labels on behalf of reviewers. It:

1. validates complete, independent decisions from two expert reviewers;
2. accepts reviewer consensus and routes deferrals/disagreements to an
   independent adjudicator;
3. audits the resulting incident timelines for unsupported transitions;
4. applies independently supplied sequence-adjudication decisions; and
5. writes final labels plus an auditable record of every decision path.

The script creates no version field, annotation timestamp, manifest, checksum,
or aggregate statistics file.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


LABELS = (
    "initial_attack",
    "rapid_escalation",
    "extended_attack",
    "containment",
    "mop_up_monitoring",
)
LABEL_ORDER = {label: index for index, label in enumerate(LABELS)}
ANNOTATION_SOURCE = "human_expert_review"

REVIEW_REQUIRED_FIELDS = {
    "review_case_id",
    "incident_id",
    "fire_day_date",
    "reviewer_id",
    "review_action",
    "reviewed_label",
    "reason_code",
    "rationale",
}

ADJUDICATION_REQUIRED_FIELDS = {
    "review_case_id",
    "incident_id",
    "fire_day_date",
    "adjudicator_id",
    "adjudication_action",
    "adjudicated_label",
    "reason_code",
    "rationale",
}

SEQUENCE_REQUIRED_FIELDS = {
    "review_case_id",
    "incident_id",
    "fire_day_date",
    "adjudicator_id",
    "sequence_adjudication_action",
    "sequence_adjudicated_label",
    "reason_code",
    "rationale",
}

FINAL_ADDED_FIELDS = (
    "final_lifecycle_label",
    "primary_review_action",
    "primary_review_label",
    "primary_reason_code",
    "primary_rationale",
    "primary_reviewer_code",
    "primary_review_confidence",
    "primary_evidence_fields",
    "secondary_review_action",
    "secondary_review_label",
    "secondary_reason_code",
    "secondary_rationale",
    "secondary_reviewer_code",
    "secondary_review_confidence",
    "secondary_evidence_fields",
    "reviewer_agreement_flag",
    "adjudication_required",
    "adjudication_action",
    "adjudicated_label",
    "adjudication_reason_code",
    "adjudication_rationale",
    "adjudicator_code",
    "adjudication_confidence",
    "adjudication_evidence_fields",
    "final_label_source",
    "sequence_review_required",
    "sequence_adjudication_action",
    "sequence_adjudicated_label",
    "sequence_adjudication_reason_code",
    "sequence_adjudication_rationale",
    "sequence_adjudicator_code",
    "sequence_adjudication_confidence",
    "sequence_adjudication_evidence_fields",
    "supervised_evaluation_eligible",
    "annotation_source",
)

SEQUENCE_ANOMALY_FIELDS = (
    "review_case_id",
    "incident_id",
    "previous_fire_day_date",
    "fire_day_date",
    "previous_final_lifecycle_label",
    "current_final_lifecycle_label",
    "sequence_anomaly_type",
    "current_final_label_source",
    "rapid_growth",
    "intense_firms",
    "active_firms",
    "high_severity_behavior",
    "resource_surge",
)


def canonical_date(value: str) -> str:
    """Return a supported date representation as ISO ``YYYY-MM-DD``."""
    text = (value or "").strip()
    if not text:
        raise ValueError("A required Fire-Day date is blank")
    candidates = (text, text[:10])
    for candidate in candidates:
        for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(candidate, date_format).date().isoformat()
            except ValueError:
                continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Unsupported Fire-Day date: {value!r}") from exc


def case_id(incident_id: str, fire_day_date: str) -> str:
    incident = (incident_id or "").strip()
    if not incident:
        raise ValueError("A required incident_id is blank")
    return f"taskA::{incident}::{canonical_date(fire_day_date)}"


def validate_declared_case_id(row: dict[str, str], expected: str, path: Path) -> None:
    declared = (row.get("review_case_id") or "").strip()
    if declared == expected:
        return
    try:
        prefix, declared_date = declared.rsplit("::", 1)
        normalized = f"{prefix}::{canonical_date(declared_date)}"
    except (ValueError, AttributeError):
        normalized = declared
    if normalized != expected:
        raise ValueError(
            f"{path}: review_case_id {declared!r} does not match incident/date key {expected!r}"
        )


def read_stage1(path: Path) -> tuple[list[str], list[dict[str, str]], dict[str, dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        required = {"incident_id", "fire_day_date", "provisional_lifecycle_label"}
        missing = required - set(fields)
        if missing:
            raise ValueError(f"{path} is missing Stage 1 fields: {sorted(missing)}")
        ordered: list[dict[str, str]] = []
        indexed: dict[str, dict[str, str]] = {}
        for source in reader:
            row = dict(source)
            row["fire_day_date"] = canonical_date(row["fire_day_date"])
            key = case_id(row["incident_id"], row["fire_day_date"])
            if key in indexed:
                raise ValueError(f"Duplicate Stage 1 Fire-Day: {key}")
            label = row["provisional_lifecycle_label"].strip()
            if label and label not in LABELS:
                raise ValueError(f"Invalid Stage 1 provisional label for {key}: {label!r}")
            ordered.append(row)
            indexed[key] = row
    return fields, ordered, indexed


def read_case_rows(
    path: Path,
    required_fields: set[str],
) -> tuple[list[str], list[dict[str, str]], dict[str, dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        missing = required_fields - set(fields)
        if missing:
            raise ValueError(f"{path} is missing required fields: {sorted(missing)}")
        ordered: list[dict[str, str]] = []
        indexed: dict[str, dict[str, str]] = {}
        for source in reader:
            row = dict(source)
            row["fire_day_date"] = canonical_date(row["fire_day_date"])
            key = case_id(row["incident_id"], row["fire_day_date"])
            validate_declared_case_id(row, key, path)
            row["review_case_id"] = key
            if key in indexed:
                raise ValueError(f"Duplicate review_case_id={key!r} in {path}")
            ordered.append(row)
            indexed[key] = row
    return fields, ordered, indexed


def validate_confidence(row: dict[str, str], key: str, context: str) -> None:
    value = (row.get("confidence") or "").strip()
    if not value:
        return
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ValueError(f"{context} confidence is not numeric for {key}: {value!r}") from exc
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{context} confidence is outside [0, 1] for {key}: {value!r}")


def validate_reviewer(
    rows: dict[str, dict[str, str]],
    queue: dict[str, dict[str, str]],
    role_name: str,
) -> None:
    expected_keys = set(queue)
    if set(rows) != expected_keys:
        missing = len(expected_keys - set(rows))
        extra = len(set(rows) - expected_keys)
        raise ValueError(f"{role_name} coverage mismatch: missing={missing}, extra={extra}")
    for key, row in rows.items():
        action = row["review_action"].strip()
        label = row["reviewed_label"].strip()
        provisional = queue[key].get("provisional_lifecycle_label", "").strip()
        if action not in {"accept", "correct", "defer"}:
            raise ValueError(f"Invalid {role_name} action for {key}: {action!r}")
        if action == "defer" and label:
            raise ValueError(f"Deferred {role_name} decision has a label for {key}")
        if action != "defer" and label not in LABELS:
            raise ValueError(f"Invalid {role_name} label for {key}: {label!r}")
        if action == "accept" and label != provisional:
            raise ValueError(f"{role_name} accepted but changed the provisional label for {key}")
        if action == "correct" and label == provisional:
            raise ValueError(f"{role_name} marked correct without changing the label for {key}")
        if not row["reviewer_id"].strip():
            raise ValueError(f"Missing {role_name} reviewer_id for {key}")
        if not row["reason_code"].strip() or not row["rationale"].strip():
            raise ValueError(f"Missing {role_name} audit text for {key}")
        validate_confidence(row, key, role_name)


def validate_reviewer_independence(
    reviewer_a: dict[str, dict[str, str]],
    reviewer_b: dict[str, dict[str, str]],
) -> None:
    for key in reviewer_a:
        if reviewer_a[key]["reviewer_id"].strip() == reviewer_b[key]["reviewer_id"].strip():
            raise ValueError(f"The same reviewer_id appears in both independent reviews for {key}")


def validate_adjudicator(
    rows: dict[str, dict[str, str]],
    required_keys: set[str],
    reviewer_a: dict[str, dict[str, str]],
    reviewer_b: dict[str, dict[str, str]],
) -> None:
    if set(rows) != required_keys:
        missing = len(required_keys - set(rows))
        extra = len(set(rows) - required_keys)
        raise ValueError(f"Adjudicator coverage mismatch: missing={missing}, extra={extra}")
    for key, row in rows.items():
        action = row["adjudication_action"].strip()
        label = row["adjudicated_label"].strip()
        adjudicator_id = row["adjudicator_id"].strip()
        if action not in {"resolve", "defer"}:
            raise ValueError(f"Invalid adjudication action for {key}: {action!r}")
        if action == "defer" and label:
            raise ValueError(f"Deferred adjudication has a label for {key}")
        if action == "resolve" and label not in LABELS:
            raise ValueError(f"Invalid adjudicated label for {key}: {label!r}")
        if not adjudicator_id:
            raise ValueError(f"Missing adjudicator_id for {key}")
        if adjudicator_id in {
            reviewer_a[key]["reviewer_id"].strip(),
            reviewer_b[key]["reviewer_id"].strip(),
        }:
            raise ValueError(f"Adjudicator is not independent of both reviewers for {key}")
        if not row["reason_code"].strip() or not row["rationale"].strip():
            raise ValueError(f"Missing adjudication audit text for {key}")
        validate_confidence(row, key, "adjudicator")


def validate_sequence_adjudicator(
    rows: dict[str, dict[str, str]],
    required_keys: set[str],
) -> None:
    if set(rows) != required_keys:
        missing = len(required_keys - set(rows))
        extra = len(set(rows) - required_keys)
        raise ValueError(f"Sequence-adjudicator coverage mismatch: missing={missing}, extra={extra}")
    for key, row in rows.items():
        action = row["sequence_adjudication_action"].strip()
        label = row["sequence_adjudicated_label"].strip()
        if action not in {"resolve", "defer"}:
            raise ValueError(f"Invalid sequence-adjudication action for {key}: {action!r}")
        if action == "defer" and label:
            raise ValueError(f"Deferred sequence adjudication has a label for {key}")
        if action == "resolve" and label not in LABELS:
            raise ValueError(f"Invalid sequence-adjudicated label for {key}: {label!r}")
        if not row["adjudicator_id"].strip():
            raise ValueError(f"Missing sequence adjudicator_id for {key}")
        if not row["reason_code"].strip() or not row["rationale"].strip():
            raise ValueError(f"Missing sequence-adjudication audit text for {key}")
        validate_confidence(row, key, "sequence adjudicator")


def is_supported_reescalation(row: dict[str, str]) -> bool:
    return any(
        row.get(field, "").strip().lower() in {"1", "true", "yes"}
        for field in (
            "rapid_growth",
            "intense_firms",
            "active_firms",
            "high_severity_behavior",
            "resource_surge",
        )
    )


def audit_sequences(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_incident: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_incident[row["incident_id"]].append(row)

    for row in rows:
        row["sequence_review_required"] = "0"

    anomalies: list[dict[str, str]] = []
    for incident_id, incident_rows in by_incident.items():
        incident_rows.sort(key=lambda item: canonical_date(item["fire_day_date"]))
        previous: dict[str, str] | None = None
        for row in incident_rows:
            label = row["final_lifecycle_label"]
            if previous is not None and previous["final_lifecycle_label"] and label:
                old = previous["final_lifecycle_label"]
                delta = LABEL_ORDER[label] - LABEL_ORDER[old]
                anomaly_type = ""
                if delta > 1:
                    anomaly_type = "forward_phase_skip"
                elif delta < 0 and not (
                    label == "rapid_escalation" and is_supported_reescalation(row)
                ):
                    anomaly_type = "unsupported_backward_transition"
                if anomaly_type and row.get("sequence_adjudication_action") != "resolve":
                    row["sequence_review_required"] = "1"
                    row["supervised_evaluation_eligible"] = "0"
                    anomalies.append(
                        {
                            "review_case_id": case_id(incident_id, row["fire_day_date"]),
                            "incident_id": incident_id,
                            "previous_fire_day_date": previous["fire_day_date"],
                            "fire_day_date": row["fire_day_date"],
                            "previous_final_lifecycle_label": old,
                            "current_final_lifecycle_label": label,
                            "sequence_anomaly_type": anomaly_type,
                            "current_final_label_source": row["final_label_source"],
                            "rapid_growth": row.get("rapid_growth", ""),
                            "intense_firms": row.get("intense_firms", ""),
                            "active_firms": row.get("active_firms", ""),
                            "high_severity_behavior": row.get("high_severity_behavior", ""),
                            "resource_surge": row.get("resource_surge", ""),
                        }
                    )
            previous = row
    return anomalies


def write_csv(
    path: Path,
    fields: Iterable[str],
    rows: Iterable[dict[str, str]],
) -> None:
    field_list = list(fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_list, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def copy_optional(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def apply_sequence_decisions(
    output_rows: list[dict[str, str]],
    decisions: dict[str, dict[str, str]],
    source_name: str,
) -> None:
    for row in output_rows:
        key = case_id(row["incident_id"], row["fire_day_date"])
        decision = decisions.get(key)
        if decision is None:
            continue
        action = decision["sequence_adjudication_action"].strip()
        row.update(
            {
                "sequence_review_required": "0",
                "sequence_adjudication_action": action,
                "sequence_adjudicated_label": decision["sequence_adjudicated_label"].strip(),
                "sequence_adjudication_reason_code": decision["reason_code"].strip(),
                "sequence_adjudication_rationale": decision["rationale"].strip(),
                "sequence_adjudicator_code": decision["adjudicator_id"].strip(),
                "sequence_adjudication_confidence": copy_optional(decision, "confidence"),
                "sequence_adjudication_evidence_fields": copy_optional(
                    decision, "evidence_fields"
                ),
            }
        )
        if action == "resolve":
            row["final_lifecycle_label"] = decision["sequence_adjudicated_label"].strip()
            row["final_label_source"] = source_name
            row["supervised_evaluation_eligible"] = "1"
        else:
            row["final_lifecycle_label"] = ""
            row["final_label_source"] = "unresolved_sequence_defer"
            row["supervised_evaluation_eligible"] = "0"


def validate_final_output(rows: list[dict[str, str]], expected_count: int) -> None:
    if len(rows) != expected_count:
        raise ValueError("Final output row count differs from Stage 1")
    seen: set[str] = set()
    for row in rows:
        key = case_id(row["incident_id"], row["fire_day_date"])
        if key in seen:
            raise ValueError(f"Duplicate final Fire-Day: {key}")
        seen.add(key)
        label = row["final_lifecycle_label"]
        eligible = row["supervised_evaluation_eligible"]
        if label and label not in LABELS:
            raise ValueError(f"Invalid final lifecycle label for {key}: {label!r}")
        expected_eligible = "1" if label and row["sequence_review_required"] == "0" else "0"
        if eligible != expected_eligible:
            raise ValueError(
                f"Eligibility mismatch for {key}: expected {expected_eligible}, found {eligible!r}"
            )
        if row["annotation_source"] != ANNOTATION_SOURCE:
            raise ValueError(f"Unexpected annotation source for {key}")


def build(args: argparse.Namespace) -> None:
    stage1_fields, stage1_ordered, stage1 = read_stage1(args.prelabels)
    _, _, queue = read_case_rows(args.review_queue, {"review_case_id", "incident_id", "fire_day_date"})
    queue_keys = set(queue)
    if not queue_keys <= set(stage1):
        raise ValueError("The expert-review queue contains cases absent from Stage 1")
    for key, queued in queue.items():
        queued_label = queued.get("provisional_lifecycle_label", "").strip()
        if queued_label and queued_label != stage1[key]["provisional_lifecycle_label"].strip():
            raise ValueError(f"Review-queue provisional label differs from Stage 1 for {key}")

    _, _, reviewer_a = read_case_rows(args.reviewer_a, REVIEW_REQUIRED_FIELDS)
    _, _, reviewer_b = read_case_rows(args.reviewer_b, REVIEW_REQUIRED_FIELDS)
    validate_reviewer(reviewer_a, queue, "Reviewer A")
    validate_reviewer(reviewer_b, queue, "Reviewer B")
    validate_reviewer_independence(reviewer_a, reviewer_b)

    required_adjudication = {
        key
        for key in queue_keys
        if reviewer_a[key]["review_action"].strip() == "defer"
        or reviewer_b[key]["review_action"].strip() == "defer"
        or reviewer_a[key]["reviewed_label"].strip()
        != reviewer_b[key]["reviewed_label"].strip()
    }
    _, _, adjudicator = read_case_rows(args.adjudicator, ADJUDICATION_REQUIRED_FIELDS)
    validate_adjudicator(adjudicator, required_adjudication, reviewer_a, reviewer_b)

    output_rows: list[dict[str, str]] = []
    for source in stage1_ordered:
        key = case_id(source["incident_id"], source["fire_day_date"])
        row = dict(source)
        row.update({field: "" for field in FINAL_ADDED_FIELDS})
        row["sequence_review_required"] = "0"
        row["annotation_source"] = ANNOTATION_SOURCE

        if key not in queue_keys:
            label = source["provisional_lifecycle_label"].strip()
            row.update(
                {
                    "final_lifecycle_label": label,
                    "adjudication_required": "0",
                    "adjudication_action": "not_required",
                    "final_label_source": "stage1_not_routed_to_stage2",
                    "supervised_evaluation_eligible": "1" if label else "0",
                }
            )
            output_rows.append(row)
            continue

        a = reviewer_a[key]
        b = reviewer_b[key]
        row.update(
            {
                "primary_review_action": a["review_action"].strip(),
                "primary_review_label": a["reviewed_label"].strip(),
                "primary_reason_code": a["reason_code"].strip(),
                "primary_rationale": a["rationale"].strip(),
                "primary_reviewer_code": a["reviewer_id"].strip(),
                "primary_review_confidence": copy_optional(a, "confidence"),
                "primary_evidence_fields": copy_optional(a, "evidence_fields"),
                "secondary_review_action": b["review_action"].strip(),
                "secondary_review_label": b["reviewed_label"].strip(),
                "secondary_reason_code": b["reason_code"].strip(),
                "secondary_rationale": b["rationale"].strip(),
                "secondary_reviewer_code": b["reviewer_id"].strip(),
                "secondary_review_confidence": copy_optional(b, "confidence"),
                "secondary_evidence_fields": copy_optional(b, "evidence_fields"),
            }
        )
        consensus = (
            a["review_action"].strip() != "defer"
            and b["review_action"].strip() != "defer"
            and a["reviewed_label"].strip() == b["reviewed_label"].strip()
        )
        row["reviewer_agreement_flag"] = "1" if consensus else "0"
        if consensus:
            row.update(
                {
                    "final_lifecycle_label": a["reviewed_label"].strip(),
                    "adjudication_required": "0",
                    "adjudication_action": "not_required",
                    "final_label_source": "expert_reviewer_consensus",
                    "supervised_evaluation_eligible": "1",
                }
            )
        else:
            decision = adjudicator[key]
            action = decision["adjudication_action"].strip()
            row.update(
                {
                    "adjudication_required": "1",
                    "adjudication_action": action,
                    "adjudicated_label": decision["adjudicated_label"].strip(),
                    "adjudication_reason_code": decision["reason_code"].strip(),
                    "adjudication_rationale": decision["rationale"].strip(),
                    "adjudicator_code": decision["adjudicator_id"].strip(),
                    "adjudication_confidence": copy_optional(decision, "confidence"),
                    "adjudication_evidence_fields": copy_optional(
                        decision, "evidence_fields"
                    ),
                    "final_lifecycle_label": decision["adjudicated_label"].strip(),
                    "final_label_source": (
                        "expert_adjudicator" if action == "resolve" else "unresolved_defer"
                    ),
                    "supervised_evaluation_eligible": "1" if action == "resolve" else "0",
                }
            )
        output_rows.append(row)

    anomalies = audit_sequences(output_rows)
    if anomalies and not args.skip_sequence_decisions:
        if not args.sequence_decisions.exists():
            raise FileNotFoundError(
                f"Sequence decisions are required for {len(anomalies)} cases: "
                f"{args.sequence_decisions}. Run with --skip-sequence-decisions to write "
                "the initial candidate output and anomaly queue."
            )
        _, _, sequence_decisions = read_case_rows(
            args.sequence_decisions, SEQUENCE_REQUIRED_FIELDS
        )
        validate_sequence_adjudicator(
            sequence_decisions, {row["review_case_id"] for row in anomalies}
        )
        apply_sequence_decisions(output_rows, sequence_decisions, "expert_sequence_adjudicator")
        anomalies = audit_sequences(output_rows)

        if anomalies and not args.skip_sequence_round2:
            if not args.sequence_decisions_round2.exists():
                raise FileNotFoundError(
                    f"Round-two sequence decisions are required for {len(anomalies)} cases: "
                    f"{args.sequence_decisions_round2}. Run with --skip-sequence-round2 "
                    "to write the round-two candidate output and anomaly queue."
                )
            _, _, round2_decisions = read_case_rows(
                args.sequence_decisions_round2, SEQUENCE_REQUIRED_FIELDS
            )
            validate_sequence_adjudicator(
                round2_decisions, {row["review_case_id"] for row in anomalies}
            )
            apply_sequence_decisions(
                output_rows,
                round2_decisions,
                "expert_sequence_adjudicator_round2",
            )
            anomalies = audit_sequences(output_rows)

    output_fields = stage1_fields + list(FINAL_ADDED_FIELDS)
    if len(output_fields) != len(set(output_fields)):
        raise ValueError("Duplicate output column name")
    if any(not field or field.startswith("Unnamed:") for field in output_fields):
        raise ValueError("Malformed output column name")

    validate_final_output(output_rows, len(stage1_ordered))
    write_csv(args.output, output_fields, output_rows)
    write_csv(args.sequence_anomalies, SEQUENCE_ANOMALY_FIELDS, anomalies)

    print(f"Wrote {len(output_rows):,} final Task A rows to {args.output}")
    print(f"Remaining sequence-review cases: {len(anomalies):,}")


def parse_args() -> argparse.Namespace:
    expert_root = Path(__file__).resolve().parent
    task_root = expert_root.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prelabels",
        type=Path,
        default=task_root / "labels" / "automatic_prelabels.csv",
    )
    parser.add_argument(
        "--review-queue",
        type=Path,
        default=task_root / "labels" / "expert_review_queue.csv",
    )
    parser.add_argument(
        "--reviewer-a",
        type=Path,
        default=expert_root / "reviewer_a_decisions.csv",
    )
    parser.add_argument(
        "--reviewer-b",
        type=Path,
        default=expert_root / "reviewer_b_decisions.csv",
    )
    parser.add_argument(
        "--adjudicator",
        type=Path,
        default=expert_root / "adjudicator_decisions.csv",
    )
    parser.add_argument(
        "--sequence-decisions",
        type=Path,
        default=expert_root / "sequence_adjudicator_decisions.csv",
    )
    parser.add_argument(
        "--sequence-decisions-round2",
        type=Path,
        default=expert_root / "sequence_adjudicator_decisions_round2.csv",
    )
    parser.add_argument(
        "--skip-sequence-decisions",
        action="store_true",
        help="Write the pre-sequence-adjudication candidate and initial anomaly queue",
    )
    parser.add_argument(
        "--skip-sequence-round2",
        action="store_true",
        help="Apply round-one decisions and write any resulting round-two anomaly queue",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=task_root / "labels" / "final_expert_labels.csv",
    )
    parser.add_argument(
        "--sequence-anomalies",
        type=Path,
        default=expert_root / "sequence_anomalies.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
