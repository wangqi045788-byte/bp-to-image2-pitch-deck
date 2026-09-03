# Evidence and Feishu-style work document

The work document is the reasoning layer between raw sources and slide design. It should be easy to audit before any Image2 generation begins.

## Required sections

1. **Decision objective** — audience, desired reaction, and constraints.
2. **Source map** — stable source ID, title, date, locator, provenance, confidentiality, and usage rights.
3. **Evidence cards** — atomic claims with exact wording, units, periods, and locators.
4. **Content clusters** — company, problem, product, technology, market, business model, traction, competition, team, financials, transaction, risks.
5. **Narrative options** — alternative storylines and why one was selected.
6. **Slide map** — purpose, key message, evidence IDs, and intended visual mechanism for every page.
7. **Assumptions and omissions** — what is inferred, missing, excluded, or awaiting confirmation.

## Evidence-card fields

- `id`: stable identifier such as `E01`;
- `claim`: exact claim suitable for reuse;
- `evidence_type`: `reported`, `derived`, `user_assertion`, or `analyst_judgment`;
- `source_id` and `locator`;
- `period`, `unit`, and `currency` when relevant;
- `confidence`: `high`, `medium`, or `low`;
- `public_safe`: whether the claim may appear in a public example;
- `notes`: methodology, caveat, or reconciliation.

## Claim rules

- Every visible number, date, ranking, percentage, named customer, quote, and factual comparison must resolve to at least one evidence card.
- Derived numbers must record the formula and source inputs.
- Analyst judgment must be written as interpretation, not company guidance or reported fact.
- Never round away a change in meaning. Preserve currency, period, denominator, and measurement basis.
- Do not turn a roadmap into a current capability, a target into an achieved result, or a third-party estimate into company disclosure.

## Slide-source notes

Each slide brief lists the evidence IDs used. The final deck should retain these IDs and full citations in speaker notes or an accompanying ledger even when citations are not prominent on the visible canvas.
