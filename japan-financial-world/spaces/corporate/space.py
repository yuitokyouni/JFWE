from __future__ import annotations

from dataclasses import dataclass

from spaces.base import BaseSpace
from world.scheduler import Frequency


@dataclass
class CorporateSpace(BaseSpace):
    """
    Empty Corporate Space.

    v0.2 scope: declares its frequencies and is invoked by the scheduler.
    No firm decision logic, no balance sheet logic, no accounting engine.
    """

    space_id: str = "corporate"
    frequencies: tuple[Frequency, ...] = (
        Frequency.MONTHLY,
        Frequency.QUARTERLY,
        Frequency.YEARLY,
    )
