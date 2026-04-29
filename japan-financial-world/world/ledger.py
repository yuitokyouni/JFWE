"""Append-only world ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_CHANNELS = {
    "asset_ownership",
    "contract",
    "market_price",
    "information_signal",
    "constraint",
}


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    timestamp: int
    entry_type: str
    channel: str
    source_space: str
    target_refs: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.channel not in ALLOWED_CHANNELS:
            raise ValueError(f"unsupported ledger channel: {self.channel}")


@dataclass
class Ledger:
    entries: list[LedgerEntry] = field(default_factory=list)

    def append(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)
