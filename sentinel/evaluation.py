"""Chronological holdout evaluation and detector ablations."""

import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from sentinel.model import Detector, ModelConfig, data_fingerprint
from sentinel.schema import DataValidationError, normalize_events


def temporal_split(frame):
    """60/20/20 by elapsed time, never divide equal timestamps across splits."""
    df, _ = normalize_events(frame)
    df = df.sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    start, end = df.event_time.min(), df.event_time.max()
    duration = end - start
    a, b = start + duration * 0.6, start + duration * 0.8
    train = df[df.event_time < a].copy()
    cal = df[(df.event_time >= a) & (df.event_time < b)].copy()
    test = df[df.event_time >= b].copy()
    if len(train) < 100 or len(cal) < 50 or len(test) < 50:
        raise DataValidationError(
            "The time split needs at least 100 train, 50 calibration and 50 test events."
        )
    return tuple(x.reset_index(drop=True) for x in (train, cal, test))


def classification_metrics(y, predictions, scores):
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    both_classes = len(np.unique(y)) == 2
    return {
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
        "average_precision": float(average_precision_score(y, scores)) if both_classes else None,
        "roc_auc": float(roc_auc_score(y, scores)) if both_classes else None,
        "true_positive": int(tp),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "false_negative": int(fn),
        "alerts": int(np.sum(predictions)),
    }


def evaluate(frame, config=None):
    train, cal, test = temporal_split(frame)
    if "label" not in test:
        raise DataValidationError("Evaluation requires a binary label column (0=benign, 1=scenario anomaly).")
    labels = pd.to_numeric(test.label, errors="coerce")
    if labels.isna().any() or not labels.isin([0, 1]).all():
        raise DataValidationError("Every evaluation label must be 0 or 1.")
    test["label"] = labels.astype(int)
    start = perf_counter()
    detector = Detector(config).fit(train, cal)
    training_seconds = perf_counter() - start
    start = perf_counter()
    results, diagnostics = detector.score(test)
    inference_seconds = perf_counter() - start
    variants = {
        "Isolation Forest": (results.iso_flag, results.iso_score),
        "PCA reconstruction": (results.pca_flag, results.pca_error),
        "Rules only": (results.rule_flag, results.rule_score),
        "Hybrid union": (results.is_suspicious, results.priority_score),
    }
    metrics = {
        name: classification_metrics(labels, predictions, scores)
        for name, (predictions, scores) in variants.items()
    }
    scenarios = []
    if "scenario" in results:
        for scenario, part in results.groupby("scenario"):
            positives = part[part.label == 1]
            negatives = part[part.label == 0]
            scenarios.append(
                {
                    "scenario": scenario,
                    "events": len(part),
                    "alerts": int(part.is_suspicious.sum()),
                    "recall": float(positives.is_suspicious.mean()) if len(positives) else None,
                    "false_positive_rate": float(negatives.is_suspicious.mean()) if len(negatives) else None,
                }
            )
    report = {
        "dataset": "synthetic"
        if "is_synthetic" in frame and frame.is_synthetic.astype(str).str.lower().eq("true").all()
        else "user-provided",
        "evaluation_unit": "event (not independent attack incident)",
        "split_method": "60/20/20 of elapsed time; train-only feature fitting; fixed calibration quantiles",
        "test_rows": len(test),
        "test_positive_rows": int(labels.sum()),
        "test_start": test.event_time.min().isoformat(),
        "test_end": test.event_time.max().isoformat(),
        "test_sha256": data_fingerprint(test),
        "model": detector.metadata,
        "metrics": metrics,
        "scenarios": scenarios,
        "diagnostics": diagnostics,
        "timing": {
            "training_seconds": round(training_seconds, 4),
            "scoring_seconds": round(inference_seconds, 4),
        },
        "limitations": [
            "Synthetic scenarios are designed alongside the rules; results are an engineering check, not external validity.",
            "Correlated events in one scenario are not independent samples; event recall is not incident recall.",
            "The per-model calibration alert target is not a guaranteed test false-positive rate or hybrid alert rate.",
            "Hybrid average precision uses the discrete review-priority score, not a probability.",
            "Low-and-slow access is intentionally difficult to distinguish from normal access with these fields.",
        ],
    }
    return report, detector, results


def write_report(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    table = pd.DataFrame(report["metrics"]).T
    table.to_csv(directory / "metrics.csv", index_label="detector")
    lines = [
        "# SentinelML evaluation",
        "",
        f"Dataset: **{report['dataset']}**. Unit: **{report['evaluation_unit']}**.",
        "",
        f"Train / calibration / test: {report['model']['train_rows']:,} / {report['model']['calibration_rows']:,} / {report['test_rows']:,} events.",
        "",
        "| Detector | Precision | Recall | F1 | False-positive rate | Average precision |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, m in report["metrics"].items():
        cells = [
            f"{m[k]:.3f}" if m[k] is not None else "N/A"
            for k in ("precision", "recall", "f1", "false_positive_rate", "average_precision")
        ]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.extend(["", "## Interpretation limits", ""] + ["- " + x for x in report["limitations"]])
    (directory / "evaluation.md").write_text("\n".join(lines) + "\n")


def seed_study(seeds=(11, 42, 73), config=None):
    from sentinel.demo import generate_demo

    runs, rows = [], []
    for seed in seeds:
        base = config or ModelConfig()
        cfg = ModelConfig(
            seed=seed,
            trees=base.trees,
            target_alert_rate=base.target_alert_rate,
            pca_variance=base.pca_variance,
        )
        report, _, _ = evaluate(generate_demo(seed=seed), cfg)
        runs.append(report)
        for detector, metrics in report["metrics"].items():
            rows.append({"seed": seed, "detector": detector, **metrics})
    return runs, pd.DataFrame(rows)
