"""Rainfall feature engineering from the hourly gauge series.

The raw archive stores, for every debris-flow event, the hourly rainfall of every
rain gauge within 8 km of the affected catchment, for a window from 7 days before
to 1 day after the event (see the paper's "Triggering rainfalls" section).  That
window contains far more than the single triggering storm, so it also supplies the
*non-triggering* rainstorms needed to build a supervised threshold dataset.

Pipeline implemented here
-------------------------
1. ``split_rain_events`` splits one hourly series into independent rainstorms: a
   rainstorm is a run of wet hours (>= ``WET_MM``) whose internal dry gaps are
   shorter than ``DRY_GAP_H`` hours.
2. ``event_features`` computes, for each rainstorm, the rainfall descriptors used
   by the debris-flow threshold literature: cumulative depth over 1-72 h windows,
   peak and mean intensity, duration, and antecedent rainfall (API).
3. ``label_triggers`` marks the rainstorm that overlaps the debris-flow date.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Tunable constants (all recorded in the report's reproducibility appendix)
# --------------------------------------------------------------------------- #
WET_MM = 0.1          # a hour counts as "wet" above this depth (mm)
DRY_GAP_H = 6         # dry hours needed to separate two rainstorms
MIN_TOTAL_MM = 1.0    # rainstorms below this total depth are discarded
ANTECEDENT_H = (24, 72, 168)
API_K = 0.9           # antecedent precipitation index decay per hour


@dataclass
class RainEventRow:
    DF_ID: int
    RG_ID: int
    rank: int
    start: pd.Timestamp
    end: pd.Timestamp
    duration_h: int
    n_wet_hours: int
    total_mm: float
    max_1h: float
    max_3h: float
    max_6h: float
    max_12h: float
    max_24h: float
    max_48h: float
    max_72h: float
    mean_intensity: float
    peak_intensity: float
    antecedent_24h: float
    antecedent_72h: float
    antecedent_168h: float
    api: float
    is_trigger: bool
    trigger_overlap_h: int


def _rolling_max(values: np.ndarray, window: int) -> float:
    """Maximum sum over any contiguous ``window`` hours (partial windows allowed)."""
    if values.size == 0:
        return 0.0
    if values.size < window:
        return float(values.sum())
    csum = np.concatenate([[0.0], np.cumsum(values)])
    return float((csum[window:] - csum[:-window]).max())


def split_rain_events(series: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Split an hourly series into ``(start, end)`` rainstorm spans.

    ``series`` must be indexed by hourly timestamps with no duplicate index.
    """
    if series.empty:
        return []
    wet = series[series >= WET_MM]
    if wet.empty:
        return []

    times = wet.index.to_list()
    spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = prev = times[0]
    for t in times[1:]:
        gap_h = (t - prev) / pd.Timedelta(hours=1)
        if gap_h > DRY_GAP_H:
            spans.append((start, prev))
            start = t
        prev = t
    spans.append((start, prev))
    return spans


def event_features(
    series: pd.Series, start: pd.Timestamp, end: pd.Timestamp
) -> dict:
    """Rainfall descriptors for the rainstorm spanning ``[start, end]``."""
    block = series.loc[start:end]
    values = block.to_numpy(dtype=float)

    total = float(np.nansum(values))
    duration_h = int((end - start) / pd.Timedelta(hours=1)) + 1
    n_wet = int((values >= WET_MM).sum())
    max_1h = float(np.nanmax(values)) if values.size else 0.0

    pre = series.loc[: start - pd.Timedelta(hours=1)]
    antecedent = {}
    for hours in ANTECEDENT_H:
        antecedent[hours] = float(pre.tail(hours).sum()) if not pre.empty else 0.0

    # API: exponentially weighted sum of all preceding hourly rainfall.
    if pre.empty:
        api = 0.0
    else:
        weights = API_K ** np.arange(pre.size - 1, -1, -1)
        api = float(np.nansum(pre.to_numpy(dtype=float) * weights))

    return dict(
        start=start,
        end=end,
        duration_h=duration_h,
        n_wet_hours=n_wet,
        total_mm=total,
        max_1h=max_1h,
        max_3h=_rolling_max(values, 3),
        max_6h=_rolling_max(values, 6),
        max_12h=_rolling_max(values, 12),
        max_24h=_rolling_max(values, 24),
        max_48h=_rolling_max(values, 48),
        max_72h=_rolling_max(values, 72),
        mean_intensity=total / duration_h if duration_h else 0.0,
        peak_intensity=max_1h,
        antecedent_24h=antecedent[24],
        antecedent_72h=antecedent[72],
        antecedent_168h=antecedent[168],
        api=api,
    )


def label_triggers(
    spans: list[tuple[pd.Timestamp, pd.Timestamp]], event_date: pd.Timestamp
) -> tuple[int, int]:
    """Index of the triggering rainstorm and its overlap (hours) with the DF date.

    A rainstorm is a candidate trigger when it overlaps the debris-flow calendar
    day.  The published archive stores the event time as a 12:00 placeholder in
    the file name and leaves ``Time(24 hour)`` empty for 96 of 186 events, so the
    whole calendar day is used as the trigger window.  When no rainstorm overlaps
    the day, the rainstorm that ended closest before the day is used, which
    matches the "rainfall recorded before the debris flow broke out" reading of
    the dataset.
    """
    day_start = pd.Timestamp(event_date).normalize()
    day_end = day_start + pd.Timedelta(hours=23)

    best_idx, best_overlap = -1, 0
    for i, (s, e) in enumerate(spans):
        lo = max(s, day_start)
        hi = min(e, day_end)
        if hi >= lo:
            overlap = int((hi - lo) / pd.Timedelta(hours=1)) + 1
            if overlap > best_overlap:
                best_idx, best_overlap = i, overlap
    if best_idx >= 0:
        return best_idx, best_overlap

    # fallback: last rainstorm that ended before the event day
    prior = [i for i, (_, e) in enumerate(spans) if e < day_start]
    if prior:
        return prior[-1], 0
    return -1, 0


def build_rain_event_table(
    rain_index: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    """One row per (rain gauge file, rainstorm) with the trigger label."""
    ev_date = (
        events.dropna(subset=["DF_ID"])
        .assign(DF_ID=lambda d: d["DF_ID"].astype(int))
        .set_index("DF_ID")["date"]
    )

    rows: list[dict] = []
    for rec in rain_index.itertuples():
        if not rec.has_name or pd.isna(rec.RG_ID):
            continue
        series = __import__("wenchuan.io", fromlist=["read_rain_series"]).read_rain_series(
            rec.path
        )
        if series.empty:
            continue
        spans = split_rain_events(series)
        if not spans:
            continue

        date = ev_date.get(rec.DF_ID)
        if date is None or pd.isna(date):
            trig_idx, overlap = -1, 0
        else:
            trig_idx, overlap = label_triggers(spans, date)

        for i, (s, e) in enumerate(spans):
            feats = event_features(series, s, e)
            if feats["total_mm"] < MIN_TOTAL_MM:
                continue
            row = RainEventRow(
                DF_ID=int(rec.DF_ID),
                RG_ID=int(rec.RG_ID),
                rank=int(rec.rank) if not pd.isna(rec.rank) else -1,
                is_trigger=(i == trig_idx),
                trigger_overlap_h=overlap if i == trig_idx else 0,
                **feats,
            )
            rows.append(asdict(row))

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["DF_ID", "rank", "start"]).reset_index(drop=True)
    return df


def gauge_gap_stats(rain_index: pd.DataFrame, sample: int = 60) -> dict:
    """Diagnostics: are the hourly series gap-free and strictly 1 h apart?"""
    from . import io as wio

    gaps = []
    steps = []
    for path in rain_index["path"].head(sample):
        s = wio.read_rain_series(path)
        if len(s) < 3:
            continue
        full = pd.date_range(s.index.min(), s.index.max(), freq="h")
        gaps.append(len(full) - len(s))
        d = s.index.to_series().diff().dropna() / pd.Timedelta(hours=1)
        steps.extend(d.unique().tolist())
    return {
        "n_files_sampled": int(sample),
        "max_missing_hours_in_range": int(max(gaps)) if gaps else 0,
        "distinct_step_hours": sorted(set(steps)),
    }