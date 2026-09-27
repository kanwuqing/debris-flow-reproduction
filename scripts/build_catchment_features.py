"""Stage 3a: static catchment features (geometry + mitigation) -> processed CSV."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from wenchuan import catchment_geom, clean  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 80)

INTERIM = os.path.join(ROOT, "data", "interim")
PROCESSED = os.path.join(ROOT, "data", "processed")


def main() -> None:
    os.makedirs(PROCESSED, exist_ok=True)

    events = pd.read_csv(os.path.join(INTERIM, "events.csv"), parse_dates=["date"])
    catch = pd.read_csv(os.path.join(INTERIM, "catchments.csv"))
    catch = clean.add_event_counts(catch, events)

    geom = pd.DataFrame(catchment_geom.catchment_polygon_features())
    geom = geom.drop(columns=[c for c in ("n_events",) if c in geom.columns])

    # merge geometry onto the event-count table by C_ID
    out = catch.merge(
        geom[[
            "C_ID", "polygon_index", "poly_area_km2", "poly_perimeter_km",
            "compactness", "bbox_width_km", "bbox_height_km", "bbox_aspect",
            "centroid_lon", "centroid_lat",
        ]],
        on="C_ID",
        how="left",
        validate="one_to_one",
    )

    out["area_check_rel_err"] = (
        (out["poly_area_km2"] - out["area_km2"]).abs() / out["area_km2"]
    )

    print("=" * 78)
    print("CATCHMENT FEATURE TABLE")
    print("=" * 78)
    print("shape:", out.shape)
    print("\narea cross-check (polygon vs .dbf attribute):")
    print(out["area_check_rel_err"].describe().to_string())
    print("max rel err:", out["area_check_rel_err"].max(),
          "| rows >1%:", int((out["area_check_rel_err"] > 0.01).sum()))
    print("\narea_km2 stats:", out["area_km2"].describe().to_dict())
    print("compactness stats:", out["compactness"].describe().to_dict())
    print("centroid lon range:", out["centroid_lon"].min(), out["centroid_lon"].max())
    print("centroid lat range:", out["centroid_lat"].min(), out["centroid_lat"].max())
    print("\ndam_number distribution:")
    print(out["dam_number"].value_counts().sort_index().to_string())
    print("\nbuilt_year distribution:")
    print(out["built_year"].value_counts(dropna=False).sort_index().to_string())
    print("\nn_events distribution:")
    print(out["n_events"].value_counts().sort_index().to_string())
    print("\ncorrelation area vs n_events:",
          out[["area_km2", "n_events"]].corr().iloc[0, 1])
    print("correlation area vs has_dam:",
          out[["area_km2", "has_dam"]].corr().iloc[0, 1])

    path = os.path.join(PROCESSED, "catchment_features.csv")
    out.to_csv(path, index=False, encoding="utf-8")
    print("\nwrote ->", path)


if __name__ == "__main__":
    main()