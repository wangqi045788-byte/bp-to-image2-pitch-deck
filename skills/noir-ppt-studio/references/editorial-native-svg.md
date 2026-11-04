# Editable SVG to native PowerPoint

Use this reference for approved raster-slide reconstruction. Keep jobs outside the skill folder. The included converter handles this page-JSON contract; use available presentation tooling for additional charts, equations and rendering.

## Representation and evidence

- Use source-image pixel coordinates. Text `y` is an alphabetic baseline, not the top of its visible box.
- Record the visible source box (`source_bbox: [x,y,w,h]`) for measured titles, labels, metrics and tight layouts. Verify it visually; OCR is only candidate evidence.
- Use a separate text object for each deliberate display line. Preserve exact diacritics, punctuation, units and qualifications. Do not convert ordinary text into paths.
- Use native lines, rectangles and polygons for dividers, arrows, cells and simple diagrams. Keep the topology correct; do not vectorize detector noise.
- Crop separable photographs exactly, excluding neighboring slide copy. Preserve original marks inside factual photography. Do not duplicate those marks as another visible text layer unless the embedded mark was actually removed.
- Use a text-free photographic plate when copy crosses an unrecoverable continuous image. Rebuild every slide title/label/page number above it. A plate with the old words still visible fails.
- Preserve genuine equations through FigEdit's math/Office Math route. Ordinary financial thresholds and numeric labels may remain editable typographic text; document that distinction rather than treating every `%` or comparison sign as an equation.

## Generic job contract

`scripts/export_editorial_svg.py` accepts a job file and uses the bundled FigEdit/PPT Master native DrawingML converter. No separate local FigEdit installation is required. It performs no network requests, dependency installation or font installation.

```json
{
  "language": "fr-FR",
  "canvas": [1600, 900],
  "slide_size": [1600, 900],
  "pages": ["pages/slide_01.json", "pages/slide_02.json"],
  "output": "output/editable.pptx",
  "notes_from_pptx": "input/reference.pptx",
  "font_faces": [{"family": "Example Display", "file": "fonts/example.ttf"}]
}
```

`notes_from_pptx` and `font_faces` are optional. All paths belong to the job directory. Keep output distinct from input. `pages` and `canvas` come from the task; do not impose the benchmark's page count, dimensions, company, language or file paths.

Each page has `number`, matching `canvas`, one `background` (`fill` or `plate`), and `elements`. Element IDs must be unique within the page. Supported elements:

```json
{
  "number": 1,
  "canvas": [1600, 900],
  "background": {"fill": "#111111"},
  "elements": [
    {"type":"image","id":"photograph","file":"assets/photo.png","x":900,"y":120,"w":600,"h":640},
    {"type":"text","id":"headline","text":"Créativité et valeur","x":100,"y":230,"font":"Example Display","size":72,"fill":"#F3F3F3","spacing":0,"anchor":"start","source_bbox":[100,170,700,65]},
    {"type":"line","id":"divider","x1":100,"y1":280,"x2":770,"y2":280,"stroke":"#BBBBBB","width":1}
  ]
}
```

Text supports `bold` and `italic`. Rectangles use `x,y,w,h,fill,stroke,width`; polygons use `points` plus fill/stroke/width. `anchor` is `start`, `middle` or `end`. Source boxes are evidence, not permission to compress typography arbitrarily. A page may provide `notes` to override its copied notes after a deliberate content update.

Run through the interpreter:

```text
python scripts/export_editorial_svg.py <job-directory>/job.json
python scripts/qa_editorial_pptx.py <job-directory>/output/editable.pptx --out-dir <job-directory>/qa --expected-slides <N> --min-text-per-slide 1 --probe-editability
```

Use `--figedit-dir` only to explicitly override the bundled converter. Use the QA tool's optional PDF and font-embedding outputs when required. Inspect `--help` if needed. Exported SVGs and native PPTX remain working outputs until visual QA is complete. Arbitrary external SVG with nested `tspan` nodes is outside this standalone page-JSON route.

For a deliberate offline-only check, add `--skip-office-render` and omit all other Office options. `--expected-aspect-ratio 16:9` is optional, not a global default. The Office helper has a bounded timeout and reports busy/unavailable phases separately; do not repeatedly retry an unchanged busy application or terminate PowerPoint to force a test.

## Typography issues proven by the benchmark

Treat these as compatibility cases, not universal font rules:

1. **Numeric SVG units.** The tested converter parsed `font-size` and `letter-spacing` with `float()`. Unit-suffixed strings such as `24px` could silently fall back. Emit numeric SVG user units.
2. **Locale.** French text emitted with `lang="zh-CN"` showed abnormal curly-apostrophe spacing in PowerPoint. Set slide text language from the actual job. Do not change Chinese notes to French or force all decks to one locale.
3. **Tracked anchors.** One converter version increased the width for positive tracking without moving middle/end-aligned frames. Its padding was also calculated but not applied as text insets. The adapter checks that geometry signature before compensation, so a fixed converter is not patched twice.
4. **Canvas.** A near-16:9 raster is not an exact 16:9 slide. Normalize positions, extents, font sizes, tracking and stroke widths together when the target size differs.
5. **Optical font metrics.** An installed font name does not ensure the same visible proportions as generated lettering. Compare rendered glyph width, height, baseline and spacing. A smaller font alone cannot fix a word that is simultaneously too wide and too short.
6. **Hairlines.** The benchmark's very large optical-size font instance lost fine strokes at content-page sizes. A tested moderate optical-size instance worked better there. This is not a mandate to use that font or optical size for another project.
7. **Units.** When a value and currency/scale unit crowd each other, use separate aligned native objects with a real gap; keep the value/unit relationship clear.

The exporter does not automatically solve visual font fitting. After any adjustment, render and inspect the affected page. Do not repair one title by tightening letters until they touch.

## Fonts and notes

Use the reference's type system when available and appropriately licensed. Font enumeration, a font file, and a successful PowerPoint render are stronger evidence than a registry entry alone. For portable delivery, embed fonts when their permissions allow it and verify the embedded-font list. Do not silently substitute a font while claiming pixel identity.

An optional open-font reference used in the approved local template is retained at `assets/fonts/BodoniModaEditorial-Regular.ttf` with `OFL.txt` and provenance. It is not a global default. Copy an authorized font into the job's `fonts/` directory before referencing it in `font_faces`. Register a job font only when needed for rendering; do not change system/global font settings merely by loading this skill.

Preserve notes, factual sources and language. Update obsolete delivery statements (for example “image-only”) and visual attribution when the actual output changes. The exporter copies notes or accepts explicit page notes; it does not guess which old statements should be removed.

## Release checks

The Windows QA helper uses a hidden PowerPoint document and closes only the document it opened. It must not close unrelated user presentations. Its optional editability probe changes a disposable copy, saves it, and reopens it. The source file hash must remain unchanged.

Office operations begin from a unique copy inside the QA directory, so auditing an input already open by the user cannot close that same presentation. The helper does not resolve linked external workbooks or media: preserve any authorized dependencies in the job, or use its structural checks while the appropriate presentation workflow handles those links.

Validate all required pages, native text/shape/image counts, visible copy, notes, exact target aspect, font behavior, photo crops, absence of old text under overlays, and SVG asset resolution. Check ZIP integrity for source bundles. Package only used assets and required licenses, keeping relative paths valid.

If PowerPoint is unavailable, report that limitation and perform the checks available. Do not describe XML object counts, a programmatic preview or a successful save as native-application visual approval.

The initial reusable-tool validation covered synthetic SVG/native-export cases and offline/timeout audit cases. Its final live Office round-trip was not completed because the local application was busy. The retained reference deck has its own successful native edit/save/reopen evidence, which is not a substitute for running the helper on a new job. The optional live integration test is enabled by `RUN_POWERPOINT_QA_INTEGRATION=1` when that testing is appropriate; keep unexecuted phases explicit.
