#!/bin/bash
# ContentFleet · PostToolUse Hook: T3 文章自动质检
# 当 Claude Code Agent 写入 T3_*.md 文件时自动触发 lint_article.py
#
# 从 stdin 读取 Claude Code 传入的 JSON，提取文件路径，
# 如果文件匹配 outputs/T3_*.md 或 T3_头条.md，执行质检并返回结果。

set -e

# 读取 stdin JSON
INPUT=$(cat)

# 提取文件路径
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# Write tool: file_path in tool_input
fp = data.get('tool_input', {}).get('file_path', '')
print(fp)
" 2>/dev/null)

# 检查是否是 T3 文件
if [[ "$FILE_PATH" == *"/T3_"*".md" ]] || [[ "$FILE_PATH" == *"outputs/T3_"*".md" ]]; then
    # 执行质检
    LINT_RESULT=$(python3 "$CLAUDE_PROJECT_DIR/Scripts/lint_article.py" "$FILE_PATH" --json 2>/dev/null || true)

    if [ -z "$LINT_RESULT" ]; then
        exit 0
    fi

    # 解析结果
    PASSED=$(echo "$LINT_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('true' if d['passed'] else 'false')" 2>/dev/null)
    ERROR_COUNT=$(echo "$LINT_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['error_count'])" 2>/dev/null)
    WARNING_COUNT=$(echo "$LINT_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['warning_count'])" 2>/dev/null)
    AUTO_FIXABLE=$(echo "$LINT_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['auto_fixable'])" 2>/dev/null)

    if [ "$PASSED" = "false" ]; then
        # 有 ERROR — 向 Claude 提供上下文信息，提示需要修复
        ERRORS_DETAIL=$(echo "$LINT_RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for e in d['errors'][:10]:
    line = f\"L{e['line']}\" if e['line'] > 0 else '全文'
    print(f'  [{line}] {e[\"msg\"]}')
" 2>/dev/null)

        # 输出 JSON 给 Claude Code
        python3 -c "
import json
output = {
    'hookSpecificOutput': {
        'hookEventName': 'PostToolUse',
        'additionalContext': '''⚠️ T3 质检未通过（lint_article.py）
发现 ${ERROR_COUNT} 个 ERROR、${WARNING_COUNT} 个 WARNING，其中 ${AUTO_FIXABLE} 处可自动修复。

ERROR 详情:
${ERRORS_DETAIL}

请修复以上问题后重新写入文件。
可运行 python3 Scripts/lint_article.py \"${FILE_PATH}\" --fix 自动修复绝对化用语。'''
    }
}
print(json.dumps(output, ensure_ascii=False))
"
        exit 0  # exit 0 but with context, so Claude sees the issues
    else
        # 通过 — 给 Claude 正面反馈
        python3 -c "
import json
output = {
    'hookSpecificOutput': {
        'hookEventName': 'PostToolUse',
        'additionalContext': '✅ T3 质检通过（lint_article.py）：无绝对化用语、无感叹号、标题长度合规、字数达标。可提交 T4 审查。'
    }
}
print(json.dumps(output, ensure_ascii=False))
"
        exit 0
    fi
fi

# 非 T3 文件，不做任何处理
exit 0
