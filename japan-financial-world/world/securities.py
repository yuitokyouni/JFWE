"""
v1.15.1 ListedSecurityRecord + MarketVenueRecord +
SecurityMarketBook.

Append-only **label-based** synthetic storage for the v1.15
securities-market-intent layer's static surface: jurisdiction-
neutral, synthetic records naming listed / tradable securities
and the market venues that host or observe them.

This is a **market surface**. It is **not** trading. It is
**not** price formation. It is **not** order submission. It is
**not** order matching. It is **not** clearing. It is **not**
settlement. It is **not** quote dissemination. It is **not**
real exchange mechanics. It is **not** target prices, expected
returns, or investment recommendations. It is **not** real
data ingestion. It is **not** Japan calibration.

Two records ship at v1.15.1:

    ListedSecurityRecord  — one synthetic listed security
    MarketVenueRecord     — one synthetic market venue

Both records carry only labels + plain-id cross-references +
visibility / status / metadata. Closed-set vocabularies are
**enforced** at construction so downstream readers can rely on
the small label sets:

    security_type_label      ∈ {equity, corporate_bond,
                                 convertible, preferred_equity,
                                 fund_unit, loan_claim, hybrid,
                                 unknown}
    listing_status_label     ∈ {listed, private, suspended,
                                 delisted, proposed, unknown}
    issue_profile_label      ∈ {seasoned, newly_issued,
                                 proposed, legacy, unknown}
    liquidity_profile_label  ∈ {liquid, moderate, thin,
                                 illiquid, unknown}
    investor_access_label    ∈ {broad, qualified_only,
                                 restricted, private, unknown}
    venue_type_label         ∈ {exchange, broker, dealer,
                                 otc_network, dark_pool,
                                 primary_market_platform,
                                 internal_crossing, unknown}
    venue_role_label         ∈ {listing_venue, intent_aggregator,
                                 quote_collector,
                                 primary_distribution_context,
                                 secondary_market_context,
                                 unknown}
    MarketVenueRecord.status ∈ {active, inactive, proposed,
                                 archived, unknown}

A `MarketVenueRecord` carries two tuple slots:

    supported_security_type_labels — every entry must be a
        closed-set ``security_type_label`` value.
    supported_intent_labels — every entry must be a v1.15 **safe
        intent label** (``increase_interest`` /
        ``reduce_interest`` / ``hold_review`` /
        ``liquidity_watch`` / ``rebalance_review`` /
        ``risk_reduction_review`` /
        ``engagement_linked_review``). The forbidden trading
        verbs (``buy`` / ``sell`` / ``order`` / ``target_weight``
        / ``overweight`` / ``underweight`` / ``execution``) are
        rejected by closed-set membership.

Neither record carries an ``order_id``, ``trade_id``, ``buy``,
``sell``, ``bid``, ``ask``, ``quote``, ``execution``,
``clearing``, ``settlement``, ``price``, ``target_price``,
``expected_return``, ``recommendation``, ``investment_advice``,
or ``real_data_value`` field. Tests pin the absence on both
the dataclass field set and the ledger payload key set.

`SecurityMarketBook` is append-only. Adding one
`ListedSecurityRecord` emits exactly one
``RecordType.LISTED_SECURITY_REGISTERED`` ledger record; adding
one `MarketVenueRecord` emits exactly one
``RecordType.MARKET_VENUE_REGISTERED`` ledger record. The book
mutates no other source-of-truth book.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set label vocabularies
# ---------------------------------------------------------------------------


SECURITY_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "equity",
        "corporate_bond",
        "convertible",
        "preferred_equity",
        "fund_unit",
        "loan_claim",
        "hybrid",
        "unknown",
    }
)

LISTING_STATUS_LABELS: frozenset[str] = frozenset(
    {
        "listed",
        "private",
        "suspended",
        "delisted",
        "proposed",
        "unknown",
    }
)

ISSUE_PROFILE_LABELS: frozenset[str] = frozenset(
    {
        "seasoned",
        "newly_issued",
        "proposed",
        "legacy",
        "unknown",
    }
)

LIQUIDITY_PROFILE_LABELS: frozenset[str] = frozenset(
    {
        "liquid",
        "moderate",
        "thin",
        "illiquid",
        "unknown",
    }
)

INVESTOR_ACCESS_LABELS: frozenset[str] = frozenset(
    {
        "broad",
        "qualified_only",
        "restricted",
        "private",
        "unknown",
    }
)

VENUE_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "exchange",
        "broker",
        "dealer",
        "otc_network",
        "dark_pool",
        "primary_market_platform",
        "internal_crossing",
        "unknown",
    }
)

VENUE_ROLE_LABELS: frozenset[str] = frozenset(
    {
        "listing_venue",
        "intent_aggregator",
        "quote_collector",
        "primary_distribution_context",
        "secondary_market_context",
        "unknown",
    }
)

VENUE_STATUS_LABELS: frozenset[str] = frozenset(
    {
        "active",
        "inactive",
        "proposed",
        "archived",
        "unknown",
    }
)

# v1.15 safe intent vocabulary. Carried verbatim from the
# v1.15.0 design note. The forbidden trading verbs (`buy`,
# `sell`, `order`, `target_weight`, `overweight`, `underweight`,
# `execution`) are deliberately absent — closed-set membership
# rejects them.
SAFE_INTENT_LABELS: frozenset[str] = frozenset(
    {
        "increase_interest",
        "reduce_interest",
        "hold_review",
        "liquidity_watch",
        "rebalance_review",
        "risk_reduction_review",
        "engagement_linked_review",
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SecurityMarketError(Exception):
    """Base class for v1.15.1 securities-layer errors."""


class DuplicateListedSecurityError(SecurityMarketError):
    """Raised when a security_id is added twice."""


class UnknownListedSecurityError(SecurityMarketError, KeyError):
    """Raised when a security_id is not found."""


class DuplicateMarketVenueError(SecurityMarketError):
    """Raised when a venue_id is added twice."""


class UnknownMarketVenueError(SecurityMarketError, KeyError):
    """Raised when a venue_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _validate_label_membership(
    values: tuple[str, ...],
    allowed: frozenset[str],
    *,
    field_name: str,
) -> None:
    for entry in values:
        if entry not in allowed:
            raise ValueError(
                f"{field_name} entries must be one of "
                f"{sorted(allowed)!r}; got {entry!r}"
            )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListedSecurityRecord:
    """Immutable record naming one synthetic listed / tradable
    security at a market venue. Storage / surface only — never an
    order, a trade, a price, a quote, a fill, or a recommendation.

    Field semantics
    ---------------
    - ``security_id`` is the stable id; unique within a
      ``SecurityMarketBook``.
    - ``issuer_firm_id`` names the firm that issues this
      security. Free-form jurisdiction-neutral string; the book
      does not validate the id against any other book per the
      v0/v1 cross-reference rule.
    - ``security_type_label`` /  ``listing_status_label`` /
      ``issue_profile_label`` / ``liquidity_profile_label`` /
      ``investor_access_label`` are closed-set labels enforced
      at construction.
    - ``primary_market_venue_id`` names the venue that hosts
      this security as a listing-context reference. Plain-id
      cross-reference; not validated.
    - ``currency_label`` is a free-form synthetic label such
      as ``synthetic_currency_a``. **Never** a real ISO 4217
      code.
    - ``status`` and ``visibility`` are free-form lifecycle /
      visibility tags.
    - ``metadata`` is free-form.
    """

    security_id: str
    issuer_firm_id: str
    security_type_label: str
    listing_status_label: str
    primary_market_venue_id: str
    currency_label: str
    issue_profile_label: str
    liquidity_profile_label: str
    investor_access_label: str
    status: str
    visibility: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "security_id",
        "issuer_firm_id",
        "security_type_label",
        "listing_status_label",
        "primary_market_venue_id",
        "currency_label",
        "issue_profile_label",
        "liquidity_profile_label",
        "investor_access_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[tuple[tuple[str, frozenset[str]], ...]] = (
        ("security_type_label", SECURITY_TYPE_LABELS),
        ("listing_status_label", LISTING_STATUS_LABELS),
        ("issue_profile_label", ISSUE_PROFILE_LABELS),
        ("liquidity_profile_label", LIQUIDITY_PROFILE_LABELS),
        ("investor_access_label", INVESTOR_ACCESS_LABELS),
    )

    def __post_init__(self) -> None:
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

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "security_id": self.security_id,
            "issuer_firm_id": self.issuer_firm_id,
            "security_type_label": self.security_type_label,
            "listing_status_label": self.listing_status_label,
            "primary_market_venue_id": self.primary_market_venue_id,
            "currency_label": self.currency_label,
            "issue_profile_label": self.issue_profile_label,
            "liquidity_profile_label": self.liquidity_profile_label,
            "investor_access_label": self.investor_access_label,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class MarketVenueRecord:
    """Immutable record naming one synthetic market venue. Storage /
    surface only — never an order book, a quote stream, a match
    engine, a fee schedule, or a clearing path.

    Field semantics
    ---------------
    - ``venue_id`` is the stable id; unique within a
      ``SecurityMarketBook``.
    - ``venue_type_label`` / ``venue_role_label`` / ``status``
      are closed-set labels enforced at construction.
    - ``visibility`` is a free-form generic visibility tag.
    - ``supported_security_type_labels`` is a tuple whose
      entries must each be a closed-set
      ``security_type_label`` value.
    - ``supported_intent_labels`` is a tuple whose entries must
      each be a v1.15 **safe intent label**. The forbidden
      trading verbs (``buy`` / ``sell`` / ``order`` /
      ``target_weight`` / ``overweight`` / ``underweight`` /
      ``execution``) are rejected by closed-set membership —
      this record is a **review-posture aggregator**, never a
      trade-instruction surface.
    - ``metadata`` is free-form.
    """

    venue_id: str
    venue_type_label: str
    venue_role_label: str
    status: str
    visibility: str
    supported_security_type_labels: tuple[str, ...] = field(
        default_factory=tuple
    )
    supported_intent_labels: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "venue_id",
        "venue_type_label",
        "venue_role_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[tuple[tuple[str, frozenset[str]], ...]] = (
        ("venue_type_label", VENUE_TYPE_LABELS),
        ("venue_role_label", VENUE_ROLE_LABELS),
        ("status", VENUE_STATUS_LABELS),
    )

    def __post_init__(self) -> None:
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

        normalized_security_types = _normalize_string_tuple(
            self.supported_security_type_labels,
            field_name="supported_security_type_labels",
        )
        _validate_label_membership(
            normalized_security_types,
            SECURITY_TYPE_LABELS,
            field_name="supported_security_type_labels",
        )
        object.__setattr__(
            self,
            "supported_security_type_labels",
            normalized_security_types,
        )

        normalized_intents = _normalize_string_tuple(
            self.supported_intent_labels,
            field_name="supported_intent_labels",
        )
        _validate_label_membership(
            normalized_intents,
            SAFE_INTENT_LABELS,
            field_name="supported_intent_labels",
        )
        object.__setattr__(
            self, "supported_intent_labels", normalized_intents
        )

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_id": self.venue_id,
            "venue_type_label": self.venue_type_label,
            "venue_role_label": self.venue_role_label,
            "status": self.status,
            "visibility": self.visibility,
            "supported_security_type_labels": list(
                self.supported_security_type_labels
            ),
            "supported_intent_labels": list(self.supported_intent_labels),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class SecurityMarketBook:
    """Append-only storage for v1.15.1 ``ListedSecurityRecord`` and
    ``MarketVenueRecord`` instances. Adding one record emits
    exactly one ledger record (``LISTED_SECURITY_REGISTERED`` or
    ``MARKET_VENUE_REGISTERED``); the book refuses to mutate any
    other source-of-truth book.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _securities: dict[str, ListedSecurityRecord] = field(default_factory=dict)
    _venues: dict[str, MarketVenueRecord] = field(default_factory=dict)

    # --- Listed securities ---------------------------------------------------

    def add_security(
        self, security: ListedSecurityRecord
    ) -> ListedSecurityRecord:
        if security.security_id in self._securities:
            raise DuplicateListedSecurityError(
                f"Duplicate security_id: {security.security_id}"
            )
        self._securities[security.security_id] = security

        if self.ledger is not None:
            self.ledger.append(
                event_type="listed_security_registered",
                simulation_date=self._now(),
                object_id=security.security_id,
                source=security.issuer_firm_id,
                payload={
                    "security_id": security.security_id,
                    "issuer_firm_id": security.issuer_firm_id,
                    "security_type_label": security.security_type_label,
                    "listing_status_label": security.listing_status_label,
                    "primary_market_venue_id": (
                        security.primary_market_venue_id
                    ),
                    "currency_label": security.currency_label,
                    "issue_profile_label": security.issue_profile_label,
                    "liquidity_profile_label": (
                        security.liquidity_profile_label
                    ),
                    "investor_access_label": security.investor_access_label,
                    "status": security.status,
                    "visibility": security.visibility,
                },
                space_id="security_market",
                visibility=security.visibility,
            )
        return security

    def get_security(self, security_id: str) -> ListedSecurityRecord:
        try:
            return self._securities[security_id]
        except KeyError as exc:
            raise UnknownListedSecurityError(
                f"Listed security not found: {security_id!r}"
            ) from exc

    def list_securities(self) -> tuple[ListedSecurityRecord, ...]:
        return tuple(self._securities.values())

    def list_by_issuer(
        self, issuer_firm_id: str
    ) -> tuple[ListedSecurityRecord, ...]:
        return tuple(
            s
            for s in self._securities.values()
            if s.issuer_firm_id == issuer_firm_id
        )

    def list_by_security_type(
        self, security_type_label: str
    ) -> tuple[ListedSecurityRecord, ...]:
        return tuple(
            s
            for s in self._securities.values()
            if s.security_type_label == security_type_label
        )

    def list_by_listing_status(
        self, listing_status_label: str
    ) -> tuple[ListedSecurityRecord, ...]:
        return tuple(
            s
            for s in self._securities.values()
            if s.listing_status_label == listing_status_label
        )

    def list_by_primary_venue(
        self, primary_market_venue_id: str
    ) -> tuple[ListedSecurityRecord, ...]:
        return tuple(
            s
            for s in self._securities.values()
            if s.primary_market_venue_id == primary_market_venue_id
        )

    # --- Market venues -------------------------------------------------------

    def add_venue(self, venue: MarketVenueRecord) -> MarketVenueRecord:
        if venue.venue_id in self._venues:
            raise DuplicateMarketVenueError(
                f"Duplicate venue_id: {venue.venue_id}"
            )
        self._venues[venue.venue_id] = venue

        if self.ledger is not None:
            self.ledger.append(
                event_type="market_venue_registered",
                simulation_date=self._now(),
                object_id=venue.venue_id,
                source=venue.venue_id,
                payload={
                    "venue_id": venue.venue_id,
                    "venue_type_label": venue.venue_type_label,
                    "venue_role_label": venue.venue_role_label,
                    "status": venue.status,
                    "visibility": venue.visibility,
                    "supported_security_type_labels": list(
                        venue.supported_security_type_labels
                    ),
                    "supported_intent_labels": list(
                        venue.supported_intent_labels
                    ),
                },
                space_id="security_market",
                visibility=venue.visibility,
            )
        return venue

    def get_venue(self, venue_id: str) -> MarketVenueRecord:
        try:
            return self._venues[venue_id]
        except KeyError as exc:
            raise UnknownMarketVenueError(
                f"Market venue not found: {venue_id!r}"
            ) from exc

    def list_venues(self) -> tuple[MarketVenueRecord, ...]:
        return tuple(self._venues.values())

    def list_by_venue_type(
        self, venue_type_label: str
    ) -> tuple[MarketVenueRecord, ...]:
        return tuple(
            v
            for v in self._venues.values()
            if v.venue_type_label == venue_type_label
        )

    def list_by_venue_role(
        self, venue_role_label: str
    ) -> tuple[MarketVenueRecord, ...]:
        return tuple(
            v
            for v in self._venues.values()
            if v.venue_role_label == venue_role_label
        )

    def snapshot(self) -> dict[str, Any]:
        securities = sorted(
            (s.to_dict() for s in self._securities.values()),
            key=lambda item: item["security_id"],
        )
        venues = sorted(
            (v.to_dict() for v in self._venues.values()),
            key=lambda item: item["venue_id"],
        )
        return {
            "security_count": len(securities),
            "venue_count": len(venues),
            "securities": securities,
            "venues": venues,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
