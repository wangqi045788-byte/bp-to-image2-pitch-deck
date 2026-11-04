#!/usr/bin/env python3
"""Export page JSON files as linked/embedded SVGs and editable native PPTX."""

from __future__ import annotations

import argparse
import base64
import json
import math
import mimetypes
import os
import re
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree as StdET

from lxml import etree as ET
from pptx import Presentation


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
EMU_PER_PIXEL = 9525
NS = {"p": P_NS, "a": A_NS}
ALLOWED_ELEMENTS = {"text", "line", "rect", "polygon", "image"}
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
COLOR_RE = re.compile(
    r"^(?:none|currentColor|#[0-9A-Fa-f]{3,8}|[A-Za-z]{1,32}|"
    r"(?:rgb|rgba|hsl|hsla)\([0-9.,%\s+-]+\))$"
)

StdET.register_namespace("", SVG_NS)
StdET.register_namespace("xlink", XLINK_NS)


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _job_path(root: Path, raw: Any, label: str, *, must_exist: bool = True) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label} must be a non-empty relative path.")
    candidate_text = Path(raw)
    windows_path = PureWindowsPath(raw)
    if candidate_text.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ValueError(f"{label} must be relative to the job directory.")
    candidate = (root / candidate_text).resolve()
    if not _path_within(candidate, root):
        raise ValueError(f"{label} escapes the job directory: {raw}")
    if must_exist and not candidate.is_file():
        raise FileNotFoundError(f"{label} does not exist: {raw}")
    return candidate


def _dimension_pair(value: Any, label: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must be [width, height].")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label} dimensions must be positive integers.")
        if not math.isfinite(float(item)) or int(item) != item or item <= 0:
            raise ValueError(f"{label} dimensions must be positive integers.")
        result.append(int(item))
    return result[0], result[1]


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _safe_color(value: Any, label: str) -> str:
    color = str(value)
    if not COLOR_RE.fullmatch(color):
        raise ValueError(f"{label} must be a color value, not an external paint reference.")
    return color


def _safe_font_family(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 100 or value != value.strip():
        return False
    return all(
        char.isalpha()
        or char.isdigit()
        or unicodedata.category(char).startswith("M")
        or char in " _.-"
        for char in value
    )


def _validate_page(page: Any, path: Path, canvas: tuple[int, int], root: Path) -> dict[str, Any]:
    if not isinstance(page, dict):
        raise ValueError(f"Page JSON must contain an object: {path.name}")
    number = page.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError(f"{path.name}: number must be a positive integer.")
    if _dimension_pair(page.get("canvas"), f"{path.name}: canvas") != canvas:
        raise ValueError(f"{path.name}: canvas must match the job canvas {list(canvas)}.")
    background = page.get("background")
    if not isinstance(background, dict) or (("fill" in background) == ("plate" in background)):
        raise ValueError(f"{path.name}: background must specify exactly one of fill or plate.")
    if "fill" in background:
        _safe_color(background["fill"], f"{path.name}: background fill")
    else:
        _job_path(root, background["plate"], f"{path.name}: background plate")
    elements = page.get("elements")
    if not isinstance(elements, list):
        raise ValueError(f"{path.name}: elements must be a list.")
    ids: set[str] = set()
    for index, element in enumerate(elements, start=1):
        label = f"{path.name}: element {index}"
        if not isinstance(element, dict):
            raise ValueError(f"{label} must be an object.")
        kind = element.get("type")
        if kind not in ALLOWED_ELEMENTS:
            raise ValueError(f"{label}: unsupported type {kind!r}.")
        if not isinstance(element.get("id"), str) or not element["id"].strip():
            raise ValueError(f"{label}: id must be a non-empty string.")
        if element["id"] in ids:
            raise ValueError(f"{path.name}: duplicate element id {element['id']!r}.")
        ids.add(element["id"])
        if kind == "text":
            for key in ("text", "font", "size", "fill", "x", "anchor"):
                if key not in element:
                    raise ValueError(f"{label}: text is missing {key!r}.")
            if "y" not in element and "baseline" not in element:
                raise ValueError(f"{label}: text requires y or baseline.")
            if not isinstance(element["text"], str) or not element["text"]:
                raise ValueError(f"{label}: text must be a non-empty string.")
            if "\n" in element["text"] or "\r" in element["text"]:
                raise ValueError(f"{label}: text must be single-line; use separate elements for separate lines.")
            if not isinstance(element["font"], str) or not element["font"].strip():
                raise ValueError(f"{label}: font must be a non-empty family name.")
            if element["anchor"] not in {"start", "middle", "end"}:
                raise ValueError(f"{label}: anchor must be start, middle, or end.")
            for key in ("x", "size"):
                _number(element[key], f"{label}: {key}")
            _number(element.get("baseline", element.get("y")), f"{label}: baseline")
            _number(element.get("spacing", 0), f"{label}: spacing")
            if float(element["size"]) <= 0:
                raise ValueError(f"{label}: font size must be positive.")
            _safe_color(element["fill"], f"{label}: fill")
        elif kind == "line":
            for key in ("x1", "y1", "x2", "y2"):
                if key not in element:
                    raise ValueError(f"{label}: line is missing {key!r}.")
                _number(element[key], f"{label}: {key}")
            _safe_color(element.get("stroke", "#000000"), f"{label}: stroke")
            _number(element.get("width", 1), f"{label}: width")
        elif kind == "rect":
            for key in ("x", "y", "w", "h"):
                if key not in element:
                    raise ValueError(f"{label}: rect is missing {key!r}.")
                _number(element[key], f"{label}: {key}")
            _safe_color(element.get("fill", "none"), f"{label}: fill")
            _safe_color(element.get("stroke", "none"), f"{label}: stroke")
            _number(element.get("width", 1), f"{label}: width")
        elif kind == "polygon":
            points = element.get("points")
            if not isinstance(points, list) or len(points) < 3:
                raise ValueError(f"{label}: polygon requires at least three points.")
            for point in points:
                if not isinstance(point, (tuple, list)) or len(point) != 2:
                    raise ValueError(f"{label}: each polygon point must be [x, y].")
                _number(point[0], f"{label}: polygon x")
                _number(point[1], f"{label}: polygon y")
            _safe_color(element.get("fill", "none"), f"{label}: fill")
            _safe_color(element.get("stroke", "none"), f"{label}: stroke")
            _number(element.get("width", 1), f"{label}: width")
        elif kind == "image":
            for key in ("x", "y", "w", "h"):
                if key not in element:
                    raise ValueError(f"{label}: image is missing {key!r}.")
                _number(element[key], f"{label}: {key}")
            _job_path(root, element.get("file"), f"{label}: image file")
    if "notes" in page and not isinstance(page["notes"], str):
        raise ValueError(f"{path.name}: notes override must be a string.")
    return page


def _font_faces(job: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    raw_faces = job.get("font_faces", [])
    if not isinstance(raw_faces, list):
        raise ValueError("font_faces must be a list.")
    faces = []
    seen: set[str] = set()
    for index, face in enumerate(raw_faces, start=1):
        if not isinstance(face, dict):
            raise ValueError(f"font_faces[{index - 1}] must be an object.")
        family = face.get("family")
        if not _safe_font_family(family):
            raise ValueError(f"font_faces[{index - 1}].family is not a safe font family name.")
        if family.casefold() in seen:
            raise ValueError(f"font_faces contains duplicate family {family!r}.")
        seen.add(family.casefold())
        font_path = _job_path(root, face.get("file"), f"font_faces[{index - 1}].file")
        extension = font_path.suffix.lower()
        if extension not in {".ttf", ".otf", ".woff", ".woff2"}:
            raise ValueError(f"font file must be TTF, OTF, WOFF, or WOFF2: {font_path.name}")
        faces.append({"family": family, "path": font_path, "extension": extension})
    return faces


def _font_format(extension: str) -> tuple[str, str]:
    return {
        ".ttf": ("font/ttf", "truetype"),
        ".otf": ("font/otf", "opentype"),
        ".woff": ("font/woff", "woff"),
        ".woff2": ("font/woff2", "woff2"),
    }[extension]


def _image_href(source: Path, final_svg_dir: Path, embedded: bool) -> str:
    if embedded:
        mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        payload = base64.b64encode(source.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{payload}"
    return Path(os.path.relpath(source, final_svg_dir)).as_posix()


def _append_image_href(node: StdET.Element, source: Path, final_svg_dir: Path, embedded: bool) -> None:
    href = _image_href(source, final_svg_dir, embedded)
    node.set("href", href)
    node.set(f"{{{XLINK_NS}}}href", href)


def _write_svg(
    page: dict[str, Any],
    index: int,
    output_path: Path,
    href_dir: Path,
    root_dir: Path,
    canvas: tuple[int, int],
    faces: list[dict[str, Any]],
    embedded: bool,
) -> None:
    width, height = canvas
    svg_root = StdET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "preserveAspectRatio": "none",
        },
    )
    if faces:
        style = StdET.SubElement(svg_root, f"{{{SVG_NS}}}style")
        rules = []
        for face in faces:
            mime, fmt = _font_format(face["extension"])
            if embedded:
                encoded = base64.b64encode(face["path"].read_bytes()).decode("ascii")
                src = f"data:{mime};base64,{encoded}"
            else:
                relative = Path(os.path.relpath(face["path"], href_dir)).as_posix()
                src = quote(relative, safe="/:._-")
            rules.append(
                f"@font-face {{ font-family: '{face['family']}'; "
                f"src: url('{src}') format('{fmt}'); font-weight: 400; font-style: normal; }}"
            )
        style.text = "\n".join(rules)

    background = page["background"]
    if "fill" in background:
        StdET.SubElement(
            svg_root,
            f"{{{SVG_NS}}}rect",
            {"id": "background-fill", "x": "0", "y": "0", "width": str(width), "height": str(height), "fill": background["fill"], "stroke": "none"},
        )
    else:
        plate = StdET.SubElement(
            svg_root,
            f"{{{SVG_NS}}}image",
            {"id": "background-plate", "x": "0", "y": "0", "width": str(width), "height": str(height), "preserveAspectRatio": "none"},
        )
        _append_image_href(plate, _job_path(root_dir, background["plate"], "background plate"), href_dir, embedded)

    for element in page["elements"]:
        kind = element["type"]
        common = {"id": element["id"]}
        if kind == "text":
            node = StdET.SubElement(svg_root, f"{{{SVG_NS}}}text", common)
            node.set("x", str(element["x"]))
            node.set("y", str(element.get("baseline", element.get("y"))))
            node.set("font-family", element["font"])
            node.set("font-size", str(element["size"]))
            node.set("fill", element["fill"])
            node.set("text-anchor", element["anchor"])
            if float(element.get("spacing", 0)) != 0:
                node.set("letter-spacing", str(element["spacing"]))
            if element.get("bold"):
                node.set("font-weight", "700")
            if element.get("italic"):
                node.set("font-style", "italic")
            if "source_bbox" in element:
                if not isinstance(element["source_bbox"], list) or len(element["source_bbox"]) != 4:
                    raise ValueError(f"{element['id']}: source_bbox must have four values.")
                node.set("data-source-bbox", ",".join(str(_number(x, "source_bbox")) for x in element["source_bbox"]))
            node.set(f"{{{XML_NS}}}space", "preserve")
            node.text = element["text"]
        elif kind == "line":
            node = StdET.SubElement(svg_root, f"{{{SVG_NS}}}line", common)
            for key in ("x1", "y1", "x2", "y2"):
                node.set(key, str(element[key]))
            node.set("fill", "none")
            node.set("stroke", str(element.get("stroke", "#000000")))
            node.set("stroke-width", str(element.get("width", 1)))
        elif kind == "rect":
            node = StdET.SubElement(svg_root, f"{{{SVG_NS}}}rect", common)
            for key, svg_key in (("x", "x"), ("y", "y"), ("w", "width"), ("h", "height")):
                node.set(svg_key, str(element[key]))
            node.set("fill", str(element.get("fill", "none")))
            node.set("stroke", str(element.get("stroke", "none")))
            node.set("stroke-width", str(element.get("width", 1)))
        elif kind == "polygon":
            node = StdET.SubElement(svg_root, f"{{{SVG_NS}}}polygon", common)
            node.set("points", " ".join(f"{x},{y}" for x, y in element["points"]))
            node.set("fill", str(element.get("fill", "none")))
            node.set("stroke", str(element.get("stroke", "none")))
            node.set("stroke-width", str(element.get("width", 1)))
        elif kind == "image":
            node = StdET.SubElement(
                svg_root,
                f"{{{SVG_NS}}}image",
                {**common, "x": str(element["x"]), "y": str(element["y"]), "width": str(element["w"]), "height": str(element["h"]), "preserveAspectRatio": "none"},
            )
            _append_image_href(node, _job_path(root_dir, element["file"], f"{element['id']} image"), href_dir, embedded)
    StdET.indent(svg_root, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    StdET.ElementTree(svg_root).write(output_path, encoding="utf-8", xml_declaration=True)


def _discover_figedit(explicit: str | None) -> tuple[Path, str]:
    """Find the SVG converter, preferring the copy distributed with this skill."""
    candidates: list[tuple[Path, str]] = []
    if explicit:
        candidates.append((Path(explicit).expanduser().resolve(), "argument"))
    else:
        bundled = Path(__file__).resolve().parents[1] / "vendor"
        candidates.append((bundled, "bundled package"))
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            candidates.append((Path(codex_home).expanduser() / "skills" / "figedit", "CODEX_HOME"))
        candidates.append((Path.home() / ".codex" / "skills" / "figedit", "user skill directory"))
    for candidate, source in candidates:
        options = [candidate / "scripts", candidate]
        for scripts_dir in options:
            if (scripts_dir / "svg_to_pptx" / "pptx_builder.py").is_file():
                return scripts_dir.resolve(), source
    expected = ", ".join(str(path) for path, _ in candidates) or "a converter directory"
    raise FileNotFoundError(f"SVG-to-PPTX converter not found in {expected}.")


def _read_text_width_estimator(scripts_dir: Path):
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from svg_to_pptx.drawingml_utils import estimate_text_width
    except Exception as exc:
        raise RuntimeError(f"Unable to import FigEdit DrawingML helpers: {exc}") from exc
    return estimate_text_width


def _close_emu(actual: int, expected: int) -> bool:
    return abs(actual - expected) <= 1


def _compat_geometry(
    shape: ET._Element,
    element: dict[str, Any],
    estimate_text_width,
) -> tuple[ET._Element, ET._Element, ET._Element, int, int] | None:
    body = shape.find("p:txBody/a:bodyPr", NS)
    off = shape.find("p:spPr/a:xfrm/a:off", NS)
    ext = shape.find("p:spPr/a:xfrm/a:ext", NS)
    c_nv = shape.find("p:nvSpPr/p:cNvSpPr", NS)
    if body is None or off is None or ext is None or c_nv is None:
        return None
    if body.get("wrap") != "none" or body.find(f"{{{A_NS}}}spAutoFit") is None or c_nv.get("txBox") != "1":
        return None
    if int(body.get("lIns", "0")) != 0 or int(body.get("rIns", "0")) != 0:
        return None
    font_size = float(element["size"])
    font_weight = "700" if element.get("bold") else "400"
    width = estimate_text_width(element["text"], font_size, font_weight) * 1.05
    padding = font_size * 0.1
    tracking = max(float(element.get("spacing", 0)), 0) * max(len(element["text"]) - 1, 0)
    expected_cx = round((width + 2 * padding + tracking) * EMU_PER_PIXEL)
    if not _close_emu(int(ext.get("cx")), expected_cx):
        return None
    x = float(element["x"])
    if element["anchor"] == "middle":
        old_x = round((x - width / 2 - padding) * EMU_PER_PIXEL)
        corrected_x = old_x - round(tracking * EMU_PER_PIXEL / 2)
        paragraph_alignment = "ctr"
    elif element["anchor"] == "end":
        old_x = round((x - width - padding) * EMU_PER_PIXEL)
        corrected_x = old_x - round(tracking * EMU_PER_PIXEL)
        paragraph_alignment = "r"
    else:
        old_x = round((x - padding) * EMU_PER_PIXEL)
        corrected_x = old_x
        paragraph_alignment = "l"
    ppr = shape.find("p:txBody/a:p/a:pPr", NS)
    if ppr is None or ppr.get("algn", "l") != paragraph_alignment:
        return None
    actual_x = int(off.get("x"))
    if not (_close_emu(actual_x, old_x) or _close_emu(actual_x, corrected_x)):
        return None
    return body, off, ext, round(padding * EMU_PER_PIXEL), corrected_x


def patch_compatibility_and_canvas(
    pptx_path: Path,
    pages: list[dict[str, Any]],
    canvas: tuple[int, int],
    slide_size: tuple[int, int],
    language: str | None,
    estimate_text_width,
) -> dict[str, Any]:
    """Patch only FigEdit's recognized old textbox geometry and target canvas."""
    width, height = canvas
    target_width, target_height = slide_size
    report: dict[str, Any] = {
        "language_runs_changed": {},
        "legacy_text_padding_insets": [],
        "legacy_tracking_anchor_offsets": [],
        "canvas_scaling": {"applied": False, "sx": 1.0, "sy": 1.0},
    }
    temporary = pptx_path.with_name(f".{pptx_path.stem}.compat.tmp.pptx")
    try:
        with zipfile.ZipFile(pptx_path, "r") as source:
            pres_root = ET.fromstring(source.read("ppt/presentation.xml"))
            size_node = pres_root.find("p:sldSz", NS)
            if size_node is None:
                raise RuntimeError("PPTX presentation is missing p:sldSz.")
            current_width, current_height = int(size_node.get("cx")), int(size_node.get("cy"))
            source_dims = (width * EMU_PER_PIXEL, height * EMU_PER_PIXEL)
            target_dims = (target_width * EMU_PER_PIXEL, target_height * EMU_PER_PIXEL)
            if (current_width, current_height) == target_dims:
                sx = sy = 1.0
            elif (current_width, current_height) == source_dims:
                sx = target_width / width
                sy = target_height / height
                size_node.set("cx", str(target_dims[0]))
                size_node.set("cy", str(target_dims[1]))
                report["canvas_scaling"] = {"applied": sx != 1 or sy != 1, "sx": sx, "sy": sy}
            else:
                raise RuntimeError(
                    f"Unexpected FigEdit slide size {current_width}x{current_height} EMU; "
                    f"expected canvas {source_dims[0]}x{source_dims[1]} or target {target_dims[0]}x{target_dims[1]}."
                )

            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "ppt/presentation.xml":
                        data = ET.tostring(pres_root, xml_declaration=True, encoding="UTF-8", standalone=True)
                    elif re.fullmatch(r"ppt/slides/slide\d+\.xml", info.filename):
                        slide_number = int(re.search(r"slide(\d+)", info.filename).group(1))
                        if not 1 <= slide_number <= len(pages):
                            target.writestr(info, data)
                            continue
                        slide_root = ET.fromstring(data)
                        if language is not None:
                            changed = 0
                            for node in slide_root.iter():
                                if ET.QName(node).localname in {"rPr", "defRPr", "endParaRPr"}:
                                    node.set("lang", language)
                                    changed += 1
                            report["language_runs_changed"][str(slide_number)] = changed

                        page = pages[slide_number - 1]
                        text_elements = [item for item in page["elements"] if item["type"] == "text"]
                        text_shapes = [
                            shape for shape in slide_root.findall(".//p:sp", NS)
                            if shape.find("p:txBody", NS) is not None and shape.findall(".//a:t", NS)
                        ]
                        if len(text_shapes) != len(text_elements):
                            raise RuntimeError(
                                f"Slide {slide_number} has {len(text_shapes)} native text shapes for "
                                f"{len(text_elements)} text elements."
                            )
                        for shape, element in zip(text_shapes, text_elements):
                            recognized = _compat_geometry(shape, element, estimate_text_width)
                            if recognized is None:
                                continue
                            body, off, _ext, padding_emu, corrected_x = recognized
                            if int(off.get("x")) != corrected_x and element["anchor"] in {"middle", "end"} and float(element.get("spacing", 0)) != 0:
                                off.set("x", str(corrected_x))
                                report["legacy_tracking_anchor_offsets"].append(
                                    {"slide": slide_number, "id": element["id"], "anchor": element["anchor"]}
                                )
                            body.set("lIns", str(padding_emu))
                            body.set("rIns", str(padding_emu))
                            report["legacy_text_padding_insets"].append(
                                {"slide": slide_number, "id": element["id"], "inset_emu": padding_emu}
                            )

                        if sx != 1 or sy != 1:
                            for off in slide_root.findall(".//a:xfrm/a:off", NS):
                                off.set("x", str(round(int(off.get("x")) * sx)))
                                off.set("y", str(round(int(off.get("y")) * sy)))
                            for ext in slide_root.findall(".//a:xfrm/a:ext", NS):
                                ext.set("cx", str(round(int(ext.get("cx")) * sx)))
                                ext.set("cy", str(round(int(ext.get("cy")) * sy)))
                            for node in slide_root.iter():
                                tag = ET.QName(node).localname
                                if tag in {"rPr", "defRPr", "endParaRPr"}:
                                    if node.get("sz") is not None:
                                        node.set("sz", str(round(int(node.get("sz")) * sy)))
                                    if node.get("spc") is not None:
                                        node.set("spc", str(round(int(node.get("spc")) * sx)))
                                elif tag == "bodyPr":
                                    for attr in ("lIns", "rIns"):
                                        if node.get(attr) is not None:
                                            node.set(attr, str(round(int(node.get(attr)) * sx)))
                                elif tag == "ln" and node.get("w") is not None:
                                    node.set("w", str(round(int(node.get("w")) * sx)))
                        data = ET.tostring(slide_root, xml_declaration=True, encoding="UTF-8", standalone=True)
                    target.writestr(info, data)
        os.replace(temporary, pptx_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return report


def _notes_for_pages(job: dict[str, Any], pages: list[dict[str, Any]], root: Path) -> dict[str, str]:
    source_path = None
    source = None
    if "notes_from_pptx" in job:
        source_path = _job_path(root, job["notes_from_pptx"], "notes_from_pptx")
        source = Presentation(str(source_path))
    notes: dict[str, str] = {}
    for index, page in enumerate(pages, start=1):
        if "notes" in page:
            text = page["notes"]
        elif source is not None:
            source_index = page["number"] - 1
            if source_index >= len(source.slides):
                raise ValueError(
                    f"Page number {page['number']} has no corresponding notes slide in notes_from_pptx."
                )
            text = source.slides[source_index].notes_slide.notes_text_frame.text
        else:
            text = ""
        notes[f"slide_{index:02d}"] = text
    return notes


def _artifact_path(root: Path, raw: Any, label: str) -> Path:
    path = _job_path(root, raw, label, must_exist=False)
    if path.suffix.lower() != ".pptx":
        raise ValueError("output must end with .pptx.")
    return path


def _read_job(job_path: Path, figedit_dir: str | None):
    job_path = job_path.resolve()
    root = job_path.parent.resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if not isinstance(job, dict):
        raise ValueError("Job JSON must contain an object.")
    canvas = _dimension_pair(job.get("canvas"), "canvas")
    slide_size = _dimension_pair(job.get("slide_size", list(canvas)), "slide_size")
    raw_pages = job.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ValueError("pages must be a non-empty list of relative page JSON paths.")
    page_paths = [_job_path(root, raw, f"pages[{i}]") for i, raw in enumerate(raw_pages)]
    pages = [_validate_page(json.loads(path.read_text(encoding="utf-8")), path, canvas, root) for path in page_paths]
    output_path = _artifact_path(root, job.get("output"), "output")
    if output_path == job_path or output_path in page_paths:
        raise ValueError("output cannot overwrite the job JSON or a page JSON file.")
    source_paths = set(page_paths)
    if "notes_from_pptx" in job:
        source_paths.add(_job_path(root, job["notes_from_pptx"], "notes_from_pptx"))
    if output_path in source_paths:
        raise ValueError("output cannot overwrite a source PPTX or page input.")
    faces = _font_faces(job, root)
    for face in faces:
        source_paths.add(face["path"])
    for page in pages:
        for element in page["elements"]:
            if element["type"] == "image":
                source_paths.add(_job_path(root, element["file"], f"{element['id']} image"))
        if "plate" in page["background"]:
            source_paths.add(_job_path(root, page["background"]["plate"], "background plate"))
    if output_path in source_paths:
        raise ValueError("output cannot overwrite a source file.")
    language = job.get("language")
    if language is not None and (not isinstance(language, str) or not LANGUAGE_RE.fullmatch(language)):
        raise ValueError("language must be a BCP 47 language tag such as fr-FR, or null/omitted.")
    figedit_scripts, figedit_source = _discover_figedit(figedit_dir)
    estimator = _read_text_width_estimator(figedit_scripts)
    return root, job, canvas, slide_size, pages, page_paths, output_path, faces, language, source_paths, figedit_scripts, figedit_source, estimator


def export_job(job_path: Path, *, figedit_dir: str | None = None, overwrite: bool = False) -> Path:
    (
        root, job, canvas, slide_size, pages, _page_paths, output_path, faces, language,
        source_paths, figedit_scripts, figedit_source, estimate_text_width,
    ) = _read_job(job_path, figedit_dir)
    notes = _notes_for_pages(job, pages, root)
    report_path = output_path.with_name(f"{output_path.stem}.report.json")
    linked_final = (root / "svg").resolve()
    embedded_final = (root / "svg_embedded").resolve()
    if not _path_within(linked_final, root) or not _path_within(embedded_final, root):
        raise ValueError("svg/ and svg_embedded/ must remain inside the job directory.")
    planned = [output_path, report_path]
    for index in range(1, len(pages) + 1):
        name = f"slide_{index:02d}.svg"
        planned.extend((linked_final / name, embedded_final / name))
    conflicts = [str(path.relative_to(root)) for path in planned if path.exists()]
    if conflicts and not overwrite:
        raise FileExistsError("Output already exists (pass --overwrite to replace): " + ", ".join(conflicts))
    if any(path.exists() and path.is_dir() for path in planned):
        raise IsADirectoryError("An output file path is an existing directory.")
    if any(path.resolve() in source_paths for path in planned):
        raise ValueError("A generated artifact would overwrite one of the input files.")

    from svg_to_pptx.pptx_builder import create_pptx_with_native_svg

    with tempfile.TemporaryDirectory(prefix=".editorial-svg-export-", dir=root) as temp_name:
        stage = Path(temp_name)
        linked_dir = stage / "svg"
        embedded_dir = stage / "svg_embedded"
        linked_paths: list[Path] = []
        embedded_paths: list[Path] = []
        for index, page in enumerate(pages, start=1):
            name = f"slide_{index:02d}.svg"
            linked_path = linked_dir / name
            embedded_path = embedded_dir / name
            _write_svg(page, index, linked_path, linked_final, root, canvas, faces, False)
            _write_svg(page, index, embedded_path, embedded_final, root, canvas, faces, True)
            linked_paths.append(linked_path)
            embedded_paths.append(embedded_path)
        staged_pptx = stage / output_path.name
        success = create_pptx_with_native_svg(
            embedded_paths,
            staged_pptx,
            canvas_format=None,
            verbose=False,
            transition=None,
            use_compat_mode=False,
            notes=notes,
            enable_notes=True,
            use_native_shapes=True,
            animation=None,
            workers=1,
        )
        if not success or not staged_pptx.is_file():
            raise RuntimeError("FigEdit did not create the expected PowerPoint.")
        compatibility = patch_compatibility_and_canvas(
            staged_pptx, pages, canvas, slide_size, language, estimate_text_width
        )
        presentation = Presentation(str(staged_pptx))
        if len(presentation.slides) != len(pages):
            raise RuntimeError(f"Expected {len(pages)} slides, found {len(presentation.slides)}.")
        native_counts = []
        with zipfile.ZipFile(staged_pptx) as archive:
            for slide_index, page in enumerate(pages, start=1):
                slide_root = ET.fromstring(archive.read(f"ppt/slides/slide{slide_index}.xml"))
                shapes = slide_root.findall(".//p:sp", NS)
                text_count = sum(bool(shape.findall(".//a:t", NS)) for shape in shapes)
                geometry_count = len(shapes) - text_count
                pictures = len(slide_root.findall(".//p:pic", NS))
                expected_text = sum(item["type"] == "text" for item in page["elements"])
                expected_geometry = sum(item["type"] in {"line", "rect", "polygon"} for item in page["elements"])
                expected_geometry += int("fill" in page["background"])
                expected_pictures = sum(item["type"] == "image" for item in page["elements"])
                expected_pictures += int("plate" in page["background"])
                counts = {"text": text_count, "geometry": geometry_count, "pictures": pictures}
                expected = {"text": expected_text, "geometry": expected_geometry, "pictures": expected_pictures}
                if counts != expected:
                    raise RuntimeError(f"Slide {slide_index} native objects {counts} do not match source elements {expected}.")
                native_counts.append(counts)

        report = {
            "slides": len(pages),
            "canvas": list(canvas),
            "slide_size": list(slide_size),
            "native_objects": native_counts,
            "language": language,
            "figedit_discovery": figedit_source,
            "compatibility_fixes": compatibility,
            "generated": {
                "svg": [f"svg/slide_{i:02d}.svg" for i in range(1, len(pages) + 1)],
                "svg_embedded": [f"svg_embedded/slide_{i:02d}.svg" for i in range(1, len(pages) + 1)],
                "pptx": output_path.relative_to(root).as_posix(),
            },
        }
        staged_report = stage / report_path.name
        staged_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        for staged, final in ((linked_paths, linked_final), (embedded_paths, embedded_final)):
            final.mkdir(parents=True, exist_ok=True)
            for item in staged:
                os.replace(item, final / item.name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_pptx, output_path)
        os.replace(staged_report, report_path)
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_json", type=Path, help="job JSON; all relative paths are rooted at its directory")
    parser.add_argument("--figedit-dir", help="FigEdit skill or scripts directory (auto-discovered by default)")
    parser.add_argument("--overwrite", action="store_true", help="replace generated files with matching names")
    args = parser.parse_args(argv)
    try:
        output = export_job(args.job_json, figedit_dir=args.figedit_dir, overwrite=args.overwrite)
    except Exception as exc:
        print(f"export_editorial_svg: {exc}", file=sys.stderr)
        return 1
    print(f"Created {output}")
    print(f"Report {output.with_name(output.stem + '.report.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
