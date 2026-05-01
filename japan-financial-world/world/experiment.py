"""
v1.8 Experiment Harness — config-driven driver for the FWE Reference Demo.

This module turns the FWE Reference Demo from a script-driven artifact
into a config-driven, reproducible experiment. It does **not** add new
simulation behavior. It loads a YAML config, validates it against a
small synthetic-only schema, calls the existing
``examples/reference_world/run_reference_loop.py`` to produce the
ledger trace, computes the replay digest, and writes a manifest.

Scope discipline (v1.8):

- The harness drives **only** the existing reference demo. Custom
  entities files, custom start dates, custom day counts, and the
  intraday-phase execution mode are documented in the schema but
  raise ``NotImplementedError`` at runtime — those are wiring
  points for future v1.8.x milestones.
- The optional config sections (``external_observations``,
  ``signal_templates``, ``valuation_templates``,
  ``institutional_actions``, ``event_delivery_targets``) are
  parsed and stored on the config object so they are visible in
  the manifest, but they do not yet drive alternate behavior.
- Synthetic-only guard: a config that contains any real-firm or
  jurisdiction-specific token (toyota, mufg, smbc, mizuho, boj,
  fsa, jpx, gpif, tse, nikkei, topix, sony, jgb, nyse) is rejected
  before any code runs. v2 (Japan public calibration) will use a
  separate, documented schema with a license-aware vocabulary;
  this guard keeps the v1.8 surface jurisdiction-neutral.

The harness produces:

- An ``ExperimentResult`` with ``kernel``, ``summary``,
  ``ledger_digest``, and the paths of any manifest / digest files
  written.
- ``{output_dir}/manifest.json`` (deterministic JSON, atomic
  rename) when ``manifest_enabled`` is true.
- ``{output_dir}/ledger_digest.txt`` (the sha256 hex digest plus a
  single trailing newline) when ``replay_digest_enabled`` is true.

The harness reads only from the kernel and writes only to
``output_dir``. It does not touch the ledger or any v0 / v1 book.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from world.loader import load_yaml_file_raw


__all__ = (
    "ExperimentConfig",
    "ExperimentConfigError",
    "ExperimentResult",
    "load_experiment_config",
    "validate_experiment_config",
    "run_reference_experiment",
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


CONFIG_SCHEMA_VERSION: str = "fwe_experiment_config.v1"

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The bundled demo's defaults. The v1.8 harness only supports configs
# that match these. Different values are accepted in the schema but
# raise NotImplementedError at run time so future v1.8.x milestones
# can wire each parameter without breaking v1.8 callers.
_DEMO_DIR = _REPO_ROOT / "examples" / "reference_world"
_DEMO_DEFAULT_ENTITIES_PATH: Path = _DEMO_DIR / "entities.yaml"
_DEMO_DEFAULT_START_DATE: str = "2026-01-01"
_DEMO_DEFAULT_DAYS: int = 2
_DEMO_DEFAULT_EXECUTION_MODE: str = "date_tick"

_VALID_EXECUTION_MODES: frozenset[str] = frozenset(
    {"date_tick", "intraday_phase"}
)

# Synthetic-only guard. Real-firm / jurisdiction-specific tokens are
# forbidden in any string value of the config. v2 (Japan public
# calibration) introduces a separate schema with explicit per-source
# license metadata; this list keeps the v1.8 surface neutral.
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
)

# Required field names. All eight must appear in the config.
_REQUIRED_FIELDS: tuple[str, ...] = (
    "run_id",
    "run_label",
    "start_date",
    "days",
    "execution_mode",
    "input_entities_path",
    "output_dir",
    "manifest_enabled",
    "replay_digest_enabled",
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ExperimentConfigError(ValueError):
    """Raised when a config fails validation. Subclass of ValueError."""


# ---------------------------------------------------------------------------
# Config + Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentConfig:
    """
    Validated experiment config for the v1.8 reference-demo harness.

    Required fields mirror the user-facing schema in
    ``examples/reference_world/configs/base.yaml``. Optional sections
    are stored as plain mappings/lists so they round-trip through
    JSON / YAML; v1.8 does not interpret them.
    """

    # Required
    run_id: str
    run_label: str
    start_date: str
    days: int
    execution_mode: str
    input_entities_path: str
    output_dir: str
    manifest_enabled: bool
    replay_digest_enabled: bool

    # Optional sections (default-empty; documented schema for v1.8.x).
    external_observations: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    signal_templates: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    valuation_templates: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    institutional_actions: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    event_delivery_targets: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict view suitable for the manifest payload."""
        return {
            "run_id": self.run_id,
            "run_label": self.run_label,
            "start_date": self.start_date,
            "days": self.days,
            "execution_mode": self.execution_mode,
            "input_entities_path": self.input_entities_path,
            "output_dir": self.output_dir,
            "manifest_enabled": self.manifest_enabled,
            "replay_digest_enabled": self.replay_digest_enabled,
            "external_observations": [dict(x) for x in self.external_observations],
            "signal_templates": [dict(x) for x in self.signal_templates],
            "valuation_templates": [dict(x) for x in self.valuation_templates],
            "institutional_actions": [dict(x) for x in self.institutional_actions],
            "event_delivery_targets": [dict(x) for x in self.event_delivery_targets],
        }


@dataclass
class ExperimentResult:
    """
    Result of ``run_reference_experiment``. Carries the populated
    kernel, the demo summary, the replay digest (if enabled), and the
    paths of any artifacts written to ``output_dir``.
    """

    config: ExperimentConfig
    kernel: Any
    summary: Any
    ledger_digest: str | None
    manifest_path: Path | None
    digest_path: Path | None


# ---------------------------------------------------------------------------
# Loader + validator
# ---------------------------------------------------------------------------


def _coerce_list_of_mappings(
    value: Any, field_name: str
) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ExperimentConfigError(
            f"config field {field_name!r} must be a list of mappings; "
            f"got {type(value).__name__}"
        )
    out: list[Mapping[str, Any]] = []
    for i, entry in enumerate(value):
        if not isinstance(entry, Mapping):
            raise ExperimentConfigError(
                f"config field {field_name!r}[{i}] must be a mapping; "
                f"got {type(entry).__name__}"
            )
        out.append(dict(entry))
    return tuple(out)


def _check_synthetic_only(value: Any, *, path: str = "config") -> None:
    """
    Walk every string in ``value`` and raise if any forbidden token
    appears (case-insensitive substring match).
    """
    if isinstance(value, str):
        lowered = value.lower()
        for token in _FORBIDDEN_TOKENS:
            if token in lowered:
                raise ExperimentConfigError(
                    f"forbidden token {token!r} found in {path}: {value!r}. "
                    "v1.8 experiment configs must be jurisdiction-neutral; "
                    "see docs/naming_policy.md."
                )
    elif isinstance(value, Mapping):
        for k, v in value.items():
            _check_synthetic_only(k, path=f"{path}.{k}")
            _check_synthetic_only(v, path=f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _check_synthetic_only(v, path=f"{path}[{i}]")


def load_experiment_config(path: Path | str) -> ExperimentConfig:
    """
    Load and validate an experiment config from ``path``.

    Raises ``ExperimentConfigError`` (a subclass of ``ValueError``)
    on a missing file, malformed YAML, missing required fields,
    type errors, or synthetic-only-guard failures.
    """
    p = Path(path)
    if not p.is_file():
        raise ExperimentConfigError(
            f"experiment config file not found: {p}"
        )

    raw = load_yaml_file_raw(p)
    if not isinstance(raw, Mapping):
        raise ExperimentConfigError(
            f"experiment config root must be a mapping; got "
            f"{type(raw).__name__}"
        )

    return _config_from_mapping(dict(raw))


def _config_from_mapping(raw: Mapping[str, Any]) -> ExperimentConfig:
    # Synthetic-only guard runs first so a malicious or accidentally
    # mis-named config is rejected before any field-shape work.
    _check_synthetic_only(dict(raw))

    missing = [f for f in _REQUIRED_FIELDS if f not in raw]
    if missing:
        raise ExperimentConfigError(
            f"experiment config is missing required field(s): "
            f"{sorted(missing)}"
        )

    # Type coercion + checks for the required scalars.
    def _str_field(name: str) -> str:
        v = raw[name]
        if not isinstance(v, str) or not v.strip():
            raise ExperimentConfigError(
                f"{name!r} must be a non-empty string; got {v!r}"
            )
        return v

    def _bool_field(name: str) -> bool:
        v = raw[name]
        if not isinstance(v, bool):
            raise ExperimentConfigError(
                f"{name!r} must be a bool; got {type(v).__name__}"
            )
        return v

    days_raw = raw["days"]
    if not isinstance(days_raw, int) or isinstance(days_raw, bool):
        raise ExperimentConfigError(
            f"'days' must be an int; got {type(days_raw).__name__}"
        )
    if days_raw < 1:
        raise ExperimentConfigError(
            f"'days' must be >= 1; got {days_raw}"
        )

    execution_mode = _str_field("execution_mode")
    if execution_mode not in _VALID_EXECUTION_MODES:
        raise ExperimentConfigError(
            f"'execution_mode' must be one of "
            f"{sorted(_VALID_EXECUTION_MODES)}; got {execution_mode!r}"
        )

    config = ExperimentConfig(
        run_id=_str_field("run_id"),
        run_label=_str_field("run_label"),
        start_date=_str_field("start_date"),
        days=days_raw,
        execution_mode=execution_mode,
        input_entities_path=_str_field("input_entities_path"),
        output_dir=_str_field("output_dir"),
        manifest_enabled=_bool_field("manifest_enabled"),
        replay_digest_enabled=_bool_field("replay_digest_enabled"),
        external_observations=_coerce_list_of_mappings(
            raw.get("external_observations"), "external_observations"
        ),
        signal_templates=_coerce_list_of_mappings(
            raw.get("signal_templates"), "signal_templates"
        ),
        valuation_templates=_coerce_list_of_mappings(
            raw.get("valuation_templates"), "valuation_templates"
        ),
        institutional_actions=_coerce_list_of_mappings(
            raw.get("institutional_actions"), "institutional_actions"
        ),
        event_delivery_targets=_coerce_list_of_mappings(
            raw.get("event_delivery_targets"), "event_delivery_targets"
        ),
    )

    # Validate start_date format. Accept YYYY-MM-DD only.
    try:
        date.fromisoformat(config.start_date)
    except ValueError as exc:
        raise ExperimentConfigError(
            f"'start_date' must be ISO YYYY-MM-DD; got "
            f"{config.start_date!r}"
        ) from exc

    return config


def validate_experiment_config(config: ExperimentConfig) -> None:
    """
    Re-validate a constructed config. ``load_experiment_config``
    already runs this; the function is exposed so callers that
    construct configs in code (tests, downstream tooling) can reuse
    the same checks.

    Raises ``ExperimentConfigError`` on any violation.
    """
    if not isinstance(config, ExperimentConfig):
        raise ExperimentConfigError(
            f"validate_experiment_config expected ExperimentConfig; "
            f"got {type(config).__name__}"
        )

    # Re-run the synthetic-only guard on the round-tripped dict so a
    # config built in code is held to the same standard as one loaded
    # from YAML.
    _check_synthetic_only(config.to_dict())

    if config.execution_mode not in _VALID_EXECUTION_MODES:
        raise ExperimentConfigError(
            f"'execution_mode' must be one of "
            f"{sorted(_VALID_EXECUTION_MODES)}; got "
            f"{config.execution_mode!r}"
        )
    if config.days < 1:
        raise ExperimentConfigError(
            f"'days' must be >= 1; got {config.days}"
        )
    try:
        date.fromisoformat(config.start_date)
    except ValueError as exc:
        raise ExperimentConfigError(
            f"'start_date' must be ISO YYYY-MM-DD; got "
            f"{config.start_date!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _resolve_path(value: str) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = (_REPO_ROOT / p).resolve()
    return p


def _load_demo_module() -> Any:
    """
    Load examples/reference_world/run_reference_loop.py without
    requiring examples/ to be a Python package. Re-uses an already-
    loaded copy if one is in sys.modules.
    """
    for candidate in (
        "fwe_reference_demo_run",
        "demo_run",
        "fwe_demo_run_for_manifest",
    ):
        module = sys.modules.get(candidate)
        if module is not None and hasattr(module, "run"):
            return module

    sibling = _DEMO_DIR / "run_reference_loop.py"
    spec = importlib.util.spec_from_file_location(
        "fwe_reference_demo_run", sibling
    )
    if spec is None or spec.loader is None:
        raise ExperimentConfigError(
            f"could not load demo runner at {sibling}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["fwe_reference_demo_run"] = module
    spec.loader.exec_module(module)
    return module


def _load_replay_utils() -> Any:
    for candidate in (
        "fwe_reference_replay_utils",
        "replay_utils",
    ):
        module = sys.modules.get(candidate)
        if module is not None and hasattr(module, "ledger_digest"):
            return module

    sibling = _DEMO_DIR / "replay_utils.py"
    spec = importlib.util.spec_from_file_location(
        "fwe_reference_replay_utils", sibling
    )
    if spec is None or spec.loader is None:
        raise ExperimentConfigError(
            f"could not load replay_utils at {sibling}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["fwe_reference_replay_utils"] = module
    spec.loader.exec_module(module)
    return module


def _load_manifest_module() -> Any:
    for candidate in (
        "fwe_manifest_module",
        "fwe_manifest",
    ):
        module = sys.modules.get(candidate)
        if module is not None and hasattr(module, "build_reference_demo_manifest"):
            return module

    sibling = _DEMO_DIR / "manifest.py"
    spec = importlib.util.spec_from_file_location(
        "fwe_manifest_module", sibling
    )
    if spec is None or spec.loader is None:
        raise ExperimentConfigError(
            f"could not load manifest module at {sibling}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["fwe_manifest_module"] = module
    spec.loader.exec_module(module)
    return module


def _check_unimplemented_overrides(config: ExperimentConfig) -> None:
    """
    The v1.8 harness only supports configs equivalent to the bundled
    demo. Any deviation raises ``NotImplementedError`` so future
    v1.8.x milestones can wire each parameter explicitly. The error
    is intentionally catchable separately from validation errors.
    """
    entities_path = _resolve_path(config.input_entities_path)
    if entities_path != _DEMO_DEFAULT_ENTITIES_PATH:
        raise NotImplementedError(
            f"v1.8 harness only supports the bundled demo entities at "
            f"{_DEMO_DEFAULT_ENTITIES_PATH}; got {entities_path}. "
            "Custom entity catalogs are a v1.8.x extension."
        )
    if config.start_date != _DEMO_DEFAULT_START_DATE:
        raise NotImplementedError(
            f"v1.8 harness only supports start_date="
            f"{_DEMO_DEFAULT_START_DATE!r}; got {config.start_date!r}. "
            "Custom start dates are a v1.8.x extension."
        )
    if config.days != _DEMO_DEFAULT_DAYS:
        raise NotImplementedError(
            f"v1.8 harness only supports days={_DEMO_DEFAULT_DAYS}; "
            f"got {config.days}. Custom day counts are a v1.8.x "
            "extension."
        )
    if config.execution_mode != _DEMO_DEFAULT_EXECUTION_MODE:
        raise NotImplementedError(
            f"v1.8 harness only supports execution_mode="
            f"{_DEMO_DEFAULT_EXECUTION_MODE!r}; got "
            f"{config.execution_mode!r}. The intraday_phase mode is "
            "a v1.8.x extension."
        )
    # Optional sections that v1.8 cannot yet honor: warn loudly by
    # raising. The schema is documented and round-trips through the
    # manifest, but driving alternate behavior comes later.
    nonempty_optional: list[str] = []
    if config.external_observations:
        nonempty_optional.append("external_observations")
    if config.signal_templates:
        nonempty_optional.append("signal_templates")
    if config.valuation_templates:
        nonempty_optional.append("valuation_templates")
    if config.institutional_actions:
        nonempty_optional.append("institutional_actions")
    if config.event_delivery_targets:
        nonempty_optional.append("event_delivery_targets")
    if nonempty_optional:
        raise NotImplementedError(
            "v1.8 harness does not yet drive alternate behavior from "
            "config sections: "
            f"{nonempty_optional}. These sections are documented in "
            "the schema for forward-compatibility; v1.8.x will wire "
            "them step by step."
        )


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
    tmp.replace(path)


def run_reference_experiment(
    config: ExperimentConfig,
) -> ExperimentResult:
    """
    Run the reference demo under the given experiment config.

    Validation is run again here so callers that constructed a config
    in code without going through ``load_experiment_config`` are still
    held to the same checks. Unsupported config combinations raise
    ``NotImplementedError``; data validation errors raise
    ``ExperimentConfigError``.
    """
    validate_experiment_config(config)
    _check_unimplemented_overrides(config)

    demo = _load_demo_module()
    replay_utils = _load_replay_utils()

    kernel, summary = demo.run()

    digest: str | None = None
    if config.replay_digest_enabled:
        digest = replay_utils.ledger_digest(kernel)

    output_dir = _resolve_path(config.output_dir)

    manifest_path: Path | None = None
    if config.manifest_enabled:
        manifest_module = _load_manifest_module()
        manifest = manifest_module.build_reference_demo_manifest(
            kernel,
            summary,
            input_paths=[Path(config.input_entities_path)],
        )
        # Attach the experiment-level metadata that the demo manifest
        # alone does not carry. The base manifest schema stays
        # unchanged; this is a strict superset.
        manifest["experiment"] = {
            "config_schema_version": CONFIG_SCHEMA_VERSION,
            "run_id": config.run_id,
            "run_label": config.run_label,
            "config_used": config.to_dict(),
        }
        manifest_path = output_dir / "manifest.json"
        manifest_module.write_manifest(manifest, manifest_path)

    digest_path: Path | None = None
    if config.replay_digest_enabled and digest is not None:
        digest_path = output_dir / "ledger_digest.txt"
        _atomic_write_text(digest_path, digest + "\n")

    return ExperimentResult(
        config=config,
        kernel=kernel,
        summary=summary,
        ledger_digest=digest,
        manifest_path=manifest_path,
        digest_path=digest_path,
    )
