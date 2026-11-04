#!/usr/bin/env python3
"""Build editable PowerPoint pages from a validated JSON page plan."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

CHARTS = {"bar": XL_CHART_TYPE.BAR_CLUSTERED, "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
          "line": XL_CHART_TYPE.LINE, "pie": XL_CHART_TYPE.PIE,
          "doughnut": XL_CHART_TYPE.DOUGHNUT}
SHAPES = {"rect": MSO_AUTO_SHAPE_TYPE.RECTANGLE,
          "round_rect": MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
          "ellipse": MSO_AUTO_SHAPE_TYPE.OVAL,
          "triangle": MSO_AUTO_SHAPE_TYPE.ISOSCELES_TRIANGLE,
          "chevron": MSO_AUTO_SHAPE_TYPE.CHEVRON}
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER,
         "right": PP_ALIGN.RIGHT, "justify": PP_ALIGN.JUSTIFY}
VALIGN = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE,
          "bottom": MSO_ANCHOR.BOTTOM}
HEX = re.compile(r"^[0-9A-Fa-f]{6}$")


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number.")
    if positive and value <= 0:
        raise ValueError(f"{label} must be positive.")
    return float(value)


def _color(value: Any, label: str, *, allow_none: bool = False):
    if allow_none and value == "none":
        return None
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError(f"{label} must be six hex digits without '#'.")
    return RGBColor.from_string(value.upper())


def _box(element: dict, sw: float, sh: float, label: str) -> tuple[float, float, float, float]:
    x, y = _number(element.get("x"), f"{label}.x"), _number(element.get("y"), f"{label}.y")
    w, h = _number(element.get("w"), f"{label}.w", positive=True), _number(element.get("h"), f"{label}.h", positive=True)
    if x < 0 or y < 0 or x + w > sw + 1e-6 or y + h > sh + 1e-6:
        raise ValueError(f"{label} is outside the {sw:g} × {sh:g} inch slide.")
    return x, y, w, h


def _asset(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.file must be a relative asset path.")
    raw = Path(value)
    win = PureWindowsPath(value)
    if raw.is_absolute() or win.is_absolute() or win.drive:
        raise ValueError(f"{label}.file must be relative to the JSON directory.")
    cursor = root
    for part in raw.parts:
        if part in ("..", ""):
            raise ValueError(f"{label}.file cannot traverse outside the JSON directory.")
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(f"{label}.file cannot use symbolic links.")
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label}.file escapes the JSON directory.") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"{label}.file does not exist: {value}")
    return resolved


def _validate_chart(el: dict, label: str) -> None:
    kind, categories, series = el.get("chart"), el.get("categories"), el.get("series")
    if kind not in CHARTS:
        raise ValueError(f"{label}.chart must be one of {', '.join(CHARTS)}.")
    if not isinstance(categories, list) or not categories or any(not isinstance(c, (str, int, float)) for c in categories):
        raise ValueError(f"{label}.categories must be a non-empty list of labels.")
    if not isinstance(series, list) or not series:
        raise ValueError(f"{label}.series must be a non-empty list.")
    if kind in ("pie", "doughnut") and len(series) != 1:
        raise ValueError(f"{label} {kind} chart requires one series.")
    for i, s in enumerate(series):
        if not isinstance(s, dict) or not isinstance(s.get("name"), str) or not s["name"]:
            raise ValueError(f"{label}.series[{i}] requires a name.")
        values = s.get("values")
        if not isinstance(values, list) or len(values) != len(categories):
            raise ValueError(f"{label}.series[{i}].values must match the category count.")
        numbers = [_number(v, f"{label}.series[{i}].values[{j}]") for j, v in enumerate(values)]
        if kind in ("pie", "doughnut") and any(v < 0 for v in numbers):
            raise ValueError(f"{label} {kind} charts cannot contain negative values.")
    if kind in ("pie", "doughnut") and sum(series[0]["values"]) <= 0:
        raise ValueError(f"{label} {kind} chart must have a positive total.")


def _validate_table(el: dict, label: str) -> None:
    rows = el.get("rows")
    if not isinstance(rows, list) or not rows or any(not isinstance(r, list) or not r for r in rows):
        raise ValueError(f"{label}.rows must be a non-empty rectangular array.")
    columns = len(rows[0])
    if any(len(row) != columns for row in rows):
        raise ValueError(f"{label}.rows must have equal column counts.")
    for row in rows:
        for value in row:
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise ValueError(f"{label}.rows values must be text or finite numbers.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"{label}.rows cannot contain non-finite numbers.")
    for key, default in (("header_fill", "202C3B"), ("fill", "FFFFFF"),
                         ("color", "20242A"), ("header_color", "FFFFFF")):
        _color(el.get(key, default), f"{label}.{key}")
    _number(el.get("font_size", 13), f"{label}.font_size", positive=True)


def _validate_line(el: dict, sw: float, sh: float, label: str) -> None:
    x1, y1, x2, y2 = [_number(el.get(k), f"{label}.{k}") for k in ("x1", "y1", "x2", "y2")]
    if x1 < 0 or x2 < 0 or y1 < 0 or y2 < 0 or x1 > sw or x2 > sw or y1 > sh or y2 > sh:
        raise ValueError(f"{label} endpoints must be inside the slide.")
    _color(el.get("color", "20242A"), f"{label}.color")
    _number(el.get("width", 1), f"{label}.width", positive=True)


def _validate(document: dict, root: Path, output: Path, overwrite: bool) -> tuple[float, float, dict]:
    if not isinstance(document, dict) or not isinstance(document.get("slides"), list) or not document["slides"]:
        raise ValueError("The JSON must contain a non-empty slides array.")
    size = document.get("slide_size", [13.333, 7.5])
    if not isinstance(size, list) or len(size) != 2:
        raise ValueError("slide_size must be [width_inches, height_inches].")
    sw, sh = _number(size[0], "slide_size[0]", positive=True), _number(size[1], "slide_size[1]", positive=True)
    if sw > 56 or sh > 56:
        raise ValueError("slide dimensions cannot exceed PowerPoint's 56 inch limit.")
    theme = document.get("theme", {})
    if not isinstance(theme, dict):
        raise ValueError("theme must be an object.")
    _color(theme.get("background", "FFFFFF"), "theme.background")
    _color(theme.get("text", "20242A"), "theme.text")
    root = root.resolve()
    output = output.resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise ValueError("output must stay inside the JSON directory.") from exc
    if output.suffix.lower() != ".pptx":
        raise ValueError("output file extension must be .pptx.")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output exists; use --overwrite to replace it: {output}")
    for si, page in enumerate(document["slides"], 1):
        if not isinstance(page, dict):
            raise ValueError(f"slides[{si - 1}] must be an object.")
        if not isinstance(page.get("notes", ""), str):
            raise ValueError(f"slide {si} notes must be a string.")
        _color(page.get("background", theme.get("background", "FFFFFF")), f"slide {si}.background")
        elements = page.get("elements", [])
        if not isinstance(elements, list):
            raise ValueError(f"slide {si}.elements must be an array.")
        for ei, el in enumerate(elements, 1):
            if not isinstance(el, dict):
                raise ValueError(f"slide {si} element {ei} must be an object.")
            kind = el.get("type")
            label = f"slide {si} element {ei} ({kind})"
            if kind == "line":
                _validate_line(el, sw, sh, label)
            elif kind in ("text", "shape", "image", "table", "chart"):
                _box(el, sw, sh, label)
                if kind == "text":
                    if not isinstance(el.get("text"), str):
                        raise ValueError(f"{label}.text must be a string.")
                    _number(el.get("font_size", 18), f"{label}.font_size", positive=True)
                    _color(el.get("color", theme.get("text", "20242A")), f"{label}.color")
                    if el.get("align", "left") not in ALIGN or el.get("valign", "top") not in VALIGN:
                        raise ValueError(f"{label} has an invalid alignment.")
                elif kind == "shape":
                    if el.get("shape", "rect") not in SHAPES:
                        raise ValueError(f"{label}.shape must be one of {', '.join(SHAPES)}.")
                    _color(el.get("fill", theme.get("accent", "3567A8")), f"{label}.fill", allow_none=True)
                    _color(el.get("line", "none"), f"{label}.line", allow_none=True)
                elif kind == "image":
                    _asset(root, el.get("file"), label)
                elif kind == "table":
                    _validate_table(el, label)
                elif kind == "chart":
                    _validate_chart(el, label)
            else:
                raise ValueError(f"Unsupported {label}.")
    return sw, sh, theme


def _add_text(slide, el: dict, sw: float, sh: float, theme: dict, label: str) -> None:
    x, y, w, h = _box(el, sw, sh, label)
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    margin = _number(el.get("margin", 0.04), f"{label}.margin")
    for field in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(frame, field, Inches(margin))
    frame.vertical_anchor = VALIGN[el.get("valign", "top")]
    align = ALIGN[el.get("align", "left")]
    font = el.get("font", theme.get("font", "Aptos"))
    if not isinstance(font, str) or not font.strip() or len(font) > 100:
        raise ValueError(f"{label}.font must be a non-empty family name.")
    text_color = _color(el.get("color", theme.get("text", "20242A")), f"{label}.color")
    for i, line in enumerate(el["text"].split("\n")):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.alignment = align
        p.space_after = Pt(_number(el.get("space_after", 0), f"{label}.space_after"))
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(_number(el.get("font_size", 18), f"{label}.font_size", positive=True))
        run.font.bold = bool(el.get("bold", False))
        run.font.italic = bool(el.get("italic", False))
        run.font.color.rgb = text_color


def _add_line(slide, el: dict, sw: float, sh: float, label: str) -> None:
    x1, y1, x2, y2 = [float(el[k]) for k in ("x1", "y1", "x2", "y2")]
    shape = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    shape.line.color.rgb = _color(el.get("color", "20242A"), f"{label}.color")
    shape.line.width = Pt(_number(el.get("width", 1), f"{label}.width", positive=True))


def _add_shape(slide, el: dict, sw: float, sh: float, theme: dict, label: str) -> None:
    x, y, w, h = _box(el, sw, sh, label)
    obj = slide.shapes.add_shape(SHAPES[el.get("shape", "rect")], Inches(x), Inches(y), Inches(w), Inches(h))
    fill = _color(el.get("fill", theme.get("accent", "3567A8")), f"{label}.fill", allow_none=True)
    if fill is None:
        obj.fill.background()
    else:
        obj.fill.solid()
        obj.fill.fore_color.rgb = fill
    stroke = _color(el.get("line", "none"), f"{label}.line", allow_none=True)
    if stroke is None:
        obj.line.fill.background()
    else:
        obj.line.color.rgb = stroke
        obj.line.width = Pt(_number(el.get("line_width", 1), f"{label}.line_width", positive=True))


def _add_image(slide, el: dict, root: Path, sw: float, sh: float, label: str) -> None:
    x, y, w, h = _box(el, sw, sh, label)
    pic = slide.shapes.add_picture(str(_asset(root, el.get("file"), label)), Inches(x), Inches(y), Inches(w), Inches(h))
    target_ratio = w / h
    image_width, image_height = pic.image.size
    source_ratio = image_width / image_height
    if source_ratio > target_ratio:
        crop = (1 - target_ratio / source_ratio) / 2
        pic.crop_left = pic.crop_right = crop
    elif source_ratio < target_ratio:
        crop = (1 - source_ratio / target_ratio) / 2
        pic.crop_top = pic.crop_bottom = crop


def _add_table(slide, el: dict, sw: float, sh: float, theme: dict, label: str) -> None:
    x, y, w, h = _box(el, sw, sh, label)
    rows = el["rows"]
    table = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h)).table
    header = bool(el.get("header", True))
    head_fill = _color(el.get("header_fill", "202C3B"), f"{label}.header_fill")
    body_fill = _color(el.get("fill", "FFFFFF"), f"{label}.fill")
    ink = _color(el.get("color", "20242A"), f"{label}.color")
    head_ink = _color(el.get("header_color", "FFFFFF"), f"{label}.header_color")
    font = theme.get("body_font", theme.get("font", "Aptos"))
    size = _number(el.get("font_size", 13), f"{label}.font_size", positive=True)
    for ri, row in enumerate(rows):
        for ci, value in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = str(value)
            is_head = header and ri == 0
            cell.fill.solid()
            cell.fill.fore_color.rgb = head_fill if is_head else body_fill
            cell.margin_left = cell.margin_right = Inches(0.07)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.name = font
                    run.font.size = Pt(size)
                    run.font.bold = is_head
                    run.font.color.rgb = head_ink if is_head else ink


def _add_chart(slide, el: dict, sw: float, sh: float, label: str) -> None:
    x, y, w, h = _box(el, sw, sh, label)
    data = CategoryChartData()
    data.categories = [str(v) for v in el["categories"]]
    for s in el["series"]:
        data.add_series(s["name"], [_number(v, f"{label} series") for v in s["values"]])
    chart = slide.shapes.add_chart(CHARTS[el["chart"]], Inches(x), Inches(y), Inches(w), Inches(h), data).chart
    if el.get("title"):
        chart.has_title = True
        chart.chart_title.text_frame.text = str(el["title"])
    chart.has_legend = len(el["series"]) > 1 or el["chart"] in ("pie", "doughnut")
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False


def build(document: dict, job_json: Path, output: Path, *, overwrite: bool = False) -> Path:
    job_json = job_json.resolve()
    root = job_json.parent
    if not isinstance(output, Path):
        output = Path(output)
    if not output.is_absolute():
        output = root / output
    if output.resolve() == job_json:
        raise ValueError("output cannot replace the source JSON.")
    sw, sh, theme = _validate(document, root, output, overwrite)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(sw), Inches(sh)
    prs.core_properties.title = str(document.get("title", "Presentation"))
    prs.core_properties.subject = "Generated from a validated page plan"
    blank = prs.slide_layouts[6]
    for page_number, page in enumerate(document["slides"], 1):
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = _color(page.get("background", theme.get("background", "FFFFFF")), f"slide {page_number}.background")
        if page.get("title"):
            _add_text(slide, {"x": 0.8, "y": 0.35, "w": sw - 1.6, "h": 0.45,
                              "text": str(page["title"]), "font_size": 16, "bold": True,
                              "color": theme.get("text", "20242A"), "valign": "middle"},
                      sw, sh, theme, f"slide {page_number} title")
        for index, el in enumerate(page.get("elements", []), 1):
            label = f"slide {page_number} element {index} ({el['type']})"
            kind = el["type"]
            if kind == "text":
                _add_text(slide, el, sw, sh, theme, label)
            elif kind == "line":
                _add_line(slide, el, sw, sh, label)
            elif kind == "shape":
                _add_shape(slide, el, sw, sh, theme, label)
            elif kind == "image":
                _add_image(slide, el, root, sw, sh, label)
            elif kind == "table":
                _add_table(slide, el, sw, sh, theme, label)
            elif kind == "chart":
                _add_chart(slide, el, sw, sh, label)
        if page.get("notes"):
            slide.notes_slide.notes_text_frame.text = page["notes"]
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{output.stem}-", suffix=".pptx", dir=output.parent)
    os.close(descriptor)
    temp = Path(temp_name)
    try:
        prs.save(temp)
        if overwrite:
            os.replace(temp, output)
        else:
            # link() provides an atomic create-if-absent operation on the same volume.
            os.link(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    return output


def convert(job_json: Path, output: Path, *, overwrite: bool = False) -> Path:
    job_json = job_json.expanduser().resolve(strict=True)
    if not job_json.is_file():
        raise FileNotFoundError(f"Input is not a file: {job_json}")
    try:
        document = json.loads(job_json.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid UTF-8 JSON: {exc}") from exc
    return build(document, job_json, output, overwrite=overwrite)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_json", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="new .pptx path, relative to the JSON directory")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing output atomically")
    args = parser.parse_args(argv)
    try:
        path = convert(args.job_json, args.output, overwrite=args.overwrite)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"build_deck: {exc}\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
