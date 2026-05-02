"""
v1.12.2 MarketEnvironmentStateRecord + MarketEnvironmentBook +
``build_market_environment_state``.

A jurisdiction-neutral, synthetic, **label-based** snapshot of one
period's market environment, normalized into nine compact regime
labels:

    - ``liquidity_regime``       (abundant / normal / tight / unknown)
    - ``volatility_regime``      (calm / elevated / stressed / unknown)
    - ``credit_regime``          (easing / neutral / tightening / stressed / unknown)
    - ``funding_regime``         (cheap / normal / expensive / constrained / unknown)
    - ``risk_appetite_regime``   (risk_on / neutral / risk_off / unknown)
    - ``rate_environment``       (low / rising / high / falling / unknown)
    - ``refinancing_window``     (open / selective / closed / unknown)
    - ``equity_valuation_regime`` (supportive / neutral / demanding / unknown)
    - ``overall_market_access_label`` (open_or_constructive / mixed /
                                       selective_or_constrained / unknown)

This is the *compact context object* future LLM agents and
attention-conditioned mechanisms can consume — one record per
period instead of five `MarketConditionRecord` instances + one
`CapitalMarketReadoutRecord`. It does **not** introduce price
formation, yield-curve calibration, spread calibration, forecasts,
investment recommendations, DCM / ECM execution, loan origination,
real-data ingestion, or Japan calibration. The record is labels +
provenance ids; nothing else.

Per ``docs/world_model.md`` §82 and the v1.12.2 task spec:

- ``MarketEnvironmentStateRecord`` — a single immutable,
  append-only record naming the period's nine regime labels plus
  the source ids (market_condition / market_readout /
  industry_condition) the builder read.
- ``MarketEnvironmentBook`` — append-only storage with
  read-only listings and a deterministic snapshot.
- ``build_market_environment_state(kernel, *, as_of_date,
  market_condition_ids, market_readout_ids,
  industry_condition_ids, ...)`` — deterministic builder reading
  ONLY the cited ids and applying the v1.12.2 rule set.
  Idempotent on ``environment_state_id``.

Anti-fields (binding)
---------------------

The record deliberately has **no** ``price``, ``market_price``,
``yield_value``, ``spread_bps``, ``index_level``,
``forecast_value``, ``expected_return``, ``target_price``,
``recommendation``, ``investment_advice``, ``real_data_value``,
``market_size``, ``order``, ``trade``, or ``allocation`` field.
Tests pin the absence on both the dataclass field set and the
ledger payload key set.

Scope discipline (v1.12.2)
==========================

The record / book / builder:

- write only to ``MarketEnvironmentBook`` and the kernel ledger;
  never to any other source-of-truth book;
- never produce a price, yield, spread, index level, forecast,
  expected return, recommendation, target price, target weight,
  order, trade, or allocation;
- never execute any DCM / ECM action, loan origination, security
  issuance, pricing, trading, price formation, yield-curve
  calibration, spread calibration, real-data ingestion, or
  Japan calibration;
- read only the source ids the caller passes (attention
  discipline — same as v1.12.1 investor intent);
- never enforce membership of any free-form tag against any
  controlled vocabulary; the recommended labels are illustrative.

The rule set is small, documented, and reproducible. No rule is
a recommendation; each branch returns a *label*, never a market
view, and never a binding action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from world.clock import Clock
from world.industry import IndustryConditionBook
from world.ledger import Ledger
from world.market_conditions import MarketConditionBook
from world.market_surface_readout import CapitalMarketReadoutBook


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MarketEnvironmentError(Exception):
    """Base class for market-environment-layer errors."""


class DuplicateMarketEnvironmentStateError(MarketEnvironmentError):
    """Raised when an environment_state_id is added twice."""


class UnknownMarketEnvironmentStateError(
    MarketEnvironmentError, KeyError
):
    """Raised when an environment_state_id is not found."""


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
class MarketEnvironmentStateRecord:
    """
    Immutable record of one period's market environment as nine
    compact regime labels plus the source ids the builder read.

    All required strings reject empty values; tuple fields
    normalize to ``tuple[str, ...]`` and reject empty entries; the
    ``confidence`` scalar is validated to ``[0.0, 1.0]`` inclusive
    with explicit bool rejection (matching the v1.11.0 / v1.11.1 /
    v1.12.0 / v1.12.1 idiom).

    Field semantics
    ---------------
    Nine regime label fields. Each is a small free-form
    controlled-vocabulary tag; v1.12.2 stores the tag without
    enforcing membership in any specific list. Recommended
    jurisdiction-neutral label sets are listed in the module
    docstring and are pinned by the v1.12.2 builder.

    - ``environment_state_id`` is the stable id; unique within a
      ``MarketEnvironmentBook``. Records are append-only.
    - ``as_of_date`` is the required ISO ``YYYY-MM-DD`` date.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` scalar — the
      builder's ordering on how strongly the cited evidence
      conditions the environment labels. Booleans rejected.
      **Never** a calibrated probability.
    - ``status`` is a small free-form lifecycle tag.
    - ``visibility`` is a free-form generic visibility tag.
    - ``source_market_condition_ids`` /
      ``source_market_readout_ids`` /
      ``source_industry_condition_ids`` are tuples of plain-id
      cross-references the builder read. Stored as data; not
      validated against any other book (the v0/v1
      cross-reference rule).
    - ``metadata`` is free-form for provenance.

    Anti-fields
    -----------
    The record deliberately has **no** ``price``, ``market_price``,
    ``yield_value``, ``spread_bps``, ``index_level``,
    ``forecast_value``, ``expected_return``, ``target_price``,
    ``recommendation``, ``investment_advice``, ``real_data_value``,
    ``market_size``, ``order``, ``trade``, or ``allocation``
    field. Tests pin the absence on both the dataclass field set
    and the ledger payload key set.
    """

    environment_state_id: str
    as_of_date: str
    liquidity_regime: str
    volatility_regime: str
    credit_regime: str
    funding_regime: str
    risk_appetite_regime: str
    rate_environment: str
    refinancing_window: str
    equity_valuation_regime: str
    overall_market_access_label: str
    status: str
    visibility: str
    confidence: float
    source_market_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    source_market_readout_ids: tuple[str, ...] = field(default_factory=tuple)
    source_industry_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "environment_state_id",
        "as_of_date",
        "liquidity_regime",
        "volatility_regime",
        "credit_regime",
        "funding_regime",
        "risk_appetite_regime",
        "rate_environment",
        "refinancing_window",
        "equity_valuation_regime",
        "overall_market_access_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_market_condition_ids",
        "source_market_readout_ids",
        "source_industry_condition_ids",
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
            "environment_state_id": self.environment_state_id,
            "as_of_date": self.as_of_date,
            "liquidity_regime": self.liquidity_regime,
            "volatility_regime": self.volatility_regime,
            "credit_regime": self.credit_regime,
            "funding_regime": self.funding_regime,
            "risk_appetite_regime": self.risk_appetite_regime,
            "rate_environment": self.rate_environment,
            "refinancing_window": self.refinancing_window,
            "equity_valuation_regime": self.equity_valuation_regime,
            "overall_market_access_label": self.overall_market_access_label,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "source_market_condition_ids": list(
                self.source_market_condition_ids
            ),
            "source_market_readout_ids": list(
                self.source_market_readout_ids
            ),
            "source_industry_condition_ids": list(
                self.source_industry_condition_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class MarketEnvironmentBook:
    """
    Append-only storage for ``MarketEnvironmentStateRecord``
    instances.

    The book emits exactly one ledger record per ``add_state``
    call (``RecordType.MARKET_ENVIRONMENT_STATE_ADDED``) and
    refuses to mutate any other source-of-truth book in the
    kernel. v1.12.2 ships storage and read-only listings only —
    no order submission, no trade, no rebalancing, no portfolio
    allocation, no price formation, no yield-curve calibration.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _states: dict[str, MarketEnvironmentStateRecord] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_state(
        self, state: MarketEnvironmentStateRecord
    ) -> MarketEnvironmentStateRecord:
        if state.environment_state_id in self._states:
            raise DuplicateMarketEnvironmentStateError(
                f"Duplicate environment_state_id: "
                f"{state.environment_state_id}"
            )
        self._states[state.environment_state_id] = state

        if self.ledger is not None:
            self.ledger.append(
                event_type="market_environment_state_added",
                simulation_date=self._now(),
                object_id=state.environment_state_id,
                payload={
                    "environment_state_id": state.environment_state_id,
                    "as_of_date": state.as_of_date,
                    "liquidity_regime": state.liquidity_regime,
                    "volatility_regime": state.volatility_regime,
                    "credit_regime": state.credit_regime,
                    "funding_regime": state.funding_regime,
                    "risk_appetite_regime": state.risk_appetite_regime,
                    "rate_environment": state.rate_environment,
                    "refinancing_window": state.refinancing_window,
                    "equity_valuation_regime": state.equity_valuation_regime,
                    "overall_market_access_label": (
                        state.overall_market_access_label
                    ),
                    "status": state.status,
                    "visibility": state.visibility,
                    "confidence": state.confidence,
                    "source_market_condition_ids": list(
                        state.source_market_condition_ids
                    ),
                    "source_market_readout_ids": list(
                        state.source_market_readout_ids
                    ),
                    "source_industry_condition_ids": list(
                        state.source_industry_condition_ids
                    ),
                },
                space_id="market_environment",
                visibility=state.visibility,
                confidence=state.confidence,
            )
        return state

    def get_state(
        self, environment_state_id: str
    ) -> MarketEnvironmentStateRecord:
        try:
            return self._states[environment_state_id]
        except KeyError as exc:
            raise UnknownMarketEnvironmentStateError(
                f"Market environment state not found: "
                f"{environment_state_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_states(self) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(self._states.values())

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            s for s in self._states.values() if s.as_of_date == target
        )

    def list_by_liquidity_regime(
        self, liquidity_regime: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.liquidity_regime == liquidity_regime
        )

    def list_by_volatility_regime(
        self, volatility_regime: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.volatility_regime == volatility_regime
        )

    def list_by_credit_regime(
        self, credit_regime: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.credit_regime == credit_regime
        )

    def list_by_funding_regime(
        self, funding_regime: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.funding_regime == funding_regime
        )

    def list_by_risk_appetite_regime(
        self, risk_appetite_regime: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.risk_appetite_regime == risk_appetite_regime
        )

    def list_by_rate_environment(
        self, rate_environment: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.rate_environment == rate_environment
        )

    def list_by_refinancing_window(
        self, refinancing_window: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.refinancing_window == refinancing_window
        )

    def list_by_overall_market_access_label(
        self, overall_market_access_label: str
    ) -> tuple[MarketEnvironmentStateRecord, ...]:
        return tuple(
            s
            for s in self._states.values()
            if s.overall_market_access_label == overall_market_access_label
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        states = sorted(
            (s.to_dict() for s in self._states.values()),
            key=lambda item: item["environment_state_id"],
        )
        return {
            "state_count": len(states),
            "states": states,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()


# ---------------------------------------------------------------------------
# Builder — deterministic synthetic rule set
# ---------------------------------------------------------------------------


# v1.12.2 deterministic mapping: market_condition.direction →
# regime label, per market_type. None of these is a calibrated
# yield, spread, or probability; each is a small documented
# label-to-label mapping. Unrecognized direction → "unknown".

_LIQUIDITY_DIRECTION_TO_REGIME: Mapping[str, str] = {
    "abundant": "abundant",
    "easing": "abundant",
    "supportive": "normal",
    "stable": "normal",
    "mixed": "normal",
    "tightening": "tight",
    "restrictive": "tight",
    "stressed": "tight",
}

_VOLATILITY_DIRECTION_TO_REGIME: Mapping[str, str] = {
    "calm": "calm",
    "stable": "calm",
    "supportive": "calm",
    "elevated": "elevated",
    "tightening": "elevated",
    "mixed": "elevated",
    "stressed": "stressed",
    "restrictive": "stressed",
}

_CREDIT_DIRECTION_TO_REGIME: Mapping[str, str] = {
    "easing": "easing",
    "narrowing": "easing",
    "supportive": "easing",
    "stable": "neutral",
    "mixed": "neutral",
    "tightening": "tightening",
    "widening": "tightening",
    "restrictive": "stressed",
    "stressed": "stressed",
}

_FUNDING_DIRECTION_TO_REGIME: Mapping[str, str] = {
    "supportive": "cheap",
    "easing": "cheap",
    "open": "cheap",
    "stable": "normal",
    "mixed": "normal",
    "tightening": "expensive",
    "restrictive": "constrained",
    "constrained": "constrained",
}

_RATE_DIRECTION_TO_ENVIRONMENT: Mapping[str, str] = {
    "easing": "falling",
    "falling": "falling",
    "supportive": "low",
    "stable": "low",
    "mixed": "low",
    "tightening": "rising",
    "rising": "rising",
    "restrictive": "high",
    "high": "high",
}

_EQUITY_DIRECTION_TO_REGIME: Mapping[str, str] = {
    "supportive": "supportive",
    "easing": "supportive",
    "stable": "neutral",
    "mixed": "neutral",
    "tightening": "demanding",
    "restrictive": "demanding",
    "stressed": "demanding",
}

# funding_regime → refinancing_window label. Funding is the
# most direct driver of refinancing access.
_FUNDING_REGIME_TO_REFINANCING_WINDOW: Mapping[str, str] = {
    "cheap": "open",
    "normal": "open",
    "expensive": "selective",
    "constrained": "closed",
}

_DEFAULT_ENVIRONMENT_CONFIDENCE: float = 0.5


@dataclass(frozen=True)
class MarketEnvironmentStateResult:
    """Return type for :func:`build_market_environment_state`.

    Carries the produced ``MarketEnvironmentStateRecord`` so the
    caller can branch on the labels without re-fetching."""

    environment_state_id: str
    record: MarketEnvironmentStateRecord


def _default_environment_state_id(as_of_date: str) -> str:
    return f"market_environment:{as_of_date}"


def _classify_risk_appetite_regime(
    *,
    overall_market_access_label: str,
    equity_valuation_regime: str,
    liquidity_regime: str,
    credit_regime: str,
) -> str:
    """v1.12.2 deterministic risk-appetite classifier (priority
    order):

    1. ``risk_on`` when the readout is constructive AND equity
       valuation is supportive AND liquidity is at least normal;
    2. ``risk_off`` when the readout is constrained AND
       (liquidity is tight OR credit is tightening / stressed);
    3. ``unknown`` when overall access is unknown;
    4. ``neutral`` otherwise.
    """
    if (
        overall_market_access_label == "open_or_constructive"
        and equity_valuation_regime == "supportive"
        and liquidity_regime in {"abundant", "normal"}
    ):
        return "risk_on"
    if overall_market_access_label == "selective_or_constrained" and (
        liquidity_regime == "tight"
        or credit_regime in {"tightening", "stressed"}
    ):
        return "risk_off"
    if overall_market_access_label == "unknown":
        return "unknown"
    return "neutral"


def build_market_environment_state(
    kernel: Any,
    *,
    as_of_date: date | str,
    market_condition_ids: Sequence[str] = (),
    market_readout_ids: Sequence[str] = (),
    industry_condition_ids: Sequence[str] = (),
    environment_state_id: str | None = None,
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> MarketEnvironmentStateResult:
    """
    Build and store one v1.12.2 market-environment-state record
    by reading the cited source records and applying the v1.12.2
    rule set. Returns a result wrapping the produced record.

    Idempotent: a state already added under the same
    ``environment_state_id`` is returned unchanged. Read-only
    over every other book; writes only to
    ``kernel.market_environments`` and the kernel ledger.

    Reads only the source ids the caller passes (attention
    discipline). Unresolved ids are tolerated (treated as
    "no signal for this slot") so the builder is forward-
    compatible with caller-defined market types.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    iso_date = _coerce_iso_date(as_of_date)
    sid = environment_state_id or _default_environment_state_id(iso_date)

    book: MarketEnvironmentBook = kernel.market_environments
    try:
        existing = book.get_state(sid)
        return MarketEnvironmentStateResult(
            environment_state_id=existing.environment_state_id,
            record=existing,
        )
    except UnknownMarketEnvironmentStateError:
        pass

    # ------------------------------------------------------------------
    # Read source evidence — only the caller-supplied ids.
    # ------------------------------------------------------------------
    direction_by_market_type: dict[str, str] = {}
    market_book: MarketConditionBook = kernel.market_conditions
    for cid in market_condition_ids:
        try:
            cond = market_book.get_condition(cid)
        except Exception:
            continue
        direction_by_market_type[cond.market_type] = cond.direction

    overall_market_access_label = "unknown"
    confidences: list[float] = []
    readout_book: CapitalMarketReadoutBook = kernel.capital_market_readouts
    for rid in market_readout_ids:
        try:
            readout = readout_book.get_readout(rid)
        except Exception:
            continue
        overall_market_access_label = readout.overall_market_access_label
        confidences.append(readout.confidence)

    # Industry conditions don't directly drive any of the nine
    # labels in v1.12.2; they're recorded as provenance only.
    # The builder still accesses them to verify they exist (and
    # collect confidences) — but does not (yet) derive labels
    # from them. Future v1.12.x may extend this.
    industry_book: IndustryConditionBook = kernel.industry_conditions
    for icid in industry_condition_ids:
        try:
            industry_cond = industry_book.get_condition(icid)
        except Exception:
            continue
        confidences.append(industry_cond.confidence)

    # Collect market-condition confidences too.
    for cid in market_condition_ids:
        try:
            cond = market_book.get_condition(cid)
        except Exception:
            continue
        confidences.append(cond.confidence)

    # ------------------------------------------------------------------
    # Apply rule set.
    # ------------------------------------------------------------------
    liquidity_regime = _LIQUIDITY_DIRECTION_TO_REGIME.get(
        direction_by_market_type.get("liquidity_market", "unknown"),
        "unknown",
    )
    volatility_regime = _VOLATILITY_DIRECTION_TO_REGIME.get(
        direction_by_market_type.get("volatility_regime", "unknown"),
        "unknown",
    )
    credit_regime = _CREDIT_DIRECTION_TO_REGIME.get(
        direction_by_market_type.get("credit_spreads", "unknown"),
        "unknown",
    )
    funding_regime = _FUNDING_DIRECTION_TO_REGIME.get(
        direction_by_market_type.get("funding_market", "unknown"),
        "unknown",
    )
    rate_environment = _RATE_DIRECTION_TO_ENVIRONMENT.get(
        direction_by_market_type.get("reference_rates", "unknown"),
        "unknown",
    )
    equity_valuation_regime = _EQUITY_DIRECTION_TO_REGIME.get(
        direction_by_market_type.get("equity_market", "unknown"),
        "unknown",
    )
    refinancing_window = _FUNDING_REGIME_TO_REFINANCING_WINDOW.get(
        funding_regime, "unknown"
    )
    risk_appetite_regime = _classify_risk_appetite_regime(
        overall_market_access_label=overall_market_access_label,
        equity_valuation_regime=equity_valuation_regime,
        liquidity_regime=liquidity_regime,
        credit_regime=credit_regime,
    )

    if confidences:
        confidence = max(0.0, min(1.0, sum(confidences) / len(confidences)))
    else:
        confidence = _DEFAULT_ENVIRONMENT_CONFIDENCE

    record = MarketEnvironmentStateRecord(
        environment_state_id=sid,
        as_of_date=iso_date,
        liquidity_regime=liquidity_regime,
        volatility_regime=volatility_regime,
        credit_regime=credit_regime,
        funding_regime=funding_regime,
        risk_appetite_regime=risk_appetite_regime,
        rate_environment=rate_environment,
        refinancing_window=refinancing_window,
        equity_valuation_regime=equity_valuation_regime,
        overall_market_access_label=overall_market_access_label,
        status="active",
        visibility=visibility,
        confidence=confidence,
        source_market_condition_ids=tuple(market_condition_ids),
        source_market_readout_ids=tuple(market_readout_ids),
        source_industry_condition_ids=tuple(industry_condition_ids),
        metadata=dict(metadata or {}),
    )
    book.add_state(record)
    return MarketEnvironmentStateResult(
        environment_state_id=record.environment_state_id,
        record=record,
    )
