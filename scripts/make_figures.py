"""Stage 5: figures for the experiment report.

Every figure is written to ``results/figures/*.png`` and the numbers behind it are
already in ``results/*.json`` / ``results/*.csv``, so nothing in the report
depends on reading a picture.

Usage::

    python scripts/make_figures.py
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from wenchuan import threshold  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
FIGS = os.path.join(RESULTS, "figures")

plt.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 140,
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load() -> tuple[pd.DataFrame, dict, dict, pd.DataFrame]:
    task_a = pd.read_csv(os.path.join(ROOT, "data", "processed", "task_a_rainstorms.csv"),
                         parse_dates=["start", "end"])
    with open(os.path.join(RESULTS, "task_a_rainfall_threshold.json"), encoding="utf-8") as fh:
        res_a = json.load(fh)
    with open(os.path.join(RESULTS, "task_b_susceptibility.json"), encoding="utf-8") as fh:
        res_b = json.load(fh)
    catch = pd.read_csv(os.path.join(ROOT, "data", "processed", "catchment_features.csv"))
    return task_a, res_a, res_b, catch


# --------------------------------------------------------------------------- #
def fig_id_scatter(task_a: pd.DataFrame, res_a: dict) -> None:
    trig = task_a[task_a["label"] == 1]
    nont = task_a[task_a["label"] == 0]

    # The correlation is computed here rather than hard-coded: an earlier draft
    # of this figure asserted r = 0.01, which the data do not support (the
    # actual log-log Pearson r on the wet-spell definition is ~0.27).
    sel = task_a[(task_a["total_mm"] > 0) & (task_a["duration_h"] > 0)]
    r_wetspell = float(np.corrcoef(np.log10(sel["duration_h"].to_numpy(dtype=float)),
                                   np.log10(sel["mean_intensity"].to_numpy(dtype=float)))[0, 1])

    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    ax.scatter(nont["duration_h"], nont["mean_intensity"], s=6, c="#b0b7c3",
               alpha=0.5, label=f"non-triggering (n={len(nont)})", edgecolors="none")
    ax.scatter(trig["duration_h"], trig["mean_intensity"], s=8, c="#c0392b",
               alpha=0.6, label=f"triggering (n={len(trig)})", edgecolors="none")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("wet-spell duration D (h)")
    ax.set_ylabel("mean intensity I = total / D (mm/h)")
    ax.set_title("Rainstorm cloud on the wet-spell definition\n"
                 f"log–log Pearson r = {r_wetspell:.3f} (n={len(sel)}), and the OLS slope "
                 "is set by the tails, not by the physical envelope")
    ax.legend(fontsize=6.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig01_id_scatter.png"))
    plt.close(fig)


def fig_id_windows(task_a: pd.DataFrame, res_a: dict) -> None:
    """The window-based I-D cloud, which is what the fits are actually made on."""
    pairs = threshold.build_id_pairs(task_a)
    if pairs.empty:
        return
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for lab, colour, name in [(0, "#b0b7c3", "non-triggering"), (1, "#c0392b", "triggering")]:
        sub = pairs[pairs["label"] == lab]
        ax.scatter(sub["duration_h"], sub["intensity"], s=7, c=colour, alpha=0.45,
                   label=f"{name} (n={len(sub)})", edgecolors="none")
    d = np.logspace(0, np.log10(72), 100)
    styles = {
        "ols_trigger_only": ("-", "#1f77b4"),
        "quantile_p50_trigger": ("--", "#2ca02c"),
        "quantile_p90_trigger": (":", "#9467bd"),
    }
    for rec in res_a["id_thresholds"]:
        if rec["name"] not in styles:
            continue
        ls, colour = styles[rec["name"]]
        thr = threshold.IDThreshold(rec["a"], rec["b"], rec["n"], rec["r2"], rec["name"])
        ax.plot(d, thr.intensity(d), ls, color=colour, lw=1.6,
                label=f"{rec['name']}: {rec['equation']}")
    ml = res_a.get("ml_equivalent_threshold") or {}
    if ml:
        c = ml["curve"]
        thr = threshold.IDThreshold(c["a"], c["b"], c["n"], c["r2"], "ml")
        ax.plot(d, thr.intensity(d), "-.", color="#ff7f0e", lw=1.6,
                label=f"ML 0.5-prob contour: {c['equation']}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("window length D (h)")
    ax.set_ylabel("I(D) = max depth in D hours / D (mm/h)")
    ax.set_title("Fixed-window I–D pairs and fitted thresholds")
    ax.legend(fontsize=6.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig02_id_windows.png"))
    plt.close(fig)


def fig_events_by_year(task_a: pd.DataFrame, res_a: dict) -> None:
    trig = task_a[task_a["label"] == 1]
    per_year = trig.groupby("event_year").agg(
        n_events=("DF_ID", "nunique"),
        n_rows=("label", "size"),
        mean_total_mm=("total_mm", "mean"),
        mean_max1h=("max_1h", "mean"),
    ).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6))
    ax = axes[0]
    ax.bar(per_year["event_year"], per_year["n_events"], color="#c0392b", alpha=0.85)
    for x, y in zip(per_year["event_year"], per_year["n_events"]):
        ax.text(x, y + 0.3, str(int(y)), ha="center", fontsize=7)
    ax.set_xlabel("year")
    ax.set_ylabel("debris-flow events with rain data")
    ax.set_title("Recorded events per year")

    ax = axes[1]
    ax.plot(per_year["event_year"], per_year["mean_total_mm"], "o-",
            color="#1f77b4", label="mean event total (mm)")
    ax.set_xlabel("year")
    ax.set_ylabel("mean total rainfall (mm)")
    ax2 = ax.twinx()
    ax2.plot(per_year["event_year"], per_year["mean_max1h"], "s--",
             color="#ff7f0e", label="mean max 1-h (mm)")
    ax2.set_ylabel("mean max 1-h rainfall (mm)")
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right")
    ax.set_title("Triggering-rainfall magnitude by year")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig03_events_by_year.png"))
    plt.close(fig)


def fig_task_a_models(res_a: dict) -> None:
    protos = ["random", "group_event", "temporal"]
    model_names = [r["model"] for r in res_a["protocols"]["group_event"]]
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.8), sharey=True)
    for ax, proto in zip(axes, protos):
        rows = {r["model"]: r for r in res_a["protocols"].get(proto, [])}
        xs = np.arange(len(model_names))
        acc = [rows[m]["accuracy"] if m in rows else np.nan for m in model_names]
        f1 = [rows[m]["f1"] if m in rows else np.nan for m in model_names]
        ax.bar(xs - 0.2, acc, width=0.4, label="accuracy", color="#1f77b4")
        ax.bar(xs + 0.2, f1, width=0.4, label="F1", color="#ff7f0e")
        ax.set_xticks(xs)
        ax.set_xticklabels([m.replace("_", "\n") for m in model_names], fontsize=7)
        ax.set_ylim(0, 1.05)
        ax.set_title(f"protocol: {proto}")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("score")
    fig.suptitle("Task A — rainstorm classification under three evaluation protocols", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig04_task_a_models.png"))
    plt.close(fig)


def fig_confusion(res_a: dict, res_b: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.5))
    rows = {r["model"]: r for r in res_a["protocols"]["group_event"]}
    cm = np.array(rows["random_forest"]["confusion_matrix"])
    for ax, mat, title in [
        (axes[0], cm, "Task A — random forest, GroupKFold on event"),
    ]:
        im = ax.imshow(mat, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(mat[i, j]), ha="center", va="center",
                        color="black" if mat[i, j] < mat.max() * 0.6 else "white", fontsize=11)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["pred 0", "pred 1"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["true 0", "true 1"])
        ax.set_title(title, fontsize=9)
        ax.grid(False)

    ax = axes[1]
    oof = res_b["models"]["random_forest"]["oof"]
    mat = np.array(oof["confusion_matrix"])
    ax.imshow(mat, cmap="Greens")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(mat[i, j]), ha="center", va="center",
                    color="black" if mat[i, j] < mat.max() * 0.6 else "white", fontsize=11)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["pred low", "pred high"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["true low", "true high"])
    ax.set_title("Task B — random forest, 5-fold OOF", fontsize=9)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig05_confusion.png"))
    plt.close(fig)


def fig_importance(res_a: dict, res_b: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.2))
    for ax, key, title in [
        (axes[0], "feature_importance_random_forest", "Task A — rain features (RF impurity)"),
        (axes[1], "feature_importance_random_forest", "Task B — catchment features (RF impurity)"),
    ]:
        pass

    imp = pd.DataFrame(res_a["feature_importance_random_forest"]).head(12)
    axes[0].barh(imp["feature"][::-1], imp["importance"][::-1], color="#1f77b4")
    axes[0].set_title("Task A — rain features (RF impurity importance)", fontsize=9)

    imp_b = pd.DataFrame(res_b["feature_importance_random_forest"]).head(12)
    axes[1].barh(imp_b["feature"][::-1], imp_b["importance"][::-1], color="#2ca02c")
    axes[1].set_title("Task B — catchment features (RF impurity importance)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig06_feature_importance.png"))
    plt.close(fig)


def fig_susceptibility(res_b: dict) -> None:
    df = pd.DataFrame(res_b["catchments"])
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.5))

    ax = axes[0]
    counts = df["n_events"].value_counts().sort_index()
    ax.bar(counts.index, counts.values, color="#c0392b", alpha=0.85)
    ax.set_xlabel("events recorded in the catchment")
    ax.set_ylabel("number of catchments")
    ax.set_title("Event-count distribution (n=%d)" % len(df))

    ax = axes[1]
    sub = df.dropna(subset=["area_km2"])
    for lab, colour, name in [(0, "#b0b7c3", "low"), (1, "#c0392b", "high")]:
        s = sub[sub["susceptible"] == lab]
        ax.scatter(s["area_km2"], s["n_events"] + 0.05, s=22, c=colour, alpha=0.8,
                   label=f"{name} susceptibility")
    ax.set_xscale("log")
    ax.set_xlabel("catchment area (km$^2$, log)")
    ax.set_ylabel("events (+0.05 jitter)")
    ax.set_title("Area vs events")
    ax.legend(fontsize=7)

    ax = axes[2]
    sub = df.copy()
    sub["dam_bin"] = pd.cut(sub["dam_number"], [-0.1, 0, 1, 2, 100],
                            labels=["0", "1", "2", ">=3"])
    grp = sub.groupby("dam_bin", observed=True)["n_events"].agg(["mean", "count"])
    ax.bar(grp.index.astype(str), grp["mean"], color="#1f77b4", alpha=0.85)
    for i, (m, c) in enumerate(zip(grp["mean"], grp["count"])):
        ax.text(i, m + 0.05, f"n={int(c)}", ha="center", fontsize=7)
    ax.set_xlabel("check dams in the catchment")
    ax.set_ylabel("mean events per catchment")
    ax.set_title("Mitigation vs events")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig07_susceptibility.png"))
    plt.close(fig)


def main() -> None:
    os.makedirs(FIGS, exist_ok=True)
    task_a, res_a, res_b, catch = load()
    fig_id_scatter(task_a, res_a)
    fig_id_windows(task_a, res_a)
    fig_events_by_year(task_a, res_a)
    fig_task_a_models(res_a)
    fig_confusion(res_a, res_b)
    fig_importance(res_a, res_b)
    fig_susceptibility(res_b)
    print("figures written to", FIGS)
    for name in sorted(os.listdir(FIGS)):
        print("  ", name, os.path.getsize(os.path.join(FIGS, name)), "bytes")


if __name__ == "__main__":
    main()