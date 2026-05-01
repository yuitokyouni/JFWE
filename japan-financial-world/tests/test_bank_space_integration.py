from datetime import date

from spaces.banking.space import BankSpace
from spaces.banking.state import BankState
from world.clock import Clock
from world.constraints import ConstraintRecord
from world.contracts import ContractRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Scheduler
from world.signals import InformationSignal
from world.state import State


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _loan(
    *,
    contract_id: str,
    lender: str,
    borrower: str,
    principal: float,
    collateral: tuple[str, ...] = (),
    status: str = "active",
) -> ContractRecord:
    return ContractRecord(
        contract_id=contract_id,
        contract_type="loan",
        parties=(lender, borrower),
        principal=principal,
        collateral_asset_ids=collateral,
        status=status,
        metadata={"lender_id": lender, "borrower_id": borrower},
    )


# ---------------------------------------------------------------------------
# bind() wires kernel projections (mirror of CorporateSpace tests)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    bank_space = BankSpace()

    # Before registration -> no refs.
    assert bank_space.balance_sheets is None
    assert bank_space.contracts is None
    assert bank_space.constraint_evaluator is None
    assert bank_space.signals is None

    kernel.register_space(bank_space)

    # After registration -> kernel refs are wired in.
    assert bank_space.registry is kernel.registry
    assert bank_space.contracts is kernel.contracts
    assert bank_space.balance_sheets is kernel.balance_sheets
    assert bank_space.constraint_evaluator is kernel.constraint_evaluator
    assert bank_space.signals is kernel.signals
    assert bank_space.ledger is kernel.ledger
    assert bank_space.clock is kernel.clock


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    bank_space = BankSpace(ledger=other_ledger)

    kernel.register_space(bank_space)

    # Explicit ledger wins; bind only fills in unset refs.
    assert bank_space.ledger is other_ledger
    # Other refs were unset, so bind filled them in.
    assert bank_space.contracts is kernel.contracts


def test_bind_is_idempotent():
    kernel = _kernel()
    bank_space = BankSpace()
    kernel.register_space(bank_space)

    contracts_after_first = bank_space.contracts
    ledger_after_first = bank_space.ledger

    # Calling bind again should leave the space identical.
    bank_space.bind(kernel)

    assert bank_space.contracts is contracts_after_first
    assert bank_space.ledger is ledger_after_first


# ---------------------------------------------------------------------------
# Reading projections through the space
# ---------------------------------------------------------------------------


def test_bank_space_can_read_balance_sheet_view():
    kernel = _kernel()
    kernel.ownership.add_position("bank:reference_bank_a", "asset:cash", 10_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")

    bank_space = BankSpace()
    kernel.register_space(bank_space)
    bank_space.add_bank_state(
        BankState(bank_id="bank:reference_bank_a", bank_type="city_bank", tier="large")
    )

    view = bank_space.get_balance_sheet_view("bank:reference_bank_a")
    assert view is not None
    assert view.agent_id == "bank:reference_bank_a"
    assert view.asset_value == 10_000.0
    assert view.as_of_date == "2026-01-01"


def test_bank_space_can_read_constraint_evaluations():
    kernel = _kernel()
    kernel.ownership.add_position("bank:reference_bank_a", "asset:cash", 10_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_001",
            lender="bank:reference_bank_a",
            borrower="firm:reference_manufacturer_a",
            principal=2_000.0,
        )
    )
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:bank_lev",
            owner_id="bank:reference_bank_a",
            constraint_type="max_leverage",
            threshold=0.7,
            comparison="<=",
        )
    )

    bank_space = BankSpace()
    kernel.register_space(bank_space)

    evaluations = bank_space.get_constraint_evaluations("bank:reference_bank_a")
    # Bank holds 10_000 in cash, lent 2_000 (financial asset), no liabilities
    # against this bank as borrower -> leverage = 0 / 12_000 = 0 -> ok.
    assert len(evaluations) == 1
    assert evaluations[0].status == "ok"


def test_bank_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rate_decision",
            signal_type="policy_announcement",
            subject_id="agent:central_bank",
            source_id="agent:central_bank",
            published_date="2026-01-01",
            payload={"rate": 0.005},
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_memo",
            signal_type="internal_memo",
            subject_id="bank:reference_bank_a",
            source_id="bank:reference_bank_a",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:legal",)},
        )
    )

    bank_space = BankSpace()
    kernel.register_space(bank_space)

    visible_to_bank = bank_space.get_visible_signals("bank:reference_bank_a")
    visible_ids = {s.signal_id for s in visible_to_bank}

    assert "signal:rate_decision" in visible_ids
    assert "signal:internal_memo" not in visible_ids


# ---------------------------------------------------------------------------
# Contract-derived views
# ---------------------------------------------------------------------------


def test_list_contracts_for_bank_returns_all_contracts_with_bank_as_party():
    kernel = _kernel()
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_001",
            lender="bank:reference_bank_a",
            borrower="firm:reference_manufacturer_a",
            principal=1_000.0,
        )
    )
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_002",
            lender="bank:smbc",
            borrower="firm:sony",
            principal=2_000.0,
        )
    )
    # A contract where mufg is borrower (interbank loan).
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_003",
            lender="bank:smbc",
            borrower="bank:reference_bank_a",
            principal=500.0,
        )
    )

    bank_space = BankSpace()
    kernel.register_space(bank_space)

    contracts = bank_space.list_contracts_for_bank("bank:reference_bank_a")
    contract_ids = {c.contract_id for c in contracts}
    # Every contract where bank:reference_bank_a appears as a party.
    assert contract_ids == {"contract:loan_001", "contract:loan_003"}


def test_list_lending_exposures_filters_to_lender_role():
    kernel = _kernel()
    # Two loans where mufg is lender.
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_001",
            lender="bank:reference_bank_a",
            borrower="firm:reference_manufacturer_a",
            principal=1_000_000.0,
            collateral=("asset:property_a",),
        )
    )
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_002",
            lender="bank:reference_bank_a",
            borrower="firm:sony",
            principal=500_000.0,
        )
    )
    # An interbank loan where mufg is borrower (must NOT be in lending exposures).
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_003",
            lender="bank:smbc",
            borrower="bank:reference_bank_a",
            principal=300_000.0,
        )
    )

    bank_space = BankSpace()
    kernel.register_space(bank_space)

    exposures = bank_space.list_lending_exposures("bank:reference_bank_a")
    exposure_ids = {e.contract_id for e in exposures}
    assert exposure_ids == {"contract:loan_001", "contract:loan_002"}

    # Borrower id is exposed from metadata.
    by_id = {e.contract_id: e for e in exposures}
    assert by_id["contract:loan_001"].borrower_id == "firm:reference_manufacturer_a"
    assert by_id["contract:loan_001"].principal == 1_000_000.0
    assert by_id["contract:loan_001"].collateral_asset_ids == ("asset:property_a",)
    assert by_id["contract:loan_002"].borrower_id == "firm:sony"
    assert by_id["contract:loan_002"].collateral_asset_ids == ()


def test_list_lending_exposures_does_not_infer_role_from_parties_order():
    """
    A contract with parties=(bank:x, firm:y) but no metadata roles must
    NOT be classified as a lending exposure for bank:x. v0.9 requires
    explicit metadata tagging.
    """
    kernel = _kernel()
    kernel.contracts.add_contract(
        ContractRecord(
            contract_id="contract:untagged",
            contract_type="loan",
            parties=("bank:reference_bank_a", "firm:reference_manufacturer_a"),
            principal=1_000.0,
            # no metadata.lender_id / borrower_id
        )
    )

    bank_space = BankSpace()
    kernel.register_space(bank_space)

    assert bank_space.list_lending_exposures("bank:reference_bank_a") == ()
    # But the broader contracts-for-bank view does include it
    # (because the bank IS in parties).
    contracts = bank_space.list_contracts_for_bank("bank:reference_bank_a")
    assert {c.contract_id for c in contracts} == {"contract:untagged"}


def test_list_lending_exposures_preserves_status():
    kernel = _kernel()
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:settled",
            lender="bank:reference_bank_a",
            borrower="firm:reference_manufacturer_a",
            principal=1_000.0,
            status="settled",
        )
    )
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:active",
            lender="bank:reference_bank_a",
            borrower="firm:sony",
            principal=2_000.0,
            status="active",
        )
    )

    bank_space = BankSpace()
    kernel.register_space(bank_space)

    exposures = {
        e.contract_id: e for e in bank_space.list_lending_exposures("bank:reference_bank_a")
    }
    # v0.9 does NOT filter by status — it copies status verbatim from the
    # contract. Callers decide what to do.
    assert exposures["contract:settled"].status == "settled"
    assert exposures["contract:active"].status == "active"


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_bank_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.ownership.add_position("bank:reference_bank_a", "asset:cash", 10_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")
    kernel.contracts.add_contract(
        _loan(
            contract_id="contract:loan_001",
            lender="bank:reference_bank_a",
            borrower="firm:reference_manufacturer_a",
            principal=1_000.0,
        )
    )
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:bank_lev",
            owner_id="bank:reference_bank_a",
            constraint_type="max_leverage",
            threshold=0.7,
            comparison="<=",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rate_decision",
            signal_type="policy_announcement",
            subject_id="agent:central_bank",
            source_id="agent:central_bank",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    bank_space = BankSpace()
    kernel.register_space(bank_space)
    bank_space.add_bank_state(BankState(bank_id="bank:reference_bank_a"))

    # Read every projection through the space.
    bank_space.get_balance_sheet_view("bank:reference_bank_a")
    bank_space.get_constraint_evaluations("bank:reference_bank_a")
    bank_space.get_visible_signals("bank:reference_bank_a")
    bank_space.list_contracts_for_bank("bank:reference_bank_a")
    bank_space.list_lending_exposures("bank:reference_bank_a")
    bank_space.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_bank_space_runs_for_one_year_after_state_added():
    """
    BankSpace's scheduler integration must continue to work after v0.9.
    Daily and quarterly tasks should still fire at expected counts.
    """
    kernel = _kernel()
    bank_space = BankSpace()
    kernel.register_space(bank_space)
    bank_space.add_bank_state(BankState(bank_id="bank:reference_bank_a"))

    kernel.run(days=365)

    daily = kernel.ledger.filter(
        event_type="task_executed", task_id="task:banking_daily"
    )
    quarterly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:banking_quarterly"
    )
    assert len(daily) == 365
    assert len(quarterly) == 4
