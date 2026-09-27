"""Stage 5: verify that the produced artefacts match the reproduction manifest.

The manifest (``results/repro_manifest.json``) stores a SHA-256 for every CSV,
JSON and PNG the pipeline writes.  Re-running ``run_all.py`` on the same raw
archive must reproduce them byte-for-byte, which is the actual claim behind
"fixed random seed, one-click reproduce".

Usage::

    python scripts/verify_results.py            # check
    python scripts/verify_results.py --update   # re-record the manifest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "results", "repro_manifest.json")

#: every artefact the pipeline is expected to produce
TRACKED_GLOBS = [
    "data/interim/events.csv",
    "data/interim/catchments.csv",
    "data/interim/rain_index.csv",
    "data/processed/catchment_features.csv",
    "data/processed/rain_events_raw.csv",
    "data/processed/task_a_rainstorms.csv",
    "results/metrics_summary.csv",
    "results/task_a_rainfall_threshold.json",
    "results/task_b_susceptibility.json",
]
TRACKED_DIRS = ["results/figures"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def collect() -> dict[str, dict]:
    files: dict[str, dict] = {}
    for rel in TRACKED_GLOBS:
        full = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.exists(full):
            files[rel] = {"sha256": sha256(full), "bytes": os.path.getsize(full)}
    for rel_dir in TRACKED_DIRS:
        full_dir = os.path.join(ROOT, rel_dir.replace("/", os.sep))
        if not os.path.isdir(full_dir):
            continue
        for name in sorted(os.listdir(full_dir)):
            full = os.path.join(full_dir, name)
            if os.path.isfile(full):
                rel = f"{rel_dir}/{name}"
                files[rel] = {"sha256": sha256(full), "bytes": os.path.getsize(full)}
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true",
                    help="re-record the manifest instead of checking it")
    args = ap.parse_args()

    current = collect()
    if args.update or not os.path.exists(MANIFEST):
        payload = {
            "note": "SHA-256 of every artefact produced by run_all.py "
                    "(seed 20220901). Re-run run_all.py and this file must not change.",
            "n_files": len(current),
            "files": current,
        }
        os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"recorded {len(current)} artefacts -> {os.path.relpath(MANIFEST, ROOT)}")
        return 0

    with open(MANIFEST, encoding="utf-8") as fh:
        expected = json.load(fh)["files"]

    missing = sorted(set(expected) - set(current))
    extra = sorted(set(current) - set(expected))
    changed = sorted(k for k in set(expected) & set(current)
                     if expected[k]["sha256"] != current[k]["sha256"])

    print(f"manifest artefacts: {len(expected)} | present: {len(current)}")
    if missing:
        print("\nMISSING (in manifest, not on disk):")
        for k in missing:
            print("  -", k)
    if extra:
        print("\nUNTRACKED (on disk, not in manifest):")
        for k in extra:
            print("  +", k)
    if changed:
        print("\nCHANGED (sha256 differs -> not bit-reproducible):")
        for k in changed:
            print(f"  ! {k}\n      expected {expected[k]['sha256'][:16]}\n"
                  f"      actual   {current[k]['sha256'][:16]}")
    if not (missing or extra or changed):
        print("OK: every artefact reproduces bit-for-bit.")
        return 0
    print("\nFAILED: see the lists above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())