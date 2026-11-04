---
name: ppt-quality
description: "Review analytical presentations for evidence, calculations, narrative, native editability, charts/tables, typography and exported-slide quality. Use before delivering a PPT or when auditing/fixing an existing deck; distinguish structural checks from actual visual verification."
---

# PPT Quality

Inspect the final deliverable against the user's objective, authoritative sources and selected design. Do not approve a deck merely because a builder succeeded or the slides contain many native objects.

## Check the important failure modes

1. **Substance:** required questions answered; claims match sources and confidence; historical results, estimates and targets distinguished; material caveats visible; counterevidence and risks not dropped for a smoother story.
2. **Numbers:** periods, dates, units, denominators, currencies and definitions agree across text, native charts, tables and notes. Recompute totals/percentages and identify forecast assumptions. Do not force an invalid total to 100%.
3. **Narrative:** headline follows from evidence; recommendations answer the decision; options and tradeoffs use comparable criteria; required pages present; no repeated filler.
4. **Native semantics:** text is editable text, table cells remain table cells, analytical charts retain actual data/series, and photos are separate images. A whole-slide screenshot or SVG wrapper is not decomposition.
5. **Visual output:** inspect every exported page at full size for clipped/wrapped text, missing glyphs, weak contrast, overlaps, misaligned objects, broken charts, inconsistent type and incorrect crops. Inspect a contact sheet for pacing and image repetition.
6. **Delivery:** notes/sources preserved, links and assets resolve, filenames clear, originals intact, and requested formats actually open. Sensitive source files do not enter a public package.

## Tools and limits

The suite's [native builder](../ppt-production/SKILL.md) returns actual PowerPoint objects. Use the included `../noir-ppt-studio/scripts/qa_editorial_pptx.py` for package/native counts, notes and optional Windows PowerPoint rendering. Its offline report is structural evidence only.

```text
python <suite>/noir-ppt-studio/scripts/qa_editorial_pptx.py <job>/output/deck.pptx --out-dir <job>/qa/office --expected-slides N --probe-editability
```

If PowerPoint is unavailable, use an available presentation renderer for visible checks and disclose the different rendering environment. With no renderer, finish structural/content checks and label visual verification unavailable. Do not stop all independent work or fabricate render screenshots.

Use unique copies for Office save/reopen tests. Preserve the user's open presentations and source hash. The standalone quality skill can be applied manually when helper modules are not installed; disclose which automated checks were unavailable.

## Report and repair

Record `check`, `status`, `evidence`, `issue`, and `action` in a compact QA ledger. Valid statuses include passed, failed, not applicable and unavailable. Known wrong content, broken native data or unreadable required copy blocks a verified-final claim. Unexecuted phases are not passed.

Fix the source of a defect: correct the data mapping, copy, text frame, font choice or asset crop; then rerender the affected pages. Repeat broader checks only when the change could affect them. Preserve a prior accepted version and report material intentional raster regions or substitutions.

Provide a concise delivery note with artifact links, checked scope and unresolved limitations. Do not replace the presentation with the check report.
