#!/usr/bin/env python3
"""Prepare role-separated FireAgentBench inputs without calling an LLM."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Optional


KEYS = ("incident_id", "fire_day_date")
DECISION_VIEWS = {
    "geo_agent": "geo_agent_view.csv",
    "fire_behavior_agent": "fire_behavior_agent_view.csv",
    "resource_history_agent": "resource_history_agent_view.csv",
}


def read_row(path: Path, incident_id: str, fire_day_date: str) -> Dict[str, Optional[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["incident_id"] == incident_id and row["fire_day_date"] == fire_day_date:
                return {key: (value if value != "" else None) for key, value in row.items()}
    raise KeyError(f"Case not found in {path.name}: {(incident_id, fire_day_date)}")


def first_case(path: Path) -> tuple[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    return row["incident_id"], row["fire_day_date"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id")
    parser.add_argument("--fire-day-date")
    parser.add_argument(
        "--include-critic",
        action="store_true",
        help="Include ground truth for scoring/post-hoc diagnosis only.",
    )
    args = parser.parse_args()
    if bool(args.incident_id) != bool(args.fire_day_date):
        parser.error("--incident-id and --fire-day-date must be supplied together")
    return args


def main() -> None:
    args = parse_args()
    agent_root = Path(__file__).resolve().parents[1]
    incident_id, fire_day_date = (
        (args.incident_id, args.fire_day_date)
        if args.incident_id
        else first_case(agent_root / DECISION_VIEWS["geo_agent"])
    )

    payload = {
        "case_key": dict(zip(KEYS, (incident_id, fire_day_date))),
        "phase": "posthoc" if args.include_critic else "prediction",
        "roles": {
            role: read_row(agent_root / filename, incident_id, fire_day_date)
            for role, filename in DECISION_VIEWS.items()
        },
    }
    if args.include_critic:
        payload["roles"]["critic_agent"] = read_row(
            agent_root / "critic_agent_view.csv", incident_id, fire_day_date
        )

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
