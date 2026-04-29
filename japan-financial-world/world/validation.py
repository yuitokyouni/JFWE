"""Lightweight validation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def require_fields(item: dict[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if field not in item]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")


def require_unique_ids(items: Iterable[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for item in items:
        object_id = item.get("id")
        if not object_id:
            raise ValueError("item is missing id")
        if object_id in seen:
            raise ValueError(f"duplicate id: {object_id}")
        seen.add(object_id)
