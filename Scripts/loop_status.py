#!/usr/bin/env python3
"""Super Writer · 闭环状态看板（飞轮健康度）

扫描 projects/ 所有归档篇，判定每篇是否需要复盘、是否已复盘，
标出"待复盘"清单并给出可一键复制的 /fupan 命令。

判定口径（与 .claude/commands/fupan.md Step1b 一致）：
  - 公司号（牛科技 / 牛科技说）→ 需复盘，飞轮由它驱动
  - 个人号（宅研社 / 北北ks）   → 不复盘，跳过
  - 已复盘 = 归档目录内存在 *复盘* 或 06_归档复盘卡 文件

只读，不改任何文件。纯标准库。
用法：
  python3 Scripts/loop_status.py            # 看板
  python3 Scripts/loop_status.py --json     # 机器可读
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
TODAY = date.today()

COMPANY_ACCOUNTS = ["牛科技说", "牛科技"]      # 公司号 → 必复盘
PERSONAL_ACCOUNTS = ["宅研社", "北北ks"]        # 个人号 → 跳过
REVIEW_WINDOW_DAYS = 3                          # 发布/归档后 ≥3 天进入复盘窗口

DATE_RE = re.compile(r"(20\d{6})")
# 归档目录特征：直接含成品文件之一
ARTICLE_FILE_RES = [re.compile(r"^03_风控"), re.compile(r"图文稿.*\.docx$"), re.compile(r"^02_")]
# 复盘完成特征
REVIEW_FILE_RE = re.compile(r"复盘|06_归档", re.IGNORECASE)


def parse_account(name: str):
    for a in COMPANY_ACCOUNTS + PERSONAL_ACCOUNTS:
        if a in name:
            return a
    return None


def account_type(acct):
    if acct in COMPANY_ACCOUNTS:
        return "公司号"
    if acct in PERSONAL_ACCOUNTS:
        return "个人号"
    return "未知"


def parse_date(name: str):
    m = DATE_RE.search(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def is_article_dir(d: Path) -> bool:
    """目录直接含成品文件才算文章归档（避免把周文件夹/分类文件夹当文章）。"""
    try:
        for f in d.iterdir():
            if f.is_file() and any(rx.search(f.name) for rx in ARTICLE_FILE_RES):
                return True
    except PermissionError:
        return False
    return False


def has_review(d: Path) -> bool:
    try:
        for f in d.iterdir():
            if f.is_file() and REVIEW_FILE_RE.search(f.name):
                return True
    except PermissionError:
        return False
    return False


def scan():
    items = []
    if not PROJECTS.exists():
        return items
    for week_dir in sorted(PROJECTS.iterdir()):
        if not week_dir.is_dir():
            continue
        # 周文件夹内的文章子目录
        for art in sorted(week_dir.iterdir()):
            if art.is_dir() and is_article_dir(art):
                items.append(classify(art))
        # 顶层直接归档的文章（如 projects/洗衣机_牛科技_20260618）
        if is_article_dir(week_dir):
            items.append(classify(week_dir))
    return items


def classify(d: Path):
    name = d.name
    acct = parse_account(name)
    atype = account_type(acct)
    d_ = parse_date(name)
    days = (TODAY - d_).days if d_ else None
    reviewed = has_review(d)
    return {
        "dir": str(d.relative_to(ROOT)),
        "name": name,
        "account": acct,
        "account_type": atype,
        "date": d_.isoformat() if d_ else None,
        "days_since": days,
        "reviewed": reviewed,
    }


def bucket(it):
    if it["account_type"] == "个人号":
        return "personal"
    if it["reviewed"]:
        return "done"
    if it["account_type"] == "公司号":
        if it["days_since"] is not None and it["days_since"] >= REVIEW_WINDOW_DAYS:
            return "pending"
        return "too_early"
    return "unknown"


def render(items):
    groups = {"pending": [], "too_early": [], "done": [], "personal": [], "unknown": []}
    for it in items:
        groups[bucket(it)].append(it)

    company = [i for i in items if i["account_type"] == "公司号"]
    reviewed = [i for i in company if i["reviewed"]]
    rate = (len(reviewed) / len(company) * 100) if company else 0.0

    out = []
    out.append("=" * 60)
    out.append("Super Writer · 飞轮闭环看板")
    out.append("=" * 60)
    out.append(f"归档总数：{len(items)} 篇  |  公司号：{len(company)} 篇  |  已复盘：{len(reviewed)} 篇")
    out.append(f"复盘闭合率：{rate:.0f}%   （复盘窗口 = 归档后 ≥{REVIEW_WINDOW_DAYS} 天）")
    out.append("")

    def line(it):
        ds = f"{it['days_since']}天前" if it["days_since"] is not None else "日期未知"
        return f"  · [{it['date']}] {it['name']}  ({ds})"

    out.append(f"🔴 待复盘（公司号 · 未复盘 · 已过窗口）：{len(groups['pending'])}")
    for it in sorted(groups["pending"], key=lambda x: x["days_since"] or 0, reverse=True):
        out.append(line(it))
        out.append(f"      → /fupan \"{it['dir']}\" \"<头条链接>\"")
    if not groups["pending"]:
        out.append("  （无）")
    out.append("")

    out.append(f"🟡 未到窗口（公司号 · 未复盘 · 不足{REVIEW_WINDOW_DAYS}天）：{len(groups['too_early'])}")
    for it in sorted(groups["too_early"], key=lambda x: x["days_since"] or 0):
        out.append(line(it))
    if not groups["too_early"]:
        out.append("  （无）")
    out.append("")

    out.append(f"✅ 已复盘：{len(groups['done'])}")
    for it in groups["done"]:
        out.append(line(it))
    if not groups["done"]:
        out.append("  （无）")
    out.append("")

    out.append(f"⚪ 个人号（不复盘 · 跳过）：{len(groups['personal'])}")
    for it in groups["personal"]:
        out.append(line(it))
    out.append("")

    if groups["unknown"]:
        out.append(f"❓ 未知账号（需人工认领）：{len(groups['unknown'])}")
        for it in groups["unknown"]:
            out.append(line(it))
        out.append("")

    out.append("-" * 60)
    if rate < 50 and company:
        out.append("⚠ 闭环断裂：复盘闭合率偏低，飞轮没转起来。优先把 🔴 待复盘 跑掉。")
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="飞轮闭环看板")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()
    items = scan()
    if args.json:
        summary = {
            "total": len(items),
            "company": sum(1 for i in items if i["account_type"] == "公司号"),
            "reviewed": sum(1 for i in items if i["account_type"] == "公司号" and i["reviewed"]),
            "items": items,
        }
        summary["closure_rate"] = (
            summary["reviewed"] / summary["company"] * 100 if summary["company"] else 0.0
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render(items))


if __name__ == "__main__":
    sys.exit(main())
