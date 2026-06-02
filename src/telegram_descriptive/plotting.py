"""Small plotting helpers used by descriptive notebooks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def lorenz_points(values: Sequence[float]) -> tuple[list[float], list[float]]:
    """Return x/y Lorenz curve points for nonnegative values."""

    clean = sorted(float(v) for v in values if v is not None and float(v) >= 0)
    if not clean:
        return [0.0, 1.0], [0.0, 0.0]
    total = sum(clean)
    x = [0.0]
    y = [0.0]
    running = 0.0
    for idx, value in enumerate(clean, start=1):
        running += value
        x.append(idx / len(clean))
        y.append(0.0 if total == 0 else running / total)
    return x, y


def save_lorenz_plot(values: Sequence[float], path: str, title: str = "Lorenz curve") -> None:
    """Render a Lorenz curve if matplotlib is available."""

    import matplotlib.pyplot as plt

    x, y = lorenz_points(values)
    fig, ax = plt.subplots(figsize=(4, 4), dpi=150)
    ax.plot(x, y, label="Observed")
    ax.plot([0, 1], [0, 1], color="0.6", linestyle="--", label="Equality")
    ax.set_title(title)
    ax.set_xlabel("Cumulative share of channels")
    ax.set_ylabel("Cumulative share of metric")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def table_preview(rows: Sequence[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return list(rows[:limit])

