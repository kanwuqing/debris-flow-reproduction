"""Locate open-access copies of the candidate threshold references.

Uses the Unpaywall API (free, no key) to resolve a DOI to its OA locations, then
downloads the PDF/HTML so the coefficients can be read locally instead of being
quoted from memory.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
    ("Accept", "application/pdf,application/json,text/html;q=0.9,*/*;q=0.8"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "refs")
EMAIL = "student@example.edu"

DOIS = {
    "guo2016_geomorphology": "10.1016/j.geomorph.2015.10.009",
    "chang2021_bege": "10.1007/s10064-020-02080-7",
    "ma2017_geomorphology": "10.1016/j.geomorph.2017.01.012",
    "guo2016_ees": "10.1007/s12665-015-5031-1",
    "guo2015_landslides": "10.1007/s10346-015-0608-z",
    "guzzetti2008_landslides": "10.1007/s10346-007-0112-1",
}


def get(url: str, timeout: int = 120):
    with OPENER.open(url, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    report: dict[str, dict] = {}

    for key, doi in DOIS.items():
        print("=" * 74)
        print(key, doi)
        entry: dict = {"doi": doi}
        try:
            blob, _ct = get(
                f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}"
            )
            meta = json.loads(blob.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print("  unpaywall FAILED:", type(exc).__name__, exc)
            report[key] = entry | {"error": str(exc)}
            continue

        entry["title"] = meta.get("title")
        entry["journal"] = meta.get("journal_name")
        entry["year"] = meta.get("year")
        entry["is_oa"] = meta.get("is_oa")
        print("  title:", meta.get("title"))
        print("  journal:", meta.get("journal_name"), meta.get("year"), "is_oa:", meta.get("is_oa"))

        best = meta.get("best_oa_location") or {}
        url = best.get("url_for_pdf") or best.get("url")
        entry["oa_url"] = url
        print("  oa_url:", url)
        if url:
            ext = ".pdf" if (best.get("url_for_pdf") or "").endswith(".pdf") else ".html"
            dst = os.path.join(OUT, key + ext)
            try:
                body, ctype = get(url, timeout=180)
                with open(dst, "wb") as fh:
                    fh.write(body)
                print(f"  saved {len(body)} bytes -> {dst} ({ctype})")
                entry["saved"] = dst
                entry["bytes"] = len(body)
            except Exception as exc:  # noqa: BLE001
                print("  download FAILED:", type(exc).__name__, exc)
                entry["download_error"] = str(exc)
        report[key] = entry

    path = os.path.join(OUT, "oa_lookup.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\nwrote ->", path)


if __name__ == "__main__":
    main()