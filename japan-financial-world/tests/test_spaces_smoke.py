from datetime import date

from spaces.banking.space import BankSpace
from spaces.corporate.space import CorporateSpace
from spaces.investors.space import InvestorSpace
from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def test_empty_spaces_are_invoked_by_frequency_for_one_year():
    kernel = _kernel()

    corporate = CorporateSpace()
    investors = InvestorSpace()
    bank = BankSpace()

    kernel.register_space(corporate)
    kernel.register_space(investors)
    kernel.register_space(bank)

    kernel.run(days=365)

    # Spaces are registered in the Registry under their world_id.
    assert "space:corporate" in kernel.registry
    assert "space:investors" in kernel.registry
    assert "space:banking" in kernel.registry

    # Each space generated an `object_registered` ledger record.
    space_registrations = [
        record
        for record in kernel.ledger.filter(event_type="object_registered")
        if record.object_id.startswith("space:")
    ]
    assert {record.object_id for record in space_registrations} == {
        "space:corporate",
        "space:investors",
        "space:banking",
    }

    def executed(task_id: str):
        return kernel.ledger.filter(event_type="task_executed", task_id=task_id)

    # Corporate: monthly (12) + quarterly (4) + yearly (1) = 17 invocations.
    assert len(executed("task:corporate_monthly")) == 12
    assert len(executed("task:corporate_quarterly")) == 4
    assert len(executed("task:corporate_yearly")) == 1

    # Investors: daily (365) + monthly (12) = 377 invocations.
    assert len(executed("task:investors_daily")) == 365
    assert len(executed("task:investors_monthly")) == 12

    # Banking: daily (365) + quarterly (4) = 369 invocations.
    assert len(executed("task:banking_daily")) == 365
    assert len(executed("task:banking_quarterly")) == 4

    # Quarter-ends fire on Mar/Jun/Sep/Dec last day.
    quarterly_dates = [
        record.simulation_date for record in executed("task:corporate_quarterly")
    ]
    assert quarterly_dates == [
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
        "2026-12-31",
    ]

    # Yearly fires once on year-end.
    yearly_dates = [
        record.simulation_date for record in executed("task:corporate_yearly")
    ]
    assert yearly_dates == ["2026-12-31"]

    # Clock landed on the day after the 365-day run.
    assert kernel.clock.current_date == date(2027, 1, 1)


def test_base_space_default_step_is_a_no_op():
    kernel = _kernel()
    corporate = CorporateSpace()

    kernel.register_space(corporate)
    kernel.run(days=31)

    # Spaces are not state-bearing in v0: nothing in state references space ids.
    snapshot = kernel.state.snapshot(kernel.clock.current_date)
    for layer_entries in snapshot.entries.values():
        for object_id in layer_entries:
            assert not object_id.startswith("space:")
