from datetime import date

import pytest

from spaces.banking.space import BankSpace
from spaces.banking.state import (
    BankState,
    DuplicateBankStateError,
    LendingExposure,
)
from world.clock import Clock
from world.ledger import Ledger


def _bank(
    bank_id: str = "bank:reference_bank_a",
    *,
    bank_type: str = "city_bank",
    tier: str = "large",
    status: str = "active",
    metadata: dict | None = None,
) -> BankState:
    return BankState(
        bank_id=bank_id,
        bank_type=bank_type,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# BankState dataclass
# ---------------------------------------------------------------------------


def test_bank_state_carries_required_fields():
    bank = _bank()
    assert bank.bank_id == "bank:reference_bank_a"
    assert bank.bank_type == "city_bank"
    assert bank.tier == "large"
    assert bank.status == "active"
    assert bank.metadata == {}


def test_bank_state_rejects_empty_bank_id():
    with pytest.raises(ValueError):
        BankState(bank_id="")


def test_bank_state_to_dict_is_serializable():
    bank = _bank(metadata={"founded": "1880"})
    payload = bank.to_dict()
    assert payload == {
        "bank_id": "bank:reference_bank_a",
        "bank_type": "city_bank",
        "tier": "large",
        "status": "active",
        "metadata": {"founded": "1880"},
    }


def test_bank_state_is_immutable():
    bank = _bank()
    with pytest.raises(Exception):
        bank.bank_type = "regional_bank"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LendingExposure dataclass
# ---------------------------------------------------------------------------


def test_lending_exposure_carries_minimum_fields():
    exposure = LendingExposure(
        contract_id="contract:loan_001",
        lender_id="bank:reference_bank_a",
        borrower_id="firm:reference_manufacturer_a",
        principal=1_000_000.0,
        contract_type="loan",
        status="active",
        collateral_asset_ids=("asset:property_a",),
    )
    assert exposure.contract_id == "contract:loan_001"
    assert exposure.lender_id == "bank:reference_bank_a"
    assert exposure.borrower_id == "firm:reference_manufacturer_a"
    assert exposure.principal == 1_000_000.0
    assert exposure.contract_type == "loan"
    assert exposure.status == "active"
    assert exposure.collateral_asset_ids == ("asset:property_a",)


def test_lending_exposure_allows_missing_borrower():
    exposure = LendingExposure(
        contract_id="contract:loan_002",
        lender_id="bank:reference_bank_a",
        borrower_id=None,
        principal=500_000.0,
        contract_type="loan",
        status="active",
    )
    assert exposure.borrower_id is None
    assert exposure.collateral_asset_ids == ()


def test_lending_exposure_to_dict_is_serializable():
    exposure = LendingExposure(
        contract_id="contract:loan_001",
        lender_id="bank:reference_bank_a",
        borrower_id="firm:reference_manufacturer_a",
        principal=1_000_000.0,
        contract_type="loan",
        status="active",
        collateral_asset_ids=("asset:property_a",),
    )
    assert exposure.to_dict() == {
        "contract_id": "contract:loan_001",
        "lender_id": "bank:reference_bank_a",
        "borrower_id": "firm:reference_manufacturer_a",
        "principal": 1_000_000.0,
        "contract_type": "loan",
        "status": "active",
        "collateral_asset_ids": ["asset:property_a"],
    }


# ---------------------------------------------------------------------------
# BankSpace state CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_bank_state():
    space = BankSpace()
    bank = _bank()
    space.add_bank_state(bank)
    assert space.get_bank_state("bank:reference_bank_a") is bank


def test_get_bank_state_returns_none_for_unknown():
    space = BankSpace()
    assert space.get_bank_state("bank:unknown") is None


def test_duplicate_bank_state_rejected():
    space = BankSpace()
    space.add_bank_state(_bank())
    with pytest.raises(DuplicateBankStateError):
        space.add_bank_state(_bank())


def test_list_banks_returns_all_in_insertion_order():
    space = BankSpace()
    space.add_bank_state(_bank("bank:a"))
    space.add_bank_state(_bank("bank:b"))
    space.add_bank_state(_bank("bank:c"))

    listed = space.list_banks()
    assert [b.bank_id for b in listed] == ["bank:a", "bank:b", "bank:c"]


def test_list_banks_returns_empty_when_no_banks():
    space = BankSpace()
    assert space.list_banks() == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_includes_all_banks_sorted():
    space = BankSpace()
    space.add_bank_state(_bank("bank:b", bank_type="trust_bank"))
    space.add_bank_state(_bank("bank:a", bank_type="city_bank"))

    snap = space.snapshot()
    assert snap["space_id"] == "banking"
    assert snap["count"] == 2
    assert [item["bank_id"] for item in snap["banks"]] == ["bank:a", "bank:b"]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = BankSpace().snapshot()
    assert snap == {"space_id": "banking", "count": 0, "banks": []}


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_bank_state_records_to_ledger():
    ledger = Ledger()
    space = BankSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_bank_state(_bank(bank_type="regional_bank", tier="mid"))

    records = ledger.filter(event_type="bank_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "bank:reference_bank_a"
    assert record.agent_id == "bank:reference_bank_a"
    assert record.payload["bank_type"] == "regional_bank"
    assert record.payload["tier"] == "mid"
    assert record.payload["status"] == "active"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "banking"


def test_add_bank_state_does_not_record_when_no_ledger():
    space = BankSpace()
    space.add_bank_state(_bank())  # should not raise
    assert space.get_bank_state("bank:reference_bank_a") is not None


# ---------------------------------------------------------------------------
# Helper accessors return None / () when world refs are missing
# ---------------------------------------------------------------------------


def test_get_balance_sheet_view_returns_none_when_unbound():
    space = BankSpace()
    assert space.get_balance_sheet_view("bank:reference_bank_a") is None


def test_get_constraint_evaluations_returns_empty_when_unbound():
    space = BankSpace()
    assert space.get_constraint_evaluations("bank:reference_bank_a") == ()


def test_get_visible_signals_returns_empty_when_unbound():
    space = BankSpace()
    assert space.get_visible_signals("bank:reference_bank_a") == ()


def test_list_contracts_for_bank_returns_empty_when_unbound():
    space = BankSpace()
    assert space.list_contracts_for_bank("bank:reference_bank_a") == ()


def test_list_lending_exposures_returns_empty_when_unbound():
    space = BankSpace()
    assert space.list_lending_exposures("bank:reference_bank_a") == ()
