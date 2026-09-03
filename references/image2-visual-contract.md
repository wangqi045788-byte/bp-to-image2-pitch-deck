# Image2 visual contract

The designed slide surface is generated with Image2 and delivered as one full-slide visual. This is intentionally different from an editable-object reconstruction.

## Generation modes

### Full-slide generation

Use when the page contains no exact external asset that must remain pixel-faithful. Image2 receives the full prompt and renders the complete canvas.

### Reference-image editing

Use when a supplied logo, product photo, interface, report excerpt, or visual reference must guide the page. Provide only the minimum required reference images and identify each one in the prompt.

### Lossless evidence composite

If Image2 cannot preserve a factual asset exactly, generate the designed surface with an explicit reserved region, then composite the unmodified asset into the final raster. Do not recreate the asset. The final PowerPoint slide must still contain one full-slide visual rather than native PowerPoint overlays. Record the composite in the QA ledger.

## Prohibited shortcuts

- Do not use a screenshot of an existing slide as the new slide.
- Do not claim the output is object-level editable.
- Do not add native PowerPoint shapes or text merely to hide a generation failure.
- Do not let Image2 invent logos, interfaces, charts, numbers, citations, customer names, or product features.
- Do not accept pseudo-text, duplicated characters, malformed Chinese, or changed units.

## Generation order

1. lock content and evidence;
2. lock brand and layout;
3. run copyfit;
4. generate the slide;
5. inspect exact copy and factual assets at full resolution;
6. revise the smallest failing region;
7. approve only after content and visual gates pass.

## Deck assembly

Place each approved image edge-to-edge on its slide at the target aspect ratio. Keep citations, exact copy, evidence IDs, asset provenance, assumptions, and analyst judgment in speaker notes or an accompanying ledger. Render the exported PPTX itself for final QA.
