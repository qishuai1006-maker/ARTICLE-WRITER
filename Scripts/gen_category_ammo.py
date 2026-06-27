#!/usr/bin/env python3
"""Generate per-category 「弹药包」(ammo packs) from Feishu article tracking.

For each product category, emit a sniper-pack md that Agent 02 reads BEFORE
writing that category: TOP爆款样本(学钩子) + 限流反面(避开) + 有效公式 +
未消费的活跃公式(机会). Precision-first:少而精,不是全量倾倒.

Run weekly (or before writing a category): python3 Scripts/gen_category_ammo.py
Output: 对标拆解库/品类弹药包/{品类}.md + 00_索引.md
Single-file, stdlib only, shells out to lark-cli.
"""
import json
import subprocess
import sys
import os
from collections import defaultdict
from datetime import datetime

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
LARK = "/opt/homebrew/bin/lark-cli"
TBL = "tblA8dT3x3bdOF9Y"
OUT_DIR = "对标拆解库/品类弹药包"
ART_FIELDS = ["ID", "文章标题", "发布账号", "展现量", "阅读量", "CTR(%)",
              "标题结构模板", "表现分层", "是否限流", "产品品类", "收藏数", "评论数"]

# 活跃公式（来自 02_爆款公式库 v2.1，用于算"未消费机会"）
ACTIVE_FORMULAS = ["踩坑顿悟型", "内幕视角型", "多品牌对决型", "对比选择型", "反问悬念型"]

# 每个结构的钩子要素（TOP样本"学什么"列 + 公式提示）
STRUCT_HOOKS = {
    "踩坑顿悟型": "经历次数+悟了+具体损失金额+强动作(白送也别装)",
    "内幕视角型": "老炮人设+行业内幕+真实差距结论(揭秘式,非否定式)",
    "多品牌对决型": "多品牌横向+各自优劣+场景适配",
    "对比选择型": "A vs B 核心维度+人群适配+具体数字",
    "反问悬念型": "反问+认知反转+比喻降维",
    "内幕避坑型": "痛点钩子+避坑清单+具体型号(别只给泛指南)",
    "价格段推荐型": "按预算分档+每档首推型号+决策口诀",
    "趋势判断型": "X vs Y 谁成标准+被忽略的行业变量",
    "型号推荐型": "这N款+口碑+不后悔(带人群边界)",
    "时效攻略型": "节点+具体可操作动作(非空洞预测)",
    "教程排障型": "怎么用/检查步骤+省钱省事利益",
    "品牌锚点型": "⚠️均CTR2%弱,慎用",
    "全景指南型": "⛔实测限流,禁用",
    "人群细分型": "⚠️实测限流",
    "反常识型": "不是A是B(非家电慎用)",
    "其他": "结构未标注,需回标",
}


def lark_query(fields=None, limit=300):
    cmd = [LARK, "base", "+record-list", "--base-token", BASE_TOKEN,
           "--table-id", TBL, "--format", "json", "--limit", str(limit)]
    if fields:
        for f in fields:
            cmd += ["--field-id", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] {r.stderr.strip()}", file=sys.stderr); return []
    try:
        return json.loads(r.stdout)["data"]["data"]
    except (json.JSONDecodeError, KeyError):
        return []


def parse_articles():
    rows = lark_query(fields=ART_FIELDS)
    out = []
    for r in rows:
        try:
            out.append({
                "title": r[1] or "", "account": r[2][0] if r[2] else "",
                "impressions": r[3] or 0, "ctr": r[5] or 0,
                "structure": r[6][0] if r[6] else "其他",
                "tier": r[7][0] if r[7] else "", "blocked": r[8][0] if r[8] else "正常",
                "category": r[9][0] if r[9] else "",
            })
        except (IndexError, TypeError):
            continue
    return out


def gen_pack(cat, items, date):
    n = len(items)
    hot = [a for a in items if a["tier"] == "爆款"]
    click = [a for a in items if a["tier"] == "点击强"]
    blocked = [a for a in items if a["blocked"] in ("疑似限流", "确认限流")]
    avg_ctr = sum(a["ctr"] for a in items) / n
    a_acc = [a for a in items if a["account"] == "牛科技"]
    b_acc = [a for a in items if a["account"] == "牛科技说"]
    a_ctr = sum(a["ctr"] for a in a_acc) / len(a_acc) if a_acc else 0
    b_ctr = sum(a["ctr"] for a in b_acc) / len(b_acc) if b_acc else 0

    # 最强结构(均展现)
    sg = defaultdict(list)
    for a in items:
        sg[a["structure"]].append(a)
    best = max(sg.items(), key=lambda kv: sum(x["impressions"] for x in kv[1]) / len(kv[1]))
    best_struct, best_imp = best[0], sum(x["impressions"] for x in best[1]) / len(best[1])

    L = [f"# {cat} 弹药包",
         f"> 🤖 自动生成自飞书文章追踪表 · {date} 刷新",
         f"> **主笔 Agent 02 写「{cat}」前必读**：参考 TOP 爆款的钩子结构，避开限流反面。",
         f"> 刷新：`python3 Scripts/gen_category_ammo.py`",
         ""]
    if n < 3:
        L.append(f"> ⚠️ 本品类仅 {n} 篇样本，统计仅供参考，结论需谨慎。")
    L += ["", "## 📊 品类概况",
          f"- 累计 **{n}** 篇 · 爆款 {len(hot)} · 点击强 {len(click)} · 限流 {len(blocked)} · 均 CTR {avg_ctr:.1f}%",
          f"- 双号：牛科技(A) {len(a_acc)}篇均CTR{a_ctr:.1f}% / 牛科技说(B) {len(b_acc)}篇均CTR{b_ctr:.1f}%",
          f"- 最强结构：**{best_struct}**（均展现 {int(best_imp):,}）", ""]

    # TOP 爆款样本
    top = sorted(items, key=lambda x: -x["impressions"])[:8]
    L += ["## 🏆 TOP 爆款样本（学钩子结构，勿抄标题）", "",
          "| # | 标题 | 展现 | CTR | 结构 | 账号 | 学什么 |",
          "|---|---|---|---|---|---|---|"]
    for i, a in enumerate(top, 1):
        hook = STRUCT_HOOKS.get(a["structure"], "?")
        L.append(f"| {i} | {a['title'][:26]} | {a['impressions']:,} | {a['ctr']}% | {a['structure']} | {a['account']} | {hook[:24]} |")
    L.append("")

    # 限流反面
    L.append("## ⛔ 限流反面（必须避开）")
    if blocked:
        L += ["", "| 标题 | 展现 | 结构 | 教训 |", "|---|---|---|---|"]
        for a in sorted(blocked, key=lambda x: x["impressions"]):
            L.append(f"| {a['title'][:30]} | {a['impressions']:,} | {a['structure']} | 检查是否触发限流词/标题党 |")
    else:
        L.append("\n本品类暂无限流篇。")
    L.append("")

    # 该品类用过的结构
    L += ["## ✅ 该品类用过的结构", "", "| 结构 | 篇数 | 均CTR | 均展现 | 推荐 |", "|---|---|---|---|---|"]
    for s, ss in sorted(sg.items(), key=lambda kv: -sum(x["impressions"] for x in kv[1]) / len(kv[1])):
        sc = len(ss); sctr = sum(x["ctr"] for x in ss) / sc; simp = int(sum(x["impressions"] for x in ss) / sc)
        rec = "推荐" if s in ACTIVE_FORMULAS else ("慎用" if s in ("品牌锚点型",) else "禁用" if s in ("全景指南型", "人群细分型") else "可测")
        L.append(f"| {s} | {sc} | {sctr:.1f}% | {simp:,} | {rec} |")
    L.append("")

    # 机会：活跃公式未消费
    used = set(sg.keys())
    opp = [f for f in ACTIVE_FORMULAS if f not in used]
    L.append("## 🎯 机会：活跃公式未在本品类用过")
    if opp:
        for f in opp:
            L.append(f"- **{f}**：{STRUCT_HOOKS.get(f, '')}")
    else:
        L.append("活跃公式已全覆盖，建议从最强结构里找新角度。")
    L.append("")

    # 写作提示
    L += ["## 📝 写「" + cat + "」的提示"]
    tips = [f"- 最强结构是 **{best_struct}**，优先套用（展现 {int(best_imp):,}）"]
    if a_acc and b_acc:
        if a_ctr > b_ctr + 1:
            tips.append(f"- A 号(牛科技)表现更强(均CTR {a_ctr:.1f}% vs B号 {b_ctr:.1f}%)，本品类优先 A 号")
        elif b_ctr > a_ctr + 1:
            tips.append(f"- B 号(牛科技说)表现更强(均CTR {b_ctr:.1f}% vs A号 {a_ctr:.1f}%)，本品类优先 B 号")
    if opp:
        tips.append(f"- 机会结构：{', '.join(opp[:2])} 还没用过，可试")
    if blocked:
        tips.append(f"- 有 {len(blocked)} 篇限流，写前过 `06-合规红线词库.md` 扫描")
    L += tips
    return "\n".join(L)


def main():
    articles = parse_articles()
    cats = defaultdict(list)
    for a in articles:
        if a["category"]:
            cats[a["category"]].append(a)
    os.makedirs(OUT_DIR, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    idx = [f"# 品类弹药包索引", f"> 🤖 自动生成 · {date} · 共 {len(cats)} 个品类",
           f"> 主笔 Agent 02 写某品类前，读 `{{品类}}.md`。刷新：`python3 Scripts/gen_category_ammo.py`",
           "", "| 品类 | 篇数 | 爆款 | 限流 | 均CTR | 最强结构 |", "|---|---|---|---|---|---|"]
    for cat, items in sorted(cats.items(), key=lambda x: -len(x[1])):
        md = gen_pack(cat, items, date)
        with open(f"{OUT_DIR}/{cat}.md", "w", encoding="utf-8") as f:
            f.write(md)
        n = len(items)
        hot = len([a for a in items if a["tier"] == "爆款"])
        blk = len([a for a in items if a["blocked"] in ("疑似限流", "确认限流")])
        avg = sum(a["ctr"] for a in items) / n
        sg = defaultdict(list)
        for a in items:
            sg[a["structure"]].append(a)
        best = max(sg.items(), key=lambda kv: sum(x["impressions"] for x in kv[1]) / len(kv[1]))[0]
        idx.append(f"| [{cat}]({cat}.md) | {n} | {hot} | {blk} | {avg:.1f}% | {best} |")
        print(f"[生成] {cat}.md ({n}篇, 爆款{hot}, 限流{blk})")
    with open(f"{OUT_DIR}/00_索引.md", "w", encoding="utf-8") as f:
        f.write("\n".join(idx))
    print(f"\n[完成] {len(cats)} 个品类弹药包 + 索引 → {OUT_DIR}/")


if __name__ == "__main__":
    main()
