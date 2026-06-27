# /write 命令 (Phase 1 单会话重构版)

> **核心哲学**：不派子 agent，单会话角色切换，强制产物链。
> **目标**：完成一篇符合牛科技长文规范的图文创作。

## 铁律
1. **单会话执行**：不使用多进程，不唤起子 agent。
2. **强制产物链**：上一步未落盘文件，不可进入下一步。
3. **强制 Lint**：每步必须通过对应的 lint 脚本，否则回退修改。
4. **日志记录**：所有的关键步骤成功/失败，需追加写入 `execution_log.jsonl`（记录时间、步骤、产出、状态）。

---

## 阶段 1：选题策略 (Step 1)
**动作**：
1. 分析用户输入的选题（例如：`85寸TCL T7M Ultra vs Pro 差200元怎么选`）。
2. 出 5 角度选题方案。
3. 撞车检查。
4. 选题评分。
5. 落盘 `00_选题方案表.md`。
**闸门**：需等 CEO 确认或直接执行。

---

## 阶段 2：情报调研 (Step 2 - 角色：情报调研员)
**动作**：
1. 收集事实、配置、价格差异等。
2. 填写 `L3_调研报告`。
3. 必须生成 `## 证据登记表`，并为每条数据分配 `evidence_id`。
4. 预生成 8-12 个候选标题，作为后续定稿参考。
**落盘**：`家电知识库/L3_场景调研报告/[YYYYMMDD]_[账号]_[品类]_[关键词]_L3调研报告.md`
**闸门**：运行 `python3 Scripts/lint_research_gate.py <L3报告路径>`，必须 PASS。

---

## 阶段 2.5：总编辑定稿卡 (Step 2.5 - 角色：总编辑)
**本步骤必读规则卡**：`Skills/规则卡/R02_标题优先级.md`、`Skills/规则卡/R07_爆款母体.md`、`Skills/规则卡/R08_业务策略.md`
**动作**：
1. 审阅调研报告与选题，复述用户真实意图（`original_user_intent`），不得篡改。
2. 锁定 `main_conflict`（本篇核心购买决策冲突）和 `main_conflict_keywords`。
3. 锁定 `secondary_conflict`（副冲突只能服务主线，不得抢戏）。
4. 对 Step 2 产出的 8-12 个候选标题，逐条按 7 维度打分：
   - 承接main_conflict / 使用最强证据 / 有购买决策冲突 / 没有把结论说死 / 不踩保护型号 / 能被前300字承接 / 比旧标题更有点击力
5. **标题选择铁律**：`preferred_title` 必须在全部候选中"承接main_conflict"和"有购买决策冲突"两项同时为 true，否则不得选用。
6. 填写 `must_use_evidence`（结构化、绑定 evidence_id）、`forbidden_positioning`、`allowed_positioning`、`business_strategy`（正向定位，不只是禁词）、`conclusion_direction`（必须回答"到底怎么选"）。
7. 填写 `visual_lock`：封面必须承接 main_conflict，不做视觉拉踩，每个正文图位必须有结构化描述。
**落盘**：`01b_总编辑定稿卡.yaml`
**闸门**：YAML 所有必填字段非空。`preferred_title` 必须命中 ≥2 个 `main_conflict_keywords`。

---

## 阶段 3：主笔初稿 (Step 3 - 角色：首席主笔)
**本步骤必读规则卡**：`Skills/规则卡/R01_不制造新疑问.md`、`Skills/规则卡/R04_证据密度.md`、`Skills/规则卡/R06_家电参数翻译.md`，以及当前品类的 `Skills/style_examples/[品类].md`（不要全量读取其他品类）。
**动作**：
1. 读取 `Agents/02-首席主笔Agent.md`、`01b_总编辑定稿卡.yaml`、`L3_调研报告`。
2. 围绕定稿卡的主冲突和首选标题写初稿，不可改写主线，必须嵌入 `must_use_evidence` 要求的核心证据。
**落盘**：`02_首席主笔初稿_[品类].md`、`02b_轻量证据卡_[品类].md`
**闸门**：运行 `python3 Scripts/check_editorial_lock.py 02_首席主笔初稿_[品类].md --lock 01b_总编辑定稿卡.yaml --evidence 02b_轻量证据卡_[品类].md`，必须 PASS。之后运行 `python3 Scripts/lint_writing_gate.py 02_首席主笔初稿_[品类].md`。

---

## 阶段 4：风控与对账 (Step 3.5 & 4 - 角色：风控主编)
**本步骤必读规则卡**：`Skills/规则卡/R04_证据密度.md`、`Skills/规则卡/R08_业务策略.md`
**动作**：
1. 检查标题是否依然被正文兑现。
2. 扫描红线词汇、核对事实，检查定稿卡要求是否被满足。
3. 只能在不削弱核心钩子（main_conflict）的前提下微调标题。如果必须改标题，必须在审核报告里输出：原标题、新标题、修改原因、是否削弱点击力、是否仍承接 main_conflict。如果削弱主冲突，必须 ERROR。
**落盘**：`03_风控主编终稿_[品类].md`、`03_审核报告_[品类].md`

---

## 阶段 5：视觉规划 (Step 5 - 角色：视觉指挥官)
**本步骤必读规则卡**：`Skills/规则卡/R03_封面规则.md`、`Skills/规则卡/R05_图位闭环.md`
**动作**：
1. 读取 `01b_总编辑定稿卡.yaml` 的 `visual_lock` 字段、`main_conflict`、`preferred_title`、`business_strategy`、`forbidden_positioning`、`protected_models_or_brands`、`must_use_evidence`。
2. 规划封面和信息图。封面必须服务购买决策，不是做漂亮广告图。
3. 终稿中严禁出现"此处插图缺失：未指定"。每个占位必须写清功能（封面/理解/收藏/对比）、段落、核心关系、evidence_id、提示词、禁止事项。
4. 如果 `visual_plan.yaml` 未能覆盖所有正文插图位置，必须打回。
**落盘**：`04_视觉指挥官配图_[品类].md`、`visual_plan.yaml`
**闸门**：运行 `python3 Scripts/check_visual_lock.py 03_风控主编终稿_[品类].md --lock 01b_总编辑定稿卡.yaml --visual visual_plan.yaml`，必须 PASS。

---

## 阶段 6：出 Word 与状态卡 (Step 6)
**动作**：
1. 组装 `00_生产状态卡.md`。
2. 运行出 Word 脚本（注：若无真实图片，Word 脚本不报错，仅保留图片占位符）。
**落盘**：`.docx` 最终文件。

---

## 阶段 7：归档
**动作**：
将所有 `00` 到 `05` 以及 `.docx` 文件归档到 `projects/W[本周数]/[选题]_归档/` 下。
完成。
