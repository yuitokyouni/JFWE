from datetime import date

import pytest

from spaces.external.space import ExternalSpace
from spaces.external.state import (
    DuplicateExternalFactorStateError,
    DuplicateExternalSourceStateError,
    ExternalFactorState,
    ExternalSourceState,
)
from world.clock import Clock
from world.ledger import Ledger


def _factor(
    factor_id: str = "factor:usd_jpy",
    *,
    factor_type: str = "fx_rate",
    unit: str = "USD/JPY",
    status: str = "active",
    metadata: dict | None = None,
) -> ExternalFactorState:
    return ExternalFactorState(
        factor_id=factor_id,
        factor_type=factor_type,
        unit=unit,
        status=status,
        metadata=metadata or {},
    )


def _source(
    source_id: str = "source:imf",
    *,
    source_type: str = "international_organization",
    status: str = "active",
    metadata: dict | None = None,
) -> ExternalSourceState:
    return ExternalSourceState(
        source_id=source_id,
        source_type=source_type,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# ExternalFactorState dataclass
# ---------------------------------------------------------------------------


def test_factor_state_carries_required_fields():
    f = _factor()
    assert f.factor_id == "factor:usd_jpy"
    assert f.factor_type == "fx_rate"
    assert f.unit == "USD/JPY"
    assert f.status == "active"
    assert f.metadata == {}


def test_factor_state_rejects_empty_id():
    with pytest.raises(ValueError):
        ExternalFactorState(factor_id="")


def test_factor_state_to_dict_is_serializable():
    f = _factor(factor_type="commodity_price", unit="USD/barrel")
    assert f.to_dict() == {
        "factor_id": "factor:usd_jpy",
        "factor_type": "commodity_price",
        "unit": "USD/barrel",
        "status": "active",
        "metadata": {},
    }


def test_factor_state_is_immutable():
    f = _factor()
    with pytest.raises(Exception):
        f.unit = "EUR/JPY"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExternalSourceState dataclass
# ---------------------------------------------------------------------------


def test_external_source_state_carries_required_fields():
    s = _source()
    assert s.source_id == "source:imf"
    assert s.source_type == "international_organization"
    assert s.status == "active"
    assert s.metadata == {}


def test_external_source_state_rejects_empty_id():
    with pytest.raises(ValueError):
        ExternalSourceState(source_id="")


def test_external_source_state_to_dict_is_serializable():
    s = _source(source_type="data_vendor")
    assert s.to_dict() == {
        "source_id": "source:imf",
        "source_type": "data_vendor",
        "status": "active",
        "metadata": {},
    }


def test_external_source_state_is_immutable():
    s = _source()
    with pytest.raises(Exception):
        s.source_type = "central_bank"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExternalSpace factor CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_factor_state():
    space = ExternalSpace()
    f = _factor()
    space.add_factor_state(f)
    assert space.get_factor_state("factor:usd_jpy") is f


def test_get_factor_state_returns_none_for_unknown():
    space = ExternalSpace()
    assert space.get_factor_state("factor:unknown") is None


def test_duplicate_factor_rejected():
    space = ExternalSpace()
    space.add_factor_state(_factor())
    with pytest.raises(DuplicateExternalFactorStateError):
        space.add_factor_state(_factor())


def test_list_factors_returns_all_in_insertion_order():
    space = ExternalSpace()
    space.add_factor_state(_factor("factor:a"))
    space.add_factor_state(_factor("factor:b"))
    space.add_factor_state(_factor("factor:c"))

    listed = space.list_factors()
    assert [f.factor_id for f in listed] == ["factor:a", "factor:b", "factor:c"]


# ---------------------------------------------------------------------------
# ExternalSpace source CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_source_state():
    space = ExternalSpace()
    s = _source()
    space.add_source_state(s)
    assert space.get_source_state("source:imf") is s


def test_get_source_state_returns_none_for_unknown():
    space = ExternalSpace()
    assert space.get_source_state("source:unknown") is None


def test_duplicate_source_rejected():
    space = ExternalSpace()
    space.add_source_state(_source())
    with pytest.raises(DuplicateExternalSourceStateError):
        space.add_source_state(_source())


def test_list_sources_returns_all_in_insertion_order():
    space = ExternalSpace()
    space.add_source_state(_source("source:imf"))
    space.add_source_state(_source("source:world_bank"))
    space.add_source_state(_source("source:oecd"))

    listed = space.list_sources()
    assert [s.source_id for s in listed] == [
        "source:imf",
        "source:world_bank",
        "source:oecd",
    ]


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_sorts_factors_and_sources_deterministically():
    space = ExternalSpace()
    space.add_factor_state(_factor("factor:b"))
    space.add_factor_state(_factor("factor:a"))
    space.add_source_state(_source("source:y"))
    space.add_source_state(_source("source:x"))

    snap = space.snapshot()
    assert snap["space_id"] == "external"
    assert snap["factor_count"] == 2
    assert snap["source_count"] == 2
    assert [f["factor_id"] for f in snap["factors"]] == ["factor:a", "factor:b"]
    assert [s["source_id"] for s in snap["sources"]] == ["source:x", "source:y"]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = ExternalSpace().snapshot()
    assert snap == {
        "space_id": "external",
        "factor_count": 0,
        "source_count": 0,
        "factors": [],
        "sources": [],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_factor_records_to_ledger():
    ledger = Ledger()
    space = ExternalSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_factor_state(
        _factor(factor_type="commodity_price", unit="USD/barrel")
    )

    records = ledger.filter(event_type="external_factor_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "factor:usd_jpy"
    assert record.payload["factor_type"] == "commodity_price"
    assert record.payload["unit"] == "USD/barrel"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "external"


def test_add_source_records_to_ledger():
    ledger = Ledger()
    space = ExternalSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_source_state(_source(source_type="data_vendor"))

    records = ledger.filter(event_type="external_source_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "source:imf"
    assert record.payload["source_type"] == "data_vendor"


def test_add_state_does_not_record_when_no_ledger():
    space = ExternalSpace()
    space.add_factor_state(_factor())
    space.add_source_state(_source())
    assert space.get_factor_state("factor:usd_jpy") is not None
    assert space.get_source_state("source:imf") is not None
