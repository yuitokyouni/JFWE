from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from world.balance_sheet import BalanceSheetProjector, BalanceSheetView
from world.clock import Clock
from world.ledger import Ledger


_VALID_STATUSES = frozenset({"ok", "warning", "breached", "unknown"})
_VALID_COMPARISONS = frozenset({"<=", "<", ">=", ">", "=="})


class ConstraintError(Exception):
    """Base class for constraint-book errors."""


class DuplicateConstraintError(ConstraintError):
    """Raised when a constraint_id is added twice."""


class UnknownConstraintError(ConstraintError, KeyError):
    """Raised when a constraint_id is not found."""


@dataclass(frozen=True)
class ConstraintRecord:
    """
    A declarative financial constraint attached to an agent.

    A ConstraintRecord describes what to check, not what to do when the
    check fails. v0.6 evaluators report ok / warning / breached / unknown.
    They never trigger sales, downgrades, defaults, or any other behavior.
    """

    constraint_id: str
    owner_id: str
    constraint_type: str
    threshold: float
    comparison: str
    target_ids: tuple[str, ...] = field(default_factory=tuple)
    warning_threshold: float | None = None
    severity: str = "warning"
    source: str = "system"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise ValueError("constraint_id is required")
        if not self.owner_id:
            raise ValueError("owner_id is required")
        if not self.constraint_type:
            raise ValueError("constraint_type is required")
        if self.comparison not in _VALID_COMPARISONS:
            raise ValueError(
                f"comparison must be one of {sorted(_VALID_COMPARISONS)}; "
                f"got {self.comparison!r}"
            )
        object.__setattr__(self, "target_ids", tuple(self.target_ids))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "owner_id": self.owner_id,
            "constraint_type": self.constraint_type,
            "threshold": self.threshold,
            "comparison": self.comparison,
            "target_ids": list(self.target_ids),
            "warning_threshold": self.warning_threshold,
            "severity": self.severity,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ConstraintEvaluation:
    """
    The result of evaluating a single constraint against a balance sheet view.

    status semantics:
        ok       — current value satisfies the constraint with margin.
        warning  — current value satisfies the threshold but crossed the
                   warning_threshold (closer to the breach boundary).
        breached — current value violates the constraint.
        unknown  — current value cannot be derived (missing data, divide
                   by zero, or unsupported constraint_type). Reason is
                   recorded in metadata["reason"] and in message.
    """

    constraint_id: str
    owner_id: str
    as_of_date: str
    status: str
    current_value: float | None
    threshold: float
    message: str = ""
    related_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_STATUSES)}; "
                f"got {self.status!r}"
            )
        object.__setattr__(self, "related_ids", tuple(self.related_ids))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "owner_id": self.owner_id,
            "as_of_date": self.as_of_date,
            "status": self.status,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "message": self.message,
            "related_ids": list(self.related_ids),
            "metadata": dict(self.metadata),
        }


@dataclass
class ConstraintBook:
    """
    Storage for declarative constraints. Stores facts; evaluates nothing.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _constraints: dict[str, ConstraintRecord] = field(default_factory=dict)

    def add_constraint(self, record: ConstraintRecord) -> ConstraintRecord:
        if record.constraint_id in self._constraints:
            raise DuplicateConstraintError(
                f"Duplicate constraint_id: {record.constraint_id}"
            )
        self._constraints[record.constraint_id] = record

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="constraint_added",
                simulation_date=simulation_date,
                object_id=record.constraint_id,
                agent_id=record.owner_id,
                source=record.source,
                payload={
                    "constraint_id": record.constraint_id,
                    "owner_id": record.owner_id,
                    "constraint_type": record.constraint_type,
                    "threshold": record.threshold,
                    "comparison": record.comparison,
                    "warning_threshold": record.warning_threshold,
                    "severity": record.severity,
                    "target_ids": list(record.target_ids),
                },
                space_id="constraints",
            )
        return record

    def get_constraint(self, constraint_id: str) -> ConstraintRecord:
        try:
            return self._constraints[constraint_id]
        except KeyError as exc:
            raise UnknownConstraintError(
                f"Constraint not found: {constraint_id!r}"
            ) from exc

    def list_by_owner(self, owner_id: str) -> tuple[ConstraintRecord, ...]:
        return tuple(
            record
            for record in self._constraints.values()
            if record.owner_id == owner_id
        )

    def list_by_type(self, constraint_type: str) -> tuple[ConstraintRecord, ...]:
        return tuple(
            record
            for record in self._constraints.values()
            if record.constraint_type == constraint_type
        )

    def all_constraints(self) -> tuple[ConstraintRecord, ...]:
        return tuple(self._constraints.values())

    def snapshot(self) -> dict[str, Any]:
        constraints = sorted(
            (record.to_dict() for record in self._constraints.values()),
            key=lambda item: item["constraint_id"],
        )
        return {"count": len(constraints), "constraints": constraints}


# ---------------------------------------------------------------------------
# Constraint-type derivers.
#
# Each deriver maps (BalanceSheetView, target_ids) to (current_value, reason).
# When current_value is None, the evaluator returns status="unknown" and
# attaches the reason to the evaluation. Derivers must not raise; they must
# express failure through (None, reason).
# ---------------------------------------------------------------------------


def _derive_max_leverage(
    view: BalanceSheetView,
    target_ids: tuple[str, ...],
) -> tuple[float | None, str | None]:
    if view.asset_value == 0:
        return None, "asset_value is zero; cannot compute leverage"
    return view.liabilities / view.asset_value, None


def _derive_min_net_asset_value(
    view: BalanceSheetView,
    target_ids: tuple[str, ...],
) -> tuple[float | None, str | None]:
    return view.net_asset_value, None


def _derive_min_cash_like_assets(
    view: BalanceSheetView,
    target_ids: tuple[str, ...],
) -> tuple[float | None, str | None]:
    if view.cash_like_assets is None:
        return None, "cash_like_assets unavailable (no registry-based detection)"
    return view.cash_like_assets, None


def _derive_min_collateral_coverage(
    view: BalanceSheetView,
    target_ids: tuple[str, ...],
) -> tuple[float | None, str | None]:
    if view.collateral_value is None:
        return None, "collateral_value unavailable"
    if view.debt_principal is None or view.debt_principal == 0:
        return None, "debt_principal is zero or unavailable"
    return view.collateral_value / view.debt_principal, None


def _derive_max_single_asset_concentration(
    view: BalanceSheetView,
    target_ids: tuple[str, ...],
) -> tuple[float | None, str | None]:
    if view.asset_value == 0 or not view.asset_breakdown:
        return None, "asset_breakdown is empty; cannot compute concentration"

    if target_ids:
        relevant = {
            asset_id: value
            for asset_id, value in view.asset_breakdown.items()
            if asset_id in target_ids
        }
        if not relevant:
            return None, "none of target_ids are present in asset_breakdown"
    else:
        relevant = dict(view.asset_breakdown)

    return max(relevant.values()) / view.asset_value, None


_DERIVERS = {
    "max_leverage": _derive_max_leverage,
    "min_net_asset_value": _derive_min_net_asset_value,
    "min_cash_like_assets": _derive_min_cash_like_assets,
    "min_collateral_coverage": _derive_min_collateral_coverage,
    "max_single_asset_concentration": _derive_max_single_asset_concentration,
}


SUPPORTED_CONSTRAINT_TYPES = frozenset(_DERIVERS.keys())


def _is_violation(current: float, ref: float, comparison: str) -> bool:
    """
    Return True when `current` violates the constraint expressed as
    `current comparison ref`.

    Examples:
        comparison="<=" with current=0.8 and ref=0.7 -> True (violates)
        comparison=">=" with current=50  and ref=100 -> True (violates)
    """
    if comparison == "<=":
        return current > ref
    if comparison == "<":
        return current >= ref
    if comparison == ">=":
        return current < ref
    if comparison == ">":
        return current <= ref
    if comparison == "==":
        return current != ref
    raise ValueError(f"Unsupported comparison: {comparison!r}")


def _classify(
    current: float,
    threshold: float,
    warning_threshold: float | None,
    comparison: str,
) -> str:
    if _is_violation(current, threshold, comparison):
        return "breached"
    if warning_threshold is not None and _is_violation(
        current, warning_threshold, comparison
    ):
        return "warning"
    return "ok"


@dataclass
class ConstraintEvaluator:
    """
    Read-only evaluator that joins ConstraintBook with a
    BalanceSheetProjector and produces ConstraintEvaluation records.

    The evaluator must not mutate any source book. It writes only to the
    ledger, and only when one is configured. Higher-level methods compose
    on evaluate_constraint, which is the one place that emits
    `constraint_evaluated` ledger records.
    """

    book: ConstraintBook
    projector: BalanceSheetProjector
    clock: Clock | None = None
    ledger: Ledger | None = None

    def evaluate_constraint(
        self,
        constraint: ConstraintRecord,
        view: BalanceSheetView,
    ) -> ConstraintEvaluation:
        deriver = _DERIVERS.get(constraint.constraint_type)

        if deriver is None:
            evaluation = ConstraintEvaluation(
                constraint_id=constraint.constraint_id,
                owner_id=constraint.owner_id,
                as_of_date=view.as_of_date,
                status="unknown",
                current_value=None,
                threshold=constraint.threshold,
                message=(
                    f"unsupported constraint_type: {constraint.constraint_type!r}"
                ),
                related_ids=constraint.target_ids,
                metadata={"reason": "unsupported_constraint_type"},
            )
        else:
            current, reason = deriver(view, constraint.target_ids)
            if current is None:
                evaluation = ConstraintEvaluation(
                    constraint_id=constraint.constraint_id,
                    owner_id=constraint.owner_id,
                    as_of_date=view.as_of_date,
                    status="unknown",
                    current_value=None,
                    threshold=constraint.threshold,
                    message=reason or "value unavailable",
                    related_ids=constraint.target_ids,
                    metadata={"reason": reason or "missing_value"},
                )
            else:
                status = _classify(
                    current,
                    constraint.threshold,
                    constraint.warning_threshold,
                    constraint.comparison,
                )
                evaluation = ConstraintEvaluation(
                    constraint_id=constraint.constraint_id,
                    owner_id=constraint.owner_id,
                    as_of_date=view.as_of_date,
                    status=status,
                    current_value=current,
                    threshold=constraint.threshold,
                    message=(
                        f"{constraint.constraint_type}: "
                        f"current={current:.6g} {constraint.comparison} "
                        f"threshold={constraint.threshold:.6g}"
                    ),
                    related_ids=constraint.target_ids,
                )

        self._record(evaluation, constraint)
        return evaluation

    def evaluate_owner(
        self,
        owner_id: str,
        *,
        as_of_date: str | None = None,
    ) -> tuple[ConstraintEvaluation, ...]:
        constraints = self.book.list_by_owner(owner_id)
        if not constraints:
            return ()
        view = self.projector.build_view(owner_id, as_of_date=as_of_date)
        return tuple(
            self.evaluate_constraint(constraint, view) for constraint in constraints
        )

    def evaluate_all(
        self,
        *,
        as_of_date: str | None = None,
    ) -> tuple[ConstraintEvaluation, ...]:
        owners = sorted({c.owner_id for c in self.book.all_constraints()})
        results: list[ConstraintEvaluation] = []
        for owner_id in owners:
            results.extend(self.evaluate_owner(owner_id, as_of_date=as_of_date))
        return tuple(results)

    def snapshot(
        self,
        *,
        as_of_date: str | None = None,
    ) -> dict[str, Any]:
        evaluations = self.evaluate_all(as_of_date=as_of_date)
        return {
            "count": len(evaluations),
            "evaluations": [evaluation.to_dict() for evaluation in evaluations],
        }

    def _record(
        self,
        evaluation: ConstraintEvaluation,
        constraint: ConstraintRecord,
    ) -> None:
        if self.ledger is None:
            return
        self.ledger.append(
            event_type="constraint_evaluated",
            simulation_date=evaluation.as_of_date,
            object_id=evaluation.constraint_id,
            agent_id=evaluation.owner_id,
            source=constraint.source,
            payload={
                "constraint_id": evaluation.constraint_id,
                "owner_id": evaluation.owner_id,
                "constraint_type": constraint.constraint_type,
                "status": evaluation.status,
                "current_value": evaluation.current_value,
                "threshold": evaluation.threshold,
                "comparison": constraint.comparison,
                "severity": constraint.severity,
            },
            space_id="constraints",
        )
