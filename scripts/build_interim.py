"""Stage 2: build the interim (cleaned) tables and the rain-event feature table."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from wenchuan import clean, features  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 80)

INTERIM = os.path.join(ROOT, "data", "interim")
PROCESSED = os.path.join(ROOT, "data", "processed")


def section(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    tables = clean.build_all(INTERIM)
    events, rain_index, catch = tables["events"], tables["rain_index"], tables["catchments"]

    section("CLEANED TABLES")
    print("events      :", events.shape)
    print("rain_index  :", rain_index.shape)
    print("catchments  :", catch.shape)
    print("\nevents with C_ID:", int(events["C_ID"].notna().sum()), "/", len(events))
    print("events with rain folder:",
          int(events["DF_ID"].isin(rain_index["DF_ID"]).sum()), "/", len(events))
    print("\ncatchments with dam info:",
          int(catch["dam_number"].notna().sum()), "/", len(catch))
    print("catchments n_events describe:")
    print(catch["n_events"].describe().to_string())
    print("n catchments with 0 events:", int((catch["n_events"] == 0).sum()))

    section("GAUGE SERIES GAP DIAGNOSTICS")
    print(features.gauge_gap_stats(rain_index))

    section("RAIN EVENT FEATURES")
    re_df = features.build_rain_event_table(rain_index, events)
    os.makedirs(PROCESSED, exist_ok=True)
    re_df.to_csv(os.path.join(PROCESSED, "rain_events_raw.csv"), index=False,
                 encoding="utf-8")
    print("rows:", len(re_df))
    print("trigger rows:", int(re_df["is_trigger"].sum()))
    print("DF_ID with a labelled trigger:",
          int(re_df.loc[re_df["is_trigger"], "DF_ID"].nunique()),
          "/ folders", rain_index["DF_ID"].nunique())
    print("\nfeature summary for triggering rainstorms:")
    trig = re_df[re_df["is_trigger"]]
    cols = ["duration_h", "total_mm", "max_1h", "max_24h", "mean_intensity",
            "antecedent_24h", "antecedent_72h", "api"]
    print(trig[cols].describe().to_string())
    print("\nnon-triggering rainstorms:")
    print(re_df.loc[~re_df["is_trigger"], cols].describe().to_string())


if __name__ == "__main__":
    main()