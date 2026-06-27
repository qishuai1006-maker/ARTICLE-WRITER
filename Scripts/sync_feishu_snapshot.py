#!/usr/bin/env python3
"""Sync Feishu bitable data → Super Writer flywheel calibration.

Pulls 选题公式库 + 文章追踪 from Feishu via lark-cli, computes per-formula
real stats (count / avg CTR / tier distribution / suggested lifecycle), and
emits a snapshot report. Run weekly to keep 运营方法论/02_爆款公式库.md calibrated.

Single-file, stdlib only, shells out to lark-cli (no external deps).
"""
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
LARK = "/opt/homebrew/bin/lark-cli"
TBL_FORMULAS = "tblExwpbnp875Vnh"   # 选题公式库
TBL_ARTICLES = "tblA8dT3x3bdOF9Y"   # 文章追踪

# 文章追踪字段（field-id 中文，已验证可用）
ART_FIELDS = ["ID", "文章标题", "发布账号", "展现量", "阅读量", "CTR(%)",
              "标题结构模板", "表现分层", "是否限流", "产品品类", "收藏数", "评论数", "互动率(%)"]


def lark_query(table_id, fields=None, limit=300):
    cmd = [LARK, "base", "+record-list", "--base-token", BASE_TOKEN,
           "--table-id", table_id, "--format", "json", "--limit", str(limit)]
    if fields:
        for f in fields:
            cmd += ["--field-id", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] query {table_id}: {r.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(r.stdout)["data"]["data"]
    except (json.JSONDecodeError, KeyError):
        print(f"[ERROR] parse {table_id}: {r.stdout[:200]}", file=sys.stderr)
        return []


def parse_articles():
    rows = lark_query(TBL_ARTICLES, fields=ART_FIELDS, limit=300)
    out = []
    for r in rows:
        try:
            out.append({
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
            })
        except (IndexError, TypeError):
            continue
    return out


def parse_formulas():
    """公式库按原生列顺序解析（同旧 fetch_feishu_pool.py）。"""
    rows = lark_query(TBL_FORMULAS, limit=100)
    out = []
    for r in rows:
        try:
            out.append({
                "id": r[0],
                "lifecycle": r[2][0] if r[2] else "?",
                "usage": r[3] or 0,
                "template": r[4] or "",
                "structure": r[5] or "",
                "perf": r[8] or "",
                "hooks": r[10] or "",
                "name": r[11] or "",
                "accounts": r[12] or [],
                "status": r[14][0] if r[14] else "活跃",
            })
        except (IndexError, TypeError):
            continue
    return out


def suggest_lifecycle(count, avg_ctr, tier_dist, blocked_ratio):
    """根据真实数据建议生命周期（与 02_爆款公式库 5 态对齐）。"""
    strong = tier_dist.get("爆款", 0) + tier_dist.get("点击强", 0) + tier_dist.get("承接强", 0)
    weak = tier_dist.get("普通", 0) + tier_dist.get("疑似限流", 0)
    if count == 0:
        return "新公式(未消费)"
    if count >= 2 and strong / count >= 0.5:
        return "活跃"
    if blocked_ratio >= 0.5 or (count >= 2 and weak / count >= 0.7):
        return "降权"
    if count >= 2 and weak / count >= 0.5:
        return "降权(疲劳)"
    if count <= 1:
        return "验证中"
    return "活跃"


def main():
    articles = parse_articles()
    formulas = parse_formulas()
    print(f"[拉取] 文章追踪 {len(articles)} 篇 | 选题公式库 {len(formulas)} 条\n")

    # 按标题结构分组统计
    groups = defaultdict(list)
    for a in articles:
        groups[a["structure"]].append(a)

    calib = []
    for struct, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        n = len(items)
        avg_ctr = sum(i["ctr"] for i in items) / n
        avg_imp = sum(i["impressions"] for i in items) / n
        tier_dist = defaultdict(int)
        for i in items:
            if i["tier"]:
                tier_dist[i["tier"]] += 1
        blocked = sum(1 for i in items if i["blocked"] in ("疑似限流", "确认限流"))
        blocked_ratio = blocked / n
        life = suggest_lifecycle(n, avg_ctr, dict(tier_dist), blocked_ratio)
        tier_str = "/".join(f"{k}{v}" for k, v in sorted(tier_dist.items(), key=lambda x: -x[1]))
        calib.append({
            "structure": struct, "n": n, "avg_ctr": round(avg_ctr, 2),
            "avg_imp": int(avg_imp), "tier": tier_str,
            "blocked": blocked, "life": life,
        })

    # 控制台：校准表（核心）
    print("=" * 90)
    print("公式库校准表（按真实飞书数据 · 直接用于更新 02_爆款公式库.md）")
    print("=" * 90)
    print(f"{'结构':<14}{'篇数':>4}{'均CTR':>7}{'均展现':>9}  {'分层分布':<22}{'限流':>4}  建议生命周期")
    print("-" * 90)
    for c in calib:
        print(f"{c['structure']:<14}{c['n']:>4}{c['avg_ctr']:>6}%{c['avg_imp']:>9,}  {c['tier']:<22}{c['blocked']:>4}  {c['life']}")

    # TOP 爆款 + 限流反面
    by_imp = sorted(articles, key=lambda x: -x["impressions"])
    print("\n" + "=" * 90)
    print("TOP 10 爆款（按展现量）")
    print("=" * 90)
    for i, a in enumerate(by_imp[:10], 1):
        print(f"{i:>2}. [{a['tier'] or '?'}] {a['impressions']:>7,}展现 {a['ctr']:>5}% | {a['account']}·{a['category']} | {a['structure']} | {a['title'][:34]}")

    blocked_list = [a for a in articles if a["blocked"] in ("疑似限流", "确认限流")]
    print(f"\n限流反面教材：{len(blocked_list)} 篇")
    for a in blocked_list[:8]:
        print(f"  - {a['impressions']:>6,}展现 | {a['structure']} | {a['title'][:40]}")

    # 写完整快照到文件
    ts = datetime.now().strftime("%Y%m%d")
    out_path = f"data/feishu_snapshot_{ts}.md"
    L = [f"# 飞书数据快照（飞轮校准用）",
         f"> 拉取时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 文章 {len(articles)} 篇 | 公式 {len(formulas)} 条\n",
         "## 一、公式库校准表", "",
         "| 标题结构 | 真实篇数 | 平均CTR | 平均展现 | 分层分布 | 限流篇 | 建议生命周期 |",
         "|---|---|---|---|---|---|---|"]
    for c in calib:
        L.append(f"| {c['structure']} | {c['n']} | {c['avg_ctr']}% | {c['avg_imp']:,} | {c['tier']} | {c['blocked']} | {c['life']} |")
    L += ["\n## 二、TOP 15 爆款", "", "| # | 分层 | 展现 | CTR | 账号 | 品类 | 结构 | 标题 |",
          "|---|---|---|---|---|---|---|---|"]
    for i, a in enumerate(by_imp[:15], 1):
        L.append(f"| {i} | {a['tier']} | {a['impressions']:,} | {a['ctr']}% | {a['account']} | {a['category']} | {a['structure']} | {a['title'][:30]} |")
    if blocked_list:
        L += ["\n## 三、限流反面教材", "", "| 展现 | 结构 | 品类 | 标题 |", "|---|---|---|---|"]
        for a in blocked_list:
            L.append(f"| {a['impressions']:,} | {a['structure']} | {a['category']} | {a['title'][:36]} |")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\n[完成] 完整快照已写入 {out_path}")


if __name__ == "__main__":
    main()
