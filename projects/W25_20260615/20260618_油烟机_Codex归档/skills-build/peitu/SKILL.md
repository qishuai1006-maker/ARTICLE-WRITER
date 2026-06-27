---
name: peitu
description: "Read an article and plan, generate, QA, and insert a fixed set of three images for Chinese home-appliance articles: one Toutiao-style cover image plus two in-article infographics. Use when the user asks for 配图, 封面图, 信息图, 出图, 把图片放进文案, 输出含图 Word, or visual assets for 今日头条/什么值得买家电选购、避坑、参数解释、型号对比、安装提醒、使用体验文章."
---

# 配图

## Core Rule

Generate exactly three article images unless the user explicitly requests a different count:

1. Cover image: attract clicks and communicate the article's main conflict or benefit.
2. Infographic 1: explain the first important parameter, structure, comparison, or concept.
3. Infographic 2: support final purchase decisions with a sequence, checklist, segment table, scenario match, or model comparison.

Do not generate decorative filler images. Every image must answer one reader question.

## Workflow

1. Read the full article before planning images. Identify the topic, article type, core conclusion, key paragraphs, product category, target account, and any existing image placeholders.
2. Create a three-image plan. Select the exact paragraph after which each body infographic should be inserted. Avoid putting both body images together.
3. Produce a complete prompt/spec for each image before generating it. For information graphics, list every required Chinese phrase, number, unit, and model exactly.
4. Generate the images:
   - Use image generation for photographic or editorial cover images when available.
   - Prefer deterministic HTML/SVG/canvas rendering for information graphics that contain Chinese, numbers, units, or model names. AI image models often corrupt text.
   - If the user insists on model-generated infographics, still provide exact text prompts and then manually QA every word.
5. Save outputs in the current project under `outputs/Codex/` unless the user gives another path. Use clear filenames such as `T5_cover_<topic>.png`, `T5_info1_<topic>.png`, `T5_info2_<topic>.png`.
6. Insert the three image references into the article at the chosen positions. If the user asks for Word, use the documents workflow after insertion and render-check the `.docx`.
7. QA all images and the final article layout. If any image has wrong text, wrong units, cropping, logo/watermark, or poor readability, regenerate or revise before final delivery.

For the full production standard, read `references/visual-standards.md`.

## Article Type Mapping

- 选购攻略: cover = "别只看某个参数"; infographic 1 = core parameter explanation; infographic 2 = decision path or scenario match.
- 参数解释: cover = parameter misconception; infographic 1 = principle diagram; infographic 2 = parameter-to-family-scenario match.
- 型号对比: cover = which model to choose; infographic 1 = configuration comparison table; infographic 2 = people/scenario recommendation.
- 避坑提醒: cover = biggest pitfall; infographic 1 = wrong vs right; infographic 2 = checklist.
- 安装教程: cover = most ignored installation issue; infographic 1 = position/size/structure diagram; infographic 2 = pre-install checklist.

## Prompt Requirements

Each image prompt/spec must include:

- Image type: cover image or in-article infographic.
- Ratio: 16:9 landscape.
- Theme and reader question answered by the image.
- Layout: close-up subject, left-right comparison, four cards, table, flow, structure diagram, etc.
- Required text: exact title, labels, numbers, units, model names, and short notes.
- Visual style: mobile-readable, clean hierarchy, safe central area, colors, typography.
- Banned elements: logo, QR code, watermark, price bait, promotional tags, exaggerated claims, unsupported "best/0-difference/first" wording.
- Text-accuracy rule: do not change units such as `m³/min`, `Pa`, `kW`, `Hz`, `nits`, `L`, `mm`, `kg`, or product model capitalization.

## Generation Guidance

Use a photographic cover when the article benefits from a real-life scene: kitchen smoke, TV glare, air-conditioner airflow, washer laundry room, refrigerator storage. Keep the product large and clear. Use little or no text when the generation tool cannot reliably render Chinese.

Use controlled information graphics for text-heavy visuals. Build them as HTML/SVG/canvas and render to PNG when possible. Keep tables to five rows or fewer and cards to three or four major points.

If using a generated image from a browser session, do not claim it is saved until the file exists on disk. If it only appears in chat, tell the user clearly and provide the prompt for manual download.

## Output Contract

When finished, report:

```markdown
## 配图完成
### 图 1：封面图
- 作用：
- 插入位置：
- 文件：
- 质检结果：

### 图 2：正文信息图 1
- 作用：
- 插入位置：
- 文件：
- 质检结果：

### 图 3：正文信息图 2
- 作用：
- 插入位置：
- 文件：
- 质检结果：
```

If a Word file is requested, include the final `.docx` path and mention that a rendered preview was checked.

## Useful Script

Use `scripts/plan_article_images.py` for a fast first-pass JSON plan from a Markdown article. Treat its output as a draft and refine it with judgment before generating images.
