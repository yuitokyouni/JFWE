from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spaces.domain import DomainSpace
from spaces.external.state import (
    DuplicateExternalFactorStateError,
    DuplicateExternalSourceStateError,
    ExternalFactorState,
    ExternalSourceState,
)
from world.scheduler import Frequency


@dataclass
class ExternalSpace(DomainSpace):
    """
    External Space — minimum internal state for external factors and
    external data sources.

    v0.14 scope:
        - hold a mapping of factor_id -> ExternalFactorState
          (what exogenous things the world tracks)
        - hold a mapping of source_id -> ExternalSourceState
          (where exogenous data comes from)
        - read SignalBook for visibility-filtered signals (e.g., to
          observe macro announcements, policy rate decisions from
          foreign central banks) via the inherited DomainSpace
          accessor
        - log external_factor_state_added and
          external_source_state_added when those records enter the
          space

    v0.14 explicitly does NOT implement:
        - external shock generation (oil shocks, FX shocks, war,
          natural disaster, pandemic)
        - random walks, regime switching, or any stochastic process
        - historical replay of past external data
        - factor value updates or time-series progression
        - shock impact on prices, ownership, or contracts
        - any mutation of source books or other spaces
        - scenario logic

    ExternalSpace inherits :class:`DomainSpace` and requires no
    domain-specific kernel ref of its own. The inherited ``signals``
    and ``registry`` are sufficient. There is no ``bind()`` override.

    Note on factors vs sources
    --------------------------
    Factors and sources are *independent* maps in v0.14: a factor
    does not declare which source provides its data, and a source
    does not declare which factors it produces. Real-world
    relationships are many-to-many (one source produces many
    factors; one factor can be observed from many sources) and v0.14
    does not pick a representation. Future milestones may introduce
    a relation map similar to v0.11 listings if the cross-reference
    becomes load-bearing.
    """

    space_id: str = "external"
    frequencies: tuple[Frequency, ...] = (Frequency.DAILY,)
    _factors: dict[str, ExternalFactorState] = field(default_factory=dict)
    _sources: dict[str, ExternalSourceState] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factor CRUD
    # ------------------------------------------------------------------

    def add_factor_state(
        self,
        factor_state: ExternalFactorState,
    ) -> ExternalFactorState:
        if factor_state.factor_id in self._factors:
            raise DuplicateExternalFactorStateError(
                f"Duplicate factor_id: {factor_state.factor_id}"
            )
        self._factors[factor_state.factor_id] = factor_state

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="external_factor_state_added",
                simulation_date=simulation_date,
                object_id=factor_state.factor_id,
                payload={
                    "factor_id": factor_state.factor_id,
                    "factor_type": factor_state.factor_type,
                    "unit": factor_state.unit,
                    "status": factor_state.status,
                },
                space_id=self.space_id,
            )
        return factor_state

    def get_factor_state(self, factor_id: str) -> ExternalFactorState | None:
        return self._factors.get(factor_id)

    def list_factors(self) -> tuple[ExternalFactorState, ...]:
        """Return all registered external factors in insertion order."""
        return tuple(self._factors.values())

    # ------------------------------------------------------------------
    # Source CRUD
    # ------------------------------------------------------------------

    def add_source_state(
        self,
        source_state: ExternalSourceState,
    ) -> ExternalSourceState:
        if source_state.source_id in self._sources:
            raise DuplicateExternalSourceStateError(
                f"Duplicate source_id: {source_state.source_id}"
            )
        self._sources[source_state.source_id] = source_state

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="external_source_state_added",
                simulation_date=simulation_date,
                object_id=source_state.source_id,
                payload={
                    "source_id": source_state.source_id,
                    "source_type": source_state.source_type,
                    "status": source_state.status,
                },
                space_id=self.space_id,
            )
        return source_state

    def get_source_state(self, source_id: str) -> ExternalSourceState | None:
        return self._sources.get(source_id)

    def list_sources(self) -> tuple[ExternalSourceState, ...]:
        """Return all registered external sources in insertion order."""
        return tuple(self._sources.values())

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """
        Return a deterministic, JSON-friendly view of the space.

        Factors are sorted by ``factor_id``. Sources are sorted by
        ``source_id``. Both are stable across runs.
        """
        factors = sorted(
            (factor.to_dict() for factor in self._factors.values()),
            key=lambda item: item["factor_id"],
        )
        sources = sorted(
            (source.to_dict() for source in self._sources.values()),
            key=lambda item: item["source_id"],
        )
        return {
            "space_id": self.space_id,
            "factor_count": len(factors),
            "source_count": len(sources),
            "factors": factors,
            "sources": sources,
        }
