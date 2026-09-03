# QA and release gates

Inspect the exported deliverable, not only the prompt pack or in-memory composition.

## Hard gates

Delivery is blocked when any of these occur:

- a visible claim, number, date, quote, ranking, or named entity lacks evidence;
- a reported fact, derived calculation, user assertion, and analyst judgment are presented as the same evidence type;
- copy differs from the approved brief, including units, periods, punctuation, or qualifiers;
- a logo, product image, interface, report excerpt, or chart is distorted or fabricated;
- visible text contains pseudo-characters, malformed Chinese, duplicate text, or unreadably small type;
- content is clipped, overlapped, outside the canvas, or rendered at the wrong aspect ratio;
- a slide lacks a clear hierarchy or reading path;
- adjacent pages are visually inconsistent without narrative purpose;
- private content appears in a public artifact or repository;
- the PPTX cannot be reopened and rendered successfully.

## Visual review

Inspect every slide at full resolution for:

- first-glance message and dominant object;
- whitespace, alignment, margins, density, and balance;
- brand fidelity and cross-slide rhythm;
- semantic value of icons, diagrams, and decorative detail;
- evidence legibility at normal presentation distance;
- signs of generic AI styling or unnecessary complexity.

Reject pages that are merely attractive but do not communicate the intended decision message.

## Content review

Compare each slide against `deck-brief.json` and the evidence ledger. Confirm that every evidence ID resolves, source notes are present, assumptions remain labeled, and omitted topics have not reappeared through Image2 invention.

## Privacy and public release

Before public release:

1. run unit tests and Skill validation;
2. run `scripts/public_release_check.py` with a private external denylist;
3. inspect archives by extracting them into a fresh directory and rerunning the scan;
4. scan complete Git history;
5. confirm ownership, brand, license, and third-party-use approval.

Passing automated checks is necessary but not sufficient for public release.
