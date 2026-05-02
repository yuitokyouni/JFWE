"""
v1.10.3 corporate-side strategic response candidate — storage layer.

Implements the corporate-side primitive of the v1.10 engagement /
strategic-response layer named in
``docs/v1_10_universal_engagement_and_response_design.md`` and §70 of
``docs/world_model.md``. The investor-side primitives
(``PortfolioCompanyDialogueRecord`` for v1.10.2 and
``InvestorEscalationCandidate`` for v1.10.3) live in
``world/engagement.py``.

- ``CorporateStrategicResponseCandidate`` — a single immutable,
  append-only record naming that a portfolio company *could* take a
  given strategic response in a given period, given prior
  stewardship themes, dialogues, signals, and valuations. The
  candidate is **not** an executed corporate action: no buyback, no
  dividend change, no divestment, no merger, no governance change,
  no disclosure filing, no operational restructure occurs because a
  candidate is recorded.
- ``StrategicResponseCandidateBook`` — append-only storage with
  read-only listings and a deterministic snapshot.

Scope discipline (v1.10.3, corporate side)
==========================================

A ``CorporateStrategicResponseCandidate`` is **a candidate, not an
execution**. It records *that* a firm has named a strategic-response
option in scope for itself in a given period, in response to the
referenced themes, dialogues, signals, and valuations. It does not
buy back shares, does not change dividends, does not divest assets,
does not merge, does not change the board, does not file a
disclosure, does not run an operational restructure, does not move
ownership, does not move price, does not recommend any investment /
divestment / weight change, and does not mutate any other
source-of-truth book in the kernel.

By itself, a strategic-response candidate:

- does **not** execute any corporate action;
- does **not** vote, file proxies, or take any AGM / EGM action;
- does **not** issue any disclosure filing;
- does **not** recommend any investment, divestment, or weight
  change;
- does **not** trade, change ownership, or move any price;
- does **not** form any forecast or behavior probability;
- does **not** mutate any other source-of-truth book in the kernel
  (only the ``StrategicResponseCandidateBook`` itself and the
  kernel ledger are written to).

The record fields are jurisdiction-neutral by construction. The
book refuses to validate any controlled-vocabulary field
(``response_type``, ``status``, ``priority``, ``horizon``,
``expected_effect_label``, ``constraint_label``, ``visibility``)
against any specific country, regulator, code, or named
institution — those calibrations live in v2 (Japan public-data) and
beyond, not here.

Cross-references (``company_id``, ``trigger_theme_ids``,
``trigger_dialogue_ids``, ``trigger_signal_ids``,
``trigger_valuation_ids``) are recorded as data and **not**
validated for resolution against any other book, per the v0/v1
cross-reference rule already used by ``world/attention.py``,
``world/routines.py``, ``world/stewardship.py``, and
``world/engagement.py``.

v1.10.3 ships zero economic behavior: no price formation, no
trading, no lending decisions, no corporate actions, no voting
execution, no proxy filing, no public-campaign execution, no
disclosure filing, no policy reaction functions, no Japan
calibration, no calibrated behavior probabilities.
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


class StrategicResponseError(Exception):
    """Base class for corporate strategic-response-layer errors."""


class DuplicateResponseCandidateError(StrategicResponseError):
    """Raised when a response_candidate_id is added twice."""


class UnknownResponseCandidateError(StrategicResponseError, KeyError):
    """Raised when a response_candidate_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("date must be a date or ISO string")


def _coerce_optional_iso_date(value: date | str | None) -> str | None:
    if value is None:
        return None
    return _coerce_iso_date(value)


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
class CorporateStrategicResponseCandidate:
    """
    Immutable record of one corporate-side strategic-response
    *candidate*.

    A candidate names that a portfolio company *could* take a
    strategic response in a given period, given prior themes,
    dialogues, signals, and valuations. The candidate is **not** an
    executed corporate action — it does not buy back shares, change
    dividends, divest, merge, change the board, file a disclosure,
    or run an operational restructure.

    Field semantics
    ---------------
    - ``response_candidate_id`` is the stable id; unique within a
      ``StrategicResponseCandidateBook``. Candidates are
      append-only — a candidate is never mutated in place; instead,
      a new candidate is added (with a different
      ``response_candidate_id``) when the firm's stance changes (a
      previous candidate may carry ``status="superseded"`` for
      audit).
    - ``company_id`` names the portfolio company on the issuing
      side. Free-form string; cross-references are recorded as data
      and not validated against the registry.
    - ``as_of_date`` is the required ISO ``YYYY-MM-DD`` date naming
      the period the candidate is recorded against.
    - ``response_type`` is a free-form controlled-vocabulary tag
      describing the *kind* of strategic response under
      consideration. Suggested generic, jurisdiction-neutral labels:
      ``"capital_allocation_review"``,
      ``"governance_change_review"``,
      ``"operational_restructure_review"``,
      ``"disclosure_enhancement_review"``,
      ``"sustainability_practice_review"``,
      ``"no_change_candidate"``. v1.10.3 stores the tag without
      enforcing membership in any list.
    - ``status`` is a small free-form lifecycle tag. Recommended
      jurisdiction-neutral labels: ``"draft"`` / ``"active"`` /
      ``"on_hold"`` / ``"withdrawn"`` / ``"superseded"`` /
      ``"closed"``.
    - ``priority`` is a small enumerated tag (``"low"`` /
      ``"medium"`` / ``"high"``). **Never** a calibrated
      probability.
    - ``horizon`` is a free-form label
      (``"short_term"`` / ``"medium_term"`` / ``"long_term"``).
    - ``trigger_theme_ids`` is a tuple of stewardship-theme ids
      that triggered (or contextualize) the candidate;
      cross-references are stored as data and not validated.
    - ``trigger_dialogue_ids`` is a tuple of dialogue-record ids
      that triggered (or contextualize) the candidate;
      cross-references are stored as data and not validated.
    - ``trigger_signal_ids`` is a tuple of signal ids that
      triggered (or contextualize) the candidate; not validated.
      Reserved for ids that resolve against ``SignalBook`` —
      v1.10.4 ``IndustryDemandConditionRecord`` ids must use
      ``trigger_industry_condition_ids`` instead, since they live
      in a separate book and have a separate ledger record type.
    - ``trigger_valuation_ids`` is a tuple of valuation ids that
      triggered (or contextualize) the candidate; not validated.
    - ``trigger_industry_condition_ids`` is a tuple of v1.10.4
      industry-condition ids (``IndustryDemandConditionRecord``)
      that triggered (or contextualize) the candidate;
      cross-references are stored as data and not validated against
      ``IndustryConditionBook``. **Type-correctness slot, added in
      v1.10.4.1**: keeps industry-condition ids out of
      ``trigger_signal_ids`` so that ledger replay, lineage
      reconstruction, and report generation can disambiguate
      ``signal_id`` vs ``condition_id`` by field rather than by
      payload introspection.
    - ``expected_effect_label`` is a small free-form tag describing
      the generic expected-effect class the firm attached to the
      candidate (e.g.,
      ``"expected_efficiency_improvement_candidate"`` /
      ``"expected_governance_improvement_candidate"`` /
      ``"expected_disclosure_quality_improvement_candidate"`` /
      ``"effect_unspecified"``). **Never** a forecast and **never**
      a calibrated probability — illustrative ordering only.
    - ``constraint_label`` is a small free-form tag describing a
      generic constraint or precondition class (e.g.,
      ``"subject_to_board_review"`` /
      ``"subject_to_regulatory_review"`` /
      ``"subject_to_internal_review"`` / ``"no_known_constraint"``).
      Metadata only.
    - ``next_review_date`` is an *optional* ISO ``YYYY-MM-DD`` date
      naming when the firm has scheduled the next internal review
      of the candidate. ``None`` means no scheduled review date.
    - ``visibility`` is a free-form generic visibility tag
      (``"public"`` / ``"internal_only"`` / ``"restricted"``).
      Metadata only; not enforced as a runtime gate in v1.10.3.
    - ``metadata`` is free-form for provenance, parameters, and
      issuer notes. Must not carry verbatim or paraphrased dialogue
      contents, meeting notes, attendee lists, non-public company
      information, named-client material, or expert-interview
      content.

    Anti-fields
    -----------
    The record deliberately has **no** ``transcript``, ``content``,
    ``notes``, ``minutes``, ``attendees``, ``buyback_executed``,
    ``dividend_changed``, ``divestment_executed``,
    ``merger_executed``, ``board_change_executed``,
    ``disclosure_filed``, or equivalent fields. A public-FWE
    candidate stores generic labels and IDs only.
    """

    response_candidate_id: str
    company_id: str
    as_of_date: str
    response_type: str
    status: str
    priority: str
    horizon: str
    expected_effect_label: str
    constraint_label: str
    visibility: str
    trigger_theme_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_dialogue_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_valuation_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_industry_condition_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    next_review_date: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "response_candidate_id",
        "company_id",
        "as_of_date",
        "response_type",
        "status",
        "priority",
        "horizon",
        "expected_effect_label",
        "constraint_label",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "trigger_theme_ids",
        "trigger_dialogue_ids",
        "trigger_signal_ids",
        "trigger_valuation_ids",
        "trigger_industry_condition_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        if self.next_review_date is not None and not isinstance(
            self.next_review_date, (str, date)
        ):
            raise ValueError(
                "next_review_date must be a date, ISO string, or None"
            )

        object.__setattr__(
            self, "as_of_date", _coerce_iso_date(self.as_of_date)
        )
        object.__setattr__(
            self,
            "next_review_date",
            _coerce_optional_iso_date(self.next_review_date),
        )

        if (
            self.next_review_date is not None
            and self.next_review_date < self.as_of_date
        ):
            raise ValueError(
                "next_review_date must be on or after as_of_date"
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
            "response_candidate_id": self.response_candidate_id,
            "company_id": self.company_id,
            "as_of_date": self.as_of_date,
            "response_type": self.response_type,
            "status": self.status,
            "priority": self.priority,
            "horizon": self.horizon,
            "expected_effect_label": self.expected_effect_label,
            "constraint_label": self.constraint_label,
            "next_review_date": self.next_review_date,
            "visibility": self.visibility,
            "trigger_theme_ids": list(self.trigger_theme_ids),
            "trigger_dialogue_ids": list(self.trigger_dialogue_ids),
            "trigger_signal_ids": list(self.trigger_signal_ids),
            "trigger_valuation_ids": list(self.trigger_valuation_ids),
            "trigger_industry_condition_ids": list(
                self.trigger_industry_condition_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class StrategicResponseCandidateBook:
    """
    Append-only storage for ``CorporateStrategicResponseCandidate``
    instances.

    The book emits exactly one ledger record per ``add_candidate``
    call (``RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED``)
    and refuses to mutate any other source-of-truth book in the
    kernel. v1.10.3 ships storage and read-only listings only — no
    automatic candidate inference, no corporate-action execution,
    no disclosure filing, no buyback / dividend / divestment /
    merger / governance-change execution, no economic behavior.

    Cross-references (``company_id``, ``trigger_theme_ids``,
    ``trigger_dialogue_ids``, ``trigger_signal_ids``,
    ``trigger_valuation_ids``) are recorded as data and not
    validated against any other book, per the v0/v1 cross-reference
    rule.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _candidates: dict[str, CorporateStrategicResponseCandidate] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_candidate(
        self, candidate: CorporateStrategicResponseCandidate
    ) -> CorporateStrategicResponseCandidate:
        if candidate.response_candidate_id in self._candidates:
            raise DuplicateResponseCandidateError(
                "Duplicate response_candidate_id: "
                f"{candidate.response_candidate_id}"
            )
        self._candidates[candidate.response_candidate_id] = candidate

        if self.ledger is not None:
            self.ledger.append(
                event_type="corporate_strategic_response_candidate_added",
                simulation_date=self._now(),
                object_id=candidate.response_candidate_id,
                source=candidate.company_id,
                payload={
                    "response_candidate_id": candidate.response_candidate_id,
                    "company_id": candidate.company_id,
                    "as_of_date": candidate.as_of_date,
                    "response_type": candidate.response_type,
                    "status": candidate.status,
                    "priority": candidate.priority,
                    "horizon": candidate.horizon,
                    "expected_effect_label": candidate.expected_effect_label,
                    "constraint_label": candidate.constraint_label,
                    "next_review_date": candidate.next_review_date,
                    "visibility": candidate.visibility,
                    "trigger_theme_ids": list(candidate.trigger_theme_ids),
                    "trigger_dialogue_ids": list(
                        candidate.trigger_dialogue_ids
                    ),
                    "trigger_signal_ids": list(
                        candidate.trigger_signal_ids
                    ),
                    "trigger_valuation_ids": list(
                        candidate.trigger_valuation_ids
                    ),
                    "trigger_industry_condition_ids": list(
                        candidate.trigger_industry_condition_ids
                    ),
                },
                space_id="strategic_response",
                agent_id=candidate.company_id,
                visibility=candidate.visibility,
            )
        return candidate

    def get_candidate(
        self, response_candidate_id: str
    ) -> CorporateStrategicResponseCandidate:
        try:
            return self._candidates[response_candidate_id]
        except KeyError as exc:
            raise UnknownResponseCandidateError(
                f"Strategic response candidate not found: "
                f"{response_candidate_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_candidates(
        self,
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(self._candidates.values())

    def list_by_company(
        self, company_id: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if c.company_id == company_id
        )

    def list_by_type(
        self, response_type: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if c.response_type == response_type
        )

    def list_by_status(
        self, status: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(
            c for c in self._candidates.values() if c.status == status
        )

    def list_by_priority(
        self, priority: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if c.priority == priority
        )

    def list_by_theme(
        self, theme_id: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if theme_id in c.trigger_theme_ids
        )

    def list_by_dialogue(
        self, dialogue_id: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        return tuple(
            c
            for c in self._candidates.values()
            if dialogue_id in c.trigger_dialogue_ids
        )

    def list_by_industry_condition(
        self, condition_id: str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        """
        Return every candidate whose ``trigger_industry_condition_ids``
        tuple contains ``condition_id``.

        v1.10.4.1: type-correct cross-reference filter for v1.10.4
        ``IndustryDemandConditionRecord`` ids. Industry-condition ids
        do **not** appear in ``trigger_signal_ids`` — they live in
        their own slot so that ledger replay, lineage
        reconstruction, and report generation can disambiguate
        ``signal_id`` vs ``condition_id`` by field rather than by
        payload introspection.
        """
        return tuple(
            c
            for c in self._candidates.values()
            if condition_id in c.trigger_industry_condition_ids
        )

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[CorporateStrategicResponseCandidate, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            c
            for c in self._candidates.values()
            if c.as_of_date == target
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        candidates = sorted(
            (c.to_dict() for c in self._candidates.values()),
            key=lambda item: item["response_candidate_id"],
        )
        return {
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
