import sys
import yaml
import re
import argparse
from pathlib import Path

def print_error(msg):
    print(f"❌ ERROR: {msg}")

def print_warn(msg):
    print(f"⚠️ WARN: {msg}")

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def main():
    parser = argparse.ArgumentParser(description="Check Editorial Lock compliance")
    parser.add_argument("draft_path", type=Path, help="Path to the draft markdown file")
    parser.add_argument("--lock", type=Path, required=True, help="Path to the editorial_lock.yaml file")
    parser.add_argument("--evidence", type=Path, help="Path to the lightweight evidence card (for ID verification)")
    args = parser.parse_args()

    if not args.lock.exists():
        print_error(f"Editorial lock file not found: {args.lock}")
        sys.exit(1)

    if not args.draft_path.exists():
        print_error(f"Draft file not found: {args.draft_path}")
        sys.exit(1)

    # 1. Parse YAML completeness
    try:
        with open(args.lock, 'r', encoding='utf-8') as f:
            lock_data = yaml.safe_load(f)
    except Exception as e:
        print_error(f"Failed to parse YAML: {e}")
        sys.exit(1)

    required_keys = [
        "must_use_evidence", "main_conflict_keywords", "secondary_conflict_keywords",
        "forbidden_positioning", "must_answer_questions", "preferred_title"
    ]
    for k in required_keys:
        if k not in lock_data or lock_data[k] is None:
            print_error(f"Missing required field in editorial lock: {k}")
            sys.exit(1)

    with open(args.draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read()

    lines = draft_content.splitlines()
    title = ""
    body_lines = []
    in_frontmatter = False
    frontmatter_count = 0
    for line in lines:
        if line.strip() == "---":
            frontmatter_count += 1
            if frontmatter_count <= 2:
                continue
        if frontmatter_count == 1:
            continue  # skip frontmatter content
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        else:
            body_lines.append(line)

    body_text = "\n".join(body_lines)
    # 用纯文本字符计算前300字
    clean_body = re.sub(r'\s+', '', body_text)
    opening_text = body_text[:max(300, len(body_text))] if len(clean_body) < 300 else body_text
    # Better: take enough raw text to cover 300 clean chars
    char_count = 0
    opening_end = 0
    for i, ch in enumerate(body_text):
        if not ch.isspace():
            char_count += 1
        if char_count >= 300:
            opening_end = i + 1
            break
    if opening_end == 0:
        opening_end = len(body_text)
    opening_text = body_text[:opening_end]

    closing_text = body_text[-500:] if len(body_text) > 500 else body_text

    errors = 0
    warnings = 0

    # ========== A. 标题必须承接主冲突 ==========
    main_kws = [kw for kw in lock_data.get("main_conflict_keywords", []) if kw.strip()]
    title_main_hits = sum(1 for kw in main_kws if kw in title)
    if title_main_hits < 2 and len(main_kws) >= 2:
        print_error(f"标题未承接主冲突：标题需命中 ≥2 个 main_conflict_keywords，当前命中 {title_main_hits}。标题: {title}")
        errors += 1

    # ========== B. 标题不能说死结论 ==========
    conclusion_words = ["就是", "肯定", "吊打", "完胜", "碾压", "秒杀"]
    question_words = ["？", "吗", "该不该", "怎么选", "到底", "值不值"]
    has_conclusion = any(w in title for w in conclusion_words)
    has_question = any(w in title for w in question_words)
    if has_conclusion and not has_question:
        print_warn(f"标题把结论说死了，悬念提前释放。包含: {[w for w in conclusion_words if w in title]}")
        warnings += 1

    # ========== 2. 前300字主冲突关键词 ==========
    matched_main = sum(1 for kw in main_kws if kw in opening_text)
    if matched_main < 2 and len(main_kws) >= 2:
        print_error(f"前300字缺少主冲突关键词 (要求至少2个)。当前命中: {matched_main}")
        errors += 1

    # ========== 3. 副冲突防抢戏 ==========
    sec_kws = [kw for kw in lock_data.get("secondary_conflict_keywords", []) if kw.strip()]
    matched_sec_count = sum(opening_text.count(kw) for kw in sec_kws)
    matched_main_count = sum(opening_text.count(kw) for kw in main_kws)

    sec_limit = lock_data.get("secondary_conflict_limit", {}).get("max_opening_share", 0.35)

    total_kws = matched_main_count + matched_sec_count
    if total_kws > 0:
        sec_share = matched_sec_count / total_kws
        if sec_share > sec_limit:
            print_error(f"前300字副冲突抢主线 (副冲突占比 {sec_share:.0%} > 限制 {sec_limit:.0%})")
            errors += 1
    elif matched_sec_count > 0 and matched_main_count == 0:
        print_error("前300字主要围绕副冲突展开，而没有承接主冲突")
        errors += 1

    # ========== 4. Forbidden Positioning ==========
    for f_pos in lock_data.get("forbidden_positioning", []):
        if f_pos.strip() and f_pos in draft_content:
            print_error(f"正文触犯了禁忌定位词: {f_pos}")
            errors += 1

    # ========== 5. Evidence Checking ==========
    draft_evidence_ids = set(re.findall(r'\[(E\d+)\]', draft_content))
    must_evidences = lock_data.get("must_use_evidence", [])
    used_must_count = 0

    if must_evidences:
        for ev in must_evidences:
            eid = ev.get("evidence_id")
            if eid and eid in draft_evidence_ids:
                used_must_count += 1

        min_required = min(3, len(must_evidences))
        if used_must_count < min_required:
            print_error(f"正文必须至少承接 must_use_evidence 中 {min_required} 条核心证据，当前仅承接 {used_must_count} 条")
            errors += 1

    # Verify unregistered evidence against L3 if provided
    if args.evidence and args.evidence.exists():
        with open(args.evidence, 'r', encoding='utf-8') as f:
            evidence_text = f.read()
        l3_evidence_ids = set(re.findall(r'\[(E\d+)\]', evidence_text))
        for eid in draft_evidence_ids:
            if eid not in l3_evidence_ids:
                print_error(f"正文使用了未经登记的证据 ID: [{eid}]")
                errors += 1

    # ========== 6. Visual placeholder check ==========
    if "此处插图缺失：未指定" in draft_content:
        print_error('终稿中存在"此处插图缺失：未指定"，视觉流程未闭环')
        errors += 1

    # ========== 7. Must answer questions (decision words in closing) ==========
    must_ans_qs = lock_data.get("must_answer_questions", [])
    if must_ans_qs:
        decision_words = ["适合", "建议", "结论", "买", "怎么选", "选择", "推荐"]
        if not any(w in closing_text for w in decision_words):
            print_error(f"结尾段似乎没有回答 must_answer_questions，缺少决策词")
            errors += 1

    # ========== C. 正向定位检查 ==========
    conclusion_dir = lock_data.get("conclusion_direction", "")
    allowed_pos = [p for p in lock_data.get("allowed_positioning", []) if p.strip()]
    if conclusion_dir and allowed_pos:
        if not any(p in closing_text for p in allowed_pos):
            print_error(f"结尾300字未出现 allowed_positioning 中的正向定位词。要求场景区分而非单方面论证。")
            errors += 1

    # ========== D. 业务策略场景区分检查 ==========
    biz_strategy = lock_data.get("business_strategy", "")
    protected = [m for m in lock_data.get("protected_models_or_brands", []) if m.strip()]
    if ("场景" in biz_strategy or "不踩" in biz_strategy or "不拉踩" in biz_strategy) and len(protected) >= 1:
        # 结尾段必须提及至少1个 protected model（证明做了场景区分，而非只推一方）
        protected_in_closing = sum(1 for m in protected if m in closing_text)
        if protected_in_closing < 1:
            print_error(f"业务策略要求场景区分，但结尾段未提及任何 protected_models_or_brands: {protected}")
            errors += 1

    # ========== RESULT ==========
    if errors > 0:
        print(f"\n❌ Editorial Lock 校验失败，共 {errors} 个 ERROR，{warnings} 个 WARN。")
        sys.exit(1)
    else:
        if warnings > 0:
            print(f"\n✅ Editorial Lock 校验通过（{warnings} 个 WARN）。")
        else:
            print("\n✅ Editorial Lock 校验通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()
