"""Download the Zenodo record 6891244 files (Wenchuan debris-flow datasets)."""
import json
import os
import sys
import urllib.request

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [("User-Agent", "RainGaugeNet-repro/0.1 (research)")]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print("  skip (exists):", os.path.basename(dest), os.path.getsize(dest))
        return
    tmp = dest + ".part"
    with OPENER.open(url, timeout=300) as resp, open(tmp, "wb") as fh:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, dest)
    print("  saved:", os.path.basename(dest), os.path.getsize(dest))


def main():
    os.makedirs(RAW, exist_ok=True)
    meta_path = os.path.join(RAW, "zenodo_6891244.json")
    rec = json.load(open(meta_path, encoding="utf-8"))
    for f in rec["files"]:
        key = f["key"]
        url = f["links"]["self"]
        print("-", key)
        download(url, os.path.join(RAW, key))


if __name__ == "__main__":
    main()
