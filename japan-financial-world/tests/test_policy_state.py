from datetime import date

import pytest

from spaces.policy.space import PolicySpace
from spaces.policy.state import (
    DuplicatePolicyAuthorityStateError,
    DuplicatePolicyInstrumentStateError,
    PolicyAuthorityState,
    PolicyInstrumentState,
)
from world.clock import Clock
from world.ledger import Ledger


def _authority(
    authority_id: str = "authority:boj",
    *,
    authority_type: str = "central_bank",
    tier: str = "national",
    status: str = "active",
    metadata: dict | None = None,
) -> PolicyAuthorityState:
    return PolicyAuthorityState(
        authority_id=authority_id,
        authority_type=authority_type,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


def _instrument(
    instrument_id: str = "instrument:boj_policy_rate",
    *,
    authority_id: str = "authority:boj",
    instrument_type: str = "policy_rate",
    status: str = "active",
    metadata: dict | None = None,
) -> PolicyInstrumentState:
    return PolicyInstrumentState(
        instrument_id=instrument_id,
        authority_id=authority_id,
        instrument_type=instrument_type,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# PolicyAuthorityState dataclass
# ---------------------------------------------------------------------------


def test_authority_state_carries_required_fields():
    auth = _authority()
    assert auth.authority_id == "authority:boj"
    assert auth.authority_type == "central_bank"
    assert auth.tier == "national"
    assert auth.status == "active"
    assert auth.metadata == {}


def test_authority_state_rejects_empty_id():
    with pytest.raises(ValueError):
        PolicyAuthorityState(authority_id="")


def test_authority_state_to_dict_is_serializable():
    auth = _authority(authority_type="financial_regulator")
    assert auth.to_dict() == {
        "authority_id": "authority:boj",
        "authority_type": "financial_regulator",
        "tier": "national",
        "status": "active",
        "metadata": {},
    }


def test_authority_state_is_immutable():
    auth = _authority()
    with pytest.raises(Exception):
        auth.tier = "regional"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PolicyInstrumentState dataclass
# ---------------------------------------------------------------------------


def test_instrument_state_carries_required_fields():
    inst = _instrument()
    assert inst.instrument_id == "instrument:boj_policy_rate"
    assert inst.authority_id == "authority:boj"
    assert inst.instrument_type == "policy_rate"
    assert inst.status == "active"


def test_instrument_state_rejects_empty_ids():
    with pytest.raises(ValueError):
        PolicyInstrumentState(instrument_id="", authority_id="authority:x")
    with pytest.raises(ValueError):
        PolicyInstrumentState(instrument_id="instrument:x", authority_id="")


def test_instrument_state_is_immutable():
    inst = _instrument()
    with pytest.raises(Exception):
        inst.status = "suspended"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PolicySpace authority CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_authority_state():
    space = PolicySpace()
    auth = _authority()
    space.add_authority_state(auth)
    assert space.get_authority_state("authority:boj") is auth


def test_get_authority_state_returns_none_for_unknown():
    space = PolicySpace()
    assert space.get_authority_state("authority:unknown") is None


def test_duplicate_authority_rejected():
    space = PolicySpace()
    space.add_authority_state(_authority())
    with pytest.raises(DuplicatePolicyAuthorityStateError):
        space.add_authority_state(_authority())


def test_list_authorities_returns_all_in_insertion_order():
    space = PolicySpace()
    space.add_authority_state(_authority("authority:a"))
    space.add_authority_state(_authority("authority:b"))
    space.add_authority_state(_authority("authority:c"))

    listed = space.list_authorities()
    assert [a.authority_id for a in listed] == [
        "authority:a",
        "authority:b",
        "authority:c",
    ]


# ---------------------------------------------------------------------------
# PolicySpace instrument CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_instrument_state():
    space = PolicySpace()
    inst = _instrument()
    space.add_instrument_state(inst)
    assert space.get_instrument_state("instrument:boj_policy_rate") is inst


def test_duplicate_instrument_rejected():
    space = PolicySpace()
    space.add_instrument_state(_instrument())
    with pytest.raises(DuplicatePolicyInstrumentStateError):
        space.add_instrument_state(_instrument())


def test_instrument_can_reference_unregistered_authority():
    """v0.14 does not validate FK to authority — same rule as v0.12."""
    space = PolicySpace()
    inst = _instrument(authority_id="authority:not_yet_registered")
    space.add_instrument_state(inst)
    assert space.get_instrument_state("instrument:boj_policy_rate") is inst


def test_list_instruments_by_authority_filters_correctly():
    space = PolicySpace()
    space.add_instrument_state(
        _instrument(instrument_id="instrument:rate", authority_id="authority:boj")
    )
    space.add_instrument_state(
        _instrument(instrument_id="instrument:rrr", authority_id="authority:boj")
    )
    space.add_instrument_state(
        _instrument(
            instrument_id="instrument:capital_ratio",
            authority_id="authority:fsa",
        )
    )

    boj_instruments = space.list_instruments_by_authority("authority:boj")
    fsa_instruments = space.list_instruments_by_authority("authority:fsa")
    unknown = space.list_instruments_by_authority("authority:none")

    assert {i.instrument_id for i in boj_instruments} == {
        "instrument:rate",
        "instrument:rrr",
    }
    assert {i.instrument_id for i in fsa_instruments} == {
        "instrument:capital_ratio"
    }
    assert unknown == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_sorts_authorities_and_instruments_deterministically():
    space = PolicySpace()
    space.add_authority_state(_authority("authority:b"))
    space.add_authority_state(_authority("authority:a"))
    space.add_instrument_state(_instrument("instrument:y", authority_id="authority:b"))
    space.add_instrument_state(_instrument("instrument:x", authority_id="authority:a"))

    snap = space.snapshot()
    assert snap["space_id"] == "policy"
    assert snap["authority_count"] == 2
    assert snap["instrument_count"] == 2
    assert [a["authority_id"] for a in snap["authorities"]] == [
        "authority:a",
        "authority:b",
    ]
    assert [i["instrument_id"] for i in snap["instruments"]] == [
        "instrument:x",
        "instrument:y",
    ]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = PolicySpace().snapshot()
    assert snap == {
        "space_id": "policy",
        "authority_count": 0,
        "instrument_count": 0,
        "authorities": [],
        "instruments": [],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_authority_records_to_ledger():
    ledger = Ledger()
    space = PolicySpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_authority_state(_authority(authority_type="central_bank"))

    records = ledger.filter(event_type="policy_authority_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "authority:boj"
    assert record.payload["authority_type"] == "central_bank"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "policy"


def test_add_instrument_records_to_ledger():
    ledger = Ledger()
    space = PolicySpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_instrument_state(_instrument(instrument_type="reserve_requirement"))

    records = ledger.filter(event_type="policy_instrument_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "instrument:boj_policy_rate"
    assert record.target == "authority:boj"
    assert record.payload["instrument_type"] == "reserve_requirement"


def test_add_state_does_not_record_when_no_ledger():
    space = PolicySpace()
    space.add_authority_state(_authority())
    space.add_instrument_state(_instrument())
    assert space.get_authority_state("authority:boj") is not None
    assert space.get_instrument_state("instrument:boj_policy_rate") is not None
