# 冰箱稿封面 Prompt（按 CEO 4层结构标准重写版）

> **执行**：ZCode · 2026-06-18
> **标准来源**：CEO 设计的 `assets/image_prompts/方法论_Super_Writer提示词工程.md`（4层结构 + 头条4硬约束）
> **替换**：本版替换 `04_视觉指挥官配图_冰箱.md` 里 ZCode 之前自创的非标准版 Prompt

---

## 文章核心矛盾（Prompt 扣题依据）

买海尔冰箱被"双循环"忽悠，以为是双系统不串味，其实差一整套蒸发器。
→ 封面走方法论"观点输出/拆解面 → **强对比构图**"路线。

---

## 标准 Prompt（英文 · GPT-4o 用）

```
[Layer 1 - Subject]
A split-screen composition of an open refrigerator interior.
Left half shows the fresh-food compartment with a spiky yellow
durian fruit sitting on the shelf. Right half shows the freezer
compartment with white dumplings on a plate. A hard glowing
diagonal split line cuts through the middle, separating the two
sides. The fridge body fills 60% of the frame.

[Layer 2 - Action]
Static product display, no human action. The durian aroma is
visually suggested as faint misty wisps drifting toward the
split line on the left side, blocked by it — implying the odor
cannot cross to the dumplings. Still life, slight three-quarter
angle revealing both the open doors and interior shelves.

[Layer 3 - Environment]
A softly blurred real home kitchen in the background, daytime,
natural window light from the left casting gentle shadows.
Neutral warm interior lighting. The fridge is the only sharp
subject; kitchen cabinets and countertop are out of focus.
Clean, lived-in domestic atmosphere, not a showroom.

[Layer 4 - Style]
Commercial editorial product photography, photorealistic,
documentary aesthetic. Shot on 50mm lens, f/2.8 shallow depth
of field. Neutral color grading with three dominant tones:
stainless-steel silver-white of the fridge, warm yellow of the
durian, and a cool blue-cyan glow on the diagonal split line.
Crisp details on fruit texture and dumpling surfaces.

[Negative Prompt]
no text, no watermark, no logo, no caption, no Chinese
characters, no English letters, no people, no faces, no hands,
no body parts, no 3D render plastic look, no e-commerce
studio flat lighting, no blue frost特效, no AI glow halo,
no multiple fridges lined up, no complex technical cutaway
diagram, no cluttered background
```

`--ar 16:9`（MJ）/ `aspect_ratio: "16:9"`（其他工具）

---

## 自检（方法论 6 问）

| # | 问题 | 本 Prompt |
|---|---|---|
| 1 | 有无文字水印？ | ✅ 无（负面提示词已禁 text/watermark/logo/caption/中英文） |
| 2 | 有无人脸？ | ✅ 无（负面提示词已禁 people/faces/hands） |
| 3 | 主体是否清晰？ | ✅ 开门冰箱+榴莲+饺子+分割线，一眼看出"气味能否互通"的悬念 |
| 4 | 色调是否一致？ | ✅ 三主色：不锈钢银白 / 榴莲暖黄 / 分割线冷蓝（与信息图色调统一） |
| 5 | 比例是否合规？ | ✅ 16:9 |
| 6 | 是否扣题？ | ✅ 双系统vs单系统的"一整套蒸发器之差"= 分割线隔不隔得住气味 |

---

## 各工具适配（来自方法论）

- **GPT-4o**：直接用上面英文版（GPT-4o 必须英文，中等长度 100-200 字最佳）
- **Midjourney**：末尾加 `--ar 16:9 --style raw --v 6`，无需负面提示词
- **即梦/通义万相**：可翻成中文版，100-200 字短描述，无需负面提示词
- **ComfyUI (FLUX/SDXL)**：用完整 4 层 + 负面提示词 + 技术参数

---

## 落盘命名

生成后保存为：`outputs/zcode/T5_ChatGPT_封面.png`
（文件名对得上 `build_article_docx.py` 的 `--cover` 约定，可直接嵌进 Word）
