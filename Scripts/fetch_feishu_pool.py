#!/usr/bin/env python3
"""Fetch Feishu 爆款池 data and output formatted markdown for 选题情报官 Agent."""

import json, subprocess, sys

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
LARK = "/opt/homebrew/bin/lark-cli"

def lark_query(table_id, fields=None, limit=200):
    cmd = [LARK, "base", "+record-list", "--base-token", BASE_TOKEN, "--table-id", table_id, "--format", "json", "--limit", str(limit)]
    if fields:
        for f in fields:
            cmd += ["--field-id", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error querying {table_id}: {r.stderr}", file=sys.stderr)
        return []
    return json.loads(r.stdout)["data"]["data"]

def fetch_formulas():
    """Fetch 选题公式库 (tblExwpbnp875Vnh)."""
    # Fields order: ID, 来源文章, 生命周期, 使用次数, 公式模板, 标题结构, 最近复盘结论, 适用品类, 历史表现, 失效信号, 钩子要素, 公式名称, 适合账号, 适用类型, 可用性
    rows = lark_query("tblExwpbnp875Vnh")
    formulas = []
    for r in rows:
        formulas.append({
            "id": r[0],
            "lifecycle": r[2][0] if r[2] else "?",
            "usage": r[3] or 0,
            "template": r[4] or "",
            "structure": r[5] or "",
            "categories": r[7] or [],
            "perf": r[8] or "",
            "hooks": r[10] or "",
            "name": r[11] or "",
            "accounts": r[12] or [],
            "types": r[13] or [],
            "status": r[14][0] if r[14] else "活跃",
        })
    return formulas

def fetch_articles():
    """Fetch 文章追踪 (tblA8dT3x3bdOF9Y)."""
    fields = ["ID", "文章标题", "发布账号", "展现量", "阅读量", "CTR(%)", "标题结构模板",
              "表现分层", "是否限流", "产品品类", "收藏数", "评论数", "互动率(%)"]
    rows = lark_query("tblA8dT3x3bdOF9Y", fields=fields, limit=200)
    articles = []
    for r in rows:
        articles.append({
            "id": r[0],
            "title": r[1] or "",
            "account": r[2][0] if r[2] else "",
            "impressions": r[3] or 0,
            "reads": r[4] or 0,
            "ctr": r[5] or 0,
            "structure": r[6][0] if r[6] else "其他",
            "tier": r[7][0] if r[7] else "",
            "blocked": r[8][0] if r[8] else "正常",
            "category": r[9][0] if r[9] else "",
            "saves": r[10] or 0,
            "comments": r[11] or 0,
            "engagement": r[12] or 0,
        })
    return sorted(articles, key=lambda x: x["impressions"], reverse=True)

def build_matrix(formulas, articles):
    """Build 品类×结构验证矩阵."""
    cats = sorted(set(a["category"] for a in articles if a["category"]))
    structs = [f["name"] for f in formulas]

    matrix = {}
    for s in structs:
        matrix[s] = {}
        for c in cats:
            matching = [a for a in articles if a["structure"] == s and a["category"] == c]
            if not matching:
                matrix[s][c] = {"status": "⬜未消费", "best": 0, "count": 0}
            else:
                best = max(a["impressions"] for a in matching)
                cnt = len(matching)
                tier = max((a["tier"] for a in matching), key=lambda t: {"爆款": 4, "点击强": 3, "推荐强": 2, "一般": 1}.get(t, 0))
                matrix[s][c] = {"status": "🟢" + tier, "best": best, "count": cnt}
    return cats, structs, matrix

def main():
    formulas = fetch_formulas()
    articles = fetch_articles()
    cats, structs, matrix = build_matrix(formulas, articles)

    lines = []
    lines.append("# 飞书爆款池数据快照")
    lines.append(f"> 拉取时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 文章追踪: {len(articles)}篇 | 选题公式库: {len(formulas)}条")
    lines.append("")

    # Section 1: 选题公式库
    lines.append("## 一、选题公式库（从爆款提炼的可复用结构）")
    lines.append("")
    for f in formulas:
        if f["status"] == "冻结" or f["lifecycle"] in ("冻结", "降权"):
            continue
        lines.append(f"### {f['id']} · {f['name']}")
        lines.append(f"- **公式**: {f['template']}")
        lines.append(f"- **结构**: {f['structure']}")
        lines.append(f"- **钩子**: {f['hooks']}")
        lines.append(f"- **适用品类**: {', '.join(f['categories'])}")
        lines.append(f"- **适合账号**: {', '.join(f['accounts']) if f['accounts'] else '不限'}")
        lines.append(f"- **适用类型**: {', '.join(f['types'])}")
        lines.append(f"- **历史表现**: {f['perf']}")
        lines.append("")

    # Section 2: TOP爆款文章
    lines.append("## 二、文章追踪 TOP30（按展现量排序）")
    lines.append("")
    lines.append("| # | 标题 | 账号 | 展现 | CTR | 结构 | 分层 | 品类 | 限流 |")
    lines.append("|---|------|------|------|-----|------|------|------|------|")
    for i, a in enumerate(articles[:30], 1):
        lines.append(f"| {i} | {a['title'][:28]} | {a['account']} | {a['impressions']:,} | {a['ctr']}% | {a['structure']} | {a['tier']} | {a['category']} | {a['blocked']} |")

    # Section 3: 限流文章
    blocked = [a for a in articles if a["blocked"] in ("疑似限流", "确认限流")]
    if blocked:
        lines.append("")
        lines.append("## 三、限流文章（反面教材）")
        lines.append("")
        lines.append("| 标题 | 展现 | 结构 | 限流状态 |")
        lines.append("|------|------|------|---------|")
        for a in blocked:
            lines.append(f"| {a['title'][:35]} | {a['impressions']:,} | {a['structure']} | {a['blocked']} |")

    # Section 4: 品类×结构验证矩阵
    lines.append("")
    lines.append("## 四、品类×结构验证矩阵")
    lines.append("")
    header = "| 结构 | " + " | ".join(cats) + " |"
    sep = "|------|" + "|".join(["------"] * len(cats)) + "|"
    lines.append(header)
    lines.append(sep)
    for s in structs:
        cells = []
        for c in cats:
            m = matrix[s].get(c, {"status": "⬜未消费", "best": 0, "count": 0})
            if m["count"] == 0:
                cells.append("⬜")
            else:
                cells.append(f"{m['status']}({m['best']:,})")
        lines.append(f"| {s} | " + " | ".join(cells) + " |")

    # Section 5: 空白机会
    lines.append("")
    lines.append("## 五、未消费空白机会（高确定性选题来源）")
    lines.append("")
    blanks = []
    for s in structs:
        f = next((x for x in formulas if x["name"] == s), None)
        if not f:
            continue
        for c in cats:
            m = matrix[s].get(c, {"status": "⬜未消费", "count": 0})
            if m["count"] == 0 and c in f["categories"]:
                blanks.append({"structure": s, "category": c, "template": f["template"], "hooks": f["hooks"]})
    if blanks:
        for b in blanks:
            lines.append(f"- **{b['structure']}** × **{b['category']}** → 钩子: {b['hooks']} | 模板: {b['template']}")
    else:
        lines.append("> 所有品类×结构组合均已有内容，建议从表现最佳的组合中找新角度")

    print("\n".join(lines))

if __name__ == "__main__":
    main()
