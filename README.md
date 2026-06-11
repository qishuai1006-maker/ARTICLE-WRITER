# Super Writer · 头条图文工作流

> **版本**：v1.0 · 数据驱动 + 上下文管理双轨版
> **最后更新**：2026-06-11
> **状态**：✅ 可投入生产（新个人号起量期）

---

## 🎯 一句话定位

**用 100 篇历史 + 54 篇外部爆款反推出的数据驱动 + 上下文管理 v1.0 架构**，让新个人号每天稳定产出 3-5 篇高质量头条图文。

## 🚀 30 秒上手

```bash
# 1. 进工作目录
cd "/Users/aaron/Library/CloudStorage/GoogleDrive-qishuai1006@gmail.com/我的云端硬盘/Super Writer"

# 2. 启动 Claude Code / Hermes
# Claude Code: claude
# Hermes: 在 Telegram 发 /new

# 3. 第一次对话开头
读取 prompts/README.md，按「上下文管理 v1.0」工作模式执行。
我要跑第 1 篇：冰箱品类，话题是 [你来定]。
```

## 📁 目录结构

```
Super Writer/
├── prompts/                          ← 规则 + 模板（按 T 阶段分）
│ ├── README.md                       工作流总入口
│ ├── 01-选题/选题_三追问.md         T1 第一轮 Prompt + 标题配方
│ ├── 02-骨架选型/                    T1.5 骨架决策
│ ├── 03-深度/                        T2 三层深度
│ ├── 04-写作/                        T3 骨架填空
│ └── 05-自检/                        T4 12 项检查
│
├── data/                             ← 原始数据（飞书抓取）
│ ├── 历史文章_100篇_20260611.json
│ └── 外部爆款_54篇_20260611.json
│
├── assets/                           ← 🆕 跨篇复用沉淀库
│ ├── titles/                         爆款标题（按品类 + 模板）
│ ├── openings/                       优质开头（按骨架）
│ ├── golden_lines/                   金句 / 评论钩子
│ └── titles_proven/                  自己已爆款标题
│
├── test_run/                         ← 每篇独立记录
│ ├── _handoff/                       T 阶段接力 YAML
│ └── 选题_2026-06-XX_*.md
│
├── _protocols/                       ← 🆕 上下文管理协议
│ ├── README.md
│ ├── naming_convention.md
│ ├── handoff_template.yaml
│ └── cross_session_resume.md
│
├── Skills/                           ← 沿用 v7.2（保留）
├── Scripts/                          ← 沿用 v7.2（保留）
├── 运营方法论/                        沿用 v7.2（保留）
├── 图文选题库数据运营/                  沿用 v7.2（保留）
│
├── AGENTS.md                         ← 通用执行层守则
├── CLAUDE.md                         ← 通用章程
└── README.md                         ← 本文件
```

## 📐 工作流（T1-T4）

```
T1 选题（10 分钟）       第一追问：5 个角度撒网 → 选 1
T1.5 骨架选型（5 分钟）   教程→问题链 │ 感悟→故事线 │ 观点→拆解面
T2 深度（15 分钟）       第二追问：核心观点推 3 层洞察
T3 写作（30 分钟）       第三追问：喂语调样本 + 骨架填空
T4 自检（10 分钟）       骨架完整性 + 三段一致性 + 评论钩子
─────────────────────
总计：约 70 分钟 / 篇
```

## 🧠 上下文管理 v1.0（核心）

**4 条铁律**：

1. **规则在文件系统，对话只 cat 引用**（不许把 7k+ Prompt 复制到对话里）
2. **每 T 一对话**（T1/T1.5/T2/T3/T4 各开新会话）
3. **中间产物全落盘**（test_run/ 每篇独立文件 + _handoff/ YAML）
4. **5 分钟恢复承诺**（任何断点都能 5 分钟恢复）

详细见 `_protocols/README.md`。

## 📊 数据驱动核心洞察（100 篇 + 54 篇反推）

### 标题是流量的唯一开关
- 标题弱（47%）：100% 沦为普通
- 标题强点击（19%）：100% 爆款/点击强

### 标题字数黄金区间
- **25-29 字**（CTR 4.90%）⭐️
- 30-34 字（CTR 4.75%）

### 反问悬念型标题是核武
- 4 篇样本中位展现 33,303，100% 爆款

### 选题域优先级
- 冰箱 57% / 空调 45% / 电视 50% / 显示器 50%（小样本但都是爆款）
- 洗衣机 11% / AI 0% —— 避开

完整 21 个爆款标题样本 + 10 个模板见 `prompts/01-选题/选题_三追问.md`。

## 🔧 自动化工具链

```bash
# T3 完成后跑（必跑）
python3 Scripts/lint_article.py test_run/成品_第X篇.md --json

# T4 自检时跑（必跑）
python3 Scripts/validate_outputs.py --verbose

# 头条自动发布（保留）
python3 Scripts/publish_toutiao.py --draft
```

## 📚 文档地图

| 我想看… | 看哪个文件 |
| --- | --- |
| 工作流总入口 | `README.md`（本文件） |
| T1 怎么跑 | `prompts/01-选题/选题_三追问.md` |
| 标题怎么写 | `prompts/01-选题/选题_三追问.md`（含 21 个爆款样本） |
| 骨架怎么选 | `prompts/02-骨架选型/骨架选型速查表.md` |
| T3 怎么写 | `prompts/04-写作/写作_骨架填空模板.md` |
| T4 自检清单 | `prompts/05-自检/发布前自检清单.md` |
| 上下文管理 | `_protocols/README.md` |
| 命名规范 | `_protocols/naming_convention.md` |
| 接力协议 | `_protocols/handoff_template.yaml` |
| 跨会话恢复 | `_protocols/cross_session_resume.md` |
| 数据洞察 | `CLAUDE.md` 第九节 |
| 历史合规规则 | `Skills/04-合规与质量双审Skill.md` |
| 活人写手感 | `Skills/10-活人写手感.md` |
| 产品参数库 | `Skills/产品信息库技能.md` |
| 选题域白名单 | `Skills/01-选题情报Skill.md` |

## 🎯 迭代日志

- **v1.0（2026-06-11）**：上下文管理 + 数据驱动双轨版
  - 删除：Codex 教练组、Wechatsync、4 个开源 Skill、飞书排期、历史归档
  - 保留：5 个核心 Skill + 4 个核心脚本 + 5 篇运营方法论
  - 新增：5 个核心 Prompt + assets/ 沉淀库 + _protocols/ 接力协议 + data/ 数据仓库
- **v0.1（2026-06-11）**：三追问 + 三骨架融合版（已被 v1.0 替代）

## 🆚 与 v7.2 对比

| 维度 | v7.2 | v1.0 |
| --- | --- | --- |
| Agent 数 | 2（Codex + Claude） | 1 + 双 Agent 接口 |
| 生产步骤 | T1-T7（7 步） | T1-T4（4 步） |
| 对话轮数 | 单轮 + 教练交接 | 强制 3 轮 |
| 配图 | NotebookLM 多图 | 极简 1-2 张 |
| 单篇耗时 | ~120 分钟 | ~70 分钟 |
| 上下文管理 | 单文件 RUN_STATE（膨胀） | 每 T 摘要 + 文件系统规则 + YAML |
| 数据驱动 | 经验为主 | 100 + 54 篇反推 |
| 跨篇复用 | 无 | assets/ 沉淀库 |