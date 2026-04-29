"""Stable identifier helpers for world objects."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count


@dataclass
class IdGenerator:
    """Generates readable deterministic IDs per object prefix."""

    prefix: str
    start: int = 1

    def __post_init__(self) -> None:
        self._counter = count(self.start)

    def next(self) -> str:
        return f"{self.prefix}_{next(self._counter):06d}"
