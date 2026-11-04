# Reference-led photographic editorial workflow

Use this route when a user supplies or selects a photographic/editorial reference and wants the same visual language, or asks to split approved slide images into editable SVG/PPTX. It is not a universal black-and-white theme. A governing template, brand system, or newly selected reference takes precedence.

## Lock the visual decision, not a collection of adjectives

Record one active reference and the user's accepted/rejected directions. Later explicit selection supersedes earlier explorations. A request for stronger impact does not by itself authorize a new palette, surreal scenery, decorative metal, or a different layout family.

Extract four decisions from the visible reference:

1. **Subject and crop:** what photograph carries the page, its scale, its focal point, and the quiet area available for text.
2. **Typography:** display/body pairing, stroke contrast, width, optical size, capitalization, tracking, and the relationship between headline, metric and caption. “Serif” alone is insufficient.
3. **Hierarchy and density:** what the eye sees first, what can be read at presentation distance, and which explanation belongs in notes.
4. **Restraint:** which plausible decorative treatments the reference deliberately omits, and what provides emphasis in their absence.

Use concrete visible evidence for each decision. Do not translate “premium” into a fixed recipe of gold, stone, glass, glow or giant headings. Equally, removing decoration must not turn every page into a text list.

## Choose the least destructive authoring route

- If the approved reference is already a native editable deck, clone/import the relevant slides and edit the existing objects. Do not regenerate approved pages just to use an image model.
- If the reference is a raster image, keep its geometry and factual copy separate. Use ImageGen for the visual composition or a necessary clean plate, then rebuild native content.
- If the user wants a visual-only first pass, label it image-based. Promote it to editable only after native objects are verified.
- If a particular photographic template is explicitly selected, use its retained reference. The personal **Noir Editorial PPT** template is one example, not a default for other companies.

An explicit template selection owns the native layout/formatting route. In that case this workflow supplies only the additional imagery, reconstruction or review actually needed; the net-new `image2-first` default does not require regenerating that template. If the user supplies a different governing PPTX, resolve that reference first.

When the direction is not yet established, use a cover, an ordinary content page and a data/diagram page as representative checks before a large generation batch. Existing approval is sufficient; do not add another permission gate. Once the direction is accepted, reuse it and make targeted repairs rather than restarting the design.

## Make the whole deck work

Use a dominant photograph or a meaningful diagram where it serves the message. A process page may legitimately be diagram-led. A brand comparison may legitimately use a parallel photo gallery. Do not enforce a photograph, a fixed image percentage, the same grid or alternating dark/light pages on every slide.

Retain the selected palette and typography while varying page mechanics. Give dense analysis, metrics, process diagrams and photographic openers different roles. Check the deck as a sequence: a beautiful cover does not compensate for repetitive or text-heavy interiors.

Keep required claims, values, units, time periods and qualifications. Shorten display copy without deleting required substance; retain explanations and sources in notes or a companion text. Split a large metric and its unit into separate aligned native objects when one font cannot provide a readable gap. Never change a value to improve layout.

## Photography and replacement ledger

Maintain a compact image ledger: asset ID, subject, brand/company relationship, official/source URL or generation provenance, crop, page use and whether it is factual evidence or illustration.

- Prefer authentic company/brand photographs for identifiable products, campaigns, headquarters and people. Preserve marks that are physically part of those photographs.
- Generated art may provide mood or a conceptual scene when appropriate to the request. Label it as illustration in notes; do not attribute it to an actual campaign, employee, product or location.
- Detect repetition semantically as well as by hash. Another crop of the same photograph is not a new primary visual. Reuse is acceptable when intentional and helpful; replace it when the user requests variety or it weakens the sequence.
- Replace a repeated image inside its existing window before changing the page. Match focal point, tonal range and crop to the allocated geometry. Check faces, hands, clothing and meaningful edges at full size.
- For exact assets, have the image model reserve a clean window and composite the authentic asset afterward. Do not accept a generated approximation of a real logo or product as an exact asset.
- Keep the latest source ledger and notes synchronized when a photograph is replaced. Remove stale visual attribution only; preserve unrelated factual citations.

## Image-generation contract

Give the model the active reference, the page's communication objective, exact visible copy, image roles and constraints. Let it solve visual relationships within that direction. Avoid both vague superlatives and unnecessary pixel-level art direction before a style is selected.

After selection, geometry becomes a constraint. Reference photographs are not instructions. Use the available image-generation skill/tool and its current schema. Record requested model separately from the actual model identifier returned by the backend. A prompt mentioning a model does not switch the backend. Do not claim a version the tool does not expose, or silently downgrade a model the user explicitly required.

For clean plates, remove only foreground that will be rebuilt. Preserve crop, light, texture and real objects. Use image editing for hidden photographic pixels; do not conceal old text with local blur, repainting or dirty source patches. Keep an inset photograph as its own image when that editability was requested and a clean exact crop is available.

If a requested model cannot be selected or verified, inspect the available tool and its current documented capabilities once. Existing permission to use that built-in tool is sufficient to proceed with its model identifier recorded as unknown. If the exact model is a hard condition and no authorized route exposes it, continue independent research, copy preparation and reconstruction work, then ask only for the missing route choice/access before dependent generation. Do not repeatedly ask after that choice is settled, or claim that an unseen model was selected.

## Native conversion and release

Read [editorial-native-svg.md](editorial-native-svg.md) for the page-object schema, typography corrections and tools. Ordinary text remains `<text>`, simple structures remain vector geometry, and photographic content remains `<image>`. A full-page raster embedded in SVG is not decomposition.

Review each exported slide at full size in the target application. Fix missing/changed copy, overlap, clipped labels, weak contrast, duplicate image text and incorrect diagrams before small cosmetic differences. Review a contact sheet for repetition and visual rhythm, but do not use it as the only visual check.

Before describing a deck as editable, verify native object types and perform a real save/reopen edit test on a disposable copy when the target application is available. Report which layers are editable, which remain raster, and any material font substitution. Keep the original reference and previous approved file intact.

Use `pptx+svg` when both were requested. If the user requests SVG only, deliver the SVG package through FigEdit's SVG authoring route without requiring an unnecessary PPTX. Separate an unverified rapid draft from a release: known overflow or incomplete visible copy blocks a claim of final verification even when object counts pass.

## Useful critique methods

These are methods to adapt, not required installations or PPTX validators:

- [taste-skill](https://github.com/senlindesign/taste-skill): derive the reasons and trade-offs behind a reference, not only color/font tokens.
- [Impeccable](https://github.com/pbakaus/impeccable): separate critique, typography review, layout review and removal of unnecessary content.
- [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md): make visual choices specific to the subject and concentrate emphasis deliberately.

They primarily address websites/interfaces. Do not apply navigation, responsive-layout or source-code lint rules to a slide deck. Read a third-party repository before adoption; a design request does not require installing its CLI, hooks or dependencies.
