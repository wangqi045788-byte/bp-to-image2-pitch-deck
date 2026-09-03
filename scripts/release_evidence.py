#!/usr/bin/env python3
"""Combine machine-readable validation artifacts into one release-evidence report."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-validation", type=Path, required=True)
    parser.add_argument("--privacy-scan", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        skill_validation = read_json(args.skill_validation)
        privacy_scan = read_json(args.privacy_scan)
        tests = read_json(args.tests)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    checks = {
        "skill_validation": skill_validation,
        "privacy_scan": privacy_scan,
        "tests": tests,
    }
    ready = (
        skill_validation.get("status") in {"VALID", "PASS"}
        and privacy_scan.get("status") == "READY"
        and tests.get("status") in {"PASS", "PASSED"}
    )
    report = {
        "status": "READY_FOR_HUMAN_RELEASE_REVIEW" if ready else "BLOCKED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "checks": checks,
        "human_checks_still_required": [
            "ownership and company approval",
            "brand and third-party asset rights",
            "manual privacy review",
            "complete Git history review",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
