---
name: ppt-production
description: "Build or edit a PowerPoint after the message, evidence, and page plan are understood. Use when slides need editable text, shapes, tables, charts, images, speaker notes, or a tested PPTX export; works with any chosen style or analysis type."
---

# PPT Production

Turn an agreed message and page plan into a finished, editable `.pptx`. Choose design from the user's brief, reference, brand or audience; no single palette, layout or slide count is universal.

For a new deck, establish its objective, evidence and story first. Use sibling `$ppt-studio`, `$ppt-analysis`, `$ppt-research` and `$ppt-storyline` where appropriate. Analysis decides what the audience should learn; production makes it visible and editable.

## Create the deck

1. Select output size, language, type system, colors and page archetypes from the brief and chosen reference. Follow the supplied editable template when requested.
2. Put text and simple geometry in native PowerPoint objects. Use native tables and charts for data so users can edit cells, series and labels. Keep authentic or generated images as separate pictures.
3. Use diagrams, tables or photography as the main visual when they serve the message. Vary analytical layouts; do not force one text grid on every slide.
4. Keep units, period, denominator and source qualifications beside data or in notes. Do not recover facts from a visual reference when original sources are available.
5. Add detail and references to notes in the requested language. Keep displayed copy readable at presentation distance.
6. Render the exported presentation in the target app when available. Review each page; fix clipping, overlaps, fallback fonts, contrast, image crops and chart semantics. A structural pass is not visual approval.

## Deterministic page JSON converter

Use the included `scripts/build_deck.py` when a page plan fits the JSON format. It builds native text, shapes, lines, aspect-preserving cropped pictures, editable tables, editable charts and speaker notes.

```text
python <ppt-production>/scripts/build_deck.py <job>/deck.json --output <job>/output/deck.pptx
```

Read [page-json.md](references/page-json.md) for the contract. Positions use inches; default size is 13.333 × 7.5 inches. Existing outputs are protected unless `--overwrite` is supplied. Image paths are relative to the input JSON. The converter makes no network calls and installs no software or fonts.

Install this module's pinned Python dependencies into the selected environment with `python -m pip install -r <ppt-production>/requirements.txt` when they are missing. No dependency or font installation happens during a deck build.

For photographic reconstruction from SVG/JSON with editable layers, use the sibling `$noir-ppt-studio` converter when appropriate. The generic builder does not convert arbitrary SVG filters, external `<tspan>` documents or complex Office Math.

## Tables and charts

Before constructing a native table or chart, read [page-json.md](references/page-json.md). Validate series lengths, finite values and categories; distinguish blanks from zeroes in the source copy. Put units and periods in titles, axes or notes. Use a chart only when it clarifies the comparison.

Currently supported: clustered bar, clustered column, line, pie and doughnut charts. PowerPoint sets numeric-axis bounds automatically; this input format has no custom minimum/maximum axis bounds. Part-to-whole charts take one series of nonnegative values. The builder formats supplied verified values; it does not calculate evidence or choose conclusions.

## Quality gate

Inspect the actual presentation for correct copy and data, native text/shape/table/chart types, useful notes, source qualifications, presentation-size legibility, intentional image crops and intact originals. If native rendering is unavailable, report that limit. Do not infer visual quality from object counts or a successful file save.
