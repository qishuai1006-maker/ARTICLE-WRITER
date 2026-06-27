#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


TYPE_HINTS = [
    ("型号对比", ["对比", "型号", "系列", "怎么选", "区别"]),
    ("价格段推荐", ["预算", "价位", "价格段", "元以内", "元以上"]),
    ("参数解释", ["参数", "风量", "静压", "亮度", "分区", "匹数", "洗净比", "能效"]),
    ("避坑提醒", ["避坑", "别买", "不建议", "坑", "误区"]),
    ("安装教程", ["安装", "预留", "尺寸", "孔位", "烟道", "水电"]),
    ("选购攻略", ["选", "买", "挑", "攻略", "建议"]),
]


def split_paragraphs(text):
    lines = [line.strip() for line in text.splitlines()]
    paragraphs = []
    for line in lines:
        if not line:
            continue
        if line.startswith("!["):
            continue
        if line.startswith("[此处插入") or line.startswith("【此处插入"):
            continue
        paragraphs.append(line)
    return paragraphs


def detect_title(paragraphs):
    if not paragraphs:
        return ""
    first = paragraphs[0]
    return re.sub(r"^#+\s*", "", first).strip()


def detect_type(text):
    scores = []
    for type_name, words in TYPE_HINTS:
        score = sum(text.count(word) for word in words)
        scores.append((score, type_name))
    scores.sort(reverse=True)
    return scores[0][1] if scores and scores[0][0] else "选购攻略"


def choose_body_positions(paragraphs):
    candidates = []
    for idx, para in enumerate(paragraphs[1:], start=1):
        if len(para) < 18:
            continue
        score = 0
        for word in ["参数", "风量", "静压", "亮度", "分区", "匹数", "洗净比", "预算", "价位", "型号", "对比", "建议", "清单", "顺序"]:
            if word in para:
                score += 2
        if re.search(r"\d", para):
            score += 1
        if score:
            candidates.append((idx, score, para))
    early_candidates = [item for item in candidates if item[0] <= len(paragraphs) * 0.55]
    early_candidates.sort(key=lambda item: (item[0], -item[1]))
    first = early_candidates[0][0] if early_candidates else max(1, len(paragraphs) // 3)

    late_candidates = [item for item in candidates if item[0] > len(paragraphs) * 0.45 and abs(item[0] - first) > 2]
    late_candidates.sort(key=lambda item: (-item[1], item[0]))
    second = late_candidates[0][0] if late_candidates else max(first + 3, int(len(paragraphs) * 0.65))
    second = min(second, max(1, len(paragraphs) - 2))
    return first, second


def main():
    parser = argparse.ArgumentParser(description="Draft a three-image plan for a Chinese appliance article.")
    parser.add_argument("article", help="Markdown/plain text article path")
    parser.add_argument("--topic", default="", help="Optional product category/topic")
    args = parser.parse_args()

    text = Path(args.article).read_text(encoding="utf-8")
    paragraphs = split_paragraphs(text)
    title = detect_title(paragraphs)
    article_type = detect_type(text)
    pos1, pos2 = choose_body_positions(paragraphs)

    plan = {
        "title": title,
        "topic": args.topic,
        "article_type": article_type,
        "images": [
            {
                "id": "cover",
                "role": "提升点击率，表达文章最大冲突或收益",
                "ratio": "16:9",
                "suggested_position": "标题或正文开头之后",
                "layout": "大主体特写或场景痛点",
                "prompt_status": "需要人工补齐封面短标题和画面主体",
            },
            {
                "id": "info1",
                "role": "解释第一个核心参数、结构或对比关系",
                "ratio": "16:9",
                "suggested_position": f"第 {pos1 + 1} 段之后",
                "anchor_paragraph": paragraphs[pos1] if pos1 < len(paragraphs) else "",
                "layout": "四卡片 / 左右对比 / 结构图",
                "prompt_status": "需要从锚点段落提取精确文字、数字和单位",
            },
            {
                "id": "info2",
                "role": "帮助读者做最终购买或检查决策",
                "ratio": "16:9",
                "suggested_position": f"第 {pos2 + 1} 段之后",
                "anchor_paragraph": paragraphs[pos2] if pos2 < len(paragraphs) else "",
                "layout": "表格 / 流程 / 清单 / 人群匹配",
                "prompt_status": "需要从中后段提取预算、场景、型号或结论清单",
            },
        ],
        "qa_reminder": [
            "固定三张图，不多不少",
            "信息图数字、单位、型号必须和文章一致",
            "封面不要 logo、价格、二维码、水印、绝对化词",
            "正文图不要连续堆放，必须插在对应段落后",
        ],
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
