from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("ppt_launcher", TOOLS / "ppt.py")
launcher = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(launcher)


def make_skill_tree(root: Path) -> None:
    for name in launcher.SKILL_NAMES:
        skill = root / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n\nTest skill.\n", encoding="utf-8")
    noir = root / "skills" / "noir-ppt-studio"
    (noir / "scripts").mkdir()
    for script in ("export_editorial_svg.py", "qa_editorial_pptx.py"):
        (noir / "scripts" / script).write_text("# test fixture\n", encoding="utf-8")
    production = root / "skills" / "ppt-production"
    (production / "scripts").mkdir()
    (production / "scripts" / "build_deck.py").write_text("# test fixture\n", encoding="utf-8")


class PptLauncherTests(unittest.TestCase):
    def context(self, root: Path):
        make_skill_tree(root)
        return (
            patch.object(launcher, "REPO", root),
            patch.object(launcher, "CORE_SKILLS", launcher.SKILL_NAMES[:-1]),
        )

    def test_suite_preflight_prevents_partial_install_and_unrelated_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            target = root / "codex" / "skills"
            target.mkdir(parents=True)
            (target / "ppt-analysis").mkdir()
            (target / "ppt-analysis" / "SKILL.md").write_text("---\nname: ppt-analysis\n---\n", encoding="utf-8")
            (target / "ppt-quality").mkdir()
            (target / "ppt-quality" / "unrelated.txt").write_text("keep", encoding="utf-8")
            context = self.context(repo)
            with context[0], context[1], patch.object(launcher, "SKILL_NAMES", launcher.SKILL_NAMES):
                with self.assertRaises(ValueError):
                    launcher.install(target, replace=True)
            self.assertFalse((target / "ppt-studio").exists())
            self.assertEqual((target / "ppt-analysis" / "SKILL.md").read_text(encoding="utf-8"), "---\nname: ppt-analysis\n---\n")
            self.assertEqual((target / "ppt-quality" / "unrelated.txt").read_text(encoding="utf-8"), "keep")

    def test_install_copies_all_skills_and_replace_backs_up_only_matching_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            target = root / "codex" / "skills"
            context = self.context(repo)
            with context[0], context[1]:
                installed = launcher.install(target)
                self.assertEqual(set(installed), set(launcher.SKILL_NAMES))
                for name in launcher.SKILL_NAMES:
                    self.assertTrue((target / name / "SKILL.md").is_file())
                with self.assertRaises(FileExistsError):
                    launcher.install(target)
                launcher.install(target, replace=True)
            backups = list(target.glob("*.backup-*"))
            self.assertEqual(len(backups), len(launcher.SKILL_NAMES))
            for name in launcher.SKILL_NAMES:
                self.assertEqual(launcher._read_skill_name(target / name / "SKILL.md"), name)

    def test_destination_is_parent_not_filesystem_root_or_repo_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            repo.mkdir()
            context = self.context(repo)
            with context[0], context[1]:
                with self.assertRaises(ValueError):
                    launcher._validate_install_parent(Path(Path(repo.anchor)))
                with self.assertRaises(ValueError):
                    launcher._validate_install_parent(repo)
                with self.assertRaises(ValueError):
                    launcher._validate_install_parent(repo.parent)

    def test_dry_run_without_codex_bundles_suite_and_auto_never_defaults_to_noir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            brief = root / "brief.md"
            brief.write_text("Use supplied organization materials to create a management review.", encoding="utf-8")
            job = root / "job"
            context = self.context(repo)
            with context[0], context[1], patch.object(launcher.shutil, "which", return_value=None), patch.object(launcher.subprocess, "run", side_effect=AssertionError("dry-run must not start a child process")):
                self.assertEqual(launcher.generate(brief, job, dry_run=True), 0)
            prompt = (job / "request.md").read_text(encoding="utf-8")
            self.assertIn("Style mode is automatic", prompt)
            self.assertIn("Do not default to Noir or black and white", prompt)
            self.assertIn("Noir is optional", prompt)
            self.assertIn("Do not provide private chain-of-thought", prompt)
            self.assertIn("Use `$ppt-studio` as the coordinator skill", prompt)
            self.assertIn("invoke only those needed", prompt)
            self.assertIn("$ppt-analysis", prompt)
            self.assertIn("without claiming every chart or slide has an SVG source", prompt)
            for name in launcher.SKILL_NAMES:
                self.assertTrue((job / ".agents" / "skills" / name / "SKILL.md").is_file())

    def test_explicit_noir_style_is_opt_in(self):
        prompt = launcher._prompt("brief.md", Path("skills"), assets=False, style="Noir editorial photography with measured serif typography", deck_type="company introduction")
        self.assertIn("User-selected visual style: Noir editorial photography", prompt)
        self.assertIn("explicitly selected Noir", prompt)
        auto = launcher._prompt("brief.md", Path("skills"), assets=False, style="auto", deck_type="auto")
        self.assertNotIn("User-selected visual style: noir", auto)
        negative = launcher._prompt("brief.md", Path("skills"), assets=False, style="Avoid Noir and use restrained color photography", deck_type="auto")
        self.assertIn("Avoid Noir and use restrained color photography", negative)
        self.assertIn("Noir is optional and must not load", negative)

    def test_install_refuses_linked_parent_and_linked_skill_target_without_moving_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            link_parent = root / "linked-parent"
            try:
                os.symlink(external, link_parent, target_is_directory=True)
            except OSError:
                self.skipTest("creating a symbolic link is not enabled in this environment")
            with self.assertRaises(ValueError):
                launcher._validate_install_parent(link_parent)

            repo = root / "source"
            make_skill_tree(repo)
            target_parent = root / "skills"
            target_parent.mkdir()
            existing = external / "ppt-analysis"
            existing.mkdir()
            (existing / "SKILL.md").write_text("---\nname: ppt-analysis\n---\n", encoding="utf-8")
            linked_target = target_parent / "ppt-analysis"
            os.symlink(existing, linked_target, target_is_directory=True)
            with patch.object(launcher, "REPO", repo):
                with self.assertRaises(ValueError):
                    launcher.install(target_parent, replace=True)
            self.assertTrue(linked_target.is_symlink())
            self.assertEqual(launcher._read_skill_name(existing / "SKILL.md"), "ppt-analysis")

    def test_source_skill_tree_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            make_skill_tree(repo)
            external = root / "outside"
            external.mkdir()
            try:
                os.symlink(external, repo / "skills" / "ppt-design" / "linked", target_is_directory=True)
            except OSError:
                self.skipTest("creating a symbolic link is not enabled in this environment")
            with patch.object(launcher, "REPO", repo):
                with self.assertRaises(ValueError):
                    launcher._source_skills()

    def test_native_inspector_counts_chart_and_table_only_slides_and_rejects_picture_only(self):
        try:
            from pptx import Presentation
            from pptx.chart.data import CategoryChartData
            from pptx.enum.chart import XL_CHART_TYPE
            from pptx.util import Inches
            from PIL import Image
        except ImportError:
            self.skipTest("python-pptx and Pillow are not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = root / "native-frames.pptx"
            presentation = Presentation()
            chart_slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            data = CategoryChartData()
            data.categories = ["A", "B"]
            data.add_series("Revenue", [10, 12])
            chart_slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(6), Inches(4), data)
            table_slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            table_slide.shapes.add_table(2, 2, Inches(1), Inches(1), Inches(6), Inches(2))
            presentation.save(deck)
            report = launcher.inspect_powerpoint(deck)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["objects"][0]["charts"], 1)
            self.assertEqual(report["objects"][0]["text"], 0)
            self.assertEqual(report["objects"][1]["tables"], 1)
            self.assertEqual(report["objects"][1]["text"], 0)

            image = root / "only-picture.png"
            Image.new("RGB", (24, 16), "#efefef").save(image)
            picture_deck = root / "picture-only.pptx"
            picture_presentation = Presentation()
            slide = picture_presentation.slides.add_slide(picture_presentation.slide_layouts[6])
            slide.shapes.add_picture(str(image), Inches(0), Inches(0), width=Inches(13), height=Inches(7))
            picture_presentation.save(picture_deck)
            self.assertEqual(launcher.inspect_powerpoint(picture_deck)["status"], "fail")

    def test_mock_generation_preserves_existing_visual_qa_and_writes_separate_native_report(self):
        try:
            from pptx import Presentation
            from pptx.util import Inches
        except ImportError:
            self.skipTest("python-pptx is not installed")
        real_run = subprocess.run
        observed = {}

        def fake_run(command, **kwargs):
            if command[0] == "codex-fixture":
                observed["command"] = command
                cwd = Path(kwargs["cwd"])
                presentation = Presentation()
                slide = presentation.slides.add_slide(presentation.slide_layouts[6])
                slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = "Quarterly review"
                slide.shapes.add_shape(1, Inches(1), Inches(3), Inches(2), Inches(1))
                presentation.save(cwd / "output" / "deck.pptx")
                qa = cwd / "qa" / "qa_report.json"
                qa.parent.mkdir()
                qa.write_text('{"visual_review":{"status":"passed"}}', encoding="utf-8")
                return SimpleNamespace(returncode=0)
            return real_run(command, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            brief = root / "brief.md"
            brief.write_text("Quarterly review", encoding="utf-8")
            job = root / "job"
            context = self.context(repo)
            with context[0], context[1], patch.object(launcher.shutil, "which", return_value="codex-fixture"), patch.object(launcher.subprocess, "run", side_effect=fake_run):
                self.assertEqual(launcher.generate(brief, job), 0)
            command = observed["command"]
            self.assertIn("--sandbox", command)
            self.assertIn("workspace-write", command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
            self.assertEqual((job / "qa" / "qa_report.json").read_text(encoding="utf-8"), '{"visual_review":{"status":"passed"}}')
            report = json.loads((job / "qa" / "launcher-structure" / "native-structure.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "pass")

    def test_demo_uses_real_production_builder_and_preserves_its_source(self):
        try:
            from pptx import Presentation
            from pptx.util import Inches
        except ImportError:
            self.skipTest("python-pptx is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "demo"
            source = launcher.REPO / "examples" / "generic-demo" / "deck.json"
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            # Keep credentials and Python path overrides out of this real CLI run.
            clean_env = {
                key: value
                for key, value in os.environ.items()
                if key in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH"}
            }
            clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
            clean_env["PYTHONUTF8"] = "1"
            command = [sys.executable, str(TOOLS / "ppt.py"), "demo", "--out", str(out)]
            result = subprocess.run(command, cwd=TOOLS.parent, env=clean_env, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
            self.assertTrue((out / "deck.json").is_file())
            self.assertTrue((out / "deck.pptx").is_file())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)
            report = json.loads((out / "qa" / "launcher-structure" / "native-structure.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["slides"], 3)
            self.assertTrue(any(slide["tables"] for slide in report["objects"]))
            self.assertTrue(any(slide["charts"] for slide in report["objects"]))


if __name__ == "__main__":
    unittest.main()
