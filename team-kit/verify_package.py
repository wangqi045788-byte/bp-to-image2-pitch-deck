#!/usr/bin/env python3
"""Verify package hashes, required Skill files, and bundled unit tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "scripts/init_job.py",
    "scripts/validate_deck_brief.py",
    "scripts/build_prompt_pack.py",
    "references/input-contract.md",
    "references/evidence-and-workdoc.md",
    "references/narrative-and-slide-selection.md",
    "references/prompt-contract.md",
    "references/qa-and-release-gates.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent
    manifest_path = root / "PACKAGE_MANIFEST.json"
    skill = root / "skill" / "bp-to-image2-pitch-deck"
    failures: list[str] = []

    if not manifest_path.is_file():
        failures.append("PACKAGE_MANIFEST.json is missing")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for record in manifest.get("files", []):
            path = root / record["path"]
            if not path.is_file():
                failures.append(f"missing: {record['path']}")
            elif sha256(path) != record["sha256"]:
                failures.append(f"hash mismatch: {record['path']}")

    for relative in REQUIRED:
        if not (skill / relative).is_file():
            failures.append(f"required skill file missing: {relative}")

    if failures:
        print("PACKAGE INVALID")
        for failure in failures:
            print(f"- {failure}")
        return 1

    test = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=skill,
        text=True,
        capture_output=True,
        check=False,
    )
    print(test.stdout, end="")
    print(test.stderr, end="", file=sys.stderr)
    if test.returncode:
        print("PACKAGE INVALID: bundled tests failed")
        return test.returncode

    print("PACKAGE VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
