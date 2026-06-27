#!/usr/bin/env python3
"""Scan files for plaintext secrets. Exit 1 on hit (pre-commit guard).

Standard library only (project rule: single-file, no extra deps).

Use:
  python3 Scripts/scan_secrets.py            # scan all git-tracked files
  python3 Scripts/scan_secrets.py <file>...  # scan given files (pre-commit mode)

Detects:
  1. Known leaked fingerprints (2026-06 incident) — flag if they reappear.
  2. Generic high-risk value formats (Tavily/OpenAI/GitHub/AWS/Slack/Google).
  3. KEY="value" / "KEY": "value" where the key name implies a secret and the
     value is NOT a placeholder/example.
"""
import re
import subprocess
import sys
from pathlib import Path

SELF = Path(__file__).resolve()

# Prefix fingerprints of values already leaked in 2026-06. Prefixes only:
# long enough to detect reappearance, too short to recover the full key.
KNOWN_LEAKED = [
    "718af82b5941ddc5",   # CLAW_API_KEY (leaked via .mcp.json + .claude/settings.json)
    "tvly-dev-42FGra-jC",  # Tavily key (leaked via .mcp.json history)
    "tvly-dev-UR9Vd-ImL",  # Tavily key (was in settings.local.json)
]

# Generic high-risk value formats — flag anywhere they appear.
VALUE_PATTERNS = [
    (re.compile(r"tvly-[A-Za-z0-9-]{20,}"), "Tavily key"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-style key"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{30,}"), "GitHub fine-grained PAT"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
]

# KEY="value" or "KEY": "value" where the key name implies a real credential.
# NOTE: bare "TOKEN" excluded on purpose — Feishu BASE_TOKEN / app_token is a
# table identifier, not an access credential (auth lives in lark-cli config).
SUSPICIOUS_KEY = re.compile(
    r"""['"]?[A-Za-z0-9_]*?(?:API[_-]?KEY|SECRET|PASSWORD|PASSWD|PRIVATE[_-]?KEY|ACCESS[_-]?TOKEN|REFRESH[_-]?TOKEN|CLAW|TAVILY)['"]?\s*[:=]\s*['"]([^'"]{8,})['"]""",
    re.IGNORECASE,
)

# If the value contains any of these, treat as placeholder/example — don't flag.
SAFE_HINT = re.compile(
    r"(\$\{|<[^>]*>|changeme|replace|your|example|placeholder|\bhere\b|\btodo\b|fake|dummy|sample|xxxx|\btest\b)",
    re.IGNORECASE,
)

BINARY_SKIP = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx", ".xlsx",
    ".zip", ".gz", ".tar", ".pyc", ".doc", ".mp4", ".mov", ".ico", ".svg",
)


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return [Path(p) for p in out.stdout.splitlines() if p]


def scan_file(path):
    if path.resolve() == SELF:
        return []  # don't scan the scanner (it carries fingerprints on purpose)
    if path.suffix.lower() in BINARY_SKIP:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for fp in KNOWN_LEAKED:
            if fp in line:
                hits.append((path, i, f"known-leaked fingerprint {fp}…"))
        for pat, name in VALUE_PATTERNS:
            m = pat.search(line)
            if m:
                hits.append((path, i, f"{name} {m.group(0)[:18]}…"))
        for m in SUSPICIOUS_KEY.finditer(line):
            val = m.group(1)
            if SAFE_HINT.search(val):
                continue
            hits.append((path, i, f"suspicious key=value …={val[:14]}…"))
    return hits


def main():
    paths = sys.argv[1:]
    files = [Path(p) for p in paths] if paths else tracked_files()
    files = [f for f in files if f.is_file()]
    all_hits = []
    for f in files:
        all_hits.extend(scan_file(f))
    if all_hits:
        print(f"❌ scan_secrets: {len(all_hits)} 处疑似明文密钥:", file=sys.stderr)
        seen = set()
        for path, line, reason in all_hits:
            key = (str(path), line, reason)
            if key in seen:
                continue
            seen.add(key)
            print(f"  {path}:{line}  {reason}", file=sys.stderr)
        print(
            "\n修复: 明文移到 .claude/settings.local.json(已gitignore) 或改用 ${ENV_VAR} 占位符。",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"✅ scan_secrets: 扫描 {len(files)} 个文件, 无明文密钥。")


if __name__ == "__main__":
    main()
