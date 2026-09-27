"""One-click reproduction of the whole Wenchuan debris-flow pipeline.

Runs the five stages in order, from the raw Zenodo archive to the figures:

    1. build_interim.py            raw  -> data/interim/*.csv (+ processed rain table)
    2. build_catchment_features.py catchment geometry + mitigation features
    3. run_models.py               Task A / Task B models + I-D thresholds -> results/
    4. make_figures.py             results/figures/*.png
    5. verify_results.py           re-hash every produced artefact against the manifest

Everything is deterministic: ``SPLIT_SEED = 20220901`` fixes every split and every
estimator's ``random_state``.  Re-running the script on the same raw archive must
produce byte-identical CSV/JSON output (the manifest check enforces it).

Usage::

    python run_all.py              # full pipeline + verification
    python run_all.py --no-verify  # skip the manifest check (first run, or after a
                                   # deliberate methodology change)
    python run_all.py --update-manifest
                                   # re-record results/repro_manifest.json
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(ROOT, "scripts")
PY = sys.executable

STAGES = [
    ("interim tables", "build_interim.py"),
    ("catchment features", "build_catchment_features.py"),
    ("models + thresholds", "run_models.py"),
    ("figures", "make_figures.py"),
]


def run(script: str) -> None:
    path = os.path.join(SCRIPTS, script)
    print("\n" + "#" * 78)
    print(f"# {script}")
    print("#" * 78, flush=True)
    t0 = time.time()
    proc = subprocess.run([PY, path], cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(f"stage failed ({script}), exit code {proc.returncode}")
    print(f"# {script} finished in {time.time() - t0:.1f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the reproduction-manifest check")
    ap.add_argument("--update-manifest", action="store_true",
                    help="re-record results/repro_manifest.json from this run")
    args = ap.parse_args()

    # Task A is cached in data/processed/task_a_rainstorms.csv; delete it so a
    # "one-click reproduce" really rebuilds it from the interim tables.
    cached = os.path.join(ROOT, "data", "processed", "task_a_rainstorms.csv")
    if os.path.exists(cached):
        os.remove(cached)
        print(f"removed cached {os.path.relpath(cached, ROOT)}")

    t0 = time.time()
    for label, script in STAGES:
        print(f"\n=== stage: {label} ===", flush=True)
        run(script)

    if args.update_manifest:
        run("verify_results.py")  # ensures the file list is complete first
        subprocess.run([PY, os.path.join(SCRIPTS, "verify_results.py"),
                        "--update"], cwd=ROOT, check=True)
    elif not args.no_verify:
        run("verify_results.py")

    print(f"\nALL STAGES DONE in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()