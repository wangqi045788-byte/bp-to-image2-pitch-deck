from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image
from pptx import Presentation
from pptx.util import Inches


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "noir-ppt-studio"
SCRIPT = SKILL_ROOT / "scripts" / "export_editorial_svg.py"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"p": P_NS, "a": A_NS}
EMU_PER_PIXEL = 9525


def make_fixture(root: Path, *, output: str = "output/editorial.pptx") -> tuple[Path, list[dict]]:
    pages_dir = root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages = [
        {
            "number": 1,
            "canvas": [400, 225],
            "background": {"fill": "#ffffff"},
            "elements": [
                {
                    "type": "text",
                    "id": "center-title",
                    "text": "ÉTÉ",
                    "x": 200,
                    "y": 70,
                    "font": "Arial",
                    "size": 24,
                    "fill": "#111111",
                    "anchor": "middle",
                    "spacing": 2,
                },
                {
                    "type": "rect",
                    "id": "native-box",
                    "x": 12,
                    "y": 100,
                    "w": 40,
                    "h": 20,
                    "fill": "#eeeeee",
                    "stroke": "#222222",
                    "width": 1,
                },
            ],
        },
        {
            "number": 2,
            "canvas": [400, 225],
            "background": {"fill": "#fafafa"},
            "notes": "OVERRIDE NOTE 2",
            "elements": [
                {
                    "type": "text",
                    "id": "right-label",
                    "text": "l’esprit",
                    "x": 380,
                    "y": 90,
                    "font": "Arial",
                    "size": 20,
                    "fill": "#111111",
                    "anchor": "end",
                    "spacing": 3,
                },
                {
                    "type": "polygon",
                    "id": "native-triangle",
                    "points": [[40, 120], [70, 120], [55, 145]],
                    "fill": "#cccccc",
                    "stroke": "none",
                },
            ],
        },
    ]
    relative_pages = []
    for index, page in enumerate(pages, start=1):
        page_path = pages_dir / f"page_{index}.json"
        page_path.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
        relative_pages.append(page_path.relative_to(root).as_posix())

    source = Presentation()
    source.slide_width = Inches(13.333)
    source.slide_height = Inches(7.5)
    blank = source.slide_layouts[6]
    for note in ("SOURCE NOTE 1", "SOURCE NOTE 2"):
        slide = source.slides.add_slide(blank)
        slide.notes_slide.notes_text_frame.text = note
    source_path = root / "source_notes.pptx"
    source.save(source_path)

    job = {
        "language": "fr-FR",
        "canvas": [400, 225],
        "slide_size": [1600, 900],
        "pages": relative_pages,
        "output": output,
        "notes_from_pptx": "source_notes.pptx",
    }
    job_path = root / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return job_path, pages


def run_cli(job_path: Path, *options: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    isolated_home = job_path.parent / "isolated_home"
    isolated_home.mkdir(parents=True, exist_ok=True)
    env["CODEX_HOME"] = str(isolated_home / "codex")
    env["USERPROFILE"] = str(isolated_home / "user")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(job_path), *options],
        cwd=job_path.parent,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env=env,
    )


def xml_geometry(pptx_path: Path, slide_number: int, text: str) -> tuple[int, int, int, int, str | None]:
    with zipfile.ZipFile(pptx_path) as archive:
        root = ET.fromstring(archive.read(f"ppt/slides/slide{slide_number}.xml"))
    for shape in root.findall(".//p:sp", NS):
        if "".join(node.text or "" for node in shape.findall(".//a:t", NS)) != text:
            continue
        off = shape.find("p:spPr/a:xfrm/a:off", NS)
        ext = shape.find("p:spPr/a:xfrm/a:ext", NS)
        body = shape.find("p:txBody/a:bodyPr", NS)
        ppr = shape.find("p:txBody/a:p/a:pPr", NS)
        return (
            int(off.get("x")),
            int(ext.get("cx")),
            int(body.get("lIns", "0")),
            int(body.get("rIns", "0")),
            ppr.get("algn") if ppr is not None else None,
        )
    raise AssertionError(f"Native text shape not found: {text}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EditorialSvgExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="editorial_svg_test_")
        self.root = Path(self.temp.name)
        self.job_path, self.pages = make_fixture(self.root)
        self.initial_result = run_cli(self.job_path)
        self.output = self.root / "output" / "editorial.pptx"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_cli_exports_native_editable_french_slides_with_preserved_notes(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stdout + self.initial_result.stderr)
        self.assertTrue(self.output.is_file())
        report = json.loads(self.output.with_name("editorial.report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["figedit_discovery"], "bundled package")
        self.assertEqual(len(list((self.root / "svg").glob("*.svg"))), 2)
        self.assertEqual(len(list((self.root / "svg_embedded").glob("*.svg"))), 2)

        with zipfile.ZipFile(self.output) as archive:
            presentation_xml = ET.fromstring(archive.read("ppt/presentation.xml"))
            size = presentation_xml.find("p:sldSz", NS)
            self.assertEqual((int(size.get("cx")), int(size.get("cy"))), (1600 * EMU_PER_PIXEL, 900 * EMU_PER_PIXEL))
            for index, _expected_page in enumerate(self.pages, start=1):
                slide_xml = ET.fromstring(archive.read(f"ppt/slides/slide{index}.xml"))
                shapes = slide_xml.findall(".//p:sp", NS)
                text_shapes = [shape for shape in shapes if shape.findall(".//a:t", NS)]
                geometry_shapes = [shape for shape in shapes if not shape.findall(".//a:t", NS)]
                self.assertEqual(len(text_shapes), 1)
                self.assertEqual(len(geometry_shapes), 2)  # background and one editable primitive
                self.assertEqual(len(slide_xml.findall(".//p:pic", NS)), 0)
                run_languages = [node.get("lang") for node in slide_xml.findall(".//a:rPr", NS)]
                self.assertTrue(run_languages)
                self.assertEqual(set(run_languages), {"fr-FR"})
            notes_parts = sorted(
                name for name in archive.namelist()
                if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")
            )
            self.assertEqual(len(notes_parts), 2)
            notes_languages = []
            for name in notes_parts:
                note_xml = ET.fromstring(archive.read(name))
                notes_languages.extend(
                    node.get("lang")
                    for node in note_xml.iter()
                    if node.tag.rsplit("}", 1)[-1] in {"rPr", "defRPr", "endParaRPr"}
                    and node.get("lang")
                )
            self.assertTrue(notes_languages)
            self.assertEqual(set(notes_languages), {"zh-CN"})

        deck = Presentation(str(self.output))
        self.assertEqual(
            [slide.notes_slide.notes_text_frame.text for slide in deck.slides],
            ["SOURCE NOTE 1", "OVERRIDE NOTE 2"],
        )

    def test_tracking_anchors_and_padding_are_fixed_idempotently(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        report_path = self.output.with_name("editorial.report.json")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        fixed_ids = {item["id"] for item in report["compatibility_fixes"]["legacy_tracking_anchor_offsets"]}
        self.assertEqual(fixed_ids, {"center-title", "right-label"})

        center = xml_geometry(self.output, 1, "ÉTÉ")
        right = xml_geometry(self.output, 2, "l’esprit")
        center_anchor = center[0] + center[2] + (center[1] - center[2] - center[3]) // 2
        right_anchor = right[0] + right[1] - right[3]
        self.assertLessEqual(abs(center_anchor - 200 * 4 * EMU_PER_PIXEL), 2)
        # Each source coordinate and extent is rounded to EMU before scaling.
        self.assertLessEqual(abs(right_anchor - 380 * 4 * EMU_PER_PIXEL), 6)
        self.assertGreater(center[2], 0)
        self.assertGreater(center[3], 0)
        self.assertGreater(right[2], 0)
        self.assertGreater(right[3], 0)
        self.assertEqual((center[4], right[4]), ("ctr", "r"))

        spec = importlib.util.spec_from_file_location("editorial_svg_export", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        scripts_dir, _ = module._discover_figedit(None)
        estimator = module._read_text_width_estimator(scripts_dir)
        before = (xml_geometry(self.output, 1, "ÉTÉ"), xml_geometry(self.output, 2, "l’esprit"))
        second_pass = module.patch_compatibility_and_canvas(
            self.output, self.pages, (400, 225), (1600, 900), "fr-FR", estimator
        )
        after = (xml_geometry(self.output, 1, "ÉTÉ"), xml_geometry(self.output, 2, "l’esprit"))
        self.assertEqual(before, after)
        self.assertEqual(second_pass["legacy_tracking_anchor_offsets"], [])
        self.assertEqual(second_pass["legacy_text_padding_insets"], [])
        self.assertFalse(second_pass["canvas_scaling"]["applied"])

    def test_target_16_by_9_canvas_scales_native_geometry(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        with zipfile.ZipFile(self.output) as archive:
            slide = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
        found = False
        expected_x = 12 * 4 * EMU_PER_PIXEL
        expected_cx = 40 * 4 * EMU_PER_PIXEL
        for shape in slide.findall(".//p:sp", NS):
            if shape.findall(".//a:t", NS):
                continue
            off = shape.find("p:spPr/a:xfrm/a:off", NS)
            ext = shape.find("p:spPr/a:xfrm/a:ext", NS)
            if abs(int(off.get("x")) - expected_x) <= 1 and abs(int(ext.get("cx")) - expected_cx) <= 1:
                found = True
        self.assertTrue(found, "The native rectangle was not scaled from 400x225 to 1600x900.")

    def test_relative_page_paths_cannot_escape_job_directory(self) -> None:
        job = json.loads(self.job_path.read_text(encoding="utf-8"))
        job["pages"][0] = "../outside.json"
        job["output"] = "output/escaped.pptx"
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        result = run_cli(self.job_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes the job directory", result.stderr)
        self.assertFalse((self.root / "output" / "escaped.pptx").exists())

    def test_page_rejects_duplicate_element_ids(self) -> None:
        page_path = self.root / "pages" / "page_1.json"
        page = json.loads(page_path.read_text(encoding="utf-8"))
        page["elements"][1]["id"] = page["elements"][0]["id"]
        page_path.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
        job = json.loads(self.job_path.read_text(encoding="utf-8"))
        job["output"] = "output/duplicate_ids.pptx"
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

        result = run_cli(self.job_path, "--overwrite")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate element id", result.stderr)
        self.assertFalse((self.root / "output" / "duplicate_ids.pptx").exists())

    def test_ordinary_text_rejects_line_breaks(self) -> None:
        page_path = self.root / "pages" / "page_1.json"
        page = json.loads(page_path.read_text(encoding="utf-8"))
        page["elements"][0]["text"] = "ÉTÉ\nÉTÉ"
        page_path.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
        job = json.loads(self.job_path.read_text(encoding="utf-8"))
        job["output"] = "output/multiline_text.pptx"
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

        result = run_cli(self.job_path, "--overwrite")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be single-line", result.stderr)
        self.assertFalse((self.root / "output" / "multiline_text.pptx").exists())

    def test_existing_outputs_require_overwrite_and_source_notes_are_protected(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        source = self.root / "source_notes.pptx"
        before = sha256(source)
        output_before = sha256(self.output)

        blocked = run_cli(self.job_path)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("--overwrite", blocked.stderr)
        self.assertEqual(sha256(self.output), output_before)
        self.assertEqual(sha256(source), before)

        replaced = run_cli(
            self.job_path,
            "--overwrite",
            "--figedit-dir",
            str(Path.home() / ".codex" / "skills" / "figedit"),
        )
        self.assertEqual(replaced.returncode, 0, replaced.stdout + replaced.stderr)
        self.assertEqual(sha256(source), before)
        deck = Presentation(str(self.output))
        self.assertEqual(
            [slide.notes_slide.notes_text_frame.text for slide in deck.slides],
            ["SOURCE NOTE 1", "OVERRIDE NOTE 2"],
        )

    def test_overwrite_flag_cannot_replace_notes_source(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        source = self.root / "source_notes.pptx"
        source_before = sha256(source)
        job = json.loads(self.job_path.read_text(encoding="utf-8"))
        job["output"] = "source_notes.pptx"
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

        result = run_cli(self.job_path, "--overwrite")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot overwrite a source PPTX", result.stderr)
        self.assertEqual(sha256(source), source_before)

    def test_local_font_face_uses_safe_linked_and_embedded_references(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        font_path = self.root / "fonts" / "FixtureFont.ttf"
        font_path.parent.mkdir(parents=True)
        font_path.write_bytes(b"synthetic local font fixture")
        job = json.loads(self.job_path.read_text(encoding="utf-8"))
        job["font_faces"] = [{"family": "Fixture Font", "file": "fonts/FixtureFont.ttf"}]
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

        result = run_cli(self.job_path, "--overwrite")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        linked_svg = (self.root / "svg" / "slide_01.svg").read_text(encoding="utf-8")
        embedded_svg = (self.root / "svg_embedded" / "slide_01.svg").read_text(encoding="utf-8")
        self.assertIn("font-family: 'Fixture Font'", linked_svg)
        self.assertIn("url('../fonts/FixtureFont.ttf')", linked_svg)
        self.assertIn("data:font/ttf;base64,", embedded_svg)

    def test_local_font_face_serializes_safe_chinese_family(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        font_path = self.root / "fonts" / "ChineseFixture.ttf"
        font_path.parent.mkdir(parents=True)
        font_path.write_bytes(b"synthetic local font fixture")
        job = json.loads(self.job_path.read_text(encoding="utf-8"))
        job["font_faces"] = [{"family": "思源宋体", "file": "fonts/ChineseFixture.ttf"}]
        job["output"] = "output/chinese_font.pptx"
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

        result = run_cli(self.job_path, "--overwrite")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        svg = (self.root / "svg" / "slide_01.svg").read_text(encoding="utf-8")
        self.assertIn("font-family: '思源宋体'", svg)

        job["font_faces"][0]["family"] = "思源宋体; color:red"
        job["output"] = "output/unsafe_font.pptx"
        self.job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        unsafe = run_cli(self.job_path, "--overwrite")
        self.assertNotEqual(unsafe.returncode, 0)
        self.assertIn("not a safe font family name", unsafe.stderr)

    def test_local_images_are_linked_or_embedded_while_text_stays_native(self) -> None:
        self.assertEqual(self.initial_result.returncode, 0, self.initial_result.stderr)
        image_path = self.root / "assets" / "fixture.png"
        image_path.parent.mkdir(parents=True)
        Image.new("RGB", (4, 4), (180, 40, 80)).save(image_path)

        page_path = self.root / "pages" / "page_1.json"
        page = json.loads(page_path.read_text(encoding="utf-8"))
        page["elements"].append(
            {"type": "image", "id": "small-image", "file": "assets/fixture.png", "x": 80, "y": 100, "w": 12, "h": 12}
        )
        page_path.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
        result = run_cli(self.job_path, "--overwrite")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        linked_svg = ET.parse(self.root / "svg" / "slide_01.svg").getroot()
        embedded_svg = ET.parse(self.root / "svg_embedded" / "slide_01.svg").getroot()
        linked_image = next(node for node in linked_svg.iter() if node.tag.endswith("image"))
        embedded_image = next(node for node in embedded_svg.iter() if node.tag.endswith("image"))
        self.assertEqual(linked_image.get("href"), "../assets/fixture.png")
        self.assertTrue(embedded_image.get("href").startswith("data:image/png;base64,"))

        with zipfile.ZipFile(self.output) as archive:
            slide = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
        self.assertEqual(len(slide.findall(".//p:pic", NS)), 1)
        self.assertEqual(len([shape for shape in slide.findall(".//p:sp", NS) if shape.findall(".//a:t", NS)]), 1)


if __name__ == "__main__":
    unittest.main()
