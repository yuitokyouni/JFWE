from datetime import date

import pytest

from spaces.information.space import InformationSpace
from spaces.information.state import (
    DuplicateInformationChannelStateError,
    DuplicateInformationSourceStateError,
    InformationChannelState,
    InformationSourceState,
)
from world.clock import Clock
from world.ledger import Ledger


def _source(
    source_id: str = "source:reference_rating_agency_a",
    *,
    source_type: str = "rating_agency",
    tier: str = "tier_1",
    status: str = "active",
    metadata: dict | None = None,
) -> InformationSourceState:
    return InformationSourceState(
        source_id=source_id,
        source_type=source_type,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


def _channel(
    channel_id: str = "channel:reuters_wire",
    *,
    channel_type: str = "wire_service",
    visibility: str = "public",
    status: str = "active",
    metadata: dict | None = None,
) -> InformationChannelState:
    return InformationChannelState(
        channel_id=channel_id,
        channel_type=channel_type,
        visibility=visibility,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# InformationSourceState dataclass
# ---------------------------------------------------------------------------


def test_source_state_carries_required_fields():
    src = _source()
    assert src.source_id == "source:reference_rating_agency_a"
    assert src.source_type == "rating_agency"
    assert src.tier == "tier_1"
    assert src.status == "active"
    assert src.metadata == {}


def test_source_state_rejects_empty_id():
    with pytest.raises(ValueError):
        InformationSourceState(source_id="")


def test_source_state_to_dict_is_serializable():
    src = _source(metadata={"jurisdiction": "global"})
    assert src.to_dict() == {
        "source_id": "source:reference_rating_agency_a",
        "source_type": "rating_agency",
        "tier": "tier_1",
        "status": "active",
        "metadata": {"jurisdiction": "global"},
    }


def test_source_state_is_immutable():
    src = _source()
    with pytest.raises(Exception):
        src.tier = "tier_2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# InformationChannelState dataclass
# ---------------------------------------------------------------------------


def test_channel_state_carries_required_fields():
    ch = _channel()
    assert ch.channel_id == "channel:reuters_wire"
    assert ch.channel_type == "wire_service"
    assert ch.visibility == "public"
    assert ch.status == "active"
    assert ch.metadata == {}


def test_channel_state_rejects_empty_id():
    with pytest.raises(ValueError):
        InformationChannelState(channel_id="")


def test_channel_state_to_dict_is_serializable():
    ch = _channel(channel_type="press_release", visibility="public")
    assert ch.to_dict() == {
        "channel_id": "channel:reuters_wire",
        "channel_type": "press_release",
        "visibility": "public",
        "status": "active",
        "metadata": {},
    }


def test_channel_state_is_immutable():
    ch = _channel()
    with pytest.raises(Exception):
        ch.visibility = "private"  # type: ignore[misc]


def test_channel_visibility_is_free_form_string():
    """
    v0.13 does not validate visibility against SignalBook's enum.
    Channel and signal visibility are kept as independent labels.
    """
    ch = InformationChannelState(channel_id="channel:weird", visibility="cosmic")
    assert ch.visibility == "cosmic"


# ---------------------------------------------------------------------------
# InformationSpace source CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_source_state():
    space = InformationSpace()
    src = _source()
    space.add_source_state(src)
    assert space.get_source_state("source:reference_rating_agency_a") is src


def test_get_source_state_returns_none_for_unknown():
    space = InformationSpace()
    assert space.get_source_state("source:unknown") is None


def test_duplicate_source_rejected():
    space = InformationSpace()
    space.add_source_state(_source())
    with pytest.raises(DuplicateInformationSourceStateError):
        space.add_source_state(_source())


def test_list_sources_returns_all_in_insertion_order():
    space = InformationSpace()
    space.add_source_state(_source("source:a"))
    space.add_source_state(_source("source:b"))
    space.add_source_state(_source("source:c"))

    listed = space.list_sources()
    assert [s.source_id for s in listed] == ["source:a", "source:b", "source:c"]


def test_list_sources_returns_empty_when_none():
    space = InformationSpace()
    assert space.list_sources() == ()


# ---------------------------------------------------------------------------
# InformationSpace channel CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_channel_state():
    space = InformationSpace()
    ch = _channel()
    space.add_channel_state(ch)
    assert space.get_channel_state("channel:reuters_wire") is ch


def test_get_channel_state_returns_none_for_unknown():
    space = InformationSpace()
    assert space.get_channel_state("channel:unknown") is None


def test_duplicate_channel_rejected():
    space = InformationSpace()
    space.add_channel_state(_channel())
    with pytest.raises(DuplicateInformationChannelStateError):
        space.add_channel_state(_channel())


def test_list_channels_returns_all_in_insertion_order():
    space = InformationSpace()
    space.add_channel_state(_channel("channel:a"))
    space.add_channel_state(_channel("channel:b"))
    space.add_channel_state(_channel("channel:c"))

    listed = space.list_channels()
    assert [c.channel_id for c in listed] == [
        "channel:a",
        "channel:b",
        "channel:c",
    ]


def test_list_channels_returns_empty_when_none():
    space = InformationSpace()
    assert space.list_channels() == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_sorts_sources_and_channels_deterministically():
    space = InformationSpace()
    space.add_source_state(_source("source:b"))
    space.add_source_state(_source("source:a"))
    space.add_channel_state(_channel("channel:y"))
    space.add_channel_state(_channel("channel:x"))

    snap = space.snapshot()
    assert snap["space_id"] == "information"
    assert snap["source_count"] == 2
    assert snap["channel_count"] == 2
    assert [s["source_id"] for s in snap["sources"]] == ["source:a", "source:b"]
    assert [c["channel_id"] for c in snap["channels"]] == ["channel:x", "channel:y"]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = InformationSpace().snapshot()
    assert snap == {
        "space_id": "information",
        "source_count": 0,
        "channel_count": 0,
        "sources": [],
        "channels": [],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_source_state_records_to_ledger():
    ledger = Ledger()
    space = InformationSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_source_state(_source(source_type="wire_service", tier="tier_2"))

    records = ledger.filter(event_type="information_source_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "source:reference_rating_agency_a"
    assert record.payload["source_type"] == "wire_service"
    assert record.payload["tier"] == "tier_2"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "information"


def test_add_channel_state_records_to_ledger():
    ledger = Ledger()
    space = InformationSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_channel_state(_channel(channel_type="press_release"))

    records = ledger.filter(event_type="information_channel_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "channel:reuters_wire"
    assert record.payload["channel_type"] == "press_release"
    assert record.payload["visibility"] == "public"


def test_add_state_does_not_record_when_no_ledger():
    space = InformationSpace()
    space.add_source_state(_source())
    space.add_channel_state(_channel())
    assert space.get_source_state("source:reference_rating_agency_a") is not None
    assert space.get_channel_state("channel:reuters_wire") is not None


# ---------------------------------------------------------------------------
# Helper accessors return empty when refs unbound
# ---------------------------------------------------------------------------


def test_list_signals_by_source_returns_empty_when_unbound():
    space = InformationSpace()
    assert space.list_signals_by_source("source:reference_rating_agency_a") == ()


def test_list_signals_by_type_returns_empty_when_unbound():
    space = InformationSpace()
    assert space.list_signals_by_type("rating_action") == ()


def test_list_visible_signals_returns_empty_when_unbound():
    space = InformationSpace()
    assert space.list_visible_signals("agent:somebody") == ()
