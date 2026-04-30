from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spaces.domain import DomainSpace
from spaces.exchange.state import (
    DuplicateListingError,
    DuplicateMarketStateError,
    ListingState,
    MarketState,
)
from world.prices import PriceBook, PriceRecord
from world.scheduler import Frequency


@dataclass
class ExchangeSpace(DomainSpace):
    """
    Exchange Space — minimum internal state for markets and listings.

    v0.11 scope:
        - hold a mapping of market_id -> MarketState (identity-level only)
        - hold listings keyed by (market_id, asset_id) -> ListingState
        - read PriceBook for latest price and price history
        - read SignalBook for visibility-filtered signals
        - log market_state_added and listing_added when those records
          enter the space

    v0.11 explicitly does NOT implement:
        - order matching, order books, or limit-order semantics
        - price formation, last-trade vs mid vs VWAP, or quote logic
        - price impact or market impact estimation
        - trading sessions, opens, closes, auctions, or halts
        - circuit breakers, kill switches, or volatility brakes
        - index construction or rebalancing
        - trade reporting, fee computation, or settlement
        - any mutation of source books or other spaces

    Beyond the common refs supplied by :class:`DomainSpace`,
    ExchangeSpace captures :attr:`prices` so it can answer simple
    price-history queries on listed assets. The DomainSpace accessors
    (:meth:`get_balance_sheet_view`, :meth:`get_constraint_evaluations`,
    :meth:`get_visible_signals`) are inherited unchanged — Exchange
    rarely needs the first two but the inheritance is consistent and
    free.
    """

    space_id: str = "exchange"
    frequencies: tuple[Frequency, ...] = (Frequency.DAILY,)
    prices: PriceBook | None = None
    _markets: dict[str, MarketState] = field(default_factory=dict)
    _listings: dict[tuple[str, str], ListingState] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Lifecycle hook — extends DomainSpace.bind() with prices
    # ------------------------------------------------------------------

    def bind(self, kernel: Any) -> None:
        """Extend DomainSpace.bind() to also capture ``prices``."""
        super().bind(kernel)
        if self.prices is None:
            self.prices = kernel.prices

    # ------------------------------------------------------------------
    # Market state CRUD
    # ------------------------------------------------------------------

    def add_market_state(self, market_state: MarketState) -> MarketState:
        if market_state.market_id in self._markets:
            raise DuplicateMarketStateError(
                f"Duplicate market_id: {market_state.market_id}"
            )
        self._markets[market_state.market_id] = market_state

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="market_state_added",
                simulation_date=simulation_date,
                object_id=market_state.market_id,
                payload={
                    "market_id": market_state.market_id,
                    "market_type": market_state.market_type,
                    "tier": market_state.tier,
                    "status": market_state.status,
                },
                space_id=self.space_id,
            )
        return market_state

    def get_market_state(self, market_id: str) -> MarketState | None:
        return self._markets.get(market_id)

    def list_markets(self) -> tuple[MarketState, ...]:
        """
        Return all registered markets in insertion order.

        Matches v0.8 / v0.9 / v0.10: insertion order is preserved as a
        stable contract for audit-style reads. Use :meth:`snapshot` for
        a deterministic id-keyed ordering.
        """
        return tuple(self._markets.values())

    # ------------------------------------------------------------------
    # Listing CRUD
    # ------------------------------------------------------------------

    def add_listing(self, listing: ListingState) -> ListingState:
        key = (listing.market_id, listing.asset_id)
        if key in self._listings:
            raise DuplicateListingError(
                f"Duplicate listing: market={listing.market_id!r} "
                f"asset={listing.asset_id!r}"
            )
        self._listings[key] = listing

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="listing_added",
                simulation_date=simulation_date,
                object_id=listing.asset_id,
                target=listing.market_id,
                payload={
                    "market_id": listing.market_id,
                    "asset_id": listing.asset_id,
                    "listing_status": listing.listing_status,
                },
                space_id=self.space_id,
            )
        return listing

    def get_listing(
        self,
        market_id: str,
        asset_id: str,
    ) -> ListingState | None:
        return self._listings.get((market_id, asset_id))

    def list_listings(self) -> tuple[ListingState, ...]:
        """Return every listing across every market in insertion order."""
        return tuple(self._listings.values())

    def list_assets_on_market(
        self,
        market_id: str,
    ) -> tuple[ListingState, ...]:
        """
        Return all listings for the given market_id.

        Returns ``ListingState`` records (not bare asset ids) so callers
        can read ``listing_status`` and ``metadata`` without a second
        lookup. To extract just asset ids:
        ``[l.asset_id for l in space.list_assets_on_market(...)]``.
        """
        return tuple(
            listing
            for listing in self._listings.values()
            if listing.market_id == market_id
        )

    # ------------------------------------------------------------------
    # Price-derived views
    # ------------------------------------------------------------------

    def get_latest_price(self, asset_id: str) -> PriceRecord | None:
        """
        Return the most recent PriceRecord for ``asset_id``.

        Returns ``None`` if the asset has no recorded price or if
        :attr:`prices` is unbound. Does not require the asset to be
        listed on any market — price observations and listings are
        independent in v0.11.
        """
        if self.prices is None:
            return None
        return self.prices.get_latest_price(asset_id)

    def get_price_history(
        self,
        asset_id: str,
    ) -> tuple[PriceRecord, ...]:
        """
        Return the chronological PriceRecord history for ``asset_id``.

        Returns ``()`` if the asset has no recorded price or if
        :attr:`prices` is unbound.
        """
        if self.prices is None:
            return ()
        return self.prices.get_price_history(asset_id)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """
        Return a deterministic, JSON-friendly view of the space.

        Markets are sorted by ``market_id``. Listings are sorted by
        ``(market_id, asset_id)``. Both are stable across runs.
        """
        markets = sorted(
            (market.to_dict() for market in self._markets.values()),
            key=lambda item: item["market_id"],
        )
        listings = sorted(
            (listing.to_dict() for listing in self._listings.values()),
            key=lambda item: (item["market_id"], item["asset_id"]),
        )
        return {
            "space_id": self.space_id,
            "market_count": len(markets),
            "listing_count": len(listings),
            "markets": markets,
            "listings": listings,
        }
