from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_prompt_pack import build_prompt_pack  # noqa: E402
from public_release_check import scan_tree  # noqa: E402
from validate_deck_brief import validate  # noqa: E402


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.demo_path = ROOT / "examples" / "public-demo" / "deck-brief.json"
        self.demo = json.loads(self.demo_path.read_text(encoding="utf-8"))

    def test_public_demo_is_valid(self):
        errors, warnings = validate(self.demo)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_prompt_pack_contains_every_slide_and_exact_copy(self):
        prompt_pack = build_prompt_pack(self.demo)
        self.assertEqual(prompt_pack.count("## Slide "), 3)
        self.assertIn("Four handoffs fragment the operating picture", prompt_pack)
        self.assertIn("E02 [user_assertion, medium]", prompt_pack)
        self.assertIn("High complexity means precise relationships", prompt_pack)

    def test_public_mode_rejects_private_source(self):
        changed = json.loads(json.dumps(self.demo))
        changed["inputs"]["sources"][0]["label"] = "private"
        errors, _ = validate(changed)
        self.assertTrue(any("not allowed in public mode" in error for error in errors))

    def test_derived_evidence_requires_methodology(self):
        changed = json.loads(json.dumps(self.demo))
        changed["evidence_cards"][0]["evidence_type"] = "derived"
        errors, _ = validate(changed)
        self.assertTrue(any("methodology" in error for error in errors))

    def test_numeric_copy_without_evidence_warns(self):
        changed = json.loads(json.dumps(self.demo))
        changed["slides"][0]["content"][0]["text"] = "Version 2 operating view"
        _, warnings = validate(changed)
        self.assertTrue(any("numeric-looking copy" in warning for warning in warnings))

    def test_copyfit_blocks_overflow(self):
        changed = json.loads(json.dumps(self.demo))
        changed["slides"][0]["copyfit"]["title_max_chars"] = 5
        errors, _ = validate(changed)
        self.assertTrue(any("exceeds copyfit limit" in error for error in errors))

    def test_release_scan_accepts_clean_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("Synthetic public example\n", encoding="utf-8")
            self.assertEqual(scan_tree(root, []), [])

    def test_release_scan_finds_private_denylist_term(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "notes.md").write_text("Project Nightingale\n", encoding="utf-8")
            findings = scan_tree(root, ["Project Nightingale"])
            self.assertTrue(any(item["kind"] == "private denylist term" for item in findings))

    def test_init_job_refuses_nonempty_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "job"
            target.mkdir()
            (target / "keep.txt").write_text("keep", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_job.py"), str(target), "--title", "Demo"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertTrue((target / "keep.txt").exists())

    def test_init_job_creates_isolated_structure(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "job"
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_job.py"), str(target), "--title", "Demo"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((target / "input" / "bp").is_dir())
            self.assertTrue((target / "work" / "prompts").is_dir())
            self.assertTrue((target / "output").is_dir())

    def test_release_scan_blocks_office_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "client-deck.pptx").write_bytes(b"not-a-real-pptx")
            findings = scan_tree(root, [])
            self.assertTrue(any(item["kind"] == "blocked binary/archive" for item in findings))

    def test_prepare_generation_writes_prompt_pack(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prompt-pack.md"
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "prepare_generation.py"), str(self.demo_path), "--out", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output.exists())
            self.assertIn("READY_FOR_IMAGE2", completed.stdout)


if __name__ == "__main__":
    unittest.main()
