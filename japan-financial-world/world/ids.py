from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Final


class InvalidWorldID(ValueError):
    """Raised when a world ID is malformed or uses an unsupported kind."""


ID_SEPARATOR: Final[str] = ":"

ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<kind>[a-z][a-z0-9_]*):(?P<key>[a-z0-9][a-z0-9_]*)$"
)

AGENT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "agent",
        "firm",
        "bank",
        "investor",
    }
)

ENTITY_KINDS: Final[frozenset[str]] = frozenset(
    {
        "asset",
        "contract",
        "market",
        "signal",
        "price",
        "space",
    }
)

ALLOWED_WORLD_ID_KINDS: Final[frozenset[str]] = AGENT_KINDS | ENTITY_KINDS


@dataclass(frozen=True, slots=True)
class WorldID:
    """
    Stable unique ID for every object in the simulated world.

    Format:
        kind:key

    Examples:
        firm:reference_manufacturer_001
        asset:equity_reference_manufacturer_001
        contract:loan_000001
        price:equity_reference_manufacturer_001_2026_04_29
    """

    raw: str
    kind: str = field(init=False)
    key: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.raw, str):
            raise InvalidWorldID(f"WorldID must be a string, got {type(self.raw)!r}")

        match = ID_PATTERN.fullmatch(self.raw)
        if match is None:
            raise InvalidWorldID(
                f"Invalid WorldID format: {self.raw!r}. "
                "Expected format is 'kind:key' using lowercase snake_case."
            )

        kind = match.group("kind")
        key = match.group("key")

        if kind not in ALLOWED_WORLD_ID_KINDS:
            raise InvalidWorldID(
                f"Unsupported WorldID kind: {kind!r}. "
                f"Allowed kinds are: {sorted(ALLOWED_WORLD_ID_KINDS)}"
            )

        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "key", key)

    def __str__(self) -> str:
        return self.raw

    def is_agent(self) -> bool:
        return self.kind in AGENT_KINDS


def parse_world_id(value: str | WorldID) -> WorldID:
    if isinstance(value, WorldID):
        return value
    return WorldID(value)


def build_world_id(kind: str, key: str) -> WorldID:
    return WorldID(f"{kind}{ID_SEPARATOR}{key}")


def category_for_kind(kind: str) -> str:
    """
    Convert a concrete ID kind into a broader registry category.

    firm / bank / investor -> agent
    asset -> asset
    contract -> contract
    etc.
    """
    if kind in AGENT_KINDS:
        return "agent"

    if kind in ENTITY_KINDS:
        return kind

    raise InvalidWorldID(f"Unsupported WorldID kind: {kind!r}")
