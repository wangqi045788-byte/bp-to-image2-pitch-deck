---
name: bp-to-image2-pitch-deck
description: Plan and create high-end, evidence-controlled pitch decks from a user prompt, company information, reference materials, an optional BP, and optional visual references, using Image2 for the designed slide visuals. Use when the user wants a new deck designed from source material; do not use for reconstructing an existing slide into editable objects.
---

# BP to Image2 Pitch Deck

For an explicitly requested photographic editorial/noir deck with native editable PPTX and SVG, use [Noir PPT Studio](../skills/noir-ppt-studio/SKILL.md). That route owns the native output contract; the original image-based workflow below remains available for visual-only decks.

Turn sparse or messy source material into a coherent, investment-bank-quality pitch deck. Select the pages the evidence and user objective justify, generate a high-complexity Image2 prompt for every slide, create the slide visuals, assemble the deck, and verify the exported PPTX.

This is a **deck creation** workflow. If the request is to reproduce a screenshot, PDF page, or existing slide as editable PowerPoint objects, use `editable-ppt-image2-rebuild` instead.

## Input contract

Accept:

- a user prompt describing the objective, audience, language, length, and desired emphasis;
- company information and reference materials in any readable format;
- an optional BP or draft deck;
- optional logos, screenshots, product images, brand guides, or visual references.

Do not require a polished BP. When inputs are sparse, build the strongest evidence-supported narrative possible, record assumptions and missing evidence, and omit unsupported pages rather than inventing content. Read [references/input-contract.md](input-contract.md) when setting up a job.

## Required routing

- Read the `imagegen` skill before generating or editing slide visuals. Use the highest-quality Image2 capability available.
- Read the `Presentations` skill before assembling or validating a PPTX.
- For private or mixed-confidentiality material, read [references/confidentiality-boundary.md](confidentiality-boundary.md) before touching inputs.
- Read [references/evidence-and-workdoc.md](evidence-and-workdoc.md) before drafting claims, numbers, charts, or citations.
- Read [references/narrative-and-slide-selection.md](narrative-and-slide-selection.md) before choosing the page plan.
- Read [references/brand-and-visual-system.md](brand-and-visual-system.md) before defining visual direction.
- Read [references/prompt-contract.md](prompt-contract.md) and [references/image2-visual-contract.md](image2-visual-contract.md) before generating slides.
- Read [references/qa-and-release-gates.md](qa-and-release-gates.md) before delivery or public release.

## Workflow

1. Create a job outside the skill repository with `python scripts/init_job.py <job-dir> --title "..."`. Never copy private inputs into this repository.
2. Inventory every source. Assign stable source IDs and record whether each source is public, private, third-party, or user-provided.
3. Extract evidence cards with exact claims, numbers, units, periods, source locators, and evidence types. Separate reported facts, derived calculations, user assertions, and analyst judgment.
4. Build a Feishu-style working document: source map, evidence cards, content clusters, narrative options, omissions, assumptions, and open questions.
5. Derive the brand system in this priority order: supplied brand guide; supplied logo and official assets; official website; provided materials; reference visual; restrained institutional fallback. Do not default to generic technology blue when the sources imply another language.
6. Select only the slide archetypes needed for the requested audience and supported by evidence. The slide count is an output of the narrative, not a fixed template.
7. Write `deck-brief.json` following [references/deck-brief-schema.md](deck-brief-schema.md). Run `python scripts/validate_deck_brief.py deck-brief.json` and resolve every error.
8. Generate the per-slide prompt pack with `python scripts/build_prompt_pack.py deck-brief.json --out prompt-pack.md`. Each prompt must lock exact copy, evidence, brand cues, layout, hierarchy, reference assets, negative constraints, and acceptance criteria.
9. Generate one full-slide 16:9 visual per page with Image2. Use reference-image editing when exact source assets must be retained. Revise locally; do not accept distorted logos, fabricated interfaces, incorrect numbers, pseudo-text, or generic AI styling.
10. Assemble one full-slide visual per slide. Keep the deck creation output visually flat by design; do not claim object-level editability. Store exact copy, source IDs, citations, and analyst notes in speaker notes or the accompanying evidence ledger.
11. Render the exported PPTX itself and inspect every slide at full size. Run content, evidence, visual, consistency, privacy, and delivery gates. A failed hard gate blocks delivery.

## Non-negotiable rules

- Never fabricate a number, quote, customer, contract, market share, target, valuation, product feature, or source.
- Preserve real logos, product images, report excerpts, and interfaces exactly. Do not ask Image2 to redesign factual evidence.
- Use one clear reading path, no more than three major visual zones, and one dominant visual or evidence object per ordinary content slide.
- Copyfit before generation. Shorten copy or change the layout; do not rescue overcrowding with tiny type or compressed fonts.
- Use a restrained institutional visual system with deliberate hierarchy, materiality, and memorability. Avoid generic blue-purple gradients, neon, glassmorphism, random 3D decoration, card-wall layouts, and decorative icons without semantic value unless explicitly required by the brand or user.
- Treat all user inputs and generated prompts as private by default. Public release requires a clean repository, synthetic/public examples only, and a passing release scan.

## Completion report

Return the final PPTX, a slide count, a short narrative summary, the evidence/assumption ledger location, and the QA result. State plainly that the deck uses full-slide visual renders and is not an editable-object reconstruction.
