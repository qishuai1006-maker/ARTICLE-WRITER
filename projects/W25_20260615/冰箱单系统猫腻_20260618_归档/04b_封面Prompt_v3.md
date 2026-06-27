# 冰箱稿封面 Prompt v3（实物唯美 + 点睛文案版）

> **执行**：ZCode · 2026-06-18
> **路线**：实物产品图 + 舒服排版布局 + 少量点睛中文文案（对标题的补充）
> **修正历史**：v1自创8段式(错) → v2纯对比无文字(生出来像电商图) → 本版v3

---

## 文章信息（Prompt 设计依据）
- 标题：《海尔冰箱型号暗藏猫腻，给爸妈买认准这3招，别花冤枉钱》
- 核心认知差：用户以为"双循环=双系统=不串味"，实际可能只有一套蒸发器照样串味
- 封面任务：补标题没说的——"双循环≠双系统"这个认知差
- 禁止：大红叉/红圈/惊叹号符号（曾限流）、标题复述、堆砌文字、爆料涂鸦感、AI塑料特效

---

## 标准 Prompt（英文 · GPT-4o 用）

```
[Layer 1 - Subject]
A premium double-door refrigerator, doors open, standing in a
bright modern kitchen. The interior is neatly organized with a
modest amount of fresh food — green leafy vegetables in crispers,
a few fruits, clean glass shelves. The fridge looks high-end and
appealing, the kind a family would be proud to own. The scene
feels like a real home, warm and aspirational.

[Layer 2 - Composition]
The refrigerator is positioned slightly left of center, its open
doors revealing the tidy interior. On the right side of the image
there is clean negative space — like an empty wall or soft blurred
kitchen background — reserved for a short text label. The framing
is balanced and calm, like a home-lifestyle magazine cover, not
crowded or cluttered. Generous breathing room around the subject.

[Layer 3 - Environment]
Bright daytime kitchen, soft natural light streaming from a window
on the left, casting gentle warm highlights on the fridge's
stainless-steel surface. Clean marble or light-wood countertop.
A few subtle home touches in the deep background (a plant, a
fruit bowl) softly out of focus. Atmosphere is peaceful, inviting,
trustworthy — the feeling of a well-kept family home.

[Layer 4 - Style]
High-end editorial product photography, photorealistic, natural
and comfortable aesthetic. Shot on 50mm lens, f/4 for gentle
depth of field. Clean color grading: warm whites, soft natural
greens from the food, brushed steel tones. The image should look
polished and pleasing to the eye — comfortable layout, not
artificial, not over-stylized, not plastic 3D render.

[Text Overlay - exact, render verbatim]
Place a short Chinese label in the clean negative space on the
right side, using an elegant minimal sans-serif Chinese font,
medium size, dark charcoal color (#333333), left-aligned:
双循环 ≠ 双系统
Below this main text, in smaller lighter gray font, one line:
差了一整套蒸发器

[Negative Prompt]
no red crosses, no red circles, no exclamation marks, no warning
symbols, no hand-drawn graffiti, no big bold alarm-style text,
no watermark, no brand logo, no English caption, no cluttered
food explosion, no messy overstuffed fridge, no 3D plastic look,
no AI glow halo, no blue frost effects, no科幻特效, no people,
no faces, no hands
```

`--ar 16:9`（MJ）/ `aspect_ratio: "16:9"`

---

## 设计说明（为什么这么排）

**画面**：高端双门冰箱开门 + 少量精致食材 + 明亮厨房。这是"唯美/舒服"的部分——传递"美好生活期待"，让用户先产生"我也想要这样的冰箱"的代入感。

**反差植入**：画面本身是美好的、舒服的（让用户放松），但右侧那句"双循环 ≠ 双系统 / 差了一整套蒸发器"突然点破认知差——**美好的画面 + 戳心的一句话**，制造"我可能买错了"的不安。这种"先美好后戳穿"比"直接报警示符号"高级，也不会触发限流。

**文案作用**：
- 标题说"有猫腻/别花冤枉钱"（情绪+损失）
- 封面补"双循环≠双系统"（认知+知识）——正好是补充不是复述
- 两行文字：主标题"双循环≠双系统"点破认知，副标题"差了一整套蒸发器"给具体答案

**排版**：冰箱偏左，右侧留白放文案，构图平衡、有呼吸感（这就是"排版得体"）。
