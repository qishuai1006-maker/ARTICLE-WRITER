#!/usr/bin/env python3
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
TABLE_NAME = "文章追踪"
# 文章追踪表 ID。网页 URL 里看到的 tblx7PYNPRVBHGET 是被“关联选题”字段链接的选题表。
PRIMARY_TABLE_ID = "tblA8dT3x3bdOF9Y"
PACKAGE_PATH = Path(
    "图文选题库数据运营/02_数据备份与导入包/"
    "文章追踪_最新70篇导入包_20260528.json"
)
LOG_PATH = Path("图文选题库数据运营/01_过程日志/文章追踪_覆盖执行日志_20260528.txt")


def run(args, *, capture=True):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(f"\n$ {' '.join(args)}\n")
    proc = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    with LOG_PATH.open("a", encoding="utf-8") as log:
        if proc.stdout:
            log.write(proc.stdout)
        if proc.stderr:
            log.write(proc.stderr)
    if proc.returncode != 0:
        print(f"\n命令失败：{' '.join(args)}", file=sys.stderr)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode)
    return proc.stdout or ""


def load_json_output(args):
    out = run(args)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("\n无法解析 lark-cli 输出，原始输出如下：", file=sys.stderr)
        print(out, file=sys.stderr)
        sys.exit(1)


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def find_table_id():
    data = load_json_output(
        [
            "lark-cli",
            "base",
            "+table-list",
            "--as",
            "user",
            "--base-token",
            BASE_TOKEN,
        ]
    )
    matches = []
    all_tables = []
    for item in walk(data):
        name = item.get("name") or item.get("table_name")
        table_id = item.get("table_id") or item.get("id")
        if isinstance(name, str) and isinstance(table_id, str) and table_id.startswith("tbl"):
            all_tables.append((name, table_id))
        if name == TABLE_NAME and isinstance(table_id, str) and table_id.startswith("tbl"):
            matches.append(table_id)
    print("当前 Base 数据表：")
    for name, table_id in dict(all_tables).items():
        print(f"- {name}: {table_id}")
    matches = list(dict.fromkeys(matches))
    if PRIMARY_TABLE_ID in matches:
        return PRIMARY_TABLE_ID
    if len(matches) != 1:
        if PRIMARY_TABLE_ID:
            print(f"没有按表名唯一定位，尝试网页当前表 ID：{PRIMARY_TABLE_ID}")
            return PRIMARY_TABLE_ID
        print(f"没有唯一定位到 {TABLE_NAME} 表，候选：{matches}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def verify_target_table(table_id):
    data = load_json_output(
        [
            "lark-cli",
            "base",
            "+field-list",
            "--as",
            "user",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            table_id,
            "--limit",
            "200",
        ]
    )
    names = []
    for item in walk(data):
        name = item.get("field_name") or item.get("name")
        if isinstance(name, str):
            names.append(name)
    required = {"文章标题", "发布账号", "展现量", "发布日期"}
    missing = required - set(names)
    if missing:
        print(f"目标表字段不匹配，缺少：{sorted(missing)}", file=sys.stderr)
        print(f"目标表字段：{names}", file=sys.stderr)
        sys.exit(1)
    print(f"字段校验通过：{table_id} 是文章追踪结构")


def list_record_ids(table_id):
    out = run(
        [
            "lark-cli",
            "base",
            "+record-list",
            "--as",
            "user",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            table_id,
            "--limit",
            "200",
        ]
    )

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        data = None

    ids = []
    if data is not None:
        for item in walk(data):
            record_id = item.get("record_id") or item.get("_record_id") or item.get("id")
            if isinstance(record_id, str) and record_id.startswith("rec"):
                ids.append(record_id)
    else:
        # lark-cli 1.0.42 的 +record-list 默认输出 Markdown 表格，第一列是 _record_id。
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("| rec"):
                continue
            first_cell = line.split("|", 2)[1].strip()
            if first_cell.startswith("rec"):
                ids.append(first_cell)

    return list(dict.fromkeys(ids))


def delete_records(table_id, record_ids):
    for idx, record_id in enumerate(record_ids, 1):
        run(
            [
                "lark-cli",
                "base",
                "+record-delete",
                "--as",
                "user",
                "--base-token",
                BASE_TOKEN,
                "--table-id",
                table_id,
                "--record-id",
                record_id,
                "--yes",
            ]
        )
        print(f"已删除旧记录 {idx}/{len(record_ids)}")


def create_records(table_id, package_path):
    run(
        [
            "lark-cli",
            "base",
            "+record-batch-create",
            "--as",
            "user",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            table_id,
            "--json",
            f"@{package_path}",
        ]
    )


def summarize_package(package_path):
    package = json.loads(package_path.read_text(encoding="utf-8"))
    fields = package["fields"]
    rows = [dict(zip(fields, row)) for row in package["rows"]]
    return rows, Counter(row.get("发布账号") for row in rows), Counter(row.get("表现分层") for row in rows)


def main():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("文章追踪覆盖执行日志\n", encoding="utf-8")
    if not PACKAGE_PATH.exists():
        print(f"找不到导入包：{PACKAGE_PATH}", file=sys.stderr)
        sys.exit(1)

    rows, account_counts, layer_counts = summarize_package(PACKAGE_PATH)
    print(f"准备覆盖 {TABLE_NAME}：导入包 {len(rows)} 条")
    print(f"账号分布：{dict(account_counts)}")
    print(f"表现分层：{dict(layer_counts)}")

    table_id = find_table_id()
    print(f"定位到表：{TABLE_NAME} ({table_id})")
    verify_target_table(table_id)

    old_ids = list_record_ids(table_id)
    print(f"旧记录数：{len(old_ids)}")

    delete_records(table_id, old_ids)
    print("旧记录已清空，开始写入新记录...")
    create_records(table_id, PACKAGE_PATH)

    new_ids = list_record_ids(table_id)
    print(f"写入完成，当前记录数：{len(new_ids)}")
    if len(new_ids) != len(rows):
        print(f"警告：期望 {len(rows)} 条，读回 {len(new_ids)} 条", file=sys.stderr)
        sys.exit(2)
    print("校验通过：文章追踪已覆盖为最新 70 篇。")


if __name__ == "__main__":
    main()
