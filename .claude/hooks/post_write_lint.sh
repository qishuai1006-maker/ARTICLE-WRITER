#!/bin/bash
# Super Writer v4.1 · PostToolUse Hook: 终稿自动质检（lint + 标题兑现）
# 触发：Write 匹配 outputs/03_风控主编终稿*.md
# ① lint_quick_article.py 基本质检（禁词/密度/标题长度/证据卡）
# ② check_title_delivery.py 标题兑现检查（2026-06-22 新增）
#    堵"标题承诺空洞化"：0621 空调篇 03 删 UNSURE 后标题「贵239元」兑现不了，
#    lint 照样 PASS，标题钩子落地空空——lint 只数正文有什么，不查标题要什么。
# 容错：故意不 set -e，任一检查失败不阻断写入。

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
fp = data.get('tool_input', {}).get('file_path', '')
print(fp)
" 2>/dev/null)

# 只处理四棒终稿
if [[ "$FILE_PATH" != *"03_风控主编终稿"*".md" ]]; then
    exit 0
fi

# 两份质检结果落临时文件，避免 JSON 在 bash 变量里的转义问题
LINT_FILE=$(mktemp 2>/dev/null || echo "/tmp/sw_lint_$$.json")
TITLE_FILE=$(mktemp 2>/dev/null || echo "/tmp/sw_title_$$.json")
python3 "$CLAUDE_PROJECT_DIR/Scripts/lint_quick_article.py" "$FILE_PATH" --json > "$LINT_FILE" 2>/dev/null || true
python3 "$CLAUDE_PROJECT_DIR/Scripts/check_title_delivery.py" "$FILE_PATH" --json > "$TITLE_FILE" 2>/dev/null || true

python3 -c "
import json
lint, title = {}, {}
try:
    lint = json.load(open('$LINT_FILE'))
except Exception:
    pass
try:
    title = json.load(open('$TITLE_FILE'))
except Exception:
    pass

lines = []

# --- lint 报告 ---
lw = lint.get('warning_count', 0)
if lint:
    if lint.get('passed'):
        lines.append(f'✅ lint 通过（0 ERROR，{lw} WARNING）')
    else:
        le = lint.get('error_count', 0)
        lines.append(f'⛔ lint 未通过（{le} ERROR，{lw} WARNING）:')
        for e in (lint.get('errors') or [])[:10]:
            ln = f\"L{e['line']}\" if e.get('line', 0) > 0 else '全文'
            lines.append(f'  [{ln}] {e[\"message\"]}')

# --- 标题兑现报告 ---
tw = title.get('warning_count', 0)
if title:
    if title.get('passed') and tw == 0:
        lines.append('✅ 标题兑现通过：标题承诺全部在正文兑现')
    else:
        te = title.get('error_count', 0)
        tag = '⛔' if te else '⚠️'
        lines.append(f'{tag} 标题兑现检查（{te} ERROR，{tw} WARNING）:')
        for e in (title.get('errors') or [])[:10]:
            lines.append(f'  [{e[\"code\"]}] {e[\"message\"]}')
        for w in (title.get('warnings') or [])[:5]:
            lines.append(f'  [{w[\"code\"]}] {w[\"message\"]}')
        if te > 0:
            codes = {e['code'] for e in (title.get('errors') or [])}
            if 'hard_grey_word' in codes:
                lines.append('  修法[hard_grey]: 买了必后悔/全家遭殃等纯恐吓强迫词无信息能锚定, 直接换标题, 用 Skills/06 §6.2 三种替代技术(信息权威感/真实悬念/精准场景代入)重写, 不是词表替换;')
            if codes & {'digit_missing', 'compare_pledge_broken', 'unsure_leak', 'model_missing'}:
                lines.append('  修法[兑现缺口]: 回 01c 补真实数据让正文兑现标题, 或换标题主线; 不准用弱化标题(删数字/型号)逃避。')

ctx = chr(10).join(lines) if lines else '(质检无输出)'
out = {'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': ctx}}
print(json.dumps(out, ensure_ascii=False))
"

rm -f "$LINT_FILE" "$TITLE_FILE" 2>/dev/null
exit 0
