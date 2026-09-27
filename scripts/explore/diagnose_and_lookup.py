"""Diagnose the I-D fit and try to obtain verifiable published threshold coefficients.

Two independent questions:
1. Why is the fitted exponent nearly zero on this dataset?  (print the raw
   duration/intensity pairs, their correlation, and the fit on trigger-only rows)
2. Can any *published* I-D coefficient be verified from an open source that this
   environment can actually download?  Nothing is quoted from memory: every
   number printed here is either computed from the local data or extracted from a
   downloaded document/API response.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    ("Accept", "application/json,text/html;q=0.9,*/*;q=0.8"),
]

OUT = os.path.join(ROOT, "docs", "refs")

DOIS = {
    "guo2016_geomorphology": "10.1016/j.geomorph.2015.10.009",
    "chang2021_bege": "10.1007/s10064-020-02080-7",
    "ma2017_geomorphology": "10.1016/j.geomorph.2017.01.012",
    "guo2016_ees_temporal": "10.1007/s12665-015-5031-1",
    "guo2015_landslides_spatial": "10.1007/s10346-015-0608-z",
    "guzzetti2008_landslides": "10.1007/s10346-007-0112-1",
    "caine1980": "10.2307/520449",
}

ID_PATTERN = re.compile(
    r"[IＩ]\s*=\s*[0-9]+(?:\.[0-9]+)?\s*[A-Za-z]{0,3}\s*[\^\*]?\s*\(?\s*-?\s*[0-9]+(?:\.[0-9]+)?"
)


# --------------------------------------------------------------------------- #
# 1. local diagnostic
# --------------------------------------------------------------------------- #
def local_diagnostic() -> None:
    from wenchuan import dataset, threshold

    task_a = pd.read_csv(
        os.path.join(ROOT, "data", "processed", "task_a_rainstorms.csv"),
        parse_dates=["start", "end"],
    )
    trig = task_a[task_a["label"] == 1]

    print("=" * 78)
    print("LOCAL I-D DIAGNOSTIC (triggering rainstorms only)")
    print("=" * 78)
    print("n trigger rows:", len(trig), "| unique DF_ID:", trig["DF_ID"].nunique())
    print("duration_h describe:")
    print(trig["duration_h"].describe().to_string())
    print("mean_intensity describe:")
    print(trig["mean_intensity"].describe().to_string())
    print("\nPearson corr(duration, mean_intensity) = %.4f" %
          trig[["duration_h", "mean_intensity"]].corr().iloc[0, 1])
    print("Pearson corr(log10 duration, log10 intensity) = %.4f" %
          np.corrcoef(np.log10(trig["duration_h"]),
                      np.log10(trig["mean_intensity"]))[0, 1])

    for label, thr in [
        ("mean intensity, OLS", threshold.fit_id_envelope(trig)),
        ("peak intensity (max_1h), OLS", threshold.fit_id_envelope(
            trig, intensity_col="max_1h")),
        ("total depth, OLS", threshold.fit_id_envelope(
            trig, intensity_col="total_mm")),
    ]:
        print("  %-30s a=%.4g b=%.4g n=%d r2=%.4f" %
              (label, thr.a, thr.b, thr.n, thr.r2))

    print("\nduration-binned mean intensity (trigger rows):")
    bins = [1, 3, 6, 12, 24, 48, 100]
    g = trig.groupby(pd.cut(trig["duration_h"], bins), observed=True).agg(
        n=("mean_intensity", "size"),
        mean_I=("mean_intensity", "mean"),
        median_I=("mean_intensity", "median"),
        mean_total=("total_mm", "mean"),
    )
    print(g.to_string())


# --------------------------------------------------------------------------- #
# 2. reference lookups
# --------------------------------------------------------------------------- #
def fetch(url: str, timeout: int = 90) -> tuple[bytes, str]:
    with OPENER.open(url, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def strip_html(doc: str) -> str:
    import html as _html

    doc = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = _html.unescape(doc)
    return re.sub(r"\s+", " ", doc)


def lookup() -> None:
    os.makedirs(OUT, exist_ok=True)
    report: dict[str, dict] = {}

    print("\n" + "=" * 78)
    print("REFERENCE LOOKUP (only what is actually downloaded is reported)")
    print("=" * 78)

    for key, doi in DOIS.items():
        entry: dict = {"doi": doi}
        print("-", key, doi)

        # Crossref: title + abstract (some Elsevier abstracts include the equation)
        try:
            blob, _ = fetch(f"https://api.crossref.org/works/{doi}")
            msg = json.loads(blob.decode("utf-8"))["message"]
            entry["title"] = (msg.get("title") or [None])[0]
            entry["container"] = (msg.get("container-title") or [None])[0]
            entry["year"] = (msg.get("issued", {}).get("date-parts") or [[None]])[0][0]
            abstract = strip_html(msg.get("abstract") or "")
            entry["abstract"] = abstract[:4000]
            entry["abstract_equations"] = ID_PATTERN.findall(abstract)
            print("   crossref:", entry["container"], entry["year"],
                  "abstract_chars:", len(abstract))
            if entry["abstract_equations"]:
                print("   EQUATIONS IN ABSTRACT:", entry["abstract_equations"])
        except Exception as exc:  # noqa: BLE001
            entry["crossref_error"] = f"{type(exc).__name__}: {exc}"
            print("   crossref FAILED:", entry["crossref_error"])

        # OpenAlex: OA location + inverted abstract
        try:
            blob, _ = fetch(f"https://api.openalex.org/works/doi:{doi}")
            oa = json.loads(blob.decode("utf-8"))
            entry["openalex_oa_url"] = (oa.get("best_oa_location") or {}).get("pdf_url") \
                or (oa.get("best_oa_location") or {}).get("landing_page_url")
            entry["is_oa"] = oa.get("open_access", {}).get("is_oa")
            print("   openalex is_oa:", entry["is_oa"], "url:", entry["openalex_oa_url"])
        except Exception as exc:  # noqa: BLE001
            entry["openalex_error"] = f"{type(exc).__name__}: {exc}"
            print("   openalex FAILED:", entry["openalex_error"])

        report[key] = entry

    path = os.path.join(OUT, "reference_lookup.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\nwrote ->", path)


if __name__ == "__main__":
    local_diagnostic()
    lookup()
