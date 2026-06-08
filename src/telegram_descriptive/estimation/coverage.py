"""Coverage calculations for TOO frames and denominator estimates."""

from __future__ import annotations


def coverage(numerator_mass: float | None, denominator_mass: float | None) -> float | None:
    if numerator_mass is None or denominator_mass is None or denominator_mass <= 0:
        return None
    return max(0.0, min(1.0, float(numerator_mass) / float(denominator_mass)))


def conservative_lower_coverage(numerator_mass: float, denominator_upper: float | None) -> float | None:
    return coverage(numerator_mass, denominator_upper)


def top_k_share(values: list[float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    clean = sorted((float(v) for v in values if v is not None and float(v) >= 0), reverse=True)
    total = sum(clean)
    if total == 0:
        return 0.0
    return sum(clean[:k]) / total
