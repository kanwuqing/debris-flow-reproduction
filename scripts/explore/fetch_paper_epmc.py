"""Fetch the data-descriptor paper full text from Europe PMC (open access).

DOI 10.1038/s41597-022-01658-y  (Sci Data 9, 566, 2022).  The Nature landing
page is JS-gated, so the Europe PMC REST API is used to obtain the JATS XML and
the rendered abstract, plus the supplementary-material listing.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request

PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:10808"
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
OPENER.addheaders = [("User-Agent", "WenchuanRepro/0.1 (research; contact: student)")]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "raw")
DOI = "10.1038/s41597-022-01658-y"


def get(url: str, timeout: int = 120) -> bytes:
    with OPENER.open(url, timeout=timeout) as resp:
        return resp.read()


def strip_tags(doc: str) -> str:
    doc = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?is)<br\s*/?>", "\n", doc)
    doc = re.sub(r"(?is)</(p|div|li|tr|h[1-6]|table|sec|title|abstract)>", "\n", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = html.unescape(doc)
    doc = re.sub(r"[ \t\u00a0]+", " ", doc)
    doc = re.sub(r"\n\s*\n\s*\n+", "\n\n", doc)
    return doc.strip()


def main() -> None:
    os.makedirs(OUT, exist_ok=True)

    q = urllib.parse.quote(f'DOI:"{DOI}"')
    meta = json.loads(
        get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            f"?query={q}&resultType=core&format=json"
        ).decode("utf-8")
    )
    with open(os.path.join(OUT, "epmc_search.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    hits = meta.get("resultList", {}).get("result", [])
    if not hits:
        print("NO HITS for", DOI)
        return
    rec = hits[0]
    pmcid = rec.get("pmcid")
    print("title      :", rec.get("title"))
    print("journal    :", (rec.get("journalInfo") or {}).get("journal", {}).get("title"))
    print("year/vol   :", rec.get("pubYear"), (rec.get("journalInfo") or {}).get("volume"))
    print("pmcid      :", pmcid, " isOpenAccess:", rec.get("isOpenAccess"))
    print("authors    :", rec.get("authorString"))
    print("abstract len:", len(rec.get("abstractText") or ""))

    if pmcid:
        xml = get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/"
            f"{pmcid}/fullTextXML"
        ).decode("utf-8", "replace")
        with open(os.path.join(OUT, f"{pmcid}_fulltext.xml"), "w", encoding="utf-8") as fh:
            fh.write(xml)
        text = strip_tags(xml)
        with open(os.path.join(OUT, f"{pmcid}_fulltext.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        print("fulltext chars:", len(text))

        supp = get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/"
            f"{pmcid}/supplementaryFiles"
        )
        with open(os.path.join(OUT, f"{pmcid}_supp.zip"), "wb") as fh:
            fh.write(supp)
        print("supplementary bytes:", len(supp))


if __name__ == "__main__":
    main()
