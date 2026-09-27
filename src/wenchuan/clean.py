"""Cleaning layer: turn the raw Zenodo archive into three tidy tables.

Outputs (written to ``data/interim/``):

``events.csv``      one row per debris-flow event (DF_ID), with a parsed
                    timestamp, a corrected coordinate pair and the catchment
                    it belongs to.
``catchments.csv``  one row per catchment (79), with area, county, dam count,
                    construction year and event frequency.
``rain_index.csv``  one row per rainfall ``.txt`` file with its decoded
                    ``(rank, rain_gauge, event_stamp)`` and the DF_ID of the
                    folder it lives in.
"""
from __future__ import annotations

import os
import re

import numpy as np
import pandas as pd

from . import io as wio


# --------------------------------------------------------------------------- #
# name normalisation and the event -> catchment join
# --------------------------------------------------------------------------- #
def _norm(name: str) -> str:
    """Lower-case, strip everything but [a-z0-9] (the names are pinyin)."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _split_parts(name: str) -> list[str]:
    return [p.strip() for p in str(name).split("/") if p.strip()]


def build_catchment_lookup(catchments: pd.DataFrame) -> dict[str, str]:
    """Map every normalised sub-name of every catchment to its ``C_ID``.

    The published tables store a catchment as a ``/``-joined list of the gullies
    it contains (e.g. ``Douyaping/Mayangdian/Maliuwan/Qingling/Guanshan`` -> W16),
    while the event table stores a single gully name.  Sub-name expansion plus a
    containment fallback recovers the C_ID for the event table.
    """
    lookup: dict[str, str] = {}
    for row in catchments.itertuples():
        for part in _split_parts(row.catchment_name):
            lookup[_norm(part)] = row.C_ID
    return lookup


def _match_cid(gully: str, lookup: dict[str, str]) -> str | None:
    key = _norm(gully)
    if not key:
        return None
    if key in lookup:
        return lookup[key]
    # containment fallback, longest key first so the most specific name wins
    for cand_key in sorted(lookup, key=len, reverse=True):
        if cand_key and (key in cand_key or cand_key in key):
            return lookup[cand_key]
    return None


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def clean_events() -> pd.DataFrame:
    df = wio.load_events()
    df = df[df["DF_ID"].notna()].copy()
    df["DF_ID"] = df["DF_ID"].astype(int)
    df = df.sort_values("DF_ID").reset_index(drop=True)

    catch = wio.load_catchments()
    lookup = build_catchment_lookup(catch)
    df["C_ID"] = df["Gully name"].map(lambda g: _match_cid(g, lookup))

    # days since the 2008-05-12 Wenchuan mainshock: the standard "recovery"
    # clock used in the post-earthquake debris-flow literature.
    mainshock = pd.Timestamp("2008-05-12")
    df["days_since_eq"] = (df["date"] - mainshock).dt.days
    df["years_since_eq"] = df["days_since_eq"] / 365.25
    df["event_year"] = df["year"]

    keep = [
        "DF_ID", "Gully name", "C_ID", "date", "datetime", "year", "month",
        "hour", "minute", "time_missing", "lon", "lat", "Latitude_raw",
        "Longitude_raw", "Deposition volume (m3)", "Reference of Data source",
        "days_since_eq", "years_since_eq", "event_year",
    ]
    return df[keep]


def clean_rain_index() -> pd.DataFrame:
    idx = wio.list_rain_files().copy()
    idx = idx.dropna(subset=["folder_index"])
    idx["folder_index"] = idx["folder_index"].astype(int)
    idx = idx.rename(
        columns={
            "folder_index": "DF_ID",
            "seq": "rank",
            "rg_id": "RG_ID",
            "stamp": "stamp_raw",
            "stamp_dt": "stamp_dt",
        }
    )
    idx["has_name"] = idx["rank"].notna()
    idx["rank"] = idx["rank"].astype("Int64")
    idx["RG_ID"] = idx["RG_ID"].astype("Int64")
    return idx[["DF_ID", "rank", "RG_ID", "stamp_raw", "stamp_dt", "path", "has_name"]]


def clean_catchments() -> pd.DataFrame:
    catch = wio.load_catchments()
    dams = wio.load_dams()

    dparts: dict[str, str] = {}
    for row in dams.itertuples():
        for part in _split_parts(row.dam_name):
            dparts[_norm(part)] = row.C_ID

    catch["catchment_parts"] = catch["catchment_name"].map(lambda s: "|".join(_split_parts(s)))
    catch["n_gullies"] = catch["catchment_parts"].str.count(r"\|") + 1
    catch["n_name_chars"] = catch["catchment_name"].str.len()

    dam_key = catch["catchment_name"].map(_norm)
    catch = catch.merge(
        dams.rename(columns={"C_ID": "C_ID_dam"})[
            ["C_ID_dam", "dam_number", "built_year", "built_time_raw",
             "prevention_raw", "prevented", "prevention_known"]
        ],
        left_on="C_ID",
        right_on="C_ID_dam",
        how="left",
    ).drop(columns=["C_ID_dam"])

    # second pass for the few rows whose dam-table name only matches a sub-name
    missing = catch["dam_number"].isna()
    if missing.any():
        by_name = {_norm(r.dam_name): r for r in dams.itertuples()}
        for i in catch.index[missing]:
            for part in _split_parts(catch.at[i, "catchment_name"]):
                hit = by_name.get(_norm(part))
                if hit is not None:
                    catch.at[i, "dam_number"] = hit.dam_number
                    catch.at[i, "built_year"] = hit.built_year
                    catch.at[i, "built_time_raw"] = hit.built_time_raw
                    catch.at[i, "prevention_raw"] = hit.prevention_raw
                    catch.at[i, "prevented"] = hit.prevented
                    catch.at[i, "prevention_known"] = hit.prevention_known
                    break

    catch["dam_number"] = catch["dam_number"].fillna(0).astype(int)
    catch["has_dam"] = catch["dam_number"] > 0
    catch["has_built_year"] = catch["built_year"].notna()
    catch["prevention_known"] = catch["prevention_known"].fillna(False)
    catch["prevented"] = catch["prevented"].fillna(False)
    catch["dam_key"] = dam_key.values
    return catch[
        ["catchment_name", "C_ID", "county", "area_m2", "area_km2",
         "catchment_parts", "n_gullies", "dam_number", "has_dam",
         "built_year", "has_built_year", "built_time_raw", "prevention_raw",
         "prevented", "prevention_known"]
    ]


AGG_COLUMNS = [
    "n_events", "first_event", "last_event", "first_event_year", "last_event_year",
    "mean_event_year", "n_events_with_volume", "total_volume_m3", "event_span_years",
]


def add_event_counts(catch: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Attach per-catchment event statistics; idempotent (drops stale columns)."""
    catch = catch.drop(columns=[c for c in AGG_COLUMNS if c in catch.columns]).copy()
    ev = events.dropna(subset=["C_ID"])
    agg = ev.groupby("C_ID").agg(
        n_events=("DF_ID", "size"),
        first_event=("date", "min"),
        last_event=("date", "max"),
        first_event_year=("event_year", "min"),
        last_event_year=("event_year", "max"),
        mean_event_year=("event_year", "mean"),
        n_events_with_volume=("Deposition volume (m3)", "count"),
        total_volume_m3=("Deposition volume (m3)", "sum"),
    )
    catch = catch.merge(agg, left_on="C_ID", right_index=True, how="left")
    for col in ("n_events", "n_events_with_volume"):
        catch[col] = catch[col].fillna(0).astype(int)
    catch["event_span_years"] = (
        catch["last_event_year"] - catch["first_event_year"] + 1
    ).fillna(0).astype(int)
    return catch


def build_all(out_dir: str) -> dict[str, pd.DataFrame]:
    os.makedirs(out_dir, exist_ok=True)
    events = clean_events()
    rain = clean_rain_index()
    catch = add_event_counts(clean_catchments(), events)

    events.to_csv(os.path.join(out_dir, "events.csv"), index=False, encoding="utf-8")
    rain.to_csv(os.path.join(out_dir, "rain_index.csv"), index=False, encoding="utf-8")
    catch.to_csv(os.path.join(out_dir, "catchments.csv"), index=False, encoding="utf-8")
    return {"events": events, "rain_index": rain, "catchments": catch}
