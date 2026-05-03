"""
v1.15.4 IndicativeMarketPressureRecord +
IndicativeMarketPressureBook +
``build_indicative_market_pressure`` helper.

Append-only **label-based** synthetic record summarising a
security-level **indicative market pressure** state derived from
one or more :class:`AggregatedMarketInterestRecord` instances.

This is **indicative pressure**, **not** price formation,
**not** a quote, **not** an order book, **not** an order
imbalance, **not** a trade, **not** a recommendation. The record
carries small label states only; it never mutates the
``PriceBook`` (the ``_BOUND_BOOKS`` invariant assertion in tests
pins this) and never carries a price, bid, ask, quote, or order
field.

The record carries:

- five small closed-set summary labels:
    - ``demand_pressure_label``       — net demand posture
    - ``liquidity_pressure_label``    — liquidity posture
    - ``volatility_pressure_label``   — volatility posture
    - ``market_access_label``         — *shared vocabulary* with
      v1.14.3 :class:`CapitalStructureReviewCandidate`
      (``MARKET_ACCESS_LABELS``)
    - ``financing_relevance_label``   — relevance to v1.14
      financing candidates
- one closed-set lifecycle label: ``status``
- a synthetic ``confidence`` ordering in ``[0.0, 1.0]``
- four plain-id source tuples:
    - ``source_aggregated_interest_ids`` (the v1.15.3 records
      this pressure read)
    - ``source_market_environment_state_ids`` (v1.12.2)
    - ``source_security_ids``  (v1.15.1)
    - ``source_venue_ids``     (v1.15.1)
- ``visibility``, ``metadata``.

Cross-references are stored as data and not validated against
any other book per the v0/v1 cross-reference rule.

The record carries **no** ``price``, ``market_price``,
``indicative_price``, ``target_price``, ``expected_return``,
``bid``, ``ask``, ``quote``, ``order``, ``order_id``,
``order_imbalance``, ``trade``, ``trade_id``, ``execution``,
``clearing``, ``settlement``, ``recommendation``,
``investment_advice``, or ``real_data_value`` field. Tests pin
the absence on both the dataclass field set and the ledger
payload key set.

The book emits exactly one ledger record per ``add_record``
call (``RecordType.INDICATIVE_MARKET_PRESSURE_RECORDED``) with
``source = security_id`` (the security being summarised) so the
ledger graph reads as 'security S has indicative market
pressure P'. The book mutates no other source-of-truth book —
including the ``PriceBook``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping

from world.capital_structure import MARKET_ACCESS_LABELS
from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set label vocabularies
# ---------------------------------------------------------------------------


DEMAND_PRESSURE_LABELS: frozenset[str] = frozenset(
    {
        "supportive",
        "balanced",
        "cautious",
        "adverse",
        "mixed",
        "insufficient_observations",
        "unknown",
    }
)

LIQUIDITY_PRESSURE_LABELS: frozenset[str] = frozenset(
    {
        "ample",
        "normal",
        "thin",
        "tight",
        "stressed",
        "unknown",
    }
)

VOLATILITY_PRESSURE_LABELS: frozenset[str] = frozenset(
    {
        "calm",
        "elevated",
        "stressed",
        "unknown",
    }
)

# v1.14.3 alignment — the v1.15.4 record reuses the
# ``MARKET_ACCESS_LABELS`` frozenset from
# :mod:`world.capital_structure` so the two layers compose
# cleanly. Tests pin the equality.
MARKET_ACCESS_LABELS_V1154 = MARKET_ACCESS_LABELS

FINANCING_RELEVANCE_LABELS: frozenset[str] = frozenset(
    {
        "supportive_for_equity_access",
        "neutral_for_financing",
        "caution_for_dilution",
        "adverse_for_market_access",
        "insufficient_observations",
        "unknown",
    }
)

STATUS_LABELS: frozenset[str] = frozenset(
    {
        "draft",
        "active",
        "stale",
        "superseded",
        "archived",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class IndicativeMarketPressureError(Exception):
    """Base class for v1.15.4 indicative-market-pressure errors."""


class DuplicateIndicativeMarketPressureError(IndicativeMarketPressureError):
    """Raised when a market_pressure_id is added twice."""


class UnknownIndicativeMarketPressureError(
    IndicativeMarketPressureError, KeyError
):
    """Raised when a market_pressure_id is not found."""


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


def _validate_label(
    value: str, allowed: frozenset[str], *, field_name: str
) -> None:
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndicativeMarketPressureRecord:
    """Immutable record summarising one security's indicative
    market pressure at one date. Storage / audit object only —
    never a price, a quote, an order, an order book, or a
    recommendation.

    Field semantics
    ---------------
    - ``market_pressure_id`` is the stable id; unique within an
      ``IndicativeMarketPressureBook``.
    - ``security_id`` is a plain-id cross-reference.
    - ``as_of_date`` is the required ISO date.
    - the five label fields take values from the closed sets
      defined as module-level frozensets.
      ``market_access_label`` reuses the v1.14.3
      :data:`MARKET_ACCESS_LABELS` set from
      :mod:`world.capital_structure`.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` scalar
      (booleans rejected) — never a calibrated probability of
      any external action.
    - ``visibility`` is a free-form generic visibility tag.
    - ``source_*_ids`` are tuples of plain-id cross-references.
    - ``metadata`` is free-form.
    """

    market_pressure_id: str
    security_id: str
    as_of_date: str
    demand_pressure_label: str
    liquidity_pressure_label: str
    volatility_pressure_label: str
    market_access_label: str
    financing_relevance_label: str
    status: str
    visibility: str
    confidence: float
    source_aggregated_interest_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_security_ids: tuple[str, ...] = field(default_factory=tuple)
    source_venue_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "market_pressure_id",
        "security_id",
        "as_of_date",
        "demand_pressure_label",
        "liquidity_pressure_label",
        "volatility_pressure_label",
        "market_access_label",
        "financing_relevance_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_aggregated_interest_ids",
        "source_market_environment_state_ids",
        "source_security_ids",
        "source_venue_ids",
    )

    LABEL_FIELDS: ClassVar[tuple[tuple[str, frozenset[str]], ...]] = (
        ("demand_pressure_label", DEMAND_PRESSURE_LABELS),
        ("liquidity_pressure_label", LIQUIDITY_PRESSURE_LABELS),
        ("volatility_pressure_label", VOLATILITY_PRESSURE_LABELS),
        ("market_access_label", MARKET_ACCESS_LABELS_V1154),
        ("financing_relevance_label", FINANCING_RELEVANCE_LABELS),
        ("status", STATUS_LABELS),
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

        for label_field, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, label_field),
                allowed,
                field_name=label_field,
            )

        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
        ):
            raise ValueError("confidence must be a number")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                "confidence must be between 0 and 1 inclusive "
                "(synthetic ordering only; not a calibrated "
                "probability of any external action)"
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
            "market_pressure_id": self.market_pressure_id,
            "security_id": self.security_id,
            "as_of_date": self.as_of_date,
            "demand_pressure_label": self.demand_pressure_label,
            "liquidity_pressure_label": self.liquidity_pressure_label,
            "volatility_pressure_label": self.volatility_pressure_label,
            "market_access_label": self.market_access_label,
            "financing_relevance_label": self.financing_relevance_label,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "source_aggregated_interest_ids": list(
                self.source_aggregated_interest_ids
            ),
            "source_market_environment_state_ids": list(
                self.source_market_environment_state_ids
            ),
            "source_security_ids": list(self.source_security_ids),
            "source_venue_ids": list(self.source_venue_ids),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class IndicativeMarketPressureBook:
    """Append-only storage for v1.15.4
    ``IndicativeMarketPressureRecord`` instances. The book emits
    exactly one ledger record per ``add_record`` call
    (``RecordType.INDICATIVE_MARKET_PRESSURE_RECORDED``) with
    ``source = security_id``. The book mutates no other
    source-of-truth book, including the ``PriceBook``.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _records: dict[str, IndicativeMarketPressureRecord] = field(
        default_factory=dict
    )

    def add_record(
        self, record: IndicativeMarketPressureRecord
    ) -> IndicativeMarketPressureRecord:
        if record.market_pressure_id in self._records:
            raise DuplicateIndicativeMarketPressureError(
                f"Duplicate market_pressure_id: {record.market_pressure_id}"
            )
        self._records[record.market_pressure_id] = record

        if self.ledger is not None:
            self.ledger.append(
                event_type="indicative_market_pressure_recorded",
                simulation_date=self._now(),
                object_id=record.market_pressure_id,
                source=record.security_id,
                payload={
                    "market_pressure_id": record.market_pressure_id,
                    "security_id": record.security_id,
                    "as_of_date": record.as_of_date,
                    "demand_pressure_label": record.demand_pressure_label,
                    "liquidity_pressure_label": (
                        record.liquidity_pressure_label
                    ),
                    "volatility_pressure_label": (
                        record.volatility_pressure_label
                    ),
                    "market_access_label": record.market_access_label,
                    "financing_relevance_label": (
                        record.financing_relevance_label
                    ),
                    "status": record.status,
                    "visibility": record.visibility,
                    "confidence": record.confidence,
                    "source_aggregated_interest_ids": list(
                        record.source_aggregated_interest_ids
                    ),
                    "source_market_environment_state_ids": list(
                        record.source_market_environment_state_ids
                    ),
                    "source_security_ids": list(record.source_security_ids),
                    "source_venue_ids": list(record.source_venue_ids),
                },
                space_id="indicative_market_pressure",
                visibility=record.visibility,
                confidence=record.confidence,
            )
        return record

    def get_record(
        self, market_pressure_id: str
    ) -> IndicativeMarketPressureRecord:
        try:
            return self._records[market_pressure_id]
        except KeyError as exc:
            raise UnknownIndicativeMarketPressureError(
                f"Indicative market pressure record not found: "
                f"{market_pressure_id!r}"
            ) from exc

    def list_records(self) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(self._records.values())

    def list_by_security(
        self, security_id: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(
            r for r in self._records.values() if r.security_id == security_id
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            r for r in self._records.values() if r.as_of_date == target
        )

    def list_by_demand_pressure(
        self, demand_pressure_label: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if r.demand_pressure_label == demand_pressure_label
        )

    def list_by_liquidity_pressure(
        self, liquidity_pressure_label: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if r.liquidity_pressure_label == liquidity_pressure_label
        )

    def list_by_volatility_pressure(
        self, volatility_pressure_label: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if r.volatility_pressure_label == volatility_pressure_label
        )

    def list_by_market_access(
        self, market_access_label: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if r.market_access_label == market_access_label
        )

    def list_by_status(
        self, status: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(r for r in self._records.values() if r.status == status)

    def list_by_source_aggregated_interest(
        self, aggregated_interest_id: str
    ) -> tuple[IndicativeMarketPressureRecord, ...]:
        return tuple(
            r
            for r in self._records.values()
            if aggregated_interest_id in r.source_aggregated_interest_ids
        )

    def snapshot(self) -> dict[str, Any]:
        records = sorted(
            (r.to_dict() for r in self._records.values()),
            key=lambda item: item["market_pressure_id"],
        )
        return {
            "record_count": len(records),
            "records": records,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()


# ---------------------------------------------------------------------------
# Deterministic builder
#
# The helper resolves only the explicitly cited
# ``AggregatedMarketInterestRecord`` ids by calling
# ``kernel.aggregated_market_interest.get_record(id)``. It never
# scans the book globally (no ``list_*`` calls). Any cited id
# that fails to resolve is recorded in metadata under
# ``unresolved_aggregated_interest_count`` and skipped during
# label derivation. Any resolved record whose ``security_id``
# does not match the helper's ``security_id`` is ignored and
# recorded in metadata under ``mismatched_security_id_count``
# (mirroring the v1.15.3 helper's design choice).
# ---------------------------------------------------------------------------


def _derive_aggregated_net_interest_label(
    *,
    total: int,
    increased: int,
    reduced: int,
    neutral: int,
) -> str:
    """v1.15.3-style derivation reused on summed counts."""
    if total == 0:
        return "insufficient_observations"
    if increased > reduced and increased >= neutral:
        return "increased_interest"
    if reduced > increased and reduced >= neutral:
        return "reduced_interest"
    if increased > 0 and reduced > 0 and abs(increased - reduced) <= 1:
        return "mixed"
    return "balanced"


def _derive_aggregated_liquidity_interest_label(
    *,
    total: int,
    liquidity_watch_count: int,
) -> str:
    """v1.15.3-style derivation reused on summed counts."""
    if total == 0:
        return "unknown"
    if liquidity_watch_count == 0:
        return "liquidity_attention_low"
    if liquidity_watch_count * 2 < total:
        return "liquidity_attention_moderate"
    return "liquidity_attention_high"


def _derive_demand_pressure_label(
    *,
    aggregated_net_interest: str,
    liquidity_pressure: str,
) -> str:
    """v1.15.4 demand_pressure rule.

    - ``increased_interest`` → ``supportive``
    - ``reduced_interest`` → ``adverse`` if liquidity is
      ``tight`` or ``stressed``, else ``cautious``
    - ``mixed`` → ``mixed``
    - ``balanced`` → ``balanced``
    - ``insufficient_observations`` → ``insufficient_observations``
    """
    if aggregated_net_interest == "increased_interest":
        return "supportive"
    if aggregated_net_interest == "reduced_interest":
        if liquidity_pressure in ("tight", "stressed"):
            return "adverse"
        return "cautious"
    if aggregated_net_interest == "mixed":
        return "mixed"
    if aggregated_net_interest == "balanced":
        return "balanced"
    if aggregated_net_interest == "insufficient_observations":
        return "insufficient_observations"
    return "unknown"


def _derive_liquidity_pressure_label(
    *,
    aggregated_liquidity_interest: str,
    total: int,
) -> str:
    """v1.15.4 liquidity_pressure rule.

    - ``liquidity_attention_low`` → ``normal``
    - ``liquidity_attention_moderate`` → ``thin``
    - ``liquidity_attention_high`` → ``tight`` if
      ``total < 4`` (concentrated handful of investors),
      else ``stressed``
    - ``unknown`` → ``unknown``
    """
    if total == 0:
        return "unknown"
    if aggregated_liquidity_interest == "liquidity_attention_low":
        return "normal"
    if aggregated_liquidity_interest == "liquidity_attention_moderate":
        return "thin"
    if aggregated_liquidity_interest == "liquidity_attention_high":
        if total >= 4:
            return "stressed"
        return "tight"
    return "unknown"


def _derive_volatility_pressure_label(liquidity_pressure: str) -> str:
    """v1.15.4 volatility_pressure rule.

    Derived from the v1.15.4 ``liquidity_pressure_label`` (which
    is itself derived from the v1.15.3 ``liquidity_interest_label``
    on summed counts) — keeps the chain deterministic and
    one-step:

    - ``stressed`` → ``stressed``
    - ``tight`` or ``thin`` → ``elevated``
    - ``normal`` or ``ample`` → ``calm``
    - ``unknown`` → ``unknown``
    """
    if liquidity_pressure == "stressed":
        return "stressed"
    if liquidity_pressure in ("tight", "thin"):
        return "elevated"
    if liquidity_pressure in ("normal", "ample"):
        return "calm"
    return "unknown"


def _derive_market_access_label(
    *,
    demand_pressure: str,
    liquidity_pressure: str,
) -> str:
    """v1.15.4 market_access rule.

    Shares the v1.14.3 ``MARKET_ACCESS_LABELS`` vocabulary so
    capital-structure review records can compose with this
    record cleanly.

    - ``adverse`` demand OR ``stressed`` liquidity → ``constrained``
    - ``cautious`` demand AND ``tight`` liquidity → ``constrained``
    - ``supportive`` demand AND liquidity ∈ {ample, normal}
      → ``open``
    - ``mixed`` or ``cautious`` or ``balanced`` demand
      → ``selective``
    - ``insufficient_observations`` → ``unknown``
    """
    if demand_pressure == "insufficient_observations":
        return "unknown"
    if demand_pressure == "adverse" or liquidity_pressure == "stressed":
        return "constrained"
    if demand_pressure == "cautious" and liquidity_pressure == "tight":
        return "constrained"
    if (
        demand_pressure == "supportive"
        and liquidity_pressure in ("ample", "normal")
    ):
        return "open"
    if demand_pressure in ("mixed", "cautious", "balanced", "supportive"):
        return "selective"
    return "unknown"


def _derive_financing_relevance_label(
    *,
    market_access: str,
    demand_pressure: str,
) -> str:
    """v1.15.4 financing_relevance rule.

    - ``open`` market access → ``supportive_for_equity_access``
    - ``selective`` market access → ``caution_for_dilution`` if
      demand is ``cautious``, else ``neutral_for_financing``
    - ``constrained`` market access → ``adverse_for_market_access``
    - ``closed`` market access → ``adverse_for_market_access``
    - ``unknown`` → ``insufficient_observations``
    """
    if market_access == "open":
        return "supportive_for_equity_access"
    if market_access == "selective":
        if demand_pressure == "cautious":
            return "caution_for_dilution"
        return "neutral_for_financing"
    if market_access in ("constrained", "closed"):
        return "adverse_for_market_access"
    return "insufficient_observations"


def build_indicative_market_pressure(
    kernel: Any,
    *,
    security_id: str,
    as_of_date: date | str,
    source_aggregated_interest_ids: Iterable[str] = (),
    source_market_environment_state_ids: Iterable[str] = (),
    source_security_ids: Iterable[str] = (),
    source_venue_ids: Iterable[str] = (),
    market_pressure_id: str | None = None,
    confidence: float = 0.5,
    status: str = "active",
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> IndicativeMarketPressureRecord:
    """Synthesise one ``IndicativeMarketPressureRecord`` from a
    set of cited ``AggregatedMarketInterestRecord`` ids and add
    it to ``kernel.indicative_market_pressure``.

    The helper is a deterministic pure-label synthesiser:

    - Reads only the cited ids via
      ``kernel.aggregated_market_interest.get_record``. Never
      calls ``list_*`` or any other globally-scanning method.
    - Sums the v1.15.3 count fields across every matched
      record (matched = same ``security_id`` as the helper's
      ``security_id``). Mismatched records are ignored and the
      count is recorded in metadata under
      ``mismatched_security_id_count``.
    - Unresolved ids are ignored and the count is recorded in
      metadata under ``unresolved_aggregated_interest_count``.
    - Re-derives ``net_interest_label`` /
      ``liquidity_interest_label`` from the summed counts using
      the same v1.15.3 thresholds, then maps to v1.15.4 pressure
      labels via the small deterministic rules in
      :func:`_derive_demand_pressure_label`,
      :func:`_derive_liquidity_pressure_label`,
      :func:`_derive_volatility_pressure_label`,
      :func:`_derive_market_access_label`, and
      :func:`_derive_financing_relevance_label`.
    - Sets ``status = "active"`` by default at synthesis time.

    The helper does **not** infer prices, quotes, orders,
    bids / asks, or order-book imbalance. It does **not** mutate
    the ``PriceBook`` (or any other source-of-truth book).
    """

    interest_ids_t = tuple(source_aggregated_interest_ids)
    mes_ids_t = tuple(source_market_environment_state_ids)
    security_ids_t = tuple(source_security_ids)
    venue_ids_t = tuple(source_venue_ids)

    # Sum v1.15.3 count fields across every matched record.
    summed = {
        "increased_interest_count": 0,
        "reduced_interest_count": 0,
        "neutral_or_hold_review_count": 0,
        "liquidity_watch_count": 0,
        "risk_reduction_review_count": 0,
        "engagement_linked_review_count": 0,
        "total_intent_count": 0,
    }
    matched_record_count = 0
    mismatched_security_id_count = 0
    unresolved_aggregated_interest_count = 0

    book = getattr(kernel, "aggregated_market_interest", None)
    for aid in interest_ids_t:
        if book is None:
            unresolved_aggregated_interest_count += 1
            continue
        try:
            rec = book.get_record(aid)
        except Exception:
            unresolved_aggregated_interest_count += 1
            continue
        if rec.security_id != security_id:
            mismatched_security_id_count += 1
            continue
        matched_record_count += 1
        summed["increased_interest_count"] += rec.increased_interest_count
        summed["reduced_interest_count"] += rec.reduced_interest_count
        summed["neutral_or_hold_review_count"] += (
            rec.neutral_or_hold_review_count
        )
        summed["liquidity_watch_count"] += rec.liquidity_watch_count
        summed["risk_reduction_review_count"] += (
            rec.risk_reduction_review_count
        )
        summed["engagement_linked_review_count"] += (
            rec.engagement_linked_review_count
        )
        summed["total_intent_count"] += rec.total_intent_count

    total = summed["total_intent_count"]

    aggregated_net_interest = _derive_aggregated_net_interest_label(
        total=total,
        increased=summed["increased_interest_count"],
        reduced=summed["reduced_interest_count"],
        neutral=summed["neutral_or_hold_review_count"],
    )
    aggregated_liquidity_interest = _derive_aggregated_liquidity_interest_label(
        total=total,
        liquidity_watch_count=summed["liquidity_watch_count"],
    )

    liquidity_pressure = _derive_liquidity_pressure_label(
        aggregated_liquidity_interest=aggregated_liquidity_interest,
        total=total,
    )
    demand_pressure = _derive_demand_pressure_label(
        aggregated_net_interest=aggregated_net_interest,
        liquidity_pressure=liquidity_pressure,
    )
    volatility_pressure = _derive_volatility_pressure_label(
        liquidity_pressure
    )
    market_access = _derive_market_access_label(
        demand_pressure=demand_pressure,
        liquidity_pressure=liquidity_pressure,
    )
    financing_relevance = _derive_financing_relevance_label(
        market_access=market_access,
        demand_pressure=demand_pressure,
    )

    final_metadata: dict[str, Any] = dict(metadata) if metadata else {}
    final_metadata["mismatched_security_id_count"] = (
        mismatched_security_id_count
    )
    final_metadata["unresolved_aggregated_interest_count"] = (
        unresolved_aggregated_interest_count
    )
    final_metadata["matched_aggregated_record_count"] = matched_record_count

    if market_pressure_id is None:
        as_iso = _coerce_iso_date(as_of_date)
        market_pressure_id = (
            f"indicative_market_pressure:{security_id}:{as_iso}"
        )

    record = IndicativeMarketPressureRecord(
        market_pressure_id=market_pressure_id,
        security_id=security_id,
        as_of_date=as_of_date,
        demand_pressure_label=demand_pressure,
        liquidity_pressure_label=liquidity_pressure,
        volatility_pressure_label=volatility_pressure,
        market_access_label=market_access,
        financing_relevance_label=financing_relevance,
        status=status,
        visibility=visibility,
        confidence=confidence,
        source_aggregated_interest_ids=interest_ids_t,
        source_market_environment_state_ids=mes_ids_t,
        source_security_ids=security_ids_t,
        source_venue_ids=venue_ids_t,
        metadata=final_metadata,
    )
    return kernel.indicative_market_pressure.add_record(record)
