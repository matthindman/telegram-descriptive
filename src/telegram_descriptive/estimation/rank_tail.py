"""Rank-size tail denominator estimators."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

import numpy as np

MIN_SHAPE = 1e-10


@dataclass(frozen=True)
class TailParameters:
    boundary_rank: int
    y0: float
    alpha0: float
    eta0: float = 0.0
    eta1: float = 0.0
    eta2: float = 0.0
    fitting_window: int = 0
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TailEstimate:
    model: str
    observed_head_mass: float
    tail_mass: float
    total_mass: float
    parameters: TailParameters
    flags: tuple[str, ...] = ()


def _tricube_weights(distance: np.ndarray) -> np.ndarray:
    max_dist = np.nanmax(distance)
    if max_dist <= 0:
        return np.ones_like(distance)
    scaled = np.clip(distance / max_dist, 0, 1)
    return (1 - scaled**3) ** 3


def _weighted_polyfit(
    x: np.ndarray,
    y: np.ndarray,
    degree: int,
    center: float,
) -> np.ndarray:
    centered = x - center
    design = np.column_stack([centered**power for power in range(degree + 1)])
    weights = _tricube_weights(np.abs(centered))
    weighted_design = design * weights[:, None]
    beta, *_ = np.linalg.lstsq(weighted_design, y * weights, rcond=None)
    return beta


def _local_quadratic_shape(
    x: np.ndarray,
    y: np.ndarray,
    center: float,
) -> tuple[float, float, float]:
    beta = _weighted_polyfit(x, y, degree=2, center=center)
    log_y0, slope, curvature = beta
    # alpha(t) = -d log(y) / dt, where t = log(rank).
    # eta0 = d alpha / dt = -d^2 log(y) / dt^2. Positive eta0 means steepening.
    alpha = -float(slope)
    eta = -2.0 * float(curvature)
    return float(log_y0), alpha, eta


def _positive_or_zero(value: float, name: str, flags: list[str]) -> float:
    if not math.isfinite(value):
        flags.append(f"{name}_not_finite")
        return 0.0
    if value < -MIN_SHAPE:
        flags.append(f"{name}_negative_constrained")
        return 0.0
    return max(0.0, value)


def _staggered_shape_derivatives(
    x: np.ndarray,
    y: np.ndarray,
    boundary_x: float,
    flags: list[str],
) -> tuple[float, float]:
    """Estimate eta1 and eta2 from staggered local quadratic slope fits.

    Each staggered local quadratic estimates alpha at a nearby center. A cubic
    fit of alpha(center) around the boundary then yields:

    alpha(t) = alpha0 + eta0*t + eta1*t^2/2 + eta2*t^3/6.
    """

    span = float(np.nanmax(np.abs(x - boundary_x)))
    if len(x) < 12 or span <= 0:
        flags.append("too_few_staggered_windows")
        return 0.0, 0.0

    center_offsets = np.linspace(-0.6 * span, 0.6 * span, 9)
    alpha_points: list[tuple[float, float]] = []
    for offset in center_offsets:
        center = boundary_x + float(offset)
        local_mask = np.abs(x - center) <= max(span * 0.55, 1e-12)
        if int(local_mask.sum()) < 5:
            continue
        _, alpha, _ = _local_quadratic_shape(x[local_mask], y[local_mask], center)
        if math.isfinite(alpha):
            alpha_points.append((float(offset), alpha))

    if len(alpha_points) < 5:
        flags.append("too_few_staggered_windows")
        return 0.0, 0.0

    offsets = np.asarray([point[0] for point in alpha_points], dtype=float)
    alphas = np.asarray([point[1] for point in alpha_points], dtype=float)
    degree = min(3, len(alpha_points) - 1)
    beta = _weighted_polyfit(offsets, alphas, degree=degree, center=0.0)
    eta1 = 2.0 * float(beta[2]) if degree >= 2 else 0.0
    eta2 = 6.0 * float(beta[3]) if degree >= 3 else 0.0
    if degree < 2:
        flags.append("eta1_not_estimated")
    if degree < 3:
        flags.append("eta2_not_estimated")
    return eta1, eta2


def _quartic_shape_derivatives(
    x: np.ndarray,
    y: np.ndarray,
    boundary_x: float,
    flags: list[str],
) -> tuple[float, float]:
    """Fallback high-order derivative estimate from a local quartic fit."""

    if len(x) < 9:
        flags.append("too_few_quartic_points")
        return 0.0, 0.0
    beta = _weighted_polyfit(x, y, degree=4, center=boundary_x)
    eta1 = -6.0 * float(beta[3])
    eta2 = -24.0 * float(beta[4])
    return eta1, eta2


def fit_tail_parameters(
    ranked_values: Sequence[float],
    boundary_rank: int,
    fitting_window: int = 100,
) -> TailParameters:
    """Estimate local rank-tail parameters around a trusted-head boundary.

    The implementation uses a weighted local quadratic on log(metric) against
    log(rank) at the boundary, plus staggered local quadratics around the
    boundary to estimate higher-order steepening terms. It defines:

    ``alpha0 = -d log(y) / d log(rank)`` and
    ``eta0 = d alpha / d log(rank)`` at the boundary. Positive ``eta0`` means
    the curve steepens beyond the boundary.
    """

    if boundary_rank < 2:
        raise ValueError("boundary_rank must be at least 2")
    values = np.asarray(ranked_values, dtype=float)
    if len(values) < boundary_rank:
        raise ValueError("ranked_values must contain boundary_rank values")
    ranks = np.arange(1, len(values) + 1, dtype=float)
    mask = np.isfinite(values) & (values > 0)
    values = values[mask]
    ranks = ranks[mask]
    if len(values) < boundary_rank:
        raise ValueError("not enough positive finite ranked values")

    boundary_x = math.log(boundary_rank)
    lo = max(1, boundary_rank - fitting_window)
    hi = min(len(values), boundary_rank + fitting_window)
    window_mask = (ranks >= lo) & (ranks <= hi)
    x = np.log(ranks[window_mask])
    y = np.log(values[window_mask])
    if len(x) < 5:
        return TailParameters(
            boundary_rank=boundary_rank,
            y0=float(values[boundary_rank - 1]),
            alpha0=float("nan"),
            fitting_window=len(x),
            flags=("too_few_ranks",),
        )

    flags: list[str] = []
    log_y0, alpha0, raw_eta0 = _local_quadratic_shape(x, y, boundary_x)
    eta0 = _positive_or_zero(raw_eta0, "eta0", flags)
    raw_eta1, raw_eta2 = _staggered_shape_derivatives(x, y, boundary_x, flags)
    quartic_eta1, quartic_eta2 = _quartic_shape_derivatives(x, y, boundary_x, flags)
    if raw_eta1 <= MIN_SHAPE < quartic_eta1:
        raw_eta1 = quartic_eta1
        flags.append("eta1_from_quartic_fallback")
    if raw_eta2 <= MIN_SHAPE < quartic_eta2:
        raw_eta2 = quartic_eta2
        flags.append("eta2_from_quartic_fallback")
    eta1 = _positive_or_zero(raw_eta1, "eta1", flags)
    eta2 = _positive_or_zero(raw_eta2, "eta2", flags)
    if alpha0 <= 1:
        flags.append("alpha_lte_one")
    if eta0 <= MIN_SHAPE and eta1 <= MIN_SHAPE and eta2 <= MIN_SHAPE:
        flags.append("no_positive_steepening_terms")
    if raw_eta0 < -MIN_SHAPE:
        flags.append("convex_near_boundary")
    return TailParameters(
        boundary_rank=boundary_rank,
        y0=float(math.exp(log_y0)),
        alpha0=alpha0,
        eta0=eta0,
        eta1=eta1,
        eta2=eta2,
        fitting_window=int(len(x)),
        flags=tuple(flags),
    )


def _active_shape_terms(params: TailParameters, model: str) -> tuple[float, ...]:
    if model == "D1":
        return (params.eta0,)
    if model == "D2":
        return (params.eta0, params.eta1)
    if model == "D3":
        return (params.eta0, params.eta1, params.eta2)
    return ()


def _degeneracy_flags(params: TailParameters, model: str) -> list[str]:
    flags: list[str] = []
    if model == "D1" and params.eta0 <= MIN_SHAPE:
        flags.append("d1_degenerate_to_d0")
    if model == "D2" and params.eta1 <= MIN_SHAPE:
        flags.append("d2_degenerate_to_d1")
    if model == "D3" and params.eta2 <= MIN_SHAPE:
        flags.append("d3_degenerate_to_d2")
    return flags


def _tail_log_integrand(
    t: np.ndarray,
    y0: float,
    rc: float,
    alpha: float,
    eta0: float,
    eta1: float,
    eta2: float,
) -> np.ndarray:
    return (
        math.log(max(y0, 1e-300))
        + math.log(rc)
        + (1.0 - alpha) * t
        - eta0 * t**2 / 2
        - eta1 * t**3 / 6
        - eta2 * t**4 / 24
    )


def _adaptive_t_max(
    y0: float,
    rc: float,
    alpha: float,
    eta0: float,
    eta1: float,
    eta2: float,
) -> tuple[float, tuple[str, ...]]:
    flags: list[str] = []
    for t_max in (5.0, 10.0, 20.0, 40.0, 80.0):
        probe = np.linspace(0.0, t_max, 512)
        log_integrand = _tail_log_integrand(probe, y0, rc, alpha, eta0, eta1, eta2)
        if float(log_integrand[-1]) < float(np.nanmax(log_integrand)) - 14.0:
            return t_max, tuple(flags)
    flags.append("integration_cutoff_reached")
    return 80.0, tuple(flags)


def continuous_tail_mass(
    params: TailParameters,
    model: str,
    max_rank: int | None = None,
    integration_steps: int = 20_000,
) -> tuple[float, tuple[str, ...]]:
    """Integrate the continuous tail after ``boundary_rank``."""

    model = model.upper()
    if model not in {"D0", "D1", "D2", "D3"}:
        raise ValueError("model must be one of D0, D1, D2, D3")
    flags = list(params.flags)
    rc = float(params.boundary_rank)
    y0 = float(params.y0)
    alpha = float(params.alpha0)
    flags.extend(_degeneracy_flags(params, model))
    if model == "D0":
        if alpha <= 1 and max_rank is None:
            return float("inf"), tuple(flags + ["infinite_d0_tail"])
        if max_rank is None:
            return y0 * rc / (alpha - 1), tuple(flags)

    if max_rank is None:
        active_shape = _active_shape_terms(params, model)
        if alpha <= 1 and not any(term > MIN_SHAPE for term in active_shape):
            return float("inf"), tuple(flags + [f"infinite_{model.lower()}_tail"])
        eta0 = params.eta0 if model in {"D1", "D2", "D3"} else 0.0
        eta1 = params.eta1 if model in {"D2", "D3"} else 0.0
        eta2 = params.eta2 if model == "D3" else 0.0
        t_max, extra_flags = _adaptive_t_max(y0, rc, alpha, eta0, eta1, eta2)
        flags.extend(extra_flags)
    else:
        if max_rank <= params.boundary_rank:
            return 0.0, tuple(flags)
        t_max = math.log(max_rank / rc)

    eta0 = params.eta0 if model in {"D1", "D2", "D3"} else 0.0
    eta1 = params.eta1 if model in {"D2", "D3"} else 0.0
    eta2 = params.eta2 if model == "D3" else 0.0
    t = np.linspace(0.0, t_max, integration_steps)
    log_integrand = _tail_log_integrand(t, y0, rc, alpha, eta0, eta1, eta2)
    integrand = np.exp(np.clip(log_integrand, -745, 709))
    trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    tail = float(trapezoid(integrand, t))
    return tail, tuple(flags)


def estimate_tail_ladder(
    ranked_values: Sequence[float],
    boundary_rank: int,
    fitting_window: int = 100,
    max_rank: int | None = None,
) -> list[TailEstimate]:
    """Fit D0-D3 estimates for a boundary."""

    params = fit_tail_parameters(ranked_values, boundary_rank, fitting_window=fitting_window)
    observed_head_mass = float(np.nansum(np.asarray(ranked_values, dtype=float)[:boundary_rank]))
    estimates: list[TailEstimate] = []
    for model in ("D0", "D1", "D2", "D3"):
        tail, flags = continuous_tail_mass(params, model, max_rank=max_rank)
        estimates.append(
            TailEstimate(
                model=model,
                observed_head_mass=observed_head_mass,
                tail_mass=tail,
                total_mass=observed_head_mass + tail,
                parameters=params,
                flags=flags,
            )
        )
    return estimates
