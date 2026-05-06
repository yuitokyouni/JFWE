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


# v1.22.1 — keys allowed inside one ``stress_readout`` entry.
# Whitelist; v1.22.0 design pin (§3.4) lists exactly these 19
# descriptive-only keys. Adding a key here without re-pinning
# the design note is a regression.
STRESS_READOUT_ENTRY_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "stress_program_application_id",
        "stress_program_template_id",
        "as_of_date",
        "total_step_count",
        "resolved_step_count",
        "unresolved_step_count",
        "active_step_ids",
        "unresolved_step_ids",
        "unresolved_reason_labels",
        "is_partial",
        "scenario_driver_template_ids",
        "scenario_application_ids",
        "scenario_context_shift_ids",
        "context_surface_labels",
        "shift_direction_labels",
        "scenario_family_labels",
        "source_context_record_ids",
        "downstream_citation_ids",
        "warnings",
    }
)


# v1.22.1 — forbidden tokens in the ``stress_readout`` section.
# These are checked against every entry's keys and against every
# string value (separator-bounded match: a token matches when it
# appears at the boundary of a separator in
# ``_STRESS_READOUT_VALUE_SEPARATORS``). The set composes the
# v1.22.0-pinned forbidden vocabulary in
# ``docs/v1_22_static_ui_stress_readout_reflection.md`` §3.5
# with the v1.21.0a interaction-label tokens that were deferred
# to v1.22+ (manual_annotation only — never inferred by a
# helper).
FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS: frozenset[str] = (
    frozenset(
        {
            # v1.22.0 outcome / impact / risk language
            "impact",
            "outcome",
            "risk_score",
            "amplification",
            "dampening",
            "offset_effect",
            "dominant_stress",
            "net_pressure",
            "composite_risk",
            # forecast / prediction / advice
            "forecast",
            "expected_response",
            "prediction",
            "recommendation",
            "expected_return",
            "target_price",
            # trading verbs (caught at boundary, not substring)
            "buy",
            "sell",
            "order",
            "trade",
            "execution",
            # real data / Japan calibration / LLM
            "real_data",
            "japan_calibration",
            "llm_output",
            # v1.21.0a aggregate / composite / net / dominant
            # composition reduction language
            "aggregate",
            "combined",
            "net",
            "dominant",
            "composite",
            # v1.21.0a interaction-label vocabulary (deferred
            # to v1.22+ as manual_annotation only — never
            # auto-inferred; never a helper-emitted field)
            "amplify",
            "dampen",
            "offset",
            "coexist",
        }
    )
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


def _scan_value_for_forbidden_stress_readout_tokens(
    value: Any, *, field_name: str
) -> None:
    """Walk a JSON-like value and reject any v1.22.1 forbidden
    token at any depth.

    Discipline:

    - **Dict keys** are checked with exact-equality (case-
      sensitive) against
      :data:`FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS` and
      :data:`FORBIDDEN_RUN_EXPORT_FIELD_NAMES`. The 19-key
      whitelist applied to top-level entry keys catches all
      direct cases; this recursive scan catches forbidden
      keys nested under metadata-shaped values.
    - **String values** are checked with case-insensitive
      whole-string equality. This rejects literal smuggled
      tokens like ``"impact"`` or ``"forecast"`` while
      allowing legitimate v1.18.2 closed-set values such as
      ``"attention_amplify"`` (which contains ``amplify`` as
      a substring but is **not** an interaction-inference
      label — it is a single-stress shift direction).

    Whole-string equality is the right semantics: the v1.21.0a
    forbidden tokens are forbidden as **field names** (a
    helper-emitted ``interaction_label = "amplify"`` is the
    target), not as substrings of legitimate values. Upstream
    v1.18.2 / v1.21.x discipline already prevents free-text
    smuggling; the v1.22.1 export simply re-pins the rule that
    no v1.22.1-generated value may equal a forbidden token.
    """
    if isinstance(value, str):
        v_lower = value.lower()
        for token in FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS:
            if v_lower == token.lower():
                raise ValueError(
                    f"{field_name} contains forbidden token "
                    f"{token!r} as a string value "
                    "(v1.22.1 forbidden-token set — the "
                    "stress_readout export section is "
                    "descriptive-only and must not surface "
                    "interaction-inference / outcome / "
                    "forecast tokens as values)"
                )
        return
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(k, str):
                if (
                    k
                    in FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS
                ):
                    raise ValueError(
                        f"{field_name} contains forbidden key "
                        f"{k!r} (v1.22.1 forbidden-token set)"
                    )
                if k in FORBIDDEN_RUN_EXPORT_FIELD_NAMES:
                    raise ValueError(
                        f"{field_name} contains forbidden key "
                        f"{k!r} (v1.19.0 hard naming boundary)"
                    )
            _scan_value_for_forbidden_stress_readout_tokens(
                v, field_name=field_name
            )
        return
    if isinstance(value, (list, tuple)):
        for entry in value:
            _scan_value_for_forbidden_stress_readout_tokens(
                entry, field_name=field_name
            )
        return
    # bools, ints, floats, None — no string content to scan.


def _validate_stress_readout_entry(
    entry: Any, *, field_name: str
) -> dict[str, Any]:
    """Validate a single ``stress_readout`` list entry.

    Binding (v1.22.0 §3.4 / §3.6):

    - entry is a Mapping with exactly the 19 required keys
      (whitelist; no extra keys; none missing);
    - the three multiset arrays (context_surface_labels,
      shift_direction_labels, scenario_family_labels) and the
      scenario_context_shift_ids list are equal-length parallel
      arrays;
    - len(active_step_ids) == resolved_step_count;
    - len(unresolved_step_ids) == unresolved_step_count;
    - len(unresolved_reason_labels) == unresolved_step_count;
    - total_step_count == resolved_step_count + unresolved_step_count;
    - is_partial == (unresolved_step_count > 0);
    - no forbidden token at any depth (boundary scan).
    """
    if not isinstance(entry, Mapping):
        raise ValueError(
            f"{field_name} entries must be Mapping; "
            f"got {type(entry).__name__}"
        )
    keys = set(entry.keys())
    missing = STRESS_READOUT_ENTRY_REQUIRED_KEYS - keys
    extra = keys - STRESS_READOUT_ENTRY_REQUIRED_KEYS
    if missing:
        raise ValueError(
            f"{field_name} entry missing required keys: "
            f"{sorted(missing)!r}"
        )
    if extra:
        raise ValueError(
            f"{field_name} entry contains unexpected keys: "
            f"{sorted(extra)!r}"
        )
    out = dict(entry)

    # forbidden-token boundary scan
    _scan_value_for_forbidden_stress_readout_tokens(
        out, field_name=field_name
    )

    # type / shape checks
    for sk in (
        "stress_program_application_id",
        "stress_program_template_id",
        "as_of_date",
    ):
        if not isinstance(out[sk], str) or not out[sk]:
            raise ValueError(
                f"{field_name} entry {sk!r} must be a "
                "non-empty string"
            )
    for ck in (
        "total_step_count",
        "resolved_step_count",
        "unresolved_step_count",
    ):
        v = out[ck]
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(
                f"{field_name} entry {ck!r} must be a "
                "non-negative int"
            )
        if v < 0:
            raise ValueError(
                f"{field_name} entry {ck!r} must be >= 0; "
                f"got {v}"
            )
    if not isinstance(out["is_partial"], bool):
        raise ValueError(
            f"{field_name} entry 'is_partial' must be bool; "
            f"got {type(out['is_partial']).__name__}"
        )
    for lk in (
        "active_step_ids",
        "unresolved_step_ids",
        "unresolved_reason_labels",
        "scenario_driver_template_ids",
        "scenario_application_ids",
        "scenario_context_shift_ids",
        "context_surface_labels",
        "shift_direction_labels",
        "scenario_family_labels",
        "source_context_record_ids",
        "downstream_citation_ids",
        "warnings",
    ):
        v = out[lk]
        if not isinstance(v, list):
            raise ValueError(
                f"{field_name} entry {lk!r} must be a list; "
                f"got {type(v).__name__}"
            )
        for entry_str in v:
            if not isinstance(entry_str, str) or not entry_str:
                raise ValueError(
                    f"{field_name} entry {lk!r} contains a "
                    "non-string or empty entry"
                )

    # invariant checks (v1.22.0 §3.6)
    if (
        out["resolved_step_count"]
        + out["unresolved_step_count"]
        != out["total_step_count"]
    ):
        raise ValueError(
            f"{field_name} entry: "
            "resolved_step_count + unresolved_step_count must "
            "equal total_step_count"
        )
    if out["is_partial"] != (out["unresolved_step_count"] > 0):
        raise ValueError(
            f"{field_name} entry: "
            "is_partial must equal "
            "(unresolved_step_count > 0)"
        )
    if (
        len(out["active_step_ids"])
        != out["resolved_step_count"]
    ):
        raise ValueError(
            f"{field_name} entry: len(active_step_ids) must "
            "equal resolved_step_count"
        )
    if (
        len(out["unresolved_step_ids"])
        != out["unresolved_step_count"]
    ):
        raise ValueError(
            f"{field_name} entry: len(unresolved_step_ids) "
            "must equal unresolved_step_count"
        )
    if (
        len(out["unresolved_reason_labels"])
        != out["unresolved_step_count"]
    ):
        raise ValueError(
            f"{field_name} entry: "
            "len(unresolved_reason_labels) must equal "
            "unresolved_step_count"
        )
    n_shifts = len(out["scenario_context_shift_ids"])
    if (
        len(out["context_surface_labels"]) != n_shifts
        or len(out["shift_direction_labels"]) != n_shifts
        or len(out["scenario_family_labels"]) != n_shifts
    ):
        raise ValueError(
            f"{field_name} entry: parallel arrays "
            "(scenario_context_shift_ids / "
            "context_surface_labels / shift_direction_labels "
            "/ scenario_family_labels) must all be the same "
            "length"
        )
    return out


def _normalize_stress_readout(
    value: (
        Iterable[Mapping[str, Any]]
        | tuple[Mapping[str, Any], ...]
        | None
    ),
    *,
    field_name: str = "stress_readout",
) -> tuple[dict[str, Any], ...]:
    """Normalise the v1.22.1 ``stress_readout`` payload section
    to a tuple of frozen-dict-like entries.

    Cardinality (binding, v1.21.0a):
    ``len(value) ∈ {0, 1}``. v1.22.1 carries forward the v1.21
    "≤ 1 program per run" pin; an entry list of length > 1
    is a regression.
    """
    if value is None:
        return ()
    if isinstance(value, Mapping):
        raise ValueError(
            f"{field_name} must be a list / tuple of entries; "
            "got a single Mapping (wrap it in a list)"
        )
    entries = list(value)
    if len(entries) > 1:
        raise ValueError(
            f"{field_name} cardinality (binding from "
            "v1.21.0a): at most 1 entry; "
            f"got {len(entries)}"
        )
    return tuple(
        _validate_stress_readout_entry(
            e, field_name=field_name
        )
        for e in entries
    )


def _normalize_manual_annotation_readout(
    value: (
        Iterable[Mapping[str, Any]]
        | tuple[Mapping[str, Any], ...]
        | None
    ),
    *,
    field_name: str = "manual_annotation_readout",
) -> tuple[dict[str, Any], ...]:
    """Normalise the v1.24.3 ``manual_annotation_readout`` payload
    section to a tuple of frozen-dict-like entries. Cardinality:
    ``len(value) ∈ {0, 1}`` (one readout per bundle).

    Forbidden-token boundary scan applies at every key + every
    whole-string value at any depth, against the v1.23.1
    canonical
    :data:`world.forbidden_tokens.FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES`
    composition.
    """
    # Imported lazily to avoid a circular import — both
    # ``world.manual_annotation_export`` and
    # ``world.run_export`` are part of the run-export surface.
    from world.manual_annotation_export import (
        _scan_export_entry_for_forbidden,
    )
    if value is None:
        return ()
    if isinstance(value, Mapping):
        raise ValueError(
            f"{field_name} must be a list / tuple of entries; "
            "got a single Mapping (wrap it in a list)"
        )
    entries = list(value)
    if len(entries) > 1:
        raise ValueError(
            f"{field_name} cardinality (v1.24.3 binding): "
            f"at most 1 entry; got {len(entries)}"
        )
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"{field_name} entries must be Mapping; "
                f"got {type(entry).__name__}"
            )
        normalised = dict(entry)
        _scan_export_entry_for_forbidden(
            normalised, field_name=field_name
        )
        out.append(normalised)
    return tuple(out)


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
    # v1.22.1 — descriptive-only stress-readout reflection
    # section. Cardinality 0 or 1 entry. Empty by default;
    # omitted from ``to_dict`` / ``bundle_to_json`` output when
    # empty so pre-v1.22 bundles stay byte-identical.
    stress_readout: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    # v1.24.3 — descriptive-only manual-annotation readout
    # reflection section. Cardinality 0 or 1 entry. Empty by
    # default; omitted from ``to_dict`` / ``bundle_to_json``
    # output when empty so pre-v1.24 bundles stay byte-
    # identical (every v1.21.last canonical
    # ``living_world_digest`` is preserved at v1.24.3).
    manual_annotation_readout: tuple[Mapping[str, Any], ...] = (
        field(default_factory=tuple)
    )

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
        object.__setattr__(
            self,
            "stress_readout",
            _normalize_stress_readout(
                self.stress_readout, field_name="stress_readout"
            ),
        )
        object.__setattr__(
            self,
            "manual_annotation_readout",
            _normalize_manual_annotation_readout(
                self.manual_annotation_readout,
                field_name="manual_annotation_readout",
            ),
        )

    # -- serialisation -----------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Deterministic mapping representation. Same bundle →
        byte-identical dict (insertion-order preserved by
        Python's dict).

        v1.22.1: ``stress_readout`` is **omitted** from the
        output when empty (the default). This preserves
        byte-identity with pre-v1.22 bundles for every
        no-stress-program run profile, keeping all v1.21.last
        digests byte-identical.
        """
        out: dict[str, Any] = {
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
        if self.stress_readout:
            out["stress_readout"] = [
                dict(e) for e in self.stress_readout
            ]
        # v1.24.3 — manual annotation readout omitted when
        # empty (default), preserving every pre-v1.24
        # bundle digest byte-identical.
        if self.manual_annotation_readout:
            out["manual_annotation_readout"] = [
                dict(e) for e in self.manual_annotation_readout
            ]
        return out


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
    stress_readout: (
        Iterable[Mapping[str, Any]]
        | tuple[Mapping[str, Any], ...]
        | None
    ) = None,
    manual_annotation_readout: (
        Iterable[Mapping[str, Any]]
        | tuple[Mapping[str, Any], ...]
        | None
    ) = None,
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
        stress_readout=(
            tuple(dict(e) for e in stress_readout)
            if stress_readout
            else ()
        ),
        manual_annotation_readout=(
            tuple(
                dict(e)
                for e in manual_annotation_readout
            )
            if manual_annotation_readout
            else ()
        ),
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
