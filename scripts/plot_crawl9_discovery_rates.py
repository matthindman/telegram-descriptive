"""Render narrow moving discovery rates from frozen crawl-9 SQL aggregates.

The primary display uses a centered 250,000-valid-exposure window, evaluated
every 25,000 exposures. All axes are linear. No population model is fitted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd


THRESHOLDS = (1000, 10000, 100000, 1000000)
COLORS = {1000: "#1762a3", 10000: "#168676", 100000: "#ac632b", 1000000: "#8055a1"}


def read_query(root, name):
    result = json.loads((root / "results" / f"{name}.json").read_text())
    if result.get("error") or result.get("status", {}).get("state") != "SUCCEEDED":
        raise ValueError(f"Unsuccessful query: {name}")
    if result.get("manifest", {}).get("truncated"):
        raise ValueError(f"Truncated query: {name}")
    frame = pd.DataFrame(result["rows"])
    for col in frame.columns:
        if col != "label":
            frame[col] = pd.to_numeric(frame[col], errors="raise")
    return frame


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save_figure(fig, out, name):
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(out / f"{name}.{suffix}", dpi=180, facecolor="white")
    plt.close(fig)


def plot_rates(data, comparison, out, width=250000, relative=False):
    data = data[data.window_width == width]
    total = int(data.n.max())
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#bac3ca", "axes.labelcolor": "#34414d",
        "xtick.color": "#465361", "ytick.color": "#465361",
        "svg.fonttype": "none", "pdf.fonttype": 42,
    })
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.8), sharex=True, sharey=relative)
    fig.subplots_adjust(left=0.10, right=0.96, top=0.80, bottom=0.20,
                        hspace=0.38, wspace=0.22)
    fig.text(0.10, 0.944,
             "Crawl 9: relative discovery rates" if relative else "Crawl 9: moving discovery rates",
             fontsize=22, weight="bold", color="#203344")
    fig.text(0.10, 0.900,
             f"Centered {width:,}-exposure window  |  Updated every 25,000 exposures  |  Linear axes",
             fontsize=11, color="#536372")
    fig.text(0.10, 0.865,
             ("Each rate is divided by its threshold's rate in the first million exposures. Common y-range."
              if relative else
              "New channel handles per million valid exposures  |  Separate y-ranges for each threshold"),
             fontsize=10, color="#536372")
    max_relative = 0
    for ax, threshold in zip(axes.flat, THRESHOLDS):
        part = data[data.threshold == threshold].sort_values("center_idx")
        x = part.center_idx.to_numpy() / 1e6
        y = part.relative_to_first_million_pct.to_numpy() if relative else part.rate_per_million.to_numpy()
        max_relative = max(max_relative, y.max())
        info = comparison.loc[threshold]
        ax.text(0, 1.16, f"≥ {threshold:,} subscribers", transform=ax.transAxes,
                fontsize=12, weight="bold", color=COLORS[threshold])
        ax.text(1, 1.16, f"{info.whole_crawl_new:,.0f} new", transform=ax.transAxes,
                ha="right", fontsize=9, color="#536372")
        ax.text(0, 1.055,
                f"First 1m: {info.first_million_rate:,.0f}  →  Last 1m: {info.last_million_rate:,.0f}  ({info.change_pct:+.0f}%)",
                transform=ax.transAxes, fontsize=9, color="#536372")
        ax.axvspan(0, width / 2e6, color="#c1c9d0", alpha=0.25, lw=0)
        ax.axvspan((total - width / 2) / 1e6, total / 1e6, color="#c1c9d0", alpha=0.25, lw=0)
        ax.plot(x, y, color=COLORS[threshold], lw=1.8)
        if relative:
            ax.axhline(100, color="#536372", ls="--", lw=1, alpha=0.8)
        else:
            # Disjoint first/last-million summaries orient the narrow, noisy curve.
            ax.hlines(info.first_million_rate, 0, 1, color="#34414d", ls="--", lw=1.4)
            ax.hlines(info.last_million_rate, total / 1e6 - 1, total / 1e6,
                      color="#34414d", ls="--", lw=1.4)
        ax.set_ylim(0, max(y.max() * 1.10, 1))
        ax.set_xlim(0, total / 1e6)
        ax.set_xticks(np.arange(0, 5.1, 1))
        ax.grid(axis="y", color="#e6eaee", lw=0.8)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True, steps=[1, 2, 2.5, 5, 10]))
        ax.yaxis.set_major_formatter(FuncFormatter(
            (lambda value, _: f"{value:,.0f}%") if relative else (lambda value, _: f"{value:,.0f}")))
    if relative:
        axes[0, 0].set_ylim(0, max_relative * 1.10)
    for ax in axes[:, 0]:
        ax.set_ylabel("Rate relative to first million" if relative else "New handles per million exposures")
    for ax in axes[-1]:
        ax.set_xlabel("Cumulative valid exposures in crawl 9 (millions)", labelpad=11)
    fig.text(0.10, 0.090,
             "Nested thresholds. New = absent from the pre-crawl-9 frame; each handle contributes at its first valid exposure only.",
             fontsize=8.5, color="#536372")
    fig.text(0.10, 0.061,
             "Shaded edges use shorter windows, divided by actual exposure counts. Subscriber size and usability use the fixed September snapshot.",
             fontsize=8.5, color="#536372")
    fig.text(0.10, 0.032,
             ("Dashed line: the first-million baseline (100%). Each panel uses the same relative scale."
              if relative else
              "Dashed segments: average rates over the first and last million exposures. Moving windows overlap; these are descriptive rates."),
             fontsize=8.5, color="#536372")
    suffix = "relative" if relative else "absolute"
    save_figure(fig, out, f"discovery_rates_{width // 1000}k_{suffix}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--window", type=int, default=250000,
                        choices=[100000, 250000, 500000, 1000000, 1500000],
                        help="Centered moving-window width in valid exposures (default: 250000)")
    parser.add_argument("--audit-root", type=Path,
                        default=Path("outputs/crawl9_2026-09-29"))
    args = parser.parse_args()
    out = args.root / "analysis"
    out.mkdir(exist_ok=True)
    windows = pd.concat([read_query(args.root, "narrow_rolling_windows"),
                         read_query(args.root, "rolling_windows")], ignore_index=True)
    fixed = read_query(args.root, "fixed_windows").set_index("label")
    count_cols = [f"new_ge_{t}" for t in (0, *THRESHOLDS)]
    require(not windows.duplicated(["window_width", "center_idx"]).any(), "Duplicate moving windows")
    require((windows.actual_exposures == windows.end_idx - windows.start_idx).all(), "Window denominator mismatch")
    require((windows.actual_exposures > 0).all(), "Empty window")
    require((windows.start_idx >= 0).all() and (windows.end_idx <= windows.n).all(), "Window outside crawl")
    require((windows.start_idx == np.maximum(0, windows.center_idx - windows.window_width / 2)).all(),
            "Incorrect centered-window lower bound")
    require((windows.end_idx == np.minimum(windows.n, windows.center_idx + windows.window_width / 2)).all(),
            "Incorrect centered-window upper bound")
    require((np.diff(windows[count_cols].to_numpy(), axis=1) <= 0).all(), "Non-nested discovery counts")
    require((windows[count_cols] >= 0).all().all(), "Negative discovery count")
    require((fixed.loc[[f"fifth_{n}" for n in range(1, 6)], count_cols].sum()
             == fixed.loc["whole_crawl", count_cols]).all(), "Disjoint fifths do not sum to crawl total")
    previous = json.loads((args.audit_root / "results" / "accumulation_bins.json").read_text())
    for t in (0, *THRESHOLDS):
        prior_total = sum(int(row["new_to_precrawl_frame"]) for row in previous["rows"]
                          if int(row["threshold"]) == t)
        require(prior_total == fixed.loc["whole_crawl", f"new_ge_{t}"], "Earlier audit disagrees")
    require((fixed.loc[["first_million", "last_million"], "actual_exposures"] == 1000000).all(),
            "Endpoint comparison does not use exactly one million exposures")

    long = windows.melt(id_vars=[c for c in windows if c not in count_cols],
                        value_vars=count_cols, var_name="threshold", value_name="new_handles")
    long["threshold"] = long.threshold.str.removeprefix("new_ge_").astype(int)
    long["rate_per_million"] = long.new_handles / long.actual_exposures * 1e6
    comparison = pd.DataFrame([
        {"threshold": t, "whole_crawl_new": int(fixed.loc["whole_crawl", f"new_ge_{t}"]),
         "first_million_rate": int(fixed.loc["first_million", f"new_ge_{t}"]),
         "last_million_rate": int(fixed.loc["last_million", f"new_ge_{t}"])}
        for t in (0, *THRESHOLDS)
    ]).set_index("threshold")
    comparison["change_pct"] = (comparison.last_million_rate / comparison.first_million_rate - 1) * 100
    long["relative_to_first_million_pct"] = long.rate_per_million / long.threshold.map(comparison.first_million_rate) * 100
    long.sort_values(["window_width", "threshold", "center_idx"]).to_csv(out / "rolling_discovery_rates.csv", index=False)
    comparison.to_csv(out / "first_vs_last_million.csv")
    fixed.to_csv(out / "fixed_window_counts.csv")
    plot_rates(long, comparison, out, width=args.window)
    plot_rates(long, comparison, out, width=args.window, relative=True)
    summary = {
        "analysis_date": "2026-09-29", "crawl": 9, "primary_window": args.window,
        "window_alignment": "centered", "grid_step": 25000, "axis_scale": "linear",
        "edge_rule": "clip to observed crawl and divide by actual valid exposures",
        "valid_exposures": int(fixed.loc["whole_crawl", "actual_exposures"]),
        "thresholds_are_nested": True,
        "metric": "new usable handle discoveries per million valid exposures, excluding pre-crawl-9 frame",
        "comparison": comparison.reset_index().to_dict("records"),
        "validation": "window bounds, denominators, nested counts, full-crawl audit reconciliation, and disjoint fifth totals passed",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / f"summary_{args.window // 1000}k.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(comparison.to_string())
    print("Validated and rendered linear moving-rate figures.")


if __name__ == "__main__":
    main()
