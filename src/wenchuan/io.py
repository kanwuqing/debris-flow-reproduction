"""Readers for the Zenodo 6891244 Wenchuan post-earthquake debris-flow dataset.

Three raw sources are handled:

1. ``Dataset1_Debris flow.csv``        -- one row per debris-flow (DF) event.
2. ``ID_RG_DF_DATA/ID_RG_DF_*/**.txt`` -- hourly rainfall series, one file per
   (event, rain-gauge) pair.  File names look like ``<seq>_<rg_id>_<stamp>.txt``
   where ``stamp`` is ``YYYYMMDDHH`` and the body is ``YYYYMMDDHH<TAB>mm``
   hourly rainfall.
3. ``Dataset2_Dam.csv``               -- one row per catchment with dam counts.

A hand-written ``.dbf`` reader (``wenchuan.dbf``) supplies the catchment
polygon attributes (area, county) that ship with the shapefile.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .dbf import read_dbf

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
RAW = os.path.join(PROJECT_ROOT, "data", "raw")
D1_DIR = os.path.join(RAW, "dataset1", "Dataset1 Debris flow and Triggering rain")
D2_DIR = os.path.join(RAW, "dataset2", "Dataset2 Dam")
RAIN_DIR = os.path.join(D1_DIR, "ID_RG_DF_DATA")

RAIN_FILENAME_RE = re.compile(r"^(?P<seq>\d+)_(?P<rg_id>\d+)_(?P<stamp>\d{10})$")


# --------------------------------------------------------------------------- #
# Dataset 1, table A: debris-flow events
# --------------------------------------------------------------------------- #
def load_events() -> pd.DataFrame:
    """Load the debris-flow event table with a parsed ``datetime`` column."""
    path = os.path.join(D1_DIR, "Dataset1_Debris flow.csv")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [c.strip() for c in df.columns]

    for col in ("DF_ID", "Year", "Month", "Day"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["Gully name"] = df["Gully name"].astype(str).str.strip()
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["Deposition volume (m3)"] = pd.to_numeric(
        df["Deposition volume (m3)"], errors="coerce"
    )

    hhmm = df["Time(24 hour)"].astype(str).str.extract(r"(?P<h>\d{1,2}):(?P<m>\d{1,2})")
    df["hour"] = pd.to_numeric(hhmm["h"], errors="coerce").astype("Int64")
    df["minute"] = pd.to_numeric(hhmm["m"], errors="coerce").astype("Int64")
    df["time_missing"] = df["hour"].isna() | df["minute"].isna()

    # Build the timestamp from zero-padded strings: pandas' dict-based
    # ``to_datetime`` refuses nullable Int64 with missing values.
    date_part = (
        df["Year"].astype("string").str.zfill(4)
        + "-"
        + df["Month"].astype("string").str.zfill(2)
        + "-"
        + df["Day"].astype("string").str.zfill(2)
    )
    df["date"] = pd.to_datetime(date_part, format="%Y-%m-%d", errors="coerce")

    # 96 of the 186 events carry no clock time (``Time(24 hour)`` == '-'), so the
    # timestamp is built from the date alone for those and flagged instead of
    # being dropped.
    time_part = (
        df["hour"].astype("string").str.zfill(2)
        + ":"
        + df["minute"].astype("string").str.zfill(2)
    ).where(~df["time_missing"], "00:00")
    df["datetime"] = pd.to_datetime(
        date_part + " " + time_part, format="%Y-%m-%d %H:%M", errors="coerce"
    )
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # NOTE: in the published CSV the two coordinate columns are swapped -- the
    # column named ``Latitude`` holds 103.x (longitude) and ``Longitude`` holds
    # 31.x (latitude) for the Longmenshan epicentral area.  They are renamed to
    # truthful columns here; the raw names are preserved in ``*_raw``.
    df["lon"] = df["Latitude"]
    df["lat"] = df["Longitude"]
    df["Latitude_raw"] = df["Latitude"]
    df["Longitude_raw"] = df["Longitude"]
    df = df.drop(columns=["Latitude", "Longitude"])
    return df


# --------------------------------------------------------------------------- #
# Dataset 1, table B: catchment polygons (shapefile attributes)
# --------------------------------------------------------------------------- #
def load_catchments() -> pd.DataFrame:
    """Catchment polygons: name, catchment id (``CID``), county, area in m^2."""
    path = os.path.join(D1_DIR, "Debris_flow_catchment.dbf")
    table = read_dbf(path)
    df = pd.DataFrame(table.to_rows())
    df = df.rename(columns={"Name": "catchment_name", "CID": "C_ID", "County": "county"})
    df["catchment_name"] = df["catchment_name"].astype(str).str.strip()
    df["C_ID"] = df["C_ID"].astype(str).str.strip()
    df["county"] = df["county"].replace("", np.nan)
    df["area_m2"] = pd.to_numeric(df["Area"], errors="coerce")
    df["area_km2"] = df["area_m2"] / 1e6
    return df[["catchment_name", "C_ID", "county", "area_m2", "area_km2"]]


# --------------------------------------------------------------------------- #
# Dataset 2: mitigation measures (check dams)
# --------------------------------------------------------------------------- #
def _parse_built_time(value: str):
    """'2013' -> 2013; '2011-2013' -> 2011 (first year); '-' -> NaN."""
    if value is None:
        return np.nan
    text = str(value).strip()
    if text in ("", "-"):
        return np.nan
    years = re.findall(r"(19|20)\d{2}", text)
    if not years:
        return np.nan
    full = re.findall(r"(?:19|20)\d{2}", text)
    return int(full[0]) if full else np.nan


def load_dams() -> pd.DataFrame:
    """Mitigation table: catchment name(s), dam count, build year, effectiveness."""
    path = os.path.join(D2_DIR, "Dataset2_Dam.csv")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(
        columns={
            "Name": "dam_name",
            "C_ID": "C_ID",
            "Dam number": "dam_number",
            "Built Time": "built_time_raw",
            "Successful prevention and control": "prevention_raw",
            "Country": "county",
        }
    )
    df["dam_name"] = df["dam_name"].astype(str).str.strip()
    df["C_ID"] = df["C_ID"].astype(str).str.strip()
    df["dam_number"] = pd.to_numeric(df["dam_number"], errors="coerce").fillna(0).astype(int)
    df["built_year"] = df["built_time_raw"].map(_parse_built_time)
    prevention = df["prevention_raw"].fillna("-").astype(str).str.strip()
    df["prevention_raw"] = prevention
    df["prevented"] = prevention.str.startswith("Yes")
    df["prevention_known"] = prevention.isin(["Yes", "No"]) | prevention.str.startswith("Yes")
    return df


# --------------------------------------------------------------------------- #
# Dataset 1, table B: hourly rainfall series
# --------------------------------------------------------------------------- #
@dataclass
class RainFile:
    folder: str
    folder_index: int
    seq: int
    rg_id: int
    stamp: str
    path: str


def list_rain_files() -> pd.DataFrame:
    """Index every rainfall ``.txt`` file with its parsed name components."""
    rows: list[dict] = []
    if not os.path.isdir(RAIN_DIR):
        raise FileNotFoundError(RAIN_DIR)
    for folder in os.listdir(RAIN_DIR):
        fpath = os.path.join(RAIN_DIR, folder)
        if not os.path.isdir(fpath):
            continue
        m = re.match(r"ID_RG_DF_(\d+)$", folder)
        folder_index = int(m.group(1)) if m else -1
        for name in os.listdir(fpath):
            stem, ext = os.path.splitext(name)
            if ext.lower() != ".txt":
                continue
            fm = RAIN_FILENAME_RE.match(stem)
            if not fm:
                rows.append(
                    dict(
                        folder=folder,
                        folder_index=folder_index,
                        seq=np.nan,
                        rg_id=np.nan,
                        stamp="",
                        path=os.path.join(fpath, name),
                    )
                )
                continue
            rows.append(
                dict(
                    folder=folder,
                    folder_index=folder_index,
                    seq=int(fm.group("seq")),
                    rg_id=int(fm.group("rg_id")),
                    stamp=fm.group("stamp"),
                    path=os.path.join(fpath, name),
                )
            )
    df = pd.DataFrame(rows)
    df["stamp_dt"] = pd.to_datetime(df["stamp"], format="%Y%m%d%H", errors="coerce")
    return df.sort_values(["folder_index", "seq", "rg_id"]).reset_index(drop=True)


def read_rain_series(path: str) -> pd.Series:
    """Read one hourly rainfall file into a ``pd.Series`` indexed by timestamp.

    The raw files are two whitespace-separated columns (``YYYYMMDDHH`` and
    rainfall in mm) and are *not* guaranteed to be sorted or gap-free; the
    returned series is sorted and duplicate hours are summed.
    """
    stamps: list[str] = []
    values: list[float] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            stamps.append(parts[0])
            try:
                values.append(float(parts[1]))
            except ValueError:
                values.append(np.nan)
    index = pd.to_datetime(pd.Series(stamps), format="%Y%m%d%H", errors="coerce")
    series = pd.Series(values, index=index, dtype="float64")
    series = series[series.index.notna()]
    series = series.groupby(level=0).sum().sort_index()
    return series


def load_all_rain_series(index_df: pd.DataFrame | None = None) -> dict[str, pd.Series]:
    """Read every rainfall file once; keys are the file paths."""
    index_df = list_rain_files() if index_df is None else index_df
    return {row.path: read_rain_series(row.path) for row in index_df.itertuples()}
