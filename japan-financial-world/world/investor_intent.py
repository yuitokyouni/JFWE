"""
v1.12.1 InvestorIntentRecord + InvestorIntentBook +
``run_reference_investor_intent_signal``.

A jurisdiction-neutral, synthetic, **non-binding** investor intent
layer. An *investor intent* is a pre-trade / pre-decision review
posture (e.g., "increase watch", "decrease confidence",
"engagement watch", "hold review", "risk flag watch", "deepen
due diligence", "coverage review") that an investor records about
a target portfolio company in a given period, citing the evidence
the posture was conditioned on.

This is **not** an order, **not** a trade, **not** a portfolio
allocation decision, **not** a security recommendation, **not**
an expected-return forecast. The record stores labels and plain-id
cross-references; it does not move ownership, does not change
prices, does not mutate any contract or constraint, and does not
emit any execution-class record.

Per ``docs/world_model.md`` §81 and the v1.12.1 task spec:

- ``InvestorIntentRecord`` — a single immutable, append-only
  record naming one investor's review posture about one target
  company on one date, plus the evidence ids the helper read.
- ``InvestorIntentBook`` — append-only storage with read-only
  listings and a deterministic snapshot.
- ``run_reference_investor_intent_signal`` — deterministic
  helper that reads only the evidence ids the caller passes,
  applies the v1.12.1 rule set, and emits exactly one record.
  Idempotent on ``intent_id``.

Anti-fields (binding)
---------------------

The record deliberately has **no** ``order``, ``order_id``,
``trade``, ``buy``, ``sell``, ``rebalance``, ``target_weight``,
``overweight``, ``underweight``, ``expected_return``,
``target_price``, ``recommendation``, ``investment_advice``,
``portfolio_allocation``, or ``execution`` field. Tests pin the
absence on both the dataclass field set and the ledger payload
key set.

Scope discipline (v1.12.1)
==========================

The record / book / helper:

- write only to ``InvestorIntentBook`` and the kernel ledger;
  never to any other source-of-truth book;
- never produce a price, yield, spread, index level, expected
  return, target price, recommendation, target weight, or
  trade / order / portfolio-allocation event;
- never execute any order submission, trade, rebalancing,
  buy / sell decision, security recommendation, investment
  advice, real-data ingestion, or Japan calibration;
- never enforce membership of any free-form tag against any
  controlled vocabulary;
- read only the evidence ids the caller supplies; do not scan
  the kernel's other books for context (the *attention
  discipline* the v1.12.1 task spec calls out — investor intent
  is local to its cited evidence).

The rule set is small, documented, and reproducible. No rule is
a recommendation; each branch returns a *label*, never a market
view, and never a binding action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from world.clock import Clock
from world.evidence import (
    ActorContextFrame,
    EvidenceResolutionError,
    StrictEvidenceResolutionError,
    resolve_actor_context,
)
from world.firm_state import FirmFinancialStateBook
from world.ledger import Ledger
from world.market_environment import MarketEnvironmentBook
from world.market_surface_readout import CapitalMarketReadoutBook


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class InvestorIntentError(Exception):
    """Base class for investor-intent-layer errors."""


class DuplicateInvestorIntentError(InvestorIntentError):
    """Raised when an intent_id is added twice."""


class UnknownInvestorIntentError(InvestorIntentError, KeyError):
    """Raised when an intent_id is not found."""


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
class InvestorIntentRecord:
    """
    Immutable record of one investor's pre-action review posture
    about one target company on one date, plus the evidence ids
    the helper read.

    All required strings reject empty values; tuple fields
    normalize to ``tuple[str, ...]`` and reject empty entries; the
    ``confidence`` scalar is validated to ``[0.0, 1.0]`` inclusive
    with explicit bool rejection.

    Field semantics
    ---------------
    - ``intent_id`` is the stable id; unique within an
      ``InvestorIntentBook``. Records are append-only — an intent
      is never mutated in place; instead, a new intent is added
      when posture changes.
    - ``investor_id`` names the investor / steward whose intent
      this is. Free-form; cross-references are recorded as data
      and not validated against the registry.
    - ``target_company_id`` names the portfolio company / firm
      the intent is about. Free-form; not validated.
    - ``as_of_date`` is the required ISO ``YYYY-MM-DD`` date.
    - ``intent_type`` is a small free-form controlled-vocabulary
      tag describing the *kind* of review action implied.
      Suggested generic, jurisdiction-neutral labels:
      ``"watch_adjustment"``, ``"confidence_adjustment"``,
      ``"engagement_review"``, ``"risk_review"``,
      ``"coverage_review"``. v1.12.1 stores the tag without
      enforcing membership in any specific list.
    - ``intent_direction`` is a small free-form tag naming the
      synthetic direction class. Recommended jurisdiction-neutral
      labels: ``"increase_watch"`` / ``"decrease_confidence"`` /
      ``"engagement_watch"`` / ``"hold_review"`` /
      ``"risk_flag_watch"`` / ``"deepen_due_diligence"`` /
      ``"coverage_review"``. **Never** an execution label like
      ``"buy"`` / ``"sell"`` / ``"overweight"`` / ``"underweight"``;
      v1.12.1 forbids those.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` scalar — the
      helper's ordering on how strongly the cited evidence
      conditions the posture. Booleans rejected. **Never** a
      calibrated probability.
    - ``priority`` is a small free-form tag (``"low"`` /
      ``"medium"`` / ``"high"`` / ``"unknown"``).
    - ``horizon`` is a free-form label
      (``"short_term"`` / ``"medium_term"`` / ``"long_term"``).
    - ``status`` is a small free-form lifecycle tag
      (``"draft"`` / ``"active"`` / ``"superseded"`` /
      ``"retired"``).
    - ``visibility`` is a free-form generic visibility tag
      (``"public"`` / ``"internal_only"`` / ``"restricted"``).
    - The eight ``evidence_*_ids`` tuples are plain-id
      cross-references the update read.
      ``evidence_selected_observation_set_ids`` ties the intent
      to the v1.8.x attention surface — the v1.12.1 *attention
      discipline* the task spec calls out, so a future
      attention-conditioned consumer can re-walk the same
      evidence the intent was conditioned on.
    - ``metadata`` is free-form for provenance and rule-version
      notes.

    Anti-fields
    -----------
    The record deliberately has **no** ``order``, ``order_id``,
    ``trade``, ``buy``, ``sell``, ``rebalance``,
    ``target_weight``, ``overweight``, ``underweight``,
    ``expected_return``, ``target_price``, ``recommendation``,
    ``investment_advice``, ``portfolio_allocation``, or
    ``execution`` field. Tests pin the absence on both the
    dataclass field set and the ledger payload key set.
    """

    intent_id: str
    investor_id: str
    target_company_id: str
    as_of_date: str
    intent_type: str
    intent_direction: str
    priority: str
    horizon: str
    status: str
    visibility: str
    confidence: float
    evidence_selected_observation_set_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    evidence_market_readout_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_market_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    evidence_firm_state_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_valuation_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_dialogue_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_escalation_candidate_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    evidence_stewardship_theme_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "intent_id",
        "investor_id",
        "target_company_id",
        "as_of_date",
        "intent_type",
        "intent_direction",
        "priority",
        "horizon",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "evidence_selected_observation_set_ids",
        "evidence_market_readout_ids",
        "evidence_market_condition_ids",
        "evidence_market_environment_state_ids",
        "evidence_firm_state_ids",
        "evidence_valuation_ids",
        "evidence_dialogue_ids",
        "evidence_escalation_candidate_ids",
        "evidence_stewardship_theme_ids",
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
            "intent_id": self.intent_id,
            "investor_id": self.investor_id,
            "target_company_id": self.target_company_id,
            "as_of_date": self.as_of_date,
            "intent_type": self.intent_type,
            "intent_direction": self.intent_direction,
            "priority": self.priority,
            "horizon": self.horizon,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "evidence_selected_observation_set_ids": list(
                self.evidence_selected_observation_set_ids
            ),
            "evidence_market_readout_ids": list(
                self.evidence_market_readout_ids
            ),
            "evidence_market_condition_ids": list(
                self.evidence_market_condition_ids
            ),
            "evidence_market_environment_state_ids": list(
                self.evidence_market_environment_state_ids
            ),
            "evidence_firm_state_ids": list(
                self.evidence_firm_state_ids
            ),
            "evidence_valuation_ids": list(
                self.evidence_valuation_ids
            ),
            "evidence_dialogue_ids": list(
                self.evidence_dialogue_ids
            ),
            "evidence_escalation_candidate_ids": list(
                self.evidence_escalation_candidate_ids
            ),
            "evidence_stewardship_theme_ids": list(
                self.evidence_stewardship_theme_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class InvestorIntentBook:
    """
    Append-only storage for ``InvestorIntentRecord`` instances.

    The book emits exactly one ledger record per ``add_intent``
    call (``RecordType.INVESTOR_INTENT_SIGNAL_ADDED``) and
    refuses to mutate any other source-of-truth book in the
    kernel. v1.12.1 ships storage and read-only listings only —
    no order submission, no trade, no rebalancing, no portfolio
    allocation, no security recommendation, no investment
    advice.

    Cross-references (every ``evidence_*_ids`` tuple) are recorded
    as data and not validated against any other book.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _intents: dict[str, InvestorIntentRecord] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_intent(
        self, intent: InvestorIntentRecord
    ) -> InvestorIntentRecord:
        if intent.intent_id in self._intents:
            raise DuplicateInvestorIntentError(
                f"Duplicate intent_id: {intent.intent_id}"
            )
        self._intents[intent.intent_id] = intent

        if self.ledger is not None:
            self.ledger.append(
                event_type="investor_intent_signal_added",
                simulation_date=self._now(),
                object_id=intent.intent_id,
                source=intent.investor_id,
                target=intent.target_company_id,
                payload={
                    "intent_id": intent.intent_id,
                    "investor_id": intent.investor_id,
                    "target_company_id": intent.target_company_id,
                    "as_of_date": intent.as_of_date,
                    "intent_type": intent.intent_type,
                    "intent_direction": intent.intent_direction,
                    "priority": intent.priority,
                    "horizon": intent.horizon,
                    "status": intent.status,
                    "visibility": intent.visibility,
                    "confidence": intent.confidence,
                    "evidence_selected_observation_set_ids": list(
                        intent.evidence_selected_observation_set_ids
                    ),
                    "evidence_market_readout_ids": list(
                        intent.evidence_market_readout_ids
                    ),
                    "evidence_market_condition_ids": list(
                        intent.evidence_market_condition_ids
                    ),
                    "evidence_market_environment_state_ids": list(
                        intent.evidence_market_environment_state_ids
                    ),
                    "evidence_firm_state_ids": list(
                        intent.evidence_firm_state_ids
                    ),
                    "evidence_valuation_ids": list(
                        intent.evidence_valuation_ids
                    ),
                    "evidence_dialogue_ids": list(
                        intent.evidence_dialogue_ids
                    ),
                    "evidence_escalation_candidate_ids": list(
                        intent.evidence_escalation_candidate_ids
                    ),
                    "evidence_stewardship_theme_ids": list(
                        intent.evidence_stewardship_theme_ids
                    ),
                },
                space_id="investor_intent",
                visibility=intent.visibility,
                confidence=intent.confidence,
            )
        return intent

    def get_intent(self, intent_id: str) -> InvestorIntentRecord:
        try:
            return self._intents[intent_id]
        except KeyError as exc:
            raise UnknownInvestorIntentError(
                f"Investor intent not found: {intent_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_intents(self) -> tuple[InvestorIntentRecord, ...]:
        return tuple(self._intents.values())

    def list_by_investor(
        self, investor_id: str
    ) -> tuple[InvestorIntentRecord, ...]:
        return tuple(
            i for i in self._intents.values() if i.investor_id == investor_id
        )

    def list_by_target_company(
        self, target_company_id: str
    ) -> tuple[InvestorIntentRecord, ...]:
        return tuple(
            i
            for i in self._intents.values()
            if i.target_company_id == target_company_id
        )

    def list_by_intent_type(
        self, intent_type: str
    ) -> tuple[InvestorIntentRecord, ...]:
        return tuple(
            i for i in self._intents.values() if i.intent_type == intent_type
        )

    def list_by_intent_direction(
        self, intent_direction: str
    ) -> tuple[InvestorIntentRecord, ...]:
        return tuple(
            i
            for i in self._intents.values()
            if i.intent_direction == intent_direction
        )

    def list_by_status(
        self, status: str
    ) -> tuple[InvestorIntentRecord, ...]:
        return tuple(
            i for i in self._intents.values() if i.status == status
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[InvestorIntentRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            i for i in self._intents.values() if i.as_of_date == target
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        intents = sorted(
            (i.to_dict() for i in self._intents.values()),
            key=lambda item: item["intent_id"],
        )
        return {
            "intent_count": len(intents),
            "intents": intents,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()


# ---------------------------------------------------------------------------
# Helper — deterministic synthetic rule set
# ---------------------------------------------------------------------------


# v1.12.1 rule thresholds and step sizes. Each is a small,
# documented anchor; a future tuning milestone may shift them.
# None of these is a recommendation. None is a calibrated number.
_FIRM_STATE_HIGH_FUNDING_NEED_THRESHOLD: float = 0.7
_FIRM_STATE_HIGH_PRESSURE_THRESHOLD: float = 0.65
_VALUATION_LOW_CONFIDENCE_THRESHOLD: float = 0.4
_DEFAULT_INTENT_CONFIDENCE: float = 0.5

_RESTRICTIVE_OVERALL_LABEL: str = "selective_or_constrained"


@dataclass(frozen=True)
class InvestorIntentSignalResult:
    """Return type for
    :func:`run_reference_investor_intent_signal`.

    Carries the produced ``InvestorIntentRecord`` plus the
    helper's resolved ``intent_direction`` so the caller can
    branch on the label without re-fetching the record.
    """

    intent_id: str
    record: InvestorIntentRecord
    intent_direction: str


def _default_intent_id(
    investor_id: str, target_company_id: str, as_of_date: str
) -> str:
    return f"intent:{investor_id}:{target_company_id}:{as_of_date}"


def _classify_intent_direction(
    *,
    high_funding_need: bool,
    high_pressure: bool,
    restrictive_market: bool,
    low_valuation_confidence: bool,
    engagement_present: bool,
) -> tuple[str, str]:
    """v1.12.1 deterministic classifier. Priority order:

    1. ``deepen_due_diligence`` (``risk_review``) when funding
       need is high.
    2. ``risk_flag_watch`` (``risk_review``) when firm pressure
       is high OR market overall is restrictive.
    3. ``decrease_confidence`` (``confidence_adjustment``) when
       valuation confidence is low.
    4. ``engagement_watch`` (``engagement_review``) when
       dialogue / escalation evidence is cited.
    5. ``hold_review`` (``watch_adjustment``) otherwise.
    """
    if high_funding_need:
        return "deepen_due_diligence", "risk_review"
    if high_pressure or restrictive_market:
        return "risk_flag_watch", "risk_review"
    if low_valuation_confidence:
        return "decrease_confidence", "confidence_adjustment"
    if engagement_present:
        return "engagement_watch", "engagement_review"
    return "hold_review", "watch_adjustment"


def run_reference_investor_intent_signal(
    kernel: Any,
    *,
    investor_id: str,
    target_company_id: str,
    as_of_date: date | str,
    selected_observation_set_ids: Sequence[str] = (),
    market_readout_ids: Sequence[str] = (),
    market_condition_ids: Sequence[str] = (),
    market_environment_state_ids: Sequence[str] = (),
    firm_state_ids: Sequence[str] = (),
    valuation_ids: Sequence[str] = (),
    dialogue_ids: Sequence[str] = (),
    escalation_candidate_ids: Sequence[str] = (),
    stewardship_theme_ids: Sequence[str] = (),
    intent_id: str | None = None,
    priority: str = "medium",
    horizon: str = "medium_term",
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> InvestorIntentSignalResult:
    """
    Build and store one v1.12.1 investor-intent record for the
    given (investor, target_company, period) by applying the
    v1.12.1 rule set on top of the cited evidence.

    Idempotent: an intent already added under the same
    ``intent_id`` is returned unchanged. Read-only over every
    other book; writes only to ``kernel.investor_intents`` and
    the kernel ledger.

    The helper reads only the evidence ids the caller passes —
    *attention discipline* (per the v1.12.1 task spec). It does
    not scan the kernel's other books for context. If the caller
    wants the helper to use a particular firm state or readout,
    the caller passes the relevant id; otherwise the helper
    treats that signal as absent.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(investor_id, str) or not investor_id:
        raise ValueError("investor_id is required and must be a non-empty string")
    if not isinstance(target_company_id, str) or not target_company_id:
        raise ValueError(
            "target_company_id is required and must be a non-empty string"
        )

    iso_date = _coerce_iso_date(as_of_date)
    iid = intent_id or _default_intent_id(
        investor_id, target_company_id, iso_date
    )

    book: InvestorIntentBook = kernel.investor_intents
    try:
        existing = book.get_intent(iid)
        return InvestorIntentSignalResult(
            intent_id=existing.intent_id,
            record=existing,
            intent_direction=existing.intent_direction,
        )
    except UnknownInvestorIntentError:
        pass

    # ------------------------------------------------------------------
    # Read evidence — only the caller-supplied ids. v1.12.1 does
    # not scan ``kernel.firm_financial_states`` or any other book
    # for additional context (attention discipline).
    # ------------------------------------------------------------------
    high_funding_need = False
    high_pressure = False
    if firm_state_ids:
        firm_state_book: FirmFinancialStateBook = kernel.firm_financial_states
        for fsid in firm_state_ids:
            try:
                state = firm_state_book.get_state(fsid)
            except Exception:
                # Unresolved firm-state id is recorded as data on
                # the intent but does not block intent emission —
                # consistent with the v1.12.1 attention discipline
                # (cite plain ids; do not couple intent emission
                # to other-book resolution).
                continue
            if (
                state.funding_need_intensity
                >= _FIRM_STATE_HIGH_FUNDING_NEED_THRESHOLD
            ):
                high_funding_need = True
            if (
                state.market_access_pressure
                >= _FIRM_STATE_HIGH_PRESSURE_THRESHOLD
                or state.funding_need_intensity
                >= _FIRM_STATE_HIGH_PRESSURE_THRESHOLD
            ):
                high_pressure = True

    restrictive_market = False
    if market_readout_ids:
        readout_book: CapitalMarketReadoutBook = kernel.capital_market_readouts
        for rid in market_readout_ids:
            try:
                readout = readout_book.get_readout(rid)
            except Exception:
                continue
            if readout.overall_market_access_label == _RESTRICTIVE_OVERALL_LABEL:
                restrictive_market = True

    low_valuation_confidence = False
    if valuation_ids:
        # ValuationBook.get_valuation returns the v1.7 ValuationRecord.
        # We read only confidence; never any value, never any number
        # treated as a forecast.
        for vid in valuation_ids:
            try:
                valuation = kernel.valuations.get_valuation(vid)
            except Exception:
                continue
            confidence = getattr(valuation, "confidence", None)
            if (
                isinstance(confidence, (int, float))
                and not isinstance(confidence, bool)
                and float(confidence) < _VALUATION_LOW_CONFIDENCE_THRESHOLD
            ):
                low_valuation_confidence = True
                break

    engagement_present = bool(dialogue_ids) or bool(escalation_candidate_ids)

    intent_direction, intent_type = _classify_intent_direction(
        high_funding_need=high_funding_need,
        high_pressure=high_pressure,
        restrictive_market=restrictive_market,
        low_valuation_confidence=low_valuation_confidence,
        engagement_present=engagement_present,
    )

    record = InvestorIntentRecord(
        intent_id=iid,
        investor_id=investor_id,
        target_company_id=target_company_id,
        as_of_date=iso_date,
        intent_type=intent_type,
        intent_direction=intent_direction,
        priority=priority,
        horizon=horizon,
        status="active",
        visibility=visibility,
        confidence=_DEFAULT_INTENT_CONFIDENCE,
        evidence_selected_observation_set_ids=tuple(
            selected_observation_set_ids
        ),
        evidence_market_readout_ids=tuple(market_readout_ids),
        evidence_market_condition_ids=tuple(market_condition_ids),
        evidence_market_environment_state_ids=tuple(
            market_environment_state_ids
        ),
        evidence_firm_state_ids=tuple(firm_state_ids),
        evidence_valuation_ids=tuple(valuation_ids),
        evidence_dialogue_ids=tuple(dialogue_ids),
        evidence_escalation_candidate_ids=tuple(escalation_candidate_ids),
        evidence_stewardship_theme_ids=tuple(stewardship_theme_ids),
        metadata=dict(metadata or {}),
    )
    book.add_intent(record)
    return InvestorIntentSignalResult(
        intent_id=record.intent_id,
        record=record,
        intent_direction=intent_direction,
    )


# ---------------------------------------------------------------------------
# v1.12.4 — attention-conditioned helper
# ---------------------------------------------------------------------------


# v1.12.4 — additional rule-set constants. The new helper consults
# the v1.12.2 market-environment record alongside the v1.11.1
# readout. Both surfaces map ``selective_or_constrained`` to
# "restrictive market", and the v1.12.2 ``risk_appetite_regime``
# label ``risk_off`` also triggers the restrictive branch. The
# default ``open_or_constructive`` / ``risk_on`` cases never fire
# rule 2 — so the v1.12.1 default-fixture behavior is preserved.
_RESTRICTIVE_RISK_APPETITE_LABEL: str = "risk_off"


def run_attention_conditioned_investor_intent_signal(
    kernel: Any,
    *,
    investor_id: str,
    target_company_id: str,
    as_of_date: date | str,
    selected_observation_set_ids: Sequence[str] = (),
    explicit_market_environment_state_ids: Sequence[str] = (),
    explicit_firm_state_ids: Sequence[str] = (),
    explicit_market_readout_ids: Sequence[str] = (),
    explicit_market_condition_ids: Sequence[str] = (),
    explicit_valuation_ids: Sequence[str] = (),
    explicit_dialogue_ids: Sequence[str] = (),
    explicit_escalation_candidate_ids: Sequence[str] = (),
    explicit_stewardship_theme_ids: Sequence[str] = (),
    intent_id: str | None = None,
    priority: str = "medium",
    horizon: str = "medium_term",
    visibility: str = "internal_only",
    strict: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> InvestorIntentSignalResult:
    """
    v1.12.4 — attention-conditioned investor-intent helper.

    Builds an :class:`ActorContextFrame` for ``(investor_id,
    target_company_id, as_of_date)`` via the v1.12.3
    :func:`world.evidence.resolve_actor_context` substrate, then
    classifies ``intent_direction`` using **only the resolved
    frame ids**. The v1.12.1 rule-set order is preserved, with one
    additive rule path: the v1.12.2 market-environment state's
    ``overall_market_access_label`` and ``risk_appetite_regime``
    can also trigger the restrictive-market branch (rule 2).

    Idempotent: an intent already added under the same
    ``intent_id`` is returned unchanged. Read-only over every
    other book; writes only to ``kernel.investor_intents`` and
    the kernel ledger.

    The helper reads only what the resolver surfaced for *this*
    investor on *this* date — never global. Resolved evidence ids
    land in the matching ``evidence_*_ids`` slot on the produced
    record; unresolved refs are recorded as a small data list in
    ``metadata["unresolved_refs"]``; the resolver's
    ``context_frame_id`` is recorded in
    ``metadata["context_frame_id"]``. Strict mode (``strict=True``)
    is forwarded to the resolver and raises
    :class:`StrictEvidenceResolutionError` on any unresolved id —
    the helper does not emit a record in that case.

    The helper does **not**:

    - submit any order, trade, rebalance, allocation, or
      execution;
    - produce a buy / sell / overweight / underweight / target
      weight / expected return / target price / recommendation /
      investment advice;
    - ingest real data or apply any Japan-specific calibration;
    - dispatch to an LLM agent or any external solver;
    - compute any behavior probability.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(investor_id, str) or not investor_id:
        raise ValueError("investor_id is required and must be a non-empty string")
    if not isinstance(target_company_id, str) or not target_company_id:
        raise ValueError(
            "target_company_id is required and must be a non-empty string"
        )

    iso_date = _coerce_iso_date(as_of_date)
    iid = intent_id or _default_intent_id(
        investor_id, target_company_id, iso_date
    )

    book: InvestorIntentBook = kernel.investor_intents
    try:
        existing = book.get_intent(iid)
        return InvestorIntentSignalResult(
            intent_id=existing.intent_id,
            record=existing,
            intent_direction=existing.intent_direction,
        )
    except UnknownInvestorIntentError:
        pass

    # ------------------------------------------------------------------
    # Pass 1 — ask the resolver to build a context frame for this
    # actor on this date. Strict mode raises before any record is
    # emitted.
    # ------------------------------------------------------------------
    frame: ActorContextFrame = resolve_actor_context(
        kernel,
        actor_id=investor_id,
        actor_type="investor",
        as_of_date=iso_date,
        selected_observation_set_ids=tuple(selected_observation_set_ids),
        explicit_market_environment_state_ids=tuple(
            explicit_market_environment_state_ids
        ),
        explicit_firm_state_ids=tuple(explicit_firm_state_ids),
        explicit_market_readout_ids=tuple(explicit_market_readout_ids),
        explicit_market_condition_ids=tuple(explicit_market_condition_ids),
        explicit_valuation_ids=tuple(explicit_valuation_ids),
        explicit_dialogue_ids=tuple(explicit_dialogue_ids),
        explicit_escalation_candidate_ids=tuple(
            explicit_escalation_candidate_ids
        ),
        explicit_stewardship_theme_ids=tuple(
            explicit_stewardship_theme_ids
        ),
        strict=strict,
    )

    # ------------------------------------------------------------------
    # Pass 2 — classify on the resolved frame. The helper reads
    # only ids the resolver surfaced; it does not scan books for
    # additional context.
    # ------------------------------------------------------------------
    high_funding_need = False
    high_pressure = False
    if frame.resolved_firm_state_ids:
        firm_state_book: FirmFinancialStateBook = (
            kernel.firm_financial_states
        )
        for fsid in frame.resolved_firm_state_ids:
            try:
                state = firm_state_book.get_state(fsid)
            except Exception:
                continue
            if (
                state.funding_need_intensity
                >= _FIRM_STATE_HIGH_FUNDING_NEED_THRESHOLD
            ):
                high_funding_need = True
            if (
                state.market_access_pressure
                >= _FIRM_STATE_HIGH_PRESSURE_THRESHOLD
                or state.funding_need_intensity
                >= _FIRM_STATE_HIGH_PRESSURE_THRESHOLD
            ):
                high_pressure = True

    restrictive_market = False
    if frame.resolved_market_readout_ids:
        readout_book: CapitalMarketReadoutBook = (
            kernel.capital_market_readouts
        )
        for rid in frame.resolved_market_readout_ids:
            try:
                readout = readout_book.get_readout(rid)
            except Exception:
                continue
            if (
                readout.overall_market_access_label
                == _RESTRICTIVE_OVERALL_LABEL
            ):
                restrictive_market = True
    # v1.12.4 additive: the v1.12.2 environment state can also
    # carry a restrictive overall label OR a risk_off appetite —
    # either is treated as restrictive for rule 2.
    if frame.resolved_market_environment_state_ids:
        env_book: MarketEnvironmentBook = kernel.market_environments
        for eid in frame.resolved_market_environment_state_ids:
            try:
                env = env_book.get_state(eid)
            except Exception:
                continue
            if (
                env.overall_market_access_label
                == _RESTRICTIVE_OVERALL_LABEL
            ):
                restrictive_market = True
            if (
                env.risk_appetite_regime
                == _RESTRICTIVE_RISK_APPETITE_LABEL
            ):
                restrictive_market = True

    low_valuation_confidence = False
    if frame.resolved_valuation_ids:
        for vid in frame.resolved_valuation_ids:
            try:
                valuation = kernel.valuations.get_valuation(vid)
            except Exception:
                continue
            confidence = getattr(valuation, "confidence", None)
            if (
                isinstance(confidence, (int, float))
                and not isinstance(confidence, bool)
                and float(confidence)
                < _VALUATION_LOW_CONFIDENCE_THRESHOLD
            ):
                low_valuation_confidence = True
                break

    engagement_present = (
        bool(frame.resolved_dialogue_ids)
        or bool(frame.resolved_escalation_candidate_ids)
    )

    intent_direction, intent_type = _classify_intent_direction(
        high_funding_need=high_funding_need,
        high_pressure=high_pressure,
        restrictive_market=restrictive_market,
        low_valuation_confidence=low_valuation_confidence,
        engagement_present=engagement_present,
    )

    # ------------------------------------------------------------------
    # Compose the record. Resolved evidence ids land in their
    # matching ``evidence_*_ids`` slots; the cited
    # selected_observation_set_ids land in
    # ``evidence_selected_observation_set_ids``; the resolver's
    # context-frame metadata + unresolved-ref summary land in
    # ``metadata`` (we deliberately do not introduce a dedicated
    # field on the record in v1.12.4 — staying additive).
    # ------------------------------------------------------------------
    extra_metadata: dict[str, Any] = dict(metadata or {})
    extra_metadata.setdefault("attention_conditioned", True)
    extra_metadata["context_frame_id"] = frame.context_frame_id
    extra_metadata["context_frame_status"] = frame.status
    extra_metadata["context_frame_confidence"] = frame.confidence
    if frame.unresolved_refs:
        extra_metadata["unresolved_refs"] = [
            r.to_dict() for r in frame.unresolved_refs
        ]

    record = InvestorIntentRecord(
        intent_id=iid,
        investor_id=investor_id,
        target_company_id=target_company_id,
        as_of_date=iso_date,
        intent_type=intent_type,
        intent_direction=intent_direction,
        priority=priority,
        horizon=horizon,
        status="active",
        visibility=visibility,
        confidence=_DEFAULT_INTENT_CONFIDENCE,
        evidence_selected_observation_set_ids=(
            frame.selected_observation_set_ids
        ),
        evidence_market_readout_ids=frame.resolved_market_readout_ids,
        evidence_market_condition_ids=frame.resolved_market_condition_ids,
        evidence_market_environment_state_ids=(
            frame.resolved_market_environment_state_ids
        ),
        evidence_firm_state_ids=frame.resolved_firm_state_ids,
        evidence_valuation_ids=frame.resolved_valuation_ids,
        evidence_dialogue_ids=frame.resolved_dialogue_ids,
        evidence_escalation_candidate_ids=(
            frame.resolved_escalation_candidate_ids
        ),
        evidence_stewardship_theme_ids=(
            frame.resolved_stewardship_theme_ids
        ),
        metadata=extra_metadata,
    )
    book.add_intent(record)
    return InvestorIntentSignalResult(
        intent_id=record.intent_id,
        record=record,
        intent_direction=intent_direction,
    )


# Re-export for convenience.
__all__ = [
    "DuplicateInvestorIntentError",
    "InvestorIntentBook",
    "InvestorIntentRecord",
    "InvestorIntentSignalResult",
    "UnknownInvestorIntentError",
    "run_reference_investor_intent_signal",
    "run_attention_conditioned_investor_intent_signal",
    "EvidenceResolutionError",
    "StrictEvidenceResolutionError",
]
