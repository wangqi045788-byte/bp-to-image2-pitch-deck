# Input contract

The workflow is intentionally tolerant of uneven inputs. A polished BP is optional.

## Required signal

The job needs:

1. a user prompt stating what the deck should achieve; and
2. at least one usable source of company or subject information.

Company information may be typed directly in the prompt or supplied as a document. Reference materials may include reports, spreadsheets, PDFs, notes, web pages, transcripts, or images.

## Optional inputs

- BP, teaser, memo, prior deck, or draft outline;
- logo, brand guide, official product image, interface screenshot, or report excerpt;
- visual references used only for composition, density, typography, or material cues;
- requested slide count, audience, language, aspect ratio, tone, and deadline.

## Normalized job brief

Before analysis, normalize the request into:

- `objective`: the decision or reaction the deck should produce;
- `audience`: investor, management, client, committee, partner, or general reader;
- `deliverable`: full pitch deck, management roadshow, product study, investment highlights, one-page study, or other named format;
- `language` and `aspect_ratio`;
- `requested_slide_count`: exact, range, or `auto`;
- `required_topics` and `forbidden_topics`;
- `source_inventory` with confidentiality labels;
- `reference_visual_policy`: imitate only permitted design traits, never copied protected content;
- `open_questions`, `assumptions`, and `missing_evidence`.

Do not pause merely because optional fields are absent. Ask only when a missing choice would materially alter the objective, audience, confidentiality boundary, or factual meaning.

## Sparse-input behavior

When information is limited:

- choose fewer, stronger slides;
- label user assertions separately from verified facts;
- use qualitative diagrams only when supported by the described mechanism;
- omit financial, market, traction, customer, team, or competition pages without evidence;
- record gaps in the evidence ledger, not as invented slide content.

## Source precedence

For factual conflicts, prefer in order: regulatory or audited disclosure; official company publication; user-designated source of truth; reputable third-party source; derived calculation; analyst judgment. Preserve disagreements instead of silently merging them.
