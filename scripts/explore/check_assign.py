"""Compare the name-based and geometry-based event -> catchment assignment."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from wenchuan import catchment_assign, clean  # noqa: E402

pd.set_option("display.width", 220)


def main() -> None:
    events = clean.clean_events()
    assigned = catchment_assign.assign_catchments(events)

    print("=" * 78)
    print("GEOMETRIC ASSIGNMENT")
    print("=" * 78)
    print("hit kind counts:", assigned["geom_hit"].value_counts().to_dict())
    print("\nnearest-centroid distances (km) for misses:")
    miss = assigned[assigned["geom_hit"] == "nearest_centroid"]
    print(miss["centroid_dist_km"].describe().to_string())

    both = assigned.dropna(subset=["C_ID", "C_ID_geom"])
    agree = (both["C_ID"] == both["C_ID_geom"]).mean()
    print("\nname-based C_ID available:", int(assigned["C_ID"].notna().sum()))
    print("geometry-based C_ID available:", int(assigned["C_ID_geom"].notna().sum()))
    print("agreement on rows where both exist: %.4f (%d rows)" % (agree, len(both)))
    disagree = both[both["C_ID"] != both["C_ID_geom"]]
    print("disagreements:", len(disagree))
    print(disagree[["DF_ID", "Gully name", "C_ID", "C_ID_geom", "geom_hit"]].head(20).to_string())

    print("\ncatchments covered by geometry:", assigned["C_ID_geom"].nunique(), "/ 79")
    counts = assigned["C_ID_geom"].value_counts()
    print("catchments with 0 events:",
          79 - counts.shape[0], "->", sorted(set(clean.wio.load_catchments()["C_ID"]) - set(counts.index)))
    print("\nevents per catchment (geometry), describe:")
    print(counts.describe().to_string())
    print("\ntop 15:")
    print(counts.head(15).to_string())

    print("\nname-based coverage:", assigned["C_ID"].nunique(), "/ 79")
    nc = assigned["C_ID"].value_counts()
    print("name-based 0-event catchments:",
          sorted(set(clean.wio.load_catchments()["C_ID"]) - set(nc.index)))

    # unresolved events
    un = assigned[assigned["C_ID_geom"].isna()]
    print("\nunresolved events:", len(un))
    if len(un):
        print(un[["DF_ID", "Gully name", "lon", "lat"]].to_string())


if __name__ == "__main__":
    main()