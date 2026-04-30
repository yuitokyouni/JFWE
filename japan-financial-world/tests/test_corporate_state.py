from datetime import date

import pytest

from spaces.corporate.space import CorporateSpace
from spaces.corporate.state import DuplicateFirmStateError, FirmState
from world.clock import Clock
from world.ledger import Ledger


def _firm(
    firm_id: str = "firm:toyota",
    *,
    sector: str = "manufacturing",
    tier: str = "large",
    status: str = "active",
    metadata: dict | None = None,
) -> FirmState:
    return FirmState(
        firm_id=firm_id,
        sector=sector,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# FirmState dataclass
# ---------------------------------------------------------------------------


def test_firm_state_carries_required_fields():
    firm = _firm()
    assert firm.firm_id == "firm:toyota"
    assert firm.sector == "manufacturing"
    assert firm.tier == "large"
    assert firm.status == "active"
    assert firm.metadata == {}


def test_firm_state_rejects_empty_firm_id():
    with pytest.raises(ValueError):
        FirmState(firm_id="")


def test_firm_state_to_dict_is_serializable():
    firm = _firm(metadata={"founded": "1937"})
    payload = firm.to_dict()
    assert payload == {
        "firm_id": "firm:toyota",
        "sector": "manufacturing",
        "tier": "large",
        "status": "active",
        "metadata": {"founded": "1937"},
    }


def test_firm_state_is_immutable():
    firm = _firm()
    with pytest.raises(Exception):
        firm.sector = "tech"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CorporateSpace state CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_firm_state():
    space = CorporateSpace()
    firm = _firm()
    space.add_firm_state(firm)
    assert space.get_firm_state("firm:toyota") is firm


def test_get_firm_state_returns_none_for_unknown():
    space = CorporateSpace()
    assert space.get_firm_state("firm:unknown") is None


def test_duplicate_firm_state_rejected():
    space = CorporateSpace()
    space.add_firm_state(_firm())
    with pytest.raises(DuplicateFirmStateError):
        space.add_firm_state(_firm())


def test_list_firms_returns_all_in_insertion_order():
    space = CorporateSpace()
    space.add_firm_state(_firm("firm:a"))
    space.add_firm_state(_firm("firm:b"))
    space.add_firm_state(_firm("firm:c"))

    listed = space.list_firms()
    assert [f.firm_id for f in listed] == ["firm:a", "firm:b", "firm:c"]


def test_list_firms_returns_empty_when_no_firms():
    space = CorporateSpace()
    assert space.list_firms() == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_includes_all_firms_sorted():
    space = CorporateSpace()
    space.add_firm_state(_firm("firm:b", sector="auto"))
    space.add_firm_state(_firm("firm:a", sector="tech"))

    snap = space.snapshot()
    assert snap["space_id"] == "corporate"
    assert snap["count"] == 2
    assert [item["firm_id"] for item in snap["firms"]] == ["firm:a", "firm:b"]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = CorporateSpace().snapshot()
    assert snap == {"space_id": "corporate", "count": 0, "firms": []}


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_firm_state_records_to_ledger():
    ledger = Ledger()
    space = CorporateSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_firm_state(_firm(sector="auto", tier="large"))

    records = ledger.filter(event_type="firm_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "firm:toyota"
    assert record.agent_id == "firm:toyota"
    assert record.payload["sector"] == "auto"
    assert record.payload["tier"] == "large"
    assert record.payload["status"] == "active"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "corporate"


def test_add_firm_state_does_not_record_when_no_ledger():
    space = CorporateSpace()
    # Should not raise when ledger is None.
    space.add_firm_state(_firm())
    assert space.get_firm_state("firm:toyota") is not None


# ---------------------------------------------------------------------------
# Helper accessors return None / () when world refs are missing
# ---------------------------------------------------------------------------


def test_get_balance_sheet_view_returns_none_when_unbound():
    space = CorporateSpace()
    assert space.get_balance_sheet_view("firm:toyota") is None


def test_get_constraint_evaluations_returns_empty_when_unbound():
    space = CorporateSpace()
    assert space.get_constraint_evaluations("firm:toyota") == ()


def test_get_visible_signals_returns_empty_when_unbound():
    space = CorporateSpace()
    assert space.get_visible_signals("firm:toyota") == ()
