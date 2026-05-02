"""
v1.14.1 CorporateFinancingNeedRecord +
CorporateFinancingNeedBook.

Append-only **label-based** synthetic record naming a firm's
financing-need posture at a point in time. Storage only — there
is **no application, no underwriting, no allocation, no rating,
no covenant, no contract or constraint mutation, no price /
yield / spread / coupon, no calibrated probability of any
external action, no real corporate-finance data, no Japan
calibration, no investment advice**.

The record carries four small need labels:

    - ``funding_horizon_label``  (immediate / near_term /
                                   medium_term / long_term / unknown)
    - ``funding_purpose_label``  (working_capital / refinancing /
                                   growth_capex / acquisition /
                                   restructuring / unknown)
    - ``urgency_label``          (low / moderate / elevated /
                                   critical / unknown)
    - ``synthetic_size_label``   (reference_size_small /
                                   reference_size_medium /
                                   reference_size_large /
                                   unknown) — never a real
                                   currency value

Plus a synthetic ``confidence`` ordering in ``[0.0, 1.0]`` and
plain-id cross-references to the records the synthesis read
(firm financial states, market environment states, corporate
signals). Cross-references are stored as data and not
validated against any other book per the v0/v1 cross-reference
rule.

The record carries **no** ``amount``, ``loan_amount``,
``interest_rate``, ``coupon``, ``tenor_years``,
``coverage_ratio``, ``decision_outcome``,
``default_probability``, ``recommendation``,
``investment_advice``, ``forecast_value``, ``actual_value``,
``real_data_value``, ``order``, or ``trade`` field. Tests pin
the absence on both the dataclass field set and the ledger
payload key set.

The book emits exactly one ledger record per ``add_need`` call
(``RecordType.CORPORATE_FINANCING_NEED_RECORDED``) and refuses
to mutate any other source-of-truth book in the kernel.
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


class CorporateFinancingError(Exception):
    """Base class for v1.14.x corporate-financing-layer errors."""


class DuplicateCorporateFinancingNeedError(CorporateFinancingError):
    """Raised when a need_id is added twice."""


class UnknownCorporateFinancingNeedError(
    CorporateFinancingError, KeyError
):
    """Raised when a need_id is not found."""


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
class CorporateFinancingNeedRecord:
    """Immutable record of one firm's synthetic financing-need
    posture at a point in time.

    See module docstring for label vocabulary; v1.14.1 stores
    the label without enforcing membership in any specific list.
    Tests pin the recommended sets where useful.

    Field semantics
    ---------------
    - ``need_id`` is the stable id; unique within a
      ``CorporateFinancingNeedBook``.
    - ``firm_id`` names the firm whose financing-need posture
      this is. Free-form jurisdiction-neutral string.
    - ``as_of_date`` is the required ISO date.
    - the four label fields take the values listed in the module
      docstring.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` scalar — the
      synthesis's ordering on how strongly the cited evidence
      conditions the labels. Booleans rejected. **Never** a
      calibrated probability of any external action.
    - ``status`` is a small free-form lifecycle tag.
    - ``visibility`` is a free-form generic visibility tag.
    - ``source_*_ids`` are tuples of plain-id cross-references.
    - ``metadata`` is free-form.
    """

    need_id: str
    firm_id: str
    as_of_date: str
    funding_horizon_label: str
    funding_purpose_label: str
    urgency_label: str
    synthetic_size_label: str
    status: str
    visibility: str
    confidence: float
    source_firm_financial_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_corporate_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "need_id",
        "firm_id",
        "as_of_date",
        "funding_horizon_label",
        "funding_purpose_label",
        "urgency_label",
        "synthetic_size_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_firm_financial_state_ids",
        "source_market_environment_state_ids",
        "source_corporate_signal_ids",
    )

    def __post_init__(self) -> None:
        if isinstance(self.as_of_date, date):
            object.__setattr__(
                self, "as_of_date", _coerce_iso_date(self.as_of_date)
            )

        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")

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
            "need_id": self.need_id,
            "firm_id": self.firm_id,
            "as_of_date": self.as_of_date,
            "funding_horizon_label": self.funding_horizon_label,
            "funding_purpose_label": self.funding_purpose_label,
            "urgency_label": self.urgency_label,
            "synthetic_size_label": self.synthetic_size_label,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "source_firm_financial_state_ids": list(
                self.source_firm_financial_state_ids
            ),
            "source_market_environment_state_ids": list(
                self.source_market_environment_state_ids
            ),
            "source_corporate_signal_ids": list(
                self.source_corporate_signal_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class CorporateFinancingNeedBook:
    """Append-only storage for v1.14.1
    ``CorporateFinancingNeedRecord`` instances. The book emits
    exactly one ledger record per ``add_need`` call
    (``RecordType.CORPORATE_FINANCING_NEED_RECORDED``) and
    refuses to mutate any other source-of-truth book.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _needs: dict[str, CorporateFinancingNeedRecord] = field(
        default_factory=dict
    )

    def add_need(
        self, need: CorporateFinancingNeedRecord
    ) -> CorporateFinancingNeedRecord:
        if need.need_id in self._needs:
            raise DuplicateCorporateFinancingNeedError(
                f"Duplicate need_id: {need.need_id}"
            )
        self._needs[need.need_id] = need

        if self.ledger is not None:
            self.ledger.append(
                event_type="corporate_financing_need_recorded",
                simulation_date=self._now(),
                object_id=need.need_id,
                source=need.firm_id,
                payload={
                    "need_id": need.need_id,
                    "firm_id": need.firm_id,
                    "as_of_date": need.as_of_date,
                    "funding_horizon_label": need.funding_horizon_label,
                    "funding_purpose_label": need.funding_purpose_label,
                    "urgency_label": need.urgency_label,
                    "synthetic_size_label": need.synthetic_size_label,
                    "status": need.status,
                    "visibility": need.visibility,
                    "confidence": need.confidence,
                    "source_firm_financial_state_ids": list(
                        need.source_firm_financial_state_ids
                    ),
                    "source_market_environment_state_ids": list(
                        need.source_market_environment_state_ids
                    ),
                    "source_corporate_signal_ids": list(
                        need.source_corporate_signal_ids
                    ),
                },
                space_id="corporate_financing",
                visibility=need.visibility,
                confidence=need.confidence,
            )
        return need

    def get_need(self, need_id: str) -> CorporateFinancingNeedRecord:
        try:
            return self._needs[need_id]
        except KeyError as exc:
            raise UnknownCorporateFinancingNeedError(
                f"Corporate financing need not found: {need_id!r}"
            ) from exc

    def list_needs(self) -> tuple[CorporateFinancingNeedRecord, ...]:
        return tuple(self._needs.values())

    def list_by_firm(
        self, firm_id: str
    ) -> tuple[CorporateFinancingNeedRecord, ...]:
        return tuple(
            n for n in self._needs.values() if n.firm_id == firm_id
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[CorporateFinancingNeedRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            n for n in self._needs.values() if n.as_of_date == target
        )

    def list_by_urgency(
        self, urgency_label: str
    ) -> tuple[CorporateFinancingNeedRecord, ...]:
        return tuple(
            n
            for n in self._needs.values()
            if n.urgency_label == urgency_label
        )

    def list_by_purpose(
        self, funding_purpose_label: str
    ) -> tuple[CorporateFinancingNeedRecord, ...]:
        return tuple(
            n
            for n in self._needs.values()
            if n.funding_purpose_label == funding_purpose_label
        )

    def get_latest_for_firm(
        self, firm_id: str
    ) -> CorporateFinancingNeedRecord | None:
        latest: CorporateFinancingNeedRecord | None = None
        for n in self._needs.values():
            if n.firm_id == firm_id:
                latest = n
        return latest

    def snapshot(self) -> dict[str, Any]:
        needs = sorted(
            (n.to_dict() for n in self._needs.values()),
            key=lambda item: item["need_id"],
        )
        return {
            "need_count": len(needs),
            "needs": needs,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
