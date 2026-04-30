from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from spaces.base import BaseSpace
from spaces.corporate.state import DuplicateFirmStateError, FirmState
from world.balance_sheet import BalanceSheetProjector, BalanceSheetView
from world.clock import Clock
from world.constraints import ConstraintEvaluation, ConstraintEvaluator
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Frequency
from world.signals import InformationSignal, SignalBook


@dataclass
class CorporateSpace(BaseSpace):
    """
    Corporate Space — minimum internal state for firms.

    v0.8 scope:
        - hold a mapping of firm_id -> FirmState (identity-level only)
        - read kernel-level projections (balance sheets, constraints,
          signals) without mutating any source book
        - log firm_state_added when a firm enters the space

    v0.8 explicitly does NOT implement:
        - revenue / profit / earnings logic
        - asset sale or borrowing decisions
        - bank credit reactions, investor reactions, market clearing
        - any mutation of OwnershipBook / ContractBook / PriceBook /
          ConstraintBook / SignalBook
        - any mutation of other spaces (BankSpace, InvestorSpace, etc.)

    Kernel projections are wired in via bind() when the space is
    registered. Tests may also pass them at construction. Refs are not
    overwritten by bind() if already set, so explicit construction wins.
    """

    space_id: str = "corporate"
    frequencies: tuple[Frequency, ...] = (
        Frequency.MONTHLY,
        Frequency.QUARTERLY,
        Frequency.YEARLY,
    )
    registry: Registry | None = None
    balance_sheets: BalanceSheetProjector | None = None
    constraint_evaluator: ConstraintEvaluator | None = None
    signals: SignalBook | None = None
    ledger: Ledger | None = None
    clock: Clock | None = None
    _firms: dict[str, FirmState] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Lifecycle hook
    # ------------------------------------------------------------------

    def bind(self, kernel: Any) -> None:
        if self.registry is None:
            self.registry = kernel.registry
        if self.balance_sheets is None:
            self.balance_sheets = kernel.balance_sheets
        if self.constraint_evaluator is None:
            self.constraint_evaluator = kernel.constraint_evaluator
        if self.signals is None:
            self.signals = kernel.signals
        if self.ledger is None:
            self.ledger = kernel.ledger
        if self.clock is None:
            self.clock = kernel.clock

    # ------------------------------------------------------------------
    # Firm state CRUD
    # ------------------------------------------------------------------

    def add_firm_state(self, firm_state: FirmState) -> FirmState:
        if firm_state.firm_id in self._firms:
            raise DuplicateFirmStateError(
                f"Duplicate firm_id: {firm_state.firm_id}"
            )
        self._firms[firm_state.firm_id] = firm_state

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="firm_state_added",
                simulation_date=simulation_date,
                object_id=firm_state.firm_id,
                agent_id=firm_state.firm_id,
                payload={
                    "firm_id": firm_state.firm_id,
                    "sector": firm_state.sector,
                    "tier": firm_state.tier,
                    "status": firm_state.status,
                },
                space_id=self.space_id,
            )
        return firm_state

    def get_firm_state(self, firm_id: str) -> FirmState | None:
        return self._firms.get(firm_id)

    def list_firms(self) -> tuple[FirmState, ...]:
        return tuple(self._firms.values())

    # ------------------------------------------------------------------
    # Read-only world projections
    # ------------------------------------------------------------------

    def get_balance_sheet_view(
        self,
        firm_id: str,
        *,
        as_of_date: date | str | None = None,
    ) -> BalanceSheetView | None:
        if self.balance_sheets is None:
            return None
        try:
            return self.balance_sheets.build_view(firm_id, as_of_date=as_of_date)
        except ValueError:
            # No clock and no explicit date: cannot resolve as_of.
            return None

    def get_constraint_evaluations(
        self,
        firm_id: str,
        *,
        as_of_date: date | str | None = None,
    ) -> tuple[ConstraintEvaluation, ...]:
        if self.constraint_evaluator is None:
            return ()
        try:
            return self.constraint_evaluator.evaluate_owner(
                firm_id, as_of_date=as_of_date
            )
        except ValueError:
            return ()

    def get_visible_signals(
        self,
        observer_id: str,
        *,
        as_of_date: date | str | None = None,
    ) -> tuple[InformationSignal, ...]:
        if self.signals is None:
            return ()
        return self.signals.list_visible_to(observer_id, as_of_date=as_of_date)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        firms = sorted(
            (firm.to_dict() for firm in self._firms.values()),
            key=lambda item: item["firm_id"],
        )
        return {
            "space_id": self.space_id,
            "count": len(firms),
            "firms": firms,
        }
