# SentinelML: temporal evaluation of explainable audit-log anomaly detection

## Abstract

SentinelML studies the trade-off between statistical anomaly detection and explicit contextual rules for cloud audit investigation. An 18-feature representation combines event attributes, historical rarity, identity novelty and causal ten-minute context. Isolation Forest and PCA reconstruction are fitted on an earlier time period, with separate calibration thresholds. Four detector variants are evaluated on generated later events. In the seed-42 run, PCA achieves F1 0.832 while the hybrid union achieves 0.785; the union matches PCA recall but increases false positives. A three-seed comparison retains the same aggregate ordering. The result illustrates why adding detector signals should be evaluated against review workload. The benchmark is synthetic and co-designed with the rules, so it demonstrates pipeline behavior rather than generalizable security effectiveness.

## Question and hypothesis

**Question:** Does a union of statistical detectors and explicit rules improve anomaly coverage enough to justify additional review workload?

**Working hypothesis:** Rules will identify concentrated behavioral patterns, while statistical detectors may flag unusual combinations outside the rule definitions. Their union might improve coverage, but can increase false positives. The experiment is descriptive: no hypothesis-test p-values or claims of statistical significance are made.

## Data design

Seed 42 produces 7,872 events across 30 days and 16 fictional principals. Routine activity includes reads, discovery, updates, occasional failed requests, off-hours activity and scheduled inventory. Legitimate source-IP changes appear in the later baseline/test periods. Four anomaly scenarios appear in the final 20% of days: credential abuse, discovery bursts, unusual policy changes and low-and-slow access.

The low-and-slow scenario deliberately resembles routine `GetObject` traffic. Its label is generator intent, not a signal directly exposed to the detector. This prevents the demo from implying that every malicious objective is identifiable from the chosen fields.

Training and calibration contain generated benign activity; no label-based filtering is performed by the pipeline. This is a favorable novelty-detection setup and does not test resilience to contaminated historical data. Scenario design is not independent of rule design, another major source of optimistic results.

## Protocol

1. Normalize required fields and timestamps.
2. Split by 60% / 20% / 20% of elapsed time; equal timestamps remain together.
3. Fit rarity maps, principal context and standardization on training events only.
4. Fit a 200-tree Isolation Forest and PCA retaining 90% of training variance.
5. Set each model threshold at the calibration score's 97th percentile (`higher` method; strict exceedance).
6. Evaluate fixed rules, each model, and their union on later events.
7. Repeat with seeds 11, 42 and 73, changing both data-generator and Isolation Forest seeds.

The source did not change the detection thresholds or feature design after seeing the reported test metrics. The benchmark is not a tuning loop. Evaluation is per event; correlated events in a single scenario are not treated as independent incidents for any inferential claim. Windows reset in each partition, rather than carrying hidden state across splits.

## Single-run results

Training / calibration / test counts: **4,463 / 1,517 / 1,892**. There are **372** positive scenario labels in the test set, a prevalence of **19.66%**, substantially easier for precision than many rare-event operational settings.

| Detector | TP | FP | FN | TN | Precision | Recall | F1 | AP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Isolation Forest | 144 | 50 | 228 | 1,470 | 0.742 | 0.387 | 0.509 | 0.768 |
| PCA reconstruction | 308 | 60 | 64 | 1,460 | 0.837 | 0.828 | 0.832 | 0.820 |
| Rules only | 261 | 2 | 111 | 1,518 | 0.992 | 0.702 | 0.822 | 0.754 |
| Hybrid union | 308 | 105 | 64 | 1,415 | 0.746 | 0.828 | 0.785 | 0.840 |

AP is scikit-learn's average precision, not trapezoidal PR-AUC. Model AP uses raw anomaly scores; rule AP uses maximum rule weight; hybrid AP uses the discrete priority heuristic. These ranking metrics describe different scoring functions, while precision/recall/F1 describe each fixed decision rule.

## Across-seed comparison

Mean ± sample standard deviation over three seeds; these are descriptive spread estimates, not confidence intervals.

| Detector | Precision | Recall | F1 | False-positive rate |
|---|---:|---:|---:|---:|
| Isolation Forest | 0.761 ± 0.018 | 0.387 ± 0.000 | 0.513 ± 0.004 | 0.030 ± 0.003 |
| PCA reconstruction | 0.850 ± 0.035 | 0.795 ± 0.037 | 0.820 ± 0.011 | 0.035 ± 0.010 |
| Rules only | 0.986 ± 0.011 | 0.697 ± 0.004 | 0.817 ± 0.006 | 0.002 ± 0.002 |
| Hybrid union | 0.759 ± 0.021 | 0.798 ± 0.031 | 0.778 ± 0.006 | 0.062 ± 0.009 |

Changing data and model seeds together measures overall run variability; it does not isolate model initialization variance. Three seeds and a single temporal holdout per seed are not a broad robustness study.

## Error analysis

The seed-42 hybrid catches all 96 credential-abuse events and all 48 unusual-policy-change events. It flags 163 of 192 reconnaissance-burst events. It catches just **1 of 36** low-and-slow events, exposing a lack of discriminative information for that scenario.

Among generated benign events, it flags 12 of 30 IP-change events and 7 of 48 scheduled-inventory events. A frozen baseline can treat legitimate change as suspicious, and a single global threshold may not suit every principal or activity type. This is a concrete reason to evaluate adaptive baselines and identity-specific policy in future work.

The union adds **45 false positives** over PCA with **zero additional true positives** in seed 42. The test therefore provides no evidence for adopting the union over PCA as the default classifier under an F1 objective. The dashboard retains it as an explicit broad-review policy and allows the constituent evidence to be inspected. A production choice should be selected on validation data under a specified review-budget or cost objective, then evaluated once on untouched data.

## Threats to validity

- Generated patterns and hand-written rules share design assumptions; this inflates apparent coverage of those scenarios.
- Positive prevalence is high, and operating precision depends on prevalence.
- Synthetic labels reflect injection logic, not independent analyst adjudication.
- Event-level metrics can overrepresent a few repeated incidents.
- Frozen baseline novelty differs from an adaptive streaming baseline.
- Off-hours is a global UTC policy; the benchmark does not model regional work schedules.
- Calibration assumes a mostly benign, representative period. Contamination and drift remain untested.
- No independently sourced real-world benchmark, statistical significance test or production throughput claim is included.
- The heuristic evidence is not a causal explanation or proof of malicious intent.

## Reproduction and references

Run `python -m sentinel demo` and `python -m sentinel benchmark` from the repository root. Reference results include full hashes, environment versions, split dates and thresholds. Small numerical differences may occur across environments; compare using the pinned dependencies and treat timings separately.

Primary implementation references:

- [scikit-learn: data leakage and preprocessing](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn: Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [scikit-learn: average precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)
- [Streamlit: application testing](https://docs.streamlit.io/develop/api-reference/app-testing)

This note is project documentation, not a peer-reviewed publication.
