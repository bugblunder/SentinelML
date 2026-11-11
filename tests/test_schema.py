import pandas as pd
import pytest

from sentinel.schema import DataValidationError, normalize_events, read_events


def one_event(**changes):
    row = {"event_time": "2026-01-01T10:00:00Z", "event_name": "GetObject", "principal_name": "demo"}
    return pd.DataFrame([{**row, **changes}])


def test_minimal_schema_is_usable():
    df, quality = normalize_events(one_event())
    assert str(df.event_time.dt.tz) == "UTC"
    assert df.response_status.iloc[0] == 0
    assert "ip_address" in quality.missing_optional


@pytest.mark.parametrize("column", ["event_time", "event_name", "principal_name"])
def test_required_columns(column):
    with pytest.raises(DataValidationError, match="Missing required"):
        normalize_events(one_event().drop(columns=column))


@pytest.mark.parametrize("value", ["not-a-date", "", None])
def test_bad_timestamps_are_rejected(value):
    with pytest.raises(DataValidationError, match="event_time"):
        normalize_events(one_event(event_time=value))


@pytest.mark.parametrize("status", ["oops", 200.5, 999, -1])
def test_invalid_status_is_not_silently_benign(status):
    with pytest.raises(DataValidationError, match="response_status"):
        normalize_events(one_event(response_status=status))


def test_duplicate_headers_are_rejected():
    with pytest.raises(DataValidationError, match="duplicate column"):
        read_events(b"event_time,event_name,principal_name,event_name\na,b,c,d\n")


def test_duplicate_payloads_are_reported_and_have_unique_ids():
    df, quality = normalize_events(pd.concat([one_event(), one_event()], ignore_index=True))
    assert quality.duplicate_events == 1
    assert df.event_id.is_unique
    assert len(df) == 2


def test_duplicate_supplied_ids_rejected():
    df = pd.concat([one_event(event_id="same"), one_event(event_id="same")])
    with pytest.raises(DataValidationError, match="event_id must be unique"):
        normalize_events(df)


def test_unknown_principal_is_explicit():
    df, quality = normalize_events(one_event(principal_name=None))
    assert df.principal_name.iloc[0] == "unknown"
    assert quality.unknown_principals == 1


def test_empty_csv_is_actionable():
    with pytest.raises(DataValidationError):
        read_events(b"")


def test_input_frame_is_not_mutated():
    frame = one_event()
    original = frame.copy(deep=True)
    normalize_events(frame)
    pd.testing.assert_frame_equal(frame, original)
