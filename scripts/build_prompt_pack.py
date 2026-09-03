#!/usr/bin/env python3
"""Build deterministic, high-complexity Image2 prompts from deck-brief.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_deck_brief import validate


def _lines(values: list[str], prefix: str = "- ") -> str:
    return "\n".join(f"{prefix}{value}" for value in values) if values else f"{prefix}None"


def _source_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {source["id"]: source for source in data["inputs"]["sources"]}


def _evidence_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["id"]: card for card in data["evidence_cards"]}


def build_prompt_pack(data: dict[str, Any]) -> str:
    brand = data["brand"]
    job = data["job"]
    evidence = _evidence_index(data)
    sources = _source_index(data)
    global_negative = [
        "generic blue-purple neon technology styling unless explicitly required by the brand",
        "glassmorphism, random floating 3D blocks, decorative card walls, robot figures, and meaningless icons",
        "invented numbers, names, customers, logos, interfaces, charts, citations, or product features",
        "pseudo-text, malformed Chinese, duplicated characters, changed units, clipped copy, or tiny unreadable type",
        "distorted, recolored, relabeled, or redesigned factual reference assets",
    ]
    header = [
        "# Image2 production prompt pack",
        "",
        f"- Job: {job['title']}",
        f"- Objective: {job['objective']}",
        f"- Audience: {job['audience']}",
        f"- Language: {job['language']}",
        f"- Canvas: {job['aspect_ratio']}",
        f"- Mode: {job['mode']}",
        "",
        "## Global brand system",
        "",
        f"- Brand evidence: {', '.join(brand.get('basis', []))}",
        f"- Primary colors: {', '.join(brand['primary_colors'])}",
        f"- Accent colors: {', '.join(brand['accent_colors'])}",
        f"- Background colors: {', '.join(brand['background_colors'])}",
        f"- Text colors: {', '.join(brand['text_colors'])}",
        f"- Typography: {brand['typography']}",
        f"- Shape language: {brand['shape_language']}",
        f"- Image direction: {brand['image_direction']}",
        f"- Logo policy: {brand['logo_policy']}",
        f"- Forbidden motifs: {', '.join(brand.get('forbidden_motifs', []))}",
        "",
        "## Deck-level instruction",
        "",
        "Act as a senior investment-banking presentation art director. Produce a complete, presentation-ready slide—not a mood board, website, poster, or collection of disconnected cards. Keep the deck coherent through shared margins, typography, palette, evidence treatment, and finish while varying page mechanics intentionally.",
    ]

    sections: list[str] = ["\n".join(header)]
    for slide in data["slides"]:
        slide_evidence_ids = slide.get("source_note_evidence_ids", [])
        evidence_lines: list[str] = []
        source_lines: list[str] = []
        used_source_ids: set[str] = set()
        for evidence_id in slide_evidence_ids:
            card = evidence[evidence_id]
            evidence_lines.append(
                f"{evidence_id} [{card['evidence_type']}, {card['confidence']}]: {card['claim']} "
                f"(source {card['source_id']}, locator {card['locator']})"
            )
            used_source_ids.add(card["source_id"])
        for source_id in sorted(used_source_ids):
            source = sources[source_id]
            source_lines.append(
                f"{source_id}: {source['title']} | {source['kind']} | {source['label']} | {source.get('locator', 'n/a')}"
            )

        copy_lines = [f"[{item['type']}] {item['text']}" for item in slide["content"]]
        asset_ids = slide["visual"].get("reference_asset_ids", [])
        page_negative = global_negative + brand.get("forbidden_motifs", []) + slide.get("image2", {}).get("negative_constraints", [])
        section = [
            f"## Slide {slide['number']}: {slide['title']}",
            "",
            "### Role and deliverable",
            f"Create one finished {job['aspect_ratio']} pitch-deck slide at the highest available quality. The final canvas must be suitable for edge-to-edge placement in PowerPoint.",
            "",
            "### Objective and audience",
            f"- Purpose: {slide['purpose']}",
            f"- Key message: {slide['key_message']}",
            f"- Audience: {job['audience']}",
            "",
            "### Exact visible copy",
            "Render every line below exactly. Do not paraphrase, translate, add, remove, duplicate, or change punctuation, numbers, units, capitalization, or qualifiers.",
            _lines(copy_lines),
            "",
            "### Evidence lock",
            _lines(evidence_lines),
            "",
            "### Source index",
            _lines(source_lines),
            "",
            "### Reference assets",
            f"- Required asset IDs: {', '.join(asset_ids) if asset_ids else 'None'}",
            "- Preserve every factual logo, product image, interface, report excerpt, or chart exactly. Do not redesign, relabel, recolor, or fabricate it. If exact preservation is impossible, reserve a clean region for lossless post-compositing.",
            "",
            "### Composition",
            f"- Layout: {slide['visual']['layout']}",
            f"- Reading path: {slide['visual']['reading_path']}",
            f"- Dominant object: {slide['visual']['dominant_object']}",
            f"- Major visual zones: {slide['visual']['zones']}",
            f"- Visual mechanism: {slide['visual']['mechanism']}",
            "- Use disciplined institutional spacing, deliberate asymmetry where useful, a clear first-glance message, and meaningful whitespace. Do not give every element equal weight.",
            "",
            "### Brand and craft",
            f"- Palette: primary {', '.join(brand['primary_colors'])}; accents {', '.join(brand['accent_colors'])}; backgrounds {', '.join(brand['background_colors'])}; text {', '.join(brand['text_colors'])}.",
            f"- Typography: {brand['typography']}",
            f"- Shape language: {brand['shape_language']}",
            f"- Image direction: {brand['image_direction']}",
            f"- Page-specific direction: {slide.get('image2', {}).get('direction', 'Use the brief without adding decorative concepts.')}",
            "- High complexity means precise relationships among message, evidence, layout, material, and hierarchy—not extra decoration.",
            "",
            "### Negative constraints",
            _lines(list(dict.fromkeys(page_negative))),
            "",
            "### Acceptance criteria",
            "- Correct aspect ratio and complete edge-to-edge canvas.",
            "- Exact visible copy with no pseudo-text or duplicated characters.",
            "- All numbers and factual statements match the evidence lock.",
            "- Required reference assets remain intact and recognizable.",
            "- One clear reading path, no accidental crowding, clipping, overlap, or weak hierarchy.",
            "- The slide feels specific to this company and cannot be reused unchanged for an unrelated company.",
        ]
        sections.append("\n".join(section))
    return "\n\n---\n\n".join(sections) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("private", "public"))
    parser.add_argument("--allow-exact-external", action="store_true", help="Acknowledge exact external assets in public mode after rights review.")
    args = parser.parse_args()
    try:
        data = json.loads(args.brief.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.mode:
        data.setdefault("job", {})["mode"] = args.mode
    errors, warnings = validate(data)
    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    if data["job"]["mode"] == "public" and any(
        source.get("label") == "third_party" for source in data["inputs"]["sources"]
    ) and not args.allow_exact_external:
        print("ERROR: public mode contains third-party sources; pass --allow-exact-external only after rights review", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_prompt_pack(data), encoding="utf-8")
    print(f"WROTE: {args.out} ({len(data['slides'])} slide prompts, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
