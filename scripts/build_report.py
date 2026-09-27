"""Render docs/report.md -> docs/report.html -> docs/report.pdf.

Toolchain (both required, both external):

1. ``pandoc``                       markdown -> standalone HTML (+ docs/report.css)
2. headless Edge/Chrome             HTML -> PDF via ``--print-to-pdf``

Neither is needed for the data/model pipeline -- this script only exists to
regenerate the report PDF.  ``docs/report.pdf`` is committed, so a reviewer who
only wants the numbers never has to run this.

Usage::

    python scripts/build_report.py
    python scripts/build_report.py --md docs/report.md --pdf docs/report.pdf
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PANDOC_CANDIDATES = [
    "pandoc",
    r"C:\Program Files\Pandoc\pandoc.exe",
    "/usr/bin/pandoc",
    "/usr/local/bin/pandoc",
]
BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def which(candidates: list[str]) -> str | None:
    for cand in candidates:
        found = shutil.which(cand) if os.sep not in cand else (
            cand if os.path.exists(cand) else None
        )
        if found:
            return found
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--md", default=os.path.join(ROOT, "docs", "report.md"))
    ap.add_argument("--css", default=os.path.join(ROOT, "docs", "report.css"))
    ap.add_argument("--pdf", default=os.path.join(ROOT, "docs", "report.pdf"))
    args = ap.parse_args()

    html = os.path.splitext(args.pdf)[0] + ".html"

    pandoc = which(PANDOC_CANDIDATES)
    if not pandoc:
        print("ERROR: pandoc not found. Install it, or read docs/report.md instead.")
        return 2

    print(f"pandoc : {pandoc}")
    print(f"input  : {args.md}")
    subprocess.run(
        [
            pandoc, args.md,
            "-s", "--embed-resources",
            "--metadata", "title=汶川震后泥石流多时相数据集的流程复现与降雨阈值/易发性建模",
            "--css", args.css,
            "-o", html,
        ],
        cwd=ROOT,
        check=True,
    )
    print(f"html   : {html} ({os.path.getsize(html)} bytes)")

    browser = which(BROWSER_CANDIDATES)
    if not browser:
        print("WARNING: no headless Edge/Chrome found; HTML written but PDF skipped.")
        return 0

    print(f"browser: {browser}")
    profile = os.path.join(ROOT, ".pdfbuild", "browser-profile")
    os.makedirs(profile, exist_ok=True)
    url = "file:///" + html.replace("\\", "/")

    # NOTE: do NOT capture stdout/stderr here -- piping the child's stdio trips
    # the sandbox's pipe restriction.  Let the browser write straight through.
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={args.pdf}",
            url,
        ],
        cwd=ROOT,
        check=False,
    )

    if not os.path.exists(args.pdf):
        print("ERROR: browser did not produce a PDF.")
        return 1

    size = os.path.getsize(args.pdf)
    print(f"pdf    : {args.pdf} ({size} bytes)")

    try:
        from pypdf import PdfReader
        n = len(PdfReader(args.pdf).pages)
        print(f"pages  : {n}")
    except Exception as exc:  # noqa: BLE001
        print(f"(pypdf not available for page count: {exc})")

    for stale in glob.glob(os.path.join(ROOT, ".pdfbuild", "*.html")):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())