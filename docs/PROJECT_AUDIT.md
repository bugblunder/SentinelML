# Review of the uploaded prototype and v2 changes

The original archive was inspected as source and tabular data. Its serialized model files were not deserialized. This review does not establish the original model's accuracy.

## Findings and implemented changes

| Original finding | Consequence | V2 change |
|---|---|---|
| Preprocessing fitted on the full dataset before the supervised train/test split | Evaluation could benefit from information outside training | Split by event time before fitting any learned transform; labels excluded from features |
| Autoencoder flags and severity depended on quantiles of each uploaded batch | An identical event could be treated differently depending on the upload's score distribution | Fixed thresholds learned once from a separate calibration period |
| `flagged.head(100)` reused for headline counts | Dashboard could undercount flagged events | Whole-batch metrics; only the overview preview is limited |
| Inference converted the complete output to strings | Datetime and Boolean operations became fragile | Typed numerical/Boolean/timestamp outputs preserved until serialization |
| Training button referenced `sys.executable` without importing `sys` | Background training would fail | Direct, synchronous model workflow with visible progress and errors |
| “Reload models” reused cached model state without clearing it | Retrained artifacts might not actually reload | One shared detector pipeline; explicit custom training and cached immutable demo |
| Duplicate inference modules and repeated transforms | Inconsistent behavior and unnecessary work | Single package used by both dashboard and CLI |
| Window rules used current wall-clock time | Historical logs could silently produce no recent alerts | Causal context anchored to event timestamps |
| CSV/PDF export functions returned paths, then passed them as download payloads | Downloads could contain the path text instead of report bytes | CSV/JSON/HTML generated as bytes; HTML can be printed to PDF |
| A feedback CSV was cached without invalidation | Review state could become stale; concurrent writes were fragile | Parameterized SQLite upserts scoped to event/model |
| Chatbot wrappers were inconsistent and the main inference path disabled AI | Advertised explanation capability was unreliable | Deterministic detector evidence and review guidance; no API dependence |
| Dense categorical and text expansion | Potentially expensive high-dimensional representations | 18 explicit numerical features, with documented trade-offs |
| Raw logs, accumulated reports, compiled Python files, models and `.env` mixed with source | Difficult to publish a clean, reproducible repository | Curated source package, synthetic data, ignored runtime artifacts and clear setup |
| No executed benchmark or regression suite in the archive | Little evidence to substantiate résumé claims | Reproducible seeded experiments, stored outputs and automated tests |

## Deliberate removals

- **TensorFlow autoencoder:** replaced with PCA reconstruction as a lightweight linear baseline. Do not claim that v2 implements deep learning.
- **Random Forest / Gradient Boosting claims:** not retained; the original supplied dataset did not have a label column to support their training/evaluation path.
- **Gemini chatbot:** removed from the supported product flow. V2 explanations are deterministic and should not be described as generative AI.
- **Original datasets and binaries:** excluded from the shareable package. The synthetic generator documents exactly where the demonstration data comes from.

## Handling the original environment file

The archive included a `.env` file. It is excluded from the refined package and ignored by source control rules. If any credential in the original archive is live, rotate it with its provider before reuse. V2 requires no API credential. Removing a file from a new ZIP does not revoke a key or erase an earlier upload/repository history.

## What this revision does not claim

There is no verified enterprise deployment, live cloud ingestion, production throughput benchmark, independent attack dataset, incident-level evaluation, automated incident response or published research result. The future work is separated from implemented functionality throughout the documentation.
