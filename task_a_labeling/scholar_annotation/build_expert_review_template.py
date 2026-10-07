#!/usr/bin/env python3
"""Create two independent, blank Task A expert-review workbooks as CSV files.

The source review queue and all evidence columns are preserved. The script adds
human-review entry fields, prefills the reviewer roles, and leaves all decision
fields blank; it does not populate or infer decisions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parent.parent
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from build_task_a_stage2 import read_case_rows, write_csv


EXPERT_ENTRY_FIELDS = (
    "reviewer_id",
    "reviewer_role",
    "review_action",
    "reviewed_label",
    "reason_code",
    "rationale",
    "confidence",
    "evidence_fields",
)


def build_blank_template(
    queue_path: Path,
    output_path: Path,
    *,
    reviewer_role: str,
    overwrite: bool,
) -> int:
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing expert work: {output_path}. "
            "Pass --overwrite only when replacement is intentional."
        )

    queue_fields, queue_rows, _ = read_case_rows(
        queue_path,
        required_fields={
            "review_case_id",
            "incident_id",
            "fire_day_date",
            "provisional_lifecycle_label",
        },
    )
    conflicting = set(queue_fields) & set(EXPERT_ENTRY_FIELDS)
    if conflicting:
        raise ValueError(
            "The source queue already contains expert-entry columns: "
            f"{sorted(conflicting)}"
        )

    output_rows: list[dict[str, str]] = []
    for source in queue_rows:
        row = dict(source)
        for field in EXPERT_ENTRY_FIELDS:
            row[field] = reviewer_role if field == "reviewer_role" else ""
        output_rows.append(row)

    write_csv(output_path, [*queue_fields, *EXPERT_ENTRY_FIELDS], output_rows)
    return len(output_rows)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue",
        type=Path,
        default=root.parent / "labels" / "expert_review_queue.csv",
    )
    parser.add_argument(
        "--reviewer-a-output",
        type=Path,
        default=root / "reviewer_a_template.csv",
    )
    parser.add_argument(
        "--reviewer-b-output",
        type=Path,
        default=root / "reviewer_b_template.csv",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.reviewer_a_output.resolve() == args.reviewer_b_output.resolve():
        raise ValueError("Reviewer A and Reviewer B must have different output files")
    if not args.overwrite:
        existing = [
            path
            for path in (args.reviewer_a_output, args.reviewer_b_output)
            if path.exists()
        ]
        if existing:
            raise FileExistsError(
                "Refusing to overwrite existing expert work: "
                + ", ".join(str(path) for path in existing)
                + ". Pass --overwrite only when replacement is intentional."
            )

    count_a = build_blank_template(
        args.queue,
        args.reviewer_a_output,
        reviewer_role="primary_reviewer",
        overwrite=args.overwrite,
    )
    count_b = build_blank_template(
        args.queue,
        args.reviewer_b_output,
        reviewer_role="independent_secondary_reviewer",
        overwrite=args.overwrite,
    )
    if count_a != count_b:
        raise RuntimeError("The two expert templates have different row counts")

    print(f"Wrote {count_a} blank cases to {args.reviewer_a_output}")
    print(f"Wrote {count_b} blank cases to {args.reviewer_b_output}")


if __name__ == "__main__":
    main()
