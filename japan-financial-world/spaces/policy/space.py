from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spaces.domain import DomainSpace
from spaces.policy.state import (
    DuplicatePolicyAuthorityStateError,
    DuplicatePolicyInstrumentStateError,
    PolicyAuthorityState,
    PolicyInstrumentState,
)
from world.scheduler import Frequency


@dataclass
class PolicySpace(DomainSpace):
    """
    Policy Space — minimum internal state for policy authorities and
    instruments.

    v0.14 scope:
        - hold a mapping of authority_id -> PolicyAuthorityState
        - hold a mapping of instrument_id -> PolicyInstrumentState
          (each instrument declares the authority_id it belongs to)
        - read SignalBook for visibility-filtered signals (e.g., to
          observe regulatory announcements, policy statements) via the
          inherited DomainSpace accessor
        - log policy_authority_state_added and
          policy_instrument_state_added when those records enter the
          space

    v0.14 explicitly does NOT implement:
        - policy rate decisions, target setting, or policy guidance
        - reaction functions (Taylor rules, Brainard rules,
          inflation-targeting rules)
        - liquidity operations, open-market operations, or balance-
          sheet expansion / contraction
        - regulatory rule changes (capital ratios, leverage caps,
          deposit insurance ceiling)
        - constraint mutation in ConstraintBook
        - any mutation of source books or other spaces
        - scenario logic

    PolicySpace inherits :class:`DomainSpace` and requires no
    domain-specific kernel ref of its own. The inherited ``signals``
    and ``registry`` are sufficient. There is no ``bind()`` override.
    """

    space_id: str = "policy"
    frequencies: tuple[Frequency, ...] = (Frequency.MONTHLY,)
    _authorities: dict[str, PolicyAuthorityState] = field(default_factory=dict)
    _instruments: dict[str, PolicyInstrumentState] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Authority CRUD
    # ------------------------------------------------------------------

    def add_authority_state(
        self,
        authority_state: PolicyAuthorityState,
    ) -> PolicyAuthorityState:
        if authority_state.authority_id in self._authorities:
            raise DuplicatePolicyAuthorityStateError(
                f"Duplicate authority_id: {authority_state.authority_id}"
            )
        self._authorities[authority_state.authority_id] = authority_state

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="policy_authority_state_added",
                simulation_date=simulation_date,
                object_id=authority_state.authority_id,
                payload={
                    "authority_id": authority_state.authority_id,
                    "authority_type": authority_state.authority_type,
                    "tier": authority_state.tier,
                    "status": authority_state.status,
                },
                space_id=self.space_id,
            )
        return authority_state

    def get_authority_state(
        self,
        authority_id: str,
    ) -> PolicyAuthorityState | None:
        return self._authorities.get(authority_id)

    def list_authorities(self) -> tuple[PolicyAuthorityState, ...]:
        """Return all registered policy authorities in insertion order."""
        return tuple(self._authorities.values())

    # ------------------------------------------------------------------
    # Instrument CRUD
    # ------------------------------------------------------------------

    def add_instrument_state(
        self,
        instrument_state: PolicyInstrumentState,
    ) -> PolicyInstrumentState:
        if instrument_state.instrument_id in self._instruments:
            raise DuplicatePolicyInstrumentStateError(
                f"Duplicate instrument_id: {instrument_state.instrument_id}"
            )
        self._instruments[instrument_state.instrument_id] = instrument_state

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="policy_instrument_state_added",
                simulation_date=simulation_date,
                object_id=instrument_state.instrument_id,
                target=instrument_state.authority_id,
                payload={
                    "instrument_id": instrument_state.instrument_id,
                    "authority_id": instrument_state.authority_id,
                    "instrument_type": instrument_state.instrument_type,
                    "status": instrument_state.status,
                },
                space_id=self.space_id,
            )
        return instrument_state

    def get_instrument_state(
        self,
        instrument_id: str,
    ) -> PolicyInstrumentState | None:
        return self._instruments.get(instrument_id)

    def list_instruments(self) -> tuple[PolicyInstrumentState, ...]:
        """Return all registered policy instruments in insertion order."""
        return tuple(self._instruments.values())

    def list_instruments_by_authority(
        self,
        authority_id: str,
    ) -> tuple[PolicyInstrumentState, ...]:
        """
        Return every instrument declared to belong to the given authority.

        v0.14 does not validate that ``authority_id`` itself is
        registered; an instrument may reference an authority that has
        not been added.
        """
        return tuple(
            instrument
            for instrument in self._instruments.values()
            if instrument.authority_id == authority_id
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """
        Return a deterministic, JSON-friendly view of the space.

        Authorities are sorted by ``authority_id``. Instruments are
        sorted by ``instrument_id``. Both are stable across runs.
        """
        authorities = sorted(
            (auth.to_dict() for auth in self._authorities.values()),
            key=lambda item: item["authority_id"],
        )
        instruments = sorted(
            (inst.to_dict() for inst in self._instruments.values()),
            key=lambda item: item["instrument_id"],
        )
        return {
            "space_id": self.space_id,
            "authority_count": len(authorities),
            "instrument_count": len(instruments),
            "authorities": authorities,
            "instruments": instruments,
        }
