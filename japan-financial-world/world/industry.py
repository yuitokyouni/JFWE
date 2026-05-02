"""
v1.10.4 IndustryDemandConditionRecord + IndustryConditionBook.

Implements the optional context-signal primitive of the v1.10
engagement / strategic-response layer named in
``docs/v1_10_universal_engagement_and_response_design.md`` and §70
of ``docs/world_model.md``:

- ``IndustryDemandConditionRecord`` — a single immutable, append-only
  record naming a *generic, jurisdiction-neutral* demand condition
  (direction + bounded synthetic strength + bounded synthetic
  confidence) for a synthetic industry / sector / market in a given
  period. The record is **context evidence**, not a forecast and
  not a revenue model.
- ``IndustryConditionBook`` — append-only storage with read-only
  listings and a deterministic snapshot.

Scope discipline (v1.10.4)
==========================

An ``IndustryDemandConditionRecord`` is **context evidence** that
later milestones (firm pressure assessment, valuation refresh, bank
credit review, corporate strategic response candidates,
living-world reports) may *read* as one input among many. By
itself, an industry demand condition record:

- does **not** forecast demand, sales, revenue, or any other real
  quantity;
- does **not** update any firm's financial statements;
- does **not** move any price, change any contract, mutate any
  ownership, change any constraint, or trigger any corporate
  action;
- does **not** recommend any investment, divestment, or weight
  change;
- does **not** trade, change ownership, or move any price;
- does **not** make any lending decision;
- does **not** mutate any other source-of-truth book in the kernel
  (only the ``IndustryConditionBook`` itself and the kernel ledger
  are written to).

The record fields are jurisdiction-neutral by construction. The
book refuses to validate any controlled-vocabulary field
(``industry_id``, ``industry_label``, ``condition_type``,
``demand_direction``, ``time_horizon``, ``status``, ``visibility``)
against any specific country, regulator, sector classification, or
named institution — those calibrations live in v2 (Japan
public-data) and beyond, not here.

Cross-references (``related_variable_ids``, ``related_signal_ids``,
``related_exposure_ids``) are recorded as data and **not** validated
for resolution against any other book, per the v0/v1 cross-reference
rule already used by ``world/attention.py``, ``world/routines.py``,
``world/stewardship.py``, ``world/engagement.py``, and
``world/strategic_response.py``.

The two numeric fields, ``demand_strength`` and ``confidence``, are
**synthetic** quantities bounded in ``[0.0, 1.0]`` inclusive. They
are not calibrated probabilities, not forecasts, and not any
real-world measurement; they are illustrative ordering only,
following the v1 pattern set by ``world/exposures.py`` and
``world/signals.py``. Booleans are rejected for both fields (since
``bool`` is a subtype of ``int`` in Python) so ``True`` / ``False``
cannot smuggle past the bounded-numeric check.

v1.10.4 ships zero economic behavior: no demand forecast, no sales
forecast, no revenue update, no financial-statement update, no
price formation, no trading, no lending decisions, no corporate
actions, no investment recommendation, no Japan calibration, no
calibrated behavior probabilities, no jurisdiction-specific sector
classifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class IndustryConditionError(Exception):
    """Base class for industry-condition-layer errors."""


class DuplicateIndustryConditionError(IndustryConditionError):
    """Raised when a condition_id is added twice."""


class UnknownIndustryConditionError(IndustryConditionError, KeyError):
    """Raised when a condition_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("date must be a date or ISO string")


def _normalize_string_tuple(
    value: Iterable[str], *, field_name: str
) -> tuple[str, ...]:
    normalized = tuple(value)
    for entry in normalized:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty strings; "
                f"got {entry!r}"
            )
    return normalized


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndustryDemandConditionRecord:
    """
    Immutable record of one generic industry demand condition.

    A condition record names a synthetic, jurisdiction-neutral
    *demand state* of an industry / sector / market in a given
    period: a direction tag, a bounded synthetic strength, a
    bounded synthetic confidence, a horizon class, and a small
    illustrative condition-type tag. It is **context evidence**,
    not a forecast, not a revenue model, and not a real
    measurement.

    Field semantics
    ---------------
    - ``condition_id`` is the stable id; unique within an
      ``IndustryConditionBook``. Conditions are append-only — a
      condition is never mutated in place; instead, a new condition
      is added (with a different ``condition_id``) when the
      industry's stance changes (a previous record may carry
      ``status="superseded"`` for audit).
    - ``industry_id`` names the industry / sector / market this
      condition applies to. Free-form, jurisdiction-neutral string
      (e.g., ``"industry:reference_manufacturing_general"``).
    - ``industry_label`` is a short jurisdiction-neutral label.
    - ``as_of_date`` is the required ISO ``YYYY-MM-DD`` date naming
      the period the condition is recorded against.
    - ``condition_type`` is a free-form controlled-vocabulary tag
      describing the *kind* of condition the record names.
      Suggested generic, jurisdiction-neutral labels:
      ``"demand_assessment"``,
      ``"demand_outlook_synthetic"``,
      ``"structural_demand_state"``,
      ``"cyclical_demand_state"``. v1.10.4 stores the tag without
      enforcing membership in any specific list.
    - ``demand_direction`` is a small free-form tag naming the
      direction class. Recommended jurisdiction-neutral labels:
      ``"expanding"`` / ``"stable"`` / ``"contracting"`` /
      ``"mixed"`` / ``"unknown"``. v1.10.4 stores the tag without
      enforcing membership in any list.
    - ``demand_strength`` is a synthetic, bounded numeric value in
      ``[0.0, 1.0]`` inclusive — illustrative magnitude ordering
      only, **never** a calibrated probability and **never** a
      forecast. Booleans are rejected.
    - ``time_horizon`` is a free-form label naming the horizon
      class. Recommended labels: ``"short_term"`` /
      ``"medium_term"`` / ``"long_term"`` / ``"structural"``.
    - ``confidence`` is a synthetic, bounded numeric value in
      ``[0.0, 1.0]`` inclusive — illustrative confidence ordering
      only, **never** a calibrated probability and **never** a
      measurement. Booleans are rejected.
    - ``status`` is a small free-form tag tracking the lifecycle of
      the record. Recommended jurisdiction-neutral labels:
      ``"draft"`` / ``"active"`` / ``"under_review"`` /
      ``"superseded"`` / ``"retired"`` / ``"withdrawn"``.
    - ``related_variable_ids``, ``related_signal_ids``,
      ``related_exposure_ids`` are tuples of plain-id
      cross-references; stored as data and not validated against
      ``WorldVariableBook`` / ``SignalBook`` / ``ExposureBook``.
    - ``visibility`` is a free-form generic visibility tag
      (``"public"`` / ``"internal_only"`` / ``"restricted"``).
      Metadata only; not enforced as a runtime gate in v1.10.4.
    - ``metadata`` is free-form for provenance, parameters, and
      issuer notes. Must not carry market-size values, sales
      figures, revenue forecasts, real survey data, paid-data
      vendor identifiers, or expert-interview content; those
      remain restricted artifacts under
      ``docs/public_private_boundary.md`` and never appear in
      public FWE.

    Anti-fields
    -----------
    The record deliberately has **no** ``forecast_value``,
    ``revenue_forecast``, ``sales_forecast``, ``market_size``,
    ``demand_index_value``, ``vendor_consensus``, or equivalent
    fields. A public-FWE condition stores the synthetic
    direction / strength / confidence triple plus generic labels
    and IDs — never a calibrated number that could be confused
    with a real forecast.
    """

    condition_id: str
    industry_id: str
    industry_label: str
    as_of_date: str
    condition_type: str
    demand_direction: str
    demand_strength: float
    time_horizon: str
    confidence: float
    status: str
    visibility: str
    related_variable_ids: tuple[str, ...] = field(default_factory=tuple)
    related_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    related_exposure_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "condition_id",
        "industry_id",
        "industry_label",
        "as_of_date",
        "condition_type",
        "demand_direction",
        "time_horizon",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "related_variable_ids",
        "related_signal_ids",
        "related_exposure_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        # demand_strength — synthetic magnitude in [0, 1].
        if (
            isinstance(self.demand_strength, bool)
            or not isinstance(self.demand_strength, (int, float))
        ):
            raise ValueError("demand_strength must be a number")
        if not (0.0 <= float(self.demand_strength) <= 1.0):
            raise ValueError(
                "demand_strength must be between 0 and 1 inclusive "
                "(synthetic ordering only; not a calibrated forecast "
                "value)"
            )
        object.__setattr__(
            self, "demand_strength", float(self.demand_strength)
        )

        # confidence — synthetic [0, 1].
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
        ):
            raise ValueError("confidence must be a number")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                "confidence must be between 0 and 1 inclusive "
                "(synthetic ordering only; not a calibrated "
                "probability)"
            )
        object.__setattr__(self, "confidence", float(self.confidence))

        object.__setattr__(
            self, "as_of_date", _coerce_iso_date(self.as_of_date)
        )

        for tuple_field_name in self.TUPLE_FIELDS:
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "industry_id": self.industry_id,
            "industry_label": self.industry_label,
            "as_of_date": self.as_of_date,
            "condition_type": self.condition_type,
            "demand_direction": self.demand_direction,
            "demand_strength": self.demand_strength,
            "time_horizon": self.time_horizon,
            "confidence": self.confidence,
            "status": self.status,
            "visibility": self.visibility,
            "related_variable_ids": list(self.related_variable_ids),
            "related_signal_ids": list(self.related_signal_ids),
            "related_exposure_ids": list(self.related_exposure_ids),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class IndustryConditionBook:
    """
    Append-only storage for ``IndustryDemandConditionRecord``
    instances.

    The book emits exactly one ledger record per ``add_condition``
    call (``RecordType.INDUSTRY_DEMAND_CONDITION_ADDED``) and
    refuses to mutate any other source-of-truth book in the kernel.
    v1.10.4 ships storage and read-only listings only — no
    automatic condition inference, no demand forecasting, no
    revenue update, no financial-statement update, no economic
    behavior.

    Cross-references (``industry_id``, ``related_variable_ids``,
    ``related_signal_ids``, ``related_exposure_ids``) are recorded
    as data and not validated against any other book, per the
    v0/v1 cross-reference rule.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _conditions: dict[str, IndustryDemandConditionRecord] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_condition(
        self, condition: IndustryDemandConditionRecord
    ) -> IndustryDemandConditionRecord:
        if condition.condition_id in self._conditions:
            raise DuplicateIndustryConditionError(
                f"Duplicate condition_id: {condition.condition_id}"
            )
        self._conditions[condition.condition_id] = condition

        if self.ledger is not None:
            self.ledger.append(
                event_type="industry_demand_condition_added",
                simulation_date=self._now(),
                object_id=condition.condition_id,
                source=condition.industry_id,
                payload={
                    "condition_id": condition.condition_id,
                    "industry_id": condition.industry_id,
                    "industry_label": condition.industry_label,
                    "as_of_date": condition.as_of_date,
                    "condition_type": condition.condition_type,
                    "demand_direction": condition.demand_direction,
                    "demand_strength": condition.demand_strength,
                    "time_horizon": condition.time_horizon,
                    "confidence": condition.confidence,
                    "status": condition.status,
                    "visibility": condition.visibility,
                    "related_variable_ids": list(
                        condition.related_variable_ids
                    ),
                    "related_signal_ids": list(
                        condition.related_signal_ids
                    ),
                    "related_exposure_ids": list(
                        condition.related_exposure_ids
                    ),
                },
                space_id="industry",
                visibility=condition.visibility,
                confidence=condition.confidence,
            )
        return condition

    def get_condition(
        self, condition_id: str
    ) -> IndustryDemandConditionRecord:
        try:
            return self._conditions[condition_id]
        except KeyError as exc:
            raise UnknownIndustryConditionError(
                f"Industry demand condition not found: {condition_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_conditions(
        self,
    ) -> tuple[IndustryDemandConditionRecord, ...]:
        return tuple(self._conditions.values())

    def list_by_industry(
        self, industry_id: str
    ) -> tuple[IndustryDemandConditionRecord, ...]:
        return tuple(
            c
            for c in self._conditions.values()
            if c.industry_id == industry_id
        )

    def list_by_condition_type(
        self, condition_type: str
    ) -> tuple[IndustryDemandConditionRecord, ...]:
        return tuple(
            c
            for c in self._conditions.values()
            if c.condition_type == condition_type
        )

    def list_by_demand_direction(
        self, demand_direction: str
    ) -> tuple[IndustryDemandConditionRecord, ...]:
        return tuple(
            c
            for c in self._conditions.values()
            if c.demand_direction == demand_direction
        )

    def list_by_status(
        self, status: str
    ) -> tuple[IndustryDemandConditionRecord, ...]:
        return tuple(
            c for c in self._conditions.values() if c.status == status
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[IndustryDemandConditionRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            c
            for c in self._conditions.values()
            if c.as_of_date == target
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        conditions = sorted(
            (c.to_dict() for c in self._conditions.values()),
            key=lambda item: item["condition_id"],
        )
        return {
            "condition_count": len(conditions),
            "conditions": conditions,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
