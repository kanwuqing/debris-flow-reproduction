"""Stage-1 exploration: decode the raw dataset and print a structural audit."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wenchuan import io as wio  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    events = wio.load_events()
    section("EVENTS (Dataset1_Debris flow.csv)")
    print("rows:", len(events))
    print("missing datetime:", int(events["datetime"].isna().sum()))
    print(events.loc[events["datetime"].isna(), ["DF_ID", "Gully name", "Year", "Month", "Day"]])
    print("year distribution:")
    print(events["year"].value_counts().sort_index().to_string())
    print("n unique gullies:", events["Gully name"].nunique())
    print("volume non-null:", int(events["Deposition volume (m3)"].notna().sum()), "/", len(events))
    print("lat range:", events["Latitude"].min(), events["Latitude"].max())
    print("lon range:", events["Longitude"].min(), events["Longitude"].max())

    # event dates -> how many DF per date
    per_date = events.groupby(events["datetime"].dt.date).size()
    print("n distinct event dates:", len(per_date))
    print(per_date.sort_values(ascending=False).head(10).to_string())

    index_df = wio.list_rain_files()
    section("RAIN FILE INDEX")
    print("n_files:", len(index_df), " n_folders:", index_df["folder"].nunique())
    print("n distinct stamps:", index_df["stamp"].nunique())
    print("n distinct rg_id:", index_df["rg_id"].nunique())
    print("rg_id values:", sorted(index_df["rg_id"].dropna().astype(int).unique()))
    print("seq range:", index_df["seq"].min(), index_df["seq"].max(),
          " n distinct seq:", index_df["seq"].nunique())
    print("\nfiles per folder (describe):")
    print(index_df.groupby("folder").size().describe().to_string())

    print("\n--- is 'seq' == DF_ID? ---")
    seqs = set(index_df["seq"].dropna().astype(int))
    dfs = set(events["DF_ID"].dropna().astype(int))
    print("seq not in DF_ID:", sorted(seqs - dfs)[:20], "... total", len(seqs - dfs))
    print("DF_ID without rain file:", len(dfs - seqs))

    print("\n--- folder_index vs stamp ---")
    fs = index_df.groupby("folder_index")["stamp_dt"].agg(["min", "max", "nunique"])
    print("folders whose files span >1 stamp:", int((fs["nunique"] > 1).sum()))
    print(fs.head(10).to_string())

    print("\n--- map folder_index to event date ---")
    ev_dates = events.set_index("DF_ID")["date"]
    guess = []
    for fi, grp in index_df.groupby("folder_index"):
        # stamp minus 12h approximates the event date used in the event table
        d = (grp["stamp_dt"].min() - pd.Timedelta(hours=12)).normalize()
        guess.append((fi, d, grp["seq"].nunique(), len(grp), sorted(grp["rg_id"].unique())))
    gdf = pd.DataFrame(guess, columns=["folder_index", "date_guess", "n_seq", "n_files", "gauges"])
    print(gdf.head(15).to_string())

    print("\n--- do folder 'seq' values match the DF_IDs on that date? ---")
    by_date = events.groupby(events["datetime"].dt.date)["DF_ID"].apply(set).to_dict()
    hits, misses = 0, []
    for row in gdf.itertuples():
        target = by_date.get(row.date_guess.date())
        if target is None:
            misses.append((row.folder_index, str(row.date_guess.date()), "no event date"))
            continue
        seqs_in_folder = set(index_df.loc[index_df["folder_index"] == row.folder_index, "seq"].astype(int))
        if seqs_in_folder <= target:
            hits += 1
        else:
            misses.append((row.folder_index, str(row.date_guess.date()),
                           sorted(seqs_in_folder - target)[:5]))
    print("folders whose seq set is a subset of that date's DF_IDs:", hits, "/", len(gdf))
    print("misses (first 10):", misses[:10])

    section("RAIN SERIES SHAPE")
    sample_paths = index_df["path"].head(200).tolist()
    lens, steps, nan_counts = [], [], 0
    for p in sample_paths:
        s = wio.read_rain_series(p)
        lens.append(len(s))
        if len(s) > 2:
            steps.append(s.index.to_series().diff().dropna().dt.total_seconds().div(3600).mode().iloc[0])
        nan_counts += int(s.isna().sum())
    print("n sampled:", len(sample_paths))
    print("series length: min", min(lens), "median", int(np.median(lens)), "max", max(lens))
    print("modal step (h):", pd.Series(steps).value_counts().to_dict())
    print("total NaN values:", nan_counts)

    section("CATCHMENTS + DAMS")
    c = wio.load_catchments()
    print("catchments:", len(c), " unique C_ID:", c["C_ID"].nunique())
    print(c.head(5).to_string())
    print("area_km2 stats:", c["area_km2"].describe().to_dict())
    d = wio.load_dams()
    print("\ndams rows:", len(d), " unique C_ID:", d["C_ID"].nunique())
    print(d.head(8).to_string())
    print("C_ID overlap catchments/dams:", len(set(c["C_ID"]) & set(d["C_ID"])),
          "/ catchments", len(set(c["C_ID"])), "/ dams", len(set(d["C_ID"])))


if __name__ == "__main__":
    main()
