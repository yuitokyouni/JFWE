"""
v1.13.3 InterbankLiquidityStateRecord + InterbankLiquidityStateBook.

A jurisdiction-neutral, synthetic, **label-based** snapshot of
one institution's interbank-liquidity context at a point in time.
The record normalises that context into four compact regime
labels:

    - ``liquidity_regime``       (ample / normal / tight / stressed / unknown)
    - ``settlement_pressure``    (low / moderate / high / severe / unknown)
    - ``reserve_access_label``   (available / constrained / unknown)
    - ``funding_stress_label``   (low / moderate / elevated / stressed / unknown)

Plus a synthetic ``confidence`` ordering in ``[0.0, 1.0]`` and
plain-id cross-references to the records the synthesis read
(settlement accounts, payment instructions, settlement events,
market environment states). Cross-references are stored as data
and not validated against any other book per the v0/v1
cross-reference rule.

There are **no real balances**, **no calibrated liquidity model**,
**no bank default**, **no lending decision**, and **no Japan
calibration**. The record is labels + provenance ids only. Tests
pin the absence of every anti-field on the dataclass field set
and on the ledger payload key set.

The book emits exactly one ledger record per ``add_state`` call
(``RecordType.INTERBANK_LIQUIDITY_STATE_RECORDED``) and refuses to
mutate any other source-of-truth book in the kernel.
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


class InterbankLiquidityError(Exception):
    """Base class for v1.13.3 interbank-liquidity-layer errors."""


class DuplicateInterbankLiquidityStateError(InterbankLiquidityError):
    """Raised when a liquidity_state_id is added twice."""


class UnknownInterbankLiquidityStateError(
    InterbankLiquidityError, KeyError
):
    """Raised when a liquidity_state_id is not found."""


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
class InterbankLiquidityStateRecord:
    """Immutable record of one institution's synthetic
    interbank-liquidity state at a point in time.

    See module docstring for label vocabulary; v1.13.3 stores the
    label without enforcing membership in any specific list.
    Tests pin the recommended sets where useful.

    Field semantics
    ---------------
    - ``liquidity_state_id`` is the stable id; unique within a
      ``InterbankLiquidityStateBook``.
    - ``institution_id`` names the institution whose liquidity
      state this is. Free-form jurisdiction-neutral string.
    - ``as_of_date`` is the required ISO date.
    - the four regime label fields take the values listed in the
      module docstring.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` scalar — the
      synthesis's ordering on how strongly the cited evidence
      conditions the labels. Booleans rejected. **Never** a
      calibrated probability.
    - ``status`` is a small free-form lifecycle tag.
    - ``visibility`` is a free-form generic visibility tag.
    - ``source_*_ids`` are tuples of plain-id cross-references.
    - ``metadata`` is free-form.
    """

    liquidity_state_id: str
    institution_id: str
    as_of_date: str
    liquidity_regime: str
    settlement_pressure: str
    reserve_access_label: str
    funding_stress_label: str
    status: str
    visibility: str
    confidence: float
    source_settlement_account_ids: tuple[str, ...] = field(default_factory=tuple)
    source_payment_instruction_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_settlement_event_ids: tuple[str, ...] = field(default_factory=tuple)
    source_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "liquidity_state_id",
        "institution_id",
        "as_of_date",
        "liquidity_regime",
        "settlement_pressure",
        "reserve_access_label",
        "funding_stress_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_settlement_account_ids",
        "source_payment_instruction_ids",
        "source_settlement_event_ids",
        "source_market_environment_state_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
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
            "liquidity_state_id": self.liquidity_state_id,
            "institution_id": self.institution_id,
            "as_of_date": self.as_of_date,
            "liquidity_regime": self.liquidity_regime,
            "settlement_pressure": self.settlement_pressure,
            "reserve_access_label": self.reserve_access_label,
            "funding_stress_label": self.funding_stress_label,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "source_settlement_account_ids": list(
                self.source_settlement_account_ids
            ),
            "source_payment_instruction_ids": list(
                self.source_payment_instruction_ids
            ),
            "source_settlement_event_ids": list(
                self.source_settlement_event_ids
            ),
            "source_market_environment_state_ids": list(
                self.source_market_environment_state_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class InterbankLiquidityStateBook:
    """Append-only storage for v1.13.3
    ``InterbankLiquidityStateRecord`` instances. The book emits
    exactly one ledger record per ``add_state`` call
    (``RecordType.INTERBANK_LIQUIDITY_STATE_RECORDED``) and refuses
    to mutate any other source-of-truth book.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _states: dict[str, InterbankLiquidityStateRecord] = field(
        default_factory=dict
    )

    def add_state(
        self, state: InterbankLiquidityStateRecord
    ) -> InterbankLiquidityStateRecord:
        if state.liquidity_state_id in self._states:
            raise DuplicateInterbankLiquidityStateError(
                f"Duplicate liquidity_state_id: "
                f"{state.liquidity_state_id}"
            )
        self._states[state.liquidity_state_id] = state

        if self.ledger is not None:
            self.ledger.append(
                event_type="interbank_liquidity_state_recorded",
                simulation_date=self._now(),
                object_id=state.liquidity_state_id,
                source=state.institution_id,
                payload={
                    "liquidity_state_id": state.liquidity_state_id,
                    "institution_id": state.institution_id,
                    "as_of_date": state.as_of_date,
                    "liquidity_regime": state.liquidity_regime,
                    "settlement_pressure": state.settlement_pressure,
                    "reserve_access_label": state.reserve_access_label,
                    "funding_stress_label": state.funding_stress_label,
                    "status": state.status,
                    "visibility": state.visibility,
                    "confidence": state.confidence,
                    "source_settlement_account_ids": list(
                        state.source_settlement_account_ids
                    ),
                    "source_payment_instruction_ids": list(
                        state.source_payment_instruction_ids
                    ),
                    "source_settlement_event_ids": list(
                        state.source_settlement_event_ids
                    ),
                    "source_market_environment_state_ids": list(
                        state.source_market_environment_state_ids
                    ),
                },
                space_id="interbank_liquidity",
                visibility=state.visibility,
                confidence=state.confidence,
            )
        return state

    def get_state(
        self, liquidity_state_id: str
    ) -> InterbankLiquidityStateRecord:
        try:
            return self._states[liquidity_state_id]
        except KeyError as exc:
            raise UnknownInterbankLiquidityStateError(
                f"Interbank liquidity state not found: "
                f"{liquidity_state_id!r}"
            ) from exc

    def list_states(self) -> tuple[InterbankLiquidityStateRecord, ...]:
        return tuple(self._states.values())

    def list_by_institution(
        self, institution_id: str
    ) -> tuple[InterbankLiquidityStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.institution_id == institution_id
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[InterbankLiquidityStateRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            s for s in self._states.values() if s.as_of_date == target
        )

    def list_by_liquidity_regime(
        self, liquidity_regime: str
    ) -> tuple[InterbankLiquidityStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.liquidity_regime == liquidity_regime
        )

    def get_latest_for_institution(
        self, institution_id: str
    ) -> InterbankLiquidityStateRecord | None:
        latest: InterbankLiquidityStateRecord | None = None
        for s in self._states.values():
            if s.institution_id == institution_id:
                latest = s
        return latest

    def snapshot(self) -> dict[str, Any]:
        states = sorted(
            (s.to_dict() for s in self._states.values()),
            key=lambda item: item["liquidity_state_id"],
        )
        return {
            "state_count": len(states),
            "states": states,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
