#!/usr/bin/env python3
"""Render HTML card(s) to PNG via headless Chrome — full-page, crisp.

Replaces the legacy matplotlib pipeline (banned by red-line for finished
infographics). HTML card => Chrome render => PNG is the sanctioned path,
matching the TCL-TV / fridge / washer archives.

Usage:
    python3 render_html_to_png.py out1.png in1.html [out2.png in2.html ...]
    python3 render_html_to_png.py --scale 2 out.png in.html

Zero-config: drives the system Chrome through Playwright's channel='chrome',
so no extra browser download. Prints each rendered path.
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def render(pairs, scale, width, height):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
        )
        for png, html in pairs:
            page.goto(Path(html).resolve().as_uri())
            page.wait_for_timeout(500)  # let web fonts / flexbox settle
            page.screenshot(path=str(png), full_page=True)
            print(f"rendered {png}")
        browser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scale", type=int, default=3, help="device scale factor (default 3)")
    ap.add_argument("--width", type=int, default=1080, help="viewport width (default 1080)")
    ap.add_argument("--height", type=int, default=900, help="viewport height (default 900)")
    ap.add_argument("args", nargs="+", help="out.png in.html [out2.png in2.html ...]")
    ns = ap.parse_args()
    if len(ns.args) % 2 != 0:
        raise SystemExit("usage: render_html_to_png.py [--scale N] out.png in.html [...]")
    pairs = list(zip(ns.args[0::2], ns.args[1::2]))
    render(pairs, ns.scale, ns.width, ns.height)


if __name__ == "__main__":
    main()
