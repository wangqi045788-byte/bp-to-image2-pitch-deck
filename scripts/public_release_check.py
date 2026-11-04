#!/usr/bin/env python3
"""Fail closed when a proposed public skill release contains risky material."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
BLOCKED_SUFFIXES = {
    ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".pdf", ".key",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".pem", ".p12", ".pfx", ".sqlite", ".db",
}
BLOCKED_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
BLOCKED_SEGMENTS = {"input", "private", "raw-inputs", "customer-assets", "generated_images", "generated-images"}
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".js", ".mjs", ".ts", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".csv", ".html", ".css", ".sh", ".ps1", ".cmd", ".gitignore", "",
}
# One reviewed OFL font, not a blanket exemption for binaries or fonts.
REVIEWED_BINARY_SHA256 = {
    "skills/noir-ppt-studio/assets/fonts/BodoniModaEditorial-Regular.ttf":
        "1ff6ca16c3b88d7434c77817c4099f55e5d554c38818676b58ee92cdec318d4e",
}
PATTERNS = {
    "private Windows path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
    "private Unix path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic secret assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|private[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"
    ),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
}


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        yield path, relative


def load_denylist(path: Path | None) -> list[str]:
    if path is None:
        return []
    values: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            values.append(value)
    return values


def scan_tree(root: Path, denylist: list[str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path, relative in iter_files(root):
        lower_parts = {part.lower() for part in relative.parts}
        if lower_parts & BLOCKED_SEGMENTS:
            findings.append({"path": str(relative), "kind": "blocked directory", "match": sorted(lower_parts & BLOCKED_SEGMENTS)[0]})
        if path.name.lower() in BLOCKED_NAMES:
            findings.append({"path": str(relative), "kind": "blocked filename", "match": path.name})
        if path.suffix.lower() in BLOCKED_SUFFIXES:
            findings.append({"path": str(relative), "kind": "blocked binary/archive", "match": path.suffix.lower()})
            continue
        approved_digest = REVIEWED_BINARY_SHA256.get(relative.as_posix())
        if approved_digest:
            if hashlib.sha256(path.read_bytes()).hexdigest() != approved_digest:
                findings.append({"path": str(relative), "kind": "reviewed binary changed", "match": "SHA-256 mismatch"})
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", "Makefile", "LICENSE.ppt-master", "LICENSE.figedit"}:
            findings.append({"path": str(relative), "kind": "unreviewed file type", "match": path.suffix or path.name})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append({"path": str(relative), "kind": "non-UTF-8 file", "match": "binary or unknown encoding"})
            continue
        for name, pattern in PATTERNS.items():
            match = pattern.search(text)
            if match:
                findings.append({"path": str(relative), "kind": name, "match": match.group(0)[:120]})
        folded = text.casefold()
        for term in denylist:
            if term.casefold() in folded:
                findings.append({"path": str(relative), "kind": "private denylist term", "match": term})
    return findings


def scan_git_history(root: Path, denylist: list[str]) -> list[dict[str, str]]:
    if not (root / ".git").exists():
        return []
    findings: list[dict[str, str]] = []
    commands = [
        ["git", "-C", str(root), "log", "--all", "--format=%H%x09%s"],
        ["git", "-C", str(root), "rev-list", "--objects", "--all"],
    ]
    history_text = ""
    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if completed.returncode != 0:
            findings.append({"path": ".git", "kind": "history scan failure", "match": completed.stderr.strip()[:160]})
        history_text += completed.stdout + "\n"
    for name, pattern in PATTERNS.items():
        match = pattern.search(history_text)
        if match:
            findings.append({"path": ".git", "kind": f"history {name}", "match": match.group(0)[:120]})
    folded = history_text.casefold()
    for term in denylist:
        if term.casefold() in folded:
            findings.append({"path": ".git", "kind": "history private denylist term", "match": term})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--denylist", type=Path, help="Private terms file stored outside the repository")
    parser.add_argument("--skip-history", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        denylist = load_denylist(args.denylist)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    findings = scan_tree(root, denylist)
    if not args.skip_history:
        findings.extend(scan_git_history(root, denylist))
    result = {"status": "READY" if not findings else "BLOCKED", "root": str(root), "findings": findings}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {len(findings)} finding(s)")
        for finding in findings:
            print(f"{finding['kind']}: {finding['path']} -> {finding['match']}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
