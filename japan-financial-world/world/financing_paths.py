"""
v1.14.4 CorporateFinancingPathRecord +
CorporateFinancingPathBook +
``build_corporate_financing_path`` helper.

Append-only **label-based** synthetic record that connects the
three v1.14 storage layers into an auditable financing subgraph
for one firm at a point in time:

    CorporateFinancingNeedRecord (v1.14.1)
        -> FundingOptionCandidate (v1.14.2)
        -> CapitalStructureReviewCandidate (v1.14.3)

A ``CorporateFinancingPathRecord`` is a **graph / audit object**.
It is **not** execution. There is **no choice of optimal option,
no loan approval, no bond issuance, no equity issuance, no
underwriting, no syndication, no bookbuilding, no pricing, no
capital-structure optimisation, no investment recommendation,
no real leverage / D/E / WACC calculation, no real data
ingestion, no Japan calibration, no execution path**.

The record carries:

- five small closed-set labels:
    - ``path_type_label``     — what kind of financing path this is
    - ``path_status_label``   — lifecycle posture
    - ``coherence_label``     — does the cited evidence agree?
    - ``constraint_label``    — what is the binding constraint, if any?
    - ``next_review_label``   — what should happen next?
- seven id-tuple slots cross-referencing the cited records:
    ``need_ids``, ``funding_option_ids``,
    ``capital_structure_review_ids``,
    ``market_environment_state_ids``,
    ``interbank_liquidity_state_ids``,
    ``bank_credit_review_signal_ids``, ``investor_intent_ids``.
  Cross-references are stored as data and not validated against
  any other book per the v0/v1 cross-reference rule.
- a synthetic ``confidence`` ordering in ``[0.0, 1.0]``.
- ``status``, ``visibility``, ``metadata``.

The record carries **no** ``selected_option``, ``optimal_option``,
``approved``, ``executed``, ``commitment``, ``underwriting``,
``syndication``, ``allocation``, ``pricing``, ``interest_rate``,
``spread``, ``coupon``, ``fee``, ``offering_price``,
``target_price``, ``expected_return``, ``recommendation``,
``investment_advice``, or ``real_data_value`` field. Tests pin
the absence on both the dataclass field set and the ledger
payload key set.

The book emits exactly one ledger record per ``add_path`` call
(``RecordType.CORPORATE_FINANCING_PATH_RECORDED``) and refuses
to mutate any other source-of-truth book in the kernel.
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


PATH_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "refinancing_path",
        "liquidity_buffer_path",
        "capex_funding_path",
        "acquisition_funding_path",
        "balance_sheet_repair_path",
        "working_capital_path",
        "mixed_path",
        "unknown",
    }
)

PATH_STATUS_LABELS: frozenset[str] = frozenset(
    {
        "draft",
        "under_review",
        "stale",
        "superseded",
        "archived",
        "unknown",
    }
)

COHERENCE_LABELS: frozenset[str] = frozenset(
    {
        "coherent",
        "partially_coherent",
        "conflicting_evidence",
        "insufficient_evidence",
        "unknown",
    }
)

CONSTRAINT_LABELS: frozenset[str] = frozenset(
    {
        "market_access_constraint",
        "liquidity_constraint",
        "leverage_constraint",
        "dilution_constraint",
        "maturity_constraint",
        "covenant_constraint",
        "no_obvious_constraint",
        "unknown",
    }
)

NEXT_REVIEW_LABELS: frozenset[str] = frozenset(
    {
        "monitor",
        "revisit_next_period",
        "request_more_evidence",
        "compare_options",
        "escalate_to_capital_structure_review",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CorporateFinancingPathError(Exception):
    """Base class for v1.14.4 corporate-financing-path-layer errors."""


class DuplicateCorporateFinancingPathError(CorporateFinancingPathError):
    """Raised when a financing_path_id is added twice."""


class UnknownCorporateFinancingPathError(
    CorporateFinancingPathError, KeyError
):
    """Raised when a financing_path_id is not found."""


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
class CorporateFinancingPathRecord:
    """Immutable record of one financing reasoning path for a
    firm at a point in time. Graph / audit object — not
    execution.

    See module docstring for label vocabularies; v1.14.4 enforces
    closed-set membership at construction so downstream readers
    can rely on the small label sets.
    """

    financing_path_id: str
    firm_id: str
    as_of_date: str
    path_type_label: str
    path_status_label: str
    coherence_label: str
    constraint_label: str
    next_review_label: str
    status: str
    visibility: str
    confidence: float
    need_ids: tuple[str, ...] = field(default_factory=tuple)
    funding_option_ids: tuple[str, ...] = field(default_factory=tuple)
    capital_structure_review_ids: tuple[str, ...] = field(default_factory=tuple)
    market_environment_state_ids: tuple[str, ...] = field(default_factory=tuple)
    interbank_liquidity_state_ids: tuple[str, ...] = field(default_factory=tuple)
    bank_credit_review_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    investor_intent_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.15.6 additive: citation slot for v1.15.4
    # ``IndicativeMarketPressureRecord`` ids. Naming follows the
    # path's existing convention (no ``source_`` prefix) — every
    # tuple slot on ``CorporateFinancingPathRecord`` reads as the
    # set of cited ids of that bucket. The
    # :func:`build_corporate_financing_path` helper accepts these
    # ids as an additional kwarg and uses them to override
    # ``constraint_label`` / ``coherence_label`` deterministically
    # when the cited pressure conflicts with the cited reviews.
    indicative_market_pressure_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "financing_path_id",
        "firm_id",
        "as_of_date",
        "path_type_label",
        "path_status_label",
        "coherence_label",
        "constraint_label",
        "next_review_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "need_ids",
        "funding_option_ids",
        "capital_structure_review_ids",
        "market_environment_state_ids",
        "interbank_liquidity_state_ids",
        "bank_credit_review_signal_ids",
        "investor_intent_ids",
        "indicative_market_pressure_ids",
    )

    LABEL_FIELDS: ClassVar[tuple[tuple[str, frozenset[str]], ...]] = (
        ("path_type_label", PATH_TYPE_LABELS),
        ("path_status_label", PATH_STATUS_LABELS),
        ("coherence_label", COHERENCE_LABELS),
        ("constraint_label", CONSTRAINT_LABELS),
        ("next_review_label", NEXT_REVIEW_LABELS),
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
            "financing_path_id": self.financing_path_id,
            "firm_id": self.firm_id,
            "as_of_date": self.as_of_date,
            "path_type_label": self.path_type_label,
            "path_status_label": self.path_status_label,
            "coherence_label": self.coherence_label,
            "constraint_label": self.constraint_label,
            "next_review_label": self.next_review_label,
            "status": self.status,
            "visibility": self.visibility,
            "confidence": self.confidence,
            "need_ids": list(self.need_ids),
            "funding_option_ids": list(self.funding_option_ids),
            "capital_structure_review_ids": list(
                self.capital_structure_review_ids
            ),
            "market_environment_state_ids": list(
                self.market_environment_state_ids
            ),
            "interbank_liquidity_state_ids": list(
                self.interbank_liquidity_state_ids
            ),
            "bank_credit_review_signal_ids": list(
                self.bank_credit_review_signal_ids
            ),
            "investor_intent_ids": list(self.investor_intent_ids),
            "indicative_market_pressure_ids": list(
                self.indicative_market_pressure_ids
            ),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class CorporateFinancingPathBook:
    """Append-only storage for v1.14.4
    ``CorporateFinancingPathRecord`` instances. The book emits
    exactly one ledger record per ``add_path`` call
    (``RecordType.CORPORATE_FINANCING_PATH_RECORDED``) and
    refuses to mutate any other source-of-truth book.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _paths: dict[str, CorporateFinancingPathRecord] = field(
        default_factory=dict
    )

    def add_path(
        self, path: CorporateFinancingPathRecord
    ) -> CorporateFinancingPathRecord:
        if path.financing_path_id in self._paths:
            raise DuplicateCorporateFinancingPathError(
                f"Duplicate financing_path_id: {path.financing_path_id}"
            )
        self._paths[path.financing_path_id] = path

        if self.ledger is not None:
            self.ledger.append(
                event_type="corporate_financing_path_recorded",
                simulation_date=self._now(),
                object_id=path.financing_path_id,
                source=path.firm_id,
                payload={
                    "financing_path_id": path.financing_path_id,
                    "firm_id": path.firm_id,
                    "as_of_date": path.as_of_date,
                    "path_type_label": path.path_type_label,
                    "path_status_label": path.path_status_label,
                    "coherence_label": path.coherence_label,
                    "constraint_label": path.constraint_label,
                    "next_review_label": path.next_review_label,
                    "status": path.status,
                    "visibility": path.visibility,
                    "confidence": path.confidence,
                    "need_ids": list(path.need_ids),
                    "funding_option_ids": list(path.funding_option_ids),
                    "capital_structure_review_ids": list(
                        path.capital_structure_review_ids
                    ),
                    "market_environment_state_ids": list(
                        path.market_environment_state_ids
                    ),
                    "interbank_liquidity_state_ids": list(
                        path.interbank_liquidity_state_ids
                    ),
                    "bank_credit_review_signal_ids": list(
                        path.bank_credit_review_signal_ids
                    ),
                    "investor_intent_ids": list(path.investor_intent_ids),
                    "indicative_market_pressure_ids": list(
                        path.indicative_market_pressure_ids
                    ),
                },
                space_id="financing_paths",
                visibility=path.visibility,
                confidence=path.confidence,
            )
        return path

    def get_path(
        self, financing_path_id: str
    ) -> CorporateFinancingPathRecord:
        try:
            return self._paths[financing_path_id]
        except KeyError as exc:
            raise UnknownCorporateFinancingPathError(
                f"Corporate financing path not found: "
                f"{financing_path_id!r}"
            ) from exc

    def list_paths(self) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(self._paths.values())

    def list_by_firm(
        self, firm_id: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p for p in self._paths.values() if p.firm_id == firm_id
        )

    def list_by_path_type(
        self, path_type_label: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if p.path_type_label == path_type_label
        )

    def list_by_path_status(
        self, path_status_label: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if p.path_status_label == path_status_label
        )

    def list_by_coherence(
        self, coherence_label: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if p.coherence_label == coherence_label
        )

    def list_by_constraint(
        self, constraint_label: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if p.constraint_label == constraint_label
        )

    def list_by_status(
        self, status: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(p for p in self._paths.values() if p.status == status)

    def list_by_date(
        self, as_of: date | str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        target = _coerce_iso_date(as_of)
        return tuple(
            p for p in self._paths.values() if p.as_of_date == target
        )

    def list_by_need(
        self, need_id: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p for p in self._paths.values() if need_id in p.need_ids
        )

    def list_by_funding_option(
        self, funding_option_id: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if funding_option_id in p.funding_option_ids
        )

    def list_by_capital_structure_review(
        self, review_candidate_id: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if review_candidate_id in p.capital_structure_review_ids
        )

    def list_by_indicative_market_pressure(
        self, market_pressure_id: str
    ) -> tuple[CorporateFinancingPathRecord, ...]:
        return tuple(
            p
            for p in self._paths.values()
            if market_pressure_id in p.indicative_market_pressure_ids
        )

    def snapshot(self) -> dict[str, Any]:
        paths = sorted(
            (p.to_dict() for p in self._paths.values()),
            key=lambda item: item["financing_path_id"],
        )
        return {
            "path_count": len(paths),
            "paths": paths,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()


# ---------------------------------------------------------------------------
# Deterministic builder
#
# The helper resolves only the explicitly cited ids by calling
# ``kernel.corporate_financing_needs.get_need(id)`` and
# ``kernel.capital_structure_reviews.get_candidate(id)``. It never
# scans the books globally (no ``list_*`` calls). Any cited id
# that fails to resolve is kept on the record as a plain id and
# does not contribute to label derivation.
# ---------------------------------------------------------------------------


_PURPOSE_TO_PATH_TYPE: Mapping[str, str] = {
    "refinancing": "refinancing_path",
    "working_capital": "working_capital_path",
    "growth_capex": "capex_funding_path",
    "acquisition": "acquisition_funding_path",
    "restructuring": "balance_sheet_repair_path",
}


def build_corporate_financing_path(
    kernel: Any,
    *,
    firm_id: str,
    as_of_date: date | str,
    financing_path_id: str | None = None,
    need_ids: Iterable[str] = (),
    funding_option_ids: Iterable[str] = (),
    capital_structure_review_ids: Iterable[str] = (),
    market_environment_state_ids: Iterable[str] = (),
    interbank_liquidity_state_ids: Iterable[str] = (),
    bank_credit_review_signal_ids: Iterable[str] = (),
    investor_intent_ids: Iterable[str] = (),
    indicative_market_pressure_ids: Iterable[str] = (),
    confidence: float = 0.5,
    status: str = "active",
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> CorporateFinancingPathRecord:
    """Synthesise one ``CorporateFinancingPathRecord`` from a set
    of cited record ids and add it to ``kernel.financing_paths``.

    The helper is a deterministic pure-label synthesiser:

    - It reads only the cited ids via
      ``kernel.corporate_financing_needs.get_need``,
      ``kernel.capital_structure_reviews.get_candidate``, and (at
      v1.15.6) ``kernel.indicative_market_pressure.get_record``.
      It does not scan any book globally.
    - It does not choose an optimal funding option. It does not
      approve, price, underwrite, or recommend any financing.
    - It produces small synthetic labels using the label content
      of the cited records:

      ``path_type_label`` — derived from the
      ``funding_purpose_label`` of cited needs (single → mapped;
      multi → ``mixed_path``; none → ``unknown``).

      ``coherence_label`` — ``insufficient_evidence`` if either
      ``funding_option_ids`` or ``capital_structure_review_ids``
      is empty; otherwise ``coherent`` if cited reviews share one
      ``market_access_label``, else ``partially_coherent``. **At
      v1.15.6**, if any cited
      :class:`IndicativeMarketPressureRecord` has
      ``market_access_label`` ∈ {``constrained``, ``closed``}
      while any cited review has ``market_access_label`` ∈
      {``open``, ``selective``}, the coherence is upgraded to
      ``conflicting_evidence`` (the financing surface and the
      market surface disagree).

      ``constraint_label`` — first-match priority over cited
      reviews (market_access → liquidity → leverage → maturity →
      covenant → dilution); ``no_obvious_constraint`` if no
      review trips a flag, ``unknown`` if no reviews are cited.
      **At v1.15.6**, if any cited
      :class:`IndicativeMarketPressureRecord` has
      ``market_access_label`` ∈ {``constrained``, ``closed``},
      the constraint is forced to ``market_access_constraint``
      regardless of the review-derived label — the market
      pressure dominates when access is actually constrained.

      ``next_review_label`` — ``request_more_evidence`` /
      ``compare_options`` / ``escalate_to_capital_structure_review``
      / ``monitor`` derived from coherence and constraint.

      ``path_status_label`` — always ``draft`` at synthesis.
    """

    need_ids_t = tuple(need_ids)
    funding_option_ids_t = tuple(funding_option_ids)
    review_ids_t = tuple(capital_structure_review_ids)
    mes_ids_t = tuple(market_environment_state_ids)
    ibl_ids_t = tuple(interbank_liquidity_state_ids)
    bcrs_ids_t = tuple(bank_credit_review_signal_ids)
    intent_ids_t = tuple(investor_intent_ids)
    pressure_ids_t = tuple(indicative_market_pressure_ids)

    # Resolve cited needs (only the cited ids — never list_*).
    purposes: list[str] = []
    for nid in need_ids_t:
        try:
            need = kernel.corporate_financing_needs.get_need(nid)
        except Exception:
            continue
        purposes.append(need.funding_purpose_label)

    # path_type_label
    if not purposes:
        path_type = "unknown"
    else:
        unique_purposes = set(purposes)
        if len(unique_purposes) == 1:
            only = next(iter(unique_purposes))
            path_type = _PURPOSE_TO_PATH_TYPE.get(only, "unknown")
        else:
            path_type = "mixed_path"

    # Resolve cited reviews (only the cited ids — never list_*).
    reviews: list[Any] = []
    for rid in review_ids_t:
        try:
            review = kernel.capital_structure_reviews.get_candidate(rid)
        except Exception:
            continue
        reviews.append(review)

    # v1.15.6 — resolve cited indicative market pressure records
    # (only the cited ids — never list_*).
    pressures: list[Any] = []
    for pid in pressure_ids_t:
        try:
            pressure = kernel.indicative_market_pressure.get_record(pid)
        except Exception:
            continue
        pressures.append(pressure)

    pressure_market_access_set = {
        p.market_access_label for p in pressures
    }
    pressure_constrains_access = bool(
        pressure_market_access_set & {"constrained", "closed"}
    )

    # coherence_label
    if not funding_option_ids_t or not review_ids_t:
        coherence = "insufficient_evidence"
    elif not reviews:
        coherence = "insufficient_evidence"
    else:
        market_access_set = {r.market_access_label for r in reviews}
        coherence = (
            "coherent" if len(market_access_set) == 1 else "partially_coherent"
        )
        # v1.15.6 — if any cited pressure says access is
        # constrained / closed but any cited review says access is
        # open / selective, the financing surface and the market
        # surface disagree → ``conflicting_evidence``.
        if pressure_constrains_access and (
            market_access_set & {"open", "selective"}
        ):
            coherence = "conflicting_evidence"

    # constraint_label — first match wins
    if not reviews:
        constraint = "unknown"
    else:
        constraint = "no_obvious_constraint"
        for r in reviews:
            if r.market_access_label in ("constrained", "closed"):
                constraint = "market_access_constraint"
                break
            if r.liquidity_pressure_label == "stressed":
                constraint = "liquidity_constraint"
                break
            if r.leverage_pressure_label == "high":
                constraint = "leverage_constraint"
                break
            if r.maturity_wall_label == "concentrated":
                constraint = "maturity_constraint"
                break
            if r.covenant_headroom_label == "tight":
                constraint = "covenant_constraint"
                break
            if r.dilution_concern_label == "high":
                constraint = "dilution_constraint"
                break

    # v1.15.6 — pressure dominates: if any cited pressure says
    # access is constrained / closed, override the constraint to
    # ``market_access_constraint`` regardless of the review-derived
    # label. The market surface beats the financing surface for
    # the access-constraint label.
    if pressure_constrains_access:
        constraint = "market_access_constraint"

    # next_review_label
    if coherence == "insufficient_evidence":
        next_review = "request_more_evidence"
    elif coherence in ("partially_coherent", "conflicting_evidence"):
        next_review = "compare_options"
    elif constraint not in ("no_obvious_constraint", "unknown"):
        next_review = "escalate_to_capital_structure_review"
    else:
        next_review = "monitor"

    if financing_path_id is None:
        as_iso = _coerce_iso_date(as_of_date)
        financing_path_id = f"corporate_financing_path:{firm_id}:{as_iso}"

    record = CorporateFinancingPathRecord(
        financing_path_id=financing_path_id,
        firm_id=firm_id,
        as_of_date=as_of_date,
        path_type_label=path_type,
        path_status_label="draft",
        coherence_label=coherence,
        constraint_label=constraint,
        next_review_label=next_review,
        status=status,
        visibility=visibility,
        confidence=confidence,
        need_ids=need_ids_t,
        funding_option_ids=funding_option_ids_t,
        capital_structure_review_ids=review_ids_t,
        market_environment_state_ids=mes_ids_t,
        interbank_liquidity_state_ids=ibl_ids_t,
        bank_credit_review_signal_ids=bcrs_ids_t,
        investor_intent_ids=intent_ids_t,
        indicative_market_pressure_ids=pressure_ids_t,
        metadata=dict(metadata) if metadata else {},
    )
    return kernel.financing_paths.add_path(record)
