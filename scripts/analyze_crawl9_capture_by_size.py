"""Subscriber-band capture/recapture analysis from frozen, read-only crawl-9 results.

Reconcile new direct band queries with the original cumulative-threshold audit,
then render size, recapture and source-sensitivity figures without network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd


THRESHOLDS = [0, 1000, 10000, 100000, 1000000]
LABELS = ["0–999", "1k–<10k", "10k–<100k", "100k–<1m", "≥1m"]
FULL_LABELS = ["0", "1–9", "10–99", "100–999", *LABELS[1:]]
PRE_COLOR = "#1762a3"
NEW_COLOR = "#b66b2d"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_result(root, name, manifest):
    path = root / "results" / f"{name}.json"
    raw = path.read_bytes()
    result = json.loads(raw)
    require(result.get("status", {}).get("state") == "SUCCEEDED" and not result.get("error"),
            f"Unsuccessful source result: {name}")
    require(not result.get("manifest", {}).get("truncated"), f"Truncated source: {name}")
    manifest.append({"file": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
                     "statement_id": result.get("statement_id"), "started_at": result.get("started_at")})
    frame = pd.DataFrame(result["rows"])
    for col in frame:
        if col not in ("scenario", "sample_group"):
            frame[col] = pd.to_numeric(frame[col], errors="raise")
    return frame


def bands(frame):
    frame = frame.sort_index()
    require(frame.index.tolist() == THRESHOLDS, "Unexpected threshold grid")
    result = (frame - frame.shift(-1).fillna(0)).astype("int64")
    require((result >= 0).all().all(), "Negative differenced count")
    reconstructed = result.iloc[::-1].cumsum().iloc[::-1]
    require(np.array_equal(reconstructed.to_numpy(), frame.to_numpy()), "Threshold reconstruction failed")
    return result


def save(fig, out, name):
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(out / f"{name}.{suffix}", dpi=180, facecolor="white")
    plt.close(fig)


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#bdc7cf", "axes.labelcolor": "#34414d",
        "xtick.color": "#465361", "ytick.color": "#465361",
        "svg.fonttype": "none", "pdf.fonttype": 42,
    })


def setup_axis(ax, title, ylabel, percent=False, labels=LABELS):
    ax.set_title(title, loc="left", fontsize=12, weight="bold", color="#243849", pad=15)
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
    ax.set_xlabel("Subscribers per channel", labelpad=12)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#e5eaf0", lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(-0.25, len(labels) - 0.75)
    if percent:
        ax.yaxis.set_major_formatter(PercentFormatter(100))


def plot_primary(data, out):
    style()
    pre = data[(data.pre_seed == 1) & (data.size_band >= 0)].sort_values("size_band")
    new = data[(data.pre_seed == 0) & (data.size_band >= 0)].sort_values("size_band")
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))
    fig.subplots_adjust(left=0.065, right=0.98, top=0.71, bottom=0.30, wspace=0.36)
    fig.text(0.065, 0.925, "Crawl 9: subscriber size and capture / recapture", fontsize=22,
             weight="bold", color="#203344")
    fig.text(0.065, 0.867, "Disjoint subscriber bands  |  Valid link exposures, 10–28 Sep 2026  |  Linear y-axes",
             fontsize=11, color="#536372")
    fig.legend(handles=[Line2D([0], [0], color=PRE_COLOR, marker="o", lw=2,
                               label="Known before crawl 9"),
                        Line2D([0], [0], color=NEW_COLOR, marker="o", lw=2,
                               label="Newly registered during crawl 9")],
               loc="upper left", bbox_to_anchor=(0.06, 0.831), ncol=2, frameon=False)
    x = np.arange(8)
    setup_axis(axes[0], "Captured at least once", "% of pre-crawl inventory", percent=True, labels=FULL_LABELS)
    axes[0].plot(x, pre.capture_pct, "o-", color=PRE_COLOR, lw=2.3)
    for i, value in enumerate(pre.capture_pct):
        axes[0].annotate(f"{value:.1f}%", (i, value), xytext=(0, 8), textcoords="offset points",
                         ha="center", fontsize=9, color=PRE_COLOR)
    axes[0].set_ylim(0, 45)
    setup_axis(axes[1], "Recaptured in ≥2 chain IDs", "% of captured handles", percent=True, labels=FULL_LABELS)
    setup_axis(axes[2], "Repeat-capture frequency", "Mean distinct chain IDs per captured handle", labels=FULL_LABELS)
    for subset, color in [(pre, PRE_COLOR), (new, NEW_COLOR)]:
        axes[1].plot(x, subset.recapture_pct, "o-", color=color, lw=2.3)
        axes[2].plot(x, subset.mean_chains_captured, "o-", color=color, lw=2.3)
    axes[1].set_ylim(0, 100)
    axes[2].set_ylim(0, max(data.mean_chains_captured) * 1.2)
    axes[1].annotate("22 captured", (7, new.recapture_pct.iloc[-1]), xytext=(-3, -18),
                     textcoords="offset points", ha="right", fontsize=8.5, color=NEW_COLOR)
    for ax in axes:
        ax.axvline(3.5, color="#b5bec7", lw=0.8, ls=":")
    fig.text(0.065, 0.135,
             "Capture: at least one valid exposure. Recapture: detected in at least two distinct recorded chain IDs; within-chain repeats count once.",
             fontsize=9, color="#536372")
    fig.text(0.065, 0.097,
             "Capture denominator: usable handles registered before crawl 9. New channels appear only in conditional recapture panels; discovery timing differs.",
             fontsize=9, color="#536372")
    fig.text(0.065, 0.059,
             "Four handles with unknown size are omitted. Subscriber bands use the frozen export's counts; recorded chain effort is unequal and independence is unverified.",
             fontsize=9, color="#536372")
    save(fig, out, "subscriber_capture_recapture")


def plot_sensitivity(data, out):
    style()
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))
    fig.subplots_adjust(left=0.065, right=0.98, top=0.68, bottom=0.30, wspace=0.35)
    fig.text(0.065, 0.925, "How much do the two major link sources matter?", fontsize=20,
             weight="bold", color="#203344")
    fig.text(0.065, 0.864, "Crawl 9 subscriber bands  |  Same pre-crawl inventory throughout  |  Linear y-axes",
             fontsize=11, color="#536372")
    setup_axis(axes[0], "Capture of pre-crawl inventory", "% of pre-crawl inventory", percent=True, labels=FULL_LABELS)
    setup_axis(axes[1], "Recapture: previously known", "% of captured handles", percent=True, labels=FULL_LABELS)
    setup_axis(axes[2], "Recapture: newly registered", "% of captured handles", percent=True, labels=FULL_LABELS)
    styles = [("all_sources", "All sources", PRE_COLOR, "-"),
              ("without_fragment", "Exclude fragment_monitor", "#8a8f94", "--"),
              ("without_two_hubs", "Exclude both major sources", "#168676", "-")]
    for scenario, label, color, line in styles:
        part = data[(data.scenario == scenario) & (data.size_band >= 0)].sort_values("size_band")
        pre, new = part[part.pre_seed == 1], part[part.pre_seed == 0]
        axes[0].plot(range(8), pre.capture_pct, marker="o", ls=line, color=color, lw=2, label=label)
        axes[1].plot(range(8), pre.recapture_pct, marker="o", ls=line, color=color, lw=2)
        axes[2].plot(range(8), new.recapture_pct, marker="o", ls=line, color=color, lw=2)
    axes[0].set_ylim(0, 45)
    axes[1].set_ylim(0, 100)
    axes[2].set_ylim(0, 100)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(0.06, 0.821),
               ncol=3, frameon=False, fontsize=9.5)
    fig.text(0.065, 0.105,
             "The two sources are fragment_monitor and lelang_username. Exclusions are sensitivity checks, not corrected crawl estimates.",
             fontsize=9, color="#536372")
    fig.text(0.065, 0.065,
             "Recapture panels condition on handles still captured after exclusion, so their denominators change. Newly registered ≥1m handles: 22 → 16.",
             fontsize=9, color="#536372")
    save(fig, out, "subscriber_capture_source_sensitivity")


def plot_fine(data, out):
    style()
    all_sources = data[(data.scenario == "all_sources") & (data.half_decade > 0)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.6))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.71, bottom=0.27, wspace=0.23)
    fig.text(0.08, 0.93, "A closer look across subscriber size", fontsize=21, weight="bold", color="#203344")
    fig.text(0.08, 0.875, "Half-decade bins, points at cohort median size  |  Log x-axis; linear y-axes", color="#536372")
    for pre_seed, color, label in [(1, PRE_COLOR, "Known before crawl 9"),
                                   (0, NEW_COLOR, "Newly registered during crawl 9")]:
        part = all_sources[all_sources.pre_seed == pre_seed].sort_values("half_decade")
        if pre_seed:
            axes[0].plot(part.median_members, part.capture_pct, "o-", color=color, lw=2)
        axes[1].plot(part.median_members, part.recapture_pct, "o-", color=color, lw=2, label=label)
        for row in part.itertuples():
            if row.captured < 30:
                axes[1].annotate(f"n={row.captured}", (row.median_members, row.recapture_pct),
                                 xytext=(0, 9 if pre_seed else -17), textcoords="offset points",
                                 fontsize=8, ha="center", color=color)
            if pre_seed and row.eligible_handles < 100:
                axes[0].annotate(f"N={row.eligible_handles}", (row.median_members, row.capture_pct),
                                 xytext=(0, 9), textcoords="offset points", fontsize=8, ha="center", color=color)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks([1, 10, 100, 1000, 10000, 100000, 1000000, 10000000],
                      ["1", "10", "100", "1k", "10k", "100k", "1m", "10m"])
        ax.set_xlabel("Subscribers per channel (log scale)")
        ax.yaxis.set_major_formatter(PercentFormatter(100))
        ax.grid(axis="y", color="#e5eaf0")
        ax.set_axisbelow(True)
    axes[0].set_ylim(0, 70)
    axes[1].set_ylim(0, 105)
    axes[0].set_title("Captured at least once", loc="left", weight="bold", pad=12)
    axes[1].set_title("Recaptured in ≥2 chain IDs", loc="left", weight="bold", pad=12)
    axes[0].set_ylabel("% of pre-crawl inventory")
    axes[1].set_ylabel("% of captured handles")
    fig.legend(*axes[1].get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(0.075, 0.834),
               ncol=2, frameon=False)
    fig.text(0.08, 0.13, "N = pre-crawl inventory; n = captured handles. Sparse upper bins are labeled. Lines connect observed bin summaries; no fitted model.",
             fontsize=9, color="#536372")
    fig.text(0.08, 0.087, "Zero-subscriber and unknown-size handles are omitted here; zero-subscriber results appear in the main figure. Bins have unequal counts.",
             fontsize=9, color="#536372")
    fig.text(0.08, 0.044, "Crawl 9, 10–28 Sep 2026, fixed Delta versions. Chain effort is unequal; newly registered handles differ in time available for recapture.",
             fontsize=9, color="#536372")
    save(fig, out, "subscriber_capture_fine_bins")


def process_direct_results(root, combined, sensitivity, manifest, out):
    direct = read_result(root, "size_band_capture", manifest)
    fine = read_result(root, "fine_size_capture", manifest)
    associations = read_result(root, "subscriber_incidence_association", manifest)
    counts = ["eligible_handles", "captured", "recaptured", "q1", "q2", "chain_incidences"]
    for frame in [direct, fine]:
        require((frame[counts] >= 0).all().all(), "Negative direct count")
        require((frame.captured <= frame.eligible_handles).all(), "Direct capture exceeds frame")
        require((frame.recaptured == frame.captured - frame.q1).all(), "Recapture is not D-Q1")
        require((frame.q2 <= frame.recaptured).all(), "Q2 exceeds recaptures")
        require(np.allclose(frame.mean_chains_captured, frame.chain_incidences / frame.captured, equal_nan=True),
                "Mean chain count does not reconcile")
        frame["capture_pct"] = 100 * frame.captured / frame.eligible_handles
        frame["recapture_pct"] = 100 * frame.recaptured / frame.captured
        frame["mean_chains_per_registered_handle"] = frame.chain_incidences / frame.eligible_handles
    direct["band"] = direct.size_band.map({-1: "Unknown", **dict(enumerate(FULL_LABELS))})
    direct["multiple_source_pct"] = 100 * direct.captured_from_multiple_sources / direct.captured
    direct["coarse_threshold"] = direct.size_band.map({0: 0, 1: 0, 2: 0, 3: 0, 4: 1000,
                                                      5: 10000, 6: 100000, 7: 1000000})
    coarse = direct[direct.size_band >= 0].groupby(["scenario", "pre_seed", "coarse_threshold"])[counts].sum()
    for row in combined.itertuples():
        matched = coarse.loc[("all_sources", row.pre_seed, row.threshold)]
        expected = [row.registered, row.observed, row.recaptured, row.q1, row.q2, row.incidence_total]
        require(np.array_equal(matched.to_numpy(), expected), "New direct query disagrees with earlier audit")
    for row in sensitivity.itertuples():
        old, new = [coarse.loc[(row.scenario, p, row.threshold)] for p in [1, 0]]
        require(old.captured == row.pre_captured and new.captured == row.new_captured
                and new.q1 == row.new_q1 and new.q2 == row.new_q2,
                "Source-exclusion queries disagree with earlier audit")
    fine["size_band"] = fine.half_decade.map(lambda b: b if b <= 0 else min(7, (int(b) + 1) // 2))
    regrouped = fine.groupby(["scenario", "pre_seed", "size_band"])[counts].sum().sort_index()
    expected = direct.set_index(["scenario", "pre_seed", "size_band"])[counts].sort_index()
    pd.testing.assert_frame_equal(regrouped, expected, check_dtype=False)
    all_sources = direct[direct.scenario == "all_sources"]
    require(all_sources.eligible_handles.sum() == 612589, "Registry total differs from frozen audit")
    require(all_sources.captured.sum() == 205610, "Captured total differs from frozen audit")
    for row in associations.itertuples():
        part = all_sources[(all_sources.size_band >= (1 if row.min_members == 1 else 4))
                           & (all_sources.pre_seed == (0 if row.sample_group == "new_captured" else 1))]
        require(row.handles == (part.eligible_handles.sum() if row.sample_group == "pre_frame" else part.captured.sum()),
                "Rank-correlation cohort does not reconcile")
        require(row.captured == part.captured.sum(), "Rank-correlation capture total differs")
    correlations = associations.filter(like="spearman").stack()
    require(correlations.between(-1, 1).all(), "Invalid correlation")
    direct.to_csv(out / "subscriber_size_bands_all_scenarios.csv", index=False)
    fine.to_csv(out / "subscriber_half_decade_bands.csv", index=False)
    associations.to_csv(out / "subscriber_rank_correlations.csv", index=False)
    plot_primary(all_sources, out)
    plot_sensitivity(direct, out)
    plot_fine(fine, out)
    return associations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--audit-root", type=Path, default=Path("outputs/crawl9_2026-09-29"))
    args = parser.parse_args()
    out = args.root / "analysis"
    out.mkdir(exist_ok=True)
    manifest = []
    raw = read_result(args.audit_root, "incidence_raw", manifest)
    inv = read_result(args.audit_root, "threshold_inventory", manifest).set_index("threshold")
    hubs = read_result(args.audit_root, "hub_incidence_sensitivity", manifest)
    removed = read_result(args.audit_root, "source_removal_sensitivity", manifest).set_index("threshold")
    inventory = bands(inv[["pre_crawl_membership", "added_during_crawl9"]])
    cohorts = []
    for pre_seed in (1, 0):
        counted = raw[raw.pre_seed == pre_seed].set_index("threshold")
        part = bands(counted[["observed", "q1", "q2", "incidence_total"]])
        part["registered"] = inventory["pre_crawl_membership" if pre_seed else "added_during_crawl9"]
        part["pre_seed"] = pre_seed
        part["recaptured"] = part.observed - part.q1
        part["q3plus"] = part.observed - part.q1 - part.q2
        require((part.q3plus >= 0).all(), "Invalid incidence categories")
        require((part.observed <= part.registered).all(), "Captures exceed registry cohort")
        part["capture_pct"] = 100 * part.observed / part.registered
        part["recapture_pct"] = 100 * part.recaptured / part.observed
        part["mean_chains_captured"] = part.incidence_total / part.observed
        part["mean_chains_per_registered_handle"] = part.incidence_total / part.registered
        part["band"] = LABELS
        cohorts.append(part.reset_index())
    combined = pd.concat(cohorts, ignore_index=True)
    combined.to_csv(out / "subscriber_band_capture_recapture.csv", index=False)
    sensitivity = []
    for scenario, exclusion in [("all_sources", None), ("without_fragment", "exclusive_fragment"),
                                 ("without_two_hubs", "exclusive_top2")]:
        new_counts = hubs[hubs.scenario == scenario].set_index("threshold")[["observed", "q1", "q2"]]
        all_captured = removed.observed - (removed[exclusion] if exclusion else 0)
        pre_captured = (all_captured - new_counts.observed).to_frame("pre_captured")
        old_bands = bands(pre_captured)
        new_bands = bands(new_counts)
        for t, label in zip(THRESHOLDS, LABELS):
            sensitivity.append({"scenario": scenario, "threshold": t, "band": label,
                                "pre_registered": int(inventory.loc[t, "pre_crawl_membership"]),
                                "pre_captured": int(old_bands.loc[t, "pre_captured"]),
                                "pre_capture_pct": float(100 * old_bands.loc[t, "pre_captured"] / inventory.loc[t, "pre_crawl_membership"]),
                                "new_captured": int(new_bands.loc[t, "observed"]),
                                "new_q1": int(new_bands.loc[t, "q1"]),
                                "new_q2": int(new_bands.loc[t, "q2"]),
                                "new_recapture_pct": float(100 * (new_bands.loc[t, "observed"] - new_bands.loc[t, "q1"]) / new_bands.loc[t, "observed"])})
    sensitivity = pd.DataFrame(sensitivity)
    pre = combined[combined.pre_seed == 1].set_index("threshold")
    require(np.array_equal(sensitivity[sensitivity.scenario == "all_sources"].pre_captured,
                           pre.observed), "Source decomposition does not reproduce pre-frame counts")
    sensitivity.to_csv(out / "source_sensitivity_by_band.csv", index=False)
    associations = process_direct_results(args.root, combined, sensitivity, manifest, out)
    summary = {
        "analysis_date": "2026-09-30", "snapshot": "2026-09-28 fixed export, same as prior audit",
        "basis": "Direct subscriber-band queries, finer bins and exact tie-adjusted channel-level rank correlations; reconciled with original audit",
        "capture_unit": "valid exposure target, presence in distinct recorded chain IDs",
        "pre_frame_known_member_count": int(pre.registered.sum()),
        "pre_frame_captured": int(pre.observed.sum()),
        "pre_frame_capture_pct": float(100 * pre.observed.sum() / pre.registered.sum()),
        "capture_fraction_ratio_ge1m_vs_lt1k": float(pre.loc[1000000, "capture_pct"] / pre.loc[0, "capture_pct"]),
        "mean_chain_ratio_ge1m_vs_1k_to10k": float(pre.loc[1000000, "mean_chains_captured"] / pre.loc[1000, "mean_chains_captured"]),
        "checks": "Successful untruncated results; exact cumulative reconstruction; nonnegative counts; cohort bounds; source decomposition; direct vs original audit; fine vs broad bins; rank-correlation cohort counts",
        "rank_correlations": json.loads(associations.to_json(orient="records")),
        "query_history": "First attempt denied by IP ACL; failures preserved in results/blocked_attempt. After the connection was restored, all three queries succeeded.",
        "limits": ["Current subscriber snapshot and current usability", "Handle identities", "Unequal recorded-chain effort and unverified independent chains", "New-cohort discovery time affects recapture opportunity", "Rates refer to the known frame, not all Telegram"]
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "input_provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(combined.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
