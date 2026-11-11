import pandas as pd
from streamlit.testing.v1 import AppTest

from sentinel.export import csv_bytes, html_report
from sentinel.feedback import load_feedback, save_feedback


def test_export_escapes_formulas():
    data = pd.DataFrame({"principal": ["=HYPERLINK(1)", "  +1", "normal"]})
    content = csv_bytes(data).decode("utf-8-sig")
    assert "'=HYPERLINK" in content
    assert "'  +1" in content


def test_export_escapes_formula_headers():
    content = csv_bytes(pd.DataFrame({"=1+1": ["text"]})).decode("utf-8-sig")
    assert content.startswith("'=1+1")


def test_report_escapes_untrusted_html(detector, splits):
    results, diagnostics = detector.score(splits[2])
    results.loc[results.is_suspicious, "principal_name"] = "<script>alert(1)</script>"
    output = html_report(results, diagnostics).decode()
    assert "<script>" not in output
    assert "&lt;script&gt;" in output
    assert str(len(results)) in output.replace(",", "")


def test_feedback_upsert_and_model_isolation(tmp_path):
    path = tmp_path / "feedback.sqlite"
    save_feedback(path, "event-1", "model-a", "Needs investigation", "Review")
    save_feedback(path, "event-1", "model-a", "Expected activity", "Approved")
    save_feedback(path, "event-1", "model-b", "Confirmed issue", "Different model")
    frame = load_feedback(path, "model-a")
    assert len(frame) == 1
    assert frame.verdict.iloc[0] == "Expected activity"
    assert len(load_feedback(path, "model-b")) == 1


def test_dashboard_demo_and_filter():
    app = AppTest.from_file("app.py", default_timeout=60).run()
    assert not app.exception
    assert len(app.tabs) == 4
    assert int(app.metric[0].value.replace(",", "")) > 100
    assert int(app.metric[1].value.replace(",", "")) > 100  # Original dashboard incorrectly capped at 100.
    app.text_input[0].set_value("no-such-principal").run()
    assert not app.exception
    assert any("No flagged events match" in item.value for item in app.info)
    app.sidebar.radio[0].set_value("Your audit logs").run()
    assert not app.exception
    assert any("Load a historical baseline" in item.value for item in app.info)
