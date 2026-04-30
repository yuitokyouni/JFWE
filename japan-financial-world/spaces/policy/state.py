from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class PolicyStateError(Exception):
    """Base class for policy-space state errors."""


class DuplicatePolicyAuthorityStateError(PolicyStateError):
    """Raised when an authority_id is added twice."""


class DuplicatePolicyInstrumentStateError(PolicyStateError):
    """Raised when an instrument_id is added twice."""


@dataclass(frozen=True)
class PolicyAuthorityState:
    """
    Identity-level record for a policy-making authority.

    A policy authority is *who has the legal mandate to set policy*: a
    central bank, a financial regulator, a treasury / finance ministry,
    a securities commission, a deposit insurance corporation. v0.14
    stores classification only — which authority, what type, what
    tier, what status. It does NOT store reaction functions, target
    rates, mandates, voting members, or independence indices.

    The intent is to give PolicySpace just enough native classification
    to organize policy authorities without introducing reaction logic
    or rate-setting behavior. Reasoning about *what an authority will
    do* is deferred. Right now we only record *that the authority
    exists*.
    """

    authority_id: str
    authority_type: str = "unspecified"
    tier: str = "unspecified"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.authority_id:
            raise ValueError("authority_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "authority_type": self.authority_type,
            "tier": self.tier,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class PolicyInstrumentState:
    """
    Identity-level record for a policy instrument.

    A policy instrument is *what an authority can use to act on the
    economy*: a policy rate, a reserve requirement, an open-market
    operation framework, a regulatory capital ratio, a deposit
    insurance ceiling. Each instrument is associated with one
    authority via a foreign key (``authority_id``); v0.14 does not
    validate that the referenced authority is registered.

    What this record does NOT carry: current rate level, target,
    transmission lag, effectiveness estimate, or any time-series of
    past values. v0.14 does not implement policy behavior — those
    fields would be the foundation of reaction-function modeling and
    are deferred.
    """

    instrument_id: str
    authority_id: str
    instrument_type: str = "unspecified"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.instrument_id:
            raise ValueError("instrument_id is required")
        if not self.authority_id:
            raise ValueError("authority_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_id": self.instrument_id,
            "authority_id": self.authority_id,
            "instrument_type": self.instrument_type,
            "status": self.status,
            "metadata": dict(self.metadata),
        }
