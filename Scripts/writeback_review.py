#!/usr/bin/env python3
"""Write review-attribution fields back to a Feishu article record.

Usage:
  python3 writeback_review.py <record_id> 字段=值 ...

Example:
  python3 writeback_review.py recXXXX 主因归因=标题强点击 下次动作=复用 \
    复盘日期=2026-06-18 可复用点="标题钩子强，正文承接稳"

Field rules:
  - select (主因归因/辅因归因/下次动作): MUST be a preset option (validated).
  - 复盘日期 (datetime): accept YYYY-MM-DD, auto-convert to epoch ms.
  - text (可复用点/问题点/建议改写标题/限流原因): free text.
  - 关联公式 (link): NOT handled here — needs formula-table record_id; /fupan
    drives 公式库 lifecycle via the formula table, not this field.

Single-file, stdlib only, shells out to lark-cli record-batch-update.
"""
import json
import subprocess
import sys
from datetime import datetime

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
LARK = "/opt/homebrew/bin/lark-cli"
TBL_ARTICLES = "tblA8dT3x3bdOF9Y"

# Preset select options (from +field-search-options). Do NOT pass other values.
SELECT_OPTIONS = {
    "主因归因": ["标题强点击", "平台愿意推", "内容承接强", "选题过窄", "标题弱",
              "疑似限流", "时效失配", "品类疲劳", "公式可复用", "公式需降权"],
    "辅因归因": ["标题强点击", "平台愿意推", "内容承接强", "选题过窄", "标题弱",
              "疑似限流", "时效失配", "品类疲劳", "公式可复用", "公式需降权"],
    "下次动作": ["复用", "改标题再试", "换账号试", "降权", "冻结", "淘汰", "降权观察"],
}
TEXT_FIELDS = ["可复用点", "问题点", "建议改写标题", "限流原因"]
ALLOWED = set(SELECT_OPTIONS) | set(TEXT_FIELDS) | {"复盘日期"}


def to_ts(val):
    """YYYY-MM-DD [HH:MM] -> epoch ms (Feishu datetime)."""
    val = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(val, fmt).timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"复盘日期格式应为 YYYY-MM-DD，收到「{val}」")


def build_patch(pairs):
    patch = {}
    for k, v in pairs:
        if k not in ALLOWED:
            print(f"[拒绝] 字段「{k}」不在复盘白名单。允许：{sorted(ALLOWED)}",
                  file=sys.stderr)
            sys.exit(1)
        if k in SELECT_OPTIONS:
            if v not in SELECT_OPTIONS[k]:
                print(f"[拒绝] 「{k}」必须选预设值。\n  选项：{SELECT_OPTIONS[k]}",
                      file=sys.stderr)
                sys.exit(1)
            patch[k] = v
        elif k == "复盘日期":
            patch[k] = to_ts(v)
        else:
            patch[k] = v
    return patch


def main():
    if len(sys.argv) < 3:
        print("Usage: writeback_review.py <record_id> 字段=值 ...", file=sys.stderr)
        sys.exit(2)
    rid = sys.argv[1]
    pairs = []
    for arg in sys.argv[2:]:
        if "=" not in arg:
            print(f"[跳过] 无法解析「{arg}」（需 字段=值）", file=sys.stderr)
            continue
        k, v = arg.split("=", 1)
        pairs.append((k.strip(), v.strip()))
    patch = build_patch(pairs)
    if not patch:
        print("[错误] 没有可写字段", file=sys.stderr)
        sys.exit(1)

    payload = {"record_id_list": [rid], "patch": patch}
    cmd = [LARK, "base", "+record-batch-update", "--base-token", BASE_TOKEN,
           "--table-id", TBL_ARTICLES, "--json",
           json.dumps(payload, ensure_ascii=False)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[失败] {r.stderr.strip() or r.stdout.strip()}", file=sys.stderr)
        sys.exit(1)
    print(f"[写回成功] record={rid}")
    for k, v in patch.items():
        shown = v if k != "复盘日期" else f"{v}(ms)"
        print(f"  {k} = {shown}")


if __name__ == "__main__":
    main()
