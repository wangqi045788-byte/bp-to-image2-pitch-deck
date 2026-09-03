#!/usr/bin/env python3
"""Validate a deck brief and build its Image2 prompt pack in one command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_prompt_pack import build_prompt_pack
from validate_deck_brief import validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.brief.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors, warnings = validate(data)
    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_prompt_pack(data), encoding="utf-8")
    report = {
        "status": "READY_FOR_IMAGE2",
        "slide_count": len(data["slides"]),
        "warning_count": len(warnings),
        "warnings": warnings,
        "prompt_pack": str(args.out),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
