"""Stage 4: train and evaluate the two classification tasks, write JSON/CSV.

Task A -- rainfall threshold (rainstorm level, binary)
Task B -- catchment susceptibility (catchment level, binary)

Protocol notes that matter for reading the numbers
--------------------------------------------------
* Task A rows are not independent: one debris-flow event contributes several
  rain-gauge files and its triggering rainstorm is duplicated across them.  A
  random split therefore leaks.  Three protocols are reported side by side:
  ``random`` (leaky; kept only to quantify the optimism), ``group_event``
  (GroupKFold on DF_ID) and ``temporal`` (train <=2013, test >=2016).
* Task B has 79 rows, so it is scored with repeated stratified 5-fold CV
  (10 repeats) and mean/std are reported.

Usage::

    python scripts/run_models.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import (
    GroupKFold,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    train_test_split,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from wenchuan import clean, dataset, models, threshold  # noqa: E402

SEED = 20220901
RESULTS = os.path.join(ROOT, "results")


def section(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def load_or_build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events = dataset.build_events_with_catchment()
    catch = dataset.build_task_b(clean.clean_catchments(), events)

    processed = os.path.join(ROOT, "data", "processed")
    os.makedirs(processed, exist_ok=True)
    task_a_path = os.path.join(processed, "task_a_rainstorms.csv")
    if os.path.exists(task_a_path):
        task_a = pd.read_csv(task_a_path, parse_dates=["start", "end"])
    else:
        rain_index = pd.read_csv(
            os.path.join(ROOT, "data", "interim", "rain_index.csv"),
            parse_dates=["stamp_dt"],
        )
        task_a = dataset.build_task_a(events, rain_index)
        task_a.to_csv(task_a_path, index=False, encoding="utf-8")
    return events, catch, task_a


# --------------------------------------------------------------------------- #
# Task A
# --------------------------------------------------------------------------- #
def run_task_a(task_a: pd.DataFrame) -> dict:
    df = task_a.dropna(subset=["label"]).copy()
    df["label"] = df["label"].astype(int)
    feats = [f for f in dataset.RAIN_FEATURES if f in df.columns]
    X, y = df[feats], df["label"]

    out: dict = {
        "n_rows": int(len(df)),
        "n_positive": int(y.sum()),
        "n_negative": int((1 - y).sum()),
        "positive_rate": float(y.mean()),
        "n_events": int(df["DF_ID"].nunique()),
        "n_gauges": int(df["RG_ID"].nunique()),
        "features": feats,
        "protocols": {},
    }

    # ---- protocol 1: random split (leaky; optimism estimate only) ----------
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)
    random_rows = []
    for name in models.make_models(len(feats)):
        pipe = models.make_models(len(feats))[name]
        pipe.fit(Xtr, ytr)
        random_rows.append({
            "model": name,
            **models.score_predictions(yte, pipe.predict(Xte),
                                       models.decision_scores(pipe, Xte)),
        })
    out["protocols"]["random"] = random_rows

    # ---- protocol 2: GroupKFold on DF_ID ----------------------------------
    groups = df["DF_ID"].astype(int)
    gkf = GroupKFold(n_splits=min(5, groups.nunique()))
    group_rows = []
    for name in models.make_models(len(feats)):
        pred = np.zeros(len(df), dtype=int)
        score = np.zeros(len(df), dtype=float)
        for tr, te in gkf.split(X, y, groups):
            if len(np.unique(y.iloc[tr])) < 2:
                pred[te] = int(y.iloc[tr].mode().iloc[0])
                score[te] = float(pred[te][0])
                continue
            pipe = models.make_models(len(feats))[name]
            pipe.fit(X.iloc[tr], y.iloc[tr])
            pred[te] = pipe.predict(X.iloc[te])
            score[te] = models.decision_scores(pipe, X.iloc[te])
        group_rows.append({"model": name,
                           **models.score_predictions(y, pred, score)})
    out["protocols"]["group_event"] = group_rows

    # ---- protocol 3: temporal holdout -------------------------------------
    years = df["event_year"].astype(float)
    tr_mask, te_mask = (years <= 2013).to_numpy(), (years >= 2016).to_numpy()
    temporal_rows = []
    if tr_mask.sum() and te_mask.sum() and len(np.unique(y[tr_mask])) == 2:
        for name in models.make_models(len(feats)):
            pipe = models.make_models(len(feats))[name]
            pipe.fit(X[tr_mask], y[tr_mask])
            temporal_rows.append({
                "model": name,
                **models.score_predictions(y[te_mask], pipe.predict(X[te_mask]),
                                           models.decision_scores(pipe, X[te_mask])),
            })
    out["protocols"]["temporal"] = temporal_rows
    out["temporal_split"] = {
        "train_years": sorted(pd.unique(years[tr_mask]).tolist()),
        "test_years": sorted(pd.unique(years[te_mask]).tolist()),
        "n_train": int(tr_mask.sum()),
        "n_test": int(te_mask.sum()),
    }

    # ---- I-D threshold fits on fixed-window maxima -------------------------
    pairs = threshold.build_id_pairs(df)
    out["id_pairs"] = {
        "n_rows": int(len(pairs)),
        "windows": [int(w) for w in sorted(pairs["duration_h"].unique())] if len(pairs) else [],
    }

    candidates = [
        ("ols_all_points", threshold.fit_id_windows(
            pairs, label=None, source="OLS on all window points")),
        ("ols_trigger_only", threshold.fit_id_windows(
            pairs, label=1, source="OLS on triggering window points")),
        ("ols_trigger_minus_1sd", threshold.fit_id_windows(
            pairs, label=1, sigma_shift=1.0,
            source="trigger points, OLS shifted down 1 residual sigma")),
        ("quantile_p50_trigger", threshold.fit_id_quantile(
            pairs, 0.50, label=1, source="P50 of triggering window intensities")),
        ("quantile_p90_trigger", threshold.fit_id_quantile(
            pairs, 0.90, label=1, source="P90 of triggering window intensities")),
        ("quantile_p90_all", threshold.fit_id_quantile(
            pairs, 0.90, label=None, source="P90 of all window intensities")),
    ]
    out["id_thresholds"] = []
    for name, thr in candidates:
        metrics = threshold.evaluate_id_threshold(df, thr)
        out["id_thresholds"].append({"name": name, **thr.as_dict(), **metrics})

    # ---- ML-derived I-D contour -------------------------------------------
    rf = models.make_models(len(feats))["random_forest"]
    rf.fit(X, y)
    out["ml_equivalent_threshold"] = threshold.fit_ml_equivalent_threshold(
        df, rf, feats
    )
    imp_rf = models.feature_importance(rf, feats)
    out["feature_importance_random_forest"] = (
        imp_rf.to_dict(orient="records") if imp_rf is not None else []
    )
    lr = models.make_models(len(feats))["logistic_regression"]
    lr.fit(X, y)
    imp_lr = models.feature_importance(lr, feats)
    out["feature_importance_logistic"] = (
        imp_lr.to_dict(orient="records") if imp_lr is not None else []
    )

    # ---- temporal decay of the event rate (paper's "recovery" question) ----
    trig = df[df["label"] == 1]
    per_year = (
        trig.groupby("event_year")
        .agg(n_trigger_rows=("label", "size"),
             n_events=("DF_ID", "nunique"),
             mean_duration_h=("duration_h", "mean"),
             mean_total_mm=("total_mm", "mean"),
             mean_max1h=("max_1h", "mean"),
             mean_intensity=("mean_intensity", "mean"))
        .reset_index()
    )
    out["per_year_triggering"] = per_year.to_dict(orient="records")

    return out


# --------------------------------------------------------------------------- #
# Task B
# --------------------------------------------------------------------------- #
def run_task_b(catch: pd.DataFrame) -> dict:
    df = catch.dropna(subset=["susceptible"]).copy()
    df["susceptible"] = df["susceptible"].astype(int)
    feats = [f for f in dataset.CATCHMENT_FEATURES if f in df.columns]
    X, y = df[feats], df["susceptible"]

    out: dict = {
        "n_rows": int(len(df)),
        "n_positive": int(y.sum()),
        "n_negative": int((1 - y).sum()),
        "median_n_events": float(df["n_events"].median()),
        "label_rule": "susceptible = (n_events > median(n_events))",
        "features": feats,
        "excluded_features": {
            "event_derived": ["n_events", "first_event", "last_event",
                              "total_volume_m3", "event_span_years"],
            "reason": "event-derived columns would leak the label",
        },
        "models": {},
    }

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
    for name in models.make_models(len(feats)):
        accs, f1s, aucs, precs, recs = [], [], [], [], []
        for tr, te in cv.split(X, y):
            pipe = models.make_models(len(feats))[name]
            pipe.fit(X.iloc[tr], y.iloc[tr])
            m = models.score_predictions(
                y.iloc[te], pipe.predict(X.iloc[te]),
                models.decision_scores(pipe, X.iloc[te]),
            )
            accs.append(m["accuracy"]); f1s.append(m["f1"])
            precs.append(m["precision"]); recs.append(m["recall"])
            aucs.append(m.get("roc_auc", float("nan")))
        out["models"][name] = {
            "accuracy_mean": float(np.nanmean(accs)),
            "accuracy_std": float(np.nanstd(accs)),
            "precision_mean": float(np.nanmean(precs)),
            "recall_mean": float(np.nanmean(recs)),
            "f1_mean": float(np.nanmean(f1s)),
            "f1_std": float(np.nanstd(f1s)),
            "roc_auc_mean": float(np.nanmean(aucs)),
            "n_folds": int(len(accs)),
        }

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for name in ("random_forest", "logistic_regression"):
        pred = np.zeros(len(df), dtype=int)
        score = np.zeros(len(df), dtype=float)
        for tr, te in skf.split(X, y):
            pipe = models.make_models(len(feats))[name]
            pipe.fit(X.iloc[tr], y.iloc[tr])
            pred[te] = pipe.predict(X.iloc[te])
            score[te] = models.decision_scores(pipe, X.iloc[te])
        out["models"][name]["oof"] = models.score_predictions(y, pred, score)
        pipe = models.make_models(len(feats))[name]
        pipe.fit(X, y)
        imp = models.feature_importance(pipe, feats)
        if imp is not None:
            out[f"feature_importance_{name}"] = imp.to_dict(orient="records")

    out["catchments"] = df[[
        "C_ID", "catchment_name", "county", "area_km2", "n_events", "susceptible",
        "dam_number", "built_year", "prevented", "poly_perimeter_km", "compactness",
    ]].to_dict(orient="records")
    return out


def main() -> None:
    os.makedirs(RESULTS, exist_ok=True)
    events, catch, task_a = load_or_build()

    section("TASK A -- RAINFALL THRESHOLD")
    res_a = run_task_a(task_a)
    print("rows:", res_a["n_rows"], " positives:", res_a["n_positive"],
          " rate:", round(res_a["positive_rate"], 4))
    for proto, rows in res_a["protocols"].items():
        print(f"\n[{proto}]")
        for r in rows:
            print("  %-22s acc=%.4f prec=%.4f rec=%.4f f1=%.4f auc=%.4f" % (
                r["model"], r["accuracy"], r["precision"], r["recall"], r["f1"],
                r.get("roc_auc", float("nan"))))
    print("\nI-D threshold fits (window-based):")
    for r in res_a["id_thresholds"]:
        print("  %-24s %-34s n=%5d acc=%.4f prec=%.4f rec=%.4f f1=%.4f" % (
            r["name"], r["equation"], r["n"], r["accuracy"], r["precision"],
            r["recall"], r["f1"]))
    ml = res_a.get("ml_equivalent_threshold") or {}
    if ml:
        print("  ML-derived contour:", ml["curve"]["equation"])

    section("TASK B -- CATCHMENT SUSCEPTIBILITY")
    res_b = run_task_b(catch)
    print("rows:", res_b["n_rows"], " positives:", res_b["n_positive"],
          " median n_events:", res_b["median_n_events"])
    for name, m in res_b["models"].items():
        print("  %-22s acc=%.4f+-%.4f prec=%.4f rec=%.4f f1=%.4f+-%.4f auc=%.4f" % (
            name, m["accuracy_mean"], m["accuracy_std"], m["precision_mean"],
            m["recall_mean"], m["f1_mean"], m["f1_std"], m["roc_auc_mean"]))

    with open(os.path.join(RESULTS, "task_a_rainfall_threshold.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res_a, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(RESULTS, "task_b_susceptibility.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res_b, fh, ensure_ascii=False, indent=2)

    rows = []
    for proto, rs in res_a["protocols"].items():
        for r in rs:
            rows.append({"task": "A", "protocol": proto, "model": r["model"],
                         "accuracy": r["accuracy"], "precision": r["precision"],
                         "recall": r["recall"], "f1": r["f1"],
                         "roc_auc": r.get("roc_auc"),
                         "confusion_matrix": json.dumps(r["confusion_matrix"])})
    for r in res_a["id_thresholds"]:
        rows.append({"task": "A", "protocol": "id_threshold", "model": r["name"],
                     "accuracy": r["accuracy"], "precision": r["precision"],
                     "recall": r["recall"], "f1": r["f1"],
                     "roc_auc": None,
                     "confusion_matrix": json.dumps([[r["tn"], r["fp"]],
                                                     [r["fn"], r["tp"]]]),
                     "equation": r["equation"], "n": r["n"]})
    for name, m in res_b["models"].items():
        rows.append({"task": "B", "protocol": "repeated_5fold_x10", "model": name,
                     "accuracy": m["accuracy_mean"], "precision": m["precision_mean"],
                     "recall": m["recall_mean"], "f1": m["f1_mean"],
                     "roc_auc": m["roc_auc_mean"], "confusion_matrix": None})
    pd.DataFrame(rows).to_csv(os.path.join(RESULTS, "metrics_summary.csv"),
                              index=False, encoding="utf-8")
    print("\nwrote ->", RESULTS)


if __name__ == "__main__":
    main()