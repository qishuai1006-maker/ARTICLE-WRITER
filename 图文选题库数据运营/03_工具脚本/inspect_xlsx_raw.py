#!/usr/bin/env python3
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def col_to_idx(cell_ref: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_ref).group(1)
    idx = 0
    for ch in letters:
        idx = idx * 26 + ord(ch) - ord("A") + 1
    return idx - 1


def load_shared_strings(zf: zipfile.ZipFile):
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    values = []
    for si in root.findall("main:si", NS):
        parts = []
        for t in si.findall(".//main:t", NS):
            parts.append(t.text or "")
        values.append("".join(parts))
    return values


def sheet_paths(zf: zipfile.ZipFile):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("pkgrel:Relationship", NS)
    }
    out = []
    for sheet in wb.findall("main:sheets/main:sheet", NS):
        name = sheet.attrib["name"]
        rid = sheet.attrib[f"{{{NS['rel']}}}id"]
        target = rid_to_target[rid]
        if not target.startswith("xl/"):
            target = "xl/" + target
        out.append((name, target))
    return out


def cell_text(cell, shared):
    t = cell.attrib.get("t")
    if t == "inlineStr":
        return "".join(x.text or "" for x in cell.findall(".//main:t", NS))
    v = cell.find("main:v", NS)
    if v is None:
        return ""
    raw = v.text or ""
    if t == "s":
        try:
            return shared[int(raw)]
        except Exception:
            return raw
    if t == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw


def read_sheet(zf, path, shared):
    root = ET.fromstring(zf.read(path))
    rows = []
    for row in root.findall(".//main:sheetData/main:row", NS):
        values = []
        for cell in row.findall("main:c", NS):
            idx = col_to_idx(cell.attrib["r"])
            while len(values) <= idx:
                values.append("")
            values[idx] = cell_text(cell, shared)
        rows.append(values)
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def main():
    for raw_path in sys.argv[1:]:
        path = Path(raw_path)
        with zipfile.ZipFile(path) as zf:
            shared = load_shared_strings(zf)
            result = {"file": str(path), "sheets": []}
            for name, sheet_path in sheet_paths(zf):
                rows = read_sheet(zf, sheet_path, shared)
                non_empty = [r for r in rows if any(str(v).strip() for v in r)]
                result["sheets"].append(
                    {
                        "name": name,
                        "shape": [len(non_empty), max((len(r) for r in non_empty), default=0)],
                        "preview": non_empty[:8],
                    }
                )
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
