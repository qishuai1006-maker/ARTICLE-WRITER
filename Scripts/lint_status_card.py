#!/usr/bin/env python3
"""
Super Writer · status card lint

Checks the 00_生产状态卡 (single source of truth for one article) against
the actual landed files. Four checks:

1. uniqueness        — exactly one 00_生产状态卡*.md in the project dir
2. title consistency  — status card title vs 02 / 03 titles vs Word filename
3. stage ↔ file match — stages marked 通过 must have their product file landed
4. mandatory fields   — CLAUDE.md-mandated 10 fields non-empty in topic→content 卡

Born from:
- CLAUDE.md mandate: "缺 15字点击钩子、首屏冲突、反常识判断、收藏死线、评论触发点、
  主证据对象、必召回 L1/L2/L4/L3 任一项，必须退回，不得自行脑补；下游只认状态卡和
  落盘文件，不认口头完成"
- SOP §八: "所有生产开工先建 00_生产状态卡... 下游只认状态卡 + 落盘文件"
- 0621 复盘: 流程层没钉状态卡 → 子 agent 跳步、标题/文件对不上、口头"做完了"不可验

Wired into /write Step 8.5 (before Step 9 交付). ERROR blocks delivery.

Usage:
  python3 Scripts/lint_status_card.py outputs/牛科技_空调_2026-06-22/
  python3 Scripts/lint_status_card.py outputs/.../00_生产状态卡.md
  python3 Scripts/lint_status_card.py <dir> --json

Exit codes: 0 = pass, 1 = error, 2 = warning only
"""

import argparse
import json
import re
import sys
from pathlib import Path


# CLAUDE.md-mandated mandatory fields in topic→content 交接卡.
# Each must be non-empty (placeholder like 不适用 / 无 / N/A counts as filled —
# the field is acknowledged; ERROR is for template leftovers never touched).
MANDATORY_FIELDS = [
    "15 字点击钩子",
    "首屏冲突",
    "反常识判断",
    "收藏死线",
    "评论触发点",
    "主证据对象",
    "必召回 L1",
    "必召回 L2",
    "必召回 L4",
    "L3 场景调研",
]

# Stage → product file glob it must have landed when marked 通过.
# S6-S9 are post-delivery (publish/data/review), not checked at pre-delivery lint.
STAGE_PRODUCTS = {
    "S1": ["01*.md"],            # 拆解卡 / 01c 数据调研
    "S2": ["02_*.md"],           # 正文初稿
    "S3": ["03_*.md"],           # 风控终稿
    "S4": ["T5_*.png"],          # 配图落盘（至少一张）
    "S5": ["*.docx"],            # Word 成品
}

EMPTY_MARKERS = ("", "待填", "TODO", "TBD", "未填", "待补充")


def normalize(s):
    """Collapse whitespace + lowercase for tolerant comparison."""
    return re.sub(r"\s+", "", s).lower() if s else ""


def find_project_dir(path: Path) -> Path:
    """Accept either a project dir or a status-card file path; return the dir."""
    if path.is_dir():
        return path
    if path.is_file():
        return path.parent
    # nonexistent — assume the caller meant a dir
    return path


def find_status_cards(project_dir: Path):
    return sorted(project_dir.glob("00_生产状态卡*.md"))


def extract_card_title(content: str) -> str:
    """Pull 文章标题 from 基础信息; fall back to 首选标题 in topic→content 卡."""
    # Primary: "- 文章标题：<value>"
    m = re.search(r"文章标题[：:]\s*(.+)", content)
    if m:
        v = m.group(1).strip()
        # strip trailing markdown / list artifacts
        v = re.sub(r"\s*\|.*$", "", v).strip()
        if v:
            return v
    # Fallback: "- 首选标题：<value>"
    m = re.search(r"首选标题[：:]\s*(.+)", content)
    if m:
        return re.sub(r"\s*\|.*$", "", m.group(1)).strip()
    return ""


def extract_md_title(path: Path) -> str:
    """First '# ' heading from a markdown article."""
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def parse_stage_table(content: str):
    """Yield (stage_id, status_text) for each row in 阶段状态 table."""
    for line in content.splitlines():
        s = line.strip()
        if not s.startswith("|") or "S" not in s:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4:
            continue
        first = cells[0]
        if not re.match(r"^S\d+$", first):
            continue
        # status is typically the 4th column (after 阶段/状态名/负责人)
        status = cells[3] if len(cells) > 3 else ""
        yield first, status, cells


def field_is_empty(value: str) -> bool:
    v = value.strip()
    if v in EMPTY_MARKERS:
        return True
    # only whitespace / punctuation leftover
    if not re.search(r"[一-鿿A-Za-z0-9]", v):
        return True
    return False


def check_mandatory_fields(content: str):
    """Return list of (field_name, '') for each empty mandatory field."""
    missing = []
    # Restrict to topic→content section so we don't grab content→image fields
    # with similar names. Section header in template: "## topic -> content 交接卡"
    section = ""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## ") and "topic" in line.lower() and "content" in line.lower():
            section_start = i
            # find next ## section
            section_end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## "):
                    section_end = j
                    break
            section = "\n".join(lines[section_start:section_end])
            break
    if not section:
        section = content  # fallback: search whole card
    for field in MANDATORY_FIELDS:
        # match "- <field>：<value>" tolerating spacing variants ("15 字" / "15字")
        field_pattern = r"\s*".join(re.escape(part) for part in field.split())
        pat = re.compile(field_pattern + r"\s*[：:]\s*(.*)$")
        found = False
        for line in section.splitlines():
            m = pat.search(line)
            if m:
                found = True
                if field_is_empty(m.group(1)):
                    missing.append(field)
                break
        if not found:
            # field itself absent from the card
            missing.append(field)
    return missing


def add_issue(bucket, code, message):
    bucket.append({"code": code, "message": message})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path,
                    help="project dir or status card file path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    errors, warnings = [], []
    project_dir = find_project_dir(args.target)
    cards = find_status_cards(project_dir)

    # --- check 1: uniqueness ---
    if len(cards) == 0:
        add_issue(errors, "missing_status_card",
                  f"项目目录里没有 00_生产状态卡*.md：{project_dir}"
                  f"（SOP §八：所有生产开工先建；下游只认状态卡 + 落盘文件）")
        _emit(errors, warnings, args.json, project_dir=str(project_dir))
        return 1
    if len(cards) > 1:
        names = ", ".join(c.name for c in cards)
        add_issue(errors, "duplicate_status_card",
                  f"项目目录里有 {len(cards)} 份状态卡（{names}）——真相源必须唯一，合并或删冗余")
        _emit(errors, warnings, args.json, project_dir=str(project_dir))
        return 1

    card_path = cards[0]
    card_content = card_path.read_text(encoding="utf-8")
    card_title = extract_card_title(card_content)

    if not card_title:
        add_issue(errors, "missing_card_title",
                  "状态卡未填「文章标题」（基础信息）也未填「首选标题」（topic→content 卡）")

    # --- check 2: title consistency across 4 sources ---
    title_02 = ""
    title_03 = ""
    for p in project_dir.glob("02_*.md"):
        title_02 = extract_md_title(p)
        if title_02:
            break
    for p in project_dir.glob("03_*.md"):
        title_03 = extract_md_title(p)
        if title_03:
            break

    # status card vs 03 终稿 — must match (03 is the final truth)
    if card_title and title_03 and normalize(card_title) != normalize(title_03):
        add_issue(errors, "title_drift_card_vs_03",
                  f"状态卡标题「{card_title}」≠ 03 终稿标题「{title_03}」"
                  f"——交付前必须对齐（03 是最终真相）")

    # 02 vs 03 — title may be refined in 风控, flag but don't block
    if title_02 and title_03 and normalize(title_02) != normalize(title_03):
        add_issue(warnings, "title_refined_02_to_03",
                  f"02 标题「{title_02}」≠ 03 标题「{title_03}」"
                  f"（风控改标题正常，确认是有意修订即可）")

    # Word filename overlap with title — CJK char overlap ≥2 OR a shared latin/digit token
    docx_files = list(project_dir.glob("*.docx"))
    if docx_files and card_title:
        title_cjk = set(re.findall(r"[一-鿿]", card_title))
        title_latin = set(re.findall(r"[A-Za-z]{3,}|\d{2,}", card_title))
        matched = False
        for docx in docx_files:
            fname = docx.stem
            fname_cjk = set(re.findall(r"[一-鿿]", fname))
            if len(title_cjk & fname_cjk) >= 2:
                matched = True
                break
            fname_latin = set(re.findall(r"[A-Za-z]{3,}|\d{2,}", fname))
            if title_latin & fname_latin:
                matched = True
                break
        if not matched:
            add_issue(warnings, "word_filename_disjoint",
                      f"Word 文件名「{docx_files[0].stem}」与标题无重叠字——"
                      f"归档/检索时易混淆，建议改名含标题关键词")

    # --- check 3: stage ↔ file match ---
    stage_status = {}
    for stage_id, status, _cells in parse_stage_table(card_content):
        stage_status[stage_id] = status
    for stage_id, expected_globs in STAGE_PRODUCTS.items():
        status = stage_status.get(stage_id, "未开始")
        if "通过" not in status and "兜底" not in status:
            continue  # only check stages claimed done
        landed = False
        for g in expected_globs:
            if list(project_dir.glob(g)):
                landed = True
                break
        if not landed:
            add_issue(errors, "stage_file_missing",
                      f"{stage_id} 标「{status}」但目录里找不到对应产物（{expected_globs}）"
                      f"——状态卡声称通过但文件没落盘 = 流程不完整")

    # --- check 4: mandatory fields ---
    missing_fields = check_mandatory_fields(card_content)
    for f in missing_fields:
        add_issue(errors, "mandatory_field_empty",
                  f"topic→content 卡必填字段「{f}」为空——CLAUDE.md 强制 10 字段不得脑补/留空")

    _emit(errors, warnings, args.json, project_dir=str(project_dir),
          card=str(card_path), card_title=card_title,
          title_02=title_02, title_03=title_03)
    if errors:
        return 1
    if warnings:
        return 2
    return 0


def _emit(errors, warnings, as_json, **extra):
    passed = not errors
    if as_json:
        print(json.dumps({
            "passed": passed,
            "project_dir": extra.get("project_dir", ""),
            "card": extra.get("card", ""),
            "card_title": extra.get("card_title", ""),
            "title_02": extra.get("title_02", ""),
            "title_03": extra.get("title_03", ""),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return
    status = "PASS" if passed and not warnings else ("ERROR" if errors else "WARNING")
    print(f"{status}: errors={len(errors)} warnings={len(warnings)} "
          f"card={extra.get('card', '')}")
    for issue in errors + warnings:
        print(f"- [{issue['code']}] {issue['message']}")
    if passed and not warnings:
        print("状态卡检查通过 ✓（唯一 / 标题对齐 / 阶段↔文件 / 10 字段齐）")


if __name__ == "__main__":
    sys.exit(main())
