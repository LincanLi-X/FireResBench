#!/usr/bin/env python3
"""Build a human adjudication queue from two independent expert reviews.

This script performs deterministic comparison only. It routes disagreements and
deferred cases to an adjudicator and leaves all adjudication fields blank.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from build_task_a_stage2 import (
    REVIEW_REQUIRED_FIELDS,
    read_case_rows,
    validate_reviewer,
    validate_reviewer_independence,
    write_csv,
)


REVIEW_FIELDS = [
    "reviewer_id",
    "review_action",
    "reviewed_label",
    "reason_code",
    "rationale",
    "confidence",
    "evidence_fields",
]

ADJUDICATOR_FIELDS = [
    "adjudicator_id",
    "adjudication_action",
    "adjudicated_label",
    "reason_code",
    "rationale",
    "confidence",
    "evidence_fields",
]


def prefixed_review(row: dict[str, str], prefix: str) -> dict[str, str]:
    return {f"{prefix}_{field}": row.get(field, "") for field in REVIEW_FIELDS}


def build_queue(
    queue_path: Path,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    output_path: Path,
) -> tuple[int, int]:
    queue_fields, queue_rows, queue_by_id = read_case_rows(
        queue_path,
        required_fields={
            "review_case_id",
            "incident_id",
            "fire_day_date",
            "provisional_lifecycle_label",
        },
    )
    _, _, reviewer_a_by_id = read_case_rows(
        reviewer_a_path, required_fields=set(REVIEW_REQUIRED_FIELDS)
    )
    _, _, reviewer_b_by_id = read_case_rows(
        reviewer_b_path, required_fields=set(REVIEW_REQUIRED_FIELDS)
    )

    validate_reviewer(reviewer_a_by_id, queue_by_id, "Reviewer A")
    validate_reviewer(reviewer_b_by_id, queue_by_id, "Reviewer B")
    validate_reviewer_independence(reviewer_a_by_id, reviewer_b_by_id)

    routed: list[dict[str, str]] = []
    for review_case_id, source_row in queue_by_id.items():
        reviewer_a = reviewer_a_by_id[review_case_id]
        reviewer_b = reviewer_b_by_id[review_case_id]

        reasons: list[str] = []
        if reviewer_a["review_action"] == "defer":
            reasons.append("reviewer_a_defer")
        if reviewer_b["review_action"] == "defer":
            reasons.append("reviewer_b_defer")
        if (
            reviewer_a["review_action"] != "defer"
            and reviewer_b["review_action"] != "defer"
            and reviewer_a["reviewed_label"] != reviewer_b["reviewed_label"]
        ):
            reasons.append("label_disagreement")

        if not reasons:
            continue

        output_row = dict(source_row)
        output_row.update(prefixed_review(reviewer_a, "reviewer_a"))
        output_row.update(prefixed_review(reviewer_b, "reviewer_b"))
        output_row["adjudication_queue_reason"] = ";".join(reasons)
        for field in ADJUDICATOR_FIELDS:
            output_row[field] = ""
        routed.append(output_row)

    output_fields = list(queue_fields)
    output_fields.extend(f"reviewer_a_{field}" for field in REVIEW_FIELDS)
    output_fields.extend(f"reviewer_b_{field}" for field in REVIEW_FIELDS)
    output_fields.append("adjudication_queue_reason")
    output_fields.extend(ADJUDICATOR_FIELDS)

    if len(output_fields) != len(set(output_fields)):
        raise ValueError("Output schema contains duplicate column names")

    write_csv(output_path, output_fields, routed)
    return len(queue_rows), len(routed)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=root.parent / "labels" / "expert_review_queue.csv")
    parser.add_argument("--reviewer-a", type=Path, default=root / "reviewer_a_decisions.csv")
    parser.add_argument("--reviewer-b", type=Path, default=root / "reviewer_b_decisions.csv")
    parser.add_argument("--output", type=Path, default=root / "adjudication_queue.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total, routed = build_queue(
        args.queue, args.reviewer_a, args.reviewer_b, args.output
    )
    print(f"Compared {total} review cases.")
    print(f"Routed {routed} disagreement/defer cases to {args.output}")


if __name__ == "__main__":
    main()
