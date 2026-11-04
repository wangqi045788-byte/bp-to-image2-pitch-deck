# Third-party notices

Review date: 2026-11-04.

## FigEdit SVG-to-PowerPoint converter

The vendored converter package under `svg_to_pptx/` is based on the converter bundled with FigEdit, reviewed from the local installed FigEdit snapshot on the date above. The local snapshot did not include a Git revision identifier. FigEdit is distributed under the MIT License, Copyright (c) 2025 Waka; the complete license text is in `LICENSE.figedit`.

This repository's copy has local portability changes: the package CLI is loaded lazily, and positional `<tspan>` support loads the FigEdit text-layout helper only when a `<tspan>` element is present. The Noir exporter emits plain single-line `<text>` and therefore uses the bundled package without that optional FigEdit helper.

## PPT Master

The native SVG-to-PowerPoint conversion layer in `svg_to_pptx/` includes work adapted from [PPT Master](https://github.com/hugohe3/ppt-master), created and maintained by Hugo He. FigEdit modifies and integrates that conversion work. Preserve the complete upstream MIT license at `svg_to_pptx/LICENSE.ppt-master` (Copyright (c) 2025-2026 Hugo He) when copying or distributing this code.

The bundled implementation may differ from both the reviewed FigEdit snapshot and current upstream PPT Master. No upstream Git commit was identified for the local FigEdit snapshot.
