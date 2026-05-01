from world.validation import (
    infer_object_type,
    validate_required_fields,
    validate_id_prefix,
)


def test_infer_object_type_from_explicit_type():
    obj = {
        "id": "firm:reference_manufacturer_001",
        "type": "firm",
        "name": "Reference Manufacturer",
    }

    assert infer_object_type(obj) == "firm"


def test_infer_object_type_from_id_prefix():
    obj = {
        "id": "bank:megabank_a",
        "name": "Megabank A",
    }

    assert infer_object_type(obj) == "bank"


def test_validate_required_fields_detects_missing_name():
    obj = {
        "id": "firm:reference_manufacturer_001",
    }

    issues = validate_required_fields(
        obj,
        object_type="firm",
        required_fields=["id", "name"],
    )

    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "name" in issues[0].message


def test_validate_id_prefix_warns_on_mismatch():
    obj = {
        "id": "bank:wrong_prefix",
        "name": "Wrong Prefix",
    }

    issues = validate_id_prefix(obj, object_type="firm")

    assert len(issues) == 1
    assert issues[0].severity == "warning"