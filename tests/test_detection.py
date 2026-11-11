import numpy as np
import pandas as pd
import pytest

from sentinel.evaluation import classification_metrics, evaluate, temporal_split
from sentinel.features import Baseline, build_features, context_features
from sentinel.model import Detector, ModelConfig
from sentinel.rules import evaluate_rules
from sentinel.schema import DataValidationError, normalize_events


def test_temporal_split_has_strict_order(splits):
    train, cal, test = splits
    assert train.event_time.max() < cal.event_time.min()
    assert cal.event_time.max() < test.event_time.min()
    assert set(train.event_id).isdisjoint(test.event_id)


def test_equal_timestamps_stay_together(dataset):
    duplicate_times = dataset.copy()
    duplicate_times.event_time = duplicate_times.event_time.dt.floor("h")
    train, cal, test = temporal_split(duplicate_times)
    assert set(train.event_time).isdisjoint(cal.event_time)
    assert set(cal.event_time).isdisjoint(test.event_time)


def test_overlapping_calibration_rejected(splits):
    with pytest.raises(DataValidationError, match="strictly after"):
        Detector().fit(splits[0], splits[0].tail(100))


def test_labels_and_scenarios_cannot_enter_features(splits):
    train = splits[0]
    baseline = Baseline.fit(train)
    x, _ = build_features(train, baseline)
    modified = train.assign(label=1, scenario="attack", arbitrary_target=99)
    other, _ = build_features(modified, baseline)
    pd.testing.assert_frame_equal(x, other)
    assert x.shape[1] == 18


def test_unseen_categories_are_supported(detector, splits):
    events = splits[2].head(2).copy()
    events["event_name"] = "BrandNewAction"
    events["principal_name"] = "new-person"
    scored, diag = detector.score(events)
    assert np.isfinite(scored.iso_score).all()
    assert diag["new_principal_rate"] == 1


def test_future_events_do_not_change_existing_scores(detector, splits):
    early = splits[2].head(80)
    prefix, _ = detector.score(early)
    whole, _ = detector.score(splits[2])
    whole = whole.set_index("event_id").loc[prefix.event_id]
    for col in ["iso_score", "pca_error", "iso_flag", "pca_flag", "priority_score"]:
        np.testing.assert_allclose(prefix[col], whole[col])


def test_scores_keep_types_and_all_flagged_events(detector, splits):
    scored, _ = detector.score(splits[2])
    assert scored.is_suspicious.dtype == bool
    assert pd.api.types.is_numeric_dtype(scored.iso_score)
    assert len(scored) == len(splits[2])
    assert scored.is_suspicious.equals(scored.iso_flag | scored.pca_flag | scored.rule_flag)


def test_scoring_preserves_original_input(detector, splits):
    frame = splits[2].copy(deep=True)
    original = frame.copy(deep=True)
    detector.score(frame)
    pd.testing.assert_frame_equal(frame, original)


def test_model_round_trip_preserves_scores(detector, splits, tmp_path):
    path = tmp_path / "own_model.joblib"
    detector.save(path)
    loaded = Detector.load(path)
    a, _ = detector.score(splits[2])
    b, _ = loaded.score(splits[2])
    pd.testing.assert_frame_equal(a, b)
    assert path.with_suffix(".json").exists()


def test_fitting_is_reproducible(splits):
    cfg = ModelConfig(seed=7, trees=20)
    a, b = Detector(cfg).fit(*splits[:2]), Detector(cfg).fit(*splits[:2])
    assert a.model_id == b.model_id
    assert a.iso_threshold == b.iso_threshold


def test_fixed_thresholds_do_not_adapt_to_upload(detector, splits):
    before = (detector.iso_threshold, detector.pca_threshold)
    detector.score(splits[2].head(1))
    assert before == (detector.iso_threshold, detector.pca_threshold)


def test_burst_rules_use_historical_event_time():
    raw = pd.DataFrame(
        {
            "event_time": pd.date_range("2020-01-01", periods=6, freq="min", tz="UTC"),
            "event_name": "AuthenticateUser",
            "principal_name": "test",
            "response_status": 401,
        }
    )
    df, _ = normalize_events(raw)
    features, ctx = build_features(df, Baseline.fit(df))
    rules = evaluate_rules(df, features, ctx)
    assert rules.rule_ids.iloc[3] == ""
    assert "R1" in rules.rule_ids.iloc[4]


def test_anonymous_users_do_not_form_shared_burst():
    raw = pd.DataFrame(
        {
            "event_time": pd.date_range("2020-01-01", periods=8, freq="s", tz="UTC"),
            "event_name": "AuthenticateUser",
            "principal_name": None,
            "response_status": 401,
        }
    )
    df, _ = normalize_events(raw)
    features, ctx = build_features(df, Baseline.fit(df))
    rules = evaluate_rules(df, features, ctx)
    assert not rules.rule_score.any()
    assert ctx.events_10m.max() == 1


def test_rolling_window_excludes_old_events():
    df, _ = normalize_events(
        pd.DataFrame(
            {
                "event_time": ["2026-01-01T00:00Z", "2026-01-01T00:11Z"],
                "principal_name": "one",
                "event_name": "GetVcn",
            }
        )
    )
    assert context_features(df).events_10m.tolist() == [1, 1]


def test_single_class_metrics_are_explicit():
    metrics = classification_metrics(np.array([0, 0]), np.array([0, 1]), np.array([0.1, 0.8]))
    assert metrics["roc_auc"] is None
    assert metrics["average_precision"] is None
    assert metrics["false_positive_rate"] == 0.5


def test_evaluation_includes_ablations_and_hard_case(dataset):
    report, _, _ = evaluate(dataset, ModelConfig(trees=20))
    assert len(report["metrics"]) == 4
    assert report["dataset"] == "synthetic"
    assert "low_and_slow_access" in {x["scenario"] for x in report["scenarios"]}
    assert report["model"]["train_end"] < report["test_start"]


def test_string_labels_have_correct_scenario_metrics(dataset):
    report, _, _ = evaluate(dataset.assign(label=dataset.label.astype(str)), ModelConfig(trees=20))
    credential = next(x for x in report["scenarios"] if x["scenario"] == "credential_abuse")
    assert credential["recall"] is not None
