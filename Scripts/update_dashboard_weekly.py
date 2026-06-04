#!/usr/bin/env python3
"""
update_dashboard_weekly.py — 更新周报看板的日期filter（周二~下周一周期）

用法:
    python3 Scripts/update_dashboard_weekly.py [--dry-run]

每次周二周会后运行，自动计算刚结束的周期和上一周期：
- 本周期：上周二 ~ 本周一
- 上周期：上上周二 ~ 上周一
"""

import subprocess
import json
import sys
from datetime import datetime, timedelta

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
DASHBOARD_ID = "blkyHJB3y9alAHIL"
LARK = "/opt/homebrew/bin/lark-cli"

# 周报看板中6个需要日期filter的stats组件（本周/上周各3个）
# key = block name (用于查找block_id)
WEEKLY_BLOCK_NAMES = [
    "本周发文数",
    "本周总阅读量",
    "本周平均CTR",
    "本周总展现量",
    "本周总收藏",
]

LAST_WEEK_BLOCK_NAMES = [
    "上周发文数",
    "上周总阅读量",
    "上周平均CTR",
    "上周总展现量",
    "上周总收藏",
]


def calc_periods():
    """计算本周期和上周期的日期范围（周二~下周一）"""
    today = datetime.now()

    # 找到最近的一个周一
    days_since_monday = today.weekday()  # Monday=0
    last_monday = today - timedelta(days=days_since_monday)
    last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # 上周二~本周一 = 刚结束的完整周期（本周期）
    this_period_start = last_monday - timedelta(days=6)  # Tuesday
    this_period_end = last_monday + timedelta(days=1)    # Tuesday next week (exclusive)

    # 上上周二~上周一 = 上一周期
    last_period_start = last_monday - timedelta(days=13)  # Tuesday
    last_period_end = last_monday - timedelta(days=6)     # Tuesday (exclusive)

    return this_period_start, this_period_end, last_period_start, last_period_end


def get_block_ids():
    """获取看板中所有组件的name->id映射"""
    cmd = [LARK, "base", "+dashboard-block-list",
           "--base-token", BASE_TOKEN, "--dashboard-id", DASHBOARD_ID]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error listing blocks: {result.stderr[:200]}")
        sys.exit(1)

    data = json.loads(result.stdout)
    name_to_id = {}
    for b in data["data"]["items"]:
        name_to_id[b["name"]] = b["block_id"]
    return name_to_id


def update_block_filter(block_id, date_start, date_end, dry_run=False):
    """更新组件的日期filter，保留非日期条件（如表现分层）"""
    # 先获取当前block的data_config
    cmd = [LARK, "base", "+dashboard-block-get",
           "--base-token", BASE_TOKEN, "--dashboard-id", DASHBOARD_ID,
           "--block-id", block_id]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error getting block {block_id}: {result.stderr[:200]}")
        return False

    data = json.loads(result.stdout)
    current_config = data["data"]["block"]["data_config"]

    # 保留非日期条件，替换日期条件
    old_conditions = current_config.get("filter", {}).get("conditions", [])
    non_date_conditions = [c for c in old_conditions if c.get("field_name") != "发布日期"]
    filter_config = {
        "conjunction": "and",
        "conditions": [
            {"field_name": "发布日期", "operator": "isGreater", "value": date_start.strftime("%Y-%m-%d 00:00:00")},
            {"field_name": "发布日期", "operator": "isLess", "value": date_end.strftime("%Y-%m-%d 00:00:00")},
        ] + non_date_conditions
    }

    # 构建update的data_config（只保留需要的字段）
    update_config = {}
    for key in ["table_name", "count_all", "series", "group_by"]:
        if key in current_config:
            update_config[key] = current_config[key]
    update_config["filter"] = filter_config

    if dry_run:
        print(f"  [DRY RUN] Would update {block_id} with filter:")
        print(f"    {date_start.strftime('%Y-%m-%d')} ~ {date_end.strftime('%Y-%m-%d')}")
        return True

    cmd = [LARK, "base", "+dashboard-block-update",
           "--base-token", BASE_TOKEN, "--dashboard-id", DASHBOARD_ID,
           "--block-id", block_id,
           "--data-config", json.dumps(update_config, ensure_ascii=False)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Error updating block {block_id}: {result.stderr[:200]}")
        return False

    data = json.loads(result.stdout)
    return data.get("ok", False)


def count_baokuan(this_start, this_end, last_start, last_end):
    """从文章追踪表中计算本周和上周的爆款数（展现量≥10000）"""
    TABLE_ID = "tblA8dT3x3bdOF9Y"
    cmd = [LARK, "base", "+record-list",
           "--base-token", BASE_TOKEN, "--table-id", TABLE_ID,
           "--field-id", "发布日期", "--field-id", "展现量",
           "--format", "json", "--limit", "200"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ 无法读取记录计算爆款数")
        return 0, 0

    data = json.loads(result.stdout)
    field_names = data["data"]["fields"]
    records = data["data"]["data"]
    di = field_names.index("发布日期")
    vi = field_names.index("展现量")

    this_s = this_start.strftime("%Y-%m-%d")
    this_e = (this_end - timedelta(days=1)).strftime("%Y-%m-%d")
    last_s = last_start.strftime("%Y-%m-%d")
    last_e = (last_end - timedelta(days=1)).strftime("%Y-%m-%d")

    this_count = sum(
        1 for r in records
        if str(r[di]) >= this_s and str(r[di]) <= this_e
        and isinstance(r[vi], (int, float)) and r[vi] >= 10000
    )
    last_count = sum(
        1 for r in records
        if str(r[di]) >= last_s and str(r[di]) <= last_e
        and isinstance(r[vi], (int, float)) and r[vi] >= 10000
    )
    return this_count, last_count


def count_interact(this_start, this_end, last_start, last_end):
    """从文章追踪表中计算本周和上周的总互动数（点赞+评论+收藏）"""
    TABLE_ID = "tblA8dT3x3bdOF9Y"
    cmd = [LARK, "base", "+record-list",
           "--base-token", BASE_TOKEN, "--table-id", TABLE_ID,
           "--field-id", "发布日期", "--field-id", "点赞数",
           "--field-id", "评论数", "--field-id", "收藏数",
           "--format", "json", "--limit", "200"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ 无法读取记录计算互动数")
        return 0, 0

    data = json.loads(result.stdout)
    field_names = data["data"]["fields"]
    records = data["data"]["data"]
    di = field_names.index("发布日期")
    li = field_names.index("点赞数")
    ci = field_names.index("评论数")
    si = field_names.index("收藏数")

    this_s = this_start.strftime("%Y-%m-%d")
    this_e = (this_end - timedelta(days=1)).strftime("%Y-%m-%d")
    last_s = last_start.strftime("%Y-%m-%d")
    last_e = (last_end - timedelta(days=1)).strftime("%Y-%m-%d")

    this_total = sum(
        r[li] + r[ci] + r[si] for r in records
        if str(r[di]) >= this_s and str(r[di]) <= this_e
        and isinstance(r[li], (int, float))
    )
    last_total = sum(
        r[li] + r[ci] + r[si] for r in records
        if str(r[di]) >= last_s and str(r[di]) <= last_e
        and isinstance(r[li], (int, float))
    )
    return int(this_total), int(last_total)


def main():
    dry_run = "--dry-run" in sys.argv

    this_start, this_end, last_start, last_end = calc_periods()

    print(f"=== 周报看板日期更新 ===")
    print(f"本周期: {this_start.strftime('%Y-%m-%d (Tue)')} ~ {this_end.strftime('%Y-%m-%d (Tue)')} (exclusive)")
    print(f"上周期: {last_start.strftime('%Y-%m-%d (Tue)')} ~ {last_end.strftime('%Y-%m-%d (Tue)')} (exclusive)")
    print()

    name_to_id = get_block_ids()
    print(f"找到 {len(name_to_id)} 个组件")

    # 更新本周组件
    for name in WEEKLY_BLOCK_NAMES:
        block_id = name_to_id.get(name)
        if not block_id:
            print(f"  ⚠ 未找到组件: {name}")
            continue
        print(f"更新 {name} ({block_id[:16]}...)")
        ok = update_block_filter(block_id, this_start, this_end, dry_run)
        print(f"  {'✓' if ok else '✗'}")

    # 更新上周组件
    for name in LAST_WEEK_BLOCK_NAMES:
        block_id = name_to_id.get(name)
        if not block_id:
            print(f"  ⚠ 未找到组件: {name}")
            continue
        print(f"更新 {name} ({block_id[:16]}...)")
        ok = update_block_filter(block_id, last_start, last_end, dry_run)
        print(f"  {'✓' if ok else '✗'}")

    # 计算爆款数（展现量≥10000），写入统计周期文本
    this_baokuan, last_baokuan = count_baokuan(this_start, this_end, last_start, last_end)
    this_interact, last_interact = count_interact(this_start, this_end, last_start, last_end)

    # 更新统计周期文本
    text_block_id = name_to_id.get("统计周期")
    if text_block_id:
        weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
        this_end_display = this_end - timedelta(days=1)
        last_end_display = last_end - timedelta(days=1)
        text = (
            f"**本周期**：{this_start.month}月{this_start.day}日({weekday_names[this_start.weekday()]}) "
            f"~ {this_end_display.month}月{this_end_display.day}日({weekday_names[this_end_display.weekday()]}) "
            f"— 爆款 {this_baokuan} 篇（展现≥1万）· 总互动 {this_interact}（赞+评+藏）\n"
            f"**上周期**：{last_start.month}月{last_start.day}日({weekday_names[last_start.weekday()]}) "
            f"~ {last_end_display.month}月{last_end_display.day}日({weekday_names[last_end_display.weekday()]}) "
            f"— 爆款 {last_baokuan} 篇（展现≥1万）· 总互动 {last_interact}（赞+评+藏）\n"
            f"统计周期为周二至下周一，周会时刷新"
        )
        if dry_run:
            print(f"  [DRY RUN] Would update 统计周期 text with 爆款: 本周{this_baokuan} 上周{last_baokuan}")
        else:
            cmd = [LARK, "base", "+dashboard-block-update",
                   "--base-token", BASE_TOKEN, "--dashboard-id", DASHBOARD_ID,
                   "--block-id", text_block_id,
                   "--data-config", json.dumps({"text": text}, ensure_ascii=False)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            ok = json.loads(result.stdout).get("ok", False)
            print(f"更新 统计周期文本（本周爆款{this_baokuan}，上周爆款{last_baokuan}）: {'✓' if ok else '✗'}")

    print("\nDone.")


if __name__ == "__main__":
    main()
