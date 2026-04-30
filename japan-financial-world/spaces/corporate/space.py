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
        """
        Capture kernel references the space needs to read projections.

        Contract (see BaseSpace.bind for the full statement):
            - Idempotent: every assignment is gated on ``is None``, so a
              second call leaves the space in the same state as the first.
            - Fill-only: explicit refs supplied via the constructor are
              never overwritten.
            - Hot-swap / reload is out of scope.
        """
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
        """
        Return all registered firms in insertion order.

        v0.8 documents this as a stable invariant: ``list_firms()``
        preserves the order in which ``add_firm_state`` was called. This
        is useful for audit-style reads where "added Nth" is meaningful.
        Callers that want a deterministic, content-keyed ordering should
        use :meth:`snapshot`, which sorts by ``firm_id``.
        """
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
        """
        Return signals visible to ``observer_id``.

        In CorporateSpace the natural caller is querying "what does
        firm X see?", so ``observer_id`` is typically a firm id (e.g.,
        ``"firm:toyota"``). The argument is named generically because
        the underlying check is :meth:`SignalBook.list_visible_to`,
        which is observer-agnostic — any agent or space id is valid.

        Returns an empty tuple if no SignalBook is bound.
        """
        if self.signals is None:
            return ()
        return self.signals.list_visible_to(observer_id, as_of_date=as_of_date)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """
        Return a deterministic, JSON-friendly view of the space.

        Firms are sorted by ``firm_id`` so the output is stable across
        runs regardless of insertion order. Use :meth:`list_firms` if
        insertion order matters.
        """
        firms = sorted(
            (firm.to_dict() for firm in self._firms.values()),
            key=lambda item: item["firm_id"],
        )
        return {
            "space_id": self.space_id,
            "count": len(firms),
            "firms": firms,
        }
