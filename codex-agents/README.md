# Codex Agents Workspace

本目录只放 Codex 长期 Agent 的内部过程材料，避免和文章生产内容混用。

## 目录边界

| path | 用途 |
|---|---|
| `topic-agent/` | 选题 Agent 工作区 |
| `content-writing/` | 内容写作 Agent 内部过程材料；正式文章内容写入 `outputs/Codex/` |
| `image-agent/` | 作图 Agent 内部过程材料；正式图片/配图卡写入 `outputs/Codex/` |
| `data-review/` | 数据复盘 Agent 工作区 |
| `personal-production/` | 个人号单会话生产主 Agent 工作区（选题、数据调研、正文、自审、配图、Word、发布清单、复盘） |
| `personal-visual/` | 历史视觉交付工作区；日常职责已并入 `personal-production-agent` |
| `CODEX_多Agent协作闭环方案.md` | Codex 四个长期 Agent 的协作状态机、交接卡和自动化闭环方案 |
| `个人号单会话生产线.md` | 宅研社 / 北北ks 的单会话生产职责和全流程执行版 |
| `个人号两会话生产线.md` | 历史入口，已停用并指向单会话生产线 |
| `生产状态卡_模板.md` | 每篇 Codex 图文生产必须复制到文章目录的共享状态卡模板 |

## 规则

1. 文章生产内容统一写入 `outputs/Codex/`，并长期保留这个文件夹。
2. 归档时只移动 `outputs/Codex/` 里的具体文章内容到根目录 `projects/`，不要移动或删除 `outputs/Codex/` 文件夹本身。
3. `codex-agents/` 只放 Agent 内部过程材料；成品/历史文章统一归档到根目录 `projects/`。
4. 其他软件或非 Codex 智能体不需要接入本目录。
5. Agent 职责、会话 ID、写入范围以根目录 `agent-lanes.md` 为准。
6. 做完影响系统协作的改动后，仍需登记 `系统日志.md`。
7. Codex 多 Agent 协作按 `CODEX_多Agent协作闭环方案.md` 执行；个人号日常生产按 `个人号单会话生产线.md` 执行；每篇进入生产时，先从 `生产状态卡_模板.md` 复制一份到文章目录并持续更新。
8. 数据复盘时必须审计知识库召回：状态卡/证据卡是否含 L1/L2/L4/L3，是否至少有一个知识库硬事实进入标题/首屏/前 300 字，是否形成主证据对象；低展现稿先查闸门A，再查标题和封面。
