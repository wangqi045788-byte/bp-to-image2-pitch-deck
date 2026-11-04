#!/usr/bin/env python3
"""Run offline structural and optional Microsoft PowerPoint checks on a PPTX."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from pptx import Presentation


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS = {"p": P_NS}
PPTX_OPEN_XML = 24
PPTX_PDF = 32
MPO_PICTURE = {11, 13}
GEOMETRY_TYPES = {"AUTO_SHAPE", "CALLOUT", "CONNECTOR", "FREEFORM", "GROUP", "LINE"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_path(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve(strict=False)))


def same_path(first: Path, second: Path) -> bool:
    return normalized_path(first) == normalized_path(second)


def parse_aspect_ratio(value: str) -> float:
    try:
        width_text, height_text = value.split(":", 1)
        width, height = float(width_text), float(height_text)
    except (AttributeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("aspect ratio must use WIDTH:HEIGHT, such as 16:9") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("aspect ratio width and height must be positive")
    return width / height


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def office_backend_status(os_name: str | None = None, *, pywin32_available: bool | None = None) -> dict[str, str]:
    """Describe whether PowerPoint COM can be attempted without importing it."""
    system = os_name or platform.system()
    if system != "Windows":
        return {
            "status": "unavailable",
            "reason": "Microsoft PowerPoint COM automation is available only on Windows.",
        }
    if pywin32_available is None:
        try:
            pywin32_available = importlib.util.find_spec("win32com") is not None
        except (ImportError, ValueError):
            pywin32_available = False
    if not pywin32_available:
        return {
            "status": "unavailable",
            "reason": "pywin32 (win32com) is not installed; Office checks were not run.",
        }
    return {"status": "available", "reason": "Windows and pywin32 are available."}


def inspect_embedded_fonts(pptx_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(pptx_path) as archive:
        presentation_xml = ET.fromstring(archive.read("ppt/presentation.xml"))
        faces = sorted(
            {
                face
                for node in presentation_xml.findall(".//p:embeddedFont/p:font", NS)
                if (face := node.get("typeface"))
            }
        )
        parts = sorted(
            name
            for name in archive.namelist()
            if name.lower().startswith("ppt/fonts/") and not name.endswith("/")
        )
    return {"faces": faces, "package_parts": parts}


def shape_text(shape: Any) -> str:
    try:
        if shape.has_text_frame:
            return shape.text_frame.text.strip()
    except (AttributeError, ValueError):
        pass
    return ""


def inspect_structure(pptx_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "fail",
        "shape_count_scope": "top_level_shapes_only",
        "package_crc": {"status": "not_checked", "corrupt_member": None},
        "slide_count": None,
        "slide_width_emu": None,
        "slide_height_emu": None,
        "aspect_ratio": None,
        "aspect_ratio_check": {"status": "not_requested", "expected": None},
        "expected_slides": args.expected_slides,
        "min_text_per_slide": args.min_text_per_slide,
        "embedded_fonts": {"faces": [], "package_parts": []},
        "slides": [],
        "issues": [],
    }
    try:
        with zipfile.ZipFile(pptx_path) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member:
                result["package_crc"] = {"status": "fail", "corrupt_member": corrupt_member}
                result["issues"].append(f"PPTX ZIP CRC failed for package member: {corrupt_member}")
                return result
            result["package_crc"] = {"status": "pass", "corrupt_member": None}
            fonts = inspect_embedded_fonts(pptx_path)
            result["embedded_fonts"] = fonts

        deck = Presentation(str(pptx_path))
        slide_width = int(deck.slide_width)
        slide_height = int(deck.slide_height)
        ratio = slide_width / slide_height if slide_height else None
        result["slide_count"] = len(deck.slides)
        result["slide_width_emu"] = slide_width
        result["slide_height_emu"] = slide_height
        result["aspect_ratio"] = ratio

        if args.expected_slides is not None and len(deck.slides) != args.expected_slides:
            result["issues"].append(
                f"Slide count {len(deck.slides)} does not match expected {args.expected_slides}."
            )

        if args.expected_aspect_ratio is not None:
            expected_ratio = args.expected_aspect_ratio
            result["aspect_ratio_check"] = {
                "status": "pass" if ratio is not None and abs(ratio - expected_ratio) <= max(1e-6, expected_ratio * 0.005) else "fail",
                "expected": expected_ratio,
                "tolerance_relative": 0.005,
            }
            if result["aspect_ratio_check"]["status"] == "fail":
                result["issues"].append(
                    f"Aspect ratio {ratio:.6f} does not match requested {expected_ratio:.6f} within 0.5%."
                )

        for index, slide in enumerate(deck.slides, start=1):
            text_shapes = 0
            geometry_shapes = 0
            pictures = 0
            other_shapes = 0
            text_characters = 0
            for shape in slide.shapes:
                shape_type = getattr(shape.shape_type, "name", str(shape.shape_type))
                text = shape_text(shape)
                if shape_type in {"PICTURE", "LINKED_PICTURE"}:
                    pictures += 1
                elif text:
                    text_shapes += 1
                    text_characters += len(text)
                elif shape_type in GEOMETRY_TYPES:
                    geometry_shapes += 1
                else:
                    other_shapes += 1

            try:
                notes_nonempty = bool(slide.notes_slide.notes_text_frame.text.strip())
            except (AttributeError, ValueError):
                notes_nonempty = False

            slide_report = {
                "slide": index,
                "native_text_shapes": text_shapes,
                "native_text_characters": text_characters,
                "native_geometry_shapes": geometry_shapes,
                "pictures": pictures,
                "other_shapes": other_shapes,
                "notes_nonempty": notes_nonempty,
            }
            result["slides"].append(slide_report)
            if args.min_text_per_slide is not None and text_shapes < args.min_text_per_slide:
                result["issues"].append(
                    f"Slide {index} has {text_shapes} native text shapes; minimum is {args.min_text_per_slide}."
                )

        result["status"] = "pass" if not result["issues"] else "fail"
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError, ValueError) as exc:
        result["issues"].append(f"Could not inspect PPTX structure: {type(exc).__name__}: {exc}")
    return result


def initial_phase(name: str, requested: bool, *, reason: str | None = None) -> dict[str, Any]:
    phase: dict[str, Any] = {"requested": requested, "status": "pending" if requested else "not_requested"}
    if reason:
        phase["reason"] = reason
    return phase


def set_unavailable(phases: dict[str, dict[str, Any]], reason: str) -> None:
    for phase in phases.values():
        if phase["requested"]:
            phase["status"] = "unavailable"
            phase["reason"] = reason


def brief_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def is_com_busy(exc: BaseException) -> bool:
    retryable = {-2147418111, -2147417846}  # RPC_E_CALL_REJECTED / RPC_E_SERVERCALL_RETRYLATER
    hresult = getattr(exc, "hresult", None)
    if hresult is None and getattr(exc, "args", None):
        first = exc.args[0]
        if isinstance(first, int):
            hresult = first
    return hresult in retryable


def com_retry(action: Any, pythoncom: Any = None, *, attempts: int = 2, interval: float = 0.2) -> Any:
    """Retry only transient PowerPoint busy responses for a short bounded interval."""
    for attempt in range(attempts):
        try:
            return action()
        except Exception as exc:
            if not is_com_busy(exc) or attempt + 1 == attempts:
                raise
            if pythoncom is not None:
                try:
                    pythoncom.PumpWaitingMessages()
                except Exception:
                    pass
            time.sleep(interval)


def open_presentation(app: Any, pptx_path: Path, *, read_only: bool, pythoncom: Any) -> Any:
    return com_retry(
        lambda: app.Presentations.Open(str(pptx_path), read_only, False, False),
        pythoncom,
    )


def close_presentation(pres: Any, pythoncom: Any = None) -> bool:
    if pres is not None:
        try:
            com_retry(lambda: pres.Close(), pythoncom)
            return True
        except Exception:
            return False
    return True


def render_slides(app: Any, pptx_path: Path, out_dir: Path, width: int, pythoncom: Any) -> dict[str, Any]:
    render_dir = out_dir / "powerpoint_render"
    render_dir.mkdir(parents=True, exist_ok=True)
    pres = None
    try:
        pres = open_presentation(app, pptx_path, read_only=True, pythoncom=pythoncom)
        count = com_retry(lambda: int(pres.Slides.Count), pythoncom)
        slide_width = com_retry(lambda: float(pres.PageSetup.SlideWidth), pythoncom)
        slide_height = com_retry(lambda: float(pres.PageSetup.SlideHeight), pythoncom)
        height = max(1, round(width * slide_height / slide_width))
        exported: list[int] = []
        for index in range(1, count + 1):
            slide = com_retry(lambda: pres.Slides.Item(index), pythoncom)
            path = render_dir / f"slide-{index:03d}.png"
            com_retry(lambda: slide.Export(str(path), "PNG", width, height), pythoncom)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"PowerPoint did not create a non-empty render for slide {index}.")
            exported.append(index)
        return {
            "requested": True,
            "status": "pass" if exported == list(range(1, count + 1)) else "fail",
            "slide_count": count,
            "exported_slides": exported,
            "render_dir": str(render_dir),
            "render_width": width,
            "render_height": height,
            "with_window": False,
            "source_pptx": str(pptx_path),
        }
    finally:
        close_presentation(pres, pythoncom)


def export_pdf(app: Any, pptx_path: Path, pdf_path: Path, pythoncom: Any) -> dict[str, Any]:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pres = None
    try:
        pres = open_presentation(app, pptx_path, read_only=True, pythoncom=pythoncom)
        com_retry(lambda: pres.SaveAs(str(pdf_path), PPTX_PDF), pythoncom)
        pdf_signature = b""
        if pdf_path.is_file():
            with pdf_path.open("rb") as handle:
                pdf_signature = handle.read(5)
        if not pdf_path.is_file() or pdf_path.stat().st_size < 5 or pdf_signature != b"%PDF-":
            raise RuntimeError("PowerPoint did not create a valid PDF file.")
        return {
            "requested": True,
            "status": "pass",
            "path": str(pdf_path),
            "source_pptx": str(pptx_path),
            "with_window": False,
        }
    finally:
        close_presentation(pres, pythoncom)


def save_embedded_copy(app: Any, pptx_path: Path, output_path: Path, pythoncom: Any) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pres = None
    try:
        pres = open_presentation(app, pptx_path, read_only=True, pythoncom=pythoncom)
        com_retry(lambda: pres.SaveCopyAs(str(output_path), PPTX_OPEN_XML, -1), pythoncom)
    finally:
        close_presentation(pres, pythoncom)

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("PowerPoint did not create the requested embedded-font copy.")
    with zipfile.ZipFile(output_path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member:
            raise RuntimeError(f"Embedded copy failed ZIP CRC for package member: {corrupt_member}")
    fonts = inspect_embedded_fonts(output_path)
    detected = bool(fonts["faces"] or fonts["package_parts"])
    return {
        "requested": True,
        "status": "pass" if detected else "partial",
        "path": str(output_path),
        "with_window": False,
        "embed_true_type_fonts_requested": True,
        "embedded_fonts": fonts,
        "reason": None if detected else "PowerPoint saved the copy, but no embedded font data was detected.",
    }


def com_has_text(shape: Any, pythoncom: Any) -> bool:
    try:
        return com_retry(lambda: bool(shape.HasTextFrame) and bool(shape.TextFrame.HasText), pythoncom)
    except Exception:
        return False


def run_editability_probe(app: Any, pptx_path: Path, out_dir: Path, pythoncom: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "requested": True,
        "status": "pending",
        "text_edit_verified": False,
        "geometry_move_verified": False,
        "source_copy_only": True,
        "probed_pptx": str(pptx_path),
        "with_window": False,
    }
    probe_presentation = None
    reopened = None
    stage = "create temporary copy"
    with tempfile.TemporaryDirectory(prefix=".editability-probe-", dir=out_dir) as temp_dir:
        probe_path = Path(temp_dir) / "probe_copy.pptx"
        shutil.copy2(pptx_path, probe_path)
        try:
            stage = "open temporary copy"
            probe_presentation = open_presentation(app, probe_path, read_only=False, pythoncom=pythoncom)
            slide_count = com_retry(lambda: int(probe_presentation.Slides.Count), pythoncom)
            slide_width = com_retry(lambda: float(probe_presentation.PageSetup.SlideWidth), pythoncom)
            slide_height = com_retry(lambda: float(probe_presentation.PageSetup.SlideHeight), pythoncom)
            text_target: tuple[int, str] | None = None
            shape_target: tuple[int, str, float, float] | None = None

            stage = "locate editable text and geometry"
            for slide_index in range(1, slide_count + 1):
                slide = com_retry(lambda: probe_presentation.Slides.Item(slide_index), pythoncom)
                shape_count = com_retry(lambda: int(slide.Shapes.Count), pythoncom)
                for shape_index in range(1, shape_count + 1):
                    shape = com_retry(lambda: slide.Shapes.Item(shape_index), pythoncom)
                    has_text = com_has_text(shape, pythoncom)
                    if text_target is None and has_text:
                        text_target = (slide_index, str(com_retry(lambda: shape.Name, pythoncom)))
                    if shape_target is None and not has_text:
                        try:
                            shape_type = com_retry(lambda: int(shape.Type), pythoncom)
                            width = com_retry(lambda: float(shape.Width), pythoncom)
                            height = com_retry(lambda: float(shape.Height), pythoncom)
                            area = width * height
                            if shape_type not in MPO_PICTURE and shape_type != 14 and area < slide_width * slide_height * 0.4:
                                name = str(com_retry(lambda: shape.Name, pythoncom))
                                left = com_retry(lambda: float(shape.Left), pythoncom)
                                shape_target = (slide_index, name, left, width)
                        except Exception:
                            continue

            if text_target is None or shape_target is None:
                absent = []
                if text_target is None:
                    absent.append("a non-empty native text shape")
                if shape_target is None:
                    absent.append("a movable non-background native shape")
                result["status"] = "unavailable"
                result["reason"] = "The presentation has no " + " or ".join(absent) + "."
                return result

            text_slide, text_name = text_target
            text_shape = com_retry(lambda: probe_presentation.Slides.Item(text_slide).Shapes.Item(text_name), pythoncom)
            marker = f" [QA EDITABILITY {uuid.uuid4().hex[:8]}]"
            stage = "edit native text in temporary copy"
            original_text = str(com_retry(lambda: text_shape.TextFrame.TextRange.Text, pythoncom))
            com_retry(lambda: setattr(text_shape.TextFrame.TextRange, "Text", original_text + marker), pythoncom)

            move_slide, move_name, old_left, shape_width = shape_target
            movable = com_retry(lambda: probe_presentation.Slides.Item(move_slide).Shapes.Item(move_name), pythoncom)
            delta = 7.0
            if old_left + shape_width + delta > slide_width:
                delta = -7.0
            expected_left = old_left + delta
            stage = "move native shape in temporary copy"
            com_retry(lambda: setattr(movable, "Left", expected_left), pythoncom)
            stage = "save temporary copy"
            com_retry(lambda: probe_presentation.Save(), pythoncom)
            close_presentation(probe_presentation, pythoncom)
            probe_presentation = None

            stage = "reopen temporary copy"
            reopened = open_presentation(app, probe_path, read_only=True, pythoncom=pythoncom)
            reopened_text = com_retry(
                lambda: reopened.Slides.Item(text_slide).Shapes.Item(text_name).TextFrame.TextRange.Text,
                pythoncom,
            )
            reopened_left = com_retry(
                lambda: float(reopened.Slides.Item(move_slide).Shapes.Item(move_name).Left),
                pythoncom,
            )
            stage = "verify saved edits after reopening"
            text_ok = marker in str(reopened_text)
            move_ok = abs(reopened_left - expected_left) <= 0.05
            result.update(
                {
                    "status": "pass" if text_ok and move_ok else "fail",
                    "text_edit_verified": text_ok,
                    "geometry_move_verified": move_ok,
                    "text_slide": text_slide,
                    "geometry_slide": move_slide,
                    "geometry_shape": move_name,
                    "geometry_left_before": old_left,
                    "geometry_left_after": reopened_left,
                    "source_copy_only": True,
                }
            )
            if not (text_ok and move_ok):
                result["reason"] = "A saved edit did not survive reopening of the temporary probe copy."
            return result
        except Exception as exc:
            if is_com_busy(exc):
                result["status"] = "unavailable"
                result["office_busy"] = True
                result["reason"] = f"PowerPoint was busy and rejected the editability probe at {stage}: {brief_error(exc)}"
            else:
                result["status"] = "error"
                result["reason"] = f"{stage}: {brief_error(exc)}"
            return result
        finally:
            close_presentation(probe_presentation, pythoncom)
            close_presentation(reopened, pythoncom)


def run_office_phases_live(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    requested = {
        "office_render": not args.skip_office_render,
        "pdf_export": args.pdf is not None,
        "embed_output": args.embed_output is not None,
        "editability_probe": args.probe_editability,
    }
    phases = {
        name: initial_phase(name, flag)
        for name, flag in requested.items()
    }
    needs_office = any(requested.values())
    if not needs_office:
        return {
            "office_runtime": {"status": "not_requested", "reason": "No Office-dependent phase was requested."},
            **phases,
        }

    availability = office_backend_status()
    if availability["status"] != "available":
        set_unavailable(phases, availability["reason"])
        return {"office_runtime": availability, **phases}

    try:
        import pythoncom  # type: ignore[import-not-found]
        import win32com.client  # type: ignore[import-not-found]
    except Exception as exc:
        unavailable = {"status": "unavailable", "reason": f"pywin32 could not be imported: {brief_error(exc)}"}
        set_unavailable(phases, unavailable["reason"])
        return {"office_runtime": unavailable, **phases}

    app = None
    initial_presentation_count = 0
    com_initialized = False
    old_alerts: Any = None
    alerts_changed = False
    busy_reason: str | None = None
    runtime: dict[str, Any] = {"status": "available", "reason": "PowerPoint COM is ready."}
    try:
        pythoncom.CoInitialize()
        com_initialized = True
        try:
            app = com_retry(lambda: win32com.client.DispatchEx("PowerPoint.Application"), pythoncom)
        except Exception as exc:
            runtime = {
                "status": "unavailable",
                "reason": f"Microsoft PowerPoint COM server could not be started: {brief_error(exc)}",
            }
            set_unavailable(phases, runtime["reason"])
            return {"office_runtime": runtime, **phases}

        try:
            initial_presentation_count = int(com_retry(lambda: app.Presentations.Count, pythoncom))
        except Exception as exc:
            initial_presentation_count = -1
            reason = f"PowerPoint presentation state could not be read; Office work was skipped to preserve open documents: {brief_error(exc)}"
            runtime["reason"] = reason
            set_unavailable(phases, reason)
            return {"office_runtime": runtime, **phases}
        runtime["preexisting_presentations"] = initial_presentation_count

        working_copy = out_dir / f"office_source_{uuid.uuid4().hex}.pptx"
        try:
            source_hash = sha256(args.input)
            shutil.copy2(args.input, working_copy)
            if sha256(working_copy) != source_hash:
                raise RuntimeError("QA working copy SHA-256 does not match the input.")
        except Exception:
            working_copy.unlink(missing_ok=True)
            raise
        runtime["working_source_copy"] = str(working_copy)

        if initial_presentation_count == 0:
            try:
                old_alerts = com_retry(lambda: app.DisplayAlerts, pythoncom)
                com_retry(lambda: setattr(app, "DisplayAlerts", 1), pythoncom)
                alerts_changed = True
            except Exception:
                old_alerts = None
                alerts_changed = False

        def run_phase(name: str, operation: Any) -> None:
            nonlocal busy_reason
            if not requested[name]:
                return
            if busy_reason:
                phases[name] = {
                    "requested": True,
                    "status": "unavailable",
                    "reason": "Not attempted after PowerPoint rejected an automation call while busy.",
                }
                return
            try:
                phases[name] = operation()
            except Exception as exc:
                busy = is_com_busy(exc)
                if busy:
                    busy_reason = brief_error(exc)
                phases[name] = {
                    "requested": True,
                    "status": "unavailable" if busy else "error",
                    "reason": f"PowerPoint was busy: {brief_error(exc)}" if busy else brief_error(exc),
                }

        run_phase(
            "office_render",
            lambda: render_slides(app, working_copy, out_dir, args.render_width, pythoncom),
        )
        run_phase(
            "embed_output",
            lambda: save_embedded_copy(app, working_copy, args.embed_output, pythoncom),
        )

        effective_deck = working_copy
        if args.embed_output is not None and phases["embed_output"]["status"] in {"pass", "partial"}:
            effective_deck = args.embed_output
        run_phase(
            "pdf_export",
            lambda: export_pdf(app, effective_deck, args.pdf, pythoncom),
        )
        run_phase(
            "editability_probe",
            lambda: run_editability_probe(app, effective_deck, out_dir, pythoncom),
        )
        if phases["editability_probe"].get("office_busy"):
            busy_reason = phases["editability_probe"].get("reason")
    except Exception as exc:
        runtime = {"status": "error", "reason": brief_error(exc)}
        for name, flag in requested.items():
            if flag and phases[name]["status"] == "pending":
                phases[name] = {"requested": True, "status": "error", "reason": brief_error(exc)}
    finally:
        if app is not None and alerts_changed and old_alerts is not None:
            try:
                com_retry(lambda: setattr(app, "DisplayAlerts", old_alerts), pythoncom)
            except Exception:
                pass
        if app is not None and initial_presentation_count == 0 and not busy_reason:
            try:
                if int(com_retry(lambda: app.Presentations.Count, pythoncom)) == 0:
                    com_retry(lambda: app.Quit(), pythoncom)
            except Exception:
                pass
        if com_initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
    return {"office_runtime": runtime, **phases}


def run_office_phases(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    requested = {
        "office_render": not args.skip_office_render,
        "pdf_export": args.pdf is not None,
        "embed_output": args.embed_output is not None,
        "editability_probe": args.probe_editability,
    }
    if not any(requested.values()) or office_backend_status()["status"] != "available":
        return run_office_phases_live(args, out_dir)

    worker_request = {
        "input": str(args.input),
        "out_dir": str(out_dir),
        "pdf": str(args.pdf) if args.pdf is not None else None,
        "embed_output": str(args.embed_output) if args.embed_output is not None else None,
        "probe_editability": bool(args.probe_editability),
        "skip_office_render": bool(args.skip_office_render),
        "render_width": int(args.render_width),
    }
    request_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix=".office-worker-request-",
            dir=out_dir,
            delete=False,
        ) as handle:
            request_path = Path(handle.name)
            json.dump(worker_request, handle, ensure_ascii=False)

        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--office-worker", str(request_path)],
            cwd=str(args.input.parent),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=args.office_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        phases = {
            name: initial_phase(name, flag)
            for name, flag in requested.items()
        }
        set_unavailable(
            phases,
            f"PowerPoint helper exceeded the {args.office_timeout}-second timeout and the helper process was stopped.",
        )
        return {
            "office_runtime": {
                "status": "unavailable",
                "reason": f"Office helper timed out after {args.office_timeout} seconds; only the helper was stopped, and PowerPoint was not terminated.",
            },
            **phases,
        }
    except OSError as exc:
        phases = {
            name: initial_phase(name, flag)
            for name, flag in requested.items()
        }
        reason = f"Could not start the PowerPoint helper process: {brief_error(exc)}"
        set_unavailable(phases, reason)
        return {"office_runtime": {"status": "unavailable", "reason": reason}, **phases}
    finally:
        if request_path is not None:
            request_path.unlink(missing_ok=True)

    worker_result: dict[str, Any] | None = None
    for line in reversed(completed.stdout.splitlines()):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "office_runtime" in parsed:
            worker_result = parsed
            break
    if completed.returncode != 0 or worker_result is None:
        reason = "PowerPoint helper returned no valid phase report."
        detail = (completed.stderr or completed.stdout).strip()
        if detail:
            reason += " " + detail[-2000:]
        phases = {
            name: initial_phase(name, flag)
            for name, flag in requested.items()
        }
        for name, flag in requested.items():
            if flag:
                phases[name] = {"requested": True, "status": "error", "reason": reason}
        return {"office_runtime": {"status": "error", "reason": reason}, **phases}
    return worker_result


def office_worker_main(request_path: Path) -> int:
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        args = argparse.Namespace(
            input=Path(request["input"]),
            out_dir=Path(request["out_dir"]),
            pdf=Path(request["pdf"]) if request.get("pdf") else None,
            embed_output=Path(request["embed_output"]) if request.get("embed_output") else None,
            probe_editability=bool(request.get("probe_editability")),
            skip_office_render=bool(request.get("skip_office_render")),
            render_width=int(request["render_width"]),
        )
        result = run_office_phases_live(args, args.out_dir)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"worker_error": brief_error(exc)}, ensure_ascii=False))
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect PPTX structure offline and optionally render or probe it with Microsoft PowerPoint."
    )
    parser.add_argument("input", type=Path, help="Input PowerPoint .pptx; never modified by this tool.")
    parser.add_argument("--out-dir", required=True, type=Path, help="Directory for the JSON report and any slide renders.")
    parser.add_argument("--expected-slides", type=positive_int, help="Fail structure checks unless the slide count matches.")
    parser.add_argument("--min-text-per-slide", type=nonnegative_int, help="Fail if any slide has fewer non-empty native text shapes.")
    parser.add_argument(
        "--expected-aspect-ratio",
        type=parse_aspect_ratio,
        help="Optionally check WIDTH:HEIGHT, such as 16:9. No aspect ratio is assumed by default.",
    )
    parser.add_argument("--pdf", type=Path, help="Optionally export a PDF to this new path using PowerPoint.")
    parser.add_argument("--embed-output", type=Path, help="Optionally save a separate PPTX copy requesting TrueType font embedding.")
    parser.add_argument("--probe-editability", action="store_true", help="Edit text and move a native shape in a temporary copy, save, and reopen it for verification.")
    parser.add_argument("--skip-office-render", action="store_true", help="Run structure checks only unless another Office option is supplied.")
    parser.add_argument("--render-width", type=positive_int, default=1600, help="PowerPoint render width in pixels (default: 1600).")
    parser.add_argument("--office-timeout", type=positive_int, default=120, help="Maximum seconds for the isolated PowerPoint helper (default: 120).")
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    args.input = args.input.expanduser().resolve(strict=False)
    args.out_dir = args.out_dir.expanduser().resolve(strict=False)
    if not args.input.is_file():
        parser.error(f"input PPTX does not exist: {args.input}")
    if args.input.suffix.lower() != ".pptx":
        parser.error("input must have a .pptx extension")

    if args.pdf is not None:
        args.pdf = args.pdf.expanduser().resolve(strict=False)
        if args.pdf.suffix.lower() != ".pdf":
            parser.error("--pdf output path must have a .pdf extension")
        if same_path(args.input, args.pdf):
            parser.error("PDF output path must be different from the input PPTX")
        if args.pdf.exists():
            parser.error(f"PDF output already exists; choose a new path: {args.pdf}")

    if args.embed_output is not None:
        args.embed_output = args.embed_output.expanduser().resolve(strict=False)
        if args.embed_output.suffix.lower() != ".pptx":
            parser.error("--embed-output path must have a .pptx extension")
        if same_path(args.input, args.embed_output):
            parser.error("embedded-font output path must be different from the input PPTX")
        if args.embed_output.exists():
            parser.error(f"embedded-font output already exists; choose a new path: {args.embed_output}")
        if args.pdf is not None and same_path(args.pdf, args.embed_output):
            parser.error("--pdf and --embed-output must use different output paths")


def determine_overall_status(report: dict[str, Any]) -> str:
    if report["structure"]["status"] != "pass":
        return "fail"
    phases = [report[key] for key in ("office_render", "pdf_export", "embed_output", "editability_probe")]
    requested = [phase for phase in phases if phase["requested"]]
    if any(phase["status"] == "fail" for phase in requested):
        return "fail"
    if any(phase["status"] in {"unavailable", "error", "partial"} for phase in requested):
        return "partial"
    return "pass"


def make_unexecuted(report: dict[str, Any], explicitly_skipped_render: bool) -> list[str]:
    items = ["Human visual review of rendered slide images; structural counts and PNG export are not visual acceptance."]
    if explicitly_skipped_render:
        items.append("PowerPoint slide rendering was explicitly skipped.")
    else:
        render = report["office_render"]
        if render["status"] == "unavailable":
            items.append("PowerPoint slide rendering was unavailable.")
        elif render["status"] == "error":
            items.append("PowerPoint slide rendering did not complete.")
    for key, label in (
        ("pdf_export", "PDF export"),
        ("embed_output", "embedded-font copy"),
        ("editability_probe", "editability probe"),
    ):
        phase = report[key]
        if phase["requested"] and phase["status"] in {"unavailable", "error", "partial", "fail"}:
            items.append(f"{label}: {phase.get('reason', phase['status'])}")
    return items


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--office-worker":
        if len(argv) != 2:
            print("office worker requires one request JSON path", file=sys.stderr)
            return 2
        return office_worker_main(Path(argv[1]))

    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    original_hash = sha256(args.input)
    structure = inspect_structure(args.input, args)
    if structure["status"] == "pass":
        office = run_office_phases(args, args.out_dir)
    else:
        office = {
            "office_runtime": {"status": "not_run", "reason": "PPTX structural inspection failed."},
            "office_render": initial_phase("office_render", not args.skip_office_render, reason="Not run after a structural failure."),
            "pdf_export": initial_phase("pdf_export", args.pdf is not None, reason="Not run after a structural failure."),
            "embed_output": initial_phase("embed_output", args.embed_output is not None, reason="Not run after a structural failure."),
            "editability_probe": initial_phase("editability_probe", args.probe_editability, reason="Not run after a structural failure."),
        }
        for phase in (office["office_render"], office["pdf_export"], office["embed_output"], office["editability_probe"]):
            if phase["status"] == "pending":
                phase["status"] = "not_run"

    final_hash = sha256(args.input)
    source_unchanged = original_hash == final_hash
    if not source_unchanged:
        structure["status"] = "fail"
        structure["issues"].append("Input PPTX SHA-256 changed while QA was running.")

    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "pending",
        "input": {"path": str(args.input), "sha256_before": original_hash, "sha256_after": final_hash, "unchanged": source_unchanged},
        "structure": structure,
        **office,
        "visual_review": {
            "status": "not_performed",
            "note": "Structural object counts and exported PNG files do not constitute visual inspection.",
        },
        "unexecuted": [],
    }
    report["status"] = determine_overall_status(report)
    report["unexecuted"] = make_unexecuted(report, args.skip_office_render)
    report_path = args.out_dir / "qa_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "status": report["status"],
        "report": str(report_path),
        "structure": structure["status"],
        "office_render": report["office_render"]["status"],
        "editability_probe": report["editability_probe"]["status"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    if report["status"] == "pass":
        return 0
    if report["status"] == "fail":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
