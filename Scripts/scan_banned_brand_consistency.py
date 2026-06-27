#!/usr/bin/env python3
"""Scan 家电知识库 L1/L2 cards for banned-brand consistency vs 推品逻辑手册.

Extracts every "### 禁推品牌" table from the handbook, then greps all L1/L2
cards for those brand names. Flags lines where a banned brand co-occurs with
positive wording (likely a recommendation conflict).

Usage: python3 Scripts/scan_banned_brand_consistency.py
"""
import re
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HANDBOOK = ROOT / "推品逻辑手册_2026.md"
KB = ROOT / "家电知识库"

POSITIVE_WORDS = [
    "推荐", "首推", "备选首推", "值得买", "值得", "优质", "可靠", "首选",
    "优秀", "性价比高", "性价比之王", "质量好", "质量可靠", "标杆", "王者",
    "之选", "闭眼入", "首选品牌", "主推", "甜点",
]


def extract_banned_brands(text: str) -> set:
    """Pull brand names out of every '### 禁推品牌' table in the handbook."""
    brands = set()
    in_banned = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("### ") and "禁推" in s:
            in_banned = True
            continue
        if in_banned:
            if s.startswith("### ") or s.startswith("## "):
                in_banned = False
                continue
            if s.startswith("|") and "---" not in s and "品牌" not in s[:8]:
                m = re.match(r"\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|", s)
                if m:
                    name = m.group(1).strip()
                    if name and len(name) <= 8:
                        brands.add(name)
    return brands


def scan() -> int:
    if not HANDBOOK.exists():
        print(f"[ERR] handbook not found: {HANDBOOK}", file=sys.stderr)
        return 1
    text = HANDBOOK.read_text(encoding="utf-8")
    banned = extract_banned_brands(text)
    print(f"[禁推品牌清单 · 共 {len(banned)} 个] {sorted(banned)}\n")

    cards = list((KB / "L1_品类技术原理").glob("*.md")) + list(
        (KB / "L2_品牌档案").glob("*.md")
    )

    hits = []
    for card in cards:
        for i, line in enumerate(card.read_text(encoding="utf-8").splitlines(), 1):
            for brand in banned:
                if brand in line:
                    positive = any(w in line for w in POSITIVE_WORDS)
                    # context: is this line clearly about the banned brand being bad?
                    negative = any(w in line for w in ["禁推", "智商税", "不推", "退出中国",
                                                        "品质下降", "虚高", "溢价", "不推荐",
                                                        "慎", "避坑", "反面", "碾压"])
                    if positive and not negative:
                        tag = "⚠️ 疑似正面冲突"
                    elif positive:
                        tag = "~  正面词+负面词同现(需人工看)"
                    else:
                        tag = "·  仅提及"
                    hits.append((card.relative_to(ROOT), i, brand, tag, line.strip()[:90]))

    if not hits:
        print("[结果] L1/L2 未出现任何禁推品牌名。")
        return 0

    conflicts = [h for h in hits if h[3].startswith("⚠️")]
    print(f"[扫描结果] 共 {len(hits)} 处禁推品牌提及，其中 {len(conflicts)} 处疑似正面冲突：\n")
    for path, ln, brand, tag, line in hits:
        print(f"{tag}  {path}:{ln}  [{brand}]  {line}")
    print(f"\n[汇总] 疑似正面冲突 {len(conflicts)} 处，需人工复核。")
    return 0 if not conflicts else 2


if __name__ == "__main__":
    sys.exit(scan())
