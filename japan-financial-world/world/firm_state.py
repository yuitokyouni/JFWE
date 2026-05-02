"""
v1.12.0 FirmFinancialStateRecord + FirmFinancialStateBook +
``run_reference_firm_financial_state_update``.

The first time-crossing endogenous state-update layer in public
FWE. Synthetic, jurisdiction-neutral *latent* firm-financial state
records that update across periods so market regimes, market
readouts, industry-demand context, and pressure evidence
accumulate into the next period's state — closing the first
endogenous loop.

Per ``docs/world_model.md`` §80, this is **a synthetic latent
state update for endogenous dynamics**, **not** an accounting
statement update. The record stores six bounded synthetic
pressure / readiness scalars in ``[0.0, 1.0]`` plus an explicit
chain-link to the previous-period state for the same firm. It
does **not** store revenue, sales, EBITDA, net income, cash
balance, debt amount, accounting values, forecasts, real
financial statements, or investment recommendations.

- ``FirmFinancialStateRecord`` — a single immutable, append-only
  record naming one firm's latent financial state at a point in
  time, plus the evidence the update read and a
  ``previous_state_id`` link to the prior state in this firm's
  history.
- ``FirmFinancialStateBook`` — append-only storage with
  ``add_state`` / ``get_state`` / ``list_states`` /
  ``list_by_firm`` / ``list_by_date`` / ``get_latest_for_firm``
  / ``history_for_firm`` / ``snapshot``. Ordering for
  ``history_for_firm`` is insertion order (the orchestrator adds
  one record per firm per period in chronological order).
- ``run_reference_firm_financial_state_update`` — deterministic
  helper that resolves prior state (explicit
  ``previous_state_id`` overrides ``get_latest_for_firm``),
  reads the cited evidence, applies the v1.12.0 rule set, and
  emits exactly one record. Idempotent on ``state_id``.

Anti-fields (binding)
---------------------

The record deliberately has **no** ``revenue``, ``sales``,
``EBITDA``, ``net_income``, ``cash_balance``, ``debt_amount``,
``real_financial_statement``, ``forecast_value``,
``actual_value``, ``accounting_value``, or
``investment_recommendation`` field. Tests pin the absence on
both the dataclass field set and the ledger payload key set.

Scope discipline (v1.12.0)
==========================

The record / book / helper:

- write only to ``FirmFinancialStateBook`` and the kernel
  ledger; never to any other source-of-truth book;
- never produce a price, yield, spread, index level, forecast,
  expected return, recommendation, target price, deal advice, or
  real financial number;
- never execute any DCM / ECM action, loan origination, security
  issuance, pricing, trading, price formation, contract
  mutation, covenant enforcement, real-data ingestion, or Japan
  calibration;
- never enforce membership of any free-form tag against any
  controlled vocabulary — the recommended labels are
  illustrative.

The numeric rule set is small, documented, and reproducible. No
rule is a recommendation; each scalar is a synthetic ordering
in ``[0.0, 1.0]`` whose value is shaped by the cited evidence.
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


class FirmFinancialStateError(Exception):
    """Base class for firm-financial-state-layer errors."""


class DuplicateFirmFinancialStateError(FirmFinancialStateError):
    """Raised when a state_id is added twice."""


class UnknownFirmFinancialStateError(
    FirmFinancialStateError, KeyError
):
    """Raised when a state_id is not found."""


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


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _step(value: float, delta: float) -> float:
    return _clamp_unit(value + delta)


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FirmFinancialStateRecord:
    """
    Immutable record of one firm's latent financial state at a
    point in time, plus the evidence the update read and a chain
    link to the prior state.

    All required strings reject empty values; tuple fields
    normalize to ``tuple[str, ...]`` and reject empty entries; the
    seven bounded numeric fields (``margin_pressure``,
    ``liquidity_pressure``, ``debt_service_pressure``,
    ``market_access_pressure``, ``funding_need_intensity``,
    ``response_readiness``, ``confidence``) are validated to
    ``[0.0, 1.0]`` inclusive with explicit bool rejection.

    Field semantics
    ---------------
    - ``state_id`` is the stable id; unique within a
      ``FirmFinancialStateBook``. Records are append-only — a
      state is never mutated in place; instead, a new state is
      added with a new ``state_id`` and a ``previous_state_id``
      link to the prior period's state for this firm.
    - ``firm_id`` names the firm whose state this is. Free-form;
      cross-references are recorded as data and not validated
      against the registry.
    - ``as_of_date`` is the required ISO ``YYYY-MM-DD`` date this
      state is recorded against.
    - ``status`` is a small free-form lifecycle tag.
      Recommended jurisdiction-neutral labels:
      ``"draft"`` / ``"active"`` / ``"superseded"`` / ``"retired"``.
    - ``visibility`` is a free-form generic visibility tag
      (``"public"`` / ``"internal_only"`` / ``"restricted"``).
      Metadata only; not enforced as a runtime gate.
    - ``margin_pressure`` is a synthetic ``[0.0, 1.0]`` scalar
      representing the firm's margin-pressure ordering (higher =
      more compressed margins). **Never** a calibrated revenue,
      EBITDA, or accounting figure.
    - ``liquidity_pressure`` is a synthetic ``[0.0, 1.0]`` scalar
      representing liquidity stress ordering. **Never** a
      calibrated cash balance.
    - ``debt_service_pressure`` is a synthetic ``[0.0, 1.0]``
      scalar representing debt-service-burden ordering.
      **Never** a calibrated debt amount or coupon.
    - ``market_access_pressure`` is a synthetic ``[0.0, 1.0]``
      scalar representing capital-market-access pressure
      ordering. **Never** a calibrated yield or spread.
    - ``funding_need_intensity`` is a synthetic ``[0.0, 1.0]``
      derived scalar; the v1.12.0 rule set sets it to the mean
      of ``liquidity_pressure``, ``debt_service_pressure``, and
      ``market_access_pressure``. Future milestones may refine
      the rule.
    - ``response_readiness`` is a synthetic ``[0.0, 1.0]``
      derived scalar; the v1.12.0 rule set sets it to the mean
      of ``funding_need_intensity`` and ``margin_pressure``.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` confidence
      ordering on the state itself. Booleans rejected.
    - ``previous_state_id`` is the optional id of the prior state
      for this firm; ``None`` for the first state. Stored as
      data; not validated against the book for resolution (the
      v0/v1 cross-reference rule).
    - ``evidence_market_condition_ids``,
      ``evidence_market_readout_ids``,
      ``evidence_industry_condition_ids``,
      ``evidence_pressure_signal_ids``,
      ``evidence_valuation_ids`` are tuples of plain-id
      cross-references the update read.
    - ``metadata`` is free-form for provenance and rule-version
      notes. Must not carry calibrated numbers.

    Anti-fields
    -----------
    The record deliberately has **no** ``revenue``, ``sales``,
    ``EBITDA``, ``net_income``, ``cash_balance``,
    ``debt_amount``, ``real_financial_statement``,
    ``forecast_value``, ``actual_value``, ``accounting_value``,
    or ``investment_recommendation`` field.
    """

    state_id: str
    firm_id: str
    as_of_date: str
    status: str
    visibility: str
    margin_pressure: float
    liquidity_pressure: float
    debt_service_pressure: float
    market_access_pressure: float
    funding_need_intensity: float
    response_readiness: float
    confidence: float
    previous_state_id: str | None = None
    evidence_market_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_market_readout_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_industry_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_pressure_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_valuation_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "state_id",
        "firm_id",
        "as_of_date",
        "status",
        "visibility",
    )

    BOUNDED_NUMERIC_FIELDS: ClassVar[tuple[str, ...]] = (
        "margin_pressure",
        "liquidity_pressure",
        "debt_service_pressure",
        "market_access_pressure",
        "funding_need_intensity",
        "response_readiness",
        "confidence",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "evidence_market_condition_ids",
        "evidence_market_readout_ids",
        "evidence_industry_condition_ids",
        "evidence_pressure_signal_ids",
        "evidence_valuation_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        for name in self.BOUNDED_NUMERIC_FIELDS:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            if not (0.0 <= float(value) <= 1.0):
                raise ValueError(
                    f"{name} must be between 0 and 1 inclusive "
                    "(synthetic ordering only; not a calibrated "
                    "financial value)"
                )
            object.__setattr__(self, name, float(value))

        if self.previous_state_id is not None and (
            not isinstance(self.previous_state_id, str)
            or not self.previous_state_id
        ):
            raise ValueError(
                "previous_state_id must be a non-empty string or None"
            )

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
            "state_id": self.state_id,
            "firm_id": self.firm_id,
            "as_of_date": self.as_of_date,
            "status": self.status,
            "visibility": self.visibility,
            "margin_pressure": self.margin_pressure,
            "liquidity_pressure": self.liquidity_pressure,
            "debt_service_pressure": self.debt_service_pressure,
            "market_access_pressure": self.market_access_pressure,
            "funding_need_intensity": self.funding_need_intensity,
            "response_readiness": self.response_readiness,
            "confidence": self.confidence,
            "previous_state_id": self.previous_state_id,
            "evidence_market_condition_ids": list(
                self.evidence_market_condition_ids
            ),
            "evidence_market_readout_ids": list(
                self.evidence_market_readout_ids
            ),
            "evidence_industry_condition_ids": list(
                self.evidence_industry_condition_ids
            ),
            "evidence_pressure_signal_ids": list(
                self.evidence_pressure_signal_ids
            ),
            "evidence_valuation_ids": list(self.evidence_valuation_ids),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class FirmFinancialStateBook:
    """
    Append-only storage for ``FirmFinancialStateRecord`` instances.

    The book emits exactly one ledger record per ``add_state``
    call (``RecordType.FIRM_LATENT_STATE_UPDATED``) and refuses
    to mutate any other source-of-truth book in the kernel.
    v1.12.0 ships storage and read-only listings only — no
    automatic state inference, no pricing, no DCM / ECM
    execution, no contract mutation, no covenant enforcement.

    History semantics: ``history_for_firm(firm_id)`` returns the
    records in insertion order. The v1.12 living-world
    orchestrator inserts one record per (firm, period) in
    chronological order, so the insertion order matches the
    ``as_of_date`` order. Callers who add records out of date
    order may sort the result themselves; the book does not
    re-sort.

    Cross-references (``firm_id``, ``previous_state_id``, every
    ``evidence_*_ids`` tuple) are recorded as data and not
    validated against any other book, per the v0/v1
    cross-reference rule.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _states: dict[str, FirmFinancialStateRecord] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_state(
        self, state: FirmFinancialStateRecord
    ) -> FirmFinancialStateRecord:
        if state.state_id in self._states:
            raise DuplicateFirmFinancialStateError(
                f"Duplicate state_id: {state.state_id}"
            )
        self._states[state.state_id] = state

        if self.ledger is not None:
            self.ledger.append(
                event_type="firm_latent_state_updated",
                simulation_date=self._now(),
                object_id=state.state_id,
                source=state.firm_id,
                payload={
                    "state_id": state.state_id,
                    "firm_id": state.firm_id,
                    "as_of_date": state.as_of_date,
                    "status": state.status,
                    "visibility": state.visibility,
                    "margin_pressure": state.margin_pressure,
                    "liquidity_pressure": state.liquidity_pressure,
                    "debt_service_pressure": state.debt_service_pressure,
                    "market_access_pressure": state.market_access_pressure,
                    "funding_need_intensity": state.funding_need_intensity,
                    "response_readiness": state.response_readiness,
                    "confidence": state.confidence,
                    "previous_state_id": state.previous_state_id,
                    "evidence_market_condition_ids": list(
                        state.evidence_market_condition_ids
                    ),
                    "evidence_market_readout_ids": list(
                        state.evidence_market_readout_ids
                    ),
                    "evidence_industry_condition_ids": list(
                        state.evidence_industry_condition_ids
                    ),
                    "evidence_pressure_signal_ids": list(
                        state.evidence_pressure_signal_ids
                    ),
                    "evidence_valuation_ids": list(
                        state.evidence_valuation_ids
                    ),
                },
                space_id="firm_state",
                visibility=state.visibility,
                confidence=state.confidence,
            )
        return state

    def get_state(self, state_id: str) -> FirmFinancialStateRecord:
        try:
            return self._states[state_id]
        except KeyError as exc:
            raise UnknownFirmFinancialStateError(
                f"Firm financial state not found: {state_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_states(self) -> tuple[FirmFinancialStateRecord, ...]:
        return tuple(self._states.values())

    def list_by_firm(
        self, firm_id: str
    ) -> tuple[FirmFinancialStateRecord, ...]:
        return tuple(
            s for s in self._states.values() if s.firm_id == firm_id
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[FirmFinancialStateRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            s for s in self._states.values() if s.as_of_date == target
        )

    def get_latest_for_firm(
        self, firm_id: str
    ) -> FirmFinancialStateRecord | None:
        """Return the most recently added state for ``firm_id``,
        or ``None`` if there is no state for that firm yet.

        The "most recently added" rule is *insertion order*, not
        ``as_of_date`` order — callers who insert out of date
        order should not rely on this helper. The v1.12 living
        world inserts in chronological order.
        """
        latest: FirmFinancialStateRecord | None = None
        for s in self._states.values():
            if s.firm_id == firm_id:
                latest = s
        return latest

    def history_for_firm(
        self, firm_id: str
    ) -> tuple[FirmFinancialStateRecord, ...]:
        return self.list_by_firm(firm_id)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        states = sorted(
            (s.to_dict() for s in self._states.values()),
            key=lambda item: item["state_id"],
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
# Update helper — deterministic synthetic rule set
# ---------------------------------------------------------------------------


# v1.12.0 rule set (illustrative, documented, never a
# recommendation, never a forecast). Each delta is small so a
# multi-period sweep produces a visible but bounded trajectory.
# Tests pin the qualitative ordering: a constructive market
# regime allows the pressure scalars to decay below the prior
# state; a constrained / tightening regime amplifies them above
# the prior state.

_RESTRICTIVE_CREDIT_DIRECTIONS: frozenset[str] = frozenset(
    {"restrictive", "widening", "tightening"}
)
_CONTRACTING_INDUSTRY_DIRECTIONS: frozenset[str] = frozenset(
    {"contracting", "weakening", "tightening"}
)
_EXPANDING_INDUSTRY_DIRECTIONS: frozenset[str] = frozenset(
    {"expanding", "strengthening", "supportive"}
)

# Step sizes — small. Documented so future tuning has a
# reproducible anchor. None of these is a recommendation.
_STEP_OPEN_MARKET_ACCESS: float = -0.05
_STEP_OPEN_DEBT_SERVICE: float = -0.03
_STEP_CONSTRAINED_MARKET_ACCESS: float = +0.10
_STEP_CONSTRAINED_DEBT_SERVICE: float = +0.05
_STEP_MIXED_MARKET_ACCESS: float = +0.02
_STEP_RESTRICTIVE_CREDIT_TONE_DEBT_SERVICE: float = +0.05
_STEP_CONTRACTING_MARGIN: float = +0.05
_STEP_EXPANDING_MARGIN: float = -0.03
_STEP_PRESSURE_SIGNAL_LIQUIDITY: float = +0.02

_NEUTRAL_BASELINE: float = 0.5
_DEFAULT_CONFIDENCE: float = 0.5


@dataclass(frozen=True)
class FirmFinancialStateUpdateResult:
    """Return type for
    :func:`run_reference_firm_financial_state_update`.

    Carries the produced ``FirmFinancialStateRecord`` plus the
    resolved ``previous_state_id`` (whether explicit or looked up
    via ``get_latest_for_firm``) so the caller can reason about
    the chain link without re-resolving.
    """

    state_id: str
    record: FirmFinancialStateRecord
    previous_state_id: str | None


def _default_state_id(firm_id: str, as_of_date: str) -> str:
    return f"firm_state:{firm_id}:{as_of_date}"


def _resolve_previous_state(
    book: FirmFinancialStateBook,
    *,
    firm_id: str,
    previous_state_id: str | None,
) -> FirmFinancialStateRecord | None:
    if previous_state_id is not None:
        return book.get_state(previous_state_id)
    return book.get_latest_for_firm(firm_id)


def run_reference_firm_financial_state_update(
    kernel: Any,
    *,
    firm_id: str,
    as_of_date: date | str,
    previous_state_id: str | None = None,
    market_readout_ids: Sequence[str] = (),
    market_condition_ids: Sequence[str] = (),
    industry_condition_ids: Sequence[str] = (),
    pressure_signal_ids: Sequence[str] = (),
    valuation_ids: Sequence[str] = (),
    state_id: str | None = None,
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> FirmFinancialStateUpdateResult:
    """
    Build and store one v1.12.0 firm-financial-state record for
    the given (firm, period) by applying the v1.12.0 rule set on
    top of the resolved prior state (or a neutral 0.5 baseline if
    no prior state exists).

    Idempotent: a state already added under the same
    ``state_id`` is returned unchanged. Read-only over every
    other book; writes only to ``kernel.firm_financial_states``
    and the kernel ledger.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(firm_id, str) or not firm_id:
        raise ValueError("firm_id is required and must be a non-empty string")

    iso_date = _coerce_iso_date(as_of_date)
    sid = state_id or _default_state_id(firm_id, iso_date)

    book: FirmFinancialStateBook = kernel.firm_financial_states
    try:
        existing = book.get_state(sid)
        return FirmFinancialStateUpdateResult(
            state_id=existing.state_id,
            record=existing,
            previous_state_id=existing.previous_state_id,
        )
    except UnknownFirmFinancialStateError:
        pass

    prev = _resolve_previous_state(
        book, firm_id=firm_id, previous_state_id=previous_state_id
    )
    resolved_previous_state_id = prev.state_id if prev is not None else None

    if prev is None:
        margin = _NEUTRAL_BASELINE
        liquidity = _NEUTRAL_BASELINE
        debt_service = _NEUTRAL_BASELINE
        market_access = _NEUTRAL_BASELINE
    else:
        margin = prev.margin_pressure
        liquidity = prev.liquidity_pressure
        debt_service = prev.debt_service_pressure
        market_access = prev.market_access_pressure

    # ------------------------------------------------------------------
    # Apply readout-driven steps. ``open_or_constructive`` allows
    # decay; ``selective_or_constrained`` amplifies; ``mixed`` is
    # a small positive nudge on market_access only. Credit-tone
    # restrictive bumps debt_service.
    # ------------------------------------------------------------------
    readout_book: CapitalMarketReadoutBook = kernel.capital_market_readouts
    for rid in market_readout_ids:
        readout = readout_book.get_readout(rid)
        overall = readout.overall_market_access_label
        if overall == "open_or_constructive":
            market_access = _step(market_access, _STEP_OPEN_MARKET_ACCESS)
            debt_service = _step(debt_service, _STEP_OPEN_DEBT_SERVICE)
        elif overall == "selective_or_constrained":
            market_access = _step(
                market_access, _STEP_CONSTRAINED_MARKET_ACCESS
            )
            debt_service = _step(
                debt_service, _STEP_CONSTRAINED_DEBT_SERVICE
            )
        elif overall == "mixed":
            market_access = _step(market_access, _STEP_MIXED_MARKET_ACCESS)
        if readout.credit_tone in _RESTRICTIVE_CREDIT_DIRECTIONS:
            debt_service = _step(
                debt_service, _STEP_RESTRICTIVE_CREDIT_TONE_DEBT_SERVICE
            )

    # ------------------------------------------------------------------
    # Apply market-condition-driven steps for any market_type the
    # readout did not already capture. Today this overlaps with
    # the readout's credit_tone, so we only nudge debt_service if
    # no readouts were cited (avoid double-counting under the
    # default living-world wiring where both readout and
    # conditions are cited).
    # ------------------------------------------------------------------
    if not market_readout_ids:
        market_book: MarketConditionBook = kernel.market_conditions
        for cid in market_condition_ids:
            cond = market_book.get_condition(cid)
            if (
                cond.market_type == "credit_spreads"
                and cond.direction in _RESTRICTIVE_CREDIT_DIRECTIONS
            ):
                debt_service = _step(
                    debt_service,
                    _STEP_RESTRICTIVE_CREDIT_TONE_DEBT_SERVICE,
                )

    # ------------------------------------------------------------------
    # Apply industry-demand-driven steps to margin_pressure.
    # ------------------------------------------------------------------
    industry_book: IndustryConditionBook = kernel.industry_conditions
    for icid in industry_condition_ids:
        cond = industry_book.get_condition(icid)
        if cond.demand_direction in _CONTRACTING_INDUSTRY_DIRECTIONS:
            margin = _step(margin, _STEP_CONTRACTING_MARGIN)
        elif cond.demand_direction in _EXPANDING_INDUSTRY_DIRECTIONS:
            margin = _step(margin, _STEP_EXPANDING_MARGIN)

    # ------------------------------------------------------------------
    # Apply pressure-signal count to liquidity_pressure. Each
    # cited pressure signal nudges liquidity slightly upward; the
    # clamp prevents overshoot.
    # ------------------------------------------------------------------
    for _ in pressure_signal_ids:
        liquidity = _step(liquidity, _STEP_PRESSURE_SIGNAL_LIQUIDITY)

    # ------------------------------------------------------------------
    # Synthesize derived scalars. funding_need_intensity is the
    # mean of the three "external-facing" pressures;
    # response_readiness is the mean of funding_need_intensity
    # and margin_pressure.
    # ------------------------------------------------------------------
    funding_need_intensity = _clamp_unit(
        (liquidity + debt_service + market_access) / 3.0
    )
    response_readiness = _clamp_unit(
        (funding_need_intensity + margin) / 2.0
    )

    record = FirmFinancialStateRecord(
        state_id=sid,
        firm_id=firm_id,
        as_of_date=iso_date,
        status="active",
        visibility=visibility,
        margin_pressure=margin,
        liquidity_pressure=liquidity,
        debt_service_pressure=debt_service,
        market_access_pressure=market_access,
        funding_need_intensity=funding_need_intensity,
        response_readiness=response_readiness,
        confidence=_DEFAULT_CONFIDENCE,
        previous_state_id=resolved_previous_state_id,
        evidence_market_condition_ids=tuple(market_condition_ids),
        evidence_market_readout_ids=tuple(market_readout_ids),
        evidence_industry_condition_ids=tuple(industry_condition_ids),
        evidence_pressure_signal_ids=tuple(pressure_signal_ids),
        evidence_valuation_ids=tuple(valuation_ids),
        metadata=dict(metadata or {}),
    )
    book.add_state(record)
    return FirmFinancialStateUpdateResult(
        state_id=record.state_id,
        record=record,
        previous_state_id=resolved_previous_state_id,
    )
