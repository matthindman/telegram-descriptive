"""Dashboard manifest helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def dashboard_manifest(title: str, tables: Mapping[str, str], figures: Mapping[str, str] | None = None) -> dict[str, Any]:
    return {"title": title, "tables": dict(tables), "figures": dict(figures or {})}

