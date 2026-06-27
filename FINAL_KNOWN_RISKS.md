# FINAL 已知风险与人工抽查项

> 配套 FINAL_SYSTEM_AUDIT.md。列出当前脚本拦不住、必须人工兜底的风险点 + 每篇交付前抽查清单。

## 一、脚本已闭环（无需人工，失败即回退）

| 风险 | 拦截脚本 | 触发动作 |
|---|---|---|
| 主线被副冲突抢戏 | check_editorial_lock（副冲突占比>35%）| ERROR 回 Step2.5 |
| 标题不承接主冲突 | check_editorial_lock（命中<2 keywords）| ERROR |
| 图位未指定/"此处插图缺失" | check_visual_lock V6 | ERROR |
| 字数水文（density_ratio）| lint_quick_article | ERROR 回 Step2 |
| 标题恐吓/强迫/虚假热度 | check_title_delivery check6 | ERROR |
| 标题过度平庸（删光冲击力）| check_title_delivery check8 | WARNING |
| 正文踩 forbidden_positioning | check_editorial_lock | ERROR |
| 红线词（第一/最好/最强等子串）| lint_quick_article | ERROR |
| L3 调研缺证据登记/info_gain | lint_research_gate | ERROR |
| 02 初稿缺 flow_cards/参数翻译词 | lint_writing_gate | ERROR |

## 二、必须人工抽查（脚本拦不住）

### 标题层
- **犀利度**：check8 拦"过度平庸"，但"够不够抓人/有没有点击理由"人工拍板
- **疲劳壳**：同形式连用8次从13.9万跌到59（实测），check_topic_collision 查撞车不查形式疲劳，人工控

### 封面层
- **爆文感**：R03+check_visual_lock 禁拉踩/参数墙，"像不像头条首图"人工审美
- **真实生图 vs HTML占位**：封面必须 CEO 即梦/GPT-4o 真实生图，HTML只是占位（memory: notebooklm-cli-infographic-pipeline）

### 主线层
- **隐性微偏**：check_editorial_lock 拦明显抢戏，"主冲突被软性稀释"人工审
- **信息增益**：拆解卡 1-3 个独家判断（"以为A其实B"），填不出选题枪毙——人工判断

### 内容层
- **AI 装专业**：R01 规则清晰无脚本，段落跳跃/冷知识考古人工审（T7M 2176分区是教训）
- **事实一手核**：核心参数（分区/亮度/价格/排名）必须京东详情页一手核，脚本只查 evidence_id 存在不查真假（memory: fact-verification-must-hit-primary-source）
- **绝对化/降火**：R08 还没进降火条款，"没半点关系/全系标配/不会饱和"靠人工（memory: ceo-writing-detone-no-absolutism）

### 品牌分寸层
- **拉踩火候**：forbidden_positioning 查禁词，"点名打海尔易招黑"的火候人工判断
- **同系列不踩次款**：评测同系列多款不搞对立（T7M Ultra第一Pro第三各有优势），人工控（memory: dont-trample-sibling-model）

### 发布层
- **去AI味**：Humanizer-zh 24类复核（破折号滥用/空话套话/机械三段式/广告腔），脚本辅助人工终审
- **真实博主感**：最终"像不像活人写的不是品牌稿"人工定

## 三、未闭环的系统残留（建议小修，不阻塞日常）

1. **旧 style_examples.md（33KB）仍被 CLAUDE.md/Agent02/Skills04/07 引用** ⚠️ — 主笔误读爆 token。建议引用改指向 style_examples/ 目录（按品类）
2. **R08 缺降火条款** — 绝对化/攻击表达没进规则卡，靠 memory + 人工
3. **R07 爆款母体缺典型反例/正确改法** — 6要素不全（只缺这1张）
4. **style_examples 缺冰箱/热水器/洗衣机** — 参数翻译样本不全
5. **复盘闭合率 0%** — 发布后 /fupan 闭环未形成习惯（memory: loop-status-dashboard）

## 四、人工抽查清单（每篇交付前过一遍）

- [ ] **标题**：25-29字 + 悬念/反问 + 没疲劳壳 + check_title_delivery PASS
- [ ] **封面**：真实生图（非HTML）+ 4:3安全区 + 服务点击非品牌广告
- [ ] **主冲突**：前300字兑现 + 副冲突没抢戏（check_editorial_lock PASS）
- [ ] **品牌**：结尾场景分流（非品牌战争）+ 无拉踩 + 同系列不踩次款
- [ ] **事实**：核心参数一手核（京东详情页）+ evidence_id 全挂
- [ ] **降火**：无绝对化（没半点/全系/标配/不会饱和）+ 无攻击词（假/糊弄/绕开）
- [ ] **去AI味**：Humanizer-zh 24类复核 PASS
- [ ] **信息增益**：≥1 个"以为A其实B"独家判断
- [ ] **图位**：visual_plan 覆盖所有正文图位 + check_visual_lock PASS
