"""Multi-scale simulation clock."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Clock:
    t_day: int = 0

    @property
    def t_month(self) -> int:
        return self.t_day // 21

    @property
    def t_quarter(self) -> int:
        return self.t_day // 63

    @property
    def t_year(self) -> int:
        return self.t_day // 252

    def advance_day(self, days: int = 1) -> None:
        if days < 1:
            raise ValueError("days must be positive")
        self.t_day += days

    def is_month_start(self) -> bool:
        return self.t_day % 21 == 0

    def is_quarter_start(self) -> bool:
        return self.t_day % 63 == 0

    def is_year_start(self) -> bool:
        return self.t_day % 252 == 0
