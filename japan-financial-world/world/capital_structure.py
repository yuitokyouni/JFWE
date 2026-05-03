"""
v1.14.3 CapitalStructureReviewCandidate +
CapitalStructureReviewBook.

Append-only **label-based** synthetic record naming a structured
review of balance-sheet / capital-structure implications for a
firm at a point in time. Storage only — there is **no
optimal-capital-structure decision, no loan approval, no bond
issuance, no equity issuance, no underwriting, no syndication,
no pricing, no covenant enforcement, no rating model, no
PD / LGD / EAD, no real leverage ratio, no real D/E, no WACC
calculation, no investment advice, no real data ingestion, no
Japan calibration**.

A ``CapitalStructureReviewCandidate`` reviews financing
implications without deciding anything. It reads
``CorporateFinancingNeedRecord`` ids and
``FundingOptionCandidate`` ids as plain id cross-references
and posts a non-binding posture across eight small label axes:

    - ``review_type_label``           — what kind of review this is
    - ``leverage_pressure_label``     — leverage posture
    - ``liquidity_pressure_label``    — liquidity posture
    - ``maturity_wall_label``         — maturity-profile concern
    - ``dilution_concern_label``      — dilution concern
    - ``covenant_headroom_label``     — covenant slack
    - ``market_access_label``         — market access posture
    - ``rating_perception_label``     — rating perception

Plus a synthetic ``confidence`` ordering in ``[0.0, 1.0]`` and
plain-id cross-references to the records the synthesis read
(needs, funding option candidates, firm states, market
environment states, interbank liquidity states, bank credit
review signals, investor intent signals). Cross-references are
stored as data and not validated against any other book per the
v0/v1 cross-reference rule.

The record carries **no** ``debt_amount``, ``equity_amount``,
``leverage_ratio``, ``debt_to_equity``, ``WACC``, ``rating``,
``PD``, ``LGD``, ``EAD``, ``spread``, ``coupon``, ``fee``,
``price``, ``approval``, ``execution``, ``recommendation``,
``investment_advice``, or ``real_data_value`` field. Tests pin
the absence on both the dataclass field set and the ledger
payload key set.

The book emits exactly one ledger record per ``add_candidate``
call (``RecordType.CAPITAL_STRUCTURE_REVIEW_CANDIDATE_RECORDED``)
and refuses to mutate any other source-of-truth book in the
kernel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set label vocabularies
# ---------------------------------------------------------------------------


REVIEW_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "leverage_review",
        "liquidity_review",
        "refinancing_review",
        "dilution_review",
        "covenant_review",
        "market_access_review",
        "rating_perception_review",
        "unknown",
    }
)

LEVERAGE_PRESSURE_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "moderate",
        "elevated",
        "high",
        "unknown",
    }
)

LIQUIDITY_PRESSURE_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "moderate",
        "elevated",
        "stressed",
        "unknown",
    }
)

MATURITY_WALL_LABELS: frozenset[str] = frozenset(
    {
        "none_visible",
        "manageable",
        "approaching",
        "concentrated",
        "unknown",
    }
)

DILUTION_CONCERN_LABELS: frozenset[str] = frozenset(
    {
        "not_applicable",
        "low",
        "moderate",
        "high",
        "unknown",
    }
)

COVENANT_HEADROOM_LABELS: frozenset[str] = frozenset(
    {
        "not_applicable",
        "comfortable",
        "limited",
        "tight",
        "unknown",
    }
)

MARKET_ACCESS_LABELS: frozenset[str] = frozenset(
    {
        "open",
        "selective",
        "constrained",
        "closed",
        "unknown",
    }
)

RATING_PERCEPTION_LABELS: frozenset[str] = frozenset(
    {
        "stable",
        "watch",
        "negative_watch",
        "stressed",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CapitalStructureError(Exception):
    """Base class for v1.14.3 capital-structure-review-layer errors."""


class DuplicateCapitalStructureReviewError(CapitalStructureError):
    """Raised when a review_candidate_id is added twice."""


class UnknownCapitalStructureReviewError(CapitalStructureError, KeyError):
    """Raised when a review_candidate_id is not found."""


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
class CapitalStructureReviewCandidate:
    """Immutable record of one structured capital-structure review
    posture for a firm at a point in time.

    See module docstring for label vocabularies; v1.14.3 enforces
    closed-set membership at construction so downstream readers
    can rely on the small label sets.

    Field semantics
    ---------------
    - ``review_candidate_id`` is the stable id; unique within a
      ``CapitalStructureReviewBook``.
    - ``firm_id`` names the firm whose capital-structure review
      this is. Free-form jurisdiction-neutral string.
    - ``as_of_date`` is the required ISO date.
    - the eight label fields take values from the closed sets
      defined as module-level frozensets.
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` scalar — the
      synthesis's ordering on how strongly the cited evidence
      supports this review posture. Booleans rejected. **Never**
      a calibrated default probability or any external-action
      probability.
    - ``status`` is a small free-form lifecycle tag.
    - ``visibility`` is a free-form generic visibility tag.
    - ``source_*_ids`` are tuples of plain-id cross-references.
    - ``metadata`` is free-form.
    """

    review_candidate_id: str
    firm_id: str
    as_of_date: str
    review_type_label: str
    leverage_pressure_label: str
    liquidity_pressure_label: str
    maturity_wall_label: str
    dilution_concern_label: str
    covenant_headroom_label: str
    market_access_label: str
    rating_perception_label: str
    status: str
    visibility: str
    confidence: float
    source_need_ids: tuple[str, ...] = field(default_factory=tuple)
    source_funding_option_ids: tuple[str, ...] = field(default_factory=tuple)
    source_firm_state_ids: tuple[str, ...] = field(default_factory=tuple)
    source_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_interbank_liquidity_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_bank_credit_review_signal_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_investor_intent_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.15.6 additive: citation slot for v1.15.4
    # ``IndicativeMarketPressureRecord`` ids. Plain-id cross-
    # reference; not validated against any other book per the v0/v1
    # cross-reference rule. The market-access label vocabulary
    # alignment pinned in v1.15.4 (the ``MARKET_ACCESS_LABELS``
    # frozenset is shared by reference) makes the composition
    # mechanical: the orchestrator may set this review's
    # ``market_access_label`` to match a cited pressure record
    # without any conversion step.
    source_indicative_market_pressure_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "review_candidate_id",
        "firm_id",
        "as_of_date",
        "review_type_label",
        "leverage_pressure_label",
        "liquidity_pressure_label",
        "maturity_wall_label",
        "dilution_concern_label",
        "covenant_headroom_label",
        "market_access_label",
        "rating_perception_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_need_ids",
        "source_funding_option_ids",
        "source_firm_state_ids",
        "source_market_environment_state_ids",
        "source_interbank_liquidity_state_ids",
        "source_bank_credit_review_signal_ids",
        "source_investor_intent_ids",
        "source_indicative_market_pressure_ids",
    )

    LABEL_FIELDS: ClassVar[tuple[tuple[str, frozenset[str]], ...]] = (
        ("review_type_label", REVIEW_TYPE_LABELS),
        ("leverage_pressure_label", LEVERAGE_PRESSURE_LABELS),
        ("liquidity_pressure_label", LIQUIDITY_PRESSURE_LABELS),
        ("maturity_wall_label", MATURITY_WALL_LABELS),
        ("dilution_concern_label", DILUTION_CONCERN_LABELS),
        ("covenant_headroom_label", COVENANT_HEADROOM_LABELS),
        ("market_access_label", MARKET_ACCESS_LABELS),
        ("rating_perception_label", RATING_PERCEPTION_LABELS),
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
                "default probability)"
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
            "review_candidate_id": self.review_candidate_id,
            "firm_id": self.firm_id,
            "as_of_date": self.as_of_date,
            "review_type_label": self.review_type_label,
            "leverage_pressure_label": self.leverage_pressure_label,
            "liquidity_pressure_label": self.liquidity_pressure_label,
            "maturity_wall_label": self.maturity_wall_label,
            "dilution_concern_label": self.dilution_concern_label,
            "covenant_headroom_label": self.covenant_headroom_label,
            "market_access_label": self.market_access_label,
            "rating_perception_label": self.rating_perception_label,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "source_need_ids": list(self.source_need_ids),
            "source_funding_option_ids": list(self.source_funding_option_ids),
            "source_firm_state_ids": list(self.source_firm_state_ids),
            "source_market_environment_state_ids": list(
                self.source_market_environment_state_ids
            ),
            "source_interbank_liquidity_state_ids": list(
                self.source_interbank_liquidity_state_ids
            ),
            "source_bank_credit_review_signal_ids": list(
                self.source_bank_credit_review_signal_ids
            ),
            "source_investor_intent_ids": list(self.source_investor_intent_ids),
            "source_indicative_market_pressure_ids": list(
                self.source_indicative_market_pressure_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class CapitalStructureReviewBook:
    """Append-only storage for v1.14.3
    ``CapitalStructureReviewCandidate`` instances. The book emits
    exactly one ledger record per ``add_candidate`` call
    (``RecordType.CAPITAL_STRUCTURE_REVIEW_CANDIDATE_RECORDED``)
    and refuses to mutate any other source-of-truth book.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _candidates: dict[str, CapitalStructureReviewCandidate] = field(
        default_factory=dict
    )

    def add_candidate(
        self, candidate: CapitalStructureReviewCandidate
    ) -> CapitalStructureReviewCandidate:
        if candidate.review_candidate_id in self._candidates:
            raise DuplicateCapitalStructureReviewError(
                f"Duplicate review_candidate_id: "
                f"{candidate.review_candidate_id}"
            )
        self._candidates[candidate.review_candidate_id] = candidate

        if self.ledger is not None:
            self.ledger.append(
                event_type="capital_structure_review_candidate_recorded",
                simulation_date=self._now(),
                object_id=candidate.review_candidate_id,
                source=candidate.firm_id,
                payload={
                    "review_candidate_id": candidate.review_candidate_id,
                    "firm_id": candidate.firm_id,
                    "as_of_date": candidate.as_of_date,
                    "review_type_label": candidate.review_type_label,
                    "leverage_pressure_label": candidate.leverage_pressure_label,
                    "liquidity_pressure_label": candidate.liquidity_pressure_label,
                    "maturity_wall_label": candidate.maturity_wall_label,
                    "dilution_concern_label": candidate.dilution_concern_label,
                    "covenant_headroom_label": candidate.covenant_headroom_label,
                    "market_access_label": candidate.market_access_label,
                    "rating_perception_label": candidate.rating_perception_label,
                    "status": candidate.status,
                    "visibility": candidate.visibility,
                    "confidence": candidate.confidence,
                    "source_need_ids": list(candidate.source_need_ids),
                    "source_funding_option_ids": list(
                        candidate.source_funding_option_ids
                    ),
                    "source_firm_state_ids": list(
                        candidate.source_firm_state_ids
                    ),
                    "source_market_environment_state_ids": list(
                        candidate.source_market_environment_state_ids
                    ),
                    "source_interbank_liquidity_state_ids": list(
                        candidate.source_interbank_liquidity_state_ids
                    ),
                    "source_bank_credit_review_signal_ids": list(
                        candidate.source_bank_credit_review_signal_ids
                    ),
                    "source_investor_intent_ids": list(
                        candidate.source_investor_intent_ids
                    ),
                    "source_indicative_market_pressure_ids": list(
                        candidate.source_indicative_market_pressure_ids
                    ),
                },
                space_id="capital_structure_reviews",
                visibility=candidate.visibility,
                confidence=candidate.confidence,
            )
        return candidate

    def get_candidate(
        self, review_candidate_id: str
    ) -> CapitalStructureReviewCandidate:
        try:
            return self._candidates[review_candidate_id]
        except KeyError as exc:
            raise UnknownCapitalStructureReviewError(
                f"Capital structure review candidate not found: "
                f"{review_candidate_id!r}"
            ) from exc

    def list_candidates(self) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(self._candidates.values())

    def list_by_firm(
        self, firm_id: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c for c in self._candidates.values() if c.firm_id == firm_id
        )

    def list_by_review_type(
        self, review_type_label: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if c.review_type_label == review_type_label
        )

    def list_by_market_access(
        self, market_access_label: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if c.market_access_label == market_access_label
        )

    def list_by_status(
        self, status: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c for c in self._candidates.values() if c.status == status
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            c for c in self._candidates.values() if c.as_of_date == target
        )

    def list_by_need(
        self, need_id: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if need_id in c.source_need_ids
        )

    def list_by_funding_option(
        self, funding_option_id: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if funding_option_id in c.source_funding_option_ids
        )

    def list_by_indicative_market_pressure(
        self, market_pressure_id: str
    ) -> tuple[CapitalStructureReviewCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if market_pressure_id in c.source_indicative_market_pressure_ids
        )

    def snapshot(self) -> dict[str, Any]:
        candidates = sorted(
            (c.to_dict() for c in self._candidates.values()),
            key=lambda item: item["review_candidate_id"],
        )
        return {
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
