"""Probe OpenAlex query syntax so the threshold scan can actually find works."""
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
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"),
    ("Accept", "application/json"),
]

TESTS = [
    ("simple_search", "https://api.openalex.org/works?search=Wenchuan%20debris%20flow%20rainfall%20threshold&per-page=10"),
    ("search_oa", "https://api.openalex.org/works?search=Wenchuan%20debris%20flow%20rainfall%20threshold&filter=open_access.is_oa:true&per-page=10"),
    ("title_search", "https://api.openalex.org/works?filter=title.search:debris%20flow%20threshold&per-page=5"),
    ("search_intensity", "https://api.openalex.org/works?search=rainfall%20intensity-duration%20threshold%20debris%20flow&per-page=10"),
]


def main() -> None:
    for tag, url in TESTS:
        try:
            with OPENER.open(url, timeout=90) as resp:
                res = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read()[:300].decode("utf-8", "replace")
            print(f"[{tag}] HTTP {exc.code}: {body}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"[{tag}] FAILED {type(exc).__name__}: {exc}")
            continue
        print(f"\n[{tag}] count={res.get('meta', {}).get('count')}")
        for w in res.get("results", [])[:8]:
            loc = w.get("best_oa_location") or {}
            print("   %s | %s | oa=%s pdf=%s" % (
                w.get("publication_year"),
                (w.get("title") or "")[:95],
                w.get("open_access", {}).get("is_oa"),
                bool(loc.get("pdf_url")),
            ))


if __name__ == "__main__":
    main()