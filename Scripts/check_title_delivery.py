#!/usr/bin/env python3
"""
Super Writer · title delivery checker (双向闸门: 防夸张 + 防平庸)

Checks whether what the TITLE promises actually lands in the BODY, AND whether
the title still carries enough impact to not be a 阉割版 (over-compliant weaken).

Born from two real failures / CEO design push:
- 2026-06-21 牛科技·空调: title said "华凌神机二代Pro贵239元" but after risk
  control stripped un-evidenced numbers, the body lost both 239 and the
  comparison data. Title hook landed on empty air — yet lint PASSED (lint only
  counts what IS in body, never what title PROMISED). → 正向闸门(防夸张)
- 2026-06-22 CEO 课题"吸引力×合规平衡": 简单翻译成"别写强标题"会把爆款能力
  阉割掉. 平衡公式 = 每个爆款元素锚定可兑现的信息增量. → 反向闸门(防平庸):
  标题兑现了但冲击力元素删光 = 平庸信号 = 爆款能力被阉割(CEO 担心的那个失败模式).

Three layers:
  正向·防夸张  — 标题承诺正文要兑现 (check 1-5 原有 + check 7 强度词软查)
  硬黑名单     — 纯恐吓/强迫/虚假热度, 无信息能锚定 → 直接 ERROR (check 6)
  反向·防平庸  — 标题无冲击力但正文有弹药 = 过度弱化 (check 8)

Run by /write Step 4.5 (主控对账), between 02 first draft and 03 risk control.

Usage:
  python3 Scripts/check_title_delivery.py outputs/03_终稿_xxx.md
  python3 Scripts/check_title_delivery.py outputs/03_xxx.md --evidence outputs/02b_xxx.md

Exit codes:
  0 = all title promises delivered (or only soft warnings)
  1 = hard miss: title number/model/comparison absent, or HARD_GREY word hit
  2 = warning only (strength word needs 主控 fulfillment review / title over-weak)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# --- entity regexes (kept in sync with lint_quick_article.py) ---
MODEL_RE = re.compile(
    r"\b[A-Za-z]{1,8}\d+[A-Za-z0-9]*(?:\s+(?:Pro|Ultra|MAX|Max|Plus|Mini|LED|SE|Air|XDR))*\b"
)
NUMBER_WITH_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:元|块|寸|匹|P|升|L|Hz|hz|nits|nit|Pa|kg|W|kW|kWh|分区|㎡|mm|cm|%|万\+?|万台|台)"
)
PRICE_RE = re.compile(r"(?:¥|￥)?\s*\d{3,6}\s*(?:元|块)?")
DIGIT_RUN_RE = re.compile(r"\d+(?:\.\d+)?")

# Chinese model / series names lint's MODEL_RE cannot see. Extend per category.
CN_MODEL_PATTERNS = [
    r"神机二代(?:Pro)?",
    r"酷省电(?:二代)?(?:Pro)?",
    r"全面风(?:风尊)?(?:二代)?",
    r"天仪(?:Pro)?",
    r"云佳(?:Pro)?",
    r"巨省电(?:双排版|Pro)?",
    r"小黑翼",
    r"小黑镜",
    r"双子星",
    r"净省电(?:Plus)?",
    r"AK\d+\w*",
    r"[A-Z]{1,4}\d{2,4}[A-Z0-9]*",
]
CN_MODEL_RE = re.compile("|".join(CN_MODEL_PATTERNS))

# --- 合规×爆款平衡 · 双向闸门词表 (跟 Skills/06 兑现机制章节同步) ---
# HARD_GREY: 纯恐吓/强迫/虚假热度, 无任何信息能锚定 → 命中即 ERROR.
#   对应头条社区规范"夸张式/强迫式标题"硬违规区. 没有信息能救这类词, 直接换.
HARD_GREY_WORDS = (
    "买了必后悔", "不看后悔", "不买后悔", "全家遭殃", "闭眼入",
    "内幕曝光", "惊天内幕", "震惊", "万万没想到", "看哭了",
    "疯传", "刷屏", "人人都在买",
)
# STRENGTH/SUSPENSE: 强度/悬念词, 本身不禁(白名单思维) — 标题可用, 但
# 正文必须兑现该强度(防夸张), 由主控 Step 4.5 按三个核心检验复核:
#   ① 夸张→说的正文能100%兑现? ② 悬念→标题告知了领域/问题? ③ 强迫→风险真实存在?
STRENGTH_WORDS = (
    "竟", "居然", "竟然", "真相是", "其实", "别再", "别光", "别只",
)
# 注: COMPARE_CUES (below) 已含 暗藏/玄机/猫腻/陷阱/别花/冤枉/真实差距 等,
# STRENGTH_WORDS 补"竟/居然/真相是/其实/别再"等纯强度词, 两表故意有交集.

# Title comparison-pledge cues. When the title carries one of these + a number,
# the title is promising "A vs B" or "X costs Y more" — the body must then
# deliver that delta number, otherwise the hook lands on empty air.
COMPARE_CUES = ("贵", "差价", "差", "比", "vs", "VS", "和", "与", "还是",
                "暗藏", "玄机", "猫腻", "陷阱", "别花", "冤枉", "别只看",
                "别光看", "真实差距", "谁更")

# Trivial digits not worth checking (chapter ordinals etc.)
LIST_CUE_AFTER = re.compile(r"^\s*(招|点|步|条|个|件|次|招数)")


def extract_title(content):
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    for line in content.splitlines():
        s = line.strip()
        if s:
            return s.lstrip("#").strip()
    return ""


def normalize(s):
    return re.sub(r"\s+", "", s).lower()


def body_text(content):
    """Body for entity search: strip title line, images, code, links, placeholders."""
    keep = []
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("# "):
            continue
        keep.append(line)
    body = "\n".join(keep)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    body = re.sub(r"\[[^\]]+\]\([^)]*\)", "", body)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"\[此处[^]]*\]", "", body)
    body = re.sub(r"\[信息图[^]]*\]", "", body)
    return body


def classify_title_digits(title):
    """Split title digit runs into hard (must appear in body) vs soft (structural)."""
    hard, soft = [], []
    for m in DIGIT_RUN_RE.finditer(title):
        d = m.group(0)
        tail = title[m.end():m.end() + 3]
        if LIST_CUE_AFTER.match(tail):
            soft.append(d)              # "3招" / "5步" — structural, almost always present
            continue
        if d in ("1", "2", "3") and not any(c.isdigit() for c in title[max(0, m.start()-1):m.start()]):
            soft.append(d)              # bare tiny integer — usually rhetorical
            continue
        hard.append(d)                  # price / param / delta — sharp promise
    return hard, soft


def extract_title_models(title):
    """English + Chinese model tokens from title."""
    found = set()
    for m in MODEL_RE.finditer(title):
        found.add(m.group(0).strip())
    for m in CN_MODEL_RE.finditer(title):
        tok = m.group(0).strip()
        if tok:
            found.add(tok)
    return found


def body_entity_count(body):
    """Count hard entities (number-with-unit / models) in body — for 反向闸门 check 8."""
    ents = set(NUMBER_WITH_UNIT_RE.findall(body))
    ents |= set(m.group(0) for m in MODEL_RE.finditer(body))
    ents |= set(m.group(0) for m in CN_MODEL_RE.finditer(body))
    return len(ents)


def add_issue(bucket, code, message):
    bucket.append({"code": code, "message": message})


def check_evidence_unsure_leak(evidence, body_norm):
    """Numbers flagged UNSURE in the evidence card must NOT leak into the body."""
    leaks = []
    for line in evidence.splitlines():
        if line.startswith(">"):
            continue
        if "UNSURE" not in line:
            continue
        for d in DIGIT_RUN_RE.findall(line):
            if len(d) >= 2 and d in body_norm:
                leaks.append((d, line.strip()[:70]))
    return leaks

def is_digit_in_text(d, text):
    if d in text: return True
    if d == "200" and ("两百" in text or "二百" in text): return True
    if d == "85" and "八十五" in text: return True
    if len(d) == 2:
        d1, d2 = d[0], d[1]
        c1 = "一二三四五六七八九"[int(d1)-1] if d1!='0' else ""
        c2 = "一二三四五六七八九"[int(d2)-1] if d2!='0' else ""
        if d2 == '0':
            if f"{c1}十" in text: return True
        else:
            if f"{c1}十{c2}" in text: return True
    if len(d) == 3 and d[1:] == "00":
        c1 = "两" if d[0]=='2' else "一二三四五六七八九"[int(d[0])-1]
        c1_alt = "二" if d[0]=='2' else c1
        if f"{c1}百" in text or f"{c1_alt}百" in text: return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article", type=Path)
    ap.add_argument("--evidence", type=Path)
    ap.add_argument("--title", type=str, default="",
                    help="override title (use 骨架定案/状态卡标题查 03 正文兑现)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    errors, warnings = [], []

    if not args.article.exists():
        print(json.dumps({"passed": False, "errors": [{"code": "missing_article",
              "message": f"文章不存在：{args.article}"}]}, ensure_ascii=False))
        return 1

    content = args.article.read_text(encoding="utf-8")
    title = args.title.strip() or extract_title(content)
    body = body_text(content)
    body_norm = normalize(body)

    if not title:
        add_issue(errors, "missing_title", "未找到一级标题，无法做标题兑现检查")
        _emit(errors, warnings, args.json, title="")
        return 1

    hard_digits, soft_digits = classify_title_digits(title)
    title_models = extract_title_models(title)

    # --- check 1: hard digits (prices / params / deltas) must appear in body ---
    for d in hard_digits:
        if not is_digit_in_text(d, body_norm):
            add_issue(errors, "digit_missing",
                      f"标题承诺的数字「{d}」未在正文出现——标题抛的钩子正文没接住")

    # --- check 2: models in title must appear in body ---
    for m in title_models:
        if normalize(m) not in body_norm:
            add_issue(errors, "model_missing",
                      f"标题型号「{m}」未在正文出现")

    # --- check 3: comparison pledge — title has cue + number, body must carry the number ---
    has_compare = any(c.lower() in title.lower() for c in COMPARE_CUES)
    if has_compare and hard_digits:
        missing = [d for d in hard_digits if not is_digit_in_text(d, body_norm)]
        if missing:
            add_issue(errors, "compare_pledge_broken",
                      f"标题含对比承诺词但正文中找不到差值数字「{','.join(missing)}」"
                      f"——标题说'差/贵/比 N'，正文必须兑现 N（否则主控要么回 01c 补数据，要么换标题）")

    # --- check 4 (soft): structural digits present ---
    for d in soft_digits:
        if d not in body_norm:
            add_issue(warnings, "structural_digit_soft",
                      f"标题序列数字「{d}」在正文未直接命中（通常是结构词，人工复核即可）")

    # --- check 5: evidence UNSURE leak (if --evidence given) ---
    if args.evidence:
        if not args.evidence.exists():
            add_issue(warnings, "missing_evidence", f"证据卡不存在：{args.evidence}")
        else:
            evidence = args.evidence.read_text(encoding="utf-8")
            leaks = check_evidence_unsure_leak(evidence, body_norm)
            for d, src in leaks:
                add_issue(errors, "unsure_leak",
                          f"证据卡标 UNSURE 的数字「{d}」漏进了正文（来源：{src}）")

    # ===== 合规×爆款平衡 · 双向闸门 (CEO 0622 课题) =====

    # --- check 6 (正向·防夸张·硬黑名单): HARD_GREY 词命中即 ERROR ---
    # 纯恐吓/强迫/虚假热度, 无任何信息能锚定. 跟 Skills/06 C 类同步.
    title_grey = [w for w in HARD_GREY_WORDS if w in title]
    for w in title_grey:
        add_issue(errors, "hard_grey_word",
                  f"标题含硬灰词「{w}」——纯恐吓/强迫/虚假热度, 无信息能锚定"
                  f"(头条社区规范·夸张式/强迫式标题硬违规区)."
                  f" 改写方向: Skills/06 三种替代技术(信息权威感/真实悬念/精准场景代入), 不是词表替换.")

    # --- check 7 (正向·防夸张·软白名单思维): STRENGTH 词标记需主控兑现复核 ---
    # 白名单思维: 不禁"竟/居然", 而是要求"竟"后面有真信息. 兑现判断是语义的, 脚本标记 → 主控复核.
    title_strength = [w for w in STRENGTH_WORDS if w in title and w not in title_grey]
    if title_strength:
        add_issue(warnings, "strength_word_needs_fulfillment",
                  f"标题用了强度/悬念词「{','.join(title_strength)}」——本身不禁(白名单思维),"
                  f" 但正文必须兑现该强度. 主控 Step 4.5 按三个核心检验复核:"
                  f" ①夸张→说的正文能100%兑现? ②悬念→标题告知了领域/问题? ③强迫→风险是真实存在的?")

    # --- check 8 (反向·防平庸): 标题无冲击力 + 正文有硬实体 → WARN 过度弱化 ---
    # CEO 课题核心: 平衡公式 = 每个爆款元素锚定可兑现的信息增量. 反向 = 正文有弹药(信息)
    # 但标题没用(冲击力元素全空) = 把可钩子的真实信息做成了平庸标题 = 爆款能力阉割信号.
    title_has_impact = bool(hard_digits or title_models or has_compare
                            or title_strength or title_grey)
    if not title_has_impact:
        n_body_ents = body_entity_count(body)
        if n_body_ents >= 3:
            add_issue(warnings, "title_over_weak",
                      f"标题无任何冲击力元素(数字/型号/对比/强度词全空),"
                      f" 但正文有 {n_body_ents} 个可钩子硬实体. "
                      f"这可能是过度合规弱化(爆款能力阉割信号)——"
                      f"若文章是工具型(清单/科普)标题弱属正常;"
                      f" 若是钩子型(型号解码/价格段/阵营对决)标题该用上弹药."
                      f" 参考 Skills/06 三种替代技术把真实信息做成有效吸引(不是回到夸张).")

    _emit(errors, warnings, args.json, title=title,
          hard_digits=hard_digits, soft_digits=soft_digits,
          models=list(title_models), has_compare=has_compare,
          grey=title_grey, strength=title_strength)
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
            "title": extra.get("title", ""),
            "hard_digits": extra.get("hard_digits", []),
            "soft_digits": extra.get("soft_digits", []),
            "models": extra.get("models", []),
            "has_compare": extra.get("has_compare", False),
            "grey_words": extra.get("grey", []),
            "strength_words": extra.get("strength", []),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return
    status = "PASS" if passed and not warnings else ("ERROR" if errors else "WARNING")
    print(f"{status}: errors={len(errors)} warnings={len(warnings)} title={extra.get('title','')[:40]}")
    for issue in errors + warnings:
        print(f"- [{issue['code']}] {issue['message']}")
    if passed and not warnings:
        print("标题承诺全部在正文兑现 ✓ (双向闸门: 无夸张兑现缺口 + 无过度弱化)")


if __name__ == "__main__":
    sys.exit(main())
