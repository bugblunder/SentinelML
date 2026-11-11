"""Train-only baselines and held-out, fixed anomaly thresholds."""

import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from sentinel.features import Baseline, build_features
from sentinel.rules import RULES, evaluate_rules
from sentinel.schema import DataValidationError, normalize_events


@dataclass(frozen=True)
class ModelConfig:
    seed: int = 42
    trees: int = 200
    target_alert_rate: float = 0.03
    pca_variance: float = 0.90

    def __post_init__(self):
        if not 0 < self.target_alert_rate < 0.5:
            raise ValueError("target_alert_rate must be between 0 and 0.5.")
        if not 0 < self.pca_variance < 1 or self.trees < 10:
            raise ValueError("Use 0 < pca_variance < 1 and at least 10 trees.")


def data_fingerprint(df):
    columns = [
        "event_time",
        "event_name",
        "principal_name",
        "ip_address",
        "source_service",
        "auth_type",
        "resource_name",
        "opc_client_info",
        "compartment_name",
        "response_status",
        "event_id",
    ]
    canonical = df[columns].astype(str).sort_values(["event_time", "event_id"]).to_csv(index=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def percentile(reference, scores):
    # A rank in the fixed calibration distribution, not a probability of attack.
    return np.searchsorted(reference, scores, side="right") / len(reference)


class Detector:
    def __init__(self, config=None):
        self.config = config or ModelConfig()

    def fit(self, training, calibration):
        train, _ = normalize_events(training)
        cal, _ = normalize_events(calibration)
        if len(train) < 100 or len(cal) < 50:
            raise DataValidationError("Training needs at least 100 events and calibration at least 50.")
        if train.event_time.max() >= cal.event_time.min():
            raise DataValidationError(
                "Calibration must occur strictly after training, with no overlapping timestamps."
            )
        self.baseline = Baseline.fit(train)
        x, _ = build_features(train, self.baseline)
        self.feature_names = list(x.columns)
        self.scaler = StandardScaler().fit(x)
        scaled = self.scaler.transform(x)
        if np.var(scaled, axis=0).sum() == 0:
            raise DataValidationError("Training data has no feature variation.")
        self.iso = IsolationForest(
            n_estimators=self.config.trees, random_state=self.config.seed, n_jobs=1
        ).fit(scaled)
        self.pca = PCA(n_components=self.config.pca_variance, svd_solver="full").fit(scaled)
        cx, _ = build_features(cal, self.baseline)
        iso, pca = self._raw_scores(cx)
        self.iso_reference = np.sort(iso)
        self.pca_reference = np.sort(pca)
        quantile = 1 - self.config.target_alert_rate
        self.iso_threshold = float(np.quantile(iso, quantile, method="higher"))
        self.pca_threshold = float(np.quantile(pca, quantile, method="higher"))
        self.metadata = {
            "format_version": 2,
            "config": asdict(self.config),
            "train_rows": len(train),
            "calibration_rows": len(cal),
            "train_start": train.event_time.min().isoformat(),
            "train_end": train.event_time.max().isoformat(),
            "calibration_start": cal.event_time.min().isoformat(),
            "calibration_end": cal.event_time.max().isoformat(),
            "train_sha256": data_fingerprint(train),
            "calibration_sha256": data_fingerprint(cal),
            "feature_count": len(self.feature_names),
            "pca_components": int(self.pca.n_components_),
            "iso_threshold": self.iso_threshold,
            "pca_threshold": self.pca_threshold,
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "calibration_iso_alert_rate": float(np.mean(iso > self.iso_threshold)),
            "calibration_pca_alert_rate": float(np.mean(pca > self.pca_threshold)),
        }
        self.model_id = hashlib.sha256(json.dumps(self.metadata, sort_keys=True).encode()).hexdigest()[:12]
        self.metadata["model_id"] = self.model_id
        return self

    def _raw_scores(self, features):
        x = self.scaler.transform(features[self.feature_names])
        reconstructed = self.pca.inverse_transform(self.pca.transform(x))
        return -self.iso.score_samples(x), np.mean((x - reconstructed) ** 2, axis=1)

    def score(self, frame):
        if not hasattr(self, "metadata"):
            raise ValueError("Fit or load a detector before scoring.")
        df, quality = normalize_events(frame)
        features, context = build_features(df, self.baseline)
        iso, pca = self._raw_scores(features)
        rules = evaluate_rules(df, features, context)
        out = df.copy()
        out["iso_score"], out["pca_error"] = iso, pca
        out["iso_flag"] = iso > self.iso_threshold
        out["pca_flag"] = pca > self.pca_threshold
        out["iso_percentile"] = percentile(self.iso_reference, iso)
        out["pca_percentile"] = percentile(self.pca_reference, pca)
        out["rule_ids"], out["rule_score"] = rules.rule_ids, rules.rule_score
        out["rule_flag"] = rules.rule_score.gt(0)
        out["is_suspicious"] = out.iso_flag | out.pca_flag | out.rule_flag
        out["signals"] = out[["iso_flag", "pca_flag", "rule_flag"]].sum(axis=1)
        # Triage priority: deliberately separate from raw scores and attack probability.
        out["priority_score"] = np.maximum(
            rules.rule_score, np.where(out.iso_flag | out.pca_flag, 40.0, 0.0)
        ) + 10 * (out.signals - 1).clip(lower=0)
        out["priority_score"] = out.priority_score.clip(upper=100).astype(int)
        out["severity"] = np.select(
            [out.priority_score.ge(80), out.priority_score.ge(60), out.is_suspicious],
            ["Critical", "High", "Medium"],
            default="Normal",
        )
        out["model_id"] = self.model_id
        reasons, next_steps = [], []
        for i in range(len(out)):
            row = out.iloc[i]
            parts = []
            if row.iso_flag:
                parts.append(
                    f"Isolation Forest exceeds fixed threshold ({row.iso_score:.3f} > {self.iso_threshold:.3f})"
                )
            if row.pca_flag:
                parts.append(
                    f"PCA reconstruction error exceeds fixed threshold ({row.pca_error:.3f} > {self.pca_threshold:.3f})"
                )
            ids = row.rule_ids.split(", ") if row.rule_ids else []
            parts.extend(f"{r}: {RULES[r][0]}" for r in ids)
            if row.is_suspicious:
                if features.loc[i, "new_ip"]:
                    parts.append("Source IP was not seen for this principal in training")
                if features.loc[i, "new_client"]:
                    parts.append("Client was not seen for this principal in training")
                parts.append(
                    f"Prior/current 10-minute activity: {int(context.loc[i, 'events_10m'])} events, {int(context.loc[i, 'failures_10m'])} auth failures"
                )
            reasons.append("; ".join(parts) or "No configured detector threshold or rule fired.")
            next_steps.append(
                " ".join(dict.fromkeys(RULES[r][2] for r in ids))
                or (
                    "Compare with approved work and surrounding audit events; unusual does not establish malicious intent."
                    if row.is_suspicious
                    else "No immediate review requested by this configuration."
                )
            )
        out["evidence"], out["recommended_review"] = reasons, next_steps
        diagnostics = {
            "quality": asdict(quality),
            "model_id": self.model_id,
            "new_principal_rate": float(features.new_principal.mean()),
            "new_ip_rate": float(features.new_ip.mean()),
            "alert_rate": float(out.is_suspicious.mean()),
            "temporal_overlap": bool(df.event_time.min() <= pd.Timestamp(self.metadata["calibration_end"])),
        }
        return out, diagnostics

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        joblib.dump(self, temporary)
        temporary.replace(path)
        path.with_suffix(".json").write_text(json.dumps(self.metadata, indent=2) + "\n")

    @classmethod
    def load(cls, path):
        """Only load artifacts you trained yourself; joblib is executable serialization."""
        result = joblib.load(path)
        if not isinstance(result, cls) or result.metadata.get("format_version") != 2:
            raise ValueError("Unsupported model artifact; retrain with this version.")
        if result.metadata["sklearn"] != sklearn.__version__:
            raise ValueError(
                "scikit-learn version differs from the saved model; retrain in this environment."
            )
        return result
