"""Safe aggregate export helpers."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from typing import Any


def suppress_small_counts(rows: Iterable[Mapping[str, Any]], min_cell_count: int = 5) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        for key, value in list(copied.items()):
            if key.startswith("n_") or key.endswith("_count") or key == "count":
                if isinstance(value, int | float) and 0 < value < min_cell_count:
                    copied[key] = None
                    copied[f"{key}_suppressed"] = True
        output.append(copied)
    return output


def write_csv(rows: Iterable[Mapping[str, Any]], path: str) -> None:
    data = list(rows)
    fieldnames = sorted({key for row in data for key in row})
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

