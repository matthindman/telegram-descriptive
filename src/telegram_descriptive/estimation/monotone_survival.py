"""Monotone threshold survival estimates."""

from __future__ import annotations

from collections.abc import Sequence


def enforce_nonincreasing(values: Sequence[float]) -> list[float]:
    """Project a sequence onto a nonincreasing sequence by pooled adjacent violators."""

    blocks: list[tuple[float, int]] = []
    for raw in values:
        blocks.append((float(raw), 1))
        while len(blocks) >= 2 and blocks[-2][0] < blocks[-1][0]:
            v1, n1 = blocks.pop()
            v0, n0 = blocks.pop()
            merged = (v0 * n0 + v1 * n1) / (n0 + n1)
            blocks.append((merged, n0 + n1))
    out: list[float] = []
    for value, size in blocks:
        out.extend([value] * size)
    return out


def threshold_survival(counts_by_threshold: dict[float, float]) -> dict[float, float]:
    thresholds = sorted(counts_by_threshold)
    adjusted = enforce_nonincreasing([counts_by_threshold[t] for t in thresholds])
    return dict(zip(thresholds, adjusted))

