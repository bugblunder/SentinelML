# Architecture and engineering decisions

## Boundaries

The `sentinel` package owns validation, feature engineering, scoring and evaluation. The dashboard and CLI call the same functions. Neither entry point implements an independent detector. The app trains the synthetic demo once through `st.cache_resource`; an uploaded historical baseline trains only when the user presses **Train baseline**.

| Component | Input | Output | State |
|---|---|---|---|
| Schema | DataFrame / UTF-8 CSV | Normalized events + quality report | None |
| Historical baseline | Training events | Frequencies and per-principal sets | Frozen after fitting |
| Context engine | One normalized batch | Past/current ten-minute counts | Ephemeral per batch |
| Models | 18 numerical features | IF score + PCA reconstruction error | Trained parameters |
| Calibration | Separate later baseline events | Two thresholds + score references | Frozen after calibration |
| Rule engine | Events, features and context | Rule IDs + severity weight | Constants in `rules.py` |
| Triage | Model flags and rule flags | Priority, evidence, review guidance | None |
| Feedback | Event ID, model ID, verdict | SQLite upsert | Local file, no automatic training |

## Features

The 18-dimensional representation has a fixed width regardless of category cardinality:

| Group | Features | Fit behavior |
|---|---|---|
| Time | Hour sine/cosine, weekend, off-hours | Event-local; UTC |
| Response | HTTP error, authentication failure | Event-local |
| Context | Log1p of events, auth failures, reconnaissance actions, distinct compartments in ten minutes | Past/current events only |
| Rarity | Negative log smoothed frequency of event, service, auth type, client | Training frequencies only |
| Novelty | New principal; new IP, client and action for known principal | Frozen training sets |

IDs, labels, scenario names and the `is_synthetic` indicator are excluded from model features. Resource names are retained for traceability but are not model inputs. A bounded feature vector avoids the dense high-cardinality one-hot expansion in the original implementation. The stored frequency maps still grow with observed category cardinality; this is not a constant-memory streaming system.

## Temporal semantics

Splits are derived from elapsed event time: cutoff A at 60% and cutoff B at 80%. Equal timestamps remain within a single split. Model fitting also rejects overlapping train/calibration timestamps. No data is selected based on the machine's current clock.

Context windows include `[event_time - 10 minutes, event_time]`. Events are processed in timestamp order, with event ID as the stable tie-breaker. The current event contributes to its own count. Anonymous principals get isolated context keys, so unrelated unknown users do not form one artificial burst. No row after the current event can alter its context.

Context resets for each call to `score`. Scoring one event alone can differ from scoring it with earlier events in the same batch. This is expected, explicitly tested for future-event independence, and is not presented as partition-invariant streaming. To investigate a window, include its preceding context. There is no cross-upload streaming state.

## Detection and calibration

Isolation Forest uses 200 trees, one CPU worker and a fixed seed. The implementation negates `score_samples`, making larger values more anomalous. PCA retains 90% of training variance and measures mean squared reconstruction error in the standardized feature space.

Each detector's threshold is the calibration sample's 97th percentile using the `higher` quantile method. Flags use strict `score > threshold`. Ties can reduce the actual calibration tail rate. The 3% setting describes each model's calibration score tail; it does not promise a 3% test false-positive rate, and the union can flag more events.

Statistical flags and rule flags are combined with logical OR. A separate priority heuristic uses the maximum rule weight or 40 for a statistical flag, plus 10 per additional signal family, capped at 100. Critical starts at 80, high at 60, medium covers the remaining flagged events. This is a queue-ordering mechanism, not a calibrated attack probability.

## Persistence and privacy

The dashboard processes data in its Python server process and has no LLM or cloud inference integration. Streamlit telemetry is disabled. In a remote deployment, uploaded logs still go to that remote host; “local processing” does not mean browser-only processing.

Feedback uses parameterized SQLite statements and `(event_id, model_id)` as its key. Model IDs include configuration, data fingerprints, runtime versions and learned thresholds. Supply stable, globally meaningful event IDs when combining multiple sources. Derived IDs are hashes of normalized fields with a within-batch occurrence suffix; repeated identical observations across different batch boundaries cannot always be reconciled.

Model saves use a temporary file followed by replacement and a metadata JSON sidecar. Only locally generated, trusted joblib files may be loaded: joblib/pickle deserialization can execute code. The dashboard intentionally has no model-upload control. It has no user authentication or multi-tenant access controls.

## Why the scope changed

PCA gives a compact, repeatable reconstruction baseline without requiring TensorFlow or distributing a serialized neural model. It is a linear model, not an autoencoder equivalent. Neural reconstruction models can be reintroduced only with their own validation and comparison. The external chatbot is replaced by deterministic, auditable evidence so the core demonstration requires neither a credential nor sending log content to a third party.

## Next research increments

1. Evaluate an independently sourced, permitted dataset with expert-adjudicated labels and incident-level grouping.
2. Compare a decision rule selected using training/calibration data against the fixed union on an untouched test set.
3. Test contamination and drift; measure principal-level alert rates and review workload.
4. Add resumable context state and prove equivalence between full-batch and chunked processing.
5. Explore sequence or identity-resource graph features for low-and-slow activity, with an explicit privacy model.
