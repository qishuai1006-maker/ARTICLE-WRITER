#!/usr/bin/env python3
"""选题库数据运营看板精修脚本 — 删除旧26组件 + 创建精修版26组件"""
import json
import subprocess
import sys

BASE = "CFF5boINWaBpb4sqlFVceacEn5c"
DASHBOARD = "blkfM1WeXiIeF7ZB"

OLD_BLOCKS = [
    "chtcnL0039vliptm0FZMwdbj1ed",
    "chtcniGDqxK8WSUrm4lgZ3GuRDd",
    "chtcn9sKzx4TQ6q7s8gHEQDxxVh",
    "chtcnEs7oHtvseZvQ2Pkh7os22c",
    "chtcnI2zdB4PPv7jheXVWm75Nbc",
    "chtcntdB2A7KEPeFavGWWjosmVb",
    "chtcnK50ErMkSscJyE5AlYli4Zb",
    "chtcn3YKZAzK6Grjju4yZC1k0Jc",
    "chtcn5iskBylzB0wAmoOYwphOYO",
    "chtcnW4hzGdDSPbdlpNkGx9ZLWf",
    "chtcnI2dAIFtdrvuooVMbxF1RCe",
    "chtcnSVH9BjZbo7Qj3pbNGs1EYc",
    "chtcn5VkKiqh6pv2qozUMcHj50c",
    "chtcn8fedOyRdjBsfNyYsrjdxth",
    "chtcnRVEKysAq3JBWnprR6YIjrd",
    "chtcnbiguHwu8VKUwjJF6yQZ9qd",
    "chtcnoExFXibpJT2jjOKJQbgwrd",
    "chtcnxuT5oGTiAreGpsZxaI1HBe",
    "chtcn1dl2wqWpWqOu4BWQZFgHub",
    "chtcnTQdpaCbNk5BrNclWyf0CLc",
    "chtcn5gPDNpKQE2mIJfxCQ7lmTd",
    "chtcnsAaQdFnXui4MrO0YYj4Ccg",
    "chtcnzQrKKNjCsAUqpbC4n6DXUb",
    "chtcnJygxmTv0ymvhrF6h49RNbg",
    "chtcnSyWXEUamhzltfsLEN9s63F",
    "chtcnx2WitUQtGdVpB5Z0mlc9le",
]


def lark_cli(*args, input_json=None):
    cmd = ["/opt/homebrew/bin/lark-cli"] + list(args) + ["--as", "user"]
    proc = subprocess.run(cmd, capture_output=True, text=True, input=input_json)
    if proc.returncode != 0:
        print(f"FAILED: {' '.join(args)}")
        print(f"  stdout: {proc.stdout[:200]}")
        print(f"  stderr: {proc.stderr[:200]}")
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout


def delete_old_blocks():
    print(f"\n=== 删除旧 {len(OLD_BLOCKS)} 个组件 ===")
    success = 0
    for bid in OLD_BLOCKS:
        result = lark_cli(
            "base", "+dashboard-block-delete",
            "--base-token", BASE,
            "--dashboard-id", DASHBOARD,
            "--block-id", bid,
            "--yes",
        )
        if result is not None:
            success += 1
            print(f"  deleted {bid}")
        else:
            print(f"  SKIP {bid}")
    print(f"  删除完成: {success}/{len(OLD_BLOCKS)}")
    return success


def filt(*conditions):
    return {"conjunction": "and", "conditions": list(conditions)}


def cond(field, operator, value=None):
    item = {"field_name": field, "operator": operator}
    if value is not None:
        item["value"] = value
    return item


def count(table, filter_=None, group_by=None):
    data = {"table_name": table, "count_all": True}
    if filter_:
        data["filter"] = filter_
    if group_by:
        data["group_by"] = group_by
    return data


def stat_sum(field, table="文章追踪", filter_=None):
    data = {"table_name": table, "series": [{"field_name": field, "rollup": "SUM"}]}
    if filter_:
        data["filter"] = filter_
    return data


def stat_avg(field, table="文章追踪", filter_=None):
    data = {"table_name": table, "series": [{"field_name": field, "rollup": "AVERAGE"}]}
    if filter_:
        data["filter"] = filter_
    return data


def group(field, sort="value", order="desc"):
    return [{"field_name": field, "mode": "integrated", "sort": {"type": sort, "order": order}}]


def series_group(metric, dim, rollup="SUM", table="文章追踪", filter_=None):
    data = {
        "table_name": table,
        "series": [{"field_name": metric, "rollup": rollup}],
        "group_by": group(dim),
    }
    if filter_:
        data["filter"] = filter_
    return data


NEW_BLOCKS = [
    # === A 区：总览指标 ===
    ("A01｜总文章数", "statistics", count("文章追踪")),
    ("A02｜总展现量", "statistics", stat_sum("展现量")),
    ("A03｜总阅读量", "statistics", stat_sum("阅读量")),
    ("A04｜平均CTR", "statistics", stat_avg("CTR(%)")),
    ("A05｜爆款数", "statistics", count("文章追踪", filt(cond("表现分层", "is", "爆款")))),
    ("A06｜疑似限流数", "statistics", count("文章追踪", filt(cond("是否限流", "is", "疑似限流")))),
    ("A07｜待发布排期数", "statistics", count("发稿排期", filt(cond("选题状态", "is", "已排期")))),

    # === B 区：账号表现 ===
    ("B01｜账号总阅读量", "column", series_group("阅读量", "发布账号")),
    ("B02｜账号平均CTR", "column", series_group("CTR(%)", "发布账号", "AVERAGE")),
    ("B03｜账号文章数", "column", count("文章追踪", group_by=group("发布账号"))),
    ("B04｜账号爆款数", "column", count("文章追踪", filt(cond("表现分层", "is", "爆款")), group("发布账号"))),

    # === C 区：品类策略 ===
    ("C01｜品类平均阅读量", "column", series_group("阅读量", "产品品类", "AVERAGE")),
    ("C02｜品类平均CTR", "column", series_group("CTR(%)", "产品品类", "AVERAGE")),
    ("C03｜品类文章数分布", "ring", count("文章追踪", group_by=group("产品品类"))),
    ("C04｜品类总阅读量", "column", series_group("阅读量", "产品品类")),

    # === D 区：标题与文章类型 ===
    ("D01｜标题结构平均阅读量", "column", series_group("阅读量", "标题结构模板", "AVERAGE")),
    ("D02｜标题结构平均CTR", "column", series_group("CTR(%)", "标题结构模板", "AVERAGE")),
    ("D03｜文章类型平均阅读量", "column", series_group("阅读量", "文章类型", "AVERAGE")),
    ("D04｜表现分层分布", "ring", count("文章追踪", group_by=group("表现分层"))),

    # === E 区：排行 ===
    ("E01｜阅读量排行", "bar", series_group("阅读量", "文章标题")),
    ("E02｜展现量排行", "bar", series_group("展现量", "文章标题")),
    ("E03｜CTR排行", "bar", series_group("CTR(%)", "文章标题", "AVERAGE", filter_=filt(cond("阅读量", "isGreater", 100)))),

    # === F 区：风险与动作 ===
    ("F01｜下次动作分布", "ring", count("文章追踪", group_by=group("下次动作"))),
    ("F02｜限流状态分布", "ring", count("文章追踪", group_by=group("是否限流"))),
    ("F03｜改标题再试数", "statistics", count("文章追踪", filt(cond("下次动作", "is", "改标题再试")))),
    ("F04｜冻结/淘汰数", "statistics", {"table_name": "文章追踪", "count_all": True, "filter": {"conjunction": "or", "conditions": [{"field_name": "下次动作", "operator": "is", "value": "冻结"}, {"field_name": "下次动作", "operator": "is", "value": "淘汰"}]}}),
]


def create_new_blocks():
    print(f"\n=== 创建新 {len(NEW_BLOCKS)} 个组件 ===")
    success = 0
    for name, typ, data_config in NEW_BLOCKS:
        # F04 needs special handling for OR conjunction
        if "conjunction_override" in data_config.get("filter", {}).get("conjunction", ""):
            pass

        cmd = [
            "/opt/homebrew/bin/lark-cli",
            "base", "+dashboard-block-create",
            "--base-token", BASE,
            "--dashboard-id", DASHBOARD,
            "--name", name,
            "--type", typ,
            "--data-config", json.dumps(data_config, ensure_ascii=False),
            "--as", "user",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"  FAILED {name}")
            print(f"    {proc.stderr[:200] or proc.stdout[:200]}")
            continue
        try:
            payload = json.loads(proc.stdout)
            block_id = payload["data"]["block"]["block_id"]
            print(f"  created {name} → {block_id}")
            success += 1
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  PARSE ERROR {name}: {e}")
            print(f"    raw: {proc.stdout[:200]}")
    print(f"  创建完成: {success}/{len(NEW_BLOCKS)}")
    return success


def arrange_dashboard():
    print("\n=== 智能排列看板 ===")
    result = lark_cli(
        "base", "+dashboard-arrange",
        "--base-token", BASE,
        "--dashboard-id", DASHBOARD,
    )
    if result:
        print("  排列完成")
    else:
        print("  排列失败")


def main():
    print("选题库数据运营看板精修")

    # Step 1: Delete old blocks
    deleted = delete_old_blocks()
    if deleted == 0:
        print("没有删除任何组件，停止执行")
        sys.exit(1)

    # Step 2: Create new blocks
    created = create_new_blocks()

    # Step 3: Arrange
    arrange_dashboard()

    print(f"\n完成: 删除{deleted}个旧组件, 创建{created}个新组件")


if __name__ == "__main__":
    main()
