"""Dump the attribute tables that ship with the two shapefiles."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wenchuan.dbf import read_dbf  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

TABLES = {
    "catchments": os.path.join(
        RAW, "dataset1", "Dataset1 Debris flow and Triggering rain", "Debris_flow_catchment.dbf"
    ),
    "dams": os.path.join(RAW, "dataset2", "Dataset2 Dam", "Dataset2_damdata.dbf"),
}


def main() -> None:
    for label, path in TABLES.items():
        print("=" * 78)
        print(label, "->", os.path.basename(path))
        if not os.path.exists(path):
            print("  MISSING")
            continue
        t = read_dbf(path)
        print("  n_records:", len(t))
        print("  fields   :", [(f.name, f.type, f.length, f.decimals) for f in t.fields])
        for r in t.records[:5]:
            print("   ", r)
        print("  ...")
        for r in t.records[-3:]:
            print("   ", r)


if __name__ == "__main__":
    main()