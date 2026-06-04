# T12｜ContentFleet 文章追踪更新 Skill 封装记录

**日期**：2026-05-27  
**操作人**：Codex  
**目标**：把“文章追踪全量更新”封装为可复用 Codex Skill，减少每次手工解析 Excel、生成导入包、覆盖飞书、回读校验的重复劳动。

## 1. 新增 Skill

Skill 路径：

`/Users/ltn/.codex/skills/contentfleet-article-tracking-update`

Skill 名称：

`contentfleet-article-tracking-update`

触发场景：

- 用户提供牛科技、牛科技说两个账号的今日头条全量 Excel 导出；
- 用户要求更新、覆盖、替换、刷新飞书文章追踪表；
- 用户要求生成文章追踪导入包、复盘 CSV、复盘摘要、覆盖前备份、覆盖后回读校验或操作日志。

## 2. Skill 文件结构

```text
contentfleet-article-tracking-update/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── field口径.md
└── scripts/
    └── contentfleet_article_tracking_update.py
```

## 3. 脚本能力

脚本：

`/Users/ltn/.codex/skills/contentfleet-article-tracking-update/scripts/contentfleet_article_tracking_update.py`

支持能力：

1. 自动识别或接收两个账号的 Excel 路径。
2. 解析今日头条后台导出的 `.xlsx` 文件。
3. 生成飞书文章追踪表的批量导入 JSON。
4. 生成复盘预览 CSV。
5. 生成复盘摘要 Markdown。
6. 生成操作日志 Markdown。
7. 在 `--write-feishu` 模式下执行飞书覆盖：
   - 备份旧文章追踪表；
   - 删除旧记录；
   - 批量创建新记录；
   - 回读飞书表校验记录数、账号分布、表现分层和 Top 阅读样本。

## 4. 使用方式

只生成本地导入包和复盘摘要：

```bash
/Users/ltn/.codex/skills/contentfleet-article-tracking-update/scripts/contentfleet_article_tracking_update.py \
  --workspace "/Users/ltn/Downloads/ARTICLE WRITER" \
  --batch-date 2026-05-27
```

执行飞书覆盖写入：

```bash
/Users/ltn/.codex/skills/contentfleet-article-tracking-update/scripts/contentfleet_article_tracking_update.py \
  --workspace "/Users/ltn/Downloads/ARTICLE WRITER" \
  --batch-date 2026-05-27 \
  --write-feishu
```

如需指定 Excel：

```bash
/Users/ltn/.codex/skills/contentfleet-article-tracking-update/scripts/contentfleet_article_tracking_update.py \
  --workspace "/Users/ltn/Downloads/ARTICLE WRITER" \
  --niukeji-xlsx "/Users/ltn/Downloads/图文_-_1-45牛科技.xlsx" \
  --niukejishuo-xlsx "/Users/ltn/Downloads/图文_-_1-19牛科技说.xlsx" \
  --batch-date 2026-05-27
```

## 5. 验证结果

已完成两项验证：

1. 本地 dry-run 通过：使用 `/Users/ltn/Downloads/图文_-_1-45牛科技.xlsx` 和 `/Users/ltn/Downloads/图文_-_1-19牛科技说.xlsx`，成功生成 64 条导入数据。
2. Skill 结构校验通过：`quick_validate.py` 返回 `Skill is valid!`

## 6. 后续注意

- 这个 Skill 已放在 `~/.codex/skills`，后续新会话可自动发现。
- 当前会话的技能列表可能不会即时刷新；如果要在新会话中显式使用，可说“用 `$contentfleet-article-tracking-update` 更新文章追踪”。
- 每次真实覆盖飞书前，仍建议先生成本地导入包并检查复盘摘要。
- 如果未来标题结构或文章类型识别出现偏差，优先小范围 patch 脚本里的规则，再重新生成导入包。
