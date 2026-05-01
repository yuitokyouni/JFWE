"""
YAML loading for FWE world specs and synthetic example data.

YAML parser policy
------------------

**PyYAML is the supported parser.** The project declares
``pyyaml>=6,<7`` in ``pyproject.toml``'s ``[project] dependencies``
(pinned to the 6.x major series — a future PyYAML 7 must be
evaluated as a deliberate version bump). Any ``pip install -e
".[dev]"`` (or any plain ``pip install -e .``) brings PyYAML in
by default. The reference demo, the v1.8 experiment harness, and
**the full reference demo + experiment config schemas all require
PyYAML**.

A small custom fallback parser (``_load_simple_yaml`` below)
exists only as a defensive minimal fallback for environments where
PyYAML is genuinely unavailable. **The fallback should not be
treated as a full YAML implementation.** It is intentionally
narrow:

- Top-level *lists* of mappings (the v0 ``data/sample/*.yaml``
  shape).
- One level of nested mappings inside list items.
- Scalars, ``null`` / ``true`` / ``false``, and quoted strings.

The fallback **does not** support top-level mappings (e.g., the
``loop:`` block in ``examples/reference_world/entities.yaml``):
top-level keys whose values are mappings are silently misread as
empty lists, which crashes the v1.8 reference demo at runtime.
It also does not support flow-style ``{...}`` / ``[...]`` syntax
beyond the trivial empty cases, anchors / aliases, multi-document
streams, multi-line scalars, or any of the advanced YAML 1.1 / 1.2
features PyYAML covers.

If you find yourself relying on the fallback, the right fix is to
install PyYAML — not to reshape your YAML around the fallback's
limitations and not to extend the fallback. The catalog-shape
regression test in
``tests/test_reference_demo_catalog_shape.py`` exists to fail
loudly when an environment is using the wrong parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from world.registry import RegisteredObject
from world.validation import (
    COLLECTION_KEY_TO_TYPE,
    ValidationIssue,
    infer_object_type,
    validate_registry_object,
)


# PyYAML is the supported parser; see the module docstring above.
# Keep the import guarded so a degraded environment still loads the
# module — the fallback parser will at least handle v0 sample data.
try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class RegistryRecord:
    object_type: str
    object_id: str
    payload: dict[str, Any]
    source_path: str | None = None


@dataclass(frozen=True)
class LoadResult:
    records: list[RegistryRecord]
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


@dataclass(frozen=True)
class WorldSpec:
    objects: list[RegisteredObject]


def load_yaml_file_raw(path: str | Path) -> Any:
    """
    Read a YAML file and return its parsed value.

    Uses PyYAML when available (the supported configuration; see
    module docstring). Falls back to ``_load_simple_yaml`` only if
    PyYAML is missing — that path is degraded and supports only
    the v0 sample-data shape.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    if yaml is not None:
        return yaml.safe_load(text)

    return _load_simple_yaml(text)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return {}
    if value in {"null", "None", "~"}:
        return None
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_simple_yaml(text: str) -> Any:
    """
    Defensive minimal YAML subset loader, used only when PyYAML is
    unavailable. NOT the supported parser — see the module
    docstring.

    Supported shapes (v0 sample-data only):

    - top-level lists of mappings
    - one level of nested mappings inside list items
    - scalars, ``null`` / ``true`` / ``false``, and quoted strings

    Unsupported (silently misread):

    - top-level mappings whose values are mappings
      (e.g. the ``loop:`` block in
      ``examples/reference_world/entities.yaml``)
    - inline flow-style mappings or sequences beyond the trivial
      ``{}`` / ``[]``
    - multi-document YAML

    If a caller hits the unsupported cases, the fix is to install
    PyYAML, not to extend this parser.
    """

    root: dict[str, Any] = {}
    current_list_key: str | None = None
    current_item: dict[str, Any] | None = None
    nested_key: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            if line.endswith(":"):
                current_list_key = line[:-1]
                root[current_list_key] = []
                current_item = None
                nested_key = None
            elif ":" in line:
                key, value = line.split(":", 1)
                root[key.strip()] = _parse_scalar(value)
                current_list_key = None
                current_item = None
                nested_key = None
            continue

        if current_list_key is None:
            continue

        if line.startswith("- "):
            current_item = {}
            root[current_list_key].append(current_item)
            nested_key = None
            body = line[2:]
            if ":" in body:
                key, value = body.split(":", 1)
                current_item[key.strip()] = _parse_scalar(value)
            continue

        if current_item is None or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        if indent == 4 and value.strip() == "":
            current_item[key] = {}
            nested_key = key
        elif indent == 4:
            current_item[key] = _parse_scalar(value)
            nested_key = None
        elif indent >= 6 and nested_key is not None:
            current_item[nested_key][key] = _parse_scalar(value)

    return root


def load_world_yaml(path: str | Path) -> WorldSpec:
    path = Path(path)
    raw = load_yaml_file_raw(path) or {}
    if not isinstance(raw, Mapping):
        raise ValueError("world YAML must be a mapping")

    objects: list[RegisteredObject] = []
    for collection in ("agents", "assets", "markets"):
        items = raw.get(collection, [])
        if items is None:
            continue
        if not isinstance(items, list):
            raise ValueError(f"{collection} must be a list")

        for item in items:
            if not isinstance(item, Mapping):
                raise ValueError(f"{collection} item must be a mapping")
            object_id = item.get("id")
            object_type = item.get("type")
            space = item.get("space")
            if not object_id or not object_type or not space:
                raise ValueError(f"{collection} item requires id, type, and space")
            if ":" not in str(object_id):
                raise ValueError(f"invalid object id: {object_id}")

            attributes = item.get("attributes", {})
            if attributes is None:
                attributes = {}
            if not isinstance(attributes, Mapping):
                raise ValueError(f"attributes must be a mapping for {object_id}")

            objects.append(
                RegisteredObject(
                    id=str(object_id),
                    kind=str(object_id).split(":", 1)[0],
                    type=str(object_type),
                    space=str(space),
                    attributes=dict(attributes),
                )
            )

    return WorldSpec(objects=objects)


def load_yaml_dir_raw(
    dir_path: str | Path,
    *,
    pattern: str = "*.yaml",
    recursive: bool = False,
) -> dict[Path, Any]:
    dir_path = Path(dir_path)

    if not dir_path.exists():
        raise FileNotFoundError(f"YAML directory does not exist: {dir_path}")

    paths = sorted(dir_path.rglob(pattern) if recursive else dir_path.glob(pattern))

    return {
        path: load_yaml_file_raw(path)
        for path in paths
        if path.is_file()
    }


def load_required_fields_from_schemas(
    schemas_dir: str | Path,
) -> dict[str, list[str]]:
    """
    Lightweight schema reader.

    Expected schema shape, if present:

    id: firm
    required:
      - id
      - name

    This function intentionally ignores properties/types.
    """
    schemas_dir = Path(schemas_dir)

    if not schemas_dir.exists():
        raise FileNotFoundError(f"schemas_dir does not exist: {schemas_dir}")

    required_by_type: dict[str, list[str]] = {}

    for path in sorted(schemas_dir.glob("*.yaml")):
        doc = load_yaml_file_raw(path)
        if not isinstance(doc, Mapping):
            continue

        object_type = str(doc.get("id") or path.stem)
        required = doc.get("required")

        if isinstance(required, list):
            required_by_type[object_type] = [str(field) for field in required]

    return required_by_type


def _iter_objects_from_document(
    doc: Any,
    *,
    source_path: str | Path | None = None,
) -> Iterable[tuple[Mapping[str, Any], str | None]]:
    """
    Supported v0 shapes:

    1. Single object:
       id: firm:reference_manufacturer_001
       type: firm
       name: Reference Manufacturer

    2. List of objects:
       - id: firm:a
         type: firm
       - id: firm:b
         type: firm

    3. Collection object:
       firms:
         - id: firm:a
         - id: firm:b
       banks:
         - id: bank:a
    """
    if doc is None:
        return

    if isinstance(doc, list):
        for item in doc:
            if isinstance(item, Mapping):
                yield item, None
        return

    if not isinstance(doc, Mapping):
        return

    # Single object
    if "id" in doc:
        yield doc, None
        return

    # Collection object
    for key, value in doc.items():
        object_type = COLLECTION_KEY_TO_TYPE.get(str(key))
        if object_type is None:
            continue

        if not isinstance(value, list):
            continue

        for item in value:
            if isinstance(item, Mapping):
                yield item, object_type


def convert_to_registry_record(
    obj: Mapping[str, Any],
    *,
    type_hint: str | None = None,
    source_path: str | Path | None = None,
    required_fields_by_type: dict[str, list[str]] | None = None,
) -> tuple[RegistryRecord | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []

    object_type = infer_object_type(
        obj,
        type_hint=type_hint,
        source_path=source_path,
    )

    if object_type is None:
        return None, [
            ValidationIssue(
                severity="error",
                message="Could not infer object type",
                source_path=str(source_path) if source_path is not None else None,
                object_type=None,
                object_id=str(obj.get("id")) if obj.get("id") is not None else None,
            )
        ]

    validation_issues = validate_registry_object(
        obj,
        object_type=object_type,
        required_fields_by_type=required_fields_by_type,
        source_path=source_path,
    )
    issues.extend(validation_issues)

    if any(issue.severity == "error" for issue in issues):
        return None, issues

    object_id = str(obj["id"])

    payload = dict(obj)
    payload.setdefault("type", object_type)

    record = RegistryRecord(
        object_type=object_type,
        object_id=object_id,
        payload=payload,
        source_path=str(source_path) if source_path is not None else None,
    )

    return record, issues


def load_yaml_file(
    path: str | Path,
    *,
    required_fields_by_type: dict[str, list[str]] | None = None,
    collect_errors_without_crashing: bool = True,
) -> LoadResult:
    path = Path(path)
    doc = load_yaml_file_raw(path)

    records: list[RegistryRecord] = []
    issues: list[ValidationIssue] = []

    for obj, type_hint in _iter_objects_from_document(doc, source_path=path):
        record, record_issues = convert_to_registry_record(
            obj,
            type_hint=type_hint,
            source_path=path,
            required_fields_by_type=required_fields_by_type,
        )

        issues.extend(record_issues)

        if record is not None:
            records.append(record)

    if issues and not collect_errors_without_crashing:
        error_messages = "\n".join(issue.message for issue in issues)
        raise ValueError(error_messages)

    return LoadResult(records=records, issues=issues)


def load_yaml_dir(
    dir_path: str | Path,
    *,
    pattern: str = "*.yaml",
    recursive: bool = False,
    required_fields_by_type: dict[str, list[str]] | None = None,
    collect_errors_without_crashing: bool = True,
) -> LoadResult:
    dir_path = Path(dir_path)

    records: list[RegistryRecord] = []
    issues: list[ValidationIssue] = []

    paths = sorted(dir_path.rglob(pattern) if recursive else dir_path.glob(pattern))

    for path in paths:
        if not path.is_file():
            continue

        result = load_yaml_file(
            path,
            required_fields_by_type=required_fields_by_type,
            collect_errors_without_crashing=collect_errors_without_crashing,
        )

        records.extend(result.records)
        issues.extend(result.issues)

    return LoadResult(records=records, issues=issues)
