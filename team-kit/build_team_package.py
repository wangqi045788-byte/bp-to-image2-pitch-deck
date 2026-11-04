#!/usr/bin/env python3
"""Build the self-contained teammate ZIP from a clean repository checkout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


SKILL_NAME = "bp-to-image2-pitch-deck"
KIT_NAME = "PPT_Studio_全套Skills使用包"
RUNTIME_ROOT_FILES = (
    "SKILL.md",
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "pyproject.toml",
    "PPT_REQUEST.md",
    "requirements-ppt.txt",
    "requirements-noir.txt",
    "start-ppt.cmd",
    "install-ppt.cmd",
    "NOIR_STUDIO.md",
    "NOIR_REQUEST.md",
    "start-noir.cmd",
    "install-noir.cmd",
)
RUNTIME_DIRS = ("agents", "references", "scripts", "examples", "tests", "skills", "tools")
KIT_FILES = (
    "START_HERE.md",
    "CODEX_INSTALL_AND_RUN.txt",
    "REQUEST_TEMPLATE.md",
    "install_skill.py",
    "verify_package.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def copy_runtime(repo: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    for filename in RUNTIME_ROOT_FILES:
        shutil.copy2(repo / filename, destination / filename)
    for dirname in RUNTIME_DIRS:
        shutil.copytree(
            repo / dirname,
            destination / dirname,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )


def build(repo: Path, output: Path) -> None:
    team_kit = repo / "team-kit"
    with tempfile.TemporaryDirectory(prefix="image2-pitch-kit-") as temp:
        package = Path(temp) / KIT_NAME
        package.mkdir()
        for filename in KIT_FILES:
            shutil.copy2(team_kit / filename, package / filename)

        copy_runtime(repo, package / "skill" / SKILL_NAME)
        records = []
        for path in sorted(p for p in package.rglob("*") if p.is_file()):
            records.append(
                {
                    "path": path.relative_to(package).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )

        manifest = {
            "package": KIT_NAME,
            "skill": SKILL_NAME,
            "schema_version": 1,
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_repository": "https://github.com/wangqi045788-byte/bp-to-image2-pitch-deck",
            "source_commit": git_head(repo),
            "entrypoint": "CODEX_INSTALL_AND_RUN.txt",
            "skill_entrypoint": f"skill/{SKILL_NAME}/SKILL.md",
            "files": records,
        }
        (package / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(p for p in package.rglob("*") if p.is_file()):
                archive.write(path, path.relative_to(package.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    build(repo, args.out.resolve())
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
