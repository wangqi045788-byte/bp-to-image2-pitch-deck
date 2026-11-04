from __future__ import annotations

import hashlib
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
import types
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "noir-ppt-studio" / "scripts" / "qa_editorial_pptx.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_fixture(root: Path, *, slides: int = 2, ratio: tuple[int, int] = (16, 9)) -> Path:
    deck = Presentation()
    deck.slide_width = Inches(ratio[0])
    deck.slide_height = Inches(ratio[1])
    blank = deck.slide_layouts[6]

    for index in range(1, slides + 1):
        slide = deck.slides.add_slide(blank)
        title = slide.shapes.add_textbox(Inches(1), Inches(0.6), Inches(12), Inches(0.7))
        title.text_frame.text = "Été — édition de contrôle"
        subtitle = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(10), Inches(0.5))
        subtitle.text_frame.text = f"Diapositive de test {index}"
        slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(1),
            Inches(2.5),
            Inches(2),
            Inches(1),
        )
        slide.notes_slide.notes_text_frame.text = f"备注：第 {index} 页，仅用于 QA 自动化测试。"

    source = root / "synthetic_deck.pptx"
    deck.save(source)
    return source


def run_cli(deck: Path, out_dir: Path, *options: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(deck), "--out-dir", str(out_dir), *options],
        cwd=deck.parent,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def report_at(out_dir: Path) -> dict:
    return json.loads((out_dir / "qa_report.json").read_text(encoding="utf-8"))


class EditorialPptxQaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="qa_editorial_pptx_")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_structural_audit_supports_arbitrary_slide_count_and_preserves_source(self) -> None:
        deck = make_fixture(self.root, slides=2)
        original_hash = sha256(deck)
        out_dir = self.root / "qa_structure"
        result = run_cli(
            deck,
            out_dir,
            "--expected-slides",
            "2",
            "--min-text-per-slide",
            "2",
            "--expected-aspect-ratio",
            "16:9",
            "--skip-office-render",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_at(out_dir)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["structure"]["status"], "pass")
        self.assertEqual(report["structure"]["package_crc"]["status"], "pass")
        self.assertEqual(report["structure"]["slide_count"], 2)
        self.assertEqual(len(report["structure"]["slides"]), 2)
        for slide in report["structure"]["slides"]:
            self.assertEqual(slide["native_text_shapes"], 2)
            self.assertEqual(slide["native_geometry_shapes"], 1)
            self.assertEqual(slide["pictures"], 0)
            self.assertTrue(slide["notes_nonempty"])
        self.assertEqual(report["office_render"]["status"], "not_requested")
        self.assertEqual(report["editability_probe"]["status"], "not_requested")
        self.assertEqual(report["visual_review"]["status"], "not_performed")
        self.assertIn("human visual review", " ".join(report["unexecuted"]).lower())
        self.assertEqual(sha256(deck), original_hash)

    def test_aspect_ratio_is_only_checked_when_requested(self) -> None:
        deck = make_fixture(self.root, slides=1, ratio=(4, 3))
        without_ratio = run_cli(deck, self.root / "qa_no_ratio", "--expected-slides", "1", "--skip-office-render")
        self.assertEqual(without_ratio.returncode, 0, without_ratio.stdout + without_ratio.stderr)
        self.assertEqual(report_at(self.root / "qa_no_ratio")["structure"]["aspect_ratio_check"]["status"], "not_requested")

        with_ratio = run_cli(
            deck,
            self.root / "qa_require_ratio",
            "--expected-aspect-ratio",
            "16:9",
            "--skip-office-render",
        )
        self.assertEqual(with_ratio.returncode, 1, with_ratio.stdout + with_ratio.stderr)
        report = report_at(self.root / "qa_require_ratio")
        self.assertEqual(report["structure"]["aspect_ratio_check"]["status"], "fail")
        self.assertEqual(report["status"], "fail")

    def test_embed_output_rejects_the_source_path_without_changing_it(self) -> None:
        deck = make_fixture(self.root, slides=1)
        original_hash = sha256(deck)
        out_dir = self.root / "qa_same_path"
        result = run_cli(
            deck,
            out_dir,
            "--embed-output",
            str(deck),
            "--skip-office-render",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different from the input", result.stderr.lower())
        self.assertEqual(sha256(deck), original_hash)
        self.assertFalse((out_dir / "qa_report.json").exists())

    def test_office_backend_status_explains_non_windows_and_missing_pywin32(self) -> None:
        if not SCRIPT.is_file():
            self.fail("QA CLI module does not exist yet")
        spec = importlib.util.spec_from_file_location("qa_editorial_pptx_under_test", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        non_windows = module.office_backend_status("Linux", pywin32_available=True)
        self.assertEqual(non_windows["status"], "unavailable")
        self.assertIn("Windows", non_windows["reason"])
        missing_pywin32 = module.office_backend_status("Windows", pywin32_available=False)
        self.assertEqual(missing_pywin32["status"], "unavailable")
        self.assertIn("pywin32", missing_pywin32["reason"])
        self.assertTrue(module.is_com_busy(Exception(-2147418111, "PowerPoint busy")))
        self.assertFalse(module.is_com_busy(Exception(-1, "unrelated COM error")))

        deck = make_fixture(self.root, slides=1)
        out_dir = self.root / "qa_no_office"
        with patch.object(
            module,
            "office_backend_status",
            return_value={"status": "unavailable", "reason": "Synthetic no-Office condition for test."},
        ), redirect_stdout(StringIO()):
            code = module.main([str(deck), "--out-dir", str(out_dir)])
        self.assertEqual(code, 2)
        report = report_at(out_dir)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["office_render"]["status"], "unavailable")
        self.assertIn("Synthetic no-Office condition", report["office_render"]["reason"])
        self.assertIn("PowerPoint slide rendering was unavailable", " ".join(report["unexecuted"]))

    def test_office_helper_timeout_returns_unavailable_and_cleans_request_file(self) -> None:
        if not SCRIPT.is_file():
            self.fail("QA CLI module does not exist yet")
        spec = importlib.util.spec_from_file_location("qa_editorial_pptx_timeout_test", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        deck = make_fixture(self.root, slides=1)
        original_hash = sha256(deck)
        out_dir = self.root / "qa_timeout"
        out_dir.mkdir()
        args = SimpleNamespace(
            input=deck,
            pdf=None,
            embed_output=None,
            probe_editability=True,
            skip_office_render=False,
            render_width=1600,
            office_timeout=1,
        )
        timeout = subprocess.TimeoutExpired(cmd=["synthetic PowerPoint helper"], timeout=1)
        with patch.object(
            module,
            "office_backend_status",
            return_value={"status": "available", "reason": "Synthetic Office runtime."},
        ), patch.object(module.subprocess, "run", side_effect=timeout):
            report = module.run_office_phases(args, out_dir)

        self.assertEqual(report["office_runtime"]["status"], "unavailable")
        self.assertEqual(report["office_render"]["status"], "unavailable")
        self.assertEqual(report["editability_probe"]["status"], "unavailable")
        self.assertIn("1-second timeout", report["office_render"]["reason"])
        self.assertEqual(sha256(deck), original_hash)
        self.assertFalse(list(out_dir.glob(".office-worker-request-*.json")))

    def test_office_uses_uuid_qa_copy_and_never_closes_preexisting_presentation(self) -> None:
        if not SCRIPT.is_file():
            self.fail("QA CLI module does not exist yet")
        spec = importlib.util.spec_from_file_location("qa_editorial_pptx_ownership_test", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        deck = make_fixture(self.root, slides=1)
        original_hash = sha256(deck)
        out_dir = self.root / "qa_ownership"
        out_dir.mkdir()
        pdf = out_dir / "rendered.pdf"
        embedded = out_dir / "embedded.pptx"
        saved_states: dict[str, list[dict]] = {}

        class FakeTextRange:
            def __init__(self, state: dict) -> None:
                self.state = state

            @property
            def Text(self) -> str:
                return self.state.get("text", "")

            @Text.setter
            def Text(self, value: str) -> None:
                self.state["text"] = value

        class FakeShape:
            def __init__(self, state: dict) -> None:
                self.state = state
                self.Name = state["name"]
                self.Type = state["type"]
                self.Width = state["width"]
                self.Height = state["height"]
                self.HasTextFrame = -1 if state.get("text") else 0
                self.TextFrame = types.SimpleNamespace(
                    HasText=-1 if state.get("text") else 0,
                    TextRange=FakeTextRange(state),
                )

            @property
            def Left(self) -> float:
                return self.state["left"]

            @Left.setter
            def Left(self, value: float) -> None:
                self.state["left"] = value

        class FakeShapes:
            def __init__(self, states: list[dict]) -> None:
                self.states = states
                self.Count = len(states)

            def Item(self, index):
                if isinstance(index, str):
                    state = next(state for state in self.states if state["name"] == index)
                else:
                    state = self.states[index - 1]
                return FakeShape(state)

        class FakeSlide:
            def __init__(self, states: list[dict]) -> None:
                self.Shapes = FakeShapes(states)

            def Export(self, path: str, _kind: str, _width: int, _height: int) -> None:
                Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

        class FakeSlides:
            def __init__(self, states: list[dict]) -> None:
                self.states = states
                self.Count = 1

            def Item(self, _index: int) -> FakeSlide:
                return FakeSlide(self.states)

        class FakePresentation:
            def __init__(self, path: str, owner, read_only: bool, untitled: bool, with_window: bool) -> None:
                self.path = str(Path(path).resolve())
                self.owner = owner
                self.read_only = read_only
                self.untitled = untitled
                self.with_window = with_window
                self.states = copy.deepcopy(
                    saved_states.get(
                        self.path,
                        [
                            {"name": "Title", "type": 17, "text": "Été — édition de contrôle", "left": 72.0, "width": 500.0, "height": 40.0},
                            {"name": "Box", "type": 1, "text": "", "left": 72.0, "width": 100.0, "height": 50.0},
                        ],
                    )
                )
                self.PageSetup = types.SimpleNamespace(SlideWidth=1152.0, SlideHeight=648.0)
                self.Slides = FakeSlides(self.states)
                self.closed = False
                owner.opened.append(self)

            def SaveCopyAs(self, path: str, _file_format: int, _embed_fonts: int) -> None:
                shutil.copy2(self.path, path)

            def SaveAs(self, path: str, _file_format: int) -> None:
                Path(path).write_bytes(b"%PDF-1.4\nsynthetic")

            def Save(self) -> None:
                saved_states[self.path] = copy.deepcopy(self.states)

            def Close(self) -> None:
                self.closed = True
                self.owner.opened.remove(self)

        class FakeCollection:
            def __init__(self) -> None:
                self.open_calls: list[tuple[str, bool, bool, bool]] = []
                self.opened: list[FakePresentation] = []
                self.preexisting = types.SimpleNamespace(close_count=0)

            @property
            def Count(self) -> int:
                return 1 + len(self.opened)

            def Open(self, path: str, read_only: bool, untitled: bool, with_window: bool) -> FakePresentation:
                self.open_calls.append((str(Path(path).resolve()), read_only, untitled, with_window))
                return FakePresentation(path, self, read_only, untitled, with_window)

        class FakeApplication:
            def __init__(self) -> None:
                self.Presentations = FakeCollection()
                self.DisplayAlerts = 1
                self.quit_called = False

            def Quit(self) -> None:
                self.quit_called = True

        app = FakeApplication()
        app.Presentations.preexisting.FullName = str(deck.resolve())
        fake_pythoncom = types.ModuleType("pythoncom")
        fake_pythoncom.CoInitialize = lambda: None
        fake_pythoncom.CoUninitialize = lambda: None
        fake_pythoncom.PumpWaitingMessages = lambda: None
        fake_win32com = types.ModuleType("win32com")
        fake_win32com.__path__ = []
        fake_client = types.ModuleType("win32com.client")
        fake_client.DispatchEx = lambda _name: app
        fake_win32com.client = fake_client
        args = SimpleNamespace(
            input=deck,
            out_dir=out_dir,
            pdf=pdf,
            embed_output=embedded,
            probe_editability=True,
            skip_office_render=False,
            render_width=1600,
        )

        with patch.object(
            module,
            "office_backend_status",
            return_value={"status": "available", "reason": "Synthetic Office runtime."},
        ), patch.dict(
            sys.modules,
            {"pythoncom": fake_pythoncom, "win32com": fake_win32com, "win32com.client": fake_client},
        ):
            report = module.run_office_phases_live(args, out_dir)

        opened_paths = [Path(call[0]).resolve() for call in app.Presentations.open_calls]
        self.assertTrue(opened_paths)
        self.assertNotIn(deck.resolve(), opened_paths)
        self.assertTrue(all(path.is_relative_to(out_dir.resolve()) for path in opened_paths))
        self.assertTrue(all(call[3] is False for call in app.Presentations.open_calls))
        working_copy = Path(report["office_runtime"]["working_source_copy"])
        self.assertTrue(working_copy.is_file())
        self.assertRegex(working_copy.name, r"^office_source_[0-9a-f]{32}\.pptx$")
        self.assertNotEqual(working_copy.resolve(), deck.resolve())
        self.assertTrue(any(path == working_copy.resolve() for path in opened_paths))
        self.assertEqual(report["embed_output"]["path"], str(embedded))
        self.assertTrue(report["embed_output"]["embed_true_type_fonts_requested"])
        self.assertEqual(report["pdf_export"]["source_pptx"], str(embedded))
        self.assertIn(embedded.resolve(), opened_paths)
        self.assertEqual(report["office_render"]["status"], "pass")
        self.assertEqual(report["pdf_export"]["status"], "pass")
        self.assertEqual(report["editability_probe"]["status"], "pass")
        self.assertTrue(report["editability_probe"]["text_edit_verified"])
        self.assertTrue(report["editability_probe"]["geometry_move_verified"])
        self.assertEqual(app.Presentations.preexisting.FullName, str(deck.resolve()))
        self.assertEqual(app.Presentations.preexisting.close_count, 0)
        self.assertFalse(app.quit_called)
        self.assertEqual(sha256(deck), original_hash)

    @unittest.skipUnless(
        os.environ.get("RUN_POWERPOINT_QA_INTEGRATION") == "1",
        "PowerPoint integration is opt-in because it automates the local Office instance.",
    )
    def test_office_render_pdf_embed_copy_and_real_editability_probe_or_clear_unavailable_status(self) -> None:
        deck = make_fixture(self.root, slides=2)
        original_hash = sha256(deck)
        out_dir = self.root / "qa_office"
        pdf = self.root / "rendered.pdf"
        embedded_copy = self.root / "embedded_copy.pptx"
        result = run_cli(
            deck,
            out_dir,
            "--pdf",
            str(pdf),
            "--embed-output",
            str(embedded_copy),
            "--probe-editability",
        )
        self.assertTrue((out_dir / "qa_report.json").is_file(), result.stdout + result.stderr)
        report = report_at(out_dir)
        self.assertEqual(report["structure"]["status"], "pass")
        self.assertIn(report["status"], {"pass", "partial"})
        self.assertEqual(sha256(deck), original_hash)

        office_available = report["office_runtime"]["status"] == "available"
        if office_available:
            if report["office_render"]["status"] == "pass":
                self.assertEqual(report["office_render"]["exported_slides"], [1, 2])
                self.assertTrue(all((out_dir / "powerpoint_render" / f"slide-{n:03d}.png").is_file() for n in (1, 2)))
                if report["pdf_export"]["status"] == "pass":
                    self.assertTrue(pdf.is_file())
                else:
                    self.assertEqual(report["pdf_export"]["status"], "unavailable")
                    self.assertTrue(report["pdf_export"].get("reason"))
                    self.assertNotEqual(report["status"], "pass")
                if report["embed_output"]["status"] in {"pass", "partial"}:
                    self.assertTrue(embedded_copy.is_file())
                    with zipfile.ZipFile(embedded_copy) as archive:
                        self.assertIsNone(archive.testzip())
                else:
                    self.assertEqual(report["embed_output"]["status"], "unavailable")
                    self.assertTrue(report["embed_output"].get("reason"))
                    self.assertNotEqual(report["status"], "pass")
            else:
                self.assertEqual(report["office_render"]["status"], "unavailable")
                self.assertTrue(report["office_render"].get("reason"))
                self.assertNotEqual(report["status"], "pass")

            if report["editability_probe"]["status"] == "pass":
                self.assertTrue(report["editability_probe"]["text_edit_verified"])
                self.assertTrue(report["editability_probe"]["geometry_move_verified"])
                self.assertTrue(report["editability_probe"]["source_copy_only"])
            else:
                self.assertEqual(report["editability_probe"]["status"], "unavailable")
                self.assertTrue(report["editability_probe"].get("reason"))
                self.assertNotEqual(report["status"], "pass")
        else:
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(report["office_render"]["status"], "unavailable")
            self.assertEqual(report["pdf_export"]["status"], "unavailable")
            self.assertEqual(report["embed_output"]["status"], "unavailable")
            self.assertEqual(report["editability_probe"]["status"], "unavailable")
            self.assertNotEqual(report["status"], "pass")
            self.assertTrue(report["unexecuted"])


if __name__ == "__main__":
    unittest.main()
