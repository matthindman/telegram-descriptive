"""Analyze the 2026-09-29 aggregate audit without modifying Databricks data.

These are exploratory diagnostics. No burn-in or independence certification is
inferred, and no production estimator defaults are changed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import xlogy

from telegram_descriptive.estimation.chao import chao2_from_counts
from telegram_descriptive.estimation.saturation import fit_simple_saturation


def read_result(root, name):
    result = json.loads((root / "results" / f"{name}.json").read_text())
    if result.get("error") or result.get("status", {}).get("state") != "SUCCEEDED":
        raise ValueError(f"Cannot analyze unsuccessful query {name}")
    return pd.DataFrame(result["rows"])


def numeric(frame, columns):
    frame = frame.copy()
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def deviance(y, mu):
    mu = np.maximum(np.asarray(mu, dtype=float), 1e-12)
    y = np.asarray(y, dtype=float)
    return float(2 * np.sum(xlogy(y, y / mu) - y + mu))


def model_weights(edges, log_tau, beta):
    # Effort is measured in millions of valid, within-visit deduplicated exposures.
    z = np.power(np.asarray(edges, dtype=float) / np.exp(log_tau), beta)
    return np.exp(-z[:-1]) * -np.expm1(-np.diff(z))


def fit_increments(edges, y, model):
    """Profile amplitude; fit discovery increments, not cumulative residuals.

    Poisson deviance is used as a predictive scoring rule. The dependent crawl
    observations do not justify interpreting this as an independent likelihood
    for uncertainty intervals. Bounds are numerical search bounds, not priors.
    """
    y = np.asarray(y, dtype=float)
    edges = np.asarray(edges, dtype=float)
    if y.sum() == 0:
        return {"model": model, "amplitude": 0.0, "tau": None, "beta": None,
                "flags": ["no_training_discoveries"], "training_deviance": 0.0}
    if model == "constant_rate":
        rate = float(y.sum() / (edges[-1] - edges[0]))
        return {"model": model, "rate": rate, "flags": [],
                "training_deviance": deviance(y, rate * np.diff(edges))}

    def objective(params):
        beta = float(np.exp(params[1])) if model == "stretched_exponential" else 1.0
        weights = model_weights(edges, params[0], beta)
        amplitude = y.sum() / max(weights.sum(), 1e-300)
        mu = np.maximum(amplitude * weights, 1e-12)
        return float(np.sum(mu - xlogy(y, mu)))

    bounds = [(-12, 20)]
    starts = [[x] for x in (-2, 0, 2, 6, 14)]
    if model == "stretched_exponential":
        bounds.append((np.log(0.1), 0))
        starts = [[x, np.log(b)] for x in (-2, 0, 2, 6, 14) for b in (0.3, 0.7, 1.0)]
    candidates = [minimize(objective, guess, bounds=bounds, method="L-BFGS-B")
                  for guess in starts]
    best = min(candidates, key=lambda result: result.fun)
    beta = float(np.exp(best.x[1])) if model == "stretched_exponential" else 1.0
    weights = model_weights(edges, best.x[0], beta)
    amplitude = float(y.sum() / weights.sum())
    flags = []
    if not best.success:
        flags.append("optimizer_not_converged")
    if best.x[0] > 19.9:
        flags.append("asymptote_unidentified_upper_tau_boundary")
    if best.x[0] < -11.9:
        flags.append("tau_lower_search_boundary")
    if beta < 0.1001:
        flags.append("beta_lower_search_boundary")
    if y.sum() < 30:
        flags.append("sparse_discoveries")
    return {"model": model, "amplitude": amplitude, "tau": float(np.exp(best.x[0])),
            "beta": beta, "flags": flags,
            "training_deviance": deviance(y, amplitude * weights)}


def predict_increments(fit, edges):
    if fit["model"] == "constant_rate":
        return fit["rate"] * np.diff(edges)
    if fit["amplitude"] == 0:
        return np.zeros(len(edges) - 1)
    return fit["amplitude"] * model_weights(edges, np.log(fit["tau"]), fit["beta"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root
    out = root / "analysis"
    out.mkdir(exist_ok=True)
    inventory = numeric(read_result(root, "threshold_inventory"),
                        ["threshold", "current_usable", "pre_crawl_membership", "added_during_crawl9"])
    raw = numeric(read_result(root, "incidence_raw"),
                  ["threshold", "pre_seed", "observed", "q1", "q2", "incidence_total"])
    chains = numeric(read_result(root, "chain_efforts"), ["visits", "valid_exposures", "min_depth"])
    offsets = inventory.set_index("threshold").pre_crawl_membership.to_dict()
    chao_rows = []
    for row in raw[raw.pre_seed == 0].itertuples():
        m = len(chains)
        bound = chao2_from_counts(m, int(row.observed), int(row.q1), int(row.q2))
        chao_rows.append({"threshold": row.threshold, "recorded_chain_ids": m,
                          "offset": offsets[row.threshold], "observed_after_offset": row.observed,
                          "q1": row.q1, "q2": row.q2,
                          "chao2_mechanical_diagnostic": offsets[row.threshold] + bound,
                          "additional_chao2": bound - row.observed,
                          "jackknife1_mechanical_diagnostic": offsets[row.threshold] + row.observed
                          + row.q1 * (m - 1) / m,
                          "status": "exploratory_unequal_effort_no_burnin_unverified_independence"})
    chao = pd.DataFrame(chao_rows)
    chao.to_csv(out / "chao2_and_jackknife_diagnostics.csv", index=False)
    sensitivity = numeric(read_result(root, "equal_effort_sensitivity"),
                          ["effort", "samples", "threshold", "observed", "q1", "q2"])
    sensitivity["chao2_mechanical_diagnostic"] = [
        offsets[r.threshold] + chao2_from_counts(int(r.samples), int(r.observed), int(r.q1), int(r.q2))
        for r in sensitivity.itertuples()]
    sensitivity["status"] = "conditional_on_retained_chain_subset_not_a_full_population_bound"
    sensitivity.to_csv(out / "chain_effort_sensitivity.csv", index=False)

    hub = numeric(read_result(root, "hub_incidence_sensitivity"),
                  ["threshold", "observed", "q1", "q2"])
    hub["chao2_mechanical_diagnostic"] = [
        offsets[r.threshold] + chao2_from_counts(len(chains), int(r.observed), int(r.q1), int(r.q2))
        for r in hub.itertuples()]
    hub["status"] = "source_removal_changes_sampling_process_diagnostic_only"
    hub.to_csv(out / "hub_sensitivity.csv", index=False)
    canonical_inventory = numeric(read_result(root, "canonical_threshold_sensitivity"),
                                  ["threshold", "entities", "pre_crawl_entities", "new_entities"])
    canonical_offsets = canonical_inventory.set_index("threshold").pre_crawl_entities.to_dict()
    canonical = numeric(read_result(root, "canonical_incidence_sensitivity"),
                        ["threshold", "observed", "q1", "q2"])
    canonical["chao2_mechanical_diagnostic"] = [
        canonical_offsets[r.threshold] + chao2_from_counts(len(chains), int(r.observed), int(r.q1), int(r.q2))
        for r in canonical.itertuples()]
    canonical["status"] = "known_chat_ids_merged_max_member_count_across_aliases_sensitivity_only"
    canonical.to_csv(out / "canonical_identity_sensitivity.csv", index=False)
    canonical_inventory.to_csv(out / "canonical_threshold_inventory.csv", index=False)

    curves = numeric(read_result(root, "accumulation_bins"),
                     ["bin", "exposure_end", "threshold", "first_seen", "new_to_precrawl_frame"])
    curves["cumulative_new"] = curves.groupby("threshold").new_to_precrawl_frame.cumsum()
    curves["known_frame_curve"] = curves.cumulative_new + curves.threshold.map(offsets)
    curves.to_csv(out / "subscriber_accumulation.csv", index=False)
    daily = numeric(read_result(root, "daily_usable_additions"),
                    ["added", "added_ge_1k", "added_ge_10k", "added_ge_100k", "added_ge_1m"])
    daily.to_csv(out / "daily_usable_additions.csv", index=False)
    inventory.to_csv(out / "threshold_inventory.csv", index=False)
    fits = []
    legacy = []
    comparisons = []
    for threshold, rows in curves.groupby("threshold"):
        edges = np.r_[0, rows.exposure_end.to_numpy() / 1e6]
        y = rows.new_to_precrawl_frame.to_numpy()
        split = int(np.floor(len(y) * 0.8))
        for model in ("constant_rate", "simple_exponential", "stretched_exponential"):
            train = fit_increments(edges[:split + 1], y[:split], model)
            heldout = predict_increments(train, edges[split:])
            full = fit_increments(edges, y, model)
            fits.append({"threshold": int(threshold), "model": model, "training_bins": split,
                         "heldout_bins": len(y) - split, "heldout_observed": int(y[split:].sum()),
                         "heldout_predicted": float(heldout.sum()),
                         "heldout_poisson_deviance": deviance(y[split:], heldout),
                         "training_fit": train, "full_fit": full,
                         "full_offset_plus_asymptote": float(offsets[threshold] + full["amplitude"])
                         if "amplitude" in full else None})
        legacy.append({"threshold": int(threshold), "fit": asdict(fit_simple_saturation(edges[1:], np.cumsum(y))),
                       "status": "existing_cumulative_fitter_replay_only_not_used_for_model_selection"})
        first = rows[rows.exposure_end <= 1e6]
        last = rows[rows.bin >= 45]
        last_effort = float(rows.exposure_end.max() - 4.4e6)
        comparisons.append({"threshold": int(threshold), "first_million_new": int(first.new_to_precrawl_frame.sum()),
                            "last_975849_exposures_new": int(last.new_to_precrawl_frame.sum()),
                            "last_window_exposures": last_effort,
                            "first_per_100k": float(first.new_to_precrawl_frame.sum() / 10),
                            "last_per_100k": float(last.new_to_precrawl_frame.sum() / last_effort * 1e5)})
    (out / "increment_saturation_fits.json").write_text(json.dumps(fits, indent=2) + "\n")
    (out / "existing_saturation_helper_replay.json").write_text(json.dumps(legacy, indent=2) + "\n")
    pd.DataFrame(comparisons).to_csv(out / "early_late_discovery_yield.csv", index=False)

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.3), dpi=180)
    for ax, threshold in zip(axes.flat, (1000, 10000, 100000, 1000000)):
        rows = curves[curves.threshold == threshold]
        x = np.r_[0, rows.exposure_end / 1e6]
        y = np.r_[offsets[threshold], rows.known_frame_curve]
        ax.plot(x, y, color="#12636d", linewidth=2.3)
        ax.scatter([x[-1]], [y[-1]], color="#12636d", s=25)
        ax.set_title(f"≥ {threshold:,} subscribers", loc="left", fontweight="bold")
        ax.set_xlabel("Cumulative valid exposures (millions)")
        ax.set_ylabel("Known handles: pre-crawl frame + discoveries")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
        ax.grid(alpha=0.18)
        added = int(rows.new_to_precrawl_frame.sum())
        ax.text(0.04, 0.91, f"+{added:,} discovered in crawl 9", transform=ax.transAxes,
                color="#12636d", fontsize=11)
    fig.suptitle("Telegram crawl 9: discovery continues across subscriber thresholds",
                 fontsize=16, fontweight="bold", x=0.07, ha="left")
    fig.text(0.07, 0.925, "September 10–28, 2026 · Subscriber size and usability classified at the September 28 export",
             fontsize=10, color="#444444")
    fig.text(0.07, 0.015, "Empirical accumulation, not a population estimate. Panels use different vertical scales.\n"
             "Counts are usable handles; known chat-ID aliases are analyzed separately. Four registry subscriber counts are unknown.",
             fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    fig.savefig(out / "subscriber_discovery_curves.png")
    fig.savefig(out / "subscriber_discovery_curves.svg")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.3), dpi=180)
    for ax, threshold in zip(axes.flat, (1000, 10000, 100000, 1000000)):
        rows = curves[curves.threshold == threshold]
        edges = np.r_[0, rows.exposure_end.to_numpy()]
        rate = rows.new_to_precrawl_frame.to_numpy() / np.diff(edges) * 1e5
        ax.bar((edges[1:] + edges[:-1]) / 2e6, rate, width=np.diff(edges) / 1e6 * 0.9,
               color="#337d86", alpha=0.85)
        ax.set_title(f"≥ {threshold:,} subscribers", loc="left", fontweight="bold")
        ax.set_xlabel("Cumulative valid exposures (millions)")
        ax.set_ylabel("New handles per 100,000 valid exposures")
        ax.grid(axis="y", alpha=0.18)
    fig.suptitle("Discovery yield is uneven; a flat final population is not established",
                 fontsize=16, fontweight="bold", x=0.07, ha="left")
    fig.text(0.07, 0.015, "100,000-exposure bins; final partial bin normalized by its actual effort.\n"
             "Latest-snapshot subscriber classification; pre-crawl members excluded from new discoveries.",
             fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(out / "subscriber_discovery_yield.png")
    plt.close(fig)

    diagnostics = {"formal_population_claim_enabled": False, "recorded_chain_ids": len(chains),
                   "zero_valid_exposure_chain_ids": int((chains.valid_exposures == 0).sum()),
                   "common_effort_all_chains": int(chains.valid_exposures.min()),
                   "chain_ids_starting_at_depth_zero": int((chains.min_depth == 0).sum()),
                   "flags": ["no_verified_burnin", "independent_sampling_units_unconfirmed",
                             "fixed_lookback_not_recorded_in_export",
                             "exposure_time_subscribers_missing_using_latest_registry",
                             "zero_common_effort_all_recorded_chains", "no_validated_confidence_intervals"]}
    (out / "inference_gates.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    print(chao.to_string(index=False))
    print(pd.DataFrame([{k: f[k] for k in ("threshold", "model", "heldout_observed", "heldout_predicted",
                                          "heldout_poisson_deviance", "full_offset_plus_asymptote")}
                        for f in fits]).to_string(index=False))


if __name__ == "__main__":
    main()
