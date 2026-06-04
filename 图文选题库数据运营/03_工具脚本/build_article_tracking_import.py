#!/usr/bin/env python3
import csv
import json
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import inspect_xlsx_raw as raw

ROOT = Path(__file__).resolve().parents[1]
BATCH_DATE = "2026-05-26"
OUTPUTS = ROOT / "02_数据备份与导入包"

FILES = [
    (Path("/Users/ltn/Downloads/图文_-_1-45牛科技.xlsx"), "牛科技"),
    (Path("/Users/ltn/Downloads/图文_-_1-19牛科技说.xlsx"), "牛科技说"),
]

FIELDS = [
    "文章标题",
    "发布日期",
    "头条文章ID",
    "文章链接",
    "发布账号",
    "产品品类",
    "文章类型",
    "标题结构模板",
    "展现量",
    "粉丝展现量",
    "阅读量",
    "粉丝阅读量",
    "CTR(%)",
    "完读率(%)",
    "平均阅读时长(s)",
    "点赞数",
    "评论数",
    "转发量",
    "分享量",
    "收藏数",
    "互动率(%)",
    "标题字数",
    "当前阶段",
    "是否限流",
    "限流原因",
    "表现分层",
    "主因归因",
    "辅因归因",
    "可复用点",
    "问题点",
    "下次动作",
    "建议改写标题",
    "归因来源",
    "复盘日期",
]


def num(value):
    if value in ("", None):
        return None
    try:
        f = float(str(value).replace(",", "").strip())
    except ValueError:
        return None
    if math.isfinite(f):
        return f
    return None


def intish(value):
    f = num(value)
    if f is None:
        return None
    return int(round(f))


def pct(value):
    f = num(value)
    if f is None:
        return None
    return round(f * 100, 2)


def category(title):
    t = title.lower()
    rules = [
        ("洗衣机", ["洗衣机", "洗烘", "烘干", "滚筒", "波轮", "dd直驱", "bldc", "电机"]),
        ("油烟机", ["油烟机", "烟机", "烟灶", "烟道", "厨房"]),
        ("空调", ["空调", "新风", "1.5匹", "挂机", "内机", "回南天"]),
        ("冰箱", ["冰箱", "保鲜", "制冷", "制冰", "双循环", "门体", "压缩机", "对开门", "十字门", "法式门"]),
        ("电视", ["电视", "mini led", "oled", "海信", "tcl", "创维", "索尼", "三星", "控光", "控色", "rtings"]),
        ("热水器", ["热水器", "双胆", "零冷水"]),
        ("显示器", ["显示器", "2k", "4k"]),
        ("手机", ["iphone", "手机"]),
        ("AI", ["ai", "上班了"]),
    ]
    for name, keys in rules:
        if any(k in t for k in keys):
            return name
    return "家电综合"


def article_type(title):
    t = title.lower()
    if any(k in t for k in ["避坑", "猫腻", "清洗", "滴水", "结冰", "开机", "噪音", "烟道", "先量", "处理方法", "diy", "坑", "别急", "散热片", "细菌", "安装", "维修费"]):
        return "教程避坑"
    if any(k in t for k in ["终局", "路线之争", "行业标准", "被中国赶走", "撤退", "变化", "国补", "价格预测", "越来越", "为什么越来越"]):
        return "趋势科普"
    return "选购横评"


def title_template(title):
    t = title.lower()
    brand_hits = len(re.findall(r"(海尔|美的|容声|东芝|华凌|海信|tcl|创维|小米|三星|索尼|lg|西门子)", t))
    if any(k in t for k in ["避坑", "猫腻", "不踩坑", "不会告诉", "白费", "坑", "别先", "别急", "没人提"]):
        return "内幕避坑型"
    if brand_hits >= 3 or "/" in title or "、" in title:
        return "多品牌对决型"
    if any(k in t for k in ["做了十年", "做十年", "拆开", "实录", "藏着", "真实差距", "才看清"]):
        return "内幕视角型"
    if any(k in t for k in ["为什么", "到底", "值不值", "差距在哪", "为何", "买了什么"]):
        return "反问悬念型"
    if any(k in t for k in ["vs", "还是", "选谁", "哪个", "横评", "pk", "对比"]):
        return "对比选择型"
    if brand_hits >= 1:
        return "品牌锚点型"
    return "其他"


def performance(imp, read, ctr, completion):
    imp = imp or 0
    read = read or 0
    ctr = ctr or 0
    completion = completion or 0
    if imp < 100 or read == 0:
        return "疑似限流"
    if (imp >= 40000 or read >= 3000) and ctr >= 7:
        return "爆款"
    if ctr >= 8 and read >= 100:
        return "点击强"
    if imp >= 10000 and read >= 500:
        return "推荐强"
    if completion >= 30 and read >= 100:
        return "承接强"
    return "普通"


def cause(layer, imp, read, ctr, completion):
    if layer == "疑似限流":
        return "疑似限流", ["标题弱"]
    if layer == "爆款":
        return ("标题强点击" if ctr >= 8 else "平台愿意推"), ["内容承接强", "公式可复用"]
    if layer == "点击强":
        return "标题强点击", ["公式可复用"]
    if layer == "推荐强":
        return "平台愿意推", ["标题强点击"] if ctr >= 6 else ["内容承接强"]
    if layer == "承接强":
        return "内容承接强", ["标题弱"] if ctr < 4 else ["公式可复用"]
    if ctr < 2:
        return "标题弱", ["选题过窄"]
    if imp < 1500:
        return "选题过窄", ["标题弱"]
    return "标题弱", []


def next_action(layer, cat, imp, read, ctr):
    core = cat not in {"手机", "AI"}
    if layer == "爆款":
        return "复用"
    if layer in {"点击强", "推荐强"} and read >= 500:
        return "复用"
    if layer == "疑似限流":
        return "冻结"
    if not core and ctr < 1:
        return "淘汰"
    if ctr < 2 and imp >= 1000:
        return "改标题再试"
    if layer in {"点击强", "推荐强", "承接强", "普通"}:
        return "改标题再试"
    return "降权"


def rewrite_title(title, cat, template):
    if template == "多品牌对决型":
        return f"{cat}别只看品牌，真正拉开差距的是这3个参数"
    if template == "内幕避坑型":
        return f"{cat}选购最容易踩的3个坑，卖场一般不会主动说"
    if template == "反问悬念型":
        return f"同样买{cat}，为什么有人用着省心有人天天后悔"
    if template == "品牌锚点型":
        return f"{cat}品牌怎么选，老评测只看这3个硬指标"
    if template == "内幕视角型":
        return f"做了十年{cat}评测，我发现差距藏在这3个细节里"
    return f"{cat}别急着买，先看懂这3个真正影响体验的参数"


def reusable_point(layer, template, cat):
    if layer == "爆款":
        return f"{cat}+{template} 已验证，展现/阅读/CTR 同时强，可作为下周优先复用结构。"
    if layer in {"点击强", "推荐强"}:
        return f"{template} 有点击或推荐信号，适合换角度继续测试。"
    if layer == "承接强":
        return "内容承接不错，但需要重新包装标题提高点击。"
    return "暂不作为核心公式复用，只保留为负样本或改题样本。"


def problem_point(layer, imp, read, ctr):
    if layer == "疑似限流":
        return "平台推荐入口弱或阅读为0，需检查标题关键词、品类热度和发布时间。"
    if ctr < 2 and imp >= 1000:
        return "平台给过展现但点击弱，标题缺少新信息差或利益点。"
    if imp < 1500:
        return "样本展现偏低，选题覆盖面或标题钩子不足。"
    if read < 100:
        return "阅读承接偏弱，标题承诺和正文吸引力需要复核。"
    return "暂无明显硬伤，继续观察同类样本。"


def read_rows(path, account):
    with zipfile.ZipFile(path) as zf:
        shared = raw.load_shared_strings(zf)
        rows = raw.read_sheet(zf, raw.sheet_paths(zf)[0][1], shared)
    headers = rows[0]
    data = []
    for row in rows[1:]:
        item = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        if item.get("标题"):
            item["发布账号"] = account
            data.append(item)
    return data


def main():
    OUTPUTS.mkdir(exist_ok=True)
    records = []
    source_rows = []
    for path, account in FILES:
        source_rows.extend(read_rows(path, account))

    for item in source_rows:
        title = str(item["标题"]).strip()
        imp = intish(item["展现量"]) or 0
        read = intish(item["阅读量"]) or 0
        ctr = pct(item["点击率"]) or 0
        completion = num(item["平均阅读完成率"]) or 0
        likes = intish(item["点赞量"]) or 0
        comments = intish(item["评论量"]) or 0
        reposts = intish(item["转发量"]) or 0
        shares = intish(item["分享量"]) or 0
        favs = intish(item["收藏量"]) or 0
        interact = round((likes + comments + reposts + shares + favs) / read * 100, 2) if read else 0
        cat = category(title)
        atype = article_type(title)
        tmpl = title_template(title)
        layer = performance(imp, read, ctr, completion)
        main_cause, sub_causes = cause(layer, imp, read, ctr, completion)
        action = next_action(layer, cat, imp, read, ctr)
        limit_status = "疑似限流" if layer == "疑似限流" else "正常"
        limit_reason = "展现量低于100或阅读量为0，先作为疑似限流样本复盘。" if layer == "疑似限流" else None
        review_date = BATCH_DATE
        rewrite = rewrite_title(title, cat, tmpl) if action == "改标题再试" else None

        record = {
            "文章标题": title,
            "发布日期": item["发布时间"],
            "头条文章ID": str(item["ID"]).strip(),
            "文章链接": str(item["链接"]).strip(),
            "发布账号": item["发布账号"],
            "产品品类": cat,
            "文章类型": atype,
            "标题结构模板": tmpl,
            "展现量": imp,
            "粉丝展现量": intish(item["粉丝展现量"]) or 0,
            "阅读量": read,
            "粉丝阅读量": intish(item["粉丝阅读量"]) or 0,
            "CTR(%)": ctr,
            "完读率(%)": completion,
            "平均阅读时长(s)": intish(item["平均阅读时长"]) or 0,
            "点赞数": likes,
            "评论数": comments,
            "转发量": reposts,
            "分享量": shares,
            "收藏数": favs,
            "互动率(%)": interact,
            "标题字数": len(title),
            "当前阶段": "已发布",
            "是否限流": limit_status,
            "限流原因": limit_reason,
            "表现分层": layer,
            "主因归因": main_cause,
            "辅因归因": sub_causes if sub_causes else None,
            "可复用点": reusable_point(layer, tmpl, cat),
            "问题点": problem_point(layer, imp, read, ctr),
            "下次动作": action,
            "建议改写标题": rewrite,
            "归因来源": "历史补标",
            "复盘日期": review_date,
        }
        records.append(record)

    rows = [[record.get(field) for field in FIELDS] for record in records]
    batch = {"fields": FIELDS, "rows": rows}
    (OUTPUTS / f"文章追踪_最新64篇导入包_{BATCH_DATE.replace('-', '')}.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = OUTPUTS / f"文章追踪_最新64篇复盘预览_{BATCH_DATE.replace('-', '')}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    by_account = {}
    by_cat = {}
    by_layer = {}
    for r in records:
        by_account.setdefault(r["发布账号"], []).append(r)
        by_cat.setdefault(r["产品品类"], []).append(r)
        by_layer[r["表现分层"]] = by_layer.get(r["表现分层"], 0) + 1

    def avg(items, key):
        vals = [x[key] for x in items if x[key] is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0

    lines = [
        "# 文章追踪最新数据导入与复盘摘要",
        "",
        f"- 数据批次：{BATCH_DATE}",
        f"- 来源文件：牛科技 45 篇；牛科技说 19 篇",
        f"- 导入记录：{len(records)} 篇",
        "",
        "## 账号表现",
        "",
        "| 账号 | 篇数 | 总展现 | 总阅读 | 平均CTR(%) | 平均阅读量 | 爆款数 | 疑似限流数 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for account, items in sorted(by_account.items()):
        lines.append(
            f"| {account} | {len(items)} | {sum(x['展现量'] for x in items)} | {sum(x['阅读量'] for x in items)} | "
            f"{avg(items, 'CTR(%)')} | {avg(items, '阅读量')} | "
            f"{sum(1 for x in items if x['表现分层']=='爆款')} | {sum(1 for x in items if x['表现分层']=='疑似限流')} |"
        )
    lines += [
        "",
        "## 表现分层",
        "",
        "| 分层 | 数量 |",
        "|---|---:|",
    ]
    for layer, count in sorted(by_layer.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {layer} | {count} |")
    lines += [
        "",
        "## 品类阅读量排行",
        "",
        "| 品类 | 篇数 | 平均展现 | 平均阅读 | 平均CTR(%) | 爆款数 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cat, items in sorted(by_cat.items(), key=lambda x: avg(x[1], "阅读量"), reverse=True):
        lines.append(
            f"| {cat} | {len(items)} | {avg(items, '展现量')} | {avg(items, '阅读量')} | "
            f"{avg(items, 'CTR(%)')} | {sum(1 for x in items if x['表现分层']=='爆款')} |"
        )
    lines += [
        "",
        "## 高阅读样本 Top 10",
        "",
        "| 标题 | 账号 | 品类 | 展现 | 阅读 | CTR(%) | 分层 | 下次动作 |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for r in sorted(records, key=lambda x: x["阅读量"], reverse=True)[:10]:
        lines.append(
            f"| {r['文章标题']} | {r['发布账号']} | {r['产品品类']} | {r['展现量']} | {r['阅读量']} | {r['CTR(%)']} | {r['表现分层']} | {r['下次动作']} |"
        )
    (OUTPUTS / f"文章追踪_最新64篇导入复盘摘要_{BATCH_DATE.replace('-', '')}.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"records": len(records), "csv": str(csv_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
