"""
v1.19.1 — Run Export Bundle infrastructure.

Deterministic export-bundle layer for packaging an FWE run into
UI / report-readable JSON artifacts. v1.19.1 is **export
infrastructure only** — it does not run the engine, does not
implement the ``monthly_reference`` or ``scenario_monthly`` run
profiles, does not connect the browser to Python, and does not
move the default-fixture ``living_world_digest``. The next
milestone (v1.19.2) will add the CLI exporter that produces a
real :class:`RunExportBundle` from a kernel run; v1.19.4 will
add a read-only UI loader.

Critical design constraints carried forward from v1.19.0
(binding):

- A :class:`RunExportBundle` is a **label-only / payload-only
  data carrier**. It does not call into the kernel, does not
  import any source-of-truth book, and does not emit a ledger
  record. Its construction is pure-function over arguments.
- ``generated_at_policy_label = "stable_for_replay"`` is the
  default; same arguments → byte-identical JSON. The dataclass
  carries **no** wall-clock timestamp field — there is nothing
  to drift across runs.
- ``boundary_flags`` defaults to the v1.19.0 binding set
  (``synthetic_only`` / ``no_price_formation`` / ``no_trading``
  / ``no_investment_advice`` / ``no_real_data`` /
  ``no_japan_calibration`` / ``no_llm_execution`` /
  ``display_or_export_only``). Every section payload, every
  metadata block, and every boundary-flag mapping is scanned
  against :data:`FORBIDDEN_RUN_EXPORT_FIELD_NAMES` at
  construction.
- The module is **runtime-book-free**. Tests pin the absence
  of any kernel / source-of-truth book / scenario-storage
  module import.

The module ships:

- closed-set vocabularies for ``run_profile_label``,
  ``generated_at_policy_label``, ``status``, ``visibility``;
- the v1.19.0 hard-naming-boundary
  :data:`FORBIDDEN_RUN_EXPORT_FIELD_NAMES` frozenset
  (re-export of the v1.18.0 actor-decision / price / forecast
  / advice / real-data / Japan-calibration / LLM forbidden
  set, extended with the v1.17.0 forbidden display-name
  intersection);
- the immutable :class:`RunExportBundle` dataclass;
- :func:`build_run_export_bundle` (helper), :func:`bundle_to_dict`,
  :func:`bundle_to_json` (deterministic via ``sort_keys=True``),
  :func:`write_run_export_bundle`, and
  :func:`read_run_export_bundle` (returns a ``dict`` — the
  v1.19.1 task pins JSON round-trip; full dataclass restoration
  is deferred to a later milestone).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


RUN_PROFILE_LABELS: frozenset[str] = frozenset(
    {
        "quarterly_default",
        "monthly_reference",
        # v1.20.3 / v1.20.4 — opt-in scenario universe profile.
        # The CLI exporter (``examples.reference_world.export_run_bundle``)
        # builds bundles for this label as of v1.20.4; the static
        # UI (``examples/ui/fwe_workbench_mockup.html``) renders
        # them at v1.20.5.
        "scenario_monthly_reference_universe",
        "scenario_monthly",
        "daily_display_only",
        "future_daily_full_simulation",
        "unknown",
    }
)


GENERATED_AT_POLICY_LABELS: frozenset[str] = frozenset(
    {
        "stable_for_replay",
        "explicit_timestamp",
        "omitted",
        "unknown",
    }
)


STATUS_LABELS: frozenset[str] = frozenset(
    {
        "draft",
        "exported",
        "stale",
        "superseded",
        "archived",
        "unknown",
    }
)


VISIBILITY_LABELS: frozenset[str] = frozenset(
    {
        "public",
        "restricted",
        "internal",
        "private",
        "unknown",
    }
)


# v1.19.0 hard naming boundary on bundle payload + metadata.
# Tests scan dataclass field names, payload keys, and metadata
# keys for any of the forbidden names below. The forbidden set
# composes the v1.18.0 actor-decision / price / forecast /
# advice / real-data / Japan-calibration / LLM names with the
# v1.17.0 forbidden display names so a bundle cannot smuggle a
# canonical-claim token under any sub-section.
FORBIDDEN_RUN_EXPORT_FIELD_NAMES: frozenset[str] = frozenset(
    {
        # v1.18.0 actor-decision / canonical-judgment names
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        # price / forecast / advice
        "price",
        "market_price",
        "predicted_index",
        "predicted_path",
        "forecast_path",
        "forecast_index",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "investment_recommendation",
        "price_prediction",
        # real data / Japan calibration / LLM execution
        "real_data_value",
        "real_price_series",
        "actual_price",
        "quoted_price",
        "last_trade",
        "nav",
        "index_value",
        "benchmark_value",
        "valuation_target",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
    }
)


# v1.19.0 default boundary-flag set. The eight flags below are
# the binding default carried on every emitted record. Callers
# can extend the set with additional ``True`` flags but cannot
# replace the defaults — :func:`_normalize_boundary_flags` merges
# user input on top of this default.
_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    ("synthetic_only", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_investment_advice", True),
    ("no_real_data", True),
    ("no_japan_calibration", True),
    ("no_llm_execution", True),
    ("display_or_export_only", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RunExportError(Exception):
    """Base class for v1.19.1 run-export errors."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_label(
    value: Any, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _validate_non_negative_int(
    value: Any, *, field_name: str
) -> int:
    # bool is a subclass of int — reject explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be a non-negative int; "
            f"got {type(value).__name__}"
        )
    if value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative int; got {value}"
        )
    return value


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    """Reject any v1.19.0 forbidden field name appearing in a
    metadata, payload, or boundary-flag mapping. Keys that are
    not strings are silently skipped (the caller's payload may
    be free-form JSON-ish). The recursion stays one level deep:
    nested dicts are scanned by callers as needed."""
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_RUN_EXPORT_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.19.0 hard naming boundary — run-export "
                "bundles do not carry actor-decision / price / "
                "forecast / advice / real-data / "
                "Japan-calibration / LLM fields)"
            )


def _scan_payload_recursively(
    payload: Any, *, field_name: str
) -> None:
    """Walk a JSON-like payload (dict / list / tuple / scalar)
    and reject any forbidden key name at any depth."""
    if isinstance(payload, Mapping):
        _scan_for_forbidden_keys(payload, field_name=field_name)
        for value in payload.values():
            _scan_payload_recursively(value, field_name=field_name)
        return
    if isinstance(payload, (list, tuple)):
        for entry in payload:
            _scan_payload_recursively(entry, field_name=field_name)


def _normalize_payload(
    value: Mapping[str, Any] | None, *, field_name: str
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(
            f"{field_name} must be a mapping; "
            f"got {type(value).__name__}"
        )
    out: dict[str, Any] = dict(value)
    _scan_payload_recursively(out, field_name=field_name)
    return out


def _normalize_boundary_flags(
    value: Mapping[str, Any] | Iterable[tuple[str, bool]] | None,
    *,
    field_name: str = "boundary_flags",
) -> dict[str, bool]:
    """Merge user input on top of the v1.19.0 default flag set.
    Accepts a mapping, an iterable of ``(key, bool)`` pairs, or
    ``None``. Every value must be ``bool``; every key must be a
    non-empty string and not in
    :data:`FORBIDDEN_RUN_EXPORT_FIELD_NAMES`."""
    out: dict[str, bool] = _default_boundary_flags()
    if value is None or value == ():
        return out
    if isinstance(value, Mapping):
        items: Iterable[tuple[Any, Any]] = value.items()
    else:
        items = list(value)
    for key, val in items:
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"{field_name} keys must be non-empty strings"
            )
        if not isinstance(val, bool):
            raise ValueError(
                f"{field_name} values must be bool; "
                f"got {type(val).__name__}"
            )
        if key in FORBIDDEN_RUN_EXPORT_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r}"
            )
        out[key] = val
    return out


# ---------------------------------------------------------------------------
# RunExportBundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunExportBundle:
    """Immutable run-export bundle. Carries the v1.19.0 four-
    layer surface (engine run profile / report export bundle /
    UI loading mode / local run bridge) at the **report export
    bundle** layer only — it is a pure data carrier suitable
    for serialisation to JSON and later read-only UI loading.

    The dataclass:

    - has **no** wall-clock timestamp field — the
      ``generated_at_policy_label`` records *whether* a real
      timestamp would be inserted; the actual timestamp, if
      ever needed, lives inside ``metadata`` and is opt-in;
    - has **no** ``confidence`` / ``magnitude`` / numeric
      forecast field — bundles are not predictions;
    - has **no** actor-decision field — bundles do not decide;
    - is jurisdiction-neutral by construction; tests pin the
      absence of forbidden tokens in the module text and
      payload keys.

    Default boundary flags (eight entries — see
    :data:`_DEFAULT_BOUNDARY_FLAGS_TUPLE`) ride on every emitted
    bundle. Callers may extend the flag set with additional
    ``True`` markers (e.g. ``"stable_for_replay"`` if the
    caller wants to surface that pin); they may not insert a
    forbidden name.
    """

    bundle_id: str
    run_profile_label: str
    regime_label: str
    selected_scenario_label: str
    period_count: int
    digest: str
    generated_at_policy_label: str = "stable_for_replay"
    manifest: Mapping[str, Any] = field(default_factory=dict)
    overview: Mapping[str, Any] = field(default_factory=dict)
    timeline: Mapping[str, Any] = field(default_factory=dict)
    regime_compare: Mapping[str, Any] = field(default_factory=dict)
    scenario_trace: Mapping[str, Any] = field(default_factory=dict)
    attention_diff: Mapping[str, Any] = field(default_factory=dict)
    market_intent: Mapping[str, Any] = field(default_factory=dict)
    financing: Mapping[str, Any] = field(default_factory=dict)
    ledger_excerpt: Mapping[str, Any] = field(default_factory=dict)
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    status: str = "exported"
    visibility: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "bundle_id",
        "regime_label",
        "selected_scenario_label",
        "digest",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("run_profile_label",         RUN_PROFILE_LABELS),
        ("generated_at_policy_label", GENERATED_AT_POLICY_LABELS),
        ("status",                    STATUS_LABELS),
        ("visibility",                VISIBILITY_LABELS),
    )

    PAYLOAD_FIELDS: ClassVar[tuple[str, ...]] = (
        "manifest",
        "overview",
        "timeline",
        "regime_compare",
        "scenario_trace",
        "attention_diff",
        "market_intent",
        "financing",
        "ledger_excerpt",
        "metadata",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_RUN_EXPORT_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.19.0 "
                    "forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        object.__setattr__(
            self,
            "period_count",
            _validate_non_negative_int(
                self.period_count, field_name="period_count"
            ),
        )
        for name in self.PAYLOAD_FIELDS:
            object.__setattr__(
                self,
                name,
                _normalize_payload(
                    getattr(self, name), field_name=name
                ),
            )
        object.__setattr__(
            self,
            "boundary_flags",
            _normalize_boundary_flags(
                self.boundary_flags, field_name="boundary_flags"
            ),
        )

    # -- serialisation -----------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Deterministic mapping representation. Same bundle →
        byte-identical dict (insertion-order preserved by
        Python's dict)."""
        return {
            "bundle_id": self.bundle_id,
            "run_profile_label": self.run_profile_label,
            "regime_label": self.regime_label,
            "selected_scenario_label": self.selected_scenario_label,
            "period_count": self.period_count,
            "digest": self.digest,
            "generated_at_policy_label": (
                self.generated_at_policy_label
            ),
            "manifest": dict(self.manifest),
            "overview": dict(self.overview),
            "timeline": dict(self.timeline),
            "regime_compare": dict(self.regime_compare),
            "scenario_trace": dict(self.scenario_trace),
            "attention_diff": dict(self.attention_diff),
            "market_intent": dict(self.market_intent),
            "financing": dict(self.financing),
            "ledger_excerpt": dict(self.ledger_excerpt),
            "boundary_flags": dict(self.boundary_flags),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def build_run_export_bundle(
    *,
    bundle_id: str,
    run_profile_label: str,
    regime_label: str,
    period_count: int,
    digest: str,
    selected_scenario_label: str = "none_baseline",
    manifest: Mapping[str, Any] | None = None,
    overview: Mapping[str, Any] | None = None,
    timeline: Mapping[str, Any] | None = None,
    regime_compare: Mapping[str, Any] | None = None,
    scenario_trace: Mapping[str, Any] | None = None,
    attention_diff: Mapping[str, Any] | None = None,
    market_intent: Mapping[str, Any] | None = None,
    financing: Mapping[str, Any] | None = None,
    ledger_excerpt: Mapping[str, Any] | None = None,
    boundary_flags: (
        Mapping[str, bool] | Iterable[tuple[str, bool]] | None
    ) = None,
    generated_at_policy_label: str = "stable_for_replay",
    status: str = "exported",
    visibility: str = "public",
    metadata: Mapping[str, Any] | None = None,
) -> RunExportBundle:
    """Deterministic builder. Same arguments → byte-identical
    :class:`RunExportBundle` (and therefore byte-identical
    :func:`bundle_to_json` output).

    Argument signature mirrors :class:`RunExportBundle`'s field
    set so the caller can construct a bundle without importing
    the dataclass directly. Defaults pin the v1.19.0 ``stable_for_replay`` /
    ``exported`` / ``public`` settings; ``selected_scenario_label``
    defaults to ``"none_baseline"`` so a baseline run with no
    scenario applied has a sensible carrier label.
    """
    return RunExportBundle(
        bundle_id=bundle_id,
        run_profile_label=run_profile_label,
        regime_label=regime_label,
        selected_scenario_label=selected_scenario_label,
        period_count=period_count,
        digest=digest,
        generated_at_policy_label=generated_at_policy_label,
        manifest=dict(manifest or {}),
        overview=dict(overview or {}),
        timeline=dict(timeline or {}),
        regime_compare=dict(regime_compare or {}),
        scenario_trace=dict(scenario_trace or {}),
        attention_diff=dict(attention_diff or {}),
        market_intent=dict(market_intent or {}),
        financing=dict(financing or {}),
        ledger_excerpt=dict(ledger_excerpt or {}),
        boundary_flags=(
            boundary_flags
            if boundary_flags is not None
            else _default_boundary_flags()
        ),
        status=status,
        visibility=visibility,
        metadata=dict(metadata or {}),
    )


def bundle_to_dict(bundle: RunExportBundle) -> dict[str, Any]:
    """Module-level alias for :meth:`RunExportBundle.to_dict`."""
    if not isinstance(bundle, RunExportBundle):
        raise TypeError(
            "bundle_to_dict expects a RunExportBundle instance"
        )
    return bundle.to_dict()


def bundle_to_json(
    bundle: RunExportBundle, *, indent: int | None = 2
) -> str:
    """Deterministic JSON serialisation.

    Uses ``sort_keys=True`` so the output is byte-identical
    across Python sessions for the same bundle (independent of
    insertion order in the underlying ``Mapping`` objects).
    ``ensure_ascii=False`` keeps Unicode legible in the
    rendered JSON.
    """
    if not isinstance(bundle, RunExportBundle):
        raise TypeError(
            "bundle_to_json expects a RunExportBundle instance"
        )
    return json.dumps(
        bundle.to_dict(),
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
    )


def write_run_export_bundle(
    bundle: RunExportBundle,
    path: str | Path,
    *,
    indent: int | None = 2,
) -> None:
    """Write a deterministic JSON file at ``path``.

    The function does **not** create parent directories — the
    caller is responsible for the destination directory's
    existence (the v1.19.2 CLI exporter will validate that).
    Two writes of the same bundle produce byte-identical files.
    """
    if not isinstance(bundle, RunExportBundle):
        raise TypeError(
            "write_run_export_bundle expects a RunExportBundle "
            "instance"
        )
    text = bundle_to_json(bundle, indent=indent)
    Path(path).write_text(text, encoding="utf-8")


def read_run_export_bundle(path: str | Path) -> dict[str, Any]:
    """Load a previously written run-export bundle as a
    ``dict``.

    v1.19.1 returns a plain dict — the JSON round-trip is
    sufficient for the v1.19.4 read-only UI loader to render the
    bundle into the existing tabs. Restoring a full
    :class:`RunExportBundle` instance is **deferred to a later
    milestone** (the validation cost is non-trivial and the UI
    does not need an instance — it walks the dict).
    """
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RunExportError(
            "run-export bundle JSON must decode to a dict; "
            f"got {type(data).__name__}"
        )
    return data
