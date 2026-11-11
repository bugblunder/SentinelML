# SentinelML evaluation

Dataset: **synthetic**. Unit: **event (not independent attack incident)**.

Train / calibration / test: 4,463 / 1,517 / 1,892 events.

| Detector | Precision | Recall | F1 | False-positive rate | Average precision |
|---|---:|---:|---:|---:|---:|
| Isolation Forest | 0.742 | 0.387 | 0.509 | 0.033 | 0.768 |
| PCA reconstruction | 0.837 | 0.828 | 0.832 | 0.039 | 0.820 |
| Rules only | 0.992 | 0.702 | 0.822 | 0.001 | 0.754 |
| Hybrid union | 0.746 | 0.828 | 0.785 | 0.069 | 0.840 |

## Interpretation limits

- Synthetic scenarios are designed alongside the rules; results are an engineering check, not external validity.
- Correlated events in one scenario are not independent samples; event recall is not incident recall.
- The per-model calibration alert target is not a guaranteed test false-positive rate or hybrid alert rate.
- Hybrid average precision uses the discrete review-priority score, not a probability.
- Low-and-slow access is intentionally difficult to distinguish from normal access with these fields.
