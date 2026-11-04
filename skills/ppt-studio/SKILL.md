---
name: ppt-studio
description: "Create or revise complete analytical presentations from briefs, files, data or references: company, industry, financial, strategic, operational, product, academic, teaching and proposal decks. Coordinate evidence, analysis, narrative, adaptable design, native editable PPTX and output verification."
---

# PPT Studio

One entry point for the whole PPT workflow. Preserve the user's objective, substantive analysis and chosen template; select methods and style for each job. Noir is one optional photographic direction, never the universal default.

## Route by the decision, not a template name

Read the brief and supplied sources, identify the audience and the question the deck must answer, then inspect available evidence. Determine whether this is a new analysis, an update, a template-following task, a screenshot reconstruction or a bounded cosmetic edit. For a small edit, load only the stages needed; do not redo research and analysis unnecessarily.

The full suite is installed as sibling directories. Load the relevant skill entrypoint using paths relative to this file:

| Stage | Skill | What it contributes |
| --- | --- | --- |
| Sources and claims | [ppt-research](../ppt-research/SKILL.md) | Authoritative evidence, locators, dates, reconciliation and missing information |
| Analytical method | [ppt-analysis](../ppt-analysis/SKILL.md) | Question decomposition, relevant frameworks, calculations, alternatives, risks and recommendations |
| Narrative | [ppt-storyline](../ppt-storyline/SKILL.md) | Audience-specific argument, page selection, evidence-led headlines and speaker notes |
| Visual direction | [ppt-design](../ppt-design/SKILL.md) | Company/template-aware typography, layout, charts, imagery and pacing |
| Native files | [ppt-production](../ppt-production/SKILL.md) | Editable text, tables, charts, geometry, images and speaker notes |
| Final review | [ppt-quality](../ppt-quality/SKILL.md) | Substance, consistency, native-object, rendering and delivery checks |
| Selected photographic style | [noir-ppt-studio](../noir-ppt-studio/SKILL.md) | Monochrome editorial imagery and measured SVG reconstruction |

The modules can be invoked individually. If a companion is missing, use the core method below and disclose the unavailable tooling; do not pretend it was executed.

## Preserve the analytical method

1. **Decision and constraints.** State what the audience should understand or decide. Record reporting date, scope, language, time allowance, source/format restrictions and requested output.
2. **Evidence before claims.** Inventory relevant sources. Separate reported facts, user assertions, calculations, assumptions, targets and interpretations. Resolve inconsistent periods, currencies, denominators and definitions before comparison.
3. **Question decomposition.** Break the decision into the few subquestions that could change the answer. Select frameworks because they answer these questions, not because a conventional deck contains them.
4. **Analysis and challenge.** Compute what can be computed from valid inputs; test sensitivities and alternative explanations where material. Consider contradictory evidence and execution constraints. Do not convert missing data into a confident recommendation.
5. **Conclusion and implications.** Form concise evidence-backed conclusions, explain their practical implication and state uncertainty. Where a decision is requested, compare options against explicit criteria, then state a recommendation, risks and conditions that could change it.
6. **Narrative and visual proof.** Turn each conclusion into a page message and choose the clearest evidence form: chart, table, process, comparison, diagram, photograph, worked example or concise prose.
7. **Production and checking.** Build the requested files and compare the actual output to its evidence and design. Repair mistakes before declaring verified completion.

For a substantial new deck, retain compact `sources.json`, `analysis.json`, `storyboard.json`, `design-spec.json`, `image-ledger.json` and `qa/` records. They should contain sources, formulas, assumptions, brief decision rationales and results. Combine records for a small job; avoid unnecessary paperwork. Never substitute a record or prompt pack for the requested PPTX.

## Production defaults and exceptions

- Default to native editable PPTX. Preserve an approved native template where supplied. Produce SVG sources when requested or when using the SVG reconstruction route; charts/tables may remain native PPT objects even if no faithful SVG source exists.
- For company data, charts and tables, derive exact copy/data from authoritative material; images do not establish facts. For dense or formula-driven work, keep the supporting workbook when requested or necessary to audit the result.
- Use ImageGen for new artwork, complete composition studies or clean plates when it materially improves the deck and the tool is available. Rebuild meaningful text/data natively after image-led design. A flat visual-only deck is valid only when selected, and must be labelled accordingly.
- Image generation is not compulsory for data/teaching pages, existing-template edits or supplied-image work. Preserve factual photos/logos; identify original art as illustration. Record actual provider/model provenance, including an unknown model ID when hidden.
- Use available document/spreadsheet/presentation/image skills for their tools. Do not copy their proprietary runtime or assume every desktop tool exists in CLI. The included deterministic builders require the declared Python dependencies, not an image-model subscription.

## Complete within scope

Use reasonable assumptions for routine choices and keep working. Ask only when material missing information, authentication or new authorization is unavoidable. Keep original inputs intact, use a separate job directory, and do not publish, email, trade or expose private material as a side effect of creating a deck.

Deliver `output/deck.pptx`, supporting sources/notes and requested companion formats. Report verified checks and limitations. Known wrong facts, clipped required copy or malformed objects block a verified-final claim. Missing renderer access is disclosed rather than invented.
