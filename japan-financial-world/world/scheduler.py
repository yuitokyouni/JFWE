"""World scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .clock import Clock
from .ledger import Ledger
from .registry import Registry


class Space(Protocol):
    def step_pre_market(self, world: "WorldContext") -> None:
        ...

    def step_market(self, world: "WorldContext") -> None:
        ...

    def step_post_market(self, world: "WorldContext") -> None:
        ...

    def publish_state(self) -> dict:
        ...


@dataclass
class WorldContext:
    clock: Clock
    registry: Registry
    ledger: Ledger


@dataclass
class Scheduler:
    clock: Clock
    registry: Registry
    ledger: Ledger
    spaces: list[Space] = field(default_factory=list)

    def step(self) -> None:
        context = WorldContext(self.clock, self.registry, self.ledger)
        for space in self.spaces:
            space.step_pre_market(context)
        for space in self.spaces:
            space.step_market(context)
        for space in self.spaces:
            space.step_post_market(context)
        self.clock.advance_day()
