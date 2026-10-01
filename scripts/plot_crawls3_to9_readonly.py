"""Plot cumulative discoveries from frozen, read-only crawl 3–9 SQL aggregates.

The starting frame is reconstructed at crawl 3's recorded start. Subscriber
counts and usability are retrospective classifications from the fixed export.
This script does not fit a pooled population model or change estimator defaults.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator, NullLocator
import numpy as np
import pandas as pd


THRESHOLDS = (1000, 10000, 100000, 1000000)
COLORS = {
    3: "#b55b3c", 4: "#8064a2", 5: "#898989", 6: "#b08c00",
    7: "#258f7e", 8: "#637b95", 9: "#1762a3",
}


def read_result(root, name, numeric):
    result = json.loads((root / "results" / f"{name}.json").read_text())
    if result.get("error") or result.get("status", {}).get("state") != "SUCCEEDED":
        raise ValueError(f"Unsuccessful query: {name}")
    if result.get("manifest", {}).get("truncated"):
        raise ValueError(f"Truncated query: {name}")
    frame = pd.DataFrame(result["rows"])
    for col in numeric:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    return frame


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save_figure(fig, out, name):
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(out / f"{name}.{suffix}", dpi=180, facecolor="white")
    plt.close(fig)


def make_figure(curves, inventory, out, milestones=False, log_y=False):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#c3c9ce", "axes.labelcolor": "#34414d",
        "xtick.color": "#465361", "ytick.color": "#465361",
        "svg.fonttype": "none", "pdf.fonttype": 42,
    })
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.4), sharex=True)
    fig.subplots_adjust(left=0.10, right=0.92, top=0.78, bottom=0.18,
                        hspace=0.34, wspace=0.26)
    title = ("Channels known after each crawl" if milestones else
             "Telegram discovery across crawls 3–9")
    fig.text(0.10, 0.94, title, fontsize=21, weight="bold", color="#203344")
    fig.text(0.10, 0.895,
             ("Logarithmic y axes  |  Same proportional range in each panel  |  13 Aug–28 Sep 2026"
              if log_y else
              "Starting inventory + unique subsequent discoveries  |  13 Aug–28 Sep 2026"),
             fontsize=11, color="#536372")
    handles = [Line2D([0], [0], color=COLORS[n], lw=3, label=f"Crawl {n}")
               for n in range(3, 10)]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.094, 0.868),
               ncol=7, frameon=False, handlelength=1.6, columnspacing=1.5)

    # Equal log spans make equal proportional increases equally tall in all panels.
    common_log_span = max(
        np.log(curves[curves.threshold == threshold].known_handles.iloc[-1]
               / inventory.loc[threshold, "initial_frame"])
        for threshold in THRESHOLDS
    )
    for ax, threshold in zip(axes.flat, THRESHOLDS):
        data = curves[curves.threshold == threshold].sort_values("exposure_end")
        offset = int(inventory.loc[threshold, "initial_frame"])
        ax.set_title(f"≥ {threshold:,} subscribers", loc="left", fontsize=12,
                     weight="bold", pad=10, color="#243849")
        ax.grid(axis="y", color="#e6eaee", lw=0.8)
        ax.set_axisbelow(True)
        if log_y:
            ax.set_yscale("log")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
        previous_x, previous_y = (2 if milestones else 0), offset
        ax.plot(previous_x, previous_y, "o", color="#536372", ms=4, zorder=4)
        for crawl in range(3, 10):
            part = data[data.crawl == crawl]
            if milestones:
                x = np.array([previous_x, crawl])
                y = np.array([previous_y, int(part.known_handles.iloc[-1])])
            else:
                x = np.r_[previous_x, part.exposure_end.to_numpy() / 1e6]
                y = np.r_[previous_y, part.known_handles.to_numpy()]
            ax.plot(x, y, color=COLORS[crawl], lw=2.4, solid_capstyle="round")
            ax.plot(x[-1], y[-1], "o", color=COLORS[crawl], ms=4.5, zorder=4)
            previous_x, previous_y = x[-1], y[-1]

        ax.annotate(f"{previous_y:,.0f}", (previous_x, previous_y), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=10,
                    weight="bold", color=COLORS[9], annotation_clip=False)
        span = max(previous_y - offset, 1)
        if log_y:
            lower = offset * np.exp(-0.08 * common_log_span)
            upper = offset * np.exp(1.13 * common_log_span)
            ax.set_ylim(lower, upper)
            # Label ordinary counts at their logarithmic positions; the observed
            # ranges are less than one decade, so powers-of-ten ticks are sparse.
            ticks = MaxNLocator(nbins=5, integer=True).tick_values(lower, upper)
            ax.yaxis.set_major_locator(FixedLocator(ticks[(ticks >= lower) & (ticks <= upper)]))
            ax.yaxis.set_minor_locator(NullLocator())
        else:
            ax.set_ylim(offset - span * 0.08, previous_y + span * 0.13)
        if milestones:
            ax.set_xlim(1.8, 9.65)
            ax.set_xticks(range(2, 10), ["Before\n3", "3", "4", "5", "6", "7", "8", "9"])
        else:
            ax.set_xlim(-0.07, previous_x * 1.105)
            ax.set_xticks(range(8))
            start9 = int(data[data.crawl == 9].exposure_start.min()) - 1
            ax.axvline(start9 / 1e6, color=COLORS[9], lw=0.8, ls=":", alpha=0.6)
            ax.text(start9 / 1e6 + 0.08, 0.96, "Crawl 9 begins", va="top",
                    transform=ax.get_xaxis_transform(), color=COLORS[9], fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("Known channel handles (log scale)" if log_y else "Known channel handles")
    for ax in axes[-1]:
        ax.set_xlabel("End of crawl (unequal amounts of effort)" if milestones else
                      "Cumulative valid link exposures (millions)", labelpad=9)

    fig.text(0.10, 0.070,
             "Each handle is counted once across crawls. Initial inventory predates crawl 3; size and usability use the fixed September export.",
             fontsize=8.5, color="#536372")
    fig.text(0.10, 0.044,
             "Crawl 3 used new_only; crawls 4–9 used all_valid. These observed curves do not establish population completeness.",
             fontsize=8.5, color="#536372")
    name = "crawl_end_inventory" if milestones else "subscriber_saturation_crawls3_to9"
    save_figure(fig, out, name + ("_log_y" if log_y else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--include-log-variants", action="store_true",
                        help="Also render the optional log-y figures; linear axes are the default")
    args = parser.parse_args()
    out = args.root / "analysis"
    out.mkdir(exist_ok=True)

    inventory_columns = ["threshold", "current_usable", "initial_frame", "added_after_start",
                         "missing_insert_time", "ever_valid_exposed", "exposed_new_to_initial_frame",
                         "poststart_without_valid_exposure"]
    inventory = read_result(args.root, "initial_frame_inventory", inventory_columns).set_index("threshold")
    bins = read_result(args.root, "selected_run_accumulation_bins",
                       ["bin", "exposure_start", "exposure_end", "valid_exposures", "threshold",
                        "first_seen_usable", "new_to_initial_frame", "first_seen_valid"])
    audit = read_result(args.root, "selected_run_grain_audit",
                        ["rows", "valid_rows", "valid_missing_key", "valid_duplicate_batch_target"])
    bins["crawl"] = bins.crawl_id.str.rsplit("-", n=1).str[-1].astype(int)
    bins = bins.sort_values(["threshold", "exposure_end"]).reset_index(drop=True)
    require(set(bins.crawl) == set(range(3, 10)), "Expected all seven selected crawls")
    require(not audit.valid_missing_key.any(), "Missing valid-exposure keys")
    require(not audit.valid_duplicate_batch_target.any(), "Duplicate within-run exposure keys")
    require(not inventory.missing_insert_time.any(), "Missing registry insertion times")

    for threshold, group in bins.groupby("threshold"):
        require(group.exposure_end.tolist() == group.valid_exposures.cumsum().tolist(),
                "Exposure indices are not contiguous in bin order")
        require((group.exposure_start.to_numpy() == np.r_[1, group.exposure_end.to_numpy()[:-1] + 1]).all(),
                "Overlapping or missing bin boundaries")
        require(int(group.valid_exposures.sum()) == int(audit.valid_rows.sum()), "Exposure totals disagree")
        require(int(group.first_seen_usable.sum()) == int(inventory.loc[threshold, "ever_valid_exposed"]),
                "Distinct eligible discoveries do not reconcile")
        require(int(group.new_to_initial_frame.sum()) == int(inventory.loc[threshold, "exposed_new_to_initial_frame"]),
                "New discoveries do not reconcile")
    bins["cumulative_discoveries"] = bins.groupby("threshold").new_to_initial_frame.cumsum()
    bins["known_handles"] = bins.threshold.map(inventory.initial_frame) + bins.cumulative_discoveries
    bins["cumulative_exposed_usable"] = bins.groupby("threshold").first_seen_usable.cumsum()
    bins["cumulative_exposed_valid"] = bins.groupby("threshold").first_seen_valid.cumsum()
    bins.to_csv(out / "accumulation_bins.csv", index=False)
    inventory.to_csv(out / "frame_inventory.csv")

    endpoints = bins.groupby(["threshold", "crawl"], as_index=False).agg(
        exposure_start=("exposure_start", "min"), exposure_end=("exposure_end", "max"),
        valid_exposures=("valid_exposures", "sum"), new_handles=("new_to_initial_frame", "sum"),
        known_handles=("known_handles", "last"), first_time=("first_time", "min"), last_time=("last_time", "max"),
    )
    endpoints["new_per_100k_valid_exposures"] = endpoints.new_handles / endpoints.valid_exposures * 100000
    endpoints.to_csv(out / "crawl_endpoints.csv", index=False)
    summary = {
        "date": "2026-09-29", "selected_crawls": list(range(3, 10)),
        "source_schema": "qa_catalog.telegram_link_exposure_9",
        "initial_frame_cutoff_utc": "2026-08-13T00:36:12.229Z",
        "valid_exposures": int(audit.valid_rows.sum()),
        "distinct_valid_targets": int(bins[bins.threshold == 0].first_seen_valid.sum()),
        "bin_size_within_crawl": 25000,
        "classification": "fixed export member_count and usability; handle identifiers",
        "checks": "Complete exposure keys, no within-run batch-target duplicates, contiguous bins, independent inventory reconciliation passed",
        "thresholds": inventory.reset_index().to_dict("records"),
        "limitations": [
            "Current subscriber counts and usability, not historical states",
            "Handle deduplication; incomplete stable chat IDs prevent complete entity deduplication",
            "Different crawl modes and unverified independent effort units; no pooled saturation fit or completeness estimate",
            "Poststart registry additions with no valid selected-run exposure are excluded from discovery increments",
            "Snapshot versions fixed to the initial crawl-9 report; remote data unchanged",
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    make_figure(bins, inventory, out)
    make_figure(bins, inventory, out, milestones=True)
    if args.include_log_variants:
        make_figure(bins, inventory, out, log_y=True)
        make_figure(bins, inventory, out, milestones=True, log_y=True)
    print(json.dumps(summary, indent=2))
    print(endpoints.pivot(index="crawl", columns="threshold", values="new_handles").to_string())


if __name__ == "__main__":
    main()
