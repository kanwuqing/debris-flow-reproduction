"""Stage-1b exploration: field-quality checks on the event table and the
folder<->DF_ID mapping of the rainfall archive."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wenchuan import io as wio  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)


def section(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    raw = pd.read_csv(
        os.path.join(wio.D1_DIR, "Dataset1_Debris flow.csv"), encoding="utf-8-sig", dtype=str
    )
    section("RAW TIME COLUMN VALUES")
    tc = raw["Time(24 hour)"].fillna("<NaN>").astype(str).str.strip()
    print(tc.value_counts().head(15).to_string())
    print("n distinct:", tc.nunique())

    events = wio.load_events()
    section("EVENTS AFTER PARSING")
    print("rows:", len(events))
    print("rows with DF_ID NaN:")
    print(events[events["DF_ID"].isna()].to_string())
    print("time_missing:", int(events["time_missing"].sum()))
    print("datetime NaT:", int(events["datetime"].isna().sum()))
    print("lat range:", events["lat"].min(), events["lat"].max())
    print("lon range:", events["lon"].min(), events["lon"].max())
    print("\nduplicate (gully, date) pairs:",
          int(events.duplicated(subset=["Gully name", "date"]).sum()))
    print("\nyear x month:")
    print(pd.crosstab(events["year"], events["month"]).to_string())

    section("FOLDER (ID_RG_DF_x) <-> DF_ID")
    idx = wio.list_rain_files()
    folder_ids = set(idx["folder_index"].dropna().astype(int))
    df_ids = set(events["DF_ID"].dropna().astype(int))
    print("n folders with files:", len(folder_ids), " min", min(folder_ids), " max", max(folder_ids))
    print("n DF_ID:", len(df_ids), " min", min(df_ids), " max", max(df_ids))
    print("folders not in DF_ID:", sorted(folder_ids - df_ids))
    print("DF_ID with no folder files:", sorted(df_ids - folder_ids))
    print("DF_ID with empty folder (dir exists, no txt):",
          sorted(set(range(1, 187)) - folder_ids))

    section("STAMP vs EVENT DATE")
    stamp = idx.groupby("folder_index")["stamp_dt"].first().rename("stamp")
    ev = (
        events.dropna(subset=["DF_ID"])
        .assign(DF_ID=lambda d: d["DF_ID"].astype(int))
        .set_index("DF_ID")[["date", "datetime", "time_missing"]]
    )
    m = stamp.to_frame().join(ev, how="left")
    m["day_diff"] = (m["stamp"].dt.normalize() - m["date"]).dt.days
    print(m["day_diff"].value_counts().to_string())
    print("stamp hour values:", sorted(idx["stamp_dt"].dt.hour.unique().tolist()))

    section("RAIN VALUES SANITY")
    paths = idx["path"].head(400).tolist()
    all_vals = []
    for p in paths:
        s = wio.read_rain_series(p)
        all_vals.append(s)
    cat = pd.concat(all_vals)
    print("n hourly values:", len(cat))
    print("describe:", cat.describe().to_dict())
    print("n zeros:", int((cat == 0).sum()), " share %.3f" % float((cat == 0).mean()))
    print("max value:", cat.max(), " argmax file:", cat.idxmax())

    section("PER-EVENT GAUGE COUNTS")
    g = idx.groupby("folder_index").agg(n_gauges=("rg_id", "nunique"), n_files=("path", "size"))
    print(g["n_gauges"].describe().to_string())
    print("events with 1 gauge:", int((g["n_gauges"] == 1).sum()))


if __name__ == "__main__":
    main()
