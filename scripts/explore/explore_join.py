"""Check how debris-flow events join onto catchments and dams (name matching)."""
from __future__ import annotations

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wenchuan import io as wio  # noqa: E402

pd.set_option("display.width", 200)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def main() -> None:
    ev = wio.load_events().dropna(subset=["DF_ID"])
    c = wio.load_catchments()
    d = wio.load_dams()

    print("=" * 78)
    print("CATCHMENT NAME -> SPLIT PARTS")
    c["parts"] = c["catchment_name"].map(lambda s: [p.strip() for p in str(s).split("/") if p.strip()])
    print("n catchments:", len(c))
    print("max parts:", c["parts"].map(len).max())
    print("n single-part:", int((c["parts"].map(len) == 1).sum()))
    all_parts = [p for parts in c["parts"] for p in parts]
    print("n total parts:", len(all_parts), " unique:", len(set(all_parts)))

    print("\n" + "=" * 78)
    print("EVENT GULLY NAMES vs CATCHMENT PARTS")
    gullies = sorted(ev["Gully name"].dropna().unique())
    print("n event gullies:", len(gullies))
    pmap = {}
    for row in c.itertuples():
        for p in row.parts:
            pmap.setdefault(norm(p), row.C_ID)
    matched, unmatched = [], []
    for g in gullies:
        cid = pmap.get(norm(g))
        (matched if cid else unmatched).append((g, cid))
    print("exact-normalised matches:", len(matched), "/", len(gullies))
    print("unmatched:", [g for g, _ in unmatched][:40])

    # fuzzy fallback: substring containment either way
    print("\nfuzzy (substring) fallback:")
    fuzzy_ok, still = [], []
    for g, _ in unmatched:
        ng = norm(g)
        cand = [cid for key, cid in pmap.items() if key and (ng in key or key in ng)]
        (fuzzy_ok if cand else still).append((g, cand))
    print("recovered:", len(fuzzy_ok))
    print("still unmatched:", len(still), [g for g, _ in still][:40])

    print("\n" + "=" * 78)
    print("DAM TABLE NAMES vs CATCHMENTS")
    d["parts"] = d["dam_name"].map(lambda s: [p.strip() for p in str(s).split("/") if p.strip()])
    dparts = {}
    for row in d.itertuples():
        for p in row.parts:
            dparts.setdefault(norm(p), row.C_ID)
    ok = sum(1 for row in c.itertuples() if norm(row.catchment_name) in dparts
             or any(norm(p) in dparts for p in row.parts))
    print("catchments reachable from dam table:", ok, "/", len(c))
    print("C_ID sets equal?", set(c["C_ID"]) == set(d["C_ID"]))
    print("in catchments not dams:", sorted(set(c["C_ID"]) - set(d["C_ID"])))
    print("in dams not catchments:", sorted(set(d["C_ID"]) - set(c["C_ID"])))

    print("\n" + "=" * 78)
    print("EVENTS PER C_ID (via fuzzy name)")
    norm_to_cid = dict(pmap)
    for g in gullies:
        ng = norm(g)
        if ng in norm_to_cid:
            continue
        for key, cid in norm_to_cid.items():
            if key and (ng in key or key in ng):
                norm_to_cid[ng] = cid
                break
    ev["C_ID"] = ev["Gully name"].map(lambda g: norm_to_cid.get(norm(g)))
    print("events with C_ID:", int(ev["C_ID"].notna().sum()), "/", len(ev))
    vc = ev["C_ID"].value_counts()
    print("n catchments with >=1 event:", vc.shape[0])
    print(vc.describe().to_string())
    print(vc.head(20).to_string())


if __name__ == "__main__":
    main()
