#!/usr/bin/env python3
"""Import Toutiao backend Excel stats → Feishu article-tracking table.

Usage:
  python3 import_toutiao_stats.py <excel_path> [<excel_path> ...] [--apply]

Default = DRY-RUN (report only, writes nothing). Pass --apply to actually
patch Feishu. Reads .xlsx via stdlib zipfile (openpyxl 3.1.5 crashes on the
Fill stylesheet under Python 3.14). Matches each row to a Feishu record by
the Toutiao article ID embedded in the 链接/ID column (zero ambiguity).

Updates ONLY performance fields (展现量/阅读量/CTR/完读/收藏/评论/点赞/转发/分享/
粉丝展现/粉丝阅读/平均阅读时长). Never touches review-attribution fields.

Writes one record per call with retry+backoff (飞书 rate-limits bursts of
record-batch-update; 800004135). Idempotent: re-running skips rows whose
values already match, so it doubles as a retry for previously-failed rows.

Single-file, stdlib only, shells out to lark-cli.
"""
import json
import re
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

BASE_TOKEN = "CFF5boINWaBpb4sqlFVceacEn5c"
LARK = "/opt/homebrew/bin/lark-cli"
TBL_ARTICLES = "tblA8dT3x3bdOF9Y"

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _nonneg(x):
    return max(0, int(round(float(x))))


FIELD_MAP = [
    ("展现量", "展现量", _nonneg),
    ("粉丝展现量", "粉丝展现量", _nonneg),
    ("阅读量", "阅读量", _nonneg),
    ("粉丝阅读量", "粉丝阅读量", _nonneg),
    ("点击率", "CTR(%)", lambda x: round(float(x) * 100)),       # 0.12 -> 12
    ("平均阅读完成率", "完读率(%)", lambda x: round(float(x), 2)),
    ("点赞量", "点赞数", _nonneg),
    ("评论量", "评论数", _nonneg),
    ("转发量", "转发量", _nonneg),
    ("分享量", "分享量", _nonneg),
    ("收藏量", "收藏数", _nonneg),
    ("平均阅读时长", "平均阅读时长(s)", _nonneg),
]
FEISHU_PERF_FIELDS = [f for _, f, _ in FIELD_MAP]

# ---- record-create: fields filled for newly-seen articles (Excel has, Feishu hasn't) ----
# 产品品类 from title keyword (objective fact). 标题结构模板/文章类型 left blank (post-hoc
# classification, belongs to /fupan). 互动率(%) left blank (Excel has no column; formula
# undefined — matches the update path). 归因字段 = /fupan's job. ID is auto_number, skipped.
CATEGORY_KEYWORDS = [
    ("电视", "电视"), ("空调", "空调"), ("冰箱", "冰箱"), ("洗衣机", "洗衣机"),
    ("油烟机", "油烟机"), ("热水器", "热水器"), ("显示器", "显示器"),
    ("手机", "手机"), ("洗碗机", "洗碗机"),
]

CREATE_FIELD_ORDER = (["文章标题", "文章链接", "头条文章ID", "发布账号", "发布日期",
                       "产品品类", "标题字数"] + FEISHU_PERF_FIELDS)


def guess_category(title):
    for kw, cat in CATEGORY_KEYWORDS:
        if kw in (title or ""):
            return cat
    return None


def build_create_row(er):
    """Field dict for a new record (None values dropped). Performance fields
    reuse the same converters as update so units stay consistent."""
    row = {
        "文章标题": er["标题"],
        "文章链接": er["链接"],
        "头条文章ID": er["ID"],
        "发布账号": er["账号"],
        "发布日期": er["发布时间"],
        "产品品类": guess_category(er["标题"]),
        "标题字数": len(er["标题"] or ""),
    }
    for ex_col, ff, conv in FIELD_MAP:
        raw = er["_raw"][ex_col]
        if raw is None or raw == "":
            continue
        try:
            row[ff] = conv(raw)
        except (ValueError, TypeError):
            continue
    return {k: v for k, v in row.items() if v is not None}


# ---- xlsx read (stdlib, bypass openpyxl Fill crash) ----
def _col_idx(ref):
    m = re.match(r"([A-Z]+)", ref)
    idx = 0
    for ch in m.group(1):
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def read_xlsx(path):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        r = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in r.iter(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    r = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in r.iter(f"{NS}row"):
        cells, maxc = {}, -1
        for c in row.findall(f"{NS}c"):
            ci = _col_idx(c.get("r"))
            t = c.get("t")
            v = c.find(f"{NS}v")
            val = None
            if v is not None:
                val = shared[int(v.text)] if t == "s" else v.text
            elif c.find(f"{NS}is") is not None:
                tn = c.find(f"{NS}is").find(f"{NS}t")
                val = tn.text if tn is not None else ""
            cells[ci] = val
            maxc = max(maxc, ci)
        rows.append([cells.get(i) for i in range(maxc + 1)])
    return rows


def parse_excel(path, default_account):
    rows = read_xlsx(path)
    headers = rows[0]
    hidx = {h: i for i, h in enumerate(headers)}
    out = []
    for r in rows[1:]:
        if not r or not r[hidx["ID"]]:
            continue
        out.append({
            "标题": r[hidx["标题"]],
            "ID": str(r[hidx["ID"]]),
            "链接": r[hidx["链接"]],
            "发布时间": r[hidx["发布时间"]],
            "账号": default_account,
            "_raw": {ex: r[hidx[ex]] for ex, _, _ in FIELD_MAP},
        })
    return out


# ---- Feishu ----
def lark_list(fields, limit=300):
    cmd = [LARK, "base", "+record-list", "--base-token", BASE_TOKEN,
           "--table-id", TBL_ARTICLES, "--format", "json", "--limit", str(limit)]
    for f in fields:
        cmd += ["--field-id", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] lark-cli: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    d = json.loads(r.stdout)["data"]
    return d["data"], d.get("record_id_list", []), d.get("fields", [])


def lark_update(rid, patch, retries=4):
    """Patch one record; retry with backoff on rate-limit / transient errors.
    Judges success by JSON `ok`, not just exit code (lark-cli may exit 0 on
    API errors)."""
    payload = {"record_id_list": [rid], "patch": patch}
    cmd = [LARK, "base", "+record-batch-update", "--base-token", BASE_TOKEN,
           "--table-id", TBL_ARTICLES, "--json",
           json.dumps(payload, ensure_ascii=False)]
    last = ""
    for attempt in range(retries):
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = r.stdout.strip()
        try:
            if json.loads(out).get("ok"):
                return True, ""
            last = out
        except json.JSONDecodeError:
            last = out or r.stderr.strip()
        time.sleep(0.8 * (attempt + 1))   # backoff: 0.8, 1.6, 2.4, 3.2s
    return False, last


def lark_create(row, retries=4):
    """Create one record; retry with backoff (same rate-limit rationale as
    lark_update). rows follow CREATE_FIELD_ORDER; absent keys -> null (Feishu
    treats null as empty cell)."""
    payload = {"fields": CREATE_FIELD_ORDER,
               "rows": [[row.get(f) for f in CREATE_FIELD_ORDER]]}
    cmd = [LARK, "base", "+record-batch-create", "--base-token", BASE_TOKEN,
           "--table-id", TBL_ARTICLES, "--json",
           json.dumps(payload, ensure_ascii=False)]
    last = ""
    for attempt in range(retries):
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = r.stdout.strip()
        try:
            if json.loads(out).get("ok"):
                return True, ""
            last = out
        except json.JSONDecodeError:
            last = out or r.stderr.strip()
        time.sleep(0.8 * (attempt + 1))   # backoff: 0.8, 1.6, 2.4, 3.2s
    return False, last


def extract_id(link):
    m = re.search(r"i(\d{15,})", link or "")
    return m.group(1) if m else None


def main():
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    if not args:
        print("Usage: import_toutiao_stats.py <excel...> [--apply]", file=sys.stderr)
        sys.exit(2)

    excel_rows = []
    for p in args:
        acct = "牛科技说" if "牛科技说" in p else "牛科技"
        excel_rows += parse_excel(p, acct)
    print(f"[读取] {len(args)} 个表，共 {len(excel_rows)} 行")

    want = ["文章标题", "文章链接", "发布账号"] + FEISHU_PERF_FIELDS
    frows, rids, colnames = lark_list(want)
    I = {n: i for i, n in enumerate(colnames)}
    feishu_by_id = {}
    for row, rid in zip(frows, rids):
        link = row[I["文章链接"]] if "文章链接" in I else ""
        aid = extract_id(link if isinstance(link, str) else "")
        if aid:
            feishu_by_id[aid] = (rid, row)
    print(f"[飞书] {len(frows)} 篇，可匹配键 {len(feishu_by_id)} 个\n")

    to_update, unchanged, missing = [], [], []
    for er in excel_rows:
        eid = er["ID"]
        if eid not in feishu_by_id:
            missing.append(er)
            continue
        rid, row = feishu_by_id[eid]
        patch, diff = {}, []
        for ex_col, ff, conv in FIELD_MAP:
            raw = er["_raw"][ex_col]
            if raw is None or raw == "":
                continue
            try:
                new = conv(raw)
            except (ValueError, TypeError):
                continue
            old = row[I[ff]] if ff in I else None
            old = old[0] if isinstance(old, list) else old
            if old != new:
                patch[ff] = new
                diff.append(f"{ff}: {old}→{new}")
        title = er["标题"][:26]
        if patch:
            to_update.append((rid, patch, title, diff))
        else:
            unchanged.append(title)

    print("=" * 64)
    print("DRY-RUN 匹配报告" + ("（--apply 将真实写入）" if apply else "（未传 --apply，不写入）"))
    print("=" * 64)
    print(f"✅ 唯一匹配 {len(to_update) + len(unchanged)} 篇")
    print(f"   ├─ 将更新 {len(to_update)} 篇（有数据变化）")
    print(f"   └─ 无变化跳过 {len(unchanged)} 篇")
    print(f"❌ Excel有·飞书无 {len(missing)} 篇（新发布未登记，--apply 自动新建）")

    if not apply:
        if missing:
            print(f"\n--- Excel有·飞书无 {len(missing)} 篇（--apply 时将自动新建）---")
            for er in missing[:20]:
                cr = build_create_row(er)
                cat = cr.get("产品品类") or "未识别·留空"
                pub = (er["发布时间"] or "")[:10]
                print(f"  - [{er['账号']}] {er['标题'][:28]}")
                print(f"      品类={cat} 字数={cr.get('标题字数','')} 发布={pub}"
                      f" | 阅读={cr.get('阅读量',0)} CTR={cr.get('CTR(%)',0)} 展现={cr.get('展现量',0)}")
        print("\n[提示] dry-run，未写入。--apply 将更新已存在篇 + 新建 missing 篇。")
        return

    # ---- apply: update existing (retry+backoff in lark_update; throttle) ----
    ok, fail = 0, 0
    for rid, patch, title, _ in to_update:
        success, msg = lark_update(rid, patch)
        time.sleep(0.2)   # throttle to avoid 飞书 rate-limit (800004135)
        if success:
            ok += 1
        else:
            fail += 1
            print(f"\n  [更新失败] {title} rec={rid}")
            print(f"      patch={json.dumps(patch, ensure_ascii=False)}")
            print(f"      error={msg}")
    print(f"[更新完成] 成功 {ok} 篇 | 失败 {fail} 篇")

    # ---- apply: create missing (Excel has, Feishu hasn't) ----
    cok, cfail = 0, 0
    for er in missing:
        row = build_create_row(er)
        success, msg = lark_create(row)
        time.sleep(0.2)
        if success:
            cok += 1
        else:
            cfail += 1
            print(f"\n  [新建失败] {er['标题'][:28]} ID={er['ID']}")
            print(f"      row={json.dumps(row, ensure_ascii=False)}")
            print(f"      error={msg}")
    print(f"[新建完成] 成功 {cok} 篇 | 失败 {cfail} 篇")
    print(f"\n[汇总] 更新 {ok}/{len(to_update)} | 新建 {cok}/{len(missing)}")


if __name__ == "__main__":
    main()
