"""Download candidate open-access references for the empirical I-D threshold baseline.

Nothing is trusted from memory: the numbers used in the report must be readable
in one of the downloaded documents, and the report cites the exact file.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
    ("Accept", "application/pdf,text/html;q=0.9,*/*;q=0.8"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "refs")

TARGETS = [
    ("core_395002208.pdf", "https://core.ac.uk/download/395002208.pdf"),
    ("mdpi_remotesensing_16_1265.pdf", "https://www.mdpi.com/2072-4292/16/7/1265/pdf"),
]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for name, url in TARGETS:
        dst = os.path.join(OUT, name)
        try:
            with OPENER.open(url, timeout=180) as resp:
                blob = resp.read()
        except urllib.error.HTTPError as exc:
            print(f"FAILED {name}: HTTP {exc.code} {exc.reason}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {name}: {type(exc).__name__} {exc}")
            continue
        with open(dst, "wb") as fh:
            fh.write(blob)
        print(f"OK {name}: bytes={len(blob)} magic={blob[:5]!r}")


if __name__ == "__main__":
    main()
