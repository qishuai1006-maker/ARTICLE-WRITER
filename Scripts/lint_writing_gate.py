#!/usr/bin/env python3
import sys
import argparse
import re
import yaml

def lint_writing_gate(draft_path, evidence_path=None, research_path=None):
    try:
        with open(draft_path, 'r', encoding='utf-8') as f:
            draft = f.read()
    except Exception as e:
        print(f"ERROR: Cannot read draft file {draft_path}: {e}")
        sys.exit(1)

    # Check L3 gate_pass
    if research_path:
        try:
            with open(research_path, 'r', encoding='utf-8') as f:
                l3 = f.read()
            l3_fm_match = re.match(r'^---\n(.*?)\n---', l3, re.DOTALL)
            if l3_fm_match:
                l3_meta = yaml.safe_load(l3_fm_match.group(1))
                if l3_meta.get('gate_pass') != True:
                    print("ERROR: L3 调研报告 gate_pass is not true")
                    sys.exit(1)
        except Exception as e:
            print(f"ERROR reading research file: {e}")
            sys.exit(1)

    # Check draft frontmatter 5 flow cards
    draft_fm_match = re.match(r'^---\n(.*?)\n---', draft, re.DOTALL)
    if not draft_fm_match:
        print("ERROR: Draft missing YAML frontmatter.")
        sys.exit(1)
        
    try:
        draft_meta = yaml.safe_load(draft_fm_match.group(1))
    except Exception as e:
        print(f"ERROR: Invalid Draft YAML format: {e}")
        sys.exit(1)
        
    flow_cards = ['hook_15_chars', 'hero_conflict', 'contrarian_insight', 'deadline_save', 'comment_trigger']
    for card in flow_cards:
        if card not in draft_meta:
            print(f"ERROR: Missing flow card '{card}' in Draft frontmatter.")
            sys.exit(1)

    # Check evidence card exists and is not empty
    if evidence_path:
        try:
            with open(evidence_path, 'r', encoding='utf-8') as f:
                ev_content = f.read()
            if len(ev_content.strip()) < 20:
                print("ERROR: Evidence card is empty or too short.")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: Cannot read evidence card: {e}")
            sys.exit(1)

    # NO UNSURE
    if 'UNSURE' in draft:
        print("ERROR: Draft contains 'UNSURE' facts.")
        sys.exit(1)

    # Check Business Strategy
    from pathlib import Path
    draft_dir = Path(draft_path).parent
    proposal_path = draft_dir / "00_选题方案表.md"
    if proposal_path.exists():
        try:
            with open(proposal_path, 'r', encoding='utf-8') as f:
                proposal = f.read()
            if "不拉踩" in proposal:
                banned_negative = ["阉割版", "丐版", "别碰", "消费陷阱", "垃圾", "智商税", "吃大亏"]
                for word in banned_negative:
                    if word in draft:
                        print(f"ERROR: 业务策略要求【不拉踩】，但稿件中出现了强负面词：{word}")
                        sys.exit(1)
        except Exception as e:
            print(f"WARNING: Cannot read proposal file {proposal_path}: {e}")

    # NO internal source words
    banned_words = ["我查了", "资料显示", "根据百度", "笔者查阅", "据资料"]
    for w in banned_words:
        if w in draft:
            print(f"ERROR: Draft contains internal source word: {w}")
            sys.exit(1)

    # Check semantic elements
    # 至少 3 处参数翻译词汇
    param_translations = ["这意味着", "落到家里就是", "说白了就是", "通俗来讲", "说人话就是", "大白话来说", "直接点说", "直接影响"]
    pt_count = sum(draft.count(w) for w in param_translations)
    if pt_count < 3:
        print("ERROR: 至少需要 3 处参数翻译提示词 (如 '这意味着', '落到家里就是' 等)")
        sys.exit(1)

    # 至少有适合谁/不适合谁，或边界判断
    if "适合" not in draft and "不适合" not in draft and "边界" not in draft and "人群" not in draft:
        print("ERROR: 至少要有'适合谁/不适合谁'或明确购买边界")
        sys.exit(1)

    # 至少一个评论钩子
    if "?" not in draft and "？" not in draft and "评论区" not in draft and "大家觉得" not in draft:
        print("ERROR: 至少要有 1 个评论钩子 (问号或提示语)")
        sys.exit(1)

    # 决策物
    if "建议" not in draft and "结论" not in draft and "直接上" not in draft and "没必要" not in draft:
        print("ERROR: 结尾需要决策物 (明确的购买建议)")
        sys.exit(1)

    if len(draft) < 300:
        print("ERROR: Draft too short")
        sys.exit(1)

    print("PASS: lint_writing_gate passed.")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('draft_path')
    parser.add_argument('--evidence', dest='evidence_path')
    parser.add_argument('--research', dest='research_path')
    args = parser.parse_args()
    lint_writing_gate(args.draft_path, args.evidence_path, args.research_path)
