"""Render measured results. Install requirements-analysis.txt, then run this script."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
data = pd.read_csv(ROOT / "reports/benchmark/seed_metrics.csv")
order = ["Isolation Forest", "PCA reconstruction", "Rules only", "Hybrid union"]
summary = data.groupby("detector")[["f1", "false_positive_rate"]].agg(["mean", "std"]).loc[order]
colors = ["#9eafbe", "#0b8b7a", "#54748a", "#173c52"]
plt.rcParams.update(
    {"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False}
)
fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"width_ratios": [1.05, 1]})
fig.patch.set_facecolor("#f6f8fb")
for ax, metric, title in zip(
    axes,
    ["f1", "false_positive_rate"],
    ["F1 score · higher is better", "False-positive rate · lower is better"],
):
    scale = 100 if metric == "false_positive_rate" else 1
    means = summary[(metric, "mean")].to_numpy() * scale
    stds = summary[(metric, "std")].to_numpy() * scale
    y = np.arange(len(order))
    ax.set_facecolor("#f6f8fb")
    ax.barh(
        y,
        means,
        xerr=stds,
        color=colors,
        height=0.55,
        capsize=4,
        error_kw={"ecolor": "#33495b", "elinewidth": 1.2},
    )
    ax.set_yticks(
        y,
        ["Isolation Forest", "PCA reconstruction", "Rules only", "Hybrid union"]
        if metric == "f1"
        else [""] * 4,
    )
    ax.invert_yaxis()
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=18, color="#173449")
    ax.set_xlim(0, 1 if metric == "f1" else 8)
    ax.grid(axis="x", color="#dde5ec", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.tick_params(length=0, colors="#536b7b")
    for i, (mean, std) in enumerate(zip(means, stds)):
        ax.text(
            mean + std + (0.015 if metric == "f1" else 0.15),
            i,
            f"{mean:.3f}" if metric == "f1" else f"{mean:.1f}%",
            va="center",
            fontsize=10,
            color="#173449",
        )
fig.suptitle(
    "More signals do not automatically make a better detector.",
    x=0.04,
    y=0.98,
    ha="left",
    fontsize=18,
    fontweight="bold",
    color="#173449",
)
fig.text(
    0.04,
    0.885,
    "SentinelML · Synthetic temporal holdouts · Seeds 11, 42 and 73",
    color="#637789",
    fontsize=11,
)
fig.text(
    0.04,
    0.045,
    "Bars: mean across three runs. Error bars: sample standard deviation.\nSynthetic scenarios were designed alongside the rules; these results do not establish real-world security accuracy.",
    fontsize=9,
    color="#637789",
    linespacing=1.7,
)
fig.subplots_adjust(left=0.18, right=0.97, top=0.75, bottom=0.20, wspace=0.18)
out = ROOT / "docs/assets"
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / "benchmark.png", dpi=170, facecolor=fig.get_facecolor())
fig.savefig(out / "benchmark.svg", facecolor=fig.get_facecolor())
plt.close(fig)
print("Rendered docs/assets/benchmark.png and benchmark.svg")
