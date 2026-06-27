# Codex Agent Lanes

> 用途：登记 **Codex 内部长期线程型 Agent** 的职责、当前会话、写入范围和工作区。  
> 原则：新建 Codex 长期 Agent 前，必须先在本表注册；非 Codex 智能体不录入本表。

---

## 使用规则

1. **只登记 Codex Agent**：本表只服务 Codex 的跨线程协作；Claude Code、ZCode、Gemini 等外部智能体不在这里注册。
2. **先注册，后开工**：任何新建的 Codex 长期 Agent / 独立线程 Agent，开工前必须在 Lanes 表新增一行。
3. **会话 ID 是路由地址**：`current_session` 填 Codex thread id，用于 `send_message_to_thread`、`read_thread` 等线程工具跨 Agent 通信。
4. **写入范围要收窄**：`write_scope` 必须写清楚允许改哪些目录/文件；没有写进范围的文件默认只读。
5. **工作区要隔离**：选题/复盘等 Codex Agent 过程材料落到 `codex-agents/<agent-id>/`；每次文章生产内容统一落到固定目录 `outputs/Codex/`；成品/历史文章统一归档到根目录 `projects/`。归档时只移动 `outputs/Codex/` 里的文章内容，不移动或删除 `outputs/Codex/` 文件夹本身。
6. **会话变化要更新**：如果换新线程，更新 `current_session`，不要让旧 thread id 长期挂着。
7. **日志仍写系统日志**：本文件只登记“谁负责什么”；具体改动仍按 `系统日志.md` 规则登记。
8. **四棒生产 Agent 不重复登记**：`Agents/01-04` 是单篇生产流程内角色，不是长期线程，默认由 Orchestrator 调度。
9. **单篇生产必须有状态卡**：Codex 多 Agent 协作按 `codex-agents/CODEX_多Agent协作闭环方案.md` 执行。每篇文章进入生产时，先从 `codex-agents/生产状态卡_模板.md` 复制为 `outputs/Codex/[账号]_[品类]_[日期]/00_生产状态卡.md`，下游只认状态卡和落盘文件，不认口头完成。
10. **账号边界（2026-06-21 CEO 分工）**：Codex Agent 只生产**个人号（宅研社 / 北北ks）**；**公司号（牛科技 / 牛科技说）由 Claude Code 独家负责**，Codex 不接公司号选题/生产/复盘任务，避免双线撞号。
11. **个人号单会话闭环（2026-06-23）**：个人号日常生产取消第二终审会话。默认由 `personal-production-agent` 端到端负责 S0-S9，并在本会话内完成 A1-A6 自审闸门（选题、01c、正文、提示词、配图、发布包、复盘）。`personal-review-agent` 不再作为默认流程，只在 CEO 单独点名时做专项复审。详细流程见 `codex-agents/个人号单会话生产线.md`。

---

## Lanes

| lane | purpose | current_session | write_scope | worklog | workspace | status |
|---|---|---|---|---|---|---|
| personal-production-agent | 个人号生产主 Agent；负责宅研社 / 北北ks 的 S0-S9 端到端生产：选题裁判、撞车检测、01c 数据调研、状态卡、正文/证据卡/自检/风控终稿、lint、三图提示词、image2 出图、用户确认、Word 重建、作废文件清理、发布清单、发布后复盘回灌，并在本会话内执行 A1-A6 自审闸门。正文阶段必须继承 `Agents/02-首席主笔Agent.md` 与 `Skills/02/04/05/06/07/style_examples`，不得另起一套 Codex 自建写作流程。所有常规流程从本会话走，不再调用第二终审会话。 | `019ee303-adef-7c72-b9d3-edcb2d36b33a` | `outputs/Codex/`, `codex-agents/personal-production/`, `对标拆解库/品类弹药包/`, `对标拆解库/轻量证据卡_*.md`, `对标拆解库/归档复盘卡_*.md`, read-only: `CLAUDE.md`, `Agents/`, `Skills/`, `生产SOP_全流程.md`, `codex-agents/个人号单会话生产线.md`, `codex-agents/写作前调研模块_家电爆文弹药包.md`, `codex-agents/生产状态卡_模板.md`, `运营方法论/`, `推品逻辑手册_2026.md`, `家电知识库/`, `系统日志.md`, `agent-lanes.md` | `系统日志.md` | `codex-agents/personal-production/`；文章生产：`outputs/Codex/`；成品归档：`projects/` | active / pinned |
| personal-review-agent | 个人号终审 Agent；2026-06-23 起不再作为默认生产闸门。仅在 CEO 单独点名要求专项复审时使用，不参与日常北北ks/宅研社图文生产。 | `019ee2fa-16ab-7860-8c97-f4420c35743a` | `codex-agents/personal-review/`, read-only: `outputs/Codex/`, `projects/`, `系统日志.md`, `agent-lanes.md` | `系统日志.md` | `codex-agents/personal-review/` | on-demand / deprecated for daily production |
| content-writing-agent | 旧内容写作长期会话；职责已并入 `personal-production-agent`。仅作为历史上下文存档，不再接个人号日常生产任务。 | `019ecf9e-bd17-7723-9864-fb15b57a0f84` | read-only unless CEO explicitly reactivates | `系统日志.md` | archived legacy context | merged / archived |
| topic-agent | 旧选题长期会话；职责已升级并更名为 `personal-production-agent`，保留本行仅作迁移说明。 | `019ee303-adef-7c72-b9d3-edcb2d36b33a` | see `personal-production-agent` | `系统日志.md` | see `personal-production-agent` | merged into personal-production-agent |
| image-agent | 旧作图长期会话；职责已并入 `personal-production-agent`。日常不再承担配图执行，也不再承担终审闸门。 | `019ee2fa-16ab-7860-8c97-f4420c35743a` | read-only unless CEO explicitly reactivates | `系统日志.md` | archived legacy context | merged / archived |
| data-review-agent | 旧数据复盘长期会话；个人号复盘职责并入 `personal-production-agent`。公司号复盘仍归 Claude Code / /fupan；本会话仅在 CEO 单独要求做专项数据复盘时启用。 | `019ee2fa-198e-7b40-95a3-5ee6969f2a11` | `codex-agents/data-review/`, `data/`, read-only: `projects/`, `系统日志.md`, `agent-lanes.md` | `系统日志.md` | `codex-agents/data-review/` | on-demand / archived for daily production |
| codex-production | Codex 临时文章生产区；用于未分配到固定 Agent 的一次性 Codex 文章/素材任务 | current local thread as assigned | `outputs/Codex/`, approved system files when explicitly requested | `系统日志.md` | `outputs/Codex/`，文件夹固定保留 | available |

---

## 注册模板

新增 Agent 时复制一行并填写：

```markdown
| lane-id | 这个 Codex Agent 只负责什么，不负责什么 | `Codex thread id` | `允许写入的路径` | `系统日志.md` | `codex-agents/<agent-id>/` | active |
```

登记后，还需要：

- 如果是 Codex 线程：用 `set_thread_title` 命名为清晰岗位名。
- 如果是长期 Agent：用 `set_thread_pinned` 置顶。
- 如果废弃：状态改为 `archived`，并用 `set_thread_archived` 归档线程。
