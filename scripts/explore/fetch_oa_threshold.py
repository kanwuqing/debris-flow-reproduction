"""Hunt for a *verifiable* published I-D threshold from open-access sources.

The report must not quote a coefficient that cannot be re-read from a document
this environment actually downloaded.  This script therefore:

1. queries OpenAlex for works whose title contains both "debris flow" and
   "threshold" and which are open access, plus a Wenchuan-specific query;
2. downloads the candidate PDFs / landing pages;
3. extracts text and greps for ``I = a D^-b`` style expressions;
4. saves everything it found, with the URL, so the report can cite a file.

Nothing is invented: if no coefficient is recovered, the report says so.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "refs")

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    ("Accept", "application/pdf,application/json,text/html;q=0.9,*/*;q=0.8"),
]

EQ_RE = re.compile(
    r"I\s*(?:=|＝)\s*(\d+(?:\.\d+)?)\s*[·*]?\s*[A-Za-z]{0,3}\s*[\^\u2212\-–]{0,2}\s*\(?\s*[-−]?\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

QUERIES = [
    ('title_and_abstract.search:"debris flow" AND title_and_abstract.search:"rainfall threshold" AND title_and_abstract.search:Wenchuan',
     "wenchuan_threshold"),
    ('title.search:"rainfall intensity-duration" AND title.search:"debris flow"',
     "id_debris"),
    ('title_and_abstract.search:"intensity-duration threshold" AND title_and_abstract.search:"Wenchuan"',
     "id_wenchuan"),
]


def fetch(url: str, timeout: int = 120) -> tuple[bytes, str]:
    with OPENER.open(url, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def strip_html(doc: str) -> str:
    import html as _html

    doc = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    return re.sub(r"\s+", " ", _html.unescape(doc))


def pdf_text(blob: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    import io

    try:
        reader = PdfReader(io.BytesIO(blob))
    except Exception:  # noqa: BLE001
        return ""
    parts = []
    for page in reader.pages[:40]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(parts)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    found: list[dict] = []
    log: list[dict] = []

    for query, tag in QUERIES:
        url = ("https://api.openalex.org/works?filter="
               f"open_access.is_oa:true,title_and_abstract.search:{urllib.parse.quote(query)}"
               "&per-page=25&mailto=student@example.edu")
        try:
            blob, _ = fetch(url)
            res = json.loads(blob.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[{tag}] OpenAlex FAILED: {type(exc).__name__} {exc}")
            continue

        print(f"\n===== {tag}: {res.get('meta', {}).get('count')} hits =====")
        for work in res.get("results", []):
            title = (work.get("title") or "")[:110]
            year = work.get("publication_year")
            loc = work.get("best_oa_location") or {}
            pdf = loc.get("pdf_url")
            landing = loc.get("landing_page_url")
            src = work.get("primary_location", {}).get("source") or {}
            print(f"  [{year}] {title} | {src.get('display_name')} | pdf={bool(pdf)}")
            if not (pdf or landing):
                continue

            text = ""
            used = None
            for candidate in (pdf, landing):
                if not candidate:
                    continue
                try:
                    body, ctype = fetch(candidate)
                except Exception as exc:  # noqa: BLE001
                    print(f"      download failed: {candidate} -> {exc}")
                    continue
                if body[:4] == b"%PDF" or "pdf" in ctype.lower():
                    text = pdf_text(body)
                    used = candidate
                else:
                    text = strip_html(body.decode("utf-8", "replace"))
                    used = candidate
                if text:
                    break
            if not text:
                continue

            hits = []
            for m in EQ_RE.finditer(text):
                start = max(m.start() - 160, 0)
                hits.append({"a": m.group(1), "b": m.group(2),
                             "context": text[start:m.end() + 120]})
            rec = {"tag": tag, "title": work.get("title"), "year": year,
                   "doi": work.get("doi"), "source": used,
                   "n_equation_hits": len(hits), "hits": hits[:8]}
            log.append(rec)
            if hits:
                found.append(rec)
                print(f"      *** {len(hits)} equation-like matches")
                for h in hits[:3]:
                    print(f"          a={h['a']} b={h['b']} :: ...{h['context'][-150:]}")

    with open(os.path.join(OUT, "oa_threshold_scan.json"), "w", encoding="utf-8") as fh:
        json.dump({"scanned": log, "with_equations": found}, fh,
                  ensure_ascii=False, indent=2)
    print(f"\nscanned={len(log)} with_equations={len(found)} -> {OUT}\\oa_threshold_scan.json")


if __name__ == "__main__":
    main()