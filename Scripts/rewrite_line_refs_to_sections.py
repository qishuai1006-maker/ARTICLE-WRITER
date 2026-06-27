#!/usr/bin/env python3
"""Rewrite fragile 'line NNN' references in 家电知识库 cards into stable
section-title references, by mapping line numbers back to the nearest
## / ### heading in 推品逻辑手册_2026.md.

Default = dry-run (prints diffs, writes nothing). Pass --write to apply.

Usage:
  python3 Scripts/rewrite_line_refs_to_sections.py            # dry-run
  python3 Scripts/rewrite_line_refs_to_sections.py --write    # apply
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HANDBOOK = ROOT / "推品逻辑手册_2026.md"
KB = ROOT / "家电知识库"
CARDS = list((KB / "L1_品类技术原理").glob("*.md")) + list(
    (KB / "L2_品牌档案").glob("*.md")
)

CHN = r"[一二三四五六七八九十百千]"


def build_lookup(text: str):
    chapters, sections = [], []
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if re.match(rf"^## {CHN}", s):
            chapters.append((i, re.sub(r"^#+\s*", "", s).strip()))
        elif s.startswith("### "):
            sections.append((i, re.sub(r"^#+\s*", "", s).strip()))

    def lookup(n: int):
        # find the chapter that CONTAINS n (range [ch_start, next_ch_start))
        ch_idx = None
        for idx, (ln, _) in enumerate(chapters):
            if ln <= n:
                ch_idx = idx
            else:
                break
        if ch_idx is None:
            return None, None
        ch_start, ch_title = chapters[ch_idx]
        ch_end = chapters[ch_idx + 1][0] if ch_idx + 1 < len(chapters) else float("inf")
        # section must be in the SAME chapter and <= n (else fall back to chapter only)
        sec_title = None
        for ln, t in sections:
            if ln < ch_start:
                continue
            if ln > ch_end:
                break
            if ln <= n:
                sec_title = t
            else:
                break
        return ch_title, sec_title

    return lookup


LINE_REF = re.compile(r"line\s+(\d+)(?:\s*[-–—]\s*\d+)?")


def transform(text: str, lookup):
    changes = []

    def repl(m):
        n = int(m.group(1))
        ch, sec = lookup(n)
        if not ch:
            return m.group(0)
        ref = f"§{ch}"
        if sec and sec != ch:
            ref += f" · {sec}"
        changes.append((m.group(0), ref))
        return ref

    new = LINE_REF.sub(repl, text)
    return new, changes


def main():
    write = "--write" in sys.argv
    hb = HANDBOOK.read_text(encoding="utf-8")
    lookup = build_lookup(hb)
    total = 0
    for card in CARDS:
        orig = card.read_text(encoding="utf-8")
        new, changes = transform(orig, lookup)
        if not changes:
            continue
        total += len(changes)
        rel = card.relative_to(ROOT)
        print(f"\n=== {rel}  ({len(changes)} 处) ===")
        for old, newref in changes:
            print(f"  {old:<16} → {newref}")
        if write:
            card.write_text(new, encoding="utf-8")
    mode = "已写入" if write else "[dry-run 未改动]"
    print(f"\n[汇总] 共 {total} 处行号引用，{mode}。{'加 --write 实际执行。' if not write else ''}")


if __name__ == "__main__":
    main()
