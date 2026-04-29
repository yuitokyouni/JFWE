from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from world.clock import Clock
from world.event_bus import EventBus
from world.ledger import Ledger
from world.registry import RegisteredObject, Registry
from world.scheduler import Scheduler, ScheduledTask, TaskSpec
from world.state import State

if TYPE_CHECKING:
    from spaces.base import BaseSpace


@dataclass
class WorldKernel:
    registry: Registry
    clock: Clock
    scheduler: Scheduler
    ledger: Ledger
    state: State
    event_bus: EventBus = field(default_factory=EventBus)

    def register_object(self, obj: RegisteredObject) -> None:
        self.registry.register(obj)
        self.state.initialize_object(obj.id, obj.attributes)
        self.ledger.append(
            event_type="object_registered",
            simulation_date=self.clock.current_date,
            object_id=obj.id,
            payload={
                "kind": obj.kind,
                "type": obj.type,
                "space": obj.space,
            },
            space_id=obj.space,
        )

    def register_space(self, space: "BaseSpace") -> tuple[ScheduledTask, ...]:
        """
        Register a Space and its scheduled tasks.

        The space itself is registered in the Registry under its world_id
        so that future code can look it up by ID. State is not initialized
        for spaces because spaces are not state-bearing objects.

        Returns the tuple of scheduled tasks created for this space.
        """
        self.registry.register_space(
            space,
            object_id=space.world_id,
            metadata={"space_id": space.space_id},
        )
        self.ledger.append(
            event_type="object_registered",
            simulation_date=self.clock.current_date,
            object_id=space.world_id,
            payload={
                "kind": "space",
                "space_id": space.space_id,
                "frequencies": [freq.value for freq in space.frequencies],
            },
            space_id=space.space_id,
        )

        scheduled = tuple(self.register_task(spec) for spec in space.task_specs())
        return scheduled

    def register_task(self, task: TaskSpec) -> ScheduledTask:
        scheduled = self.scheduler.register(task)
        self.ledger.append(
            event_type="task_scheduled",
            simulation_date=self.clock.current_date,
            task_id=task.id,
            object_id=task.target_id,
            payload={
                "name": task.name,
                "frequency": task.frequency.value,
            },
            space_id=task.space,
        )
        return scheduled

    def tick(self) -> None:
        due_tasks = self.scheduler.due_tasks(self.clock)
        for task in due_tasks:
            if callable(task.task):
                task.task(self)

            self.ledger.append(
                event_type="task_executed",
                simulation_date=self.clock.current_date,
                task_id=task.id,
                object_id=task.target_id,
                payload={
                    "name": task.display_name(),
                    "frequency": task.frequency.value,
                    "space": task.space,
                },
                space_id=task.space,
            )

        if self.clock.is_month_end():
            snapshot = self.state.snapshot(self.clock.current_date)
            self.ledger.append(
                event_type="state_snapshot_created",
                simulation_date=self.clock.current_date,
                object_id=snapshot.snapshot_id,
                payload={
                    "snapshot_id": snapshot.snapshot_id,
                    "state_hash": snapshot.state_hash,
                },
                snapshot_id=snapshot.snapshot_id,
                state_hash=snapshot.state_hash,
                space_id="world",
            )

        self.clock.advance()

    def run(self, days: int) -> None:
        if days < 0:
            raise ValueError("days must be non-negative")
        for _ in range(days):
            self.tick()
