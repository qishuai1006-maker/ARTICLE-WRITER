#!/usr/bin/env python3
"""Collapse duplicate section-prefix produced by rewrite_line_refs_to_sections.

Fixes patterns like '§三 §三、洗衣机' -> '§三、洗衣机' (the original card
already had a '§三' token before 'line NNN', and the rewriter prepended
another '§三、洗衣机'). Also drops a stray duplicated subsection title
sitting right before '为准' (美的-style '价格段推荐表 价格段推荐表为准').

Usage: python3 Scripts/dedupe_section_refs.py [--write]
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
KB = ROOT / "家电知识库"

# §X <品类词/空格> §X、  ->  §X、   (前后章节号必须相同，避免误伤跨章节引用)
DUP_SEC = re.compile(r"§([一二三四五六七八九十])[^\n§]{0,10} §\1、")
# '价格段推荐表（烟灶套装） 价格段推荐表' / 'X X 为准' tail dup
DUP_TAIL = re.compile(r"([^·、（()】]{2,12}) \1(?=为准)")


def main():
    write = "--write" in sys.argv
    total = 0
    for card in KB.rglob("*.md"):
        t = card.read_text(encoding="utf-8")
        orig = t
        t = DUP_SEC.sub(r"§\1、", t)
        t = DUP_TAIL.sub(r"\1", t)
        if t != orig:
            n = orig.count("§") - t.count("§")  # rough
            total += 1
            print(f"{'[write] ' if write else '[dry]   '}{card.relative_to(ROOT)}")
            if write:
                card.write_text(t, encoding="utf-8")
    mode = "已写入" if write else "[dry-run 未改动，加 --write 执行]"
    print(f"\n[汇总] 修改 {total} 个文件，{mode}")


if __name__ == "__main__":
    main()
