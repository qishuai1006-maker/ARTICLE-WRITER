#!/usr/bin/env python3
import json
import subprocess
import sys

BASE = "CFF5boINWaBpb4sqlFVceacEn5c"
DASHBOARD = "blkfM1WeXiIeF7ZB"

CYCLE_START = 1779120000000  # 2026-05-19 00:00:00 +08:00
CYCLE_END = 1779724800000    # 2026-05-26 00:00:00 +08:00
NEXT_START = 1779724800000   # 2026-05-26 00:00:00 +08:00
NEXT_END = 1780329600000     # 2026-06-02 00:00:00 +08:00


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


cycle_filter = filt(
    cond("发布日期", "isGreaterEqual", CYCLE_START),
    cond("发布日期", "isLess", CYCLE_END),
)

next_schedule_filter = filt(
    cond("选题状态", "is", "已排期"),
    cond("排期日期", "isGreaterEqual", NEXT_START),
    cond("排期日期", "isLess", NEXT_END),
)

blocks = [
    ("A01｜本周期发布数（5/19-5/25）", "statistics", count("文章追踪", cycle_filter)),
    ("A02｜本周期总展现量", "statistics", stat_sum("展现量", filter_=cycle_filter)),
    ("A03｜本周期总阅读量", "statistics", stat_sum("阅读量", filter_=cycle_filter)),
    ("A04｜本周期平均CTR", "statistics", stat_avg("CTR(%)", filter_=cycle_filter)),
    ("A05｜爆款文章数", "statistics", count("文章追踪", filt(cond("表现分层", "is", "爆款")))),
    ("A06｜疑似限流数", "statistics", count("文章追踪", filt(cond("是否限流", "is", "疑似限流")))),
    ("A07｜下周期已排期数（5/26-6/1）", "statistics", count("发稿排期", next_schedule_filter)),

    ("B01｜账号总阅读量", "column", series_group("阅读量", "发布账号")),
    ("B02｜账号平均阅读量", "column", series_group("阅读量", "发布账号", "AVERAGE")),
    ("B03｜账号平均CTR", "column", series_group("CTR(%)", "发布账号", "AVERAGE")),
    ("B04｜账号爆款数", "column", count("文章追踪", filt(cond("表现分层", "is", "爆款")), group("发布账号"))),

    ("C01｜品类平均阅读量排行", "column", series_group("阅读量", "产品品类", "AVERAGE")),
    ("C02｜品类平均展现量排行", "column", series_group("展现量", "产品品类", "AVERAGE")),
    ("C03｜品类平均CTR排行", "column", series_group("CTR(%)", "产品品类", "AVERAGE")),
    ("C04｜品类文章数分布", "ring", count("文章追踪", group_by=group("产品品类"))),

    ("D01｜标题结构平均阅读量", "column", series_group("阅读量", "标题结构模板", "AVERAGE")),
    ("D02｜标题结构平均CTR", "column", series_group("CTR(%)", "标题结构模板", "AVERAGE")),
    ("D03｜文章类型平均阅读量", "column", series_group("阅读量", "文章类型", "AVERAGE")),
    ("D04｜表现分层分布", "ring", count("文章追踪", group_by=group("表现分层"))),

    ("E01｜高阅读文章排行", "bar", series_group("阅读量", "文章标题")),
    ("E02｜高展现文章排行", "bar", series_group("展现量", "文章标题")),
    ("E03｜高CTR文章排行", "bar", series_group("CTR(%)", "文章标题", "AVERAGE")),

    ("F01｜下次动作分布", "ring", count("文章追踪", group_by=group("下次动作"))),
    ("F02｜限流状态分布", "ring", count("文章追踪", group_by=group("是否限流"))),
    ("F03｜改标题再试数量", "statistics", count("文章追踪", filt(cond("下次动作", "is", "改标题再试")))),
    ("F04｜冻结/淘汰数量", "statistics", count("文章追踪", filt(cond("下次动作", "contains", ["冻结", "淘汰"])))),
]


def run_block(name, typ, data_config):
    cmd = [
        "lark-cli",
        "base",
        "+dashboard-block-create",
        "--base-token",
        BASE,
        "--dashboard-id",
        DASHBOARD,
        "--name",
        name,
        "--type",
        typ,
        "--data-config",
        json.dumps(data_config, ensure_ascii=False),
        "--as",
        "user",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"FAILED {name}\n{proc.stderr or proc.stdout}", file=sys.stderr)
        sys.exit(proc.returncode)
    payload = json.loads(proc.stdout)
    block_id = payload["data"]["block"]["block_id"]
    print(f"created {name} {block_id}")


def main():
    for name, typ, data_config in blocks:
        run_block(name, typ, data_config)


if __name__ == "__main__":
    main()
