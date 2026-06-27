import sys
import yaml
import re
import argparse
from pathlib import Path

def print_error(msg):
    print(f"❌ ERROR: {msg}")

def print_warn(msg):
    print(f"⚠️ WARN: {msg}")

def main():
    parser = argparse.ArgumentParser(description="Check Visual Lock compliance")
    parser.add_argument("draft_path", type=Path, help="Path to the final draft markdown file")
    parser.add_argument("--lock", type=Path, required=True, help="Path to the editorial_lock.yaml file")
    parser.add_argument("--visual", type=Path, help="Path to the visual_plan.yaml file")
    args = parser.parse_args()

    if not args.lock.exists():
        print_error(f"Editorial lock file not found: {args.lock}")
        sys.exit(1)

    if not args.draft_path.exists():
        print_error(f"Draft file not found: {args.draft_path}")
        sys.exit(1)

    try:
        with open(args.lock, 'r', encoding='utf-8') as f:
            lock_data = yaml.safe_load(f)
    except Exception as e:
        print_error(f"Failed to parse editorial lock YAML: {e}")
        sys.exit(1)

    with open(args.draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read()

    errors = 0
    warnings = 0

    # ========== V6. 无缺失占位 ==========
    if "此处插图缺失：未指定" in draft_content:
        print_error('终稿中存在"此处插图缺失：未指定"，视觉流程未闭环')
        errors += 1

    # ========== Load visual_plan if provided ==========
    visual_plan = None
    if args.visual and args.visual.exists():
        try:
            with open(args.visual, 'r', encoding='utf-8') as f:
                visual_plan = yaml.safe_load(f)
        except Exception as e:
            print_error(f"Failed to parse visual_plan.yaml: {e}")
            errors += 1

    # ========== V1. 封面文案承接主冲突 ==========
    main_kws = [kw for kw in lock_data.get("main_conflict_keywords", []) if kw.strip()]

    if visual_plan:
        cover = visual_plan.get("cover", {})
        cover_text = ""
        if isinstance(cover, dict):
            cover_text = " ".join([
                str(cover.get("main_copy", "")),
                str(cover.get("sub_copy", "")),
                str(cover.get("title", "")),
                str(cover.get("description", "")),
            ])
        elif isinstance(cover, str):
            cover_text = cover

        if cover_text.strip():
            cover_main_hits = sum(1 for kw in main_kws if kw in cover_text)
            if cover_main_hits < 1:
                print_error(f"封面文案未承接主冲突，main_conflict_keywords 无一命中。封面文案: {cover_text[:100]}")
                errors += 1

            # V2. 封面不违反策略
            for f_pos in lock_data.get("forbidden_positioning", []):
                if f_pos.strip() and f_pos in cover_text:
                    print_error(f"封面文案触犯了禁忌定位词: {f_pos}")
                    errors += 1

            # V3. 不做视觉拉踩
            visual_lock = lock_data.get("visual_lock", {})
            cover_must_not = visual_lock.get("cover_must_not", [])
            lash_words = ["做暗", "做脏", "做差", "大红叉", "吊打", "缩水", "阉割", "丐版"]
            for w in lash_words:
                if w in cover_text:
                    print_error(f"封面存在视觉拉踩词: {w}")
                    errors += 1
        else:
            print_warn("visual_plan 中缺少封面文案信息 (cover.main_copy / cover.sub_copy)")
            warnings += 1

        # V4. 参数来自证据
        must_evidences = lock_data.get("must_use_evidence", [])
        evidence_claims = [ev.get("claim", "") for ev in must_evidences if ev.get("claim")]
        # Check if visual_plan references parameters - just a soft check
        slots = visual_plan.get("slots", visual_plan.get("infographic_slots", []))
        if isinstance(slots, list):
            for slot in slots:
                if isinstance(slot, dict):
                    eid = slot.get("evidence_id", "")
                    if eid and not any(ev.get("evidence_id") == eid for ev in must_evidences):
                        print_warn(f"图位 {slot.get('slot_id', '?')} 引用了 evidence_id={eid}，但不在 must_use_evidence 中")
                        warnings += 1

    # ========== V5. 正文图位全覆盖 ==========
    # Find all image placeholders in the draft
    placeholders = re.findall(r'\[此处插入信息图(\d+)：([^\]]*)\]', draft_content)
    inserted_images = re.findall(r'!\[信息图(\d+)[^\]]*\]', draft_content)
    all_image_ids = set([p[0] for p in placeholders] + [i for i in inserted_images])

    if visual_plan and all_image_ids:
        slots = visual_plan.get("slots", visual_plan.get("infographic_slots", []))
        if isinstance(slots, list):
            slot_ids = set()
            for slot in slots:
                if isinstance(slot, dict):
                    sid = str(slot.get("slot_id", slot.get("id", "")))
                    # Extract number from slot_id like "info_1" -> "1"
                    nums = re.findall(r'\d+', sid)
                    if nums:
                        slot_ids.add(nums[0])
                    slot_ids.add(sid)

            for img_id in all_image_ids:
                if img_id not in slot_ids and f"info_{img_id}" not in slot_ids:
                    print_error(f"正文图位 {img_id} 在 visual_plan.yaml 中没有对应 slot")
                    errors += 1

    # ========== V7. 每个图位结构完整 ==========
    if visual_plan:
        slots = visual_plan.get("slots", visual_plan.get("infographic_slots", []))
        required_slot_fields = ["function", "paragraph", "core_relation"]
        if isinstance(slots, list):
            for slot in slots:
                if isinstance(slot, dict):
                    sid = slot.get("slot_id", slot.get("id", "unknown"))
                    for field in required_slot_fields:
                        if not slot.get(field):
                            print_error(f"图位 {sid} 缺少必填字段: {field}")
                            errors += 1

    # ========== RESULT ==========
    if errors > 0:
        print(f"\n❌ Visual Lock 校验失败，共 {errors} 个 ERROR，{warnings} 个 WARN。")
        sys.exit(1)
    else:
        if warnings > 0:
            print(f"\n✅ Visual Lock 校验通过（{warnings} 个 WARN）。")
        else:
            print("\n✅ Visual Lock 校验通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()
