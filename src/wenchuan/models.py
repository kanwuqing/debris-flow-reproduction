"""Traditional ML models for the two classification tasks.

Everything is deterministic: every estimator is built inside a
``Pipeline``/``make_pipeline`` with an explicit ``random_state``, and the splits
are fixed by ``SPLIT_SEED``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

SPLIT_SEED = 20220901  # fixed for reproducibility


def _xgboost():
    """XGBoost if it is installed, else ``None`` (kept optional on purpose)."""
    try:
        from xgboost import XGBClassifier
    except ImportError:  # pragma: no cover - depends on the environment
        return None
    return XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=SPLIT_SEED,
        n_jobs=1,
        eval_metric="logloss",
    )


def make_models(n_features: int) -> dict[str, Pipeline]:
    """The classifiers compared on both tasks (XGBoost only when installed)."""
    models = {
        "logistic_regression": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=5000, random_state=SPLIT_SEED,
                                       class_weight="balanced")),
        ]),
        "random_forest": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(
                n_estimators=500, max_depth=None, min_samples_leaf=2,
                random_state=SPLIT_SEED, n_jobs=1, class_weight="balanced_subsample",
            )),
        ]),
        "svm_rbf": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", SVC(kernel="rbf", C=1.0, gamma="scale",
                        random_state=SPLIT_SEED, class_weight="balanced")),
        ]),
        "gradient_boosting": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", GradientBoostingClassifier(random_state=SPLIT_SEED)),
        ]),
    }
    xgb = _xgboost()
    if xgb is not None:
        models["xgboost"] = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", xgb),
        ])
    return models


def score_predictions(y_true, y_pred, y_score=None) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    out = dict(
        accuracy=float(accuracy_score(y_true, y_pred)),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        confusion_matrix=cm.tolist(),
        n=int(len(y_true)),
        n_positive=int(np.sum(np.asarray(y_true) == 1)),
    )
    if y_score is not None and len(np.unique(y_true)) == 2:
        try:
            out["roc_auc"] = float(roc_auc_score(y_true, y_score))
        except ValueError:
            out["roc_auc"] = float("nan")
    return out


def decision_scores(pipe: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """A continuous score for ROC-AUC, whatever the estimator exposes."""
    if hasattr(pipe, "predict_proba"):
        return pipe.predict_proba(X)[:, 1]
    if hasattr(pipe, "decision_function"):
        return pipe.decision_function(X)
    return pipe.predict(X).astype(float)


def feature_importance(pipe: Pipeline, feature_names: list[str]) -> pd.DataFrame | None:
    """Coefficient / impurity importance of the fitted final estimator."""
    clf = pipe.named_steps.get("clf")
    if clf is None:
        return None
    if hasattr(clf, "feature_importances_"):
        values = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        values = np.ravel(clf.coef_)
    else:
        return None
    return (
        pd.DataFrame({"feature": feature_names, "importance": values})
        .assign(abs_importance=lambda d: d["importance"].abs())
        .sort_values("abs_importance", ascending=False)
        .reset_index(drop=True)
    )


def leave_one_group_out_scores(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series, model_name: str, models: dict
) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-fold predictions with one group (year / catchment) held out."""
    y_pred = np.zeros(len(y), dtype=int)
    y_score = np.zeros(len(y), dtype=float)
    for g in sorted(pd.unique(groups.dropna())):
        test = (groups == g).to_numpy()
        train = ~test
        if test.sum() == 0 or train.sum() == 0:
            continue
        if len(np.unique(y[train])) < 2:
            y_pred[test] = int(y[train].iloc[0]) if hasattr(y[train], "iloc") else int(y[train][0])
            y_score[test] = float(y_pred[test][0])
            continue
        pipe = models[model_name]
        pipe.fit(X[train], y[train])
        y_pred[test] = pipe.predict(X[test])
        y_score[test] = decision_scores(pipe, X[test])
    return y_pred, y_score