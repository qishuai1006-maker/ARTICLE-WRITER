#!/usr/bin/env python3
"""
Super Writer v3.3 · quick article lint

Usage:
  python3 Scripts/lint_quick_article.py outputs/终稿_xxx.md --evidence outputs/轻量证据卡_xxx.md

Exit codes:
  0 = pass
  1 = error
  2 = warning only
"""

import argparse
import json
import re
import sys
from pathlib import Path


A_TERMS = {
    "横评": "清单/盘点/对比",
    "智商税": "溢价/花冤枉钱",
    "完美": "综合表现强",
    "碾压": "拉开差距",
    "吊打": "优势明显",
    "最好": "值得考虑",
    "第一": "第一梯队/头部水平",
    "秒杀": "优势明显",
}

B_TERMS = {
    "抖音达人说": "避免引述竞品平台达人",
    "随着": "AI开头风险",
    "你知道吗": "播音腔开头",
    "不仅如此": "AI过渡词",
    "首先": "机械序列词",
    "其次": "机械序列词",
    "最后": "机械序列词",
    "总之": "机械总结词",
    "综上所述": "机械总结词",
    "总的来说": "机械总结词",
}

INTERNAL_SOURCE_TERMS = {
    "推品逻辑手册": "内部资料名不得暴露给读者",
    "推品手册": "内部资料名不得暴露给读者",
    "手册里": "内部证据表达不得进入正文",
    "手册中": "内部证据表达不得进入正文",
    "手册记录": "内部证据表达不得进入正文",
    "按手册": "内部证据表达不得进入正文",
    "内部资料": "内部资料名不得暴露给读者",
    "内部收录": "内部资料名不得暴露给读者",
    "证据卡": "证据卡是内部风控产物，不得进入正文",
}

TITLE_MIN = 25
TITLE_MAX = 29

# 闸门A · 算法初筛：文本密度（前 N 字硬实体数）
# 实测依据：同智能体同流程对照，前300字硬实体 0 个的稿 90 展现被毙，4 个的 3676 展现。
DENSITY_WINDOW = 300  # 前 N 字窗口
DENSITY_WARN = 5      # < 5 WARN（不阻断，提示密度偏少）
DENSITY_ERROR = 2     # < 2 ERROR（过不了算法初筛，直接拦）

NUMBER_WITH_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:元|块|寸|匹|P|升|L|Hz|hz|nits|nit|Pa|kg|W|kW|kWh|分区|㎡|mm|cm|%|万\+?|万台|台)"
)
PRICE_RE = re.compile(r"(?:¥|￥)?\s*\d{3,6}\s*(?:元|块)?")
MODEL_RE = re.compile(
    r"\b[A-Za-z]{1,8}\d+[A-Za-z0-9]*(?:\s+(?:Pro|Ultra|MAX|Max|Plus|Mini|LED|SE|Air|XDR))*\b"
)


def visible_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))

def calc_title_len(title: str) -> int:
    # 将连续英文/数字组合视作1个字符单位，防止型号过长被误判
    t = re.sub(r'[A-Za-z0-9]+', 'A', title)
    return len(re.sub(r'\s+', '', t))


def extract_title(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip()
    return ""


def clean_article_chars(content: str) -> int:
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)
    body = re.sub(r"[#>*_`|\-\[\]():：,，.。!！?？\s]", "", body)
    return len(body)


def strip_markdown_artifacts(content: str) -> str:
    content = re.sub(r"```.*?```", "", content, flags=re.S)
    content = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)
    content = re.sub(r"\[[^\]]+\]\([^)]*\)", "", content)
    content = re.sub(r"https?://\S+", "", content)
    return content


def add_issue(bucket, code, line, message):
    bucket.append({"code": code, "line": line, "message": message})


def normalize_compact(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def split_markdown_row(line: str):
    if not line.startswith("|"):
        return []
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_evidence_rows(evidence: str):
    rows = []
    for idx, line in enumerate(evidence.splitlines(), 1):
        cells = split_markdown_row(line)
        if len(cells) < 6:
            continue
        joined = "".join(cells)
        if set(joined.replace(":", "").replace("：", "").replace(" ", "")) <= {"-"}:
            continue
        if cells[0] == "#" or "正文拟写事实" in cells[1]:
            continue
        rows.append({"line": idx, "cells": cells})
    return rows


def density_window(content: str, n: int = DENSITY_WINDOW) -> str:
    """First n visible chars of body (title / images / placeholders stripped)."""
    keep = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            continue
        if re.match(r"\[此处[^]]*\]", stripped):
            continue
        keep.append(line)
    body = "\n".join(keep)
    body = strip_markdown_artifacts(body)
    body = re.sub(r"[#>*_`|]", "", body)
    return re.sub(r"\s+", "", body)[:n]


def count_hard_entities(text: str) -> int:
    """Count hard-entity signals (models + unit-bearing numbers) in window.

    中文型号（鹤6/云溪4.0）不在此匹配，但同段必然带参数数字（尺寸/价格/容量），
    会由 NUMBER_WITH_UNIT_RE 兜住，故不单独造中文型号词典以防虚高。
    """
    return sum(sum(1 for _ in p.finditer(text)) for p in (MODEL_RE, NUMBER_WITH_UNIT_RE))


# ── self-score 启发式词库（双闸门自评） ──
CORRECTION_CUES = ("其实", "并不是", "而不是", "而是", "别只", "别被", "别拿",
                   "误区", "未必", "反而是", "真正的", "猫腻", "藏在", "别当成", "差在")
CONFLICT_CUES = ("后悔", "冤枉", "坑", "损失", "踩", "白买", "白送", "照妖镜",
                 "智商税", "花冤枉钱", "栽跟头", "打折", "被打断", "别")
STANCE_CUES = ("优先看", "别", "建议", "不是", "而是", "真正", "别拿", "别只")
SCENE_CUES = ("我帮", "我家", "换过", "装修", "买过", "朋友", "去年", "前几天",
              "后台", "售后", "评测", "我家装修", "装过")
INVITE_CUES = ("评论", "说说", "聊聊", "留言", "你家", "你呢", "你用过")
LIST_CUE_RE = re.compile(r"\d+\s*(?:处|招|个条件|条|点|步|件事)")
H2_RE = re.compile(r"^(?:##\s|\*\*[一二三四五六七八九十]+、)")


def self_score(content, title, lines, density):
    """Double-gate self-evaluation (heuristic 0-100).

    Auto-computable items are scored directly; semantic items use cue-word
    frequency as a proxy. Verdict is advisory — exit code is still driven by
    lint errors/warnings.
    """
    body_no_title = "\n".join(l for l in lines if not l.startswith("# "))
    body_compact = re.sub(r"\s+", "", body_no_title)
    h2_count = sum(1 for l in lines if H2_RE.match(l.strip()))
    clean_body = strip_markdown_artifacts(content)

    # 闸门 A · 算法初筛
    if density >= DENSITY_WARN:
        a1, a1n = 15, f"前300字硬实体{density}个，密度达标"
    elif density >= DENSITY_ERROR:
        a1, a1n = 8, f"前300字硬实体{density}个，偏少"
    else:
        a1, a1n = 0, f"前300字硬实体{density}个，过不了算法初筛(致命)"

    cues = sum(body_compact.count(c) for c in CORRECTION_CUES)
    a2, a2n = (10, f"纠偏词{cues}处，有反常识判断") if cues >= 3 else \
              ((5, f"纠偏词{cues}处，偏弱") if cues >= 1 else (0, "几乎无纠偏词，疑似中性科普"))

    if h2_count >= 3:
        a3, a3n = 10, f"{h2_count}个小标题，结构化达标"
    elif h2_count == 2:
        a3, a3n = 6, f"{h2_count}个小标题"
    elif h2_count == 1:
        a3, a3n = 3, f"{h2_count}个小标题，偏薄"
    else:
        a3, a3n = 0, "无小标题，结构化不足"

    title_tokens = re.findall(r"[A-Za-z]{2,}|[一-龥]{2,4}", title)
    head400 = density_window(content, 400)
    appear = sum(1 for t in title_tokens if t and t in head400)
    a4, a4n = (5, f"标题词前400字命中{appear}个") if appear >= 2 else \
              ((3, f"标题词前400字命中{appear}个") if appear >= 1 else (0, "标题词前400字命中0个"))

    tl = len(re.sub(r"\s+", "", title))
    title_ok = TITLE_MIN <= tl <= TITLE_MAX
    no_excl = "！" not in title and "!" not in title
    has_hook = bool(re.search(r"\d|[?？]|怎么|还是|暗藏|差距|别|到底", title))
    a5 = 10 if (title_ok and no_excl and has_hook) else (5 if (title_ok and has_hook) else 0)
    a5n = f"长度{'✓' if title_ok else '✗'} 无感叹{'✓' if no_excl else '✗'} 悬念{'✓' if has_hook else '✗'}"

    # 闸门 B · 用户行为
    head150 = density_window(content, 150)
    chits = sum(1 for c in CONFLICT_CUES if c in head150)
    shits = sum(1 for c in SCENE_CUES if c in head150)
    has_price = bool(re.search(r"\d{3,}\s*(?:元|块)|[¥￥]", head150))
    b1, b1n = (10, f"前150字钩子: 冲突{chits}/场景{shits}/价格{'有' if has_price else '无'}") if (chits >= 1 or has_price or shits >= 1) else (0, "前150字无钩子(冲突/价格/场景皆无)")

    list_hits = len(LIST_CUE_RE.findall(content))
    b2, b2n = (10, f"清单数字{list_hits}处+结构化") if (list_hits >= 1 and h2_count >= 3) else \
              ((5, f"清单数字{list_hits}处") if list_hits >= 1 else (0, "无可截图清单"))

    tail = re.sub(r"\s+", "", content)[-100:]
    invite = any(c in tail for c in INVITE_CUES)
    b3, b3n = (10, "结尾有评论诱因(问句/邀评词)") if ("？" in tail or "?" in tail or invite) else (0, "结尾无评论诱因")

    models = set(m.group(0) for m in MODEL_RE.finditer(clean_body))
    b4, b4n = (10, f"不同型号{len(models)}个") if len(models) >= 3 else \
              ((5, f"不同型号{len(models)}个") if len(models) >= 1 else (0, "全文无具体型号"))

    stance = sum(body_compact.count(w) for w in STANCE_CUES)
    b5, b5n = (10, f"立场词{stance}处") if stance >= 4 else \
              ((5, f"立场词{stance}处，偏弱") if stance >= 2 else (0, "立场不明确"))

    a_total = a1 + a2 + a3 + a4 + a5
    b_total = b1 + b2 + b3 + b4 + b5
    total = a_total + b_total
    if total >= 80:
        verdict = "建议交稿(双高)"
    elif total >= 60:
        verdict = "需补强(lint或过，质量层有缺口)"
    else:
        verdict = "不建议交稿(双闸门失守)"

    return {
        "total": total, "A": a_total, "B": b_total, "verdict": verdict,
        "items": [
            ("A1 文本密度(前300字)", a1, 15, a1n),
            ("A2 信息增益(纠偏词)", a2, 10, a2n),
            ("A3 结构化(小标题)", a3, 10, a3n),
            ("A4 标题正文一致", a4, 5, a4n),
            ("A5 标题合规", a5, 10, a5n),
            ("B1 首屏冲突", b1, 10, b1n),
            ("B2 收藏死线", b2, 10, b2n),
            ("B3 评论触发(结尾问句)", b3, 10, b3n),
            ("B4 型号落地", b4, 10, b4n),
            ("B5 立场/反常识", b5, 10, b5n),
        ],
    }


def extract_fact_tokens(content: str):
    tokens = set()
    for pattern in (NUMBER_WITH_UNIT_RE, PRICE_RE, MODEL_RE):
        for match in pattern.finditer(content):
            token = match.group(0).strip()
            if token:
                tokens.add(token)
    return sorted(tokens, key=lambda item: (len(item), item))


def token_supported_by_evidence(token: str, evidence: str) -> bool:
    compact_evidence = normalize_compact(evidence)
    compact_token = normalize_compact(token)
    if compact_token in compact_evidence:
        return True
    digits = re.sub(r"\D", "", token)
    if len(digits) >= 2 and digits in compact_evidence:
        return True
    return False


def scan_terms(lines, terms, errors, warnings, severity):
    for idx, line in enumerate(lines, 1):
        if line.startswith(">"):
            continue
        for term, hint in terms.items():
            if term in line:
                if term == "第一" and re.search(r'榜单|销量|京东|618|双11|第一梯队', line):
                    continue
                target = errors if severity == "error" else warnings
                add_issue(target, f"{severity}_term", idx, f"命中「{term}」：{hint}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("article", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-score", action="store_true",
                        help="输出双闸门自评报告(0-100，不影响 exit code)")
    args = parser.parse_args()

    errors = []
    warnings = []

    if not args.article.exists():
        add_issue(errors, "missing_article", 0, f"文章不存在：{args.article}")
        print(json.dumps({"passed": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 1

    content = args.article.read_text(encoding="utf-8")
    lines = content.splitlines()
    title = extract_title(content)
    title_len = calc_title_len(title)

    if not title:
        add_issue(errors, "missing_title", 0, "缺少一级标题")
    elif not (TITLE_MIN <= title_len <= TITLE_MAX):
        add_issue(errors, "title_length", 1, f"标题必须控制在{TITLE_MIN}-{TITLE_MAX}字，当前{title_len}字")

    if "!" in title or "！" in title:
        add_issue(errors, "title_exclamation", 1, "标题含感叹号")

    body_exclamations = 0
    for idx, line in enumerate(lines, 1):
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
        if "!" in cleaned or "！" in cleaned:
            body_exclamations += cleaned.count("!") + cleaned.count("！")
            add_issue(errors, "exclamation", idx, "正文含感叹号")

    char_count = clean_article_chars(content)
    if char_count < 1500:
        add_issue(warnings, "too_short", 0, f"正文低于1500字：{char_count}")
    elif char_count > 2800:
        add_issue(warnings, "too_long", 0, f"正文超过2800字：{char_count}")

    used_evidence_ids = len(set(re.findall(r'\[E\d+\]', content)))
    if used_evidence_ids > 0:
        density_ratio = char_count / used_evidence_ids
        if density_ratio > 250:
            add_issue(errors, "density_ratio_too_high", 0, f"证据密度过低（平均单条证据扩写{density_ratio:.0f}字，上限250）。水文风险过高，请打回Step 2补调研或精简字数。")
    elif char_count > 0:
        add_issue(errors, "no_evidence_id_used", 0, "正文未引用任何 evidence_id（如 [E01]），请确保每段主干都有证据支撑。")

    placeholders = re.findall(r"\[此处[^]]*信息图[^]]*\]", content)
    inserted_images = re.findall(r"!\[[^\]]*信息图[^\]]*\]\([^)]*\)", content)
    image_slots = len(placeholders) + len(inserted_images)
    if image_slots == 0:
        add_issue(warnings, "image_slots", 0, "正文未发现信息图占位或图片引用；如用户要求完整图文，需由视觉指挥官补图")
    elif image_slots > 3:
        add_issue(warnings, "image_slots", 0, f"快写线内页信息图建议1-3处，当前{image_slots}处；确认不是为凑图打断阅读")

    scan_terms(lines, A_TERMS, errors, warnings, "error")
    scan_terms(lines, INTERNAL_SOURCE_TERMS, errors, warnings, "error")
    scan_terms(lines, B_TERMS, errors, warnings, "warning")

    # 闸门A · 算法初筛：文本密度（前 300 字硬实体数）
    # 与开头人味不冲突——只要求中段有具体型号/参数，不要求全文冷冰冰。
    window = density_window(content)
    density = count_hard_entities(window)
    if density < DENSITY_ERROR:
        add_issue(errors, "low_density", 0,
                  f"前300字硬实体仅{density}个（型号/带单位参数），过不了算法初筛：开头需喂具体型号或参数数字")
    elif density < DENSITY_WARN:
        add_issue(warnings, "low_density", 0,
                  f"前300字硬实体{density}个，偏少：建议中段补具体型号/参数")

    if args.evidence:
        if not args.evidence.exists():
            add_issue(errors, "missing_evidence", 0, f"证据卡不存在：{args.evidence}")
        else:
            evidence = args.evidence.read_text(encoding="utf-8")
            evidence_rows = parse_evidence_rows(evidence)
            for row in evidence_rows:
                cells = row["cells"]
                status = cells[5] if len(cells) > 5 else ""
                boundary = cells[6] if len(cells) > 6 else ""
                if "UNSURE" in status:
                    add_issue(errors, "unsure_evidence", row["line"], "证据卡存在 UNSURE 项，需删除或补证后再出稿")
                if "SINGLE_SOURCE" in status and boundary.strip() in {"", "-", "—"}:
                    add_issue(warnings, "single_source_boundary", row["line"], "SINGLE_SOURCE 项缺少正文表述边界")

            fact_content = strip_markdown_artifacts(content)
            for token in extract_fact_tokens(fact_content):
                if not token_supported_by_evidence(token, evidence):
                    add_issue(warnings, "evidence_token_missing", 0, f"正文事实疑似未登记到证据卡：{token}")

    sc = self_score(content, title, lines, density) if args.self_score else None
    result = {
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "title": title,
        "title_len": title_len,
        "char_count": char_count,
        "density_score": density,
        "self_score": sc,
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["passed"] and not warnings else ("ERROR" if errors else "WARNING")
        print(f"{status}: errors={len(errors)} warnings={len(warnings)} title_len={title_len} chars={char_count} density={density}")
        for issue in errors + warnings:
            line = f":{issue['line']}" if issue["line"] else ""
            print(f"- {issue['code']}{line} {issue['message']}")

        if sc:
            print("\n" + "=" * 56)
            print(f"  双闸门自评 · 总分 {sc['total']}/100  (A算法初筛 {sc['A']}/50 + B用户行为 {sc['B']}/50)")
            print(f"  结论：{sc['verdict']}")
            if errors:
                print(f"  ⚠ 存在 {len(errors)} 个 lint ERROR —— 无论自评多少分，先修 ERROR 再交稿")
            print("-" * 56)
            for name, score, full, note in sc["items"]:
                print(f"  [{score:>2}/{full}] {name} — {note}")
            print("=" * 56)

    if errors:
        return 1
    if warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
