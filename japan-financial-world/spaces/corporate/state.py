from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class CorporateStateError(Exception):
    """Base class for corporate-space state errors."""


class DuplicateFirmStateError(CorporateStateError):
    """Raised when a firm_id is added twice."""


@dataclass(frozen=True)
class FirmState:
    """
    Minimal internal record CorporateSpace keeps about a firm.

    A FirmState stores identity-level facts only: which firm, what sector
    it belongs to, what tier it occupies, and what status it is currently
    in. v0.8 deliberately leaves out everything else — revenue, profit,
    cash position, leverage, asset base — because those are derivable
    from the world's books (ownership, contracts, prices, balance sheet
    projections). Storing them inside the space would create two sources
    of truth.

    The intent of FirmState is to give CorporateSpace just enough native
    classification to organize firms (e.g., for filtering by sector or
    tier when selecting which firms to read views for) without
    introducing economic behavior.
    """

    firm_id: str
    sector: str = "unspecified"
    tier: str = "unspecified"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.firm_id:
            raise ValueError("firm_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "firm_id": self.firm_id,
            "sector": self.sector,
            "tier": self.tier,
            "status": self.status,
            "metadata": dict(self.metadata),
        }
