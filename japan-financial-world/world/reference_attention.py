"""
v1.8.12 Reference attention demo — heterogeneous attention.

This module ships a small reference helper that demonstrates the
v1.8.5 / v1.8.9 / v1.8.10 / v1.8.11 layers fitting together as
**attention**, not as decision: an investor and a bank, looking at
the same reference world, build *different*
``SelectedObservationSet`` records from the menus the v1.8.11
``ObservationMenuBuilder`` produces.

The helper is intentionally narrow:

- It does **not** execute any review routine. There is no
  investor-review or bank-review pipeline in v1.8.12; the
  selections are recorded as data, and v1.8.13 / v1.9 may consume
  them in actual routine runs.
- It does **not** compute valuations, prices, lending decisions,
  trades, sensitivities, impacts, DSCR / LTV updates, scenario
  outcomes, or any other economic behavior.
- It does **not** reach for real Japan calibration. All ids and
  values are synthetic, and the helper only registers refs the
  caller can re-derive deterministically from the inputs.
- It does **not** add new ledger record types. Profile / menu /
  selection insertions flow through the existing
  ``ATTENTION_PROFILE_ADDED`` / ``OBSERVATION_MENU_CREATED`` /
  ``OBSERVATION_SET_SELECTED`` paths on ``AttentionBook``.

Selection semantics
-------------------

Selection is **rule-based and deterministic** so the demo's
output is reviewable without running the simulator. For each
actor, the helper:

1. Builds the per-actor ``ObservationMenu`` through the kernel's
   ``ObservationMenuBuilder`` (gates 1+2: visibility + availability).
2. Filters each menu axis against the actor's ``AttentionProfile``:
   - signals by ``signal_type`` ∈ ``watched_signal_types`` OR
     ``subject_id`` ∈ ``watched_subject_ids``;
   - variable observations whose underlying variable's
     ``variable_id`` ∈ ``watched_variable_ids`` OR
     ``variable_group`` ∈ ``watched_variable_groups``;
   - exposures whose ``exposure_type`` ∈ ``watched_exposure_types``
     OR ``metric`` ∈ ``watched_exposure_metrics``.
3. Concatenates the matched refs in **menu-order** (signals →
   variable observations → exposures) so the result is
   deterministic across runs.

The filter is **structural**, not economic — it asks "does this
ref's record satisfy this profile's filters?" not "is this ref a
good idea?". Ranking, weighting, top-k truncation, and economic
prioritization remain out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

from world.attention import AttentionProfile, SelectedObservationSet
from world.observation_menu_builder import ObservationMenuBuildRequest


# ---------------------------------------------------------------------------
# Constants — defaults that callers can override
# ---------------------------------------------------------------------------


_DEFAULT_INVESTOR_WATCHED_VARIABLE_GROUPS: tuple[str, ...] = (
    "fx",
    "rates",
    "financial_market",
    "expectations_narratives",
)
_DEFAULT_INVESTOR_WATCHED_EXPOSURE_METRICS: tuple[str, ...] = (
    "portfolio_translation_exposure",
    "valuation_discount_rate",
    "expected_return_pressure",
)
_DEFAULT_INVESTOR_WATCHED_EXPOSURE_TYPES: tuple[str, ...] = (
    "discount_rate",
    "translation",
    "narrative",
)

_DEFAULT_BANK_WATCHED_VARIABLE_GROUPS: tuple[str, ...] = (
    "rates",
    "credit",
    "real_estate",
    "energy_power",
)
_DEFAULT_BANK_WATCHED_EXPOSURE_METRICS: tuple[str, ...] = (
    "debt_service_burden",
    "collateral_value",
    "operating_cost_pressure",
    "covenant_pressure",
    "liquidity_pressure",
)
_DEFAULT_BANK_WATCHED_EXPOSURE_TYPES: tuple[str, ...] = (
    "funding_cost",
    "collateral",
    "input_cost",
)


_INVESTOR_WATCHED_SIGNAL_TYPES: tuple[str, ...] = (
    "corporate_quarterly_report",
    "earnings_disclosure",
)
_BANK_WATCHED_SIGNAL_TYPES: tuple[str, ...] = (
    "corporate_quarterly_report",
    "earnings_disclosure",
)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvestorBankAttentionDemoResult:
    """
    Aggregate result of one ``run_investor_bank_attention_demo``
    call. Carries the menu / selection ids each actor received
    plus the convenience set differences. All fields are
    deterministic functions of the kernel state at call time
    (so the same kernel + arguments produce the same result on
    every invocation).
    """

    investor_profile_id: str
    bank_profile_id: str
    investor_menu_id: str
    bank_menu_id: str
    investor_selection_id: str
    bank_selection_id: str
    investor_selected_refs: tuple[str, ...]
    bank_selected_refs: tuple[str, ...]
    shared_refs: tuple[str, ...]
    investor_only_refs: tuple[str, ...]
    bank_only_refs: tuple[str, ...]
    as_of_date: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for tuple_field_name in (
            "investor_selected_refs",
            "bank_selected_refs",
            "shared_refs",
            "investor_only_refs",
            "bank_only_refs",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)
        object.__setattr__(self, "metadata", dict(self.metadata))


# ---------------------------------------------------------------------------
# Date / id helpers
# ---------------------------------------------------------------------------


def _coerce_iso_date(value: date | str | None, *, kernel: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    if value is None:
        if (
            kernel.clock is not None
            and kernel.clock.current_date is not None
        ):
            return kernel.clock.current_date.isoformat()
        raise ValueError(
            "as_of_date is None and the kernel clock has no current_date; "
            "supply as_of_date explicitly."
        )
    raise TypeError(
        f"as_of_date must be a date / ISO string / None; got {value!r}"
    )


def _default_investor_profile_id(investor_id: str) -> str:
    return f"profile:investor:{investor_id}:reference_attention"


def _default_bank_profile_id(bank_id: str) -> str:
    return f"profile:bank:{bank_id}:reference_attention"


def _default_menu_request_id(actor_id: str, as_of_date: str) -> str:
    return f"req:menu:{actor_id}:{as_of_date}"


def _default_selection_id(actor_id: str, as_of_date: str) -> str:
    return f"selection:{actor_id}:{as_of_date}"


# ---------------------------------------------------------------------------
# Profile registration (idempotent)
# ---------------------------------------------------------------------------


def register_investor_attention_profile(
    kernel: Any,
    *,
    investor_id: str,
    profile_id: str | None = None,
    firm_id: str | None = None,
    update_frequency: str = "QUARTERLY",
    extra_watched_variable_ids: tuple[str, ...] = (),
    extra_watched_variable_groups: tuple[str, ...] = (),
    extra_watched_exposure_types: tuple[str, ...] = (),
    extra_watched_exposure_metrics: tuple[str, ...] = (),
) -> AttentionProfile:
    """Register or fetch the investor's reference attention profile.

    Idempotent: re-registering returns the existing profile
    unchanged. The helper does **not** validate that
    ``investor_id`` resolves in the registry; cross-references are
    data per the v0/v1 rule.
    """
    if not isinstance(investor_id, str) or not investor_id:
        raise ValueError("investor_id is required")
    pid = profile_id or _default_investor_profile_id(investor_id)
    try:
        return kernel.attention.get_profile(pid)
    except Exception:
        pass

    profile = AttentionProfile(
        profile_id=pid,
        actor_id=investor_id,
        actor_type="investor",
        update_frequency=update_frequency,
        watched_signal_types=_INVESTOR_WATCHED_SIGNAL_TYPES,
        watched_subject_ids=(firm_id,) if firm_id else (),
        watched_variable_ids=tuple(extra_watched_variable_ids),
        watched_variable_groups=(
            _DEFAULT_INVESTOR_WATCHED_VARIABLE_GROUPS
            + tuple(extra_watched_variable_groups)
        ),
        watched_exposure_types=(
            _DEFAULT_INVESTOR_WATCHED_EXPOSURE_TYPES
            + tuple(extra_watched_exposure_types)
        ),
        watched_exposure_metrics=(
            _DEFAULT_INVESTOR_WATCHED_EXPOSURE_METRICS
            + tuple(extra_watched_exposure_metrics)
        ),
    )
    return kernel.attention.add_profile(profile)


def register_bank_attention_profile(
    kernel: Any,
    *,
    bank_id: str,
    profile_id: str | None = None,
    firm_id: str | None = None,
    update_frequency: str = "QUARTERLY",
    extra_watched_variable_ids: tuple[str, ...] = (),
    extra_watched_variable_groups: tuple[str, ...] = (),
    extra_watched_exposure_types: tuple[str, ...] = (),
    extra_watched_exposure_metrics: tuple[str, ...] = (),
) -> AttentionProfile:
    """Register or fetch the bank's reference attention profile.

    Idempotent. Cross-references stored as data.
    """
    if not isinstance(bank_id, str) or not bank_id:
        raise ValueError("bank_id is required")
    pid = profile_id or _default_bank_profile_id(bank_id)
    try:
        return kernel.attention.get_profile(pid)
    except Exception:
        pass

    profile = AttentionProfile(
        profile_id=pid,
        actor_id=bank_id,
        actor_type="bank",
        update_frequency=update_frequency,
        watched_signal_types=_BANK_WATCHED_SIGNAL_TYPES,
        watched_subject_ids=(firm_id,) if firm_id else (),
        watched_variable_ids=tuple(extra_watched_variable_ids),
        watched_variable_groups=(
            _DEFAULT_BANK_WATCHED_VARIABLE_GROUPS
            + tuple(extra_watched_variable_groups)
        ),
        watched_exposure_types=(
            _DEFAULT_BANK_WATCHED_EXPOSURE_TYPES
            + tuple(extra_watched_exposure_types)
        ),
        watched_exposure_metrics=(
            _DEFAULT_BANK_WATCHED_EXPOSURE_METRICS
            + tuple(extra_watched_exposure_metrics)
        ),
    )
    return kernel.attention.add_profile(profile)


# ---------------------------------------------------------------------------
# Selection rules — structural, not economic
# ---------------------------------------------------------------------------


def _select_signals(
    kernel: Any,
    *,
    profile: AttentionProfile,
    available_signal_ids: tuple[str, ...],
) -> tuple[str, ...]:
    selected: list[str] = []
    for signal_id in available_signal_ids:
        try:
            signal = kernel.signals.get_signal(signal_id)
        except Exception:
            continue
        if (
            signal.signal_type in profile.watched_signal_types
            or signal.subject_id in profile.watched_subject_ids
        ):
            selected.append(signal_id)
    return tuple(selected)


def _select_variable_observations(
    kernel: Any,
    *,
    profile: AttentionProfile,
    available_variable_observation_ids: tuple[str, ...],
) -> tuple[str, ...]:
    selected: list[str] = []
    for obs_id in available_variable_observation_ids:
        try:
            obs = kernel.variables.get_observation(obs_id)
        except Exception:
            continue
        if obs.variable_id in profile.watched_variable_ids:
            selected.append(obs_id)
            continue
        if profile.watched_variable_groups:
            try:
                spec = kernel.variables.get_variable(obs.variable_id)
            except Exception:
                continue
            if spec.variable_group in profile.watched_variable_groups:
                selected.append(obs_id)
    return tuple(selected)


def _select_exposures(
    kernel: Any,
    *,
    profile: AttentionProfile,
    available_exposure_ids: tuple[str, ...],
) -> tuple[str, ...]:
    selected: list[str] = []
    for exposure_id in available_exposure_ids:
        try:
            exposure = kernel.exposures.get_exposure(exposure_id)
        except Exception:
            continue
        if (
            exposure.exposure_type in profile.watched_exposure_types
            or exposure.metric in profile.watched_exposure_metrics
        ):
            selected.append(exposure_id)
    return tuple(selected)


def select_observations_for_profile(
    kernel: Any, profile: AttentionProfile, menu
) -> tuple[str, ...]:
    """Apply the v1.8.12 demo selection rule to one menu.

    The rule is **structural**, not economic:

    - signals are kept when ``signal.signal_type`` ∈
      ``profile.watched_signal_types`` OR ``signal.subject_id`` ∈
      ``profile.watched_subject_ids``;
    - variable observations are kept when their underlying
      variable's ``variable_id`` ∈ ``profile.watched_variable_ids``
      OR ``variable.variable_group`` ∈
      ``profile.watched_variable_groups``;
    - exposures are kept when ``exposure.exposure_type`` ∈
      ``profile.watched_exposure_types`` OR ``exposure.metric`` ∈
      ``profile.watched_exposure_metrics``.

    Order: signals → variable observations → exposures (menu-order
    within each axis). The order is fixed so that two callers
    consuming the same menu produce identical ``selected_refs``
    tuples.

    This helper is the public entry point used by both the v1.8.12
    investor / bank attention demo and the v1.9.0 living reference
    world's per-period selection step. The function is
    **read-only**: it never mutates the kernel or any book.
    """
    return (
        _select_signals(
            kernel,
            profile=profile,
            available_signal_ids=menu.available_signal_ids,
        )
        + _select_variable_observations(
            kernel,
            profile=profile,
            available_variable_observation_ids=(
                menu.available_variable_observation_ids
            ),
        )
        + _select_exposures(
            kernel,
            profile=profile,
            available_exposure_ids=menu.available_exposure_ids,
        )
    )


# Backwards-compatible private alias. v1.8.12's
# run_investor_bank_attention_demo calls this name; keep it so
# that path stays a one-liner.
_build_selected_refs = select_observations_for_profile


# ---------------------------------------------------------------------------
# Top-level helper
# ---------------------------------------------------------------------------


def run_investor_bank_attention_demo(
    kernel: Any,
    *,
    firm_id: str,
    investor_id: str,
    bank_id: str,
    as_of_date: date | str | None = None,
    phase_id: str | None = None,
    investor_profile_id: str | None = None,
    bank_profile_id: str | None = None,
    investor_menu_id: str | None = None,
    bank_menu_id: str | None = None,
    investor_selection_id: str | None = None,
    bank_selection_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> InvestorBankAttentionDemoResult:
    """
    Build per-actor menus + selections for an investor and a bank.

    Flow:

    1. Resolve ``as_of_date`` (argument or kernel clock).
    2. Register (or reuse) the investor's and the bank's
       ``AttentionProfile`` with v1.8.12's variable / exposure
       hooks pre-populated to sensible defaults.
    3. For each actor, call
       ``kernel.observation_menu_builder.build_menu(...)`` with a
       deterministic ``request_id`` so the resulting ``menu_id``
       is stable across runs.
    4. Apply the structural selection rule (see module docstring)
       against each menu and persist a
       :class:`SelectedObservationSet` per actor through
       ``kernel.attention.add_selection``.

    Side effects (the only writes the helper performs):

    - Up to two ``AttentionProfile`` insertions (idempotent: skipped
      if already registered).
    - Two ``ObservationMenu`` insertions through
      ``AttentionBook.add_menu`` (each emits the existing
      ``OBSERVATION_MENU_CREATED`` ledger entry).
    - Two ``SelectedObservationSet`` insertions through
      ``AttentionBook.add_selection`` (each emits the existing
      ``OBSERVATION_SET_SELECTED`` ledger entry).

    Nothing else is mutated. v1.8.12 deliberately does not run
    review routines, recompute valuations / prices / DSCR / LTV,
    move ownership, change contracts, or update institutions —
    that work belongs to v1.8.13 / v1.9 and beyond.
    """
    for name, value in (
        ("firm_id", firm_id),
        ("investor_id", investor_id),
        ("bank_id", bank_id),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} is required and must be a non-empty string")

    if kernel.observation_menu_builder is None:
        raise ValueError(
            "kernel.observation_menu_builder is None; "
            "construct WorldKernel through __post_init__ or wire it explicitly."
        )

    iso_as_of = _coerce_iso_date(as_of_date, kernel=kernel)

    investor_profile = register_investor_attention_profile(
        kernel,
        investor_id=investor_id,
        profile_id=investor_profile_id,
        firm_id=firm_id,
    )
    bank_profile = register_bank_attention_profile(
        kernel,
        bank_id=bank_id,
        profile_id=bank_profile_id,
        firm_id=firm_id,
    )

    # 3) Menus.
    investor_menu_request = ObservationMenuBuildRequest(
        request_id=_default_menu_request_id(investor_id, iso_as_of),
        actor_id=investor_id,
        as_of_date=iso_as_of,
        phase_id=phase_id,
        metadata={"menu_id": investor_menu_id} if investor_menu_id else {},
    )
    bank_menu_request = ObservationMenuBuildRequest(
        request_id=_default_menu_request_id(bank_id, iso_as_of),
        actor_id=bank_id,
        as_of_date=iso_as_of,
        phase_id=phase_id,
        metadata={"menu_id": bank_menu_id} if bank_menu_id else {},
    )

    investor_build = kernel.observation_menu_builder.build_menu(
        investor_menu_request
    )
    bank_build = kernel.observation_menu_builder.build_menu(bank_menu_request)

    investor_menu = kernel.attention.get_menu(investor_build.menu_id)
    bank_menu = kernel.attention.get_menu(bank_build.menu_id)

    # 4) Selections.
    investor_refs = _build_selected_refs(kernel, investor_profile, investor_menu)
    bank_refs = _build_selected_refs(kernel, bank_profile, bank_menu)

    investor_selection = SelectedObservationSet(
        selection_id=(
            investor_selection_id
            or _default_selection_id(investor_id, iso_as_of)
        ),
        actor_id=investor_id,
        attention_profile_id=investor_profile.profile_id,
        menu_id=investor_menu.menu_id,
        selected_refs=investor_refs,
        selection_reason="profile_match",
        as_of_date=iso_as_of,
        phase_id=phase_id,
        status="completed" if investor_refs else "empty",
    )
    bank_selection = SelectedObservationSet(
        selection_id=(
            bank_selection_id or _default_selection_id(bank_id, iso_as_of)
        ),
        actor_id=bank_id,
        attention_profile_id=bank_profile.profile_id,
        menu_id=bank_menu.menu_id,
        selected_refs=bank_refs,
        selection_reason="profile_match",
        as_of_date=iso_as_of,
        phase_id=phase_id,
        status="completed" if bank_refs else "empty",
    )

    kernel.attention.add_selection(investor_selection)
    kernel.attention.add_selection(bank_selection)

    investor_set = set(investor_refs)
    bank_set = set(bank_refs)
    shared = tuple(r for r in investor_refs if r in bank_set)
    investor_only = tuple(r for r in investor_refs if r not in bank_set)
    bank_only = tuple(r for r in bank_refs if r not in investor_set)

    return InvestorBankAttentionDemoResult(
        investor_profile_id=investor_profile.profile_id,
        bank_profile_id=bank_profile.profile_id,
        investor_menu_id=investor_menu.menu_id,
        bank_menu_id=bank_menu.menu_id,
        investor_selection_id=investor_selection.selection_id,
        bank_selection_id=bank_selection.selection_id,
        investor_selected_refs=investor_refs,
        bank_selected_refs=bank_refs,
        shared_refs=shared,
        investor_only_refs=investor_only,
        bank_only_refs=bank_only,
        as_of_date=iso_as_of,
        metadata=dict(metadata or {}),
    )
