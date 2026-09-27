"""Emit the verified numbers the report quotes -> docs/_numbers.md (read-only)."""
from __future__ import annotations

import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(ROOT, "results")

with open(os.path.join(R, "task_a_rainfall_threshold.json"), encoding="utf-8") as fh:
    a = json.load(fh)
with open(os.path.join(R, "task_b_susceptibility.json"), encoding="utf-8") as fh:
    b = json.load(fh)

ta = pd.read_csv(os.path.join(ROOT, "data", "processed", "task_a_rainstorms.csv"))
catch = pd.read_csv(os.path.join(ROOT, "data", "processed", "catchment_features.csv"))
ev = pd.read_csv(os.path.join(ROOT, "data", "interim", "events.csv"))
ri = pd.read_csv(os.path.join(ROOT, "data", "interim", "rain_index.csv"))

L: list[str] = []


def w(s: str = "") -> None:
    L.append(s)


w("## 规模")
w(f"events={len(ev)} dfid={ev['DF_ID'].nunique()} with_CID={int(ev['C_ID'].notna().sum())} "
  f"time_missing={int(ev['time_missing'].sum())}")
w(f"rain_files={len(ri)} folders={ri['DF_ID'].nunique()} named={int(ri['has_name'].sum())} "
  f"gauges={ri['RG_ID'].nunique()}")
w(f"catchments={len(catch)} with_dam={int(catch['has_dam'].sum())} dams={int(catch['dam_number'].sum())} "
  f"no_dam={int((catch['dam_number'] == 0).sum())} zero_event={int((catch['n_events'] == 0).sum())}")
w(f"area_sum={catch['area_km2'].sum():.1f} med={catch['area_km2'].median():.2f} "
  f"max={catch['area_km2'].max():.2f}")
w(f"area_err_max={catch['area_check_rel_err'].max():.2e} "
  f"over1pct={int((catch['area_check_rel_err'] > 0.01).sum())}")
w(f"corr_area_events={catch[['area_km2', 'n_events']].corr().iloc[0, 1]:.4f} "
  f"corr_area_dam={catch[['area_km2', 'has_dam']].corr().iloc[0, 1]:.4f}")
w(f"events_by_year=" + ", ".join(f"{int(y)}:{n}" for y, n in
                                  sorted(ev['event_year'].value_counts().to_dict().items())))
w(f"rain_folders_missing_in_events={len(set(ri['DF_ID']) - set(ev['DF_ID']))}")

w()
w("## Task A 样本")
w(f"rows={a['n_rows']} pos={a['n_positive']} neg={a['n_negative']} "
  f"rate={a['positive_rate']:.4f} events={a['n_events']} gauges={a['n_gauges']}")
w(f"csv rows={len(ta)} pos={int((ta['label'] == 1).sum())} "
  f"events_with_label={ta.loc[ta['label'] == 1, 'DF_ID'].nunique()} "
  f"years={int(ta['event_year'].min())}-{int(ta['event_year'].max())}")
w(f"id_pairs={a['id_pairs']}")
w(f"temporal={a['temporal_split']}")

trig, nont = ta[ta['label'] == 1], ta[ta['label'] == 0]
w()
w("## Task A 分布（触发 vs 非触发，中位数 / 均值）")
for col in ("total_mm", "duration_h", "n_wet_hours", "max_1h", "max_24h", "max_72h",
            "mean_intensity", "antecedent_24h", "antecedent_72h", "api"):
    w(f"{col}: trig_med={trig[col].median():.2f} trig_mean={trig[col].mean():.2f} "
      f"nont_med={nont[col].median():.2f} nont_mean={nont[col].mean():.2f}")
w(f"trigger_overlap_zero={int((trig['trigger_overlap_h'] == 0).sum())}/{len(trig)}")

w()
w("## Task A 三协议（metrics_summary.csv）")
m = pd.read_csv(os.path.join(R, "metrics_summary.csv"))
for proto in ("random", "group_event", "temporal"):
    for _, r in m[(m['task'] == 'A') & (m['protocol'] == proto)].iterrows():
        w(f"{proto:12s} {r['model']:20s} acc={r['accuracy']:.4f} prec={r['precision']:.4f} "
          f"rec={r['recall']:.4f} f1={r['f1']:.4f} auc={r['roc_auc']:.4f} cm={r['confusion_matrix']}")

w()
w("## I-D 阈值")
for r in a['id_thresholds']:
    w(f"{r['name']:24s} {r['equation']:26s} r2={r['r2']:.4f} acc={r['accuracy']:.4f} "
      f"prec={r['precision']:.4f} rec={r['recall']:.4f} f1={r['f1']:.4f} "
      f"tp={r['tp']} fp={r['fp']} fn={r['fn']} tn={r['tn']}")
w(f"ml_equivalent={a['ml_equivalent_threshold']}")

w()
w("## Task A 特征重要性")
for r in a['feature_importance_random_forest']:
    w(f"RF {r['feature']:18s} {r['importance']:.4f}")
for r in a['feature_importance_logistic']:
    w(f"LR {r['feature']:18s} {r['importance']:+.4f}")

w()
w("## Task A 逐年触发")
for r in a['per_year_triggering']:
    w(f"{int(r['event_year'])} rows={r['n_trigger_rows']} events={r['n_events']} "
      f"dur={r['mean_duration_h']:.1f} tot={r['mean_total_mm']:.1f} "
      f"max1h={r['mean_max1h']:.1f} int={r['mean_intensity']:.2f}")

w()
w("## Task B")
w(f"rows={b['n_rows']} pos={b['n_positive']} neg={b['n_negative']} "
  f"median={b['median_n_events']} rule={b['label_rule']}")
w(f"excluded={b['excluded_features']['event_derived']}")
for name, mm in b['models'].items():
    w(f"{name:20s} acc={mm['accuracy_mean']:.4f}+-{mm['accuracy_std']:.4f} "
      f"prec={mm['precision_mean']:.4f} rec={mm['recall_mean']:.4f} "
      f"f1={mm['f1_mean']:.4f}+-{mm['f1_std']:.4f} auc={mm['roc_auc_mean']:.4f}")
for name in ("random_forest", "logistic_regression"):
    oof = b['models'][name].get('oof')
    if oof:
        w(f"OOF {name}: acc={oof['accuracy']:.4f} prec={oof['precision']:.4f} "
          f"rec={oof['recall']:.4f} f1={oof['f1']:.4f} cm={oof['confusion_matrix']}")
for r in b['feature_importance_random_forest']:
    w(f"B-RF {r['feature']:18s} {r['importance']:.4f}")
for r in b['feature_importance_logistic_regression']:
    w(f"B-LR {r['feature']:18s} {r['importance']:+.4f}")

w()
w("## Task B 交叉表")
buckets: dict[str, list[dict]] = {}
for row in b['catchments']:
    d = int(row['dam_number'])
    key = '0' if d == 0 else ('1' if d == 1 else ('2' if d == 2 else '>=3'))
    buckets.setdefault(key, []).append(row)
for key in ('0', '1', '2', '>=3'):
    rows = buckets.get(key, [])
    if rows:
        n_ev = sum(r['n_events'] for r in rows)
        hi = sum(int(r['susceptible']) for r in rows)
        w(f"dams={key}: catch={len(rows)} events={n_ev} mean={n_ev / len(rows):.2f} "
          f"high={hi}/{len(rows)}")

sub = catch.copy()
sub['yb'] = sub['built_year'].fillna(0).astype(int)
g = sub.groupby('yb').agg(n=('C_ID', 'size'), ev=('n_events', 'sum'))
for y, r in g.iterrows():
    w(f"built={int(y)}: catch={int(r['n'])} events={int(r['ev'])} mean={r['ev'] / r['n']:.2f}")

g2 = catch.groupby(catch['prevented'].astype(bool)).agg(n=('C_ID', 'size'), ev=('n_events', 'sum'))
for k, r in g2.iterrows():
    w(f"prevented={bool(k)}: catch={int(r['n'])} events={int(r['ev'])} mean={r['ev'] / r['n']:.2f}")

out = os.path.join(ROOT, "docs", "_numbers.md")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("wrote", out, len(L), "lines")