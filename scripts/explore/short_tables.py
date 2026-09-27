"""Write a SHORT table file for the report's discussion section."""
from __future__ import annotations

import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
catch = pd.read_csv(os.path.join(ROOT, "data", "processed", "catchment_features.csv"))
events = pd.read_csv(os.path.join(ROOT, "data", "interim", "events.csv"))

L: list[str] = []
L.append("DAM_VS_EVENTS")
b = pd.cut(catch["dam_number"], [-0.1, 0, 1, 2, 100], labels=["0", "1", "2", ">=3"])
g = catch.groupby(b, observed=True).agg(n_catch=("C_ID", "size"), n_ev=("n_events", "sum"))
g["mean_ev"] = (g["n_ev"] / g["n_catch"]).round(2)
for k, r in g.iterrows():
    L.append(f"{k},{int(r['n_catch'])},{int(r['n_ev'])},{r['mean_ev']}")

L.append("BUILT_VS_EVENTS")
c = catch.copy()
c["yb"] = c["built_year"].fillna(0).astype(int)
g2 = c.groupby("yb").agg(n_catch=("C_ID", "size"), n_ev=("n_events", "sum"))
g2["mean_ev"] = (g2["n_ev"] / g2["n_catch"]).round(2)
for k, r in g2.iterrows():
    L.append(f"{int(k)},{int(r['n_catch'])},{int(r['n_ev'])},{r['mean_ev']}")

L.append("PREVENTED_VS_EVENTS")
g3 = catch.groupby(catch["prevented"].astype(bool)).agg(
    n_catch=("C_ID", "size"), n_ev=("n_events", "sum"))
g3["mean_ev"] = (g3["n_ev"] / g3["n_catch"]).round(2)
for k, r in g3.iterrows():
    L.append(f"{k},{int(r['n_catch'])},{int(r['n_ev'])},{r['mean_ev']}")

L.append("EVENTS_BY_YEAR")
for y, n in sorted(events["event_year"].value_counts().to_dict().items()):
    L.append(f"{int(y)},{n}")

L.append("CATCHMENT_SOURCE")
ev = pd.read_csv(os.path.join(ROOT, "data", "interim", "events.csv"))
L.append(f"events_with_C_ID,{int(ev['C_ID'].notna().sum())}")
L.append(f"events_total,{len(ev)}")

out = os.path.join(ROOT, "docs", "_tables.txt")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("lines", len(L))