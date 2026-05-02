"""
v1.11.1 CapitalMarketReadoutRecord + CapitalMarketReadoutBook +
``build_capital_market_readout``.

A *readout* layer on top of v1.11.0's ``MarketConditionRecord``.
Implements a deterministic, jurisdiction-neutral summary of one
period's worth of synthetic capital-market conditions: a tone tag
per market type (rates / credit / equity / funding window /
liquidity / volatility), an overall market-access label, and a
short banker-summary label.

This is **a readout / report artifact**, not a new economic
model and not a decision engine. Per ``docs/world_model.md`` §78
and ``docs/v1_11_capital_market_readout_design.md`` (when that
document lands), v1.11.1 produces *labels* derived from existing
v1.11.0 records via a small, documented rule set; it does **not**
calibrate yields, calibrate spreads, recommend any deal, price
any security, originate any loan, execute any trade, or forecast
any market level.

- ``CapitalMarketReadoutRecord`` — a single immutable, append-only
  record naming the period's per-market tone tags + overall
  market-access label + banker-summary label.
- ``CapitalMarketReadoutBook`` — append-only storage with
  read-only listings and a deterministic snapshot.
- ``build_capital_market_readout(kernel, *, as_of_date,
  market_condition_ids, ...)`` — deterministic builder that
  reads the cited market-condition records, applies the v1.11.1
  rule set, and emits exactly one readout record. Idempotent:
  re-calling with the same readout-id returns the existing
  record.

Scope discipline (v1.11.1)
==========================

The builder:

- reads only ``MarketConditionRecord`` instances;
- produces only labels (tone strings + a small enumerated
  market-access label + a banker-summary label);
- never produces a price, yield, spread, index level, forecast,
  expected return, recommendation, target price, deal advice,
  market size, or any real-data value;
- never mutates a market condition or any other source-of-truth
  book in the kernel (only the
  ``CapitalMarketReadoutBook`` itself and the kernel ledger
  are written to);
- never executes any DCM / ECM action, loan origination, security
  issuance, pricing, trading, price formation, yield-curve
  calibration, spread calibration, market forecast, investment
  recommendation, real data ingestion, or Japan calibration.

Anti-fields (binding)
---------------------

The record deliberately has **no** ``price``, ``target_price``,
``yield_value``, ``spread_bps``, ``forecast_value``,
``expected_return``, ``recommendation``, ``deal_advice``,
``market_size``, or ``real_data_value`` field. Tests pin the
absence on both the dataclass field set and the ledger payload
key set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from world.clock import Clock
from world.ledger import Ledger
from world.market_conditions import (
    MarketConditionBook,
    MarketConditionRecord,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CapitalMarketReadoutError(Exception):
    """Base class for capital-market-readout-layer errors."""


class DuplicateCapitalMarketReadoutError(CapitalMarketReadoutError):
    """Raised when a readout_id is added twice."""


class UnknownCapitalMarketReadoutError(
    CapitalMarketReadoutError, KeyError
):
    """Raised when a readout_id is not found."""


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
class CapitalMarketReadoutRecord:
    """
    Immutable record summarizing one period's capital-market
    surface as deterministic labels.

    All required strings reject empty values; tuple fields
    normalize to ``tuple[str, ...]`` and reject empty entries;
    ``confidence`` is a synthetic bounded value in ``[0.0, 1.0]``
    inclusive (booleans rejected). Cross-references
    (``market_condition_ids``) are stored as data and not
    validated against any other book.

    Field semantics
    ---------------
    - ``readout_id`` is the stable id; unique within a
      ``CapitalMarketReadoutBook``. Readouts are append-only — a
      readout is never mutated in place; a new readout is added
      (with a different ``readout_id``) when the period's view
      changes.
    - ``as_of_date`` is the required ISO ``YYYY-MM-DD`` date the
      readout summarizes.
    - ``market_condition_ids`` is the tuple of v1.11.0
      ``MarketConditionRecord`` ids the readout was built from.
      Stored as data, not validated against
      ``MarketConditionBook``.
    - ``rates_tone`` / ``credit_tone`` / ``equity_tone`` /
      ``funding_window_tone`` / ``liquidity_tone`` /
      ``volatility_tone`` are small free-form tone tags derived
      from the cited conditions' ``direction`` field. v1.11.1
      stores the labels without enforcing membership in any
      specific list. Recommended jurisdiction-neutral labels:
      ``"easing"`` / ``"tightening"`` / ``"widening"`` /
      ``"narrowing"`` / ``"supportive"`` / ``"restrictive"`` /
      ``"stable"`` / ``"mixed"`` / ``"unknown"``.
    - ``overall_market_access_label`` is a small enumerated tag
      describing the period's overall capital-market access
      stance. Recommended labels: ``"open_or_constructive"`` /
      ``"selective_or_constrained"`` / ``"mixed"``. Illustrative
      ordering only — never a recommendation, never a forecast.
    - ``banker_summary_label`` is a short jurisdiction-neutral
      banker-readable summary label. Suggested labels:
      ``"constructive_market_access_synthetic"`` /
      ``"selective_market_access_synthetic"`` /
      ``"mixed_market_access_synthetic"``. The ``_synthetic``
      suffix is intentional: the label names a class, never a
      market view.
    - ``status`` is a small free-form lifecycle tag
      (``"draft"`` / ``"active"`` / ``"superseded"`` /
      ``"retired"``).
    - ``confidence`` is a synthetic bounded numeric value in
      ``[0.0, 1.0]`` inclusive. By convention the builder sets
      it to the arithmetic mean of the cited conditions'
      ``confidence`` values. Booleans are rejected.
    - ``visibility`` is a free-form generic visibility tag
      (``"public"`` / ``"internal_only"`` / ``"restricted"``).
      Metadata only; not enforced as a runtime gate.
    - ``metadata`` is free-form for provenance and rule-version
      notes. Must not carry calibrated yields, calibrated
      spreads, real index levels, real market-size values,
      forecast values, expected returns, target prices, deal
      advice, or any real-data payload.

    Anti-fields
    -----------
    The record deliberately has **no** ``price``,
    ``target_price``, ``yield_value``, ``spread_bps``,
    ``forecast_value``, ``expected_return``, ``recommendation``,
    ``deal_advice``, ``market_size``, or ``real_data_value``
    field. Tests pin the absence by introspection of both the
    dataclass field set and the ledger payload key set.
    """

    readout_id: str
    as_of_date: str
    rates_tone: str
    credit_tone: str
    equity_tone: str
    funding_window_tone: str
    liquidity_tone: str
    volatility_tone: str
    overall_market_access_label: str
    banker_summary_label: str
    status: str
    confidence: float
    visibility: str
    market_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "readout_id",
        "as_of_date",
        "rates_tone",
        "credit_tone",
        "equity_tone",
        "funding_window_tone",
        "liquidity_tone",
        "volatility_tone",
        "overall_market_access_label",
        "banker_summary_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "market_condition_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

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
            "readout_id": self.readout_id,
            "as_of_date": self.as_of_date,
            "rates_tone": self.rates_tone,
            "credit_tone": self.credit_tone,
            "equity_tone": self.equity_tone,
            "funding_window_tone": self.funding_window_tone,
            "liquidity_tone": self.liquidity_tone,
            "volatility_tone": self.volatility_tone,
            "overall_market_access_label": self.overall_market_access_label,
            "banker_summary_label": self.banker_summary_label,
            "status": self.status,
            "confidence": self.confidence,
            "visibility": self.visibility,
            "market_condition_ids": list(self.market_condition_ids),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class CapitalMarketReadoutBook:
    """
    Append-only storage for ``CapitalMarketReadoutRecord``
    instances.

    The book emits exactly one ledger record per ``add_readout``
    call (``RecordType.CAPITAL_MARKET_READOUT_ADDED``) and refuses
    to mutate any other source-of-truth book in the kernel.
    v1.11.1 ships storage and read-only listings only — no
    automatic readout inference, no pricing, no DCM / ECM
    execution, no order matching, no clearing, no economic
    behavior.

    Cross-references (``market_condition_ids``) are recorded as
    data and not validated against any other book, per the v0/v1
    cross-reference rule.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _readouts: dict[str, CapitalMarketReadoutRecord] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_readout(
        self, readout: CapitalMarketReadoutRecord
    ) -> CapitalMarketReadoutRecord:
        if readout.readout_id in self._readouts:
            raise DuplicateCapitalMarketReadoutError(
                f"Duplicate readout_id: {readout.readout_id}"
            )
        self._readouts[readout.readout_id] = readout

        if self.ledger is not None:
            self.ledger.append(
                event_type="capital_market_readout_added",
                simulation_date=self._now(),
                object_id=readout.readout_id,
                payload={
                    "readout_id": readout.readout_id,
                    "as_of_date": readout.as_of_date,
                    "rates_tone": readout.rates_tone,
                    "credit_tone": readout.credit_tone,
                    "equity_tone": readout.equity_tone,
                    "funding_window_tone": readout.funding_window_tone,
                    "liquidity_tone": readout.liquidity_tone,
                    "volatility_tone": readout.volatility_tone,
                    "overall_market_access_label": (
                        readout.overall_market_access_label
                    ),
                    "banker_summary_label": readout.banker_summary_label,
                    "status": readout.status,
                    "confidence": readout.confidence,
                    "visibility": readout.visibility,
                    "market_condition_ids": list(
                        readout.market_condition_ids
                    ),
                },
                space_id="capital_markets",
                visibility=readout.visibility,
                confidence=readout.confidence,
            )
        return readout

    def get_readout(
        self, readout_id: str
    ) -> CapitalMarketReadoutRecord:
        try:
            return self._readouts[readout_id]
        except KeyError as exc:
            raise UnknownCapitalMarketReadoutError(
                f"Capital market readout not found: {readout_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_readouts(
        self,
    ) -> tuple[CapitalMarketReadoutRecord, ...]:
        return tuple(self._readouts.values())

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[CapitalMarketReadoutRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            r
            for r in self._readouts.values()
            if r.as_of_date == target
        )

    def list_by_status(
        self, status: str
    ) -> tuple[CapitalMarketReadoutRecord, ...]:
        return tuple(
            r for r in self._readouts.values() if r.status == status
        )

    def list_by_overall_market_access_label(
        self, overall_market_access_label: str
    ) -> tuple[CapitalMarketReadoutRecord, ...]:
        return tuple(
            r
            for r in self._readouts.values()
            if r.overall_market_access_label == overall_market_access_label
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        readouts = sorted(
            (r.to_dict() for r in self._readouts.values()),
            key=lambda item: item["readout_id"],
        )
        return {
            "readout_count": len(readouts),
            "readouts": readouts,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


# v1.11.1 rule set: each market_type → which tone slot it populates
# in the readout. Markets not in this map are ignored. Tone slots
# not populated by any condition default to ``"unknown"``.
_MARKET_TYPE_TO_TONE_SLOT: Mapping[str, str] = {
    "reference_rates": "rates_tone",
    "credit_spreads": "credit_tone",
    "equity_market": "equity_tone",
    "funding_market": "funding_window_tone",
    "liquidity_market": "liquidity_tone",
    "volatility_regime": "volatility_tone",
}

_TONE_SLOTS: tuple[str, ...] = (
    "rates_tone",
    "credit_tone",
    "equity_tone",
    "funding_window_tone",
    "liquidity_tone",
    "volatility_tone",
)

# v1.11.1 illustrative classifier rules. None of these is a
# recommendation; they are deterministic, documented, and
# reproducible.
_FUNDING_SUPPORTIVE_DIRECTIONS: frozenset[str] = frozenset(
    {"supportive", "easing", "narrowing", "open"}
)
_CREDIT_RESTRICTIVE_DIRECTIONS: frozenset[str] = frozenset(
    {"restrictive", "widening", "tightening"}
)
_LIQUIDITY_RESTRICTIVE_DIRECTIONS: frozenset[str] = frozenset(
    {"restrictive", "tightening", "widening"}
)


_OVERALL_TO_BANKER_SUMMARY: Mapping[str, str] = {
    "open_or_constructive": "constructive_market_access_synthetic",
    "selective_or_constrained": "selective_market_access_synthetic",
    "mixed": "mixed_market_access_synthetic",
}


def _classify_overall_market_access(
    *,
    funding_window_tone: str,
    credit_tone: str,
    liquidity_tone: str,
) -> str:
    """v1.11.1 deterministic overall-market-access classifier.

    Rules (illustrative, documented, never a recommendation):

    - if funding_window is supportive AND credit is not
      restrictive → ``"open_or_constructive"``;
    - else if credit is restrictive AND liquidity is restrictive
      → ``"selective_or_constrained"``;
    - else → ``"mixed"``.
    """
    funding_supportive = (
        funding_window_tone in _FUNDING_SUPPORTIVE_DIRECTIONS
    )
    credit_restrictive = credit_tone in _CREDIT_RESTRICTIVE_DIRECTIONS
    liquidity_restrictive = (
        liquidity_tone in _LIQUIDITY_RESTRICTIVE_DIRECTIONS
    )

    if funding_supportive and not credit_restrictive:
        return "open_or_constructive"
    if credit_restrictive and liquidity_restrictive:
        return "selective_or_constrained"
    return "mixed"


def _resolve_conditions(
    market_conditions_book: MarketConditionBook,
    market_condition_ids: Sequence[str],
) -> tuple[MarketConditionRecord, ...]:
    out: list[MarketConditionRecord] = []
    for cid in market_condition_ids:
        out.append(market_conditions_book.get_condition(cid))
    return tuple(out)


def _default_readout_id(as_of_date: str) -> str:
    return f"readout:capital_market:{as_of_date}"


def build_capital_market_readout(
    kernel: Any,
    *,
    as_of_date: date | str,
    market_condition_ids: Sequence[str],
    readout_id: str | None = None,
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> CapitalMarketReadoutRecord:
    """
    Build and store one v1.11.1 capital-market readout for the
    given period, deriving labels from the cited
    ``MarketConditionRecord`` instances by the v1.11.1 rule set.

    Idempotent: a readout already added under the same
    ``readout_id`` is returned unchanged.

    Read-only over every other book; writes only to
    ``kernel.capital_market_readouts`` and the kernel ledger.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    iso_date = _coerce_iso_date(as_of_date)
    rid = readout_id or _default_readout_id(iso_date)

    book: CapitalMarketReadoutBook = kernel.capital_market_readouts
    try:
        return book.get_readout(rid)
    except UnknownCapitalMarketReadoutError:
        pass

    market_book: MarketConditionBook = kernel.market_conditions
    conditions = _resolve_conditions(market_book, market_condition_ids)

    # Tone slots default to "unknown"; overlay each cited
    # condition's direction onto the slot named by its
    # market_type (if recognized). Conditions whose market_type
    # is not in the rule set are ignored without error so the
    # builder is forward-compatible with caller-defined market
    # types.
    tone_values: dict[str, str] = {slot: "unknown" for slot in _TONE_SLOTS}
    for cond in conditions:
        slot = _MARKET_TYPE_TO_TONE_SLOT.get(cond.market_type)
        if slot is not None:
            tone_values[slot] = cond.direction

    overall = _classify_overall_market_access(
        funding_window_tone=tone_values["funding_window_tone"],
        credit_tone=tone_values["credit_tone"],
        liquidity_tone=tone_values["liquidity_tone"],
    )
    banker_summary = _OVERALL_TO_BANKER_SUMMARY[overall]

    if conditions:
        avg_confidence = sum(c.confidence for c in conditions) / float(
            len(conditions)
        )
    else:
        avg_confidence = 0.5
    avg_confidence = max(0.0, min(1.0, avg_confidence))

    record = CapitalMarketReadoutRecord(
        readout_id=rid,
        as_of_date=iso_date,
        rates_tone=tone_values["rates_tone"],
        credit_tone=tone_values["credit_tone"],
        equity_tone=tone_values["equity_tone"],
        funding_window_tone=tone_values["funding_window_tone"],
        liquidity_tone=tone_values["liquidity_tone"],
        volatility_tone=tone_values["volatility_tone"],
        overall_market_access_label=overall,
        banker_summary_label=banker_summary,
        status="active",
        confidence=avg_confidence,
        visibility=visibility,
        market_condition_ids=tuple(market_condition_ids),
        metadata=dict(metadata or {}),
    )
    return book.add_readout(record)
