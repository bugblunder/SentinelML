# Presenting SentinelML in a master's application

## Positioning

**Project title:** SentinelML — Explainable Cloud Audit Anomaly Detection

**One-line description:** A reproducible security analytics prototype that combines anomaly detection, contextual rules and analyst review, with chronological evaluation and documented failure cases.

The most defensible admissions story is the combination of problem definition, careful evaluation, software engineering and recognition of limitations. Avoid presenting the project as a proven enterprise security system. It can support applications in computer science, data science or cybersecurity; choose the emphasis that matches the actual program and your interests.

## Résumé entry

Use the bullets below only after running the project and being able to explain the implementation. Add your actual dates, role, collaborators and repository link. Do not invent a deployment, publication or performance improvement over the original project.

**SentinelML — Explainable Cloud Audit Anomaly Detection**
*Python, scikit-learn, Streamlit, Plotly, SQLite*

- Developed a cloud audit-log investigation prototype with 18 engineered features, Isolation Forest, PCA reconstruction and five contextual detection rules.
- Designed a reproducible temporal evaluation pipeline with separate training, calibration and test periods; compared four detector variants across three seeded synthetic datasets.
- Built an interactive analyst dashboard with event-level evidence, severity filtering, persistent review feedback and CSV/JSON/HTML exports, supported by automated regression tests.

If space permits, replace the second bullet with this measured version:

> Evaluated four detection variants on 7,872 synthetic events; PCA achieved 0.832 F1 on a 1,892-event temporal holdout, while error analysis exposed additional false positives from detector union and poor coverage of low-and-slow activity.

Keep **synthetic** and **temporal holdout** in any metric-bearing statement. Do not rewrite 0.832 F1 as “83.2% accuracy.” The number describes the PCA baseline, not the hybrid queue or all variants.

## Program-specific emphasis

| Program direction | Emphasize | Avoid implying |
|---|---|---|
| Computer science | Modular design, temporal semantics, regression tests, reproducibility, data contracts | Proven distributed scalability or production deployment |
| Data science / ML | Leakage control, fixed calibration, ablations, threshold trade-offs, honest error analysis | Novel algorithms, state-of-the-art performance or external benchmark validation |
| Cybersecurity | Audit telemetry, identity context, rule evidence, analyst review, detection blind spots | Confirmed incident response effectiveness or real-world attacker attribution |

## A concise statement-of-purpose paragraph

> In SentinelML, I explored how statistical anomaly detection and contextual rules can support investigation of cloud audit logs. I structured the evaluation around separate historical training, calibration and test periods, then compared Isolation Forest, PCA reconstruction, explicit rules and their union. The synthetic experiments showed that combining detectors could increase false positives without improving recall, while low-and-slow access remained difficult to distinguish from routine activity. This made me interested in evaluation under realistic operational constraints and in representations that capture longer-term behavior.

Adapt the paragraph to your own experience and interests; it should describe what you understand and actually did. The final sentence is an example research direction, not an assertion about your personal motivation.

## Two-minute technical explanation

**Problem:** Audit logs contain large numbers of ordinary operations. Analysts need a review queue with evidence, while an anomaly score alone does not establish an attack.

**Approach:** Extract a fixed-width feature vector using action/client rarity, identity novelty, time features and past/current ten-minute context. Fit Isolation Forest and a PCA reconstruction baseline on historical events. Freeze thresholds from a separate calibration period. Compare them with explicit behavioral rules.

**Evaluation:** Use a temporal holdout and a seeded generator with benign changes, obvious burst patterns and a difficult low-and-slow scenario. Keep labels and scenario names outside feature engineering. Report precision, recall, F1, false-positive rate and average precision per detector.

**Finding:** The detector union is not automatically better. In seed 42 it adds 45 false positives over PCA without adding true positives. Across three seeds, PCA's mean F1 is higher. The next step is independent data and a decision policy chosen against an analyst review budget on validation data.

**Engineering:** The same package serves a command-line experiment workflow and a dashboard. Input validation, persisted model metadata, analyst review, export handling and regression tests make the demonstration repeatable.

## Questions you should be ready to answer

| Interview question | Key points to explain |
|---|---|
| Why not a random split? | Audit data is temporal; future behavior should not influence the historical baseline. Equal timestamps stay together. |
| Why separate calibration? | A threshold selected from the test upload changes the policy based on test data. The fixed threshold uses earlier held-out baseline scores. |
| Is the 3% setting a false-positive guarantee? | No. It is a per-model calibration tail target, with ties and distribution shift; the union can flag more events. |
| Why PCA instead of the original autoencoder? | A lightweight linear reconstruction baseline is easier to reproduce and compare. It is not deep learning or equivalent to a nonlinear autoencoder. |
| Are explanations causal? | No. They report fired detectors, thresholds, rules and observed context; they do not attribute causal importance. |
| What is the strongest limitation? | Synthetic data co-designed with rules and no independent real-world validation. Correlated event labels also differ from incident-level evaluation. |
| Why does the low-and-slow case fail? | The chosen observable fields resemble normal reads; intent is not directly measurable. Longer-term or graph/sequence context might help but needs testing. |
| Does it process streams? | It processes CSV batches. Causal windows do not use future events, but context resets per batch. |
| Is feedback used to improve the model? | It is persisted for review only. Automatic retraining is not implemented. |
| Why keep the union in the UI? | It is a transparent broad-review policy, with visible constituent evidence. It is not claimed to maximize F1. |

## Before including it in an application

1. Run the app and both reproduction commands on your computer.
2. Read the implementation of features, calibration, rules and evaluation; be able to walk through one flagged event.
3. Create your own repository and add your actual identity, dates and contribution description. The package does not invent these details.
4. Ensure you have permission to publish all project material. Only the bundled synthetic data belongs in the public demo; original logs and credentials are excluded.
5. Push the included CI workflow and confirm its run in your repository. Record a short demo if your application accepts portfolio material.
6. Follow the program's rules on AI-assisted work and describe assistance accurately if requested. Do not claim sole implementation of work you cannot substantiate.
7. Prefer one independent extension you can defend: for example, contamination experiments or an event-to-incident evaluation, with an untouched final test set.

## Suggested repository description

Explainable cloud audit-log anomaly detection with temporal calibration, reproducible synthetic benchmarks, and an interactive analyst review dashboard.

Suggested topics: `anomaly-detection`, `security-analytics`, `audit-logs`, `scikit-learn`, `streamlit`, `reproducible-research`.

No repository has been created or published as part of this package. Choose a distribution license appropriate to your ownership and dependencies before publishing; this revision does not assign a license on your behalf.
