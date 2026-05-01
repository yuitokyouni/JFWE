from datetime import date

from spaces.corporate.space import CorporateSpace
from spaces.corporate.state import FirmState
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
    contract_id: str = "contract:loan_001",
    lender: str,
    borrower: str,
    principal: float,
) -> ContractRecord:
    return ContractRecord(
        contract_id=contract_id,
        contract_type="loan",
        parties=(lender, borrower),
        principal=principal,
        metadata={"lender_id": lender, "borrower_id": borrower},
    )


# ---------------------------------------------------------------------------
# bind() wires kernel projections
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    corporate = CorporateSpace()

    # Before registration -> no refs.
    assert corporate.balance_sheets is None
    assert corporate.constraint_evaluator is None
    assert corporate.signals is None

    kernel.register_space(corporate)

    # After registration -> kernel refs are wired in.
    assert corporate.registry is kernel.registry
    assert corporate.balance_sheets is kernel.balance_sheets
    assert corporate.constraint_evaluator is kernel.constraint_evaluator
    assert corporate.signals is kernel.signals
    assert corporate.ledger is kernel.ledger
    assert corporate.clock is kernel.clock


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    corporate = CorporateSpace(ledger=other_ledger)

    kernel.register_space(corporate)

    # Explicit ledger wins; bind only fills in unset refs.
    assert corporate.ledger is other_ledger
    # Other refs were unset, so bind filled them in.
    assert corporate.balance_sheets is kernel.balance_sheets


# ---------------------------------------------------------------------------
# Reading projections through the space
# ---------------------------------------------------------------------------


def test_corporate_space_can_read_balance_sheet_view():
    kernel = _kernel()
    kernel.ownership.add_position("firm:reference_manufacturer_a", "asset:cash", 1_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")

    corporate = CorporateSpace()
    kernel.register_space(corporate)
    corporate.add_firm_state(
        FirmState(firm_id="firm:reference_manufacturer_a", sector="auto", tier="large")
    )

    view = corporate.get_balance_sheet_view("firm:reference_manufacturer_a")
    assert view is not None
    assert view.agent_id == "firm:reference_manufacturer_a"
    assert view.asset_value == 1_000.0
    # When no as_of_date is passed, the kernel's clock supplies it.
    assert view.as_of_date == "2026-01-01"


def test_corporate_space_balance_sheet_view_for_unknown_firm_is_empty_view():
    kernel = _kernel()
    corporate = CorporateSpace()
    kernel.register_space(corporate)

    # Unknown firm -> projector still returns a view (empty), not None.
    view = corporate.get_balance_sheet_view("firm:ghost")
    assert view is not None
    assert view.asset_value == 0.0
    assert view.liabilities == 0.0
    assert view.net_asset_value == 0.0


def test_corporate_space_can_read_constraint_evaluations():
    kernel = _kernel()
    kernel.ownership.add_position("firm:reference_manufacturer_a", "asset:cash", 1_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")
    kernel.contracts.add_contract(
        _loan(lender="agent:bank_a", borrower="firm:reference_manufacturer_a", principal=500.0)
    )
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:reference_manufacturer_leverage_lite",
            owner_id="firm:reference_manufacturer_a",
            constraint_type="max_leverage",
            threshold=0.7,
            comparison="<=",
        )
    )

    corporate = CorporateSpace()
    kernel.register_space(corporate)
    corporate.add_firm_state(FirmState(firm_id="firm:reference_manufacturer_a"))

    evaluations = corporate.get_constraint_evaluations("firm:reference_manufacturer_a")
    assert len(evaluations) == 1
    assert evaluations[0].status == "ok"
    assert evaluations[0].current_value == 0.5


def test_corporate_space_constraint_evaluations_empty_when_no_constraints():
    kernel = _kernel()
    corporate = CorporateSpace()
    kernel.register_space(corporate)

    assert corporate.get_constraint_evaluations("firm:no_constraints") == ()


def test_corporate_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rating_001",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="agent:rating_agency",
            published_date="2026-01-01",
            payload={"rating": "AA-"},
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_001",
            signal_type="internal_memo",
            subject_id="firm:reference_manufacturer_a",
            source_id="firm:reference_manufacturer_a",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:legal",)},
        )
    )

    corporate = CorporateSpace()
    kernel.register_space(corporate)

    visible_to_corporate = corporate.get_visible_signals("corporate")
    visible_to_legal = corporate.get_visible_signals("agent:legal")

    visible_ids = {s.signal_id for s in visible_to_corporate}
    legal_ids = {s.signal_id for s in visible_to_legal}

    # Public signal reaches corporate; restricted internal_memo does not.
    assert "signal:rating_001" in visible_ids
    assert "signal:internal_001" not in visible_ids
    # Legal sees both.
    assert legal_ids == {"signal:rating_001", "signal:internal_001"}


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_corporate_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.ownership.add_position("firm:reference_manufacturer_a", "asset:cash", 1_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")
    kernel.contracts.add_contract(
        _loan(lender="agent:bank_a", borrower="firm:reference_manufacturer_a", principal=500.0)
    )
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:reference_manufacturer_leverage_lite",
            owner_id="firm:reference_manufacturer_a",
            constraint_type="max_leverage",
            threshold=0.7,
            comparison="<=",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rating_001",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="agent:rating_agency",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    corporate = CorporateSpace()
    kernel.register_space(corporate)
    corporate.add_firm_state(FirmState(firm_id="firm:reference_manufacturer_a"))

    # Read every projection through the space.
    corporate.get_balance_sheet_view("firm:reference_manufacturer_a")
    corporate.get_constraint_evaluations("firm:reference_manufacturer_a")
    corporate.get_visible_signals("corporate")
    corporate.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_corporate_space_runs_for_one_year_after_state_added():
    """
    v0.8 must not break v0.2 scheduling. With firm state added, the
    space still gets called by the scheduler at its declared
    frequencies, and the ledger still records each invocation.
    """
    kernel = _kernel()
    corporate = CorporateSpace()
    kernel.register_space(corporate)
    corporate.add_firm_state(FirmState(firm_id="firm:reference_manufacturer_a"))

    kernel.run(days=365)

    # 12 monthly + 4 quarterly + 1 yearly invocations.
    monthly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:corporate_monthly"
    )
    quarterly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:corporate_quarterly"
    )
    yearly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:corporate_yearly"
    )
    assert len(monthly) == 12
    assert len(quarterly) == 4
    assert len(yearly) == 1
