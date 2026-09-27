"""Fetch the open-access Scientific Data paper (s41597-022-01658-y) as HTML + text.

The paper is the data descriptor for Zenodo 10.5281/zenodo.6891244 and is the
primary source for the field dictionary and the reported statistics we validate
the cleaned tables against.
"""
from __future__ import annotations

import html
import os
import re
import urllib.request

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [
    ("User-Agent", "Mozilla/5.0 (compatible; WenchuanRepro/0.1; research)"),
    ("Accept", "text/html,application/xhtml+xml"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "raw")

URLS = [
    "https://www.nature.com/articles/s41597-022-01658-y",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC9481628/",
]


def strip_tags(doc: str) -> str:
    doc = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?is)<br\s*/?>", "\n", doc)
    doc = re.sub(r"(?is)</(p|div|li|tr|h[1-6]|table|section)>", "\n", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = html.unescape(doc)
    doc = re.sub(r"[ \t\u00a0]+", " ", doc)
    doc = re.sub(r"\n\s*\n\s*\n+", "\n\n", doc)
    return doc.strip()


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for url in URLS:
        name = re.sub(r"\W+", "_", url)[-60:]
        try:
            with OPENER.open(url, timeout=120) as resp:
                raw = resp.read()
        except Exception as exc:  # noqa: BLE001
            print("FAILED", url, type(exc).__name__, exc)
            continue
        html_path = os.path.join(OUT, f"paper_{name}.html")
        txt_path = os.path.join(OUT, f"paper_{name}.txt")
        with open(html_path, "wb") as fh:
            fh.write(raw)
        text = strip_tags(raw.decode("utf-8", "replace"))
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("OK", url, "bytes=", len(raw), "text_chars=", len(text))
        print("   html ->", html_path)
        print("   text ->", txt_path)


if __name__ == "__main__":
    main()