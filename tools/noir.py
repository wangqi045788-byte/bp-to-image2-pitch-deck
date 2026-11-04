#!/usr/bin/env python3
"""Install, start, and smoke-test the Noir PPT Studio Codex skill."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import posixpath
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Sequence
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
SKILL_SOURCE = REPO / "skills" / "noir-ppt-studio"
SKILL_NAME = "noir-ppt-studio"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"p": P_NS, "a": A_NS}


def _skill_root(path: Path = SKILL_SOURCE) -> Path:
    path = path.resolve()
    if not (path / "SKILL.md").is_file():
        raise FileNotFoundError(f"Skill package is incomplete: {path / 'SKILL.md'}")
    for rel in ("scripts/export_editorial_svg.py", "scripts/qa_editorial_pptx.py"):
        if not (path / rel).is_file():
            raise FileNotFoundError(f"Skill package is incomplete: {path / rel}")
    return path


def _default_skill_parent() -> Path:
    home = os.environ.get("CODEX_HOME")
    return Path(home).expanduser() / "skills" if home else Path.home() / ".codex" / "skills"


def install(dest: Path | None = None, *, replace: bool = False) -> Path:
    source = _skill_root()
    target = (dest or (_default_skill_parent() / SKILL_NAME)).expanduser().resolve()
    repo = REPO.resolve()
    if target.name != SKILL_NAME:
        raise ValueError(f"Install destination must end with the skill folder name: {SKILL_NAME}")
    if target == Path(target.anchor) or target == repo or repo in target.parents:
        raise ValueError("Install destination cannot be a filesystem root or an ancestor/part of this repository.")
    if target == source or source in target.parents or target in source.parents:
        raise ValueError("Install destination cannot overlap the source skill or its parent directories.")
    if target.exists() and not replace:
        raise FileExistsError(f"Skill already exists: {target}. Use --replace to make a dated backup first.")
    if target.exists():
        if not target.is_dir():
            raise ValueError(f"Install destination exists and is not a skill folder: {target}")
        old_skill_md = target / "SKILL.md"
        if not old_skill_md.is_file() or f"name: {SKILL_NAME}" not in old_skill_md.read_text(encoding="utf-8"):
            raise ValueError(f"Refusing to replace an unrelated directory; expected a {SKILL_NAME} Skill at {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".noir-ppt-stage-", dir=target.parent)) / SKILL_NAME
    try:
        shutil.copytree(source, stage, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        backup = None
        if target.exists():
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = target.with_name(f"{target.name}.backup-{stamp}")
            if backup.exists():
                raise FileExistsError(f"Backup path already exists: {backup}")
            target.replace(backup)
        try:
            stage.replace(target)
        except Exception:
            if backup and backup.exists() and not target.exists():
                backup.replace(target)
            raise
    finally:
        shutil.rmtree(stage.parent, ignore_errors=True)
    print(f"Installed: {target}")
    if backup:
        print(f"Previous copy preserved: {backup}")
    print("Codex discovers skills on its normal skill refresh/restart.")
    return target


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _copy_tree_no_links(source: Path, target: Path) -> None:
    source = source.expanduser().resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f"Assets path is not a directory: {source}")
    for path in source.rglob("*"):
        if _is_link_or_junction(path):
            raise ValueError(f"Assets directory contains a symbolic link or junction: {path}")
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=False)


def _new_job_path(path: Path) -> Path:
    path = path.expanduser().resolve(strict=False)
    repo = REPO.resolve()
    if path == repo or repo in path.parents:
        raise ValueError("Job directory must be outside the repository to keep private work out of Git.")
    if path.exists():
        raise FileExistsError(f"Job directory already exists; choose a new path: {path}")
    return path


def _generation_prompt(brief_name: str, skill_path: Path, *, assets: bool) -> str:
    asset_line = "Read the user's explicitly supplied assets in input/assets." if assets else "Do not expect or invent company assets beyond any cited public sources you can access."
    return f"""Work only inside this new job directory and follow `{skill_path / 'SKILL.md'}` by explicitly invoking `$noir-ppt-studio`.

Read `input/{brief_name}` as the user's full brief. {asset_line}
Create an evidence-aware, visually deliberate presentation; preserve required facts and sources; create useful SVG sources and an editable native PowerPoint; then run the skill's structural and applicable visual QA. Keep all work and outputs inside this directory. Save the finished editable deck exactly as `output/deck.pptx` and write Chinese usage/QA notes to `output/交付说明.txt`.

Use only image and research tools actually available to this Codex run. Do not claim a specific image model unless the tool reports its model identifier. If a required tool, source, or render route is unavailable, state the precise limitation and finish every independent part. Never make up render evidence or mark visual QA complete without inspection. Do not install software, change global settings, contact external people, or upload user materials."""


def generate(brief: Path, job: Path, *, assets: Path | None = None, dry_run: bool = False) -> int:
    brief = brief.expanduser().resolve(strict=True)
    if not brief.is_file():
        raise FileNotFoundError(f"Brief is not a file: {brief}")
    job = _new_job_path(job)
    assets_root = None
    if assets is not None:
        assets_root = assets.expanduser().resolve(strict=True)
        if job == assets_root or assets_root in job.parents:
            raise ValueError("Job directory cannot be inside the assets directory; that would recursively copy the job into itself.")
    codex = shutil.which("codex")
    if not dry_run and not codex:
        raise FileNotFoundError("Codex CLI was not found on PATH. Install it from the official Codex distribution or open Codex terminal.")
    skill_target = job / ".agents" / "skills" / SKILL_NAME
    job.mkdir(parents=True)
    try:
        (job / "input").mkdir()
        brief_copy = job / "input" / f"brief{brief.suffix or '.txt'}"
        shutil.copy2(brief, brief_copy)
        if assets_root is not None:
            _copy_tree_no_links(assets_root, job / "input" / "assets")
        _skill_root()
        shutil.copytree(SKILL_SOURCE, skill_target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (job / "output").mkdir()
        (job / "request.md").write_text(
            _generation_prompt(brief_copy.name, skill_target, assets=assets is not None) + "\n",
            encoding="utf-8",
        )
        cmd = [codex, "exec", "--sandbox", "workspace-write", "--skip-git-repo-check", "--cd", str(job), "--output-last-message", str(job / "codex-result.md"), "-"]
        print(f"Job: {job}")
        print(f"Brief copied to: {brief_copy}")
        if dry_run:
            print("Dry run: Codex was not started.")
            print(f"Request: {job / 'request.md'}")
            display_cmd = cmd[:-1] + ["<stdin: request.md>"]
            display_cmd[0] = codex or "codex"
            print("Command:", subprocess.list2cmdline(display_cmd))
            return 0
        with (job / "request.md").open("r", encoding="utf-8") as request:
            completed = subprocess.run(cmd, stdin=request, cwd=job, check=False)
        if completed.returncode:
            print(f"Codex stopped with exit code {completed.returncode}. Job files were preserved for recovery.", file=sys.stderr)
            return completed.returncode
        deck = job / "output" / "deck.pptx"
        if not deck.is_file():
            print(f"Codex exited successfully but did not create the required file: {deck}", file=sys.stderr)
            return 2
        native = inspect_native_pptx(deck)
        if native["status"] != "pass":
            print(f"PPTX native-structure check failed: {native}", file=sys.stderr)
            return 2
        qa_script = skill_target / "scripts" / "qa_editorial_pptx.py"
        qa_dir = job / "qa" / "launcher-structure"
        qa = subprocess.run(
            [sys.executable, str(qa_script), str(deck), "--out-dir", str(qa_dir), "--expected-slides", str(native["slides"]), "--min-text-per-slide", "1", "--skip-office-render"],
            cwd=job,
            check=False,
        )
        if qa.returncode not in (0, 2):
            print(f"Structural QA reported failure; see {qa_dir / 'qa_report.json'}", file=sys.stderr)
            return qa.returncode or 2
        report = json.loads((qa_dir / "qa_report.json").read_text(encoding="utf-8"))
        if report.get("structure", {}).get("status") != "pass":
            print(f"Structural QA did not pass; see {qa_dir / 'qa_report.json'}", file=sys.stderr)
            return 2
        (job / "native-structure.json").write_text(json.dumps(native, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        totals = {kind: sum(slide[kind] for slide in native["objects"]) for kind in ("text", "geometry", "pictures")}
        print(f"PPTX created; verified native object counts (text, geometry, pictures): {totals} — {deck}")
        print(f"Structural QA: {qa_dir / 'qa_report.json'}")
        print("Human visual review and any requested PowerPoint render/editability check remain separate from this structural pass.")
        return 0
    except Exception:
        # Preserve a partially written job for explicit recovery and inspection.
        raise


def inspect_native_pptx(deck: Path) -> dict:
    """Read Open XML counts without changing the user's presentation."""
    if not deck.is_file() or deck.suffix.lower() != ".pptx":
        return {"status": "fail", "reason": "deck.pptx is absent or is not a PPTX file"}
    slides: list[dict[str, int]] = []
    try:
        with zipfile.ZipFile(deck) as archive:
            bad_member = archive.testzip()
            if bad_member:
                return {"status": "fail", "reason": f"corrupt ZIP member: {bad_member}"}
            names = set(archive.namelist())
            presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
            presentation_rels = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
            rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
            office_rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            rel_targets = {
                rel.get("Id"): rel.get("Target")
                for rel in presentation_rels.findall(f"{{{rel_ns}}}Relationship")
                if rel.get("Type", "").endswith("/slide")
            }
            slide_paths = []
            for slide_ref in presentation.findall(".//p:sldId", NS):
                rel_id = slide_ref.get(f"{{{office_rel_ns}}}id")
                target = rel_targets.get(rel_id)
                if not target:
                    raise KeyError(f"No slide relationship for {rel_id}")
                slide_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("ppt", target))
                if slide_path not in names:
                    raise KeyError(f"Slide part is missing: {slide_path}")
                slide_paths.append(slide_path)
            for slide_path in slide_paths:
                root = ET.fromstring(archive.read(slide_path))
                shapes = root.findall(".//p:sp", NS)
                text_shapes = sum(any((run.text or "").strip() for run in shape.findall(".//a:t", NS)) for shape in shapes)
                slides.append({"text": text_shapes, "geometry": len(shapes) - text_shapes, "pictures": len(root.findall(".//p:pic", NS))})
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        return {"status": "fail", "reason": str(exc)}
    if not slides or any(sum(counts.values()) == 0 or counts["text"] == 0 for counts in slides):
        return {"status": "fail", "reason": "each slide must contain at least one native text object and some native content", "slides": slides}
    return {"status": "pass", "slides": len(slides), "objects": slides, "package_crc": "pass"}


def demo(out: Path) -> int:
    out = _new_job_path(out)
    skill = _skill_root()
    out.mkdir(parents=True)
    try:
        sample = REPO / "examples" / "noir-demo"
        for rel in ("job.json", "pages/slide_01.json", "pages/slide_02.json"):
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sample / rel, out / rel)
        exporter = skill / "scripts" / "export_editorial_svg.py"
        qa_script = skill / "scripts" / "qa_editorial_pptx.py"
        job = out / "job.json"
        result = subprocess.run([sys.executable, str(exporter), str(job)], cwd=out, check=False)
        if result.returncode:
            return result.returncode
        deck = out / "output" / "noir-demo.pptx"
        native = inspect_native_pptx(deck)
        if native["status"] != "pass" or len(native.get("objects", [])) != 2:
            print(f"Demo native-structure check failed: {native}", file=sys.stderr)
            return 2
        qa_dir = out / "qa"
        qa = subprocess.run([sys.executable, str(qa_script), str(deck), "--out-dir", str(qa_dir), "--expected-slides", "2", "--min-text-per-slide", "1", "--skip-office-render"], cwd=out, check=False)
        report_path = qa_dir / "qa_report.json"
        if qa.returncode not in (0, 2) or not report_path.is_file():
            print("Offline QA could not produce a report.", file=sys.stderr)
            return 2
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("structure", {}).get("status") != "pass":
            print(f"Demo structural QA failed; see {report_path}", file=sys.stderr)
            return 2
        print(f"Editable demo created: {deck}")
        print(f"Linked SVG sources: {out / 'svg'}")
        print(f"Offline structural QA: {report_path}")
        print("This demo has no photo and has not received human visual review.")
        return 0
    except Exception:
        raise


def doctor() -> int:
    print(f"Python: {sys.version.split()[0]} ({'supported' if sys.version_info >= (3, 10) else 'requires >=3.10'})")
    for module, label in (("pptx", "python-pptx"), ("lxml", "lxml")):
        try:
            available = __import__(module) is not None
        except Exception:
            available = False
        print(f"{label}: {'available' if available else 'missing'}")
    print(f"Codex CLI: {shutil.which('codex') or 'not found'}")
    print(f"Skill package: {'available' if SKILL_SOURCE.is_dir() and (SKILL_SOURCE / 'SKILL.md').is_file() else 'incomplete'}")
    print("Image generation, Office render and font availability are selected per job and are not inferred by this check.")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("doctor", help="list available local tools by name")
    p.set_defaults(func=lambda a: doctor())
    p = sub.add_parser("install", help="copy the skill to your Codex skills folder")
    p.add_argument("--dest", type=Path, help="install at this path instead of CODEX_HOME/.codex/skills")
    p.add_argument("--replace", action="store_true", help="preserve the old skill in a dated backup before replacing")
    p.set_defaults(func=lambda a: install(a.dest, replace=a.replace) and 0)
    p = sub.add_parser("generate", help="start a contained Codex presentation job")
    p.add_argument("--brief", required=True, type=Path)
    p.add_argument("--job", required=True, type=Path, help="new output directory outside this repository")
    p.add_argument("--assets", type=Path, help="optional folder of assets to copy into the private job")
    p.add_argument("--dry-run", action="store_true", help="prepare inputs and the request, but do not start Codex")
    p.set_defaults(func=lambda a: generate(a.brief, a.job, assets=a.assets, dry_run=a.dry_run))
    p = sub.add_parser("demo", help="build and offline-check a two-slide editable sample")
    p.add_argument("--out", required=True, type=Path, help="new output directory outside this repository")
    p.set_defaults(func=lambda a: demo(a.out))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"noir: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
