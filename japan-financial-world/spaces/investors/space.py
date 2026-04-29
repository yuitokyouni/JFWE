from __future__ import annotations

from dataclasses import dataclass

from spaces.base import BaseSpace
from world.scheduler import Frequency


@dataclass
class InvestorSpace(BaseSpace):
    """
    Empty Investors Space.

    v0.2 scope: declares its frequencies and is invoked by the scheduler.
    No allocation logic, no portfolio optimization, no trading behavior.
    """

    space_id: str = "investors"
    frequencies: tuple[Frequency, ...] = (
        Frequency.DAILY,
        Frequency.MONTHLY,
    )
