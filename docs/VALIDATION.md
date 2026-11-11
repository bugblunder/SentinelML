# Release validation

Validation performed on **10 November 2026**, using Python **3.12.14**, NumPy **2.3.5**, pandas **2.2.3**, scikit-learn **1.8.0**, Streamlit **1.51.0**, Plotly **6.4.0** and pytest **8.4.2**.

## Executed checks

| Check | Result | Scope |
|---|---|---|
| `python -m pytest -q` | **39 passed** | Schema errors, chronology, feature exclusion, causal future independence, model persistence, rule behavior, metrics, safe exports, feedback and dashboard behavior |
| `ruff check .` | Passed | Imports, syntax-related and selected Python lint rules |
| `ruff format --check .` | Passed | All Python files formatted |
| `python -m compileall -q sentinel app.py scripts` | Passed | Python syntax compilation |
| Seed-42 demo evaluation | Completed | 7,872 synthetic events; four detector variants; 1,892-event test period |
| Three-seed benchmark | Completed | Generator/model seeds 11, 42 and 73; per-run and aggregate outputs included |
| CLI train → save → load → score | Completed | Bundled CSV; separate test file; complete CSV, JSON and HTML outputs |
| Plot generation and visual inspection | Passed | Static benchmark figure rendered from the measured seed metrics |
| Streamlit AppTest | Passed | Demo rendering, four tabs, headline counts exceeding 100 flags, search empty state and custom-upload workspace empty state |

## What the checks establish

The test suite explicitly checks that changing labels/scenario names cannot alter features, future events cannot change prior event scores in a complete prefix, thresholds remain unchanged across inference calls, train/calibration times cannot overlap, and model serialization preserves predictions. Tests also cover historical-time bursts, unknown-principal isolation, duplicate payload warnings, formula-like CSV text/header escaping and HTML escaping.

The dashboard tests use Streamlit's simulated application runtime. They exercise Python-rendered application behavior; they do not establish pixel-perfect layout, accessibility conformance or all browser upload interactions.

## Verification limits

- Browser screenshot verification could not be completed: this environment blocked Chromium's required socket/process operation. No claim of browser visual QA is made.
- The container recipe is supplied but was not built here.
- The GitHub Actions workflow is supplied but has not run in a user repository. Only Python 3.12 was executed locally; the workflow also targets Python 3.11.
- No live cloud account, original serialized model artifact, production data feed or remote AI service was exercised.
- The 100,000-row limit is an input bound, not a measured throughput target. Reported timings are local observations only.
- The automated UI test writes local demonstration feedback. Runtime feedback and generated model binaries are excluded from the release archive.

The saved benchmark JSON/CSV files provide the evidence for numerical claims. The ZIP is a source distribution: install dependencies and train the small demo locally. No original audit logs, API credentials, pretrained joblib/H5 files, bytecode caches or historical generated reports are included.


## Additional publication-preparation checks — 11 November 2026

These checks were run in a separate Python 3.13.5 Linux environment and should not be confused with the earlier Python 3.12.14 release-validation run above.

| Check | Result | Scope |
|---|---|---|
| `python -m pytest -q tests/test_detection.py tests/test_schema.py` | **34 passed** | Detection, schema, chronology and feature behavior; excludes Streamlit-dependent workflow tests |
| `python -m compileall -q sentinel app.py scripts` | Passed | Python syntax compilation |
| `python -m sentinel --help` and `python -m sentinel train --help` | Passed after fix | Corrected argparse percentage formatting in the training help text |
| `python -m sentinel demo --output <temporary-directory>` | Completed | Reproduced the seed-42 evaluation and generated local demo outputs; headline metrics matched the bundled reference results |

The full suite was not completed in this environment because Streamlit is not installed (`ModuleNotFoundError: streamlit` during test collection). The Streamlit dashboard workflow tests therefore remain unverified here. The CLI help fix is included in this publication-preparation revision and must be rechecked after dependency installation. Docker packaging has been removed and is not part of the supported setup.

## Additional Windows dashboard validation — 11 November 2026

The prepared release was also tested by the project owner on Windows using Python **3.12.1** and pytest **8.4.2** in the project's virtual environment.

| Check | Result | Scope |
|---|---|---|
| `python -m pytest -v` | **39 passed in 6.84s** | Complete test suite, including workflow and dashboard demo/filter tests |
| `python -m streamlit run app.py` | Started successfully | Streamlit server launched and served the local dashboard |
| `http://127.0.0.1:8501` | Opened successfully | Local browser access to the dashboard confirmed by the project owner |

The project owner additionally confirmed that the dashboard's sample-data, detection, investigation/explanation, analyst-feedback and report-export workflows worked during manual exploration. This is owner-reported functional validation, not an independent penetration test or cross-browser accessibility review. The earlier Linux-environment limitation above remains an accurate record of that separate environment; the Windows run completes the previously missing Streamlit-dependent automated test coverage.
