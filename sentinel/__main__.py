"""python -m sentinel: reproducible demo, training, scoring and evaluation."""

import argparse
import json
from pathlib import Path

from sentinel.demo import generate_demo
from sentinel.evaluation import evaluate, seed_study, temporal_split, write_report
from sentinel.export import csv_bytes, html_report, json_bytes
from sentinel.model import Detector, ModelConfig
from sentinel.schema import DataValidationError, read_events


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m sentinel", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Generate synthetic data and evaluate a local model")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    train = commands.add_parser(
        "train", help="Fit on the first 60%% of time; calibrate on the next 20%%; hold out the last 20%%"
    )
    train.add_argument("csv", type=Path)
    train.add_argument("--output", type=Path, default=Path("artifacts/detector.joblib"))
    train.add_argument("--alert-rate", type=float, default=0.03)
    score = commands.add_parser("score", help="Score events with your own locally trained model")
    score.add_argument("csv", type=Path)
    score.add_argument("--model", type=Path, required=True)
    score.add_argument("--output", type=Path, default=Path("artifacts/scored"))
    evaluate_cmd = commands.add_parser(
        "evaluate", help="Evaluate a labeled dataset with a chronological holdout"
    )
    evaluate_cmd.add_argument("csv", type=Path)
    evaluate_cmd.add_argument("--output", type=Path, default=Path("artifacts/evaluation"))
    benchmark = commands.add_parser("benchmark", help="Repeat synthetic experiments with seeds 11, 42, 73")
    benchmark.add_argument("--output", type=Path, default=Path("artifacts/benchmark"))
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            args.output.mkdir(parents=True, exist_ok=True)
            data = generate_demo(args.seed)
            data.to_csv(args.output / "events.csv", index=False)
            report, model, results = evaluate(data, ModelConfig(seed=args.seed))
            write_report(report, args.output)
            model.save(args.output / "detector.joblib")
            (args.output / "scored.csv").write_bytes(csv_bytes(results))
            print(json.dumps({"output": str(args.output), "metrics": report["metrics"]}, indent=2))
        elif args.command == "train":
            data, quality = read_events(args.csv)
            train, cal, test = temporal_split(data)
            model = Detector(ModelConfig(target_alert_rate=args.alert_rate)).fit(train, cal)
            model.save(args.output)
            print(
                json.dumps(
                    {"model": str(args.output), "holdout_events": len(test), "warnings": quality.warnings},
                    indent=2,
                )
            )
        elif args.command == "score":
            data, quality = read_events(args.csv)
            model = Detector.load(args.model)
            results, diagnostics = model.score(data)
            diagnostics["quality"] = quality.__dict__
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "events.csv").write_bytes(csv_bytes(results))
            (args.output / "diagnostics.json").write_bytes(json_bytes(diagnostics))
            (args.output / "review.html").write_bytes(html_report(results, diagnostics))
            print(
                json.dumps(
                    {"events": len(results), "alerts": int(results.is_suspicious.sum()), **diagnostics},
                    indent=2,
                )
            )
        elif args.command == "evaluate":
            data, _ = read_events(args.csv)
            report, _, _ = evaluate(data)
            write_report(report, args.output)
            print(json.dumps(report["metrics"], indent=2))
        else:
            runs, metrics = seed_study()
            args.output.mkdir(parents=True, exist_ok=True)
            metrics.to_csv(args.output / "seed_metrics.csv", index=False)
            (args.output / "seed_runs.json").write_bytes(json_bytes(runs))
            summary = metrics.groupby("detector")[
                ["precision", "recall", "f1", "false_positive_rate", "average_precision"]
            ].agg(["mean", "std"])
            summary.to_csv(args.output / "seed_summary.csv")
            print(summary.round(3).to_string())
    except (DataValidationError, ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
