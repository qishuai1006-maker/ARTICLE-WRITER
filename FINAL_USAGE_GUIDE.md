# FINAL 低 token 使用指南

> 核心原则：**按步骤按需加载规则卡，不全量读；改什么只测什么，不跑完整 /write**。

## 一、按步骤必读规则卡（不全量加载）

| Step | 角色 | 必读规则卡 | 按品类加载 |
|---|---|---|---|
| 1 选题 | 选题策划 | R07 爆款母体 | — |
| 2 调研 | 情报调研 | R04 证据密度 | L1/L2/L3 按品类 |
| 2.5 定稿 | 总编辑 | R02 标题 / R08 业务策略 | — |
| 3 主笔 | 首席主笔 | R01 不制造新疑问 / R04 证据密度 / R06 参数翻译 | style_examples/[品类].md（只读当前品类）|
| 4 风控 | 风控主编 | R04 / R08 | — |
| 5 视觉 | 视觉指挥官 | R03 封面 / R05 图位闭环 | — |

**铁律**：style_examples 只读当前品类单个文件（≤5KB），**绝不读旧 style_examples.md（33KB）**。

## 二、改什么只测什么（省 token 决策表）

### 场景A：只改标题
- 读：R02 + 现有 01b 定稿卡
- 跑：`python3 Scripts/check_title_delivery.py 03_终稿.md` + `python3 Scripts/check_topic_collision.py`
- 不跑：完整 /write

### 场景B：只改封面
- 读：R03 + visual_plan.yaml
- 做：生成封面提示词 → CEO 即梦/GPT-4o 真实生图 → 肉眼核
- 跑：`python3 Scripts/check_visual_lock.py 03_终稿.md --lock 01b.yaml --visual visual_plan.yaml`
- 不跑：重写正文

### 场景C：只改单段落
- 读：该段相关规则卡（如净味段读 R06）
- 跑：`python3 Scripts/lint_quick_article.py 03_终稿.md`（段落密度/红线词）
- 不跑：完整 /write

### 场景D：补参数翻译
- 读：R06 + `运营方法论/05_家电参数翻译库.md` 对应品类
- 做：补≥3 条参数翻译词（说白了/落到家里就是/这意味着）
- 不跑：重写全文

### 场景E：完整产线（仅在以下情况跑完整 /write）
- 新品类首篇（需先补 style_samples + 参数翻译库）
- 新爆款母体首试
- CEO 明确要求完整重做
- 日常同品类迭代：**优先局部改，不跑完整 /write**

## 三、token 红线

1. **单次会话不读 >5KB 的非规则卡文件**（旧 style_examples.md 33KB 禁读）
2. **规则卡按 Step 加载**（一次最多读当前 Step 的 2-3 张，不预读全量）
3. **L1/L2/L3 知识库按品类召回**（不跨品类全读）
4. **对标文章归档/ 隔离**（写稿阶段不读原文，只读拆解卡/证据卡）
5. **子 agent 谨慎派**（生产子 agent 默认带4条防卡死指令；规则敏感写作主控自写，子 agent 只做数据调研）
6. **context >70% 停下**（交付/归档，不开新完整 /write）

## 四、日常生产推荐节奏

- **每周 2-3 篇**（同品类迭代，局部改为主）
- **每篇交付**：附三表（事实溯源 + 去AI味24类 + lint三闸门结果）
- **每篇发布 3-7 天**：`/fupan <归档路径> <头条链接>` 闭合数据飞轮
- **每周**：`python3 Scripts/loop_status.py` 看复盘闭合率
- **每月**：据复盘数据驱动公式库/规则卡升降级（不主动重构）

## 五、何时该停（红灯信号）

- **同形式标题连用 >5 次** → 疲劳（实测8次从13.9万跌到59）→ 换壳
- **lint 反复改同类错误 >3 次** → 停下看规则卡是否写清，别硬改
- **context >70%** → 停下交付/归档，不开新完整 /write
- **子 agent 卡住 >30min** → 跳过该步，主控接手
- **CEO 问"在哪查到的"** → 红灯，事实可能没一手核（memory: fact-verification-must-hit-primary-source）

## 六、脚本速查（何时跑哪个）

| 脚本 | 何时跑 | 硬闸门? |
|---|---|---|
| lint_research_gate.py | Step2 L3报告落盘后 | 硬（12 sys.exit）|
| check_editorial_lock.py | Step3 02初稿落盘后 | 硬（6 sys.exit）|
| lint_writing_gate.py | Step3 02初稿（check_editorial_lock之后）| 硬（17 sys.exit）|
| lint_quick_article.py | Step4 03终稿 Write 自动触发(hook) | 硬（0 ERROR才过）|
| check_title_delivery.py | Step4 风控审标题 | WARNING为主 |
| check_visual_lock.py | Step5 visual_plan落盘后 | 硬（5 sys.exit）|
| validate_visual_outputs.py | 进 Agent04 / 出 Word 前 | 硬（图真实落盘/分辨率）|
| check_topic_collision.py | Step1 选题 + 标题定稿前 | 辅助（查撞车/疲劳壳）|
