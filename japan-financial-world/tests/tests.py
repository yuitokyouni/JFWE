import pytest

from world.ids import (
    InvalidWorldID,
    WorldID,
    build_world_id,
    category_for_kind,
)


def test_world_id_parses_valid_id() -> None:
    world_id = WorldID("firm:reference_manufacturer_001")

    assert str(world_id) == "firm:reference_manufacturer_001"
    assert world_id.kind == "firm"
    assert world_id.key == "reference_manufacturer_like_001"
    assert world_id.is_agent() is True


def test_build_world_id() -> None:
    world_id = build_world_id("asset", "equity_reference_manufacturer_001")

    assert str(world_id) == "asset:equity_reference_manufacturer_001"
    assert world_id.kind == "asset"
    assert world_id.key == "equity_reference_manufacturer_001"


@pytest.mark.parametrize(
    "bad_id",
    [
        "",
        "firm",
        "firm:",
        ":toyota",
        "Firm:toyota",
        "firm:the reference manufacturer",
        "unknown:thing_001",
        "asset:equity-toyota",
        "asset:equity toyota",
    ],
)
def test_world_id_rejects_invalid_ids(bad_id: str) -> None:
    with pytest.raises(InvalidWorldID):
        WorldID(bad_id)


def test_category_for_kind() -> None:
    assert category_for_kind("firm") == "agent"
    assert category_for_kind("bank") == "agent"
    assert category_for_kind("investor") == "agent"
    assert category_for_kind("asset") == "asset"
    assert category_for_kind("contract") == "contract"