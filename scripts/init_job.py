#!/usr/bin/env python3
"""Create an isolated job directory for private deck work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--mode", choices=("private", "public"), default="private")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--aspect-ratio", choices=("16:9", "4:3"), default="16:9")
    args = parser.parse_args()

    target = args.job_dir.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        print(f"ERROR: target exists and is not empty: {target}", file=sys.stderr)
        return 1
    target.mkdir(parents=True, exist_ok=True)
    for relative in (
        "input/company",
        "input/materials",
        "input/bp",
        "input/visuals",
        "work/evidence",
        "work/briefs",
        "work/prompts",
        "work/generated",
        "output",
        "qa",
    ):
        (target / relative).mkdir(parents=True, exist_ok=True)

    job = {
        "title": args.title,
        "mode": args.mode,
        "language": args.language,
        "aspect_ratio": args.aspect_ratio,
        "status": "initialized",
        "privacy": "Treat all inputs and prompts as private unless explicitly classified otherwise.",
        "paths": {
            "company": "input/company",
            "materials": "input/materials",
            "bp_optional": "input/bp",
            "visuals_optional": "input/visuals",
            "deck_brief": "work/briefs/deck-brief.json",
            "prompt_pack": "work/prompts/prompt-pack.md",
            "generated": "work/generated",
            "output": "output",
            "qa": "qa",
        },
    }
    (target / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "input" / "SOURCE_INVENTORY.md").write_text(
        "# Source inventory\n\nAssign each input a stable source ID and one label: private, public, third_party, user_provided, or synthetic.\n",
        encoding="utf-8",
    )
    (target / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    print(f"INITIALIZED: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
