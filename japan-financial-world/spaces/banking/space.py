from __future__ import annotations

from dataclasses import dataclass

from spaces.base import BaseSpace
from world.scheduler import Frequency


@dataclass
class BankSpace(BaseSpace):
    """
    Empty Banking Space.

    v0.2 scope: declares its frequencies and is invoked by the scheduler.
    No credit analysis, no lending logic, no covenant evaluation.
    """

    space_id: str = "banking"
    frequencies: tuple[Frequency, ...] = (
        Frequency.DAILY,
        Frequency.QUARTERLY,
    )
