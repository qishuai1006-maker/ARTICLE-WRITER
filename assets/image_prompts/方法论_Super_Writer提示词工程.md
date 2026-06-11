# AIGC 提示词方法论 · Super Writer 专用版

> **目的**：让每篇文章的配图都能用结构化提示词产出专业水准
> **最后更新**：2026-06-11
> **适用工具**：MJ / GPT-4o / ComfyUI（FLUX / SDXL）/ 即梦 / 通义万相

---

## 🧠 4 层结构化方法论（核心理论）

每张图的提示词都必须按这个结构写：

```
[第1层：主体]   谁/什么 + 在哪 + 长什么样
[第2层：动作]   主体在做什么（具体动作）
[第3层：环境]   光/天气/室内外/时间/氛围
[第4层：风格]   摄影/绘画风格 + 镜头参数 + 色调
+ 负面提示词：   不许出现的内容
```

### 为什么是 4 层不是 1 层？

- 1 层："画一台热水器" → AI 输出 100 种可能，控制力 0
- 4 层：4 个维度各一句话 → 控制力 80%，AI仍有 20% 创意空间
- 7 层：太具体 → AI 失去创意，可能输出错误

**黄金比例**：每层 30-50 字，总提示词 150-250 字最优。

---

## 🎯 头条配图专用的 4 个硬约束

**这是头条图片审核的红线，必须遵守：**

| 约束 | 原因 | 写法 |
| --- | --- | --- |
| ❌ 不许出现文字 | 头条要求原创图，文字水印直接判定"非原创" | `negative_prompt: text, watermark, logo, caption` |
| ❌ 不许出现人脸 | 头条偏好"无人"画面 | `negative_prompt: people, faces, body parts, hands` |
| ✅ 真实摄影风格 | 头条读者更信实拍 | 风格层加 `photorealistic, documentary photography` |
| ✅ 16:9 / 3:2 比例 | 头条显示最佳比例 | `aspect_ratio: "16:9"` 或 `"3:2"` |

---

## 🎨 6 大文章类型 × 配图风格映射表

| 文章类型 | 推荐风格 | 推荐主体 |
| --- | --- | --- |
| **选购横评**（你的主战场）| 产品特写 + 多产品对比 | 实物产品 + 数字标牌 |
| **教程避坑**（你的主战场）| 步骤图解 + 真实场景 | 工具 + 手部动作（特写） |
| **趋势科普** | 数据可视化 + 抽象概念具象化 | 信息图 + 图形 |
| **故事线 / 个人感悟** | 生活场景 + 人物剪影 | 室内场景 + 背影 |
| **观点输出 / 拆解面** | 强对比构图 | 冷暖对比 / 新旧对比 |
| **避坑案例** | "反面教材"特写 | 问题点放大 + 红圈标注 |

**你的热水器文章是"教程避坑 + 观点输出"组合** → 推荐"产品特写 + 强对比"风格。

---

## 🖼️ 配图数量规则（头条实战）

| 配图数 | 适用情况 | 你当前 |
| --- | --- | --- |
| 1 张 | 短文（< 1500 字） | ❌ |
| **2 张** | **标准文（1500-2500 字）** | ✅ **本次** |
| 3 张 | 长文（> 2500 字） | ❌ |
| 4+ 张 | 几乎不要 | ❌ |

**你的配图位置建议**：
- 图 1：封面（头图）
- 图 2：正文条件 3 之后（北方 vs 南方）

---

## 📋 4 层结构模板（复制即用）

### 模板 A：产品对比图

```
[主体] A modern [产品名] placed on the left side,
       with a comparison [对照物] on the right side,
       both items clearly visible in frame

[动作] Static product display, slight angle showing
       both front and side details

[环境] Clean [桌面/厨房/展厅] background with soft
       natural lighting from window, daytime setting

[风格] Commercial product photography, 50mm lens,
       f/2.8 depth of field, neutral color grading
```

### 模板 B：场景对比图（南北/新旧/冷暖）

```
[主体] Split-screen composition: left side shows
       [场景 A], right side shows [场景 B], hard
       diagonal split line in the middle

[动作] No human action, static scenes side by side

[环境] Left: [冷峻/暖色调/...] lighting;
       Right: [对比的] lighting

[风格] Editorial illustration style, documentary
       photography aesthetic
```

### 模板 C：步骤图解

```
[主体] A close-up of [工具/产品] in [使用场景],
       with subtle visual indicators (numbered
       circles, arrows) marking [关键步骤]

[动作] Mid-action shot showing [具体动作]

[环境] Well-lit [场景], professional photography
       setup with controlled lighting

[风格] Tutorial photography style, instructional
       diagram aesthetic, clean and clear
```

---

## 🛠️ 各工具适配说明

### Midjourney (`/imagine`)
- 在 4 层结构末尾加 `--ar 16:9 --style raw --v 6`
- 不用写 negative prompt（MJV6 已自动处理大部分）
- 中英混合提示词也可用

### GPT-4o (`/image`)
- 必须用英文（中文支持弱）
- 中等长度（100-200 字效果最好）
- 强加 `photorealistic` 关键词效果显著

### ComfyUI（FLUX / SDXL）
- 用 4 层结构完整版
- 加技术参数（steps / cfg / sampler）
- 必须写负面提示词
- 推荐 aspect_ratio 控制 + ControlNet 增强

### 即梦 / 通义万相
- 中文提示词即可
- 推荐 100-200 字短描述
- 不需要负面提示词

---

## 📂 历史配图提示词

- `热水器_13升vs16升_2图.md` ← 首篇配图（已生成）

---

## ✅ 配图质量自检 6 问

发布前对照这 6 个问题：

| 问题 | 通过条件 |
| --- | --- |
| 1. 有无文字水印？ | ❌ 必须无 |
| 2. 有无人脸？ | ❌ 必须无 |
| 3. 主体是否清晰？ | ✅ 一眼能看出主题 |
| 4. 色调是否一致？ | ✅ 2 张图色调风格统一 |
| 5. 比例是否合规？ | ✅ 16:9 或 3:2 |
| 6. 是否扣题？ | ✅ 配图主题对应正文某段 |