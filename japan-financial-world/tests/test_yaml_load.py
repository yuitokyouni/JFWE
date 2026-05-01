from world.loader import (
    load_yaml_file,
    load_yaml_dir,
    convert_to_registry_record,
)


def test_load_single_yaml_file(tmp_path):
    path = tmp_path / "firm.yaml"
    path.write_text(
        """
id: firm:reference_manufacturer_001
type: firm
name: Reference Manufacturer
sector: manufacturing
""",
        encoding="utf-8",
    )

    result = load_yaml_file(path)

    assert result.ok
    assert len(result.records) == 1

    record = result.records[0]
    assert record.object_type == "firm"
    assert record.object_id == "firm:reference_manufacturer_001"
    assert record.payload["name"] == "Reference Manufacturer"


def test_load_collection_yaml_file(tmp_path):
    path = tmp_path / "firms.yaml"
    path.write_text(
        """
firms:
  - id: firm:a
    name: Firm A
  - id: firm:b
    name: Firm B
""",
        encoding="utf-8",
    )

    result = load_yaml_file(path)

    assert result.ok
    assert len(result.records) == 2
    assert result.records[0].object_type == "firm"
    assert result.records[1].object_id == "firm:b"


def test_load_yaml_dir(tmp_path):
    firms = tmp_path / "firms.yaml"
    banks = tmp_path / "banks.yaml"

    firms.write_text(
        """
firms:
  - id: firm:a
    name: Firm A
""",
        encoding="utf-8",
    )

    banks.write_text(
        """
banks:
  - id: bank:a
    name: Bank A
""",
        encoding="utf-8",
    )

    result = load_yaml_dir(tmp_path)

    assert result.ok
    assert len(result.records) == 2

    object_types = {record.object_type for record in result.records}
    assert object_types == {"firm", "bank"}


def test_missing_required_field_is_collected(tmp_path):
    path = tmp_path / "firms.yaml"
    path.write_text(
        """
firms:
  - id: firm:a
""",
        encoding="utf-8",
    )

    result = load_yaml_file(
        path,
        required_fields_by_type={"firm": ["id", "name"]},
    )

    assert not result.ok
    assert len(result.errors) == 1
    assert result.errors[0].message == "Missing required field: name"


def test_convert_to_registry_record():
    obj = {
        "id": "investor:foreign_macro_fund_001",
        "name": "Foreign Macro Fund 001",
    }

    record, issues = convert_to_registry_record(obj)

    assert not issues
    assert record is not None
    assert record.object_type == "investor"
    assert record.object_id == "investor:foreign_macro_fund_001"
    assert record.payload["type"] == "investor"