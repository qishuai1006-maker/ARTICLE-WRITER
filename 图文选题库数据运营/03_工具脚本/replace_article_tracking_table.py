#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
TABLE_ID = "tblA8dT3x3bdOF9Y"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "02_数据备份与导入包"
BACKUP_PATH = DATA_DIR / "文章追踪_覆盖前备份_20260526.json"
IMPORT_PATH = DATA_DIR / "文章追踪_最新64篇导入包_20260526.json"


def run_lark(args):
    result = subprocess.run(
        ["lark-cli", *args, "--as", "user"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def main():
    backup = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
    record_ids = backup["data"]["record_id_list"]
    package = json.loads(IMPORT_PATH.read_text(encoding="utf-8"))
    rows = package["rows"]

    print(f"old_records={len(record_ids)}")
    print(f"new_rows={len(rows)}")

    for idx, record_id in enumerate(record_ids, start=1):
        run_lark(
            [
                "base",
                "+record-delete",
                "--base-token",
                BASE_TOKEN,
                "--table-id",
                TABLE_ID,
                "--record-id",
                record_id,
                "--yes",
            ]
        )
        if idx % 10 == 0 or idx == len(record_ids):
            print(f"deleted={idx}/{len(record_ids)}")

    run_lark(
        [
            "base",
            "+record-batch-create",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            TABLE_ID,
            "--json",
            f"@{IMPORT_PATH}",
        ]
    )
    print(f"created={len(rows)}")


if __name__ == "__main__":
    main()
