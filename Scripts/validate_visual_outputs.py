#!/usr/bin/env python3
"""
Validate Super Writer visual outputs.

Checks:
- image files are really saved on disk
- naming follows T5_ChatGPT_* / T5_* convention
- dimensions and file sizes are publishable enough
- optional manifest references local image filenames
"""

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image


IMAGE_RE = re.compile(r".*\.(png|jpg|jpeg|webp)$", re.I)


def add_issue(bucket, code, path, message):
    bucket.append({"code": code, "path": str(path), "message": message})


def classify(path: Path) -> str:
    name = path.name
    if name.startswith("T5_ChatGPT_"):
        return "chatgpt"
    if name.startswith("T5_"):
        return "structured"
    if "封面" in name:
        return "legacy_cover"
    if "信息图" in name:
        return "legacy_infographic"
    return "unknown"


def inspect_image(path: Path):
    with Image.open(path) as img:
        return img.size


def validate_image(path: Path, errors, warnings):
    if not path.exists():
        add_issue(errors, "missing_image", path, "图片文件不存在")
        return

    if not IMAGE_RE.match(path.name):
        add_issue(errors, "not_image", path, "不是支持的图片格式")
        return

    size = path.stat().st_size
    try:
        width, height = inspect_image(path)
    except Exception as exc:
        add_issue(errors, "broken_image", path, f"图片无法打开：{exc}")
        return

    kind = classify(path)
    if kind == "unknown":
        add_issue(warnings, "naming", path, "建议使用 T5_ChatGPT_[功能].png 或 T5_[功能].png 命名")
    if kind in {"legacy_cover", "legacy_infographic"}:
        add_issue(warnings, "legacy_naming", path, "旧式命名，只能作为迁移期产物；新稿请使用 T5 命名")

    long_edge = max(width, height)
    short_edge = min(width, height)
    ratio = width / height if height else 0

    if "封面" in path.name or kind == "chatgpt":
        if width < 1280 or height < 720:
            add_issue(errors, "cover_resolution", path, f"封面最低 1280x720，当前 {width}x{height}")
        elif width < 1920 or height < 1080:
            add_issue(warnings, "cover_resolution", path, f"封面建议 ≥1920x1080，当前 {width}x{height}")
        if not (1.70 <= ratio <= 1.85):
            add_issue(warnings, "cover_ratio", path, f"封面建议 16:9，当前比例 {ratio:.2f}")
        if size < 300 * 1024:
            add_issue(warnings, "cover_filesize", path, f"封面文件偏小，当前 {size // 1024}KB")
    else:
        if long_edge < 1080 or short_edge < 720:
            add_issue(errors, "infographic_resolution", path, f"信息图分辨率偏低，当前 {width}x{height}")
        if size < 500 * 1024:
            add_issue(warnings, "infographic_filesize", path, f"信息图文件偏小，当前 {size // 1024}KB；需人工复看是否为草稿/PPT图")


def collect_images(target: Path):
    if target.is_file():
        return [target]
    return sorted(
        p for p in target.iterdir()
        if p.is_file() and IMAGE_RE.match(p.name) and not p.name.startswith(".")
    )


def validate_manifest(manifest: Path, images, errors, warnings):
    if not manifest:
        return
    if not manifest.exists():
        add_issue(warnings, "missing_manifest", manifest, "配图说明文件不存在")
        return
    text = manifest.read_text(encoding="utf-8")
    image_names = {p.name for p in images}
    required_fields = ["工具", "功能", "插入位置", "状态", "验收"]
    for name in image_names:
        if name.startswith("T5_") and name not in text:
            add_issue(warnings, "manifest_reference", manifest, f"配图说明未提到图片：{name}")
            continue
        if name.startswith("T5_"):
            start = text.find(name)
            local_block = text[start:start + 900] if start >= 0 else text
            for token in required_fields:
                if token not in local_block:
                    add_issue(warnings, "manifest_image_field", manifest, f"{name} 的配图说明缺少字段：{token}")
    for token in required_fields:
        if token not in text:
            add_issue(warnings, "manifest_field", manifest, f"配图说明建议包含字段：{token}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path, help="image file or outputs directory")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    errors = []
    warnings = []

    if not args.target.exists():
        add_issue(errors, "missing_target", args.target, "目标不存在")
        images = []
    else:
        images = collect_images(args.target)
        if not images:
            add_issue(warnings, "no_images", args.target, "未找到图片")
        for path in images:
            validate_image(path, errors, warnings)

    validate_manifest(args.manifest, images, errors, warnings)

    result = {
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "image_count": len(images),
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if not errors and not warnings else ("ERROR" if errors else "WARNING")
        print(f"{status}: images={len(images)} errors={len(errors)} warnings={len(warnings)}")
        for issue in errors + warnings:
            print(f"- {issue['code']} {issue['path']} {issue['message']}")

    if errors:
        return 1
    if warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
