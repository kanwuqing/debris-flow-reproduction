"""Inventory the raw Zenodo Wenchuan debris-flow dataset without pandas.

Prints the structure of:
  * Dataset1_Debris flow.csv          (event table)
  * ID_RG_DF_DATA/ID_RG_DF_*/**.txt   (per-event hourly rain series)
  * Dataset2_Dam.csv                  (mitigation measures)
"""
import csv
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
D1 = os.path.join(RAW, "dataset1", "Dataset1 Debris flow and Triggering rain")
D2 = os.path.join(RAW, "dataset2", "Dataset2 Dam")


def show_event_table():
    path = os.path.join(D1, "Dataset1_Debris flow.csv")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    print("=" * 78)
    print("EVENT TABLE:", os.path.basename(path))
    print("  n_rows      :", len(rows))
    print("  columns     :", list(rows[0].keys()))
    ids = [r["DF_ID"] for r in rows]
    print("  DF_ID unique:", len(set(ids)))
    print("  duplicate ids:", [k for k, v in Counter(ids).items() if v > 1][:20])
    years = Counter(r["Year"] for r in rows)
    print("  year counts :", dict(sorted(years.items())))
    gullies = Counter(r["Gully name"] for r in rows)
    print("  n_gullies   :", len(gullies))
    print("  top gullies :", gullies.most_common(10))
    vol_missing = sum(1 for r in rows if not (r["Deposition volume (m3)"] or "").strip())
    print("  vol missing :", vol_missing, "/", len(rows))
    refs = Counter(r["Reference of Data source"] for r in rows)
    print("  n_refs      :", len(refs))
    print("  first 3 rows:", rows[:3])


def parse_rain_filename(name):
    """Return (prefix, gauge, stamp) parsed from '<a>_<b>_<stamp>.txt'."""
    stem = os.path.splitext(name)[0]
    m = re.match(r"^(\d+)_(\d+)_(\d{10})$", stem)
    return m.groups() if m else None


def show_rain():
    base = os.path.join(D1, "ID_RG_DF_DATA")
    dirs = sorted(os.listdir(base), key=lambda s: int(s.split("_")[-1]))
    print("=" * 78)
    print("RAIN DATA:", base)
    print("  n_dirs      :", len(dirs))
    empty = []
    per_dir = {}
    n_files = 0
    bad_names = []
    for d in dirs:
        dp = os.path.join(base, d)
        files = sorted(os.listdir(dp)) if os.path.isdir(dp) else []
        per_dir[d] = files
        n_files += len(files)
        if not files:
            empty.append(d)
        for f in files:
            if parse_rain_filename(f) is None:
                bad_names.append(f)
    print("  n_files     :", n_files)
    print("  n_empty_dirs:", len(empty), empty[:50])
    print("  bad names   :", bad_names[:10])

    prefixes = []
    gauges = []
    stamps = []
    for files in per_dir.values():
        for f in files:
            p = parse_rain_filename(f)
            if p:
                prefixes.append(p[0])
                gauges.append(int(p[1]))
                stamps.append(p[2])
    print("  prefix range:", min(int(x) for x in prefixes), "-", max(int(x) for x in prefixes))
    print("  n_prefix    :", len(set(prefixes)))
    print("  prefix len  :", Counter(len(x) for x in prefixes))
    print("  n_gauges    :", len(set(gauges)), sorted(set(gauges)))
    print("  n_stamps    :", len(set(stamps)))
    print("  stamps      :", sorted(set(stamps)))

    # how many files per prefix / per dir
    pre_counter = Counter(prefixes)
    print("  files per prefix (top 10):", pre_counter.most_common(10))
    print("  dirs with most files:", sorted(((len(v), k) for k, v in per_dir.items()), reverse=True)[:10])

    # sample a rain file: line count + first/last lines
    print("-" * 78)
    samples = ["ID_RG_DF_1", "ID_RG_DF_2", "ID_RG_DF_18", "ID_RG_DF_186"]
    for s in samples:
        files = per_dir.get(s) or []
        if not files:
            print(" ", s, "-> EMPTY")
            continue
        for f in files[:3]:
            fp = os.path.join(base, s, f)
            with open(fp, encoding="utf-8", errors="replace") as fh:
                lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
            print(" ", s, "/", f, "n_lines=", len(lines), "first=", lines[0] if lines else None,
                  "last=", lines[-1] if lines else None)


def show_dam():
    path = os.path.join(D2, "Dataset2_Dam.csv")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    print("=" * 78)
    print("DAM TABLE:", os.path.basename(path))
    print("  n_rows      :", len(rows))
    print("  columns     :", list(rows[0].keys()))
    print("  first 5     :", rows[:5])
    print("  built time  :", Counter(r["Built Time"] for r in rows).most_common(15))
    print("  prevention  :", Counter(r["Successful prevention and control"] for r in rows))
    print("  country     :", Counter(r["Country"] for r in rows))
    print("  dam number  :", Counter(r["Dam number"] for r in rows).most_common(10))


if __name__ == "__main__":
    show_event_table()
    show_rain()
    show_dam()