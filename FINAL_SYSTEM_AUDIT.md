# FINAL 系统验收报告 · Super Writer 家电图文生产系统

> 验收日期：2026-06-27
> 验收范围：Phase 1 / 1.5 / 1.5B / 2A 暴露问题的规则化闭环核查
> 验收方式：文件级 + 脚本级 + 流程级实读核查（非记忆判断）

## 1. 一句话判断

当前系统已基本具备家电图文生产能力，CEO 历史暴露的 10 个高频问题中 **8 个已沉淀为规则卡 + 脚本闭环**，2 个（参数翻译品类覆盖 / 降火修边）部分解决；但**标题、封面、主冲突兑现、品牌分寸仍需人工抽查**，不是全自动爆文机器。建议**冻结主体 + 允许小规模日常使用 + 同步小修残留**。

## 2. 已解决问题清单（10 项逐条核查）

### ✅ 问题1 多 Agent / Skills 不稳定
- **原问题**：多 Agent 设计好但运行乱跑；Skills 过长读不动
- **对策**：`/write` 改为 Phase 1 单会话角色切换（projectSettings:write 明确"不派子 agent，单会话角色切换，强制产物链"）
- **关联脚本**：`execution_log.jsonl` 每步记录角色/读取/产出/lint
- **闭环**：✅ 闭环。仍需人工观察单会话是否真按角色切换（四棒 Agent 是纯文档无 frontmatter，靠主控扮演，见 memory: project-agents-not-wired-into-claude-code）

### ✅ 问题2 主线跑偏（T7M 京东独家抢差200元主线）
- **原问题**：secondary_conflict 抢走 main_conflict
- **对策**：`01b_总编辑定稿卡.yaml` 锁定 original_user_intent / main_conflict / secondary_conflict / main_conflict_keywords / secondary_conflict_limit.max_opening_share / must_answer_questions / conclusion_direction / business_strategy / preferred_title / title_candidates / visual_lock（字段核验齐全）
- **关联脚本**：`check_editorial_lock.py`(204行) — ①标题命中≥2 main_conflict_keywords ②前300字主冲突关键词≥2 ③**副冲突占比 > max_opening_share(默认35%) → ERROR**（直接拦截 T7M 式抢主线）④结尾承接
- **闭环**：✅ 闭环。隐性微偏仍需人工

### ✅ 问题3 标题能过 lint 但不够犀利
- **原问题**：标题合规但变平（"京东独家不是缩水款"没抓住"差200元该不该上"）
- **对策**：R02 标题优先级（七维评分）；preferred_title 必须"承接main_conflict"+"购买决策冲突"双 true；风控改标题必须记录原标题/新标题/原因/是否削弱点击力/是否仍承接main_conflict
- **关联脚本**：`check_title_delivery.py`(341行) — **双向闸门**：正向防夸张(check1-5,7) + 硬黑名单(check6 恐吓/强迫/虚假热度→ERROR) + **反向防平庸(check8 标题无冲击力但正文有弹药→过度弱化)** ← 直接对应"标题变平"
- **闭环**：⚠️ 半闭环。脚本拦平庸/夸张，"够不够犀利"人工拍板

### ✅ 问题4 业务策略只会禁词不会正向定位
- **原问题**：能避免"踩Pro"但缺"Ultra适合谁/Pro适合谁"
- **对策**：R08 业务策略四层面（protected_models_or_brands / allowed_positioning / forbidden_positioning / conclusion_direction），典型错误就是"business_strategy: 不踩Pro"
- **关联脚本**：`check_editorial_lock.py` D项 — 结尾段必须出现 allowed_positioning 正向词 + 提及 protected_models_or_brands + 全文无 forbidden_positioning
- **闭环**：✅ 闭环

### ✅ 问题5 AI 主动制造新疑问（2176分区考古）
- **原问题**：T7M 引入"发布稿最高2176分区"用户不关心的新参数
- **对策**：R01 不制造新疑问 — **典型错误直接用 2176 分区案例**；5 条准入（回答main_conflict/购买决策/标题承诺/适合谁/结尾判断）；applies_to:[主笔] read_at:[Step3]
- **闭环**：⚠️ 半闭环。规则清晰无脚本，段落跳跃靠主笔自检 + 风控人工审

### ✅ 问题6 字数硬门槛导致水文
- **原问题**：`<1500字` ERROR 诱导注水幻觉
- **对策**：`lint_quick_article.py` line 343-344 — **`<1500字` 已降为 WARNING**；同时 density_ratio（平均单条证据扩写>250字→ERROR 水文）打回 Step2 补调研
- **关联文件**：R04 证据密度
- **闭环**：✅ 闭环。证据不足明确处理：回调研/缩短/改短决策文/删无证据段

### ⚠️ 问题7 参数翻译不足（部分解决）
- **原问题**：568分区/500nits/双蒸发器/PST+/制冰/零嵌 用户无感
- **对策**：R06 家电参数翻译（applies_to:[主笔]）+ `运营方法论/05_家电参数翻译库.md`（参数→误解→后果→判断）
- **缺口**：style_examples 仅拆出**电视/空调/油烟机mini** 3 品类，**缺冰箱/热水器/洗衣机**样本
- **闭环**：⚠️ 部分。规则可用，品类样本不全

### ✅ 问题8 封面好看但不服务点击
- **原问题**：封面成品牌广告图（冰箱重复全标题/T7M把Pro做暗拉踩）
- **对策**：R03 封面规则 + 01b.visual_lock + `Skills/03-配图提示词生成规范.md`（**已从17KB精简到1.5KB**）+ 4:3安全区（16:9外框核心信息居中75%宽）
- **关联脚本**：`check_visual_lock.py` — 封面承接main_conflict + 禁视觉拉踩（protected model做暗/做脏）+ 禁大红叉/吊打/阉割
- **闭环**：⚠️ 半闭环。规则+脚本能禁硬伤，"像不像头条爆文"靠人工审美

### ✅ 问题9 图位不闭环（"此处插图缺失：未指定"）
- **原问题**：终稿出现未指定占位
- **对策**：R05 图位闭环 + `visual_plan.yaml`（每图位含 slot_id/function/paragraph/core_relation/evidence_id/prompt/forbidden）
- **关联脚本**：`check_visual_lock.py` V6 — **"此处插图缺失：未指定" → 直接 ERROR**；V5 正文图位全覆盖；slot evidence_id 核对
- **闭环**：✅ 闭环

### ⚠️ 问题10 竞品对比火力过猛（部分解决）
- **原问题**：假双循环/糊弄人/容声输给美的/绕开/跟牌子没半点关系/全系标配/标配制冰
- **对策**：R08 正向定位 + `check_title_delivery.py` HARD_GREY 黑名单（恐吓/强迫→ERROR）+ check_editorial_lock forbidden_positioning
- **缺口**：**"降火修边"（绝对化→留余地）尚未进规则卡**。本次冰箱篇 CEO 反馈的"没半点关系→不只是靠牌子 / 全系标配→主销价位下放 / 不会饱和→卖点速度快感知强 / 标配→加分项"已记入 memory（ceo-writing-detone-no-absolutism），但 R08 规则卡本身没加降火条款，脚本也不查绝对化词
- **闭环**：⚠️ 部分。攻击词有脚本兜底，绝对化靠人工 + memory

## 3. 仍需人工抽查的 6 项

1. **标题犀利度**：脚本能拦平庸/夸张，"够不够抓人"人工拍板
2. **封面爆文感**：脚本能禁拉踩/参数墙，"像不像头条首图"人工审美
3. **主线微偏**：check_editorial_lock 拦明显抢戏，隐性偏移人工审
4. **AI 装专业**：R01 规则清晰无脚本，段落跳跃感人工审
5. **竞品火力**：攻击词有脚本，绝对化/引战火候人工判断
6. **真实博主感 vs 品牌稿**：去AI味24类 + Humanizer-zh 复核辅助，最终人工定

## 4. 不建议继续做的 5 项

1. ❌ 不反复跑完整长文测试（已过验证期，继续跑=烧token无新信息）
2. ❌ 不为单个段落重构系统（规则卡已够细）
3. ❌ 不一次性拆碎所有知识库（按需召回即可，拆碎增加管理成本）
4. ❌ 不追求完全自动发布（CLAUDE.md 铁律：publish_toutiao.py 默认 --draft）
5. ❌ 不让 Agent 自己判断读哪些长文件（按步骤必读规则卡已锁定 read_at）

## 5. 最省 token 的使用方式

| 改什么 | 只测什么 | 不用跑 |
|---|---|---|
| 改标题 | check_title_delivery + check_topic_collision | 完整/write |
| 改封面 | 生成封面提示词 + CEO肉眼核 + check_visual_lock | 完整/write |
| 改段落 | 单段落重写 + lint_quick_article 段落密度 | 完整/write |
| 改参数翻译 | R06 + 参数翻译库对应品类 | 完整/write |
| 完整产线 | 阶段性跑完整 /write（新品类/新母体首篇）| 每篇都跑 |

## 6. 最终结论

**允许小规模使用**（主结论）+ 配套：
- **冻结主体**：规则卡 R01-R08 + 6 核心脚本 + /write 流程不再重构
- **小修残留**（不阻塞日常）：①删旧 style_examples.md(33KB) 引用 ②R08 补降火条款 ③补冰箱/热水器/洗衣机 style 样本 ④R07 补典型反例 ⑤复盘闭合率 0% 待养成 /fupan 习惯
- **合并 main**：当前 phase1-role-switching-pipeline 分支的规则卡/脚本/Skills 变更建议合并 main（合并前建议先做①②，③④⑤可后续）
- **维护节奏**：发布后 /fupan 复盘驱动公式库/规则卡升降级（数据飞轮），不再主动重构

> 核心判断：系统已过"流程不稳定"期，进入"基本可用 + 人工抽查标题/封面/主冲突/品牌分寸"期。继续大规模重构 ROI 极低。
