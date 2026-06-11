# 接力模板使用规则

> **配套文件**：`handoff_template.yaml`（结构化模板）
> **最后更新**：2026-06-11

## 写入时机

| 阶段完成 | 写哪个 YAML |
| --- | --- |
| T1 | `test_run/_handoff/[文章ID]_T1.yaml` |
| T1.5 | `test_run/_handoff/[文章ID]_T1.5.yaml`（追加 skeleton/title） |
| T2 | `test_run/_handoff/[文章ID]_T2.yaml`（追加 three_layers） |
| T3 | `test_run/_handoff/[文章ID]_T3.yaml`（追加 draft） |
| T4 | `test_run/_handoff/[文章ID]_T4.yaml`（追加 self_check） |

## 读取时机

- 下一阶段开始时，**第一个动作**就是读上一阶段的 YAML
- 不需要读前一阶段的具体输出文件（除非需要细节）

## 文件位置

```
test_run/_handoff/[文章ID]_T[阶段].yaml
```

**不提交到 git**（`.gitignore` 已配置 `test_run/_handoff/`，含个人决策细节）

## 为什么是 YAML 而不是 Markdown

- 机器可读（未来可自动化分析）
- 结构固定（不会因人类编辑而走样）
- 字段明确（不会忘记某个信息）
- 易转换（YAML ↔ JSON ↔ Markdown）
- 老七聊 AI 也友好（人类一眼能看懂结构）

## YAML 完整字段说明

### article（基础信息）
- `id`：简短 ID，如"第 1 篇"
- `date`：YYYY-MM-DD
- `topic`：完整话题
- `domain`：品类（冰箱/空调/电视/...）
- `skeleton`：骨架（问题链/故事线/拆解面）
- `title_template`：标题模板（反问悬念/多品牌对决/...）
- `title`：完整标题
- `target_word_count`：目标字数
- `stage`：当前已完成阶段
- `next_stage`：下一阶段

### context_summary（关键决策精炼版）
- `angles_suggested`：撒网角度数
- `angle_chosen`：选定的角度标签
- `angles`：每个角度的 id/label/one_liner（≤50 字）
- `three_layers`：3 层深度摘要（每层 ≤50 字）
- `skeleton_reason`：选骨架的理由

### assets_referenced（资产引用）
- `title_samples`：参考的标题样本文件路径
- `opening_samples`：参考的开头样本路径
- `golden_lines`：参考的金句库路径

### draft（T3 产物）
- `path`：成品正文路径
- `word_count`：实际字数
- `has_opening_hook`：开头是否有钩子
- `has_comment_hook`：结尾是否有评论钩子

### self_check（T4 自检）
- `score`：通过分数，如 "11/12"
- `passed`：是否通过
- `warnings`：警告列表
- `errors`：错误列表

### handoff（接力目标）
- `to`：下一个 agent 名
- `next_prompt`：下一个 prompt 文件路径
- `urgency`：紧急程度（high/medium/low）

### risks（风险备注）
- 任何需要下一阶段注意的边界情况

### meta（元数据）
- `created_at`：ISO 时间戳
- `created_by`：哪个 agent 填写
- `schema_version`：模板版本号