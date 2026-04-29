from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from world.clock import Clock
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Frequency, TaskSpec
from world.state import State


@dataclass
class BaseSpace:
    """
    Constitutional contract that every Space must obey.

    A Space is a domain-bounded area of the world. Spaces register tasks
    with the scheduler at declared frequencies. They act only inside their
    own boundary and must never directly mutate the internal state of
    another space.

    v0 contract:
        - observe(events, state)   -> read inputs from allowed channels
        - step(clock, state, registry, ledger) -> one tick at the given frequency
        - emit()                   -> produce outputs via allowed world objects
        - snapshot()               -> serializable view of local state

    v0 implementations are no-ops. The kernel records each invocation in
    the ledger via the standard `task_executed` event, so empty spaces are
    sufficient to verify that the wiring is correct.
    """

    space_id: str = "base"
    frequencies: tuple[Frequency, ...] = ()

    @property
    def world_id(self) -> str:
        return f"space:{self.space_id}"

    def observe(self, events: Any = None, state: State | None = None) -> None:
        return None

    def step(
        self,
        clock: Clock,
        state: State,
        registry: Registry,
        ledger: Ledger,
    ) -> None:
        return None

    def emit(self) -> tuple[Any, ...]:
        return ()

    def snapshot(self) -> dict[str, Any]:
        return {}

    def task_specs(self) -> Iterable[TaskSpec]:
        for frequency in self.frequencies:
            yield TaskSpec(
                id=f"task:{self.space_id}_{frequency.value}",
                frequency=frequency,
                name=f"{self.space_id}_{frequency.value}_step",
                space=self.space_id,
                action=self._make_action(frequency),
            )

    def _make_action(self, frequency: Frequency):
        space = self

        def _action(kernel) -> None:
            space.step(
                kernel.clock,
                kernel.state,
                kernel.registry,
                kernel.ledger,
            )

        _action.__name__ = f"{self.space_id}_{frequency.value}_step"
        return _action
