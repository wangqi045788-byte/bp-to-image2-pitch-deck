#!/usr/bin/env python3
"""Safely install the bundled Codex skill on Windows, macOS, or Linux."""

from __future__ import annotations

import argparse
import filecmp
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone


SKILL_NAME = "bp-to-image2-pitch-deck"


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return root / "skills"


def same_tree(left: Path, right: Path) -> bool:
    if not left.is_dir() or not right.is_dir():
        return False
    comparison = filecmp.dircmp(left, right, ignore=["__pycache__", ".DS_Store"])
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(
        left, right, comparison.common_files, shallow=False
    )
    if mismatch or errors:
        return False
    return all(same_tree(left / name, right / name) for name in comparison.common_dirs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=default_skills_dir(),
        help="Codex skills directory (default: $CODEX_HOME/skills or ~/.codex/skills)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Back up and replace an existing different version",
    )
    args = parser.parse_args()

    package_root = Path(__file__).resolve().parent
    source = package_root / "skill" / SKILL_NAME
    destination = args.skills_dir.expanduser().resolve() / SKILL_NAME

    if not (source / "SKILL.md").is_file():
        print(f"ERROR: bundled skill not found: {source}", file=sys.stderr)
        return 2

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if same_tree(source, destination):
            print(f"Already installed and identical: {destination}")
            return 0
        if not args.update:
            print(
                "ERROR: a different version already exists. "
                "Re-run with --update to create a backup and replace it.",
                file=sys.stderr,
            )
            return 3
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
        backup = destination.with_name(f"{SKILL_NAME}.backup-{timestamp}")
        shutil.move(str(destination), str(backup))
        print(f"Backed up previous version: {backup}")

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    print(f"Installed: {destination}")
    print(f"Invoke with: ${SKILL_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
