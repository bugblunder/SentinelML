# Data contract

## Accepted CSV

UTF-8, one header row, unique column names, at most **25 MiB** and **100,000 rows** per input. The limit is a validation guard, not a measured throughput guarantee. Column names are case-sensitive. No database connection is required.

| Column | Required | Contract |
|---|---|---|
| `event_time` | Yes | ISO 8601 recommended; parsed to UTC. Invalid/missing values reject the batch. Naive timestamps are interpreted as UTC. |
| `event_name` | Yes | Non-empty action name; missing/`unknown` values reject the batch. |
| `principal_name` | Yes | Missing/blank values become `unknown`; quality warning returned. |
| `event_id` | No | If present, non-empty and unique; preserve source IDs when possible. Otherwise deterministic IDs are generated. |
| `response_status` | No | Integer HTTP status 100–599 or 0 for unknown. Missing column becomes 0; invalid supplied values reject the batch. |
| `ip_address` | No | String; absence becomes `unknown`. Address syntax/geolocation is not validated. |
| `source_service` | No | Service string, such as `compute` or `storage`. |
| `auth_type` | No | Authentication method string. |
| `resource_name` | No | Retained for review and event identity. Not a numerical model feature. |
| `opc_client_info` | No | Client/tool string. |
| `compartment_name` | No | Scope string used for cross-compartment context. |
| `label` | Evaluation only | Exactly 0 or 1; it never enters model features. |
| `scenario` | Evaluation only | Optional group name for scenario breakdowns. |
| `is_synthetic` | Provenance only | Used to describe the evaluation source, not to fit or score. |

Known text fields are limited to 2,048 characters. Extra fields are retained in outputs but ignored by feature engineering. Duplicate payloads are reported and retained because a repeated observation is not necessarily a duplicate ingestion record; they may inflate burst counts.

```csv
event_time,event_name,principal_name,ip_address,response_status,source_service
2026-01-01T09:00:00Z,GetObject,analyst-01,192.0.2.11,200,storage
2026-01-01T09:01:00Z,ListBuckets,analyst-01,192.0.2.11,200,storage
```

This tiny example demonstrates the format; training needs at least 100 events, calibration at least 50, and the CLI time split also needs at least 50 test events.

## Rule contract

| Rule | Trigger | Weight |
|---|---|---:|
| R1 | At least 5 responses with status 401/403 for a known principal in the current/prior ten-minute window | 65 |
| R2 | At least 20 discovery actions for a known principal in ten minutes | 60 |
| R3 | IP unseen for a known principal in training, outside 07:00–19:59 UTC | 45 |
| R4 | `CreatePolicy`, `UpdatePolicy`, `Delete…` or `UpdateUser…` action with an unseen client or off-hours context | 70 |
| R5 | At least 10 events across at least 4 non-unknown compartments for a known principal in ten minutes | 55 |

Discovery actions are `GetVcn`, `GetVnic`, `ListBuckets`, `ListUsers`, `ListInstances`. Rule matching is case-sensitive. “Unseen” means absent from the frozen training baseline, not absent from the recent upload. R1/R2/R5 can keep firing on subsequent events while the historical window remains above threshold. They identify review-worthy context, not a verdict about every event in the window.

## Missingness and provenance

The supplied original training CSV had 2,090 rows, including 508 missing principals and 5 missing event names. V2 reports unknown principals and rejects missing action names instead of silently treating them as valid actions. Correct or explicitly remove invalid source records before training, and record that decision in your dataset notes. The included demonstration does not use those original logs: it is generated entirely by `sentinel/demo.py` and has its own manifest.

Exports contain original log fields and analyst notes; treat them with the same care as the input logs. CSV export prefixes formula-like text and column names, and HTML export escapes input content. These output protections do not anonymize the records.
