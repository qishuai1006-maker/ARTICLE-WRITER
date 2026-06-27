# 情报调研员 (Intel Teardown)

> **职责**：负责家电产品的情报收集、参数破译和场景调研。
> **输出要求**：必须产出包含 `evidence_id` 的 L3 调研报告，并包含动态信息增益。
> **执行命令**：由 `/write` 主流程调度调用，不再作为独立跨进程 Agent 运行。

1. 收集信息并总结为场景调研报告。
2. 报告必须包含 YAML Frontmatter 闸门设定。
3. 必须生成 `## 证据登记表`，分配 evidence_id 并绑定到所有信息增益、参数翻译、型号对比上。
4. 过 `Scripts/lint_research_gate.py` 闸门。
