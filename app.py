"""SentinelML portfolio dashboard. Run: python -m streamlit run app.py."""

import hashlib
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sentinel.demo import generate_demo
from sentinel.evaluation import evaluate, temporal_split
from sentinel.export import csv_bytes, html_report, json_bytes
from sentinel.feedback import VERDICTS, load_feedback, save_feedback
from sentinel.model import Detector
from sentinel.schema import DataValidationError, read_events

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="SentinelML | Audit intelligence", page_icon="◈", layout="wide")
st.markdown(
    """
<style>
.stApp {background:#f6f8fb;color:#172c40}
.block-container {max-width:1440px;padding-top:2.3rem;padding-bottom:3rem}
[data-testid="stSidebar"] {background:#12283b}
[data-testid="stSidebar"] * {color:#e8eff5}
[data-testid="stSidebar"] [data-testid="stFileUploader"] * {color:#172c40}
[data-testid="stSidebar"] button * {color:#172c40}
h1,h2,h3 {letter-spacing:-.035em}
h1 {font-size:2.55rem!important;font-weight:740!important}
h3 {font-size:1.2rem!important}
[data-testid="stMetric"] {background:white;border:1px solid #e1e8ef;border-radius:12px;padding:18px 22px}
[data-testid="stMetricLabel"] {color:#607284;font-size:13px}
[data-testid="stMetricValue"] {color:#173449;font-size:2rem;font-weight:650}
.eyebrow {font-size:11px;letter-spacing:.16em;font-weight:750;color:#218478;margin-bottom:10px}
.subtitle {color:#607284;font-size:16px;line-height:1.65;max-width:790px;margin-bottom:26px}
.status {display:inline-block;border:1px solid #b6ded3;border-radius:30px;background:#eaf6f0;color:#197d68;padding:6px 12px;font-size:12px;font-weight:650;margin-bottom:22px}
.brand {font-size:25px;letter-spacing:-.04em;font-weight:750;margin:10px 0 0;color:white}
.brand-sub {font-size:11px;letter-spacing:.12em;color:#8fa7ba;margin:4px 0 32px}
.side-note {font-size:12px;line-height:1.8;color:#9db2c2;margin-top:32px}
.stTabs [data-baseweb="tab-list"] {gap:28px;border-bottom:1px solid #dce5ed}
.stTabs [data-baseweb="tab"] {padding-bottom:14px}
.stTabs [aria-selected="true"] {color:#087f72}
.stButton button[kind="primary"] {background:#087f72;border-color:#087f72}
@media(max-width:700px){.block-container{padding:1.4rem 1rem}h1{font-size:2rem!important}}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Preparing the reproducible demo…")
def demo_run():
    return evaluate(generate_demo())


def chart_style(fig, height=290):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=16, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color="#637789", size=12),
        legend=dict(orientation="h", y=1.14, x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#e3eaf0", zeroline=False),
    )
    return fig


def select_data():
    st.sidebar.markdown(
        '<div class="brand">◈ SentinelML</div><div class="brand-sub">AUDIT INTELLIGENCE / V2.0</div>',
        unsafe_allow_html=True,
    )
    source = st.sidebar.radio("Workspace", ["Synthetic demo", "Your audit logs"], key="source")
    if source == "Synthetic demo":
        st.sidebar.markdown("**A reproducible investigation**")
        st.sidebar.caption(
            "30 days of generated cloud activity. Historical training, separate calibration, and a later test period."
        )
        st.sidebar.download_button(
            "Download demo dataset",
            generate_demo().to_csv(index=False).encode(),
            "sentinel_demo.csv",
            "text/csv",
            width="stretch",
        )
        report, detector, results = demo_run()
        return detector, results, report["diagnostics"], report
    st.sidebar.caption(
        "Upload historical baseline events, then a separate later batch to investigate. Processing stays in this app process."
    )
    baseline_file = st.sidebar.file_uploader("1. Historical baseline CSV", type="csv", key="baseline_upload")
    if baseline_file is not None:
        fingerprint = hashlib.sha256(baseline_file.getvalue()).hexdigest()
        if fingerprint != st.session_state.get("baseline_fingerprint"):
            for key in ["custom_model", "custom_results", "custom_diagnostics"]:
                st.session_state.pop(key, None)
            st.session_state["baseline_fingerprint"] = fingerprint
        if st.sidebar.button("Train baseline", type="primary", width="stretch"):
            try:
                baseline, quality = read_events(baseline_file.getvalue())
                train, cal, _ = temporal_split(baseline)
                with st.spinner("Fitting historical patterns and calibration thresholds…"):
                    st.session_state.custom_model = Detector().fit(train, cal)
                for warning in quality.warnings:
                    st.sidebar.warning(warning)
                st.sidebar.success("Baseline ready. The last 20% of historical time is held out.")
            except (DataValidationError, ValueError) as exc:
                st.sidebar.error(str(exc))
    test_file = st.sidebar.file_uploader("2. Later events CSV", type="csv", key="test_upload")
    if test_file is not None:
        fingerprint = hashlib.sha256(test_file.getvalue()).hexdigest()
        if fingerprint != st.session_state.get("test_fingerprint"):
            st.session_state.pop("custom_results", None)
            st.session_state["test_fingerprint"] = fingerprint
    if st.sidebar.button(
        "Analyze events",
        disabled=("custom_model" not in st.session_state or test_file is None),
        width="stretch",
    ):
        try:
            events, quality = read_events(test_file.getvalue())
            with st.spinner("Analyzing events…"):
                result, diagnostics = st.session_state.custom_model.score(events)
            diagnostics["quality"] = quality.__dict__
            st.session_state.custom_results, st.session_state.custom_diagnostics = result, diagnostics
        except (DataValidationError, ValueError) as exc:
            st.sidebar.error(str(exc))
    if "custom_results" in st.session_state:
        return (
            st.session_state.custom_model,
            st.session_state.custom_results,
            st.session_state.custom_diagnostics,
            None,
        )
    return None


selected = select_data()
st.sidebar.markdown(
    '<div class="side-note">LOCAL PROCESSING<br>No API key required. No log data is sent to a language model.<br><br>Research prototype · Human review required</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="eyebrow">SECURITY ANALYTICS / RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
st.title("Make unusual activity explainable.")
st.markdown(
    '<div class="subtitle">Turn cloud audit events into a focused review queue. Combine statistical anomaly detection with explicit rules, and inspect the evidence behind every flag.</div>',
    unsafe_allow_html=True,
)
if selected is None:
    st.info(
        "Load a historical baseline and a later event batch in the sidebar, or explore the synthetic demo."
    )
    st.markdown(
        "**Required CSV columns:** `event_time`, `event_name`, `principal_name`. Optional fields add IP, client, service, status and compartment context."
    )
    st.stop()

detector, results, diagnostics, report = selected
demo_mode = report is not None
st.markdown(
    '<span class="status">'
    + ("SYNTHETIC DEMO · HELD-OUT EVENTS" if demo_mode else "LOCAL AUDIT REVIEW")
    + "</span>",
    unsafe_allow_html=True,
)
if diagnostics["temporal_overlap"]:
    st.warning(
        "This batch overlaps the model's training/calibration period. Its results are not an independent holdout evaluation."
    )
for warning in diagnostics["quality"]["warnings"]:
    st.warning(warning)
if diagnostics["new_principal_rate"] > 0.25:
    st.warning(
        "More than 25% of this batch contains principals absent from training. Review baseline coverage before interpreting alerts."
    )

flagged = results[results.is_suspicious].copy()
cols = st.columns(4)
cols[0].metric("Events analyzed", f"{len(results):,}")
cols[1].metric("Flagged for review", f"{len(flagged):,}")
cols[2].metric("High + critical", f"{results.severity.isin(['High', 'Critical']).sum():,}")
cols[3].metric("Flag rate", f"{diagnostics['alert_rate']:.1%}")
st.caption(
    f"All events in the current batch · {results.event_time.min():%d %b %Y} – {results.event_time.max():%d %b %Y} · UTC · Model {detector.model_id}"
)

overview, investigate, evaluation_tab, methodology = st.tabs(
    ["Activity overview", "Investigate", "Evaluation", "Model & method"]
)
with overview:
    left, right = st.columns([1.75, 1])
    with left:
        st.subheader("Activity over time")
        st.caption("Hourly volume and flagged events across the entire batch")
        counts = (
            results.set_index("event_time")
            .resample("h")
            .agg(events=("event_id", "size"), flagged=("is_suspicious", "sum"))
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=counts.index,
                y=counts.events,
                name="All events",
                fill="tozeroy",
                line=dict(color="#b3c8d5", width=1.5),
                fillcolor="rgba(173,198,215,.20)",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=counts.index, y=counts.flagged, name="Flagged", line=dict(color="#0b8b7a", width=2.5)
            )
        )
        st.plotly_chart(chart_style(fig), width="stretch", config={"displayModeBar": False})
    with right:
        st.subheader("Detection signals")
        st.caption("An event can trigger more than one signal")
        signals = {
            "Isolation Forest": int(results.iso_flag.sum()),
            "PCA reconstruction": int(results.pca_flag.sum()),
            "Explicit rules": int(results.rule_flag.sum()),
        }
        fig = go.Figure(
            go.Bar(
                x=list(signals.values()),
                y=list(signals),
                orientation="h",
                marker_color=["#173c52", "#558b9b", "#0b8b7a"],
                text=list(signals.values()),
                textposition="auto",
            )
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(chart_style(fig), width="stretch", config={"displayModeBar": False})
    st.subheader("Priority review queue")
    st.caption(
        "Highest review priority first · all flagged events remain available in Investigate and exports"
    )
    queue_cols = ["event_time", "principal_name", "event_name", "severity", "priority_score", "rule_ids"]
    st.dataframe(
        flagged.sort_values(["priority_score", "event_time"], ascending=[False, False])[queue_cols].head(8),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Review priority combines detector agreement and rule severity. It is not a probability that an attack occurred."
    )

with investigate:
    st.subheader("Follow the evidence")
    c1, c2 = st.columns([1, 2])
    severities = c1.multiselect(
        "Severity", ["Critical", "High", "Medium"], default=["Critical", "High", "Medium"]
    )
    query = c2.text_input("Filter by principal, action or IP", placeholder="e.g. analyst-06 or CreatePolicy")
    queue = flagged[flagged.severity.isin(severities)].copy()
    if query:
        mask = (
            queue[["principal_name", "event_name", "ip_address"]]
            .apply(lambda col: col.str.contains(query, case=False, regex=False))
            .any(axis=1)
        )
        queue = queue[mask]
    queue = queue.sort_values(["priority_score", "event_time"], ascending=[False, False])
    st.caption(f"{len(queue):,} matching events / {len(flagged):,} total flagged events")
    if queue.empty:
        st.info("No flagged events match these filters.")
    else:
        st.dataframe(queue[queue_cols + ["event_id"]], hide_index=True, width="stretch", height=280)
        labels = {
            r.event_id: f"{r.principal_name} · {r.event_name} · {r.event_time:%d %b %H:%M:%S} · {r.event_id}"
            for r in queue.itertuples()
        }
        selected_id = st.selectbox("Inspect event", options=list(labels), format_func=labels.get)
        event = queue.loc[queue.event_id.eq(selected_id)].iloc[0]
        detail, review = st.columns([1.65, 1])
        with detail:
            st.markdown("**Detection evidence**")
            for item in event.evidence.split("; "):
                st.write("• " + item)
            st.markdown("**Suggested review**")
            st.write(event.recommended_review)
            st.caption(
                "These statements describe detector outputs and observed context; they are not causal feature attributions."
            )
            st.dataframe(
                pd.DataFrame(
                    {
                        "Detector": ["Isolation Forest", "PCA reconstruction"],
                        "Raw score": [event.iso_score, event.pca_error],
                        "Fixed threshold": [detector.iso_threshold, detector.pca_threshold],
                        "Flagged": [bool(event.iso_flag), bool(event.pca_flag)],
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        with review:
            st.markdown("**Analyst review**")
            with st.form("review_form"):
                verdict = st.selectbox("Review status", VERDICTS)
                note = st.text_area(
                    "Notes", max_chars=2000, placeholder="Record supporting context or an approved change."
                )
                if st.form_submit_button("Save review", type="primary"):
                    try:
                        save_feedback(
                            ROOT / "artifacts/feedback.sqlite", selected_id, detector.model_id, verdict, note
                        )
                        st.success("Review saved locally.")
                    except (OSError, sqlite3.Error):
                        st.error("Cannot write feedback. Check local storage permissions.")
            st.caption("Feedback is stored locally. It does not automatically retrain the detector.")
        with st.expander("Saved reviews for this model"):
            feedback = load_feedback(ROOT / "artifacts/feedback.sqlite", detector.model_id)
            st.dataframe(feedback, hide_index=True, width="stretch")
            st.download_button("Export reviews", csv_bytes(feedback), "sentinel_reviews.csv", "text/csv")
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "Download all scored events", csv_bytes(results), "sentinel_events.csv", "text/csv", width="stretch"
    )
    c2.download_button(
        "Download review report",
        html_report(results, diagnostics),
        "sentinel_review.html",
        "text/html",
        width="stretch",
    )
    c3.download_button(
        "Download diagnostics",
        json_bytes(diagnostics),
        "sentinel_diagnostics.json",
        "application/json",
        width="stretch",
    )

with evaluation_tab:
    st.subheader("Measure the trade-offs")
    if report is None:
        st.info(
            "This batch has no automatic benchmark. To evaluate labeled historical data, run: python -m sentinel evaluate your_events.csv"
        )
    else:
        st.info(
            "Synthetic benchmark only. Scenarios were created alongside the detection logic, so these results do not establish real-world security accuracy."
        )
        counts = st.columns(3)
        counts[0].metric("Training events", f"{report['model']['train_rows']:,}")
        counts[1].metric("Calibration events", f"{report['model']['calibration_rows']:,}")
        counts[2].metric("Held-out test events", f"{report['test_rows']:,}")
        metric_table = pd.DataFrame(report["metrics"]).T[
            ["precision", "recall", "f1", "false_positive_rate", "average_precision"]
        ]
        metric_table.index.name = "Detector"
        st.dataframe(metric_table.style.format("{:.3f}"), width="stretch")
        st.markdown("**Scenario-level breakdown**")
        st.dataframe(pd.DataFrame(report["scenarios"]), hide_index=True, width="stretch")
        st.caption(
            "Metrics are computed per event. Average precision summarizes score ranking; the hybrid score is a discrete priority heuristic. A difficult low-and-slow scenario is retained to show a detection blind spot."
        )
        st.download_button(
            "Download evaluation JSON", json_bytes(report), "sentinel_evaluation.json", "application/json"
        )

with methodology:
    st.subheader("An auditable detection pipeline")
    st.markdown("""
1. **Validate events.** Check required fields, timestamps, status codes, duplicate IDs and batch limits.
2. **Learn a historical baseline.** Fit frequency maps, principal context, scaling, Isolation Forest and PCA on the training period only.
3. **Calibrate once.** Set each statistical detector's threshold from a separate calibration period. Uploaded test events never set their own thresholds.
4. **Combine evidence.** Flag the union of statistical detectors and five explicit rules. More alerts can improve recall while increasing false positives.
5. **Review and export.** Inspect the exact signals, save a verdict, and export the complete results.
""")
    st.markdown("**Operational boundaries**")
    st.write(
        "This is a local, single-user research prototype. Ten-minute context resets per input batch; include the full investigation window. Events at identical timestamps are ordered by event ID. Off-hours means before 07:00 or from 20:00 UTC. New IPs and clients are compared to the frozen training baseline."
    )
    st.write(
        "The PCA detector is a lightweight linear reconstruction baseline. The earlier TensorFlow autoencoder and cloud chatbot are not part of v2. Labels and scenario names are used only for evaluation."
    )
    st.caption(
        "Default calibration tail: 3% per statistical detector. This is not a guarantee of the hybrid flag rate or production false-positive rate."
    )
    st.json(detector.metadata, expanded=False)
