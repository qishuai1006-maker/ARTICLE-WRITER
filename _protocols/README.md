# Super Writer · _protocols/

> **目的**：上下文管理、Agent 接力、跨会话恢复的所有协议
> **最后更新**：2026-06-11

## 目录内容

| 文件 | 用途 |
| --- | --- |
| `README.md` | 本文件（入口） |
| `naming_convention.md` | 文件名/目录命名规范 |
| `handoff_template.yaml` | T1→T2→T3→T4 接力 YAML 模板 |
| `handoff_template_README.md` | YAML 字段详细说明 |
| `cross_session_resume.md` | 跨会话恢复指南 + 应急命令 |

## 核心设计原则

1. **规则在文件系统，对话只 cat 引用**
2. **每 T 一对话**（T1/T1.5/T2/T3/T4 各开新会话）
3. **中间产物全落盘**（test_run/ 每篇独立文件）
4. **YAML 接力接口**（双 Agent 信息不丢失）
5. **5 分钟恢复承诺**（任何断点都能快速恢复）

## 使用流程

```
新会话开始
 ↓
读 test_run/_handoff/[最新].yaml（如果有）
 ↓
读 test_run/选题_[最新].md 看进度
 ↓
按 prompts/[当前阶段]/[对应].md 跑当前 T
 ↓
完成后追加进度 + 写 YAML
 ↓
git commit
 ↓
开新会话跑下一 T
```