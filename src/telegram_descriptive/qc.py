"""Quality-control helpers shared by notebooks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from telegram_descriptive.schemas import TableContract


@dataclass(frozen=True)
class ContractCheck:
    table_name: str
    status: str
    missing_required_columns: tuple[str, ...]
    observed_columns: tuple[str, ...]
    caveats: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "pass"


def check_contract_columns(contract: TableContract, observed_columns: Iterable[str]) -> ContractCheck:
    columns = tuple(observed_columns)
    missing = tuple(contract.validate_columns(columns))
    return ContractCheck(
        table_name=contract.name,
        status="pass" if not missing else "fail",
        missing_required_columns=missing,
        observed_columns=columns,
        caveats=contract.caveats,
    )


def gap_report(
    name: str,
    required_inputs: Iterable[str],
    observed_inputs: Iterable[str],
    reason: str,
    blocking: bool = True,
) -> dict[str, Any]:
    """Create a structured report when a planned analysis lacks source support."""

    required = tuple(required_inputs)
    observed = set(observed_inputs)
    missing = tuple(item for item in required if item not in observed)
    return {
        "name": name,
        "status": "blocked" if blocking and missing else "available",
        "reason": reason if missing else "",
        "required_inputs": list(required),
        "observed_inputs": sorted(observed),
        "missing_inputs": list(missing),
    }


def summarize_null_rates(records: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Return simple null-rate diagnostics for a sequence of dict-like rows."""

    rows = list(records)
    if not rows:
        return {}
    keys = sorted({key for row in rows for key in row})
    return {
        key: sum(row.get(key) is None for row in rows) / len(rows)
        for key in keys
    }

