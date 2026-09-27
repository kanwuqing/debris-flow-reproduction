"""Probe Zenodo records for the Wenchuan debris-flow dataset via proxy.

Fetches record metadata JSON and prints a compact summary. Falls back to
searching the Zenodo API when a record id 404s.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [("User-Agent", "RainGaugeNet-repro/0.1 (research)")]


def get_json(url, timeout=90):
    with OPENER.open(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def summarize(rec):
    md = rec.get("metadata", {})
    print("  id           :", rec.get("id"))
    print("  doi          :", rec.get("doi"))
    print("  conceptdoi   :", rec.get("conceptdoi"))
    print("  title        :", md.get("title"))
    print("  pub_date     :", md.get("publication_date"))
    print("  version      :", md.get("version"))
    print("  resource_type:", (md.get("resource_type") or {}).get("type"))
    files = rec.get("files", [])
    print("  n_files      :", len(files))
    for f in files[:60]:
        print("    -", f.get("key"), f.get("size"), f.get("links", {}).get("self"))
    desc = md.get("description") or ""
    print("  desc_len     :", len(desc))


def main():
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
    os.makedirs(outdir, exist_ok=True)

    ids = sys.argv[1:] or ["6891244", "6355211"]
    for rid in ids:
        print("=" * 70)
        print("RECORD", rid)
        url = "https://zenodo.org/api/records/%s" % rid
        try:
            rec = get_json(url)
        except urllib.error.HTTPError as exc:
            print("  HTTPError", exc.code, exc.reason)
            continue
        except Exception as exc:  # noqa: BLE001
            print("  FAILED:", type(exc).__name__, exc)
            continue
        summarize(rec)
        path = os.path.join(outdir, "zenodo_%s.json" % rid)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
        print("  saved ->", path)

    # Also run a keyword search to discover sibling records / versions.
    print("=" * 70)
    q = urllib.parse.quote('metadata.title:"debris flow" AND metadata.title:"Wenchuan"')
    try:
        res = get_json("https://zenodo.org/api/records?q=%s&size=20" % q)
        print("SEARCH hits:", res.get("hits", {}).get("total"))
        for h in res.get("hits", {}).get("hits", []):
            print("  -", h.get("id"), "|", (h.get("metadata") or {}).get("title"))
    except Exception as exc:  # noqa: BLE001
        print("  SEARCH FAILED:", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
