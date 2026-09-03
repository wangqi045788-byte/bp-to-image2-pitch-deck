#!/usr/bin/env python3
"""Validate the deck-brief contract without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED_MODES = {"private", "public"}
ALLOWED_ASPECTS = {"16:9", "4:3"}
ALLOWED_EVIDENCE_TYPES = {"reported", "derived", "user_assertion", "analyst_judgment"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
PUBLIC_LABELS = {"public", "synthetic", "third_party"}
NUMBER_RE = re.compile(r"(?:\d|[%$¥€£])")


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _require_text(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = _text(obj.get(key)).strip()
    if not value:
        errors.append(f"{path}.{key}: required non-empty string")
    return value


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["root: expected JSON object"], warnings

    if data.get("schema_version") != "1.0":
        errors.append("schema_version: expected '1.0'")

    job = data.get("job")
    if not isinstance(job, dict):
        errors.append("job: required object")
        job = {}
    for key in ("title", "objective", "audience", "language"):
        _require_text(job, key, "job", errors)
    mode = _text(job.get("mode"))
    if mode not in ALLOWED_MODES:
        errors.append(f"job.mode: expected one of {sorted(ALLOWED_MODES)}")
    aspect = _text(job.get("aspect_ratio"))
    if aspect not in ALLOWED_ASPECTS:
        errors.append(f"job.aspect_ratio: expected one of {sorted(ALLOWED_ASPECTS)}")
    count_instruction = job.get("requested_slide_count")
    if not isinstance(count_instruction, (str, int, dict)):
        errors.append("job.requested_slide_count: expected 'auto', integer, or range object")

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs: required object")
        inputs = {}
    _require_text(inputs, "user_prompt", "inputs", errors)
    company = inputs.get("company")
    if not isinstance(company, dict):
        errors.append("inputs.company: required object")
        company = {}
    _require_text(company, "name", "inputs.company", errors)
    sources = inputs.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("inputs.sources: expected at least one source")
        sources = []

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        path = f"inputs.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{path}: expected object")
            continue
        source_id = _require_text(source, "id", path, errors)
        if source_id in source_ids:
            errors.append(f"{path}.id: duplicate source id '{source_id}'")
        source_ids.add(source_id)
        _require_text(source, "kind", path, errors)
        label = _require_text(source, "label", path, errors)
        _require_text(source, "title", path, errors)
        if mode == "public" and label not in PUBLIC_LABELS:
            errors.append(f"{path}.label: '{label}' is not allowed in public mode")

    brand = data.get("brand")
    if not isinstance(brand, dict):
        errors.append("brand: required object")
        brand = {}
    for key in ("primary_colors", "accent_colors", "background_colors", "text_colors"):
        values = brand.get(key)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            errors.append(f"brand.{key}: expected non-empty string list")
    for key in ("typography", "shape_language", "image_direction", "logo_policy"):
        _require_text(brand, key, "brand", errors)
    basis = brand.get("basis")
    if not isinstance(basis, list):
        errors.append("brand.basis: expected source-id list")
    else:
        for source_id in basis:
            if source_id not in source_ids:
                errors.append(f"brand.basis: unknown source id '{source_id}'")

    evidence = data.get("evidence_cards")
    if not isinstance(evidence, list):
        errors.append("evidence_cards: expected list")
        evidence = []
    evidence_ids: set[str] = set()
    for index, card in enumerate(evidence):
        path = f"evidence_cards[{index}]"
        if not isinstance(card, dict):
            errors.append(f"{path}: expected object")
            continue
        evidence_id = _require_text(card, "id", path, errors)
        if evidence_id in evidence_ids:
            errors.append(f"{path}.id: duplicate evidence id '{evidence_id}'")
        evidence_ids.add(evidence_id)
        _require_text(card, "claim", path, errors)
        evidence_type = _require_text(card, "evidence_type", path, errors)
        if evidence_type not in ALLOWED_EVIDENCE_TYPES:
            errors.append(f"{path}.evidence_type: unsupported value '{evidence_type}'")
        source_id = _require_text(card, "source_id", path, errors)
        if source_id not in source_ids:
            errors.append(f"{path}.source_id: unknown source id '{source_id}'")
        _require_text(card, "locator", path, errors)
        confidence = _require_text(card, "confidence", path, errors)
        if confidence not in ALLOWED_CONFIDENCE:
            errors.append(f"{path}.confidence: unsupported value '{confidence}'")
        if not isinstance(card.get("public_safe"), bool):
            errors.append(f"{path}.public_safe: expected boolean")
        elif mode == "public" and not card["public_safe"]:
            errors.append(f"{path}.public_safe: false is not allowed in public mode")
        if evidence_type == "derived" and not _text(card.get("methodology")).strip():
            errors.append(f"{path}.methodology: required for derived evidence")

    narrative = data.get("narrative")
    if not isinstance(narrative, dict):
        errors.append("narrative: required object")
        narrative = {}
    _require_text(narrative, "thesis", "narrative", errors)
    storyline = narrative.get("storyline")
    if not isinstance(storyline, list) or not storyline:
        errors.append("narrative.storyline: expected non-empty string list")
    for key in ("assumptions", "omissions", "open_questions"):
        if not isinstance(narrative.get(key), list):
            errors.append(f"narrative.{key}: expected list")

    slides = data.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("slides: expected at least one slide")
        slides = []

    expected_number = 1
    for index, slide in enumerate(slides):
        path = f"slides[{index}]"
        if not isinstance(slide, dict):
            errors.append(f"{path}: expected object")
            continue
        if slide.get("number") != expected_number:
            errors.append(f"{path}.number: expected {expected_number}")
        expected_number += 1
        title = _require_text(slide, "title", path, errors)
        for key in ("archetype", "purpose", "key_message"):
            _require_text(slide, key, path, errors)

        content = slide.get("content")
        if not isinstance(content, list) or not content:
            errors.append(f"{path}.content: expected non-empty list")
            content = []
        body_chars = 0
        metric_items = 0
        for item_index, item in enumerate(content):
            item_path = f"{path}.content[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_path}: expected object")
                continue
            item_type = _require_text(item, "type", item_path, errors)
            item_text = _require_text(item, "text", item_path, errors)
            body_chars += len(item_text)
            if item_type == "metric":
                metric_items += 1
            item_evidence = item.get("evidence_ids")
            if not isinstance(item_evidence, list):
                errors.append(f"{item_path}.evidence_ids: expected list")
                item_evidence = []
            for evidence_id in item_evidence:
                if evidence_id not in evidence_ids:
                    errors.append(f"{item_path}.evidence_ids: unknown evidence id '{evidence_id}'")
            if NUMBER_RE.search(item_text) and not item_evidence:
                warnings.append(f"{item_path}: numeric-looking copy has no evidence id")

        visual = slide.get("visual")
        if not isinstance(visual, dict):
            errors.append(f"{path}.visual: required object")
            visual = {}
        for key in ("layout", "reading_path", "dominant_object", "mechanism"):
            _require_text(visual, key, f"{path}.visual", errors)
        zones = visual.get("zones")
        if not isinstance(zones, int) or zones < 1:
            errors.append(f"{path}.visual.zones: expected positive integer")
        elif zones > 3 and not visual.get("allow_dense_layout", False):
            errors.append(f"{path}.visual.zones: more than 3 requires allow_dense_layout=true")
        if not isinstance(visual.get("reference_asset_ids"), list):
            errors.append(f"{path}.visual.reference_asset_ids: expected list")

        copyfit = slide.get("copyfit")
        if not isinstance(copyfit, dict):
            errors.append(f"{path}.copyfit: required object")
            copyfit = {}
        title_max = copyfit.get("title_max_chars")
        body_max = copyfit.get("body_max_chars")
        metric_max = copyfit.get("metric_max")
        for key, value in (("title_max_chars", title_max), ("body_max_chars", body_max), ("metric_max", metric_max)):
            if not isinstance(value, int) or value < 0:
                errors.append(f"{path}.copyfit.{key}: expected non-negative integer")
        if isinstance(title_max, int) and len(title) > title_max:
            errors.append(f"{path}.title: {len(title)} chars exceeds copyfit limit {title_max}")
        if isinstance(body_max, int) and body_chars > body_max:
            errors.append(f"{path}.content: {body_chars} chars exceeds copyfit limit {body_max}")
        if isinstance(metric_max, int) and metric_items > metric_max:
            errors.append(f"{path}.content: {metric_items} metrics exceeds copyfit limit {metric_max}")

        note_ids = slide.get("source_note_evidence_ids")
        if not isinstance(note_ids, list):
            errors.append(f"{path}.source_note_evidence_ids: expected list")
        else:
            for evidence_id in note_ids:
                if evidence_id not in evidence_ids:
                    errors.append(f"{path}.source_note_evidence_ids: unknown evidence id '{evidence_id}'")
        image2 = slide.get("image2")
        if not isinstance(image2, dict):
            errors.append(f"{path}.image2: required object")
        elif not isinstance(image2.get("negative_constraints", []), list):
            errors.append(f"{path}.image2.negative_constraints: expected list")

    if isinstance(count_instruction, int) and len(slides) != count_instruction:
        errors.append(f"slides: expected exactly {count_instruction}, found {len(slides)}")
    if isinstance(count_instruction, dict):
        minimum = count_instruction.get("min")
        maximum = count_instruction.get("max")
        if not isinstance(minimum, int) or not isinstance(maximum, int) or minimum > maximum:
            errors.append("job.requested_slide_count: invalid min/max range")
        elif not minimum <= len(slides) <= maximum:
            errors.append(f"slides: {len(slides)} outside requested range {minimum}-{maximum}")

    return errors, warnings


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        data = load_json(args.brief)
    except (OSError, json.JSONDecodeError) as exc:
        if args.as_json:
            print(json.dumps({"status": "ERROR", "errors": [str(exc)], "warnings": []}, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors, warnings = validate(data)
    status = "VALID" if not errors else "INVALID"
    if args.as_json:
        print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        print(f"{status}: {len(errors)} error(s), {len(warnings)} warning(s)")
        for message in errors:
            print(f"ERROR: {message}")
        for message in warnings:
            print(f"WARNING: {message}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
