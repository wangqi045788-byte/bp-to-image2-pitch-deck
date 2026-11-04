# Page JSON schema

`build_deck.py` uses Python 3 and the packages in this Skill's own `requirements.txt`. Install them into the chosen environment with `python -m pip install -r <ppt-production>/requirements.txt`. Coordinates and dimensions use inches. The default widescreen canvas is 13.333 × 7.5 inches.

## Document

```json
{
  "title": "Decision review",
  "slide_size": [13.333, 7.5],
  "theme": {"font": "Aptos", "body_font": "Aptos", "background": "FFFFFF", "text": "20242A", "accent": "3567A8"},
  "slides": [{
    "title": "Decision in one sentence",
    "notes": "Source IDs, date, limitations, and the speaking detail.",
    "elements": [
      {"type": "text", "x": 0.8, "y": 0.7, "w": 11.7, "h": 0.8, "text": "Put the verified conclusion here.", "font_size": 30, "bold": true},
      {"type": "line", "x1": 0.8, "y1": 1.7, "x2": 12.5, "y2": 1.7, "color": "BAC2CE", "width": 1}
    ]
  }]
}
```

`title` and `slides` are required; `slide_size` and `theme` are optional. JSON text is content, not evidence. Preserve exact wording, dates, labels and units from the source ledger.

Each slide may have a title, notes, background and an ordered `elements` list. Later elements sit above earlier elements.

## Text

`{"type":"text","x":0.8,"y":0.7,"w":5,"h":1,"text":"A conclusion","font_size":26,"font":"Aptos Display","color":"20242A","bold":true,"italic":false,"align":"left","valign":"middle"}`

Text remains editable. Newlines create editable paragraphs. Use actual Unicode characters for bullets (`•`), symbols and diacritics. The converter does not edit or shrink copy to fit; adjust the planned text or box, then inspect the rendered slide.

## Shape and line

`{"type":"shape","shape":"rect","x":1,"y":2,"w":3,"h":1,"fill":"EAF0F8","line":"3567A8","line_width":1}`

Shapes are `rect`, `round_rect`, `ellipse`, `triangle` and `chevron`. Set `fill` or `line` to `"none"` to omit it.

`{"type":"line","x1":1,"y1":1,"x2":4,"y2":2,"color":"3567A8","width":1.5}`

## Picture

`{"type":"image","file":"assets/site.jpg","x":7.5,"y":1,"w":5,"h":5}`

Image bytes are embedded in the PPTX. Center cropping preserves the aspect ratio; it does not stretch a face or product. The file must be inside the JSON directory. Absolute paths, symbolic links and parent traversal are rejected.

## Native table

```json
{"type":"table","x":1,"y":2,"w":7,"h":2.5,"rows":[["Metric","FY2025"],["Revenue","14.7"],["Margin","11.1%"]],"header":true,"font_size":14,"header_fill":"202C3B"}
```

Each table is an editable PowerPoint table. Values may be text or finite numbers; blanks and zeroes remain distinct. Every row must have the same number of cells. Set `header:false` if the first row is data.

## Native chart

```json
{"type":"chart","chart":"column","x":1,"y":1.9,"w":7,"h":4,"title":"Units shipped (000s)","categories":["2023","2024","2025"],"series":[{"name":"Actual","values":[42,47,55]},{"name":"Plan","values":[40,50,60]}]}
```

Types: `bar` (horizontal clustered), `column` (vertical clustered), `line`, `pie` and `doughnut`. Multi-series arrays have one numeric value per category. Pie/doughnut accepts exactly one series of nonnegative values with a positive total. Choose and verify the chart's source range and label exact periods and units before building. The underlying source remains authoritative.

The builder does not accept explicit axis minimums/maximums; Office selects axis bounds automatically. Font names on text elements are written into the PowerPoint file as family names but are not checked or embedded. Verify that the font exists in the target presentation environment and inspect substituted text.

## Output protections

The converter checks required keys, finite values, table widths, chart dimensions, supported types, slide bounds and image paths. It writes the PPTX atomically and refuses to overwrite the source JSON or an existing PPTX without `--overwrite`.

`examples/generic-demo/deck.json` contains only synthetic illustrative numbers and names. It verifies conversion and object types; it is not a company case study or universal visual template.
