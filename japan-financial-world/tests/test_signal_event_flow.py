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
from world.signals import InformationSignal, SignalBook
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
class SignalAwareObserver(BaseSpace):
    space_id: str = "observer"
    frequencies: tuple[Frequency, ...] = (Frequency.DAILY,)
    signal_book: SignalBook | None = None
    seen_events: list[WorldEvent] = field(default_factory=list)
    seen_signals: list[InformationSignal] = field(default_factory=list)

    def observe(self, events=(), state=None):
        for event in events:
            self.seen_events.append(event)
            signal_id = event.payload.get("signal_id") if event.payload else None
            if signal_id and self.signal_book is not None:
                signal = self.signal_book.get_signal(signal_id)
                self.seen_signals.append(signal)


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
        event_bus=EventBus(),
    )


def test_signal_referenced_by_event_flows_to_observer():
    kernel = _kernel()

    # 1. Register the information signal in SignalBook.
    signal = InformationSignal(
        signal_id="signal:rating_001",
        signal_type="rating_action",
        subject_id="agent:firm_x",
        source_id="agent:rating_agency",
        published_date="2026-01-01",
        effective_date="2026-01-01",
        payload={"rating": "BBB-", "outlook": "negative"},
    )
    kernel.signals.add_signal(signal)

    # 2. Wire spaces. The observer holds a reference to the kernel's
    #    SignalBook so it can resolve event payload signal_ids.
    emitter = EmitterSpace()
    observer = SignalAwareObserver(signal_book=kernel.signals)
    kernel.register_space(emitter)
    kernel.register_space(observer)

    # 3. Queue a WorldEvent that references the signal by id.
    emitter.pending.append(
        WorldEvent(
            event_id="event:rating_announcement",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="signal_emitted",
            payload={"signal_id": "signal:rating_001"},
            related_ids=("signal:rating_001",),
        )
    )

    # Day 1: emitter publishes. Day 2: observer collects.
    kernel.run(days=2)

    # Observer received the event.
    assert len(observer.seen_events) == 1
    received = observer.seen_events[0]
    assert received.event_id == "event:rating_announcement"
    assert received.payload["signal_id"] == "signal:rating_001"

    # Observer fetched the actual signal from SignalBook via event payload.
    assert len(observer.seen_signals) == 1
    fetched = observer.seen_signals[0]
    assert fetched.signal_id == "signal:rating_001"
    assert fetched.signal_type == "rating_action"
    assert fetched.payload["rating"] == "BBB-"

    # Ledger captures the full information flow.
    assert len(kernel.ledger.filter(event_type="signal_added")) == 1
    assert len(kernel.ledger.filter(event_type="event_published")) == 1
    assert len(kernel.ledger.filter(event_type="event_delivered")) == 1


def test_signal_event_payload_can_resolve_through_correlation_id():
    kernel = _kernel()

    signal = InformationSignal(
        signal_id="signal:earnings_001",
        signal_type="earnings_report",
        subject_id="agent:firm_x",
        source_id="agent:firm_x",
        published_date="2026-01-01",
    )
    kernel.signals.add_signal(signal)

    emitter = EmitterSpace()
    observer = SignalAwareObserver(signal_book=kernel.signals)
    kernel.register_space(emitter)
    kernel.register_space(observer)

    emitter.pending.append(
        WorldEvent(
            event_id="event:earnings_announcement",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="signal_emitted",
            payload={"signal_id": "signal:earnings_001"},
            related_ids=("signal:earnings_001",),
        )
    )

    kernel.run(days=2)

    # The published / delivered ledger records carry correlation_id =
    # event_id, which the related_ids field links to signal:earnings_001.
    published = kernel.ledger.filter(event_type="event_published")[0]
    delivered = kernel.ledger.filter(event_type="event_delivered")[0]
    assert published.correlation_id == "event:earnings_announcement"
    assert delivered.correlation_id == "event:earnings_announcement"
    assert "signal:earnings_001" in tuple(published.payload["related_ids"])


def test_signal_flow_does_not_mutate_other_books():
    kernel = _kernel()

    kernel.ownership.add_position("agent:firm_x", "asset:cash", 1_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()

    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:abc",
            signal_type="news",
            subject_id="agent:firm_x",
            source_id="agent:wire_service",
            published_date="2026-01-01",
        )
    )

    emitter = EmitterSpace()
    observer = SignalAwareObserver(signal_book=kernel.signals)
    kernel.register_space(emitter)
    kernel.register_space(observer)

    emitter.pending.append(
        WorldEvent(
            event_id="event:news",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="signal_emitted",
            payload={"signal_id": "signal:abc"},
        )
    )

    kernel.run(days=2)

    # Network books remain untouched.
    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before


def test_restricted_signal_can_still_flow_via_event_payload():
    """
    A WorldEvent's reach is governed by its own target_spaces, not by
    the referenced signal's visibility. v0.7 deliberately does not
    couple event delivery to signal visibility — that is policy, not
    transport.
    """
    kernel = _kernel()

    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal",
            signal_type="internal_memo",
            subject_id="agent:firm_x",
            source_id="agent:firm_x",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:legal",)},
        )
    )

    emitter = EmitterSpace()
    observer = SignalAwareObserver(signal_book=kernel.signals)
    kernel.register_space(emitter)
    kernel.register_space(observer)

    emitter.pending.append(
        WorldEvent(
            event_id="event:memo",
            simulation_date="2026-01-01",
            source_space="emitter",
            target_spaces=("observer",),
            event_type="signal_emitted",
            payload={"signal_id": "signal:internal"},
        )
    )

    kernel.run(days=2)

    # Event reaches the observer (transport allows it). Whether the
    # observer is *allowed* to interpret the signal is a separate
    # concern, queryable via SignalBook.list_visible_to or
    # signal.is_visible_to. The observer here just records the fetch.
    assert len(observer.seen_events) == 1
    assert observer.seen_signals[0].signal_id == "signal:internal"

    # But list_visible_to enforces the restriction.
    assert kernel.signals.list_visible_to("observer") == ()
    assert len(kernel.signals.list_visible_to("agent:legal")) == 1
