from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "noir.py"
SPEC = importlib.util.spec_from_file_location("noir_launcher", SCRIPT)
noir = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(noir)


class NoirLauncherTests(unittest.TestCase):
    def test_install_is_no_clobber_and_replace_keeps_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skills" / "noir-ppt-studio"
            installed = noir.install(target)
            self.assertTrue((installed / "SKILL.md").is_file())
            (installed / "personal.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                noir.install(target)
            noir.install(target, replace=True)
            backups = list(target.parent.glob("noir-ppt-studio.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "personal.txt").read_text(encoding="utf-8"), "keep")

    def test_install_refuses_to_replace_unrelated_directory_or_bad_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            unrelated = Path(tmp) / "noir-ppt-studio"
            unrelated.mkdir()
            (unrelated / "notes.txt").write_text("valuable", encoding="utf-8")
            with self.assertRaises(ValueError):
                noir.install(unrelated, replace=True)
            self.assertEqual((unrelated / "notes.txt").read_text(encoding="utf-8"), "valuable")
            with self.assertRaises(ValueError):
                noir.install(Path(tmp) / "wrong-name")
            with self.assertRaises(ValueError):
                noir.install(noir.REPO.parent)

    def test_generate_dry_run_copies_brief_and_bundles_skill_without_calling_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "brief.md"
            brief.write_text("A fictional museum pitch", encoding="utf-8")
            job = root / "private" / "job-1"
            with patch.object(noir.subprocess, "run", side_effect=AssertionError("dry-run called a subprocess")):
                self.assertEqual(noir.generate(brief, job, dry_run=True), 0)
            self.assertEqual((job / "input" / "brief.md").read_text(encoding="utf-8"), "A fictional museum pitch")
            self.assertTrue((job / ".agents" / "skills" / "noir-ppt-studio" / "SKILL.md").is_file())
            request = (job / "request.md").read_text(encoding="utf-8")
            self.assertIn("$noir-ppt-studio", request)
            self.assertFalse((job / "output" / "deck.pptx").exists())

    def test_job_cannot_be_created_inside_repository_or_overwrite_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = Path(tmp) / "brief.md"
            brief.write_text("brief", encoding="utf-8")
            with self.assertRaises(ValueError):
                noir.generate(brief, noir.REPO / "private-job", dry_run=True)
            exists = Path(tmp) / "exists"
            exists.mkdir()
            with self.assertRaises(FileExistsError):
                noir.generate(brief, exists, dry_run=True)

    def test_job_cannot_be_nested_under_the_assets_it_would_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            assets.mkdir()
            brief = root / "brief.md"
            brief.write_text("brief", encoding="utf-8")
            job = assets / "new-job"
            with self.assertRaises(ValueError):
                noir.generate(brief, job, assets=assets, dry_run=True)
            self.assertFalse(job.exists())

    def test_prompt_does_not_request_bypass_or_invent_model(self):
        prompt = noir._generation_prompt("brief.md", Path(".agents/skills/noir-ppt-studio"), assets=False)
        self.assertIn("Do not claim a specific image model", prompt)
        self.assertIn("Never make up render evidence", prompt)
        self.assertNotIn("dangerously-bypass", prompt)
        self.assertNotIn("OPENAI_API_KEY", prompt)

    def test_generation_invokes_codex_with_scoped_workspace_and_checks_its_pptx(self):
        try:
            from pptx import Presentation
            from pptx.util import Inches
        except ImportError:
            self.skipTest("python-pptx is not installed in this Python")
        real_run = subprocess.run
        seen = {}

        def fake_run(command, **kwargs):
            if command[0] == "codex-test-stub":
                seen["command"] = command
                deck = Path(kwargs["cwd"]) / "output" / "deck.pptx"
                presentation = Presentation()
                slide = presentation.slides.add_slide(presentation.slide_layouts[6])
                slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = "Test title"
                slide.shapes.add_shape(1, Inches(1), Inches(3), Inches(2), Inches(1))
                presentation.save(deck)
                Path(kwargs["cwd"], "slide.svg").write_text("<svg/>", encoding="utf-8")
                old_qa = Path(kwargs["cwd"], "qa", "qa_report.json")
                old_qa.parent.mkdir(parents=True)
                old_qa.write_text('{"visual_review":{"status":"passed"}}', encoding="utf-8")
                return SimpleNamespace(returncode=0)
            return real_run(command, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "brief.md"
            brief.write_text("Test brief", encoding="utf-8")
            job = root / "job"
            with patch.object(noir.shutil, "which", return_value="codex-test-stub"), patch.object(noir.subprocess, "run", side_effect=fake_run):
                self.assertEqual(noir.generate(brief, job), 0)
            command = seen["command"]
            self.assertIn("--sandbox", command)
            self.assertIn("workspace-write", command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
            self.assertIn(str(job), command)
            self.assertTrue((job / "native-structure.json").is_file())
            self.assertEqual((job / "qa" / "qa_report.json").read_text(encoding="utf-8"), '{"visual_review":{"status":"passed"}}')
            report = json.loads((job / "qa" / "launcher-structure" / "qa_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["structure"]["status"], "pass")
            inventory = json.loads((job / "native-structure.json").read_text(encoding="utf-8"))
            self.assertEqual(inventory["objects"][0]["pictures"], 0)

    def test_native_inspection_follows_presentation_relationship_order(self):
        try:
            from pptx import Presentation
            from pptx.util import Inches
        except ImportError:
            self.skipTest("python-pptx is not installed in this Python")
        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp) / "reordered.pptx"
            presentation = Presentation()
            one = presentation.slides.add_slide(presentation.slide_layouts[6])
            one.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = "one"
            two = presentation.slides.add_slide(presentation.slide_layouts[6])
            two.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = "two-a"
            two.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(1)).text = "two-b"
            presentation.save(deck)
            replacement = deck.with_name("reordered-copy.pptx")
            ET.register_namespace("p", noir.P_NS)
            ET.register_namespace("a", noir.A_NS)
            with zipfile.ZipFile(deck) as source, zipfile.ZipFile(replacement, "w", zipfile.ZIP_DEFLATED) as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "ppt/presentation.xml":
                        root = ET.fromstring(data)
                        slide_list = root.find("p:sldIdLst", noir.NS)
                        refs = list(slide_list)
                        slide_list[:] = list(reversed(refs))
                        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    target.writestr(info, data)
            inventory = noir.inspect_native_pptx(replacement)
            self.assertEqual(inventory["status"], "pass")
            self.assertEqual([slide["text"] for slide in inventory["objects"]], [2, 1])

    def test_empty_text_run_does_not_count_as_native_text(self):
        try:
            from pptx import Presentation
            from pptx.util import Inches
        except ImportError:
            self.skipTest("python-pptx is not installed in this Python")
        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp) / "empty.pptx"
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = "text"
            slide.shapes.add_shape(1, Inches(1), Inches(3), Inches(2), Inches(1))
            presentation.save(deck)
            replacement = deck.with_name("empty-copy.pptx")
            ET.register_namespace("p", noir.P_NS)
            ET.register_namespace("a", noir.A_NS)
            with zipfile.ZipFile(deck) as source, zipfile.ZipFile(replacement, "w", zipfile.ZIP_DEFLATED) as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "ppt/slides/slide1.xml":
                        root = ET.fromstring(data)
                        run = root.find(".//a:t", noir.NS)
                        run.text = "   "
                        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    target.writestr(info, data)
            inventory = noir.inspect_native_pptx(replacement)
            self.assertEqual(inventory["status"], "fail")
            self.assertEqual(inventory["slides"][0]["text"], 0)

    def test_demo_builds_native_pptx_and_svg_when_dependencies_are_available(self):
        try:
            import lxml.etree  # noqa: F401
            import pptx  # noqa: F401
        except ImportError:
            self.skipTest("optional conversion dependencies are not installed in this Python")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo"
            self.assertEqual(noir.demo(out), 0)
            self.assertTrue((out / "output" / "noir-demo.pptx").is_file())
            self.assertEqual(len(list((out / "svg").glob("slide_*.svg"))), 2)
            inventory = noir.inspect_native_pptx(out / "output" / "noir-demo.pptx")
            self.assertEqual(inventory["status"], "pass")
            self.assertEqual(inventory["slides"], 2)
            report = json.loads((out / "qa" / "qa_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["structure"]["status"], "pass")
            self.assertEqual(report["visual_review"]["status"], "not_performed")


if __name__ == "__main__":
    unittest.main()
