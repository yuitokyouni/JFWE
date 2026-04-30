from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from world.clock import Clock
from world.events import WorldEvent
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

    def observe(
        self,
        events: tuple[WorldEvent, ...] = (),
        state: State | None = None,
    ) -> None:
        return None

    def step(
        self,
        clock: Clock,
        state: State,
        registry: Registry,
        ledger: Ledger,
    ) -> None:
        return None

    def emit(self) -> tuple[WorldEvent, ...]:
        return ()

    def snapshot(self) -> dict[str, Any]:
        return {}

    def bind(self, kernel: Any) -> None:
        """
        Hook invoked by WorldKernel.register_space after the space is
        registered but before its tasks are scheduled.

        BaseSpace's default is a no-op. Concrete spaces may override this
        to capture references to kernel-level books and projectors
        (registry, balance_sheets, constraint_evaluator, signals, etc.)
        without coupling the kernel to any specific space subclass.
        """
        return None

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
            bus = getattr(kernel, "event_bus", None)
            current_date = kernel.clock.current_date

            incoming: tuple[WorldEvent, ...] = ()
            if bus is not None:
                incoming = bus.collect_for_space(space.space_id, current_date)
                for event in incoming:
                    kernel.ledger.append(
                        event_type="event_delivered",
                        simulation_date=current_date,
                        object_id=event.event_id,
                        source=event.source_space,
                        target=space.space_id,
                        payload={
                            "event_type": event.event_type,
                            "source_space": event.source_space,
                            "target_space": space.space_id,
                            "visibility": event.visibility,
                            "delay_days": event.delay_days,
                        },
                        space_id=space.space_id,
                        correlation_id=event.event_id,
                        confidence=event.confidence,
                    )

            space.observe(incoming, kernel.state)
            space.step(
                kernel.clock,
                kernel.state,
                kernel.registry,
                kernel.ledger,
            )
            outgoing = tuple(space.emit() or ())

            if bus is not None:
                for event in outgoing:
                    bus.publish(event, on_date=current_date)
                    kernel.ledger.append(
                        event_type="event_published",
                        simulation_date=current_date,
                        object_id=event.event_id,
                        source=event.source_space,
                        payload={
                            "event_type": event.event_type,
                            "source_space": event.source_space,
                            "target_spaces": list(event.target_spaces),
                            "visibility": event.visibility,
                            "delay_days": event.delay_days,
                            "related_ids": list(event.related_ids),
                        },
                        space_id=space.space_id,
                        correlation_id=event.event_id,
                        confidence=event.confidence,
                    )

        _action.__name__ = f"{self.space_id}_{frequency.value}_step"
        return _action
