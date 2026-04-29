from datetime import date

import pytest

from world.event_bus import DuplicateEventError, EventBus
from world.events import WorldEvent


def make_event(**overrides) -> WorldEvent:
    base = dict(
        event_id="event:001",
        simulation_date="2026-01-01",
        source_space="alpha",
        target_spaces=(),
        event_type="test_signal",
        payload={},
    )
    base.update(overrides)
    return WorldEvent(**base)


def test_publish_and_collect_delivers_a_matching_event():
    bus = EventBus()
    bus.publish(make_event())

    # Same-tick delivery is forbidden: events become visible from the next
    # tick onward, so collection must happen at a later date than publication.
    assert bus.collect_for_space("beta", date(2026, 1, 1)) == ()

    collected = bus.collect_for_space("beta", date(2026, 1, 2))
    assert len(collected) == 1
    assert collected[0].event_id == "event:001"


def test_collect_does_not_deliver_before_delivery_date():
    bus = EventBus()
    bus.publish(make_event(simulation_date="2026-01-05", delay_days=3))

    assert bus.collect_for_space("beta", date(2026, 1, 5)) == ()
    assert bus.collect_for_space("beta", date(2026, 1, 7)) == ()

    delivered = bus.collect_for_space("beta", date(2026, 1, 8))
    assert len(delivered) == 1


def test_target_filtering_excludes_non_targets():
    bus = EventBus()
    bus.publish(make_event(target_spaces=("alpha", "gamma")))

    assert bus.collect_for_space("beta", date(2026, 1, 2)) == ()
    assert len(bus.collect_for_space("alpha", date(2026, 1, 2))) == 1
    assert len(bus.collect_for_space("gamma", date(2026, 1, 2))) == 1


def test_broadcast_event_reaches_any_space_except_source():
    bus = EventBus()
    bus.publish(make_event(source_space="alpha", target_spaces=()))

    assert len(bus.collect_for_space("b", date(2026, 1, 2))) == 1
    assert len(bus.collect_for_space("c", date(2026, 1, 2))) == 1
    assert len(bus.collect_for_space("d", date(2026, 1, 2))) == 1
    # Source itself does not receive its own broadcast.
    assert bus.collect_for_space("alpha", date(2026, 1, 2)) == ()


def test_event_delivered_to_a_space_only_once():
    bus = EventBus()
    bus.publish(make_event())

    first = bus.collect_for_space("beta", date(2026, 1, 2))
    second = bus.collect_for_space("beta", date(2026, 1, 3))

    assert len(first) == 1
    assert second == ()


def test_pending_and_delivered_split_after_partial_delivery():
    bus = EventBus()
    bus.publish(make_event(event_id="event:fresh"))
    bus.publish(
        make_event(
            event_id="event:delayed",
            simulation_date="2026-01-01",
            delay_days=10,
        )
    )

    bus.collect_for_space("beta", date(2026, 1, 2))

    pending = {event.event_id for event in bus.pending_events()}
    delivered = {event.event_id for event in bus.delivered_events()}

    assert delivered == {"event:fresh"}
    assert pending == {"event:delayed"}


def test_publish_rejects_duplicate_event_ids():
    bus = EventBus()
    bus.publish(make_event(event_id="event:dup"))

    with pytest.raises(DuplicateEventError):
        bus.publish(make_event(event_id="event:dup"))


def test_world_event_rejects_invalid_visibility():
    with pytest.raises(ValueError):
        WorldEvent(
            event_id="event:bad",
            simulation_date="2026-01-01",
            source_space="alpha",
            visibility="secret",
        )


def test_world_event_rejects_negative_delay():
    with pytest.raises(ValueError):
        WorldEvent(
            event_id="event:bad",
            simulation_date="2026-01-01",
            source_space="alpha",
            delay_days=-1,
        )


def test_world_event_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        WorldEvent(
            event_id="event:bad",
            simulation_date="2026-01-01",
            source_space="alpha",
            confidence=1.5,
        )
