# 配图视觉标准

## Fixed Image Set

Produce exactly three images:

1. Cover image: placed near the title or opening. It improves click-through and communicates the main conflict or benefit.
2. Infographic 1: placed after the first core explanation. It explains the most important parameter, structure, comparison, or misconception.
3. Infographic 2: placed in the middle-late article before the recommendation, summary, or conclusion. It helps the reader decide what to buy or check.

## Cover Standard

Use a 16:9 landscape image suitable for Toutiao mobile feed thumbnails.

Prefer:
- Large clear appliance subject.
- Big visual conflict or reader benefit.
- Central 60% safe area for the key subject or optional short text.
- Realistic editorial photography for scene-led covers.
- Low information density.

Common structures:
- Single category close-up.
- Left/right contrast.
- Parameter misconception.
- Pain-point scene: smoke backflow, TV glare, refrigerator odor, AC direct blowing, washer drying problems.

Ban:
- Brand logo, price, QR code, watermark, product-link UI, promotional sticker.
- Long text blocks.
- Absolute claims such as 最好, 闭眼入, 0差评, 第一, 全网最低.
- Fake exaggerated effects.
- E-commerce poster style.

## Infographic Standard

Use a 16:9 landscape image. Make it a professional content graphic, not a cover poster.

Each infographic must express one relationship only:
- Parameter explanation.
- Structure breakdown.
- Technical route comparison.
- Core decision standard.
- Misconception correction.
- Working principle.
- Scenario fit.

Do not cram the whole article into one image. Keep hierarchy:

`title > key number/keyword > short explanation`

Recommended layouts:
- Four cards.
- Three cards.
- Left/right comparison.
- Horizontal flow.
- Simple table.
- Center structure diagram.
- Title on top, content area below.

Card rules:
- Radius no more than 8px.
- Enough spacing.
- One core point per card.
- Text never touches edges or overlaps.

Table rules:
- Clear header.
- Enough row height.
- Reasonable column width.
- No more than five core rows.
- Avoid Excel-screenshot appearance.

## Text And Unit Standard

Chinese must be readable on a phone.

Use short titles, ideally no more than two lines. Keep each note around 20 Chinese characters when possible.

Preserve article numbers, units, and model names exactly:
- Do not write `m³/min` as `m3/min`.
- Do not corrupt `Pa`, `kW`, `mm`, `L`, `Hz`, `nits`, `W`, `kg`.
- Do not change model capitalization, spaces, slashes, or hyphens.
- Do not invent missing parameters. If information is uncertain, omit it or mark "待确认" only when useful.

## Color And Style

Default palette:
- Background: off-white, light gray, or pale blue-gray.
- Main title: dark navy, dark gray, or black.
- Key numbers: orange, warm red-orange.
- Correct direction: teal or blue-green.
- Wrong direction: red or gray strikethrough.
- Lines: light gray or pale blue-gray.

Avoid:
- Fully saturated red/green fields.
- Neon/nightclub style.
- Heavy gradients.
- Complex texture behind text.
- Overdecorated poster effects.

## Insertion Rules

Insert images like:

```markdown
![封面图](image-path)

![正文配图1：主题](image-path)

![正文配图2：主题](image-path)
```

Placement:
- Cover: article start.
- Infographic 1: after the first core parameter/concept/comparison explanation.
- Infographic 2: before middle-late recommendation, model list, checklist, or conclusion.

Avoid:
- Opening fluff.
- Pure emotion paragraphs.
- Very short paragraph gaps.
- Consecutive body images.
- Final sentence after the whole article.

## QA Checklist

Quantity:
- Exactly three images.
- One cover plus two infographics.

Position:
- Cover at the start.
- Infographic 1 after first core explanation.
- Infographic 2 near decision section.
- No image pile-up.

Content:
- One core relationship per image.
- Matches surrounding paragraph.
- No repeated image meaning.
- No new unsupported brand, model, parameter, or conclusion.

Text:
- Chinese readable.
- No typo.
- Numbers correct.
- Units correct.
- Model names correct.
- No required item omitted.

Compliance:
- No logo, QR code, watermark, price bait, promotional tag.
- No absolute words: 最好, 0差评, 闭眼入, 第一, 全网最低.

Visual:
- Mobile-readable.
- Not too dense.
- Clear focus.
- Safe central area.
- No overlapping text.
- No cropped table/card content.

If any item fails, revise the prompt/spec and regenerate or repair the image.
