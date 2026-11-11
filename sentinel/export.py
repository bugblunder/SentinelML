"""In-memory exports; CSV cells cannot be interpreted as spreadsheet formulas."""

import html
import json


def csv_bytes(frame):
    safe = frame.copy()

    def escape_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + value
        return value

    for col in safe.select_dtypes(include=["object", "string"]):
        safe[col] = safe[col].map(escape_cell)
    safe.columns = [escape_cell(col) for col in safe.columns]
    return safe.to_csv(index=False).encode("utf-8-sig")


def json_bytes(value):
    return (json.dumps(value, indent=2, default=str, allow_nan=False) + "\n").encode()


def html_report(frame, diagnostics):
    """Portable report with wrapped evidence and print styling, without external assets."""
    flags = frame[frame.is_suspicious].sort_values("priority_score", ascending=False)
    columns = ["event_time", "principal_name", "event_name", "severity", "evidence"]
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row[c]))}</td>" for c in columns) + "</tr>"
        for _, row in flags.iterrows()
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'><title>SentinelML review report</title>"
        "<style>body{font:14px system-ui;color:#152b3b;max-width:1200px;margin:48px auto;padding:0 24px}"
        "h1{font-size:32px}p{line-height:1.7}table{border-collapse:collapse;width:100%;table-layout:fixed}"
        "td,th{padding:12px;text-align:left;border-bottom:1px solid #dce3e8;overflow-wrap:anywhere;vertical-align:top}"
        "th{background:#edf4f6}td:last-child,th:last-child{width:40%}"
        "@media print{body{margin:0;font-size:10px}thead{display:table-header-group}tr{break-inside:avoid}}"
        "</style><h1>SentinelML / Audit review</h1>"
        f"<p>{len(frame):,} events · {len(flags):,} flagged · model {html.escape(diagnostics['model_id'])}</p>"
        "<p>Flags identify unusual activity for human review. They do not confirm an attack. "
        "Priority scores are heuristics, not attack probabilities. Use your browser's Print option to save as PDF.</p>"
        "<table><thead><tr>"
        + "".join(f"<th>{html.escape(c.replace('_', ' ').title())}</th>" for c in columns)
        + "</tr></thead><tbody>"
        + (rows or "<tr><td colspan='5'>No events flagged.</td></tr>")
        + "</tbody></table></html>"
    ).encode()
