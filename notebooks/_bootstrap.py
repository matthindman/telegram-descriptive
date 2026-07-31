# Databricks notebook source
"""Make the repository's ``src`` package importable in deployed notebooks."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_src() -> Path:
    """Find the synced bundle's src directory from the notebook working directory."""

    starts = [Path.cwd()]
    if "__file__" in globals():
        starts.insert(0, Path(__file__).resolve().parent)

    checked: list[Path] = []
    for start in starts:
        for directory in (start, *start.parents):
            candidate = directory / "src"
            if candidate in checked:
                continue
            checked.append(candidate)
            if (candidate / "telegram_descriptive" / "__init__.py").is_file():
                return candidate

    locations = ", ".join(str(path) for path in checked)
    raise RuntimeError(
        "Could not locate src/telegram_descriptive in the deployed bundle. "
        f"Checked: {locations}"
    )


_src = str(_find_repo_src())
if _src not in sys.path:
    sys.path.insert(0, _src)
