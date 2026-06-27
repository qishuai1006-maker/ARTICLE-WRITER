#!/usr/bin/env python3
"""Add Valid_Until field to L1/L2 card frontmatter (保鲜期).

L1 品类技术原理 (稳定)  -> 更新日期 + 1 年
L2 品牌档案     (半稳)  -> 更新日期 + 3 月
L3 场景调研报告已有有效期字段, 跳过.

Usage: python3 Scripts/add_valid_until.py
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
KB = ROOT / "家电知识库"


def add_months(ymd: str, months: int) -> str:
    y, m, d = map(int, ymd.split("-"))
    total = y * 12 + (m - 1) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}-{d:02d}"


def add_years(ymd: str, years: int) -> str:
    y, m, d = map(int, ymd.split("-"))
    return f"{y + years:04d}-{m:02d}-{d:02d}"


def process(d: pathlib.Path, shift, label: str) -> int:
    n = 0
    for card in d.glob("*.md"):
        t = card.read_text(encoding="utf-8")
        if "Valid_Until" in t:
            continue
        m = re.search(r"^更新日期:\s*(\d{4}-\d{2}-\d{2})", t, re.M)
        if not m:
            print(f"[skip] {card.name}: 无 '更新日期' 字段")
            continue
        vu = shift(m.group(1))
        t2 = t.replace(
            m.group(0), m.group(0) + f"\nValid_Until: {vu}  # {label}", 1
        )
        card.write_text(t2, encoding="utf-8")
        n += 1
    return n


if __name__ == "__main__":
    n1 = process(KB / "L1_品类技术原理", lambda x: add_years(x, 1), "技术原理稳定，1年")
    n2 = process(KB / "L2_品牌档案", lambda x: add_months(x, 3), "品牌信息半稳，3月")
    print(f"[完成] L1 加 {n1} 个、L2 加 {n2} 个 Valid_Until 字段")
