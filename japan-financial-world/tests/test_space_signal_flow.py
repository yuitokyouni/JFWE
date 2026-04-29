from dataclasses import dataclass, field
from datetime import date

from spaces.base import BaseSpace
from world.clock import Clock
from world.event_bus import EventBus
from world.events import WorldEvent
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Frequency, Scheduler
from world.state import State


@dataclass
class EmitterSpace(BaseSpace):
    space_id: str = "emitter"
    frequencies: tuple[Frequency, ...] = (Frequency.DAILY,)
    pending: list[WorldEvent] = field(default_factory=list)

    def emit(self) -> tuple[WorldEvent, ...]:
        out = tuple(self.pending)
        self.pending.clear()
        return out


@dataclass
class ObserverSpace(BaseSpace):
    space_id: str = "observer"
    frequencies: tuple[Frequency, ...] = (Frequency.DAILY,)
    seen: list[WorldEvent] = field(default_factory=list)

    def observe(self, events=(), state=None):
        if events:
            self.seen.extend(events)


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
        event_bus=EventBus(),
    )


def test_event_flows_from_emitter_to_observer_via_kernel():
    kernel = _kernel()
    emitter = EmitterSpace()
    observer = ObserverSpace()
    kernel.register_space(emitter)
    kernel.register_space(observer)

    emitter.pending.append(
        WorldEvent(
            event_id="event:flow_001",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="hello",
        )
    )

    # Day 1: emitter publishes. Day 2: observer collects.
    kernel.run(days=2)

    assert len(observer.seen) == 1
    assert observer.seen[0].event_id == "event:flow_001"
    assert observer.seen[0].source_space == "emitter"

    assert len(kernel.ledger.filter(event_type="event_published")) == 1
    assert len(kernel.ledger.filter(event_type="event_delivered")) == 1


def test_delayed_event_is_not_delivered_too_early():
    kernel = _kernel()
    emitter = EmitterSpace()
    observer = ObserverSpace()
    kernel.register_space(emitter)
    kernel.register_space(observer)

    emitter.pending.append(
        WorldEvent(
            event_id="event:delayed_001",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="delayed",
            delay_days=3,
        )
    )

    kernel.run(days=2)
    assert observer.seen == []
    assert len(kernel.ledger.filter(event_type="event_delivered")) == 0
    # The event is published on day 1; delivery should not have fired yet.
    assert len(kernel.ledger.filter(event_type="event_published")) == 1
    assert len(kernel.event_bus.pending_events()) == 1
    assert kernel.event_bus.delivered_events() == ()

    kernel.run(days=3)
    # Day 4 (2026-01-04) is the delivery_date; observer receives on day 4.
    assert len(observer.seen) == 1
    assert observer.seen[0].event_id == "event:delayed_001"
    assert len(kernel.ledger.filter(event_type="event_delivered")) == 1


def test_target_filtering_at_kernel_level():
    kernel = _kernel()
    emitter = EmitterSpace()
    target = ObserverSpace(space_id="target")
    bystander = ObserverSpace(space_id="bystander")

    kernel.register_space(emitter)
    kernel.register_space(target)
    kernel.register_space(bystander)

    emitter.pending.append(
        WorldEvent(
            event_id="event:targeted_001",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("target",),
            event_type="targeted",
        )
    )

    # Day 1: emitter publishes. Day 2: only target collects.
    kernel.run(days=2)

    assert len(target.seen) == 1
    assert bystander.seen == []
    # Only the target observer should produce an event_delivered record.
    delivered_records = kernel.ledger.filter(event_type="event_delivered")
    assert len(delivered_records) == 1
    assert delivered_records[0].target == "target"


def test_broadcast_event_reaches_every_space_except_source():
    kernel = _kernel()
    emitter = EmitterSpace()
    a = ObserverSpace(space_id="alpha")
    b = ObserverSpace(space_id="beta")
    c = ObserverSpace(space_id="gamma")

    kernel.register_space(emitter)
    kernel.register_space(a)
    kernel.register_space(b)
    kernel.register_space(c)

    emitter.pending.append(
        WorldEvent(
            event_id="event:broadcast_001",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=(),
            event_type="broadcast",
        )
    )

    # Day 1: emitter publishes. Day 2: every other space collects.
    kernel.run(days=2)

    assert len(a.seen) == 1
    assert len(b.seen) == 1
    assert len(c.seen) == 1
    # Emitter should not receive its own broadcast.
    assert len(kernel.ledger.filter(event_type="event_delivered")) == 3


def test_ledger_records_carry_event_provenance():
    kernel = _kernel()
    emitter = EmitterSpace()
    observer = ObserverSpace()
    kernel.register_space(emitter)
    kernel.register_space(observer)

    emitter.pending.append(
        WorldEvent(
            event_id="event:provenance_001",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="provenance",
            visibility="internal",
            confidence=0.42,
            related_ids=("agent:someone",),
        )
    )

    # Day 1 publish, day 2 deliver.
    kernel.run(days=2)

    published = kernel.ledger.filter(event_type="event_published")
    delivered = kernel.ledger.filter(event_type="event_delivered")

    assert len(published) == 1
    assert len(delivered) == 1

    pub = published[0]
    assert pub.correlation_id == "event:provenance_001"
    assert pub.space_id == "emitter"
    assert pub.confidence == 0.42
    assert pub.payload["visibility"] == "internal"
    # Ledger payloads are frozen, so list-typed values come back as tuples.
    assert tuple(pub.payload["related_ids"]) == ("agent:someone",)

    deliv = delivered[0]
    assert deliv.correlation_id == "event:provenance_001"
    assert deliv.source == "emitter"
    assert deliv.target == "observer"
    assert deliv.confidence == 0.42
