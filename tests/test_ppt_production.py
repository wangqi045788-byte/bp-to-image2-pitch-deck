from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "skills" / "ppt-production" / "scripts" / "build_deck.py"
SAMPLE = ROOT / "examples" / "generic-demo" / "deck.json"
SPEC = importlib.util.spec_from_file_location("build_deck", BUILDER)
build_deck = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(build_deck)


def fixture(job: Path):
    (job / "assets").mkdir(parents=True)
    Image.new("RGB", (40, 20), "#567080").save(job / "assets" / "sample.png")
    return {
        "title": "Synthetic validation deck",
        "slide_size": [13.333, 7.5],
        "theme": {"font": "Aptos", "text": "20242A", "accent": "3567A8"},
        "slides": [
            {
                "title": "Native objects",
                "notes": "Sources: synthetic test fixture. Period: 2023–2025. Units: units shipped.",
                "elements": [
                    {"type": "text", "x": 0.8, "y": 1, "w": 3, "h": 0.7, "text": "Decision", "font_size": 24, "bold": True},
                    {"type": "shape", "shape": "ellipse", "x": 4.0, "y": 1, "w": 1, "h": 1, "fill": "EAF0F8", "line": "3567A8"},
                    {"type": "line", "x1": 5.2, "y1": 1.5, "x2": 6.0, "y2": 1.5, "color": "3567A8"},
                    {"type": "image", "file": "assets/sample.png", "x": 9, "y": 1, "w": 3, "h": 1.5},
                    {"type": "table", "x": 0.8, "y": 2, "w": 5, "h": 2, "rows": [["Period", "Value"], ["2024", "10"], ["2025", "12"]]},
                    {"type": "chart", "chart": "column", "x": 6, "y": 2, "w": 6, "h": 3, "title": "Units, 000s", "categories": ["2024", "2025"], "series": [{"name": "Actual", "values": [10, 12]}, {"name": "Plan", "values": [11, 13]}]},
                ],
            },
            {
                "notes": "All values in this fixture are synthetic.",
                "elements": [
                    {"type": "chart", "chart": "line", "x": 1, "y": 1, "w": 8, "h": 4, "categories": ["Q1", "Q2", "Q3"], "series": [{"name": "Index", "values": [1, 1.2, 1.4]}]},
                ],
            },
        ],
    }


class NativePowerPointBuilderTests(unittest.TestCase):
    def test_synthetic_example_builds_native_editable_text_shapes_table_charts_and_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = json.loads(SAMPLE.read_text(encoding="utf-8"))
            source = root / "deck.json"
            source.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            result = build_deck.convert(source, Path("output/deck.pptx"))
            self.assertEqual(result, root / "output" / "deck.pptx")
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            ppt = Presentation(result)
            self.assertEqual(len(ppt.slides), 3)
            all_shapes = [shape for slide in ppt.slides for shape in slide.shapes]
            self.assertTrue(any(shape.has_table for shape in all_shapes))
            self.assertGreaterEqual(sum(shape.has_chart for shape in all_shapes), 1)
            self.assertTrue(any(shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE for shape in all_shapes))
            slide2 = ppt.slides[1]
            table = next(shape.table for shape in slide2.shapes if shape.has_table)
            self.assertEqual(table.cell(0, 0).text, "Index points")
            chart = next(shape.chart for shape in slide2.shapes if shape.has_chart)
            self.assertEqual([str(c.label) for c in chart.plots[0].categories], ["2023", "2024", "2025"])
            self.assertEqual(tuple(chart.series[0].values), (100.0, 108.0, 119.0))
            self.assertIn("synthetic scenario", ppt.slides[1].notes_slide.notes_text_frame.text.lower())

    def test_picture_is_an_independent_embedded_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            document = fixture(root)
            output = root / "picture.pptx"
            build_deck.build(document, root / "deck.json", output)
            slide = Presentation(output).slides[0]
            pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
            self.assertEqual(len(pics), 1)
            self.assertGreater(len(pics[0].image.blob), 0)

    def test_chart_values_must_match_categories_and_be_finite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = fixture(root)
            doc["slides"][0]["elements"][-1]["series"][0]["values"] = [1]
            with self.assertRaisesRegex(ValueError, "match the category count"):
                build_deck.build(doc, root / "deck.json", root / "bad.pptx")
            doc["slides"][0]["elements"][-1]["series"][0]["values"] = [float("inf"), 2]
            with self.assertRaisesRegex(ValueError, "finite number"):
                build_deck.build(doc, root / "deck.json", root / "bad.pptx")

    def test_irregular_table_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = fixture(root)
            doc["slides"][0]["elements"][4]["rows"] = [["h1", "h2"], ["v"]]
            with self.assertRaisesRegex(ValueError, "equal column counts"):
                build_deck.build(doc, root / "deck.json", root / "bad.pptx")

    def test_absolute_and_parent_traversal_image_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = fixture(root)
            doc["slides"][0]["elements"][3]["file"] = "../outside.png"
            with self.assertRaisesRegex(ValueError, "cannot traverse outside"):
                build_deck.build(doc, root / "deck.json", root / "bad.pptx")
            doc["slides"][0]["elements"][3]["file"] = str(root / "assets" / "sample.png")
            with self.assertRaisesRegex(ValueError, "relative to the JSON"):
                build_deck.build(doc, root / "deck.json", root / "bad.pptx")

    def test_output_must_stay_in_the_job_and_existing_output_is_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = fixture(root)
            with self.assertRaisesRegex(ValueError, "stay inside"):
                build_deck.build(doc, root / "deck.json", root.parent / "outside.pptx")
            output = root / "deck.pptx"
            output.write_bytes(b"preserve existing target")
            with self.assertRaises(FileExistsError):
                build_deck.build(doc, root / "deck.json", output)
            self.assertEqual(output.read_bytes(), b"preserve existing target")

    def test_source_json_cannot_become_the_pptx_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.json"
            data = fixture(root)
            source.write_text(json.dumps(data), encoding="utf-8")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "cannot replace the source JSON"):
                build_deck.convert(source, Path("deck.json"), overwrite=True)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
