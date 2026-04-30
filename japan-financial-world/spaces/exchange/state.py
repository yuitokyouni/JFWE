from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class ExchangeStateError(Exception):
    """Base class for exchange-space state errors."""


class DuplicateMarketStateError(ExchangeStateError):
    """Raised when a market_id is added twice."""


class DuplicateListingError(ExchangeStateError):
    """Raised when a (market_id, asset_id) listing is added twice."""


@dataclass(frozen=True)
class MarketState:
    """
    Minimal internal record ExchangeSpace keeps about a market.

    Mirrors FirmState (§27) / BankState (§28) / InvestorState (§29):
    identity-level facts only. v0.11 deliberately leaves out everything
    else — trading hours, lot size, tick size, settlement cycle, halt
    status, index membership, fee schedule — because those would be the
    foundation of trading behavior, and v0.11 does not implement
    trading.

    The intent is to give ExchangeSpace just enough native classification
    to organize markets (e.g., "this is the equity market", "this is the
    JGB market") without introducing market microstructure.
    """

    market_id: str
    market_type: str = "unspecified"
    tier: str = "unspecified"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.market_id:
            raise ValueError("market_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_id": self.market_id,
            "market_type": self.market_type,
            "tier": self.tier,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ListingState:
    """
    Listing relationship between a market and an asset.

    A ListingState declares "asset X is listed on market Y with status
    Z". It is identity-level; it carries no quote, no last trade, no
    order book, no halt window.

    v0.11 does not enumerate ``listing_status`` values — common labels
    might include ``"listed"``, ``"delisted"``, ``"suspended"``,
    ``"pre_listing"``, but the field is a free-form string. Any
    interpretation of these labels is a domain decision deferred to
    later milestones.
    """

    market_id: str
    asset_id: str
    listing_status: str = "listed"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.market_id:
            raise ValueError("market_id is required")
        if not self.asset_id:
            raise ValueError("asset_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_id": self.market_id,
            "asset_id": self.asset_id,
            "listing_status": self.listing_status,
            "metadata": dict(self.metadata),
        }
