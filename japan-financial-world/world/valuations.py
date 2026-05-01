from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

from world.clock import Clock
from world.ledger import Ledger
from world.prices import PriceBook


class ValuationError(Exception):
    """Base class for valuation-layer errors."""


class DuplicateValuationError(ValuationError):
    """Raised when a valuation_id is added twice."""


class UnknownValuationError(ValuationError, KeyError):
    """Raised when a valuation_id is not found."""


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("date must be a date or ISO string")


@dataclass(frozen=True)
class ValuationRecord:
    """
    A single opinionated valuation claim.

    A valuation is *what some valuer thinks some subject is worth, for a
    specific purpose, computed by a specific method, using specific
    assumptions and inputs, as of a specific date*. It is **not** a price
    (that lives in PriceBook). It is **not** a fundamental truth (the
    fundamentals layer is deferred to a later v1 milestone).

    Two important consequences of this framing:

    1. Multiple valuations of the same subject can coexist without
       conflict. A real estate appraiser, a covenant test, a buy-side
       investor model, and a tax-purpose mark may all produce different
       numbers for the same building on the same day. v1.1 stores all of
       them; it does not pick a winner.
    2. A valuation can be qualitative or failed. ``estimated_value`` may
       be ``None`` — for example when a method bails out, when only a
       directional opinion is recorded, or when inputs are missing.

    Currency vs numeraire
    ---------------------
    These are intentionally two distinct fields:

    - ``currency`` — the display currency of ``estimated_value``. This is
      the unit of the number itself. If ``estimated_value`` is 1.5e10 and
      ``currency`` is ``"JPY"``, the claim is "fifteen billion yen".
    - ``numeraire`` — the perspective currency or value basis the valuer
      is reasoning in. A USD-investor valuing the reference manufacturer in JPY for display
      would set ``currency="JPY"`` and ``numeraire="USD"``. A purely
      domestic Japanese DCF valuation would have both ``"JPY"``.

    v1.1 does not implement FX conversion. Comparators that detect a
    currency mismatch refuse to compute a numeric gap and record the
    reason instead.
    """

    valuation_id: str
    subject_id: str
    valuer_id: str
    valuation_type: str
    purpose: str
    method: str
    as_of_date: str
    estimated_value: float | None = None
    currency: str = "unspecified"
    numeraire: str = "unspecified"
    confidence: float = 1.0
    assumptions: Mapping[str, Any] = field(default_factory=dict)
    inputs: Mapping[str, Any] = field(default_factory=dict)
    related_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.valuation_id:
            raise ValueError("valuation_id is required")
        if not self.subject_id:
            raise ValueError("subject_id is required")
        if not self.valuer_id:
            raise ValueError("valuer_id is required")
        if not self.valuation_type:
            raise ValueError("valuation_type is required")
        if not self.purpose:
            raise ValueError("purpose is required")
        if not self.method:
            raise ValueError("method is required")
        if not self.as_of_date:
            raise ValueError("as_of_date is required")

        object.__setattr__(self, "as_of_date", _coerce_iso_date(self.as_of_date))

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        object.__setattr__(self, "assumptions", dict(self.assumptions))
        object.__setattr__(self, "inputs", dict(self.inputs))
        object.__setattr__(self, "related_ids", tuple(self.related_ids))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "valuation_id": self.valuation_id,
            "subject_id": self.subject_id,
            "valuer_id": self.valuer_id,
            "valuation_type": self.valuation_type,
            "purpose": self.purpose,
            "method": self.method,
            "as_of_date": self.as_of_date,
            "estimated_value": self.estimated_value,
            "currency": self.currency,
            "numeraire": self.numeraire,
            "confidence": self.confidence,
            "assumptions": dict(self.assumptions),
            "inputs": dict(self.inputs),
            "related_ids": list(self.related_ids),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ValuationGap:
    """
    The result of comparing one valuation claim against an observed price.

    A ValuationGap is informational. It records "valuer X said Y, the
    market said Z, here is the difference" — but it does not act on the
    difference. Whether a gap matters, what to do about it, who should
    react, and on what timescale are all questions for later v1
    behavioral milestones.

    Field semantics:

    - ``estimated_value`` and ``observed_price`` are copied verbatim from
      the valuation and the latest priced observation respectively. Either
      may be ``None`` (the valuation may not have produced a number; or
      no price may exist for the subject).
    - ``absolute_gap`` is ``estimated_value - observed_price`` when both
      are present.
    - ``relative_gap`` is ``absolute_gap / observed_price`` when
      ``observed_price`` is non-zero.
    - When a numeric gap cannot be computed, both ``absolute_gap`` and
      ``relative_gap`` are ``None``, and ``metadata["reason"]`` records
      the cause: ``"missing_price"``, ``"estimated_value_unavailable"``,
      ``"currency_mismatch"``, or ``"observed_price_zero"``.
    - ``currency`` mirrors the valuation's currency. v1.1 does not
      attempt FX conversion; a currency mismatch with the priced
      observation aborts the comparison rather than converting.
    """

    subject_id: str
    valuation_id: str
    as_of_date: str
    estimated_value: float | None
    observed_price: float | None
    absolute_gap: float | None
    relative_gap: float | None
    currency: str = "unspecified"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "valuation_id": self.valuation_id,
            "as_of_date": self.as_of_date,
            "estimated_value": self.estimated_value,
            "observed_price": self.observed_price,
            "absolute_gap": self.absolute_gap,
            "relative_gap": self.relative_gap,
            "currency": self.currency,
            "metadata": dict(self.metadata),
        }


@dataclass
class ValuationBook:
    """
    Storage for valuation claims.

    Multiple claims about the same subject coexist without conflict. The
    book provides indexed reads (by subject, valuer, type, purpose,
    method) and a "latest by subject" helper that selects the highest
    ``as_of_date`` among the subject's claims.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _valuations: dict[str, ValuationRecord] = field(default_factory=dict)
    _by_subject: dict[str, list[str]] = field(default_factory=dict)

    def add_valuation(self, record: ValuationRecord) -> ValuationRecord:
        if record.valuation_id in self._valuations:
            raise DuplicateValuationError(
                f"Duplicate valuation_id: {record.valuation_id}"
            )
        self._valuations[record.valuation_id] = record
        self._by_subject.setdefault(record.subject_id, []).append(
            record.valuation_id
        )

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="valuation_added",
                simulation_date=simulation_date,
                object_id=record.valuation_id,
                target=record.subject_id,
                agent_id=record.valuer_id,
                payload={
                    "valuation_id": record.valuation_id,
                    "subject_id": record.subject_id,
                    "valuer_id": record.valuer_id,
                    "valuation_type": record.valuation_type,
                    "purpose": record.purpose,
                    "method": record.method,
                    "as_of_date": record.as_of_date,
                    "estimated_value": record.estimated_value,
                    "currency": record.currency,
                    "numeraire": record.numeraire,
                    "related_ids": list(record.related_ids),
                },
                space_id="valuations",
                confidence=record.confidence,
            )
        return record

    def get_valuation(self, valuation_id: str) -> ValuationRecord:
        try:
            return self._valuations[valuation_id]
        except KeyError as exc:
            raise UnknownValuationError(
                f"Valuation not found: {valuation_id!r}"
            ) from exc

    def list_by_subject(self, subject_id: str) -> tuple[ValuationRecord, ...]:
        ids = self._by_subject.get(subject_id, [])
        return tuple(self._valuations[vid] for vid in ids)

    def list_by_valuer(self, valuer_id: str) -> tuple[ValuationRecord, ...]:
        return tuple(
            v for v in self._valuations.values() if v.valuer_id == valuer_id
        )

    def list_by_type(
        self,
        valuation_type: str,
    ) -> tuple[ValuationRecord, ...]:
        return tuple(
            v for v in self._valuations.values() if v.valuation_type == valuation_type
        )

    def list_by_purpose(self, purpose: str) -> tuple[ValuationRecord, ...]:
        return tuple(
            v for v in self._valuations.values() if v.purpose == purpose
        )

    def list_by_method(self, method: str) -> tuple[ValuationRecord, ...]:
        return tuple(
            v for v in self._valuations.values() if v.method == method
        )

    def get_latest_by_subject(
        self,
        subject_id: str,
    ) -> ValuationRecord | None:
        """
        Return the valuation for ``subject_id`` with the highest
        ``as_of_date``. ISO dates compare lexicographically, so this is a
        date-correct max. Ties are broken by insertion order — the most
        recently added valuation wins among ties.
        """
        ids = self._by_subject.get(subject_id, [])
        if not ids:
            return None
        candidates = [self._valuations[vid] for vid in ids]
        latest = candidates[0]
        for record in candidates[1:]:
            if record.as_of_date >= latest.as_of_date:
                latest = record
        return latest

    def all_valuations(self) -> tuple[ValuationRecord, ...]:
        return tuple(self._valuations.values())

    def snapshot(self) -> dict[str, Any]:
        valuations = sorted(
            (record.to_dict() for record in self._valuations.values()),
            key=lambda item: item["valuation_id"],
        )
        return {"count": len(valuations), "valuations": valuations}


@dataclass
class ValuationComparator:
    """
    Compares valuation claims to observed prices.

    The comparator is deliberately thin: it reads from ``ValuationBook``
    and ``PriceBook`` and produces a ``ValuationGap``. It does not act
    on the gap, propagate it, or trigger any other space.

    Currency handling
    -----------------
    v1.1 does not implement FX conversion. The comparator detects a
    currency mismatch by inspecting ``metadata["currency"]`` on the
    latest priced observation. If the price record declares a currency
    different from the valuation's ``currency`` field, the comparator
    refuses to compute a numeric gap and records
    ``metadata["reason"] = "currency_mismatch"`` on the resulting
    ``ValuationGap``. If the price record does not declare a currency,
    no mismatch is detected and the gap is computed normally — this is
    the intentional v1.1 behavior, not an oversight.
    """

    valuations: ValuationBook
    prices: PriceBook
    ledger: Ledger | None = None
    clock: Clock | None = None

    def compare_to_latest_price(self, valuation_id: str) -> ValuationGap:
        valuation = self.valuations.get_valuation(valuation_id)
        latest = self.prices.get_latest_price(valuation.subject_id)

        gap = self._build_gap(valuation, latest)
        self._record_comparison(valuation, gap)
        return gap

    def compare_subject_latest(
        self,
        subject_id: str,
    ) -> ValuationGap | None:
        latest_valuation = self.valuations.get_latest_by_subject(subject_id)
        if latest_valuation is None:
            return None
        return self.compare_to_latest_price(latest_valuation.valuation_id)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _build_gap(
        self,
        valuation: ValuationRecord,
        latest_price,  # PriceRecord | None
    ) -> ValuationGap:
        observed_price = latest_price.price if latest_price is not None else None

        # Failure path: estimated_value missing.
        if valuation.estimated_value is None:
            return ValuationGap(
                subject_id=valuation.subject_id,
                valuation_id=valuation.valuation_id,
                as_of_date=valuation.as_of_date,
                estimated_value=None,
                observed_price=observed_price,
                absolute_gap=None,
                relative_gap=None,
                currency=valuation.currency,
                metadata={"reason": "estimated_value_unavailable"},
            )

        # Failure path: no priced observation.
        if latest_price is None:
            return ValuationGap(
                subject_id=valuation.subject_id,
                valuation_id=valuation.valuation_id,
                as_of_date=valuation.as_of_date,
                estimated_value=valuation.estimated_value,
                observed_price=None,
                absolute_gap=None,
                relative_gap=None,
                currency=valuation.currency,
                metadata={"reason": "missing_price"},
            )

        # Failure path: declared currency mismatch.
        price_currency = latest_price.metadata.get("currency")
        if (
            price_currency is not None
            and valuation.currency != "unspecified"
            and price_currency != valuation.currency
        ):
            return ValuationGap(
                subject_id=valuation.subject_id,
                valuation_id=valuation.valuation_id,
                as_of_date=valuation.as_of_date,
                estimated_value=valuation.estimated_value,
                observed_price=observed_price,
                absolute_gap=None,
                relative_gap=None,
                currency=valuation.currency,
                metadata={
                    "reason": "currency_mismatch",
                    "valuation_currency": valuation.currency,
                    "price_currency": price_currency,
                },
            )

        # Success path: numeric gap.
        absolute = float(valuation.estimated_value) - float(observed_price)

        if observed_price == 0:
            return ValuationGap(
                subject_id=valuation.subject_id,
                valuation_id=valuation.valuation_id,
                as_of_date=valuation.as_of_date,
                estimated_value=valuation.estimated_value,
                observed_price=observed_price,
                absolute_gap=absolute,
                relative_gap=None,
                currency=valuation.currency,
                metadata={"reason": "observed_price_zero"},
            )

        relative = absolute / float(observed_price)
        return ValuationGap(
            subject_id=valuation.subject_id,
            valuation_id=valuation.valuation_id,
            as_of_date=valuation.as_of_date,
            estimated_value=valuation.estimated_value,
            observed_price=observed_price,
            absolute_gap=absolute,
            relative_gap=relative,
            currency=valuation.currency,
            metadata={},
        )

    def _record_comparison(
        self,
        valuation: ValuationRecord,
        gap: ValuationGap,
    ) -> None:
        if self.ledger is None:
            return

        # Link back to the originating valuation_added record so the
        # ledger forms a causal chain (per v1 design principle 6).
        parent_ids: tuple[str, ...] = ()
        prior = self.ledger.query(
            record_type="valuation_added", object_id=valuation.valuation_id
        )
        if prior:
            parent_ids = (prior[0].record_id,)

        simulation_date = (
            self.clock.current_date if self.clock is not None else None
        )
        self.ledger.append(
            event_type="valuation_compared",
            simulation_date=simulation_date,
            object_id=valuation.valuation_id,
            target=valuation.subject_id,
            agent_id=valuation.valuer_id,
            payload={
                "valuation_id": valuation.valuation_id,
                "subject_id": valuation.subject_id,
                "estimated_value": gap.estimated_value,
                "observed_price": gap.observed_price,
                "absolute_gap": gap.absolute_gap,
                "relative_gap": gap.relative_gap,
                "currency": gap.currency,
                "reason": gap.metadata.get("reason"),
            },
            parent_record_ids=parent_ids,
            correlation_id=valuation.valuation_id,
            space_id="valuations",
            confidence=valuation.confidence,
        )
