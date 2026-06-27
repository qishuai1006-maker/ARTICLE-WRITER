#!/usr/bin/env python3
"""check_topic_collision.py — 选题撞车检测（01 拆解前必跑）

查飞书文章追踪表，看本账号×本品类（×关键词）做过几次、表现如何，
防止同质化选题和形式疲劳。对应运营方法论/04_爆文内核库.md 的撞车规则。

检测四件事：
  1. 品类饱和（≥8 篇）
  2. 同题撞车（关键词命中，按上次展现分高危/中危）
  3. 标题壳疲劳（同账号×同壳用几次 + 最近表现）
  4. 候选标题前 15 字与历史标题相似度（需 --title）

Usage:
  python3 Scripts/check_topic_collision.py 牛科技说 电视
  python3 Scripts/check_topic_collision.py 牛科技说 电视 海信 TCL 创维
  python3 Scripts/check_topic_collision.py 牛科技说 电视 --title "TCL电视型号暗藏玄机？3招看懂Pro和Ultra，别多花冤枉钱"

Single-file, stdlib only, shells out to lark-cli.
"""
import json
import re
import subprocess
import sys
from collections import Counter

LARK = "/opt/homebrew/bin/lark-cli"
BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
TBL_ARTICLES = "tblA8dT3x3bdOF9Y"   # 文章追踪
FIELDS = ["文章标题", "发布账号", "产品品类", "展现量", "CTR(%)",
          "标题结构模板", "表现分层"]

# 标题壳分类（按特征化程度排序，命中即停）。基于 Codex 8 类 + 牛科技说实测标题校准。
# 用关键词正则做启发式归类——分类不求完美，只为抓"同一壳重复使用"。
SHELL_RULES = [
    ("型号解码", r"暗藏玄机|后缀|暗号|Pro.{0,4}Ultra|型号.{0,4}(玄机|暗号|怎么看)"),
    ("经验背书", r"做了.{0,2}年|从业|卖场|售后|拆过|帮.{0,3}(挑|买|选)|换过|干过.{0,2}年|评测|买了\d|用了.{0,2}年"),
    ("踩坑顿悟", r"我悟了|终于悟|终于懂|才懂|才看清|终于明白|才发现|原来"),
    ("内幕揭示", r"真实差距|藏着|背后|不知道|隐性|内幕|不会说|不会告诉|才关键"),
    ("价格差异", r"差价|从.{1,8}到.{1,8}|.{0,3}元和.{0,3}元|差.{0,3}千|价位"),
    ("参数真假", r"标.{0,4}就能|别被.{0,6}带偏|是.{1,6}不是.{1,6}|真假|以为.{0,4}其实"),
    ("清单死线", r"\d{1,2}种别买|这\d{1,2}(点|个|招|条)|\d{1,2}个(条件|硬|关键)|低于不买|别乱买|只认这"),
    ("反问悬念", r"怎么选|哪条|到底|谁(在|成|更|强)|凭什么|值不值|？|吗[，。？]"),
]


def query():
    cmd = [LARK, "base", "+record-list", "--base-token", BASE_TOKEN,
           "--table-id", TBL_ARTICLES, "--format", "json", "--limit", "300"]
    for f in FIELDS:
        cmd += ["--field-id", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] lark-cli: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout)["data"]["data"]


def cell(x, i):
    """Field i: 单选字段返回 list，取 [0]；数值/文本直接取。"""
    v = x[i] if i < len(x) else None
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


def shell_classify(title):
    """启发式归类标题壳。命中第一个规则即返回，否则返回 '其他'。"""
    for name, pat in SHELL_RULES:
        if re.search(pat, title):
            return name
    return "其他"


def front15(title):
    """取标题前 15 字（去标点/空格），用于撞车比对。"""
    cleaned = re.sub(r"[\s，。？！、；：·\-—（）()【】\[\]]", "", title)
    return cleaned[:15]


def jaccard(a, b):
    """字符 bigram 集合的 Jaccard 相似度，衡量前15字是否撞。"""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ba = {a[i:i + 2] for i in range(len(a) - 1)}
    bb = {b[i:i + 2] for i in range(len(b) - 1)}
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def parse_args(argv):
    """账号 / 品类 / 关键词 / --title 候选标题。"""
    account = category = candidate = None
    kws, i = [], 1
    while i < len(argv):
        a = argv[i]
        if a == "--title":
            if i + 1 < len(argv):
                candidate = argv[i + 1]
                i += 2
                continue
        elif a.startswith("--title="):
            candidate = a[len("--title="):]
            i += 1
            continue
        if account is None:
            account = a
        elif category is None:
            category = a
        else:
            kws.append(a)
        i += 1
    return account, category, kws, candidate


def main():
    account, category, kws, candidate = parse_args(sys.argv)
    if not account or not category:
        print("Usage: check_topic_collision.py <账号> <品类> [关键词...] [--title 候选标题]")
        sys.exit(2)
    rows = query()

    same_cat = []
    for x in rows:
        title = cell(x, 0)
        if cell(x, 1) != account or cell(x, 2) != category:
            continue
        same_cat.append((int(x[3] or 0), cell(x, 4), cell(x, 5), cell(x, 6), title))

    kw_desc = f" · 关键词{'/'.join(kws)}" if kws else ""
    print(f"=== 撞车检测：{account} · {category}{kw_desc} ===")
    print(f"本账号·本品类历史：{len(same_cat)} 篇")
    if len(same_cat) >= 8:
        print("  ⚠ 品类饱和（≥8 篇），新选题建议换锐角或换品类")

    # 1. 同题撞车（关键词命中）
    if kws:
        same_topic = [r for r in same_cat if all(k in r[4] for k in kws)]
        if same_topic:
            same_topic.sort(reverse=True)
            print(f"\n[同题] 关键词命中（疑似撞题）：{len(same_topic)} 篇")
            for imp, ctr, struct, tier, title in same_topic[:10]:
                print(f"  {imp:>7}展现 {ctr:>2}%CTR [{tier or '?'}] | {title}")
            top = same_topic[0][0]
            if top >= 10000:
                print(f"  🛑 高危撞车：同题曾达 {top} 展现，平台会去重/分流 → 选题打回或强制换锐角")
            elif top >= 3000:
                print(f"  ⚠ 中危撞车：同题曾达 {top} 展现，需明显差异化角度")
        else:
            print("\n[同题] 关键词未命中，选题新颖度 OK")

    # 2. 标题结构疲劳（飞书已回标的结构字段）
    sc = Counter(r[2] for r in same_cat if r[2])
    if sc:
        print("\n[结构疲劳] 本账号·本品类高频结构：")
        for struct, cnt in sc.most_common(5):
            flag = " ⚠疲劳(≥4次建议冷冻)" if cnt >= 4 else ""
            print(f"  {struct}: {cnt} 次{flag}")

    # 3. 标题壳疲劳（启发式分类，补结构字段查不到的表达层重复）
    shells = Counter(shell_classify(r[4]) for r in same_cat)
    if shells:
        print("\n[标题壳] 启发式归类（表达层重复，结构字段查不到的）：")
        for sh, cnt in shells.most_common():
            recent = sorted([r for r in same_cat if shell_classify(r[4]) == sh],
                            reverse=True)[:3]
            recent_str = " / ".join(f"{r[0]}" for r in recent)
            if sh == "其他":
                # 杂项桶：里面标题互不相同，cnt 高不代表疲劳
                print(f"  {sh}: {cnt} 次（杂项未归类，非疲劳）  (近篇展现: {recent_str})")
                continue
            flag = " ⚠疲劳(≥4次)" if cnt >= 4 else ""
            print(f"  {sh}: {cnt} 次{flag}  (近篇展现: {recent_str})")

    # 4. 候选标题前 15 字撞车
    if candidate:
        c15 = front15(candidate)
        cshell = shell_classify(candidate)
        print(f"\n[候选标题] 「{candidate}」")
        print(f"  标题壳归类：{cshell}")
        if cshell != "其他" and shells.get(cshell, 0) >= 4:
            print(f"  ⚠ 该壳本账号已用 {shells[cshell]} 次，建议换壳")
        hits = []
        for imp, ctr, struct, tier, title in same_cat:
            sim = jaccard(c15, front15(title))
            if sim >= 0.5:
                hits.append((sim, imp, title))
        hits.sort(reverse=True)
        if hits:
            print(f"  前15字相似度命中（≥0.5）：")
            for sim, imp, title in hits[:5]:
                lvl = "🛑" if sim >= 0.7 else ("⚠" if sim >= 0.6 else "·")
                print(f"    {lvl} 相似度{sim:.0%} {imp:>6}展现 | {title}")
        else:
            print(f"  前15字相似度：未命中，OK")


if __name__ == "__main__":
    main()
