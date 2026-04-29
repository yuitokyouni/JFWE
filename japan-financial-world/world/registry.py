"""Central registry for world objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Registry:
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    assets: dict[str, dict[str, Any]] = field(default_factory=dict)
    contracts: dict[str, dict[str, Any]] = field(default_factory=dict)
    markets: dict[str, dict[str, Any]] = field(default_factory=dict)
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)
    prices: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add(self, collection: str, item: dict[str, Any]) -> None:
        object_id = item.get("id")
        if not object_id:
            raise ValueError(f"{collection} item is missing id")
        target = getattr(self, collection)
        if object_id in target:
            raise ValueError(f"duplicate {collection} id: {object_id}")
        target[object_id] = item

    def get(self, collection: str, object_id: str) -> dict[str, Any]:
        return getattr(self, collection)[object_id]
