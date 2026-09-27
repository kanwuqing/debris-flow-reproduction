"""Assemble the analysis tables used by the two modelling tasks.

Task A (rainfall threshold)
---------------------------
A binary dataset of *rainstorms*, one row per (rainstorm, rain gauge) pair, with
``label = 1`` for the rainstorm that overlaps the recorded debris-flow day and
``label = 0`` for every other rainstorm inside the same 7-day-before / 1-day-after
window.  Negatives therefore come from the archive itself (its own
non-triggering rainstorms) rather than from synthetic sampling.

Task B (catchment susceptibility)
---------------------------------
One row per catchment.  The label follows debris-flow frequency, split at the
median into low / high susceptibility.  Predictors are *event-independent*
attributes only (catchment geometry + mitigation measures); event-derived
columns are excluded because they would leak the label.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import catchment_assign, clean, features

RAIN_FEATURES = [
    "duration_h",
    "n_wet_hours",
    "total_mm",
    "max_1h",
    "max_3h",
    "max_6h",
    "max_12h",
    "max_24h",
    "max_48h",
    "max_72h",
    "mean_intensity",
    "peak_intensity",
    "antecedent_24h",
    "antecedent_72h",
    "antecedent_168h",
    "api",
]

ID_COLUMNS = ["duration_h", "mean_intensity", "peak_intensity", "total_mm"]

CATCHMENT_FEATURES = [
    "area_km2",
    "poly_perimeter_km",
    "compactness",
    "bbox_width_km",
    "bbox_height_km",
    "bbox_aspect",
    "n_gullies",
    "centroid_lon",
    "centroid_lat",
    "dam_number",
    "has_dam",
    "built_year",
    "has_built_year",
]


def build_events_with_catchment() -> pd.DataFrame:
    """Events plus a catchment id: published name join first, geometry fallback."""
    events = clean.clean_events()
    assigned = catchment_assign.assign_catchments(events)
    assigned["C_ID_final"] = assigned["C_ID"].where(
        assigned["C_ID"].notna(), assigned["C_ID_geom"]
    )
    assigned["catchment_source"] = np.where(
        assigned["C_ID"].notna(),
        "name",
        np.where(assigned["C_ID_geom"].notna(), "geometry", "unassigned"),
    )
    return assigned


def build_task_a(events: pd.DataFrame, rain_index: pd.DataFrame) -> pd.DataFrame:
    """Rainstorm-level binary classification table."""
    rain_events = features.build_rain_event_table(rain_index, events)
    if rain_events.empty:
        return rain_events

    meta = (
        events.dropna(subset=["DF_ID"])
        .assign(DF_ID=lambda d: d["DF_ID"].astype(int))
        .set_index("DF_ID")[["C_ID_final", "event_year", "days_since_eq", "Gully name"]]
    )
    out = rain_events.join(meta, on="DF_ID")
    out["label"] = out["is_trigger"].astype(int)
    out["years_since_eq"] = out["days_since_eq"] / 365.25
    return out


def build_task_b(catch: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Catchment-level susceptibility table built from event-independent inputs."""
    from . import catchment_geom

    catch = catch.drop(columns=[c for c in clean.AGG_COLUMNS if c in catch.columns])
    catch = clean.add_event_counts(catch, events)

    geom = pd.DataFrame(catchment_geom.catchment_polygon_features())
    catch = catch.merge(
        geom[[
            "C_ID", "poly_area_km2", "poly_perimeter_km", "compactness",
            "bbox_width_km", "bbox_height_km", "bbox_aspect",
            "centroid_lon", "centroid_lat",
        ]],
        on="C_ID",
        how="left",
        validate="one_to_one",
    )

    med = float(catch["n_events"].median())
    catch["susceptible"] = (catch["n_events"] > med).astype(int)
    catch["n_events_bin"] = pd.cut(
        catch["n_events"], bins=[-0.1, 0, 1, 3, 100],
        labels=["none", "one", "few", "many"],
    ).astype(str)
    catch.attrs["median_n_events"] = med
    return catch
