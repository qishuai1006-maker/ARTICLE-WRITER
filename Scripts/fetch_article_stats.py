#!/usr/bin/env python3
"""Fetch a single article's full stats + review-attribution fields from Feishu.

Usage:
  python3 fetch_article_stats.py <toutiao_url | article_id | title>

Matches ONE record by priority: 头条文章ID exact > 文章链接 contains ID >
文章标题 exact > 文章标题 fuzzy contains. Prints record_id + all performance
data + current review-attribution values (the fields /fupan fills back).

Column index is built from the `fields` array lark-cli actually returns (NOT
from input order) — passing many --field-id flags can reorder or drop columns.

Single-file, stdlib only, shells out to lark-cli. Read-only.
"""
import json
import re
import subprocess
import sys

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
LARK = "/opt/homebrew/bin/lark-cli"
TBL_ARTICLES = "tblA8dT3x3bdOF9Y"   # 文章追踪表

# Request these fields; actual returned columns may differ -> index dynamically.
REQUEST_FIELDS = [
    "ID", "文章标题", "文章链接", "头条文章ID", "发布账号", "产品品类",
    "标题结构模板", "表现分层", "是否限流", "发布日期", "标题字数",
    "展现量", "阅读量", "CTR(%)", "完读率(%)", "收藏数", "评论数",
    "点赞数", "转发量", "分享量", "互动率(%)", "粉丝展现量",
    "粉丝阅读量", "平均阅读时长(s)",
    "主因归因", "辅因归因", "下次动作", "可复用点", "问题点",
    "关联公式", "建议改写标题", "复盘日期", "限流原因", "当前阶段",
]

REVIEW_FIELDS = ["主因归因", "辅因归因", "下次动作", "可复用点", "问题点",
                 "关联公式", "建议改写标题", "复盘日期", "限流原因"]
DATA_FIELDS = ["展现量", "阅读量", "CTR(%)", "完读率(%)", "收藏数", "评论数",
               "点赞数", "转发量", "分享量", "互动率(%)", "粉丝展现量",
               "粉丝阅读量", "平均阅读时长(s)"]


def lark_query(fields, limit=300):
    cmd = [LARK, "base", "+record-list", "--base-token", BASE_TOKEN,
           "--table-id", TBL_ARTICLES, "--format", "json", "--limit", str(limit)]
    for f in fields:
        cmd += ["--field-id", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] lark-cli: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    obj = json.loads(r.stdout)
    d = obj["data"]
    return d["data"], d.get("record_id_list", []), d.get("fields", [])


def cell(v):
    """Normalize a lark cell: select/multi-select lists -> '/'-joined str."""
    if isinstance(v, list):
        return "/".join(str(x) for x in v)
    return "" if v is None else v


def extract_id(s):
    m = re.search(r"i(\d{15,})", s or "")
    return m.group(1) if m else None


def match(rows, rec_ids, I, query):
    qid = extract_id(query) or (query.strip() if query.strip().isdigit() else None)
    qtitle = query.strip()
    hits = []
    for row, rid in zip(rows, rec_ids):
        title = cell(row[I["文章标题"]])
        link = cell(row[I["文章链接"]])
        aid = cell(row[I["头条文章ID"]]) if "头条文章ID" in I else ""
        link_id = extract_id(link)
        if qid and (aid == qid or link_id == qid):
            hits.append(("头条ID精确", rid, row))
        elif qtitle and qtitle == title:
            hits.append(("标题精确", rid, row))
        elif qtitle and qtitle in title:
            hits.append(("标题模糊", rid, row))
    return hits


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_article_stats.py <toutiao_url | article_id | title>",
              file=sys.stderr)
        sys.exit(2)
    query = " ".join(sys.argv[1:]).strip()

    rows, rec_ids, col_names = lark_query(REQUEST_FIELDS)
    # Build index from ACTUAL returned columns, not request order.
    I = {name: i for i, name in enumerate(col_names)}
    missing = [f for f in REQUEST_FIELDS if f not in I]
    if missing:
        print(f"[警告] 飞书未返回这些字段（将显示空）：{missing}")
    print(f"[拉取] 文章追踪 {len(rows)} 篇 | 返回字段 {len(col_names)} 个")

    hits = match(rows, rec_ids, I, query)
    if not hits:
        print(f"[未命中] 输入「{query}」未匹配任何文章。")
        print("        检查链接/标题是否准确，或该篇尚未登记飞书文章追踪表。")
        sys.exit(1)
    if len(hits) > 1:
        print(f"[多命中] {len(hits)} 篇匹配，请用更精确的链接或标题：")
        for m, rid, row in hits:
            print(f"  - [{m}] rec={rid} | {cell(row[I['文章标题']])[:40]} | {cell(row[I['文章链接']])}")
        sys.exit(1)

    def g(name):
        return cell(row[I[name]]) if name in I else "(字段未返回)"

    method, rid, row = hits[0]
    print(f"\n[匹配] {method} | record_id={rid}")
    print(f"[标题] {g('文章标题')}")
    print(f"[账号] {g('发布账号')} | [品类] {g('产品品类')} | [发布] {g('发布日期')}")
    print(f"[链接] {g('文章链接')}")

    print("\n== 表现数据 ==")
    for k in DATA_FIELDS:
        print(f"  {k}: {g(k)}")
    print(f"[分层] {g('表现分层')} | [限流] {g('是否限流')} | [结构] {g('标题结构模板')}")

    print("\n== 当前归因（/fupan 待填，空=未复盘）==")
    for k in REVIEW_FIELDS:
        v = g(k)
        print(f"  {k}: {v if v else '(空)'}")

    print(f"\n[写回键] record_id = {rid}  ← 供 writeback_review.py 写回归因字段")


if __name__ == "__main__":
    main()
