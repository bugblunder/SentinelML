# Five-minute project demonstration

## 0:00–0:45 — Frame the problem

Open `python -m streamlit run app.py`. Explain that the default dataset is synthetic and that the app is a local research prototype. Show the whole-batch event count and flag rate. A flagged event is a request for investigation, not a confirmed incident.

## 0:45–1:30 — Explain the overview

Point out the hourly volume and signal counts. Detector counts overlap because the same event can trigger multiple approaches. The first queue previews eight high-priority events; the headline flagged count and export include all flagged events.

## 1:30–2:30 — Investigate a policy change

Open **Investigate** and search for `CreatePolicy`. Select an `analyst-06` event. Inspect which models exceeded fixed thresholds and which explicit rules fired. Explain the new-IP/client context and the UTC off-hours policy. Save an analyst review and show that it appears in the saved reviews table. State that feedback does not automatically retrain the detector.

## 2:30–3:45 — Discuss the experiment

Open **Evaluation**. Explain why training, calibration and test are separate. Compare the PCA and hybrid rows: in the seed-42 run, they have the same recall, but the union has more false positives. Point out the low-and-slow failure case and the benign-IP-change false positives. State that the rules and generator share assumptions, so the numbers are not real-world validation.

## 3:45–4:30 — Show reproducibility

Open **Model & method** and expand metadata. Show split dates, hashes, thresholds and environment versions. Explain that the CLI can reproduce the experiment and run it across three seeds. The model operates on 18 features; the label and scenario columns never enter the model.

## 4:30–5:00 — Close with a concrete next experiment

Describe a controlled contamination study or independent incident-level evaluation. Specify the training/calibration choice, what will remain held out, and the metric that would justify a change. Avoid promising that a more complex model will necessarily improve detection.
