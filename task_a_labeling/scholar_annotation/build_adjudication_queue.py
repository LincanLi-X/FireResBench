#!/usr/bin/env python3
"""Build a human adjudication queue from two independent expert reviews.

This script performs deterministic comparison only. It routes disagreements and
deferred cases to an adjudicator without emitting or populating adjudication
decision fields; those decisions are stored in a separate file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parent.parent
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from build_task_a_stage2 import (
    REVIEW_REQUIRED_FIELDS,
    read_case_rows,
    validate_reviewer,
    validate_reviewer_independence,
    write_csv,
)


REVIEW_FIELDS = [
    "reviewer_id",
    "reviewer_role",
    "review_action",
    "reviewed_label",
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

        if (
            reviewer_a["review_action"] == "defer"
            and reviewer_b["review_action"] == "defer"
        ):
            adjudication_reason = "both_reviewers_deferred"
        elif reviewer_a["review_action"] == "defer":
            adjudication_reason = "reviewer_a_deferred"
        elif reviewer_b["review_action"] == "defer":
            adjudication_reason = "reviewer_b_deferred"
        elif (
            reviewer_a["review_action"] != "defer"
            and reviewer_b["review_action"] != "defer"
            and reviewer_a["reviewed_label"] != reviewer_b["reviewed_label"]
        ):
            adjudication_reason = "reviewer_label_disagreement"
        else:
            adjudication_reason = ""

        if not adjudication_reason:
            continue

        output_row = dict(source_row)
        output_row.update(prefixed_review(reviewer_a, "reviewer_a"))
        output_row.update(prefixed_review(reviewer_b, "reviewer_b"))
        output_row["reviewer_label_agreement"] = "0"
        output_row["adjudication_reason"] = adjudication_reason
        routed.append(output_row)

    output_fields = list(queue_fields)
    output_fields.extend(f"reviewer_a_{field}" for field in REVIEW_FIELDS)
    output_fields.extend(f"reviewer_b_{field}" for field in REVIEW_FIELDS)
    output_fields.extend(("reviewer_label_agreement", "adjudication_reason"))

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
