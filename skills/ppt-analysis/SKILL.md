---
name: ppt-analysis
description: "Choose, structure and check evidence-backed analysis for company, industry, finance, investment, strategy, operations, product, academic, project or policy presentations. Use when slides need reasoning, source control, or recommendations grounded in evidence."
---

# Presentation Analysis

Turn a presentation request into a justified analysis. Preserve the distinction between evidence, calculation and judgment. Give the user a concise explanation of the selected method, key findings, caveats and implications, with a traceable evidence plan; do not expose private chain-of-thought.

## Analysis sequence

1. Define the audience, decision or learning goal, time horizon, geography, unit, comparison baseline and requested deliverable. Reuse information already supplied; ask only when a material ambiguity changes the answer.
2. Inventory evidence and decide what can be answered. With current or high-consequence facts, use `ppt-research` or its documented process. Mark private versus public material and keep private source files in the task workspace.
3. Select an analytical lens because it answers the question. Compare plausible alternatives briefly; do not insert a stock framework merely because it is familiar.
4. Normalize measures, dates, populations, periods, denominators and definitions before comparing. Show calculations and assumptions. Keep forecast, scenario and historical values distinct.
5. Build the strongest supported explanation and check contrary evidence, alternative causes, limitations, decision risks and what evidence could change the conclusion.
6. Summarize the answer in a compact analysis plan; pass supported findings to `ppt-storyline` to form the slide sequence. Link each numeric or material factual claim to its source/evidence ID.

Read [framework-router.md](references/framework-router.md) when selecting an analysis method. Use [analysis-plan.md](references/analysis-plan.md) to structure analysis that spans several pages or has important assumptions. For a single straightforward slide, this structure may stay brief.

## Route by the user's question

Use the relevant lane or combine lanes only when the question needs them:

- Company or business profile; industry or market structure; competitor comparison.
- Financial performance, driver analysis, unit economics, forecasts, investment case, valuation or transaction rationale.
- Strategic choices, operating model, supply chain, process, capacity, service or risk.
- Product, customer experience, growth funnel, experiment or data analysis.
- Academic topic, literature synthesis, teaching or curriculum.
- Proposal, pitch, grant, policy or nonprofit decision.
- Project, programme, business review or status update.

The brief controls the lens. Porter, SWOT, PESTEL, stakeholder matrices, market sizing, cohort analysis, valuation, root-cause tools and other methods are options; none is required in every deck. Use qualitative narrative when the source does not support fake precision.

## Evidence rules

- Label claims as reported fact, user-provided assertion, calculated value, estimate/forecast, or interpretation. Never upgrade one category into another.
- Maintain periods, currency, units, basis, denominator and comparison population from source to calculation to displayed slide. State changed definitions and non-comparable periods.
- Every recommendation must trace to evidence, a stated objective and relevant uncertainty. Include material counterevidence and implementation consequences.
- Use ranges, sensitivities and scenarios when assumptions dominate a result; show which input drives the decision.
- Separate management targets from actual results, company guidance from third-party forecasts, correlation from causation, and planned work from delivered outcomes.
- Do not invent users, customers, market size, citations, quotations, investment returns, academic consensus or project progress to complete a slide.
- Keep named theories and frameworks proportionate to the decision. If a framework's input evidence is absent, leave that element open or use a narrower analysis.

## Handoff

Provide only decision-relevant analytical outputs: question, selected lens and reason, supported conclusion, evidence IDs, calculations, competing explanation/risks, caveats and unresolved items. Pass a page-worthy finding to `ppt-storyline` with the claim, its evidence, why it matters and possible visual expression. Leave design choices to the chosen presentation style; Noir is optional and belongs to `noir-ppt-studio`.

This skill works alone. When the suite is installed, use `ppt-research` for source work and `ppt-storyline` for page sequence. For the final artifact, the `ppt-studio` skill routes to production and visual QA.
