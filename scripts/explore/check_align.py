"""Verify that the shapefile record order matches the .dbf record order.

If the two disagree, any index-based polygon<->attribute join is wrong, so this
compares the shoelace polygon area with the ``Area`` attribute for every record.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from wenchuan import geometry as geo  # noqa: E402
from wenchuan import io as wio  # noqa: E402


def main() -> None:
    shapes = geo.read_shp(os.path.join(wio.D1_DIR, "Debris_flow_catchment.shp"))
    catch = wio.load_catchments()
    print("n_shapes:", len(shapes), " n_dbf:", len(catch))

    rows = []
    for i, shape in enumerate(shapes):
        a, _, _ = geo.polygon_area_centroid(shape)
        rows.append((i, catch.iloc[i]["C_ID"], catch.iloc[i]["catchment_name"][:28],
                     abs(a), catch.iloc[i]["area_m2"]))
    df = pd.DataFrame(rows, columns=["idx", "C_ID", "name", "shoelace_m2", "attr_m2"])
    df["rel_err"] = (df["shoelace_m2"] - df["attr_m2"]).abs() / df["attr_m2"]
    print("rel_err describe:")
    print(df["rel_err"].describe().to_string())
    print("n rows with rel_err > 1e-6:", int((df["rel_err"] > 1e-6).sum()))
    print(df[df["rel_err"] > 1e-6].head(15).to_string())

    print("\nname-based lookup (top names by event count):")
    for cid in ["W4", "W16", "W27", "W63", "W15", "W26", "W29", "W12"]:
        sub = catch[catch["C_ID"] == cid]
        if len(sub):
            print(" ", cid, "->", sub.iloc[0]["catchment_name"],
                  "area_km2=", round(sub.iloc[0]["area_km2"], 3))
        else:
            print(" ", cid, "-> NOT IN CATCHMENT TABLE")

    print("\ncatchment name list (C_ID: name):")
    for row in catch.sort_values("C_ID").itertuples():
        print("  %-5s %s" % (row.C_ID, row.catchment_name))


if __name__ == "__main__":
    main()