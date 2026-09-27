"""Print the numbers from results/*.json that the report quotes. Read-only."""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(ROOT, "results")

with open(os.path.join(R, "task_a_rainfall_threshold.json"), encoding="utf-8") as fh:
    a = json.load(fh)
with open(os.path.join(R, "task_b_susceptibility.json"), encoding="utf-8") as fh:
    b = json.load(fh)


def show(title, value):
    print(f"\n=== {title} ===")
    print(json.dumps(value, ensure_ascii=False, indent=2)[:4000])


show("A. headline", {k: a[k] for k in
                     ("n_rows", "n_positive", "n_negative", "positive_rate",
                      "n_events", "n_gauges")})
show("A. features", a["features"])
show("A. id_pairs", a["id_pairs"])
show("A. temporal_split", a["temporal_split"])
show("A. id_thresholds", a["id_thresholds"])
show("A. ml_equivalent_threshold", a.get("ml_equivalent_threshold"))
show("A. feature_importance_random_forest", a["feature_importance_random_forest"])
show("A. feature_importance_logistic", a["feature_importance_logistic"])
show("A. per_year_triggering", a["per_year_triggering"])

show("B. headline", {k: b[k] for k in
                     ("n_rows", "n_positive", "n_negative", "median_n_events",
                      "label_rule")})
show("B. features", b["features"])
show("B. excluded", b["excluded_features"])
show("B. models", {k: {kk: vv for kk, vv in v.items() if kk != "oof"}
                   for k, v in b["models"].items()})
show("B. FI rf", b["feature_importance_random_forest"])
show("B. FI lr", b["feature_importance_logistic_regression"])

# catchment-level cross tab of dam vs events, for the discussion section
catch = b["catchments"]
print("\n=== B. dam vs events (cross-check of fig07) ===")
from collections import defaultdict
buckets = defaultdict(list)
for row in catch:
    d = int(row["dam_number"])
    key = "0" if d == 0 else ("1" if d == 1 else ("2" if d == 2 else ">=3"))
    buckets[key].append(row)
for key in ("0", "1", "2", ">=3"):
    rows = buckets[key]
    if not rows:
        continue
    n_ev = sum(r["n_events"] for r in rows)
    print(f"  dams={key:>3}  catchments={len(rows):>2}  events={n_ev:>3}  "
          f"mean_events={n_ev / len(rows):.2f}  "
          f"high_susc={sum(r['susceptible'] for r in rows)}/{len(rows)}")

print("\n=== B. built_year vs events ===")
for year in sorted({r["built_year"] for r in catch if r["built_year"] is not None}):
    rows = [r for r in catch if r["built_year"] == year]
    n_ev = sum(r["n_events"] for r in rows)
    print(f"  built={int(year)}  catchments={len(rows):>2}  events={n_ev:>3}  "
          f"mean={n_ev / len(rows):.2f}")

print("\n=== B. prevented vs events ===")
for flag in (True, False):
    rows = [r for r in catch if bool(r["prevented"]) is flag]
    if not rows:
        continue
    n_ev = sum(r["n_events"] for r in rows)
    print(f"  prevented={flag!s:>5}  catchments={len(rows):>2}  events={n_ev:>3}  "
          f"mean={n_ev / len(rows):.2f}")