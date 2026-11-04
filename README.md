# PPT Studio — Analysis to Editable Presentations

[完整中文说明](README.zh-CN.md) · [Main Skill](skills/ppt-studio/SKILL.md) · [Analytical Method](skills/ppt-analysis/SKILL.md)

A complete Codex Skill suite for researching, analyzing, structuring, designing, producing and checking presentations. It supports company, industry, financial, strategic, operational, product, academic, teaching, proposal, project and policy work. Choose a suitable method and visual system for the actual question; do not force every deck into Noir or a stock pitch template.

## What is preserved

The reusable method is **decision question → evidence → normalized calculations → relevant analytical framework → supported conclusion and counterevidence → audience-led narrative → visual proof → native output → review**. Sources, formulas, assumptions and concise decision rationales remain auditable. Design is one part of the workflow, not a replacement for analysis.

| Skill | Role |
| --- | --- |
| [ppt-studio](skills/ppt-studio/SKILL.md) | One entry point coordinating the full task |
| [ppt-research](skills/ppt-research/SKILL.md) | Source discovery, factual checks and claim provenance |
| [ppt-analysis](skills/ppt-analysis/SKILL.md) | Decision decomposition, appropriate frameworks, calculations and alternatives |
| [ppt-storyline](skills/ppt-storyline/SKILL.md) | Evidence-led narrative, slide messages and speaker notes |
| [ppt-design](skills/ppt-design/SKILL.md) | Audience/brand-specific layouts, typography, diagrams and imagery |
| [ppt-production](skills/ppt-production/SKILL.md) | Native editable text, tables, charts, geometry, photos and notes |
| [ppt-quality](skills/ppt-quality/SKILL.md) | Content, numbers, native semantics and rendered-slide review |
| [noir-ppt-studio](skills/noir-ppt-studio/SKILL.md) | Optional monochrome photographic style and SVG reconstruction |

## Install and invoke

Requires Python 3.10+ and an available Codex environment. From this repository:

```bash
python -m pip install -r requirements-ppt.txt
python tools/ppt.py install
```

Then ask Codex:

```text
Use $ppt-studio to turn these materials into an editable presentation.
Determine the relevant analytical method, verify the facts, develop the argument,
choose a suitable style, and deliver the PPTX with sources, notes and QA results.
```

Windows: double-click `install-ppt.cmd` once, then drag your brief onto `start-ppt.cmd`. The dependency installation above is an explicit first-time setup step; the launcher does not silently install packages.

```bash
python tools/ppt.py generate --brief my-brief.md --job ../my-deck --assets my-materials
```

`--assets` is optional. Both type and style default to `auto`; optional `--type` and `--style` accept a specific direction. A supplied reference/template takes priority. Use `PPT_REQUEST.md` as a brief template. `--dry-run` prepares inputs without calling Codex.

## Real production paths

- Build ordinary analytical slides with native PowerPoint text, tables and chart data using the bundled general builder.
- Reuse an approved native template for updates and company house-style work.
- Use ImageGen for artwork, composition studies or clean plates when available and appropriate; reconstruct meaningful text/data natively.
- Use the bundled source-coordinate SVG adapter for photographic or screenshot reconstruction. Keep photos as independent image objects.
- Render and inspect the actual exported deck. Structural success alone is not visual acceptance.

```bash
python tools/ppt.py demo --out ../ppt-demo
```

The model-free synthetic demo exercises native production; it is not proof that every possible generative presentation type has been benchmarked. The corresponding [production Skill](skills/ppt-production/SKILL.md) describes supported object types and limitations.

## Runtime and privacy boundaries

The agent-driven creation route uses the tools and account available in the user's Codex session. CLI and desktop may expose different image or rendering capabilities. No image model, inference quota, API key or guarantee of an unseen backend model is bundled. Record the actual tool/model ID, or unknown when hidden.

The launcher keeps jobs outside the repository, copies only explicitly supplied assets, preserves existing outputs and does not bypass sandbox protections. No uploading to GitHub, messaging, financial transactions or account changes are part of making a presentation.

The public package excludes private company decks, brand campaign photographs, source research and speaker notes. Code is MIT; bundled FigEdit/PPT Master notices and the optional font's OFL license are retained. User inputs and outputs do not inherit the code license.

## Verification and packaging

```bash
python -m unittest discover -s tests -v
python scripts/public_release_check.py . --skip-history
python tools/build_ppt_package.py --out ../PPT_Studio_Full_Skills.zip
```

Real PowerPoint integration is opt-in on an appropriate Windows machine. Always report unexecuted checks rather than marking them passed. GitHub CI checks the deterministic code paths and synthetic examples, not artistic quality or live image generation.

The original evidence/prompt-generation helpers and [visual-only Image2 workflow](references/legacy-image2-workflow.md) remain available for explicitly selected flat-image decks. The old [Noir guide](NOIR_STUDIO.md) now describes an optional style route. The full-suite default is `$ppt-studio` with editable output.
