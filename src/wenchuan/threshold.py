"""Empirical and machine-learned rainfall I-D thresholds.

The classical form is ``I = a * D^-b`` (Caine 1980), with ``I`` the mean
intensity in mm/h and ``D`` the duration in hours.

Why the I-D pair is built from *fixed windows* and not from the wet-spell
------------------------------------------------------------------------
A first attempt defined ``D`` as the length of the wet spell and
``I = total / D``.  That is worse for this archive: wet spells are long
(median 20 h, up to 82 h) because the 6-hour inter-event gap merges successive
monsoon bursts, and the resulting ``(D, I)`` cloud is dominated by a handful of
very long, low-intensity spells.  Measured on the committed rainstorm table the
log-log Pearson r is **+0.274** (n = 1597) -- not zero, but the OLS slope it
produces is set by those few extreme durations rather than by the physical
envelope.  (An earlier version of this docstring claimed r = -0.08; that figure
was never reproduced and has been corrected here.)

The debris-flow literature instead pairs every duration ``D`` with the
**maximum rainfall depth observed in any D-hour window**, ``I(D) = P_max(D)/D``.
Those points do follow the classical power law, and each rainstorm contributes
one point per duration rather than a single point.  ``build_id_pairs``
implements that; ``fit_id_windows`` fits the power law to the resulting cloud.

``evaluate_id_threshold`` scores any ``(a, b)`` curve as a binary classifier on
the rainstorm table so that empirical curves and ML models are compared on
identical rows and labels.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_DURATION_H = 1.0
MIN_INTENSITY = 1e-6

#: window lengths (hours) available as ``max_{h}h`` columns in the rain table
WINDOWS = (1, 3, 6, 12, 24, 48, 72)


@dataclass
class IDThreshold:
    a: float
    b: float
    n: int
    r2: float
    source: str

    def intensity(self, duration_h):
        d = np.maximum(np.asarray(duration_h, dtype=float), MIN_DURATION_H)
        return self.a * d ** (-self.b)

    def equation(self) -> str:
        sign = "-" if self.b >= 0 else "+"
        return f"I = {self.a:.4g} * D^({sign}{abs(self.b):.4g})"

    def as_dict(self) -> dict:
        return dict(a=self.a, b=self.b, n=self.n, r2=self.r2,
                    source=self.source, equation=self.equation())


# --------------------------------------------------------------------------- #
# I-D pair construction
# --------------------------------------------------------------------------- #
def build_id_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Long-form ``(duration_h, intensity)`` pairs from the fixed-window maxima.

    One row per (rainstorm row, duration window) where the window column exists
    and is positive.  ``intensity = max_depth_in_window / window`` (mm/h).
    """
    frames = []
    for w in WINDOWS:
        col = f"max_{w}h"
        if col not in df.columns:
            continue
        depth = pd.to_numeric(df[col], errors="coerce")
        sel = df[depth.notna() & (depth > 0)].copy()
        if sel.empty:
            continue
        sel["duration_h"] = float(w)
        sel["intensity"] = depth[sel.index].to_numpy(dtype=float) / w
        frames.append(sel[["DF_ID", "RG_ID", "label", "duration_h", "intensity",
                           "event_year", "C_ID_final"]])
    if not frames:
        return pd.DataFrame(columns=["DF_ID", "RG_ID", "label", "duration_h",
                                     "intensity", "event_year", "C_ID_final"])
    return pd.concat(frames, ignore_index=True)


def _fit_loglog(d: np.ndarray, i: np.ndarray, source: str) -> IDThreshold:
    x = np.log10(d)
    y = np.log10(i)
    slope, intercept = np.polyfit(x, y, 1)
    pred = intercept + slope * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return IDThreshold(a=float(10 ** intercept), b=float(-slope), n=int(d.size),
                       r2=float(r2), source=source)


def fit_id_windows(
    pairs: pd.DataFrame,
    label: int | None = 1,
    sigma_shift: float = 0.0,
    source: str = "fitted",
    duration_min: float = MIN_DURATION_H,
) -> IDThreshold:
    """Least-squares fit of ``log10 I = log10 a - b log10 D`` on window pairs.

    ``sigma_shift`` moves the line down by that many residual standard
    deviations, which is how a lower envelope is approximated.
    """
    sel = pairs if label is None else pairs[pairs["label"] == label]
    d = sel["duration_h"].to_numpy(dtype=float)
    i = sel["intensity"].to_numpy(dtype=float)
    mask = (d >= duration_min) & (i > MIN_INTENSITY) & np.isfinite(d) & np.isfinite(i)
    d, i = d[mask], i[mask]
    if d.size < 3:
        return IDThreshold(float("nan"), float("nan"), int(d.size), float("nan"), source)

    x, y = np.log10(d), np.log10(i)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    sd = float(np.sqrt(ss_res / max(d.size - 2, 1)))
    return IDThreshold(a=float(10 ** (intercept - sigma_shift * sd)),
                       b=float(-slope), n=int(d.size), r2=float(r2), source=source)


def fit_id_quantile(
    pairs: pd.DataFrame,
    quantile: float = 0.5,
    label: int | None = 1,
    source: str = "fitted-quantile",
) -> IDThreshold:
    """Power law through the intensity quantile of each duration window.

    Because the windows are already discrete durations, the "bins" are exact:
    for each ``D`` the requested quantile of ``I(D)`` over the population is
    taken, and the power law is fitted to those (D, quantile) points.
    """
    sel = pairs if label is None else pairs[pairs["label"] == label]
    xs, ys = [], []
    for w in sorted(sel["duration_h"].unique()):
        vals = sel.loc[sel["duration_h"] == w, "intensity"].to_numpy(dtype=float)
        vals = vals[np.isfinite(vals) & (vals > MIN_INTENSITY)]
        if vals.size < 5:
            continue
        xs.append(np.log10(float(w)))
        ys.append(np.log10(float(np.quantile(vals, quantile))))
    if len(xs) < 3:
        return fit_id_windows(pairs, label=label, source=source)
    x, y = np.array(xs), np.array(ys)
    slope, intercept = np.polyfit(x, y, 1)
    pred = intercept + slope * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return IDThreshold(a=float(10 ** intercept), b=float(-slope), n=int(len(x)),
                       r2=float(r2), source=source)


# --------------------------------------------------------------------------- #
# scoring a threshold curve against the rainstorm table
# --------------------------------------------------------------------------- #
def _curve_at(row_duration: np.ndarray, threshold: IDThreshold) -> np.ndarray:
    return threshold.intensity(row_duration)


def observed_intensity(row: pd.Series, threshold: IDThreshold) -> float:
    """Intensity the row actually reached, measured on the *same* window basis.

    The curve ``I(D)`` is compared against ``P_max(D)/D`` for the row's own
    duration ``D`` -- i.e. the same quantity the threshold was fitted on.  For
    rows without the corresponding window column, ``mean_intensity`` is used.
    """
    d = float(row["duration_h"])
    col = f"max_{int(d)}h"
    if col in row.index and pd.notna(row[col]) and row[col] > 0:
        return float(row[col]) / d
    return float(row.get("mean_intensity", np.nan))


def predict_labels(df: pd.DataFrame, threshold: IDThreshold) -> np.ndarray:
    """Predict 'triggered' when the observed window intensity exceeds the curve."""
    i_obs = np.array([observed_intensity(r, threshold) for _, r in df.iterrows()],
                     dtype=float)
    i_thr = _curve_at(df["duration_h"].to_numpy(dtype=float), threshold)
    return (i_obs > i_thr).astype(int)


def evaluate_id_threshold(
    df: pd.DataFrame, threshold: IDThreshold, label_col: str = "label"
) -> dict:
    """Score ``I(D) > I_threshold(D)`` as a binary classifier on ``df``."""
    y = df[label_col].to_numpy(dtype=int)
    y_hat = predict_labels(df, threshold)

    tp = int(np.sum((y == 1) & (y_hat == 1)))
    fp = int(np.sum((y == 0) & (y_hat == 1)))
    fn = int(np.sum((y == 1) & (y_hat == 0)))
    tn = int(np.sum((y == 0) & (y_hat == 0)))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / len(y) if len(y) else float("nan")
    return dict(
        source=threshold.source,
        a=threshold.a,
        b=threshold.b,
        equation=threshold.equation(),
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        tp=tp, fp=fp, fn=fn, tn=tn,
        n=int(len(y)),
    )


# --------------------------------------------------------------------------- #
# ML-equivalent "learned threshold" in the same I-D space
# --------------------------------------------------------------------------- #
def fit_ml_equivalent_threshold(
    df: pd.DataFrame, model, feature_names: list[str], label_col: str = "label"
) -> dict:
    """Extract a usable I-D rule from a fitted probabilistic classifier.

    A random forest has no closed-form I-D curve, so the fitted probability is
    turned into a *threshold surface*: for each duration window the model is
    evaluated on a synthetic rainstorm whose peak depth sweeps a range, and the
    intensity at which the predicted probability crosses 0.5 is recorded.  That
    gives an ML-derived I-D curve directly comparable with the empirical fits.

    NOTE: this is a diagnostic, not a claim that the paper's authors used it.
    """
    rows = []
    for w in WINDOWS:
        col = f"max_{w}h"
        if col not in feature_names:
            continue
        depth_grid = np.linspace(0.5, 400.0, 400)
        frame = pd.DataFrame({f: np.zeros(len(depth_grid)) for f in feature_names})
        frame[col] = depth_grid
        frame["duration_h"] = float(w)
        frame["n_wet_hours"] = w
        frame["total_mm"] = depth_grid
        frame["max_1h"] = np.minimum(depth_grid, depth_grid / max(w, 1) * 3)
        frame["mean_intensity"] = depth_grid / w
        frame["peak_intensity"] = frame["max_1h"]
        frame = frame[feature_names]
        proba = model.predict_proba(frame)[:, 1]
        crossed = np.where(proba >= 0.5)[0]
        if crossed.size == 0:
            continue
        k = int(crossed[0])
        rows.append({"duration_h": float(w),
                     "threshold_mm": float(depth_grid[k]),
                     "threshold_intensity": float(depth_grid[k] / w)})
    if len(rows) < 3:
        return {}
    pairs = pd.DataFrame(rows)
    fit = _fit_loglog(pairs["duration_h"].to_numpy(dtype=float),
                      pairs["threshold_intensity"].to_numpy(dtype=float),
                      source="ML-derived 0.5-probability contour")
    return {"curve": fit.as_dict(), "points": rows}