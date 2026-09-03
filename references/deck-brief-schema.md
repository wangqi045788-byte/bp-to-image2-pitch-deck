# Deck brief schema

`deck-brief.json` is the contract between research, narrative planning, prompt generation, Image2, and QA.

## Top-level fields

- `schema_version`: currently `1.0`;
- `job`: title, mode, objective, audience, language, aspect ratio, and slide-count instruction;
- `inputs`: user prompt, company information, and source inventory;
- `brand`: brand evidence and visual system;
- `evidence_cards`: atomic claims;
- `narrative`: thesis, storyline, assumptions, omissions, and open questions;
- `slides`: ordered slide briefs.

## Minimal example

```json
{
  "schema_version": "1.0",
  "job": {
    "title": "Example company pitch",
    "mode": "private",
    "objective": "Explain why the product matters",
    "audience": "management",
    "language": "zh-CN",
    "aspect_ratio": "16:9",
    "requested_slide_count": "auto"
  },
  "inputs": {
    "user_prompt": "Build a concise product pitch",
    "company": {"name": "Example Company", "one_liner": "A synthetic example"},
    "sources": [
      {"id": "S01", "kind": "company_info", "label": "synthetic", "title": "Synthetic company note", "locator": "inline"}
    ]
  },
  "brand": {
    "basis": ["S01"],
    "primary_colors": ["#17324D"],
    "accent_colors": ["#E6B34A"],
    "background_colors": ["#F7F5F0"],
    "text_colors": ["#14212B"],
    "typography": "normal-width sans-serif",
    "shape_language": "precise lines, restrained radii",
    "image_direction": "editorial product realism",
    "logo_policy": "preserve supplied logo exactly",
    "forbidden_motifs": ["generic blue-purple neon", "decorative card wall"]
  },
  "evidence_cards": [
    {"id": "E01", "claim": "Synthetic workflow reduces a four-step handoff to two steps", "evidence_type": "user_assertion", "source_id": "S01", "locator": "paragraph 2", "confidence": "medium", "public_safe": true}
  ],
  "narrative": {
    "thesis": "A shorter workflow improves decision speed",
    "storyline": ["Current friction", "New mechanism", "Expected operating effect"],
    "assumptions": [],
    "omissions": ["No financial claims supplied"],
    "open_questions": []
  },
  "slides": []
}
```

## Slide fields

Each slide requires:

- `number`, `title`, `archetype`, `purpose`, and `key_message`;
- `content`: ordered visible items with `type`, `text`, and `evidence_ids`;
- `visual`: layout, reading path, dominant object, zone count, mechanism, and reference asset IDs;
- `copyfit`: title and body budgets plus metric count;
- `source_note_evidence_ids`;
- `image2`: optional page-specific direction and negative constraints.

Use `scripts/validate_deck_brief.py` as the executable specification.
