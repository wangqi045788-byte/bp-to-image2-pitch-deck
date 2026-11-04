# Presentation analysis plan

Use this lightweight record when an analysis spans multiple pages, includes material calculations, or will be handed to another author. It is not a slide template and need not be created for a simple reformat.

```json
{
  "decision_question": "question the presentation must answer",
  "audience": "decision maker or learner",
  "decision": "action or understanding sought",
  "scope": {
    "subject": "company, market, policy, project, topic...",
    "geography": "region or population",
    "as_of": "YYYY-MM-DD or period end",
    "measure_basis": "accounting, market, population or process definition"
  },
  "evidence": {
    "sources": [{"id":"S01", "title":"...", "publisher":"...", "date":"...", "locator":"...", "url_or_path":"..."}],
    "claims": [{"id":"E01", "statement":"...", "status":"reported_fact", "source_ids":["S01"], "period":"...", "unit":"...", "denominator":"...", "calculation":"...", "caveat":"..."}]
  },
  "analysis": {
    "primary_lens":"...",
    "rationale":"how it answers the question",
    "calculations":[{"metric":"...", "formula":"...", "input_claim_ids":["E01"], "result":"..."}],
    "alternatives":[{"lens":"...", "rationale":"brief criterion-based reason"}],
    "findings":[{"claim":"...", "evidence_ids":["E01"], "implication":"..."}],
    "counterevidence":[{"point":"...", "evidence_ids":[], "effect":"..."}],
    "uncertainty":[{"issue":"...", "impact":"...", "what_would_resolve_it":"..."}],
    "recommendation":"..."
  },
  "storyboard":[{"id":"S1", "message":"one supported page conclusion", "evidence_ids":["E01"], "visual":"...", "notes":"..."}]
}
```

This aligns with the suite `analysis.json` and its `storyboard.json` page records `{id, message, evidence_ids, visual, notes}`. Keep the real workspace sources and QA beside them. Use only relevant fields. A qualitative analysis can omit numerical details; a financial analysis needs enough detail to reproduce important figures. Claim states: `reported_fact`, `user_assertion`, `calculated`, `estimate_or_forecast`, `interpretation`, `unverified`.

## Mini example (fictional)

Question: Why did renewal revenue fall in the latest quarter?

- Lens: cohort/segment bridge by renewal month and plan, because aggregate growth alone cannot separate churn from mix or timing.
- Evidence: reported renewal revenue by month, opening eligible contracts, renewal rate, plan mix and price change. Each metric has period, denominator and source ID.
- Finding: total renewed value fell; most measured difference comes from a smaller renewal-eligible base. No source establishes whether customer dissatisfaction drove the change.
- Counterevidence: a subset has higher retention but small sample size; show cohort sizes.
- Slide sequence: executive answer → bridge by eligible base/rate/mix → cohort evidence and sample → limits and next investigation.
- Title discipline: “A smaller renewal-eligible base drove most of the quarter decline” only if the reproduced bridge supports it. Put unresolved churn cause in notes or a clearly labelled open question.
