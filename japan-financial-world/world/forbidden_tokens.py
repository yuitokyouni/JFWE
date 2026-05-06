"""
v1.23.1 — Composable forbidden-name vocabulary.

Single source of truth for the forbidden-name frozensets that
v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0 layers each declare
in-place. v1.23.1 decomposes those flat sets into:

- a ``FORBIDDEN_TOKENS_BASE`` carrying the v1.18.0
  actor-decision / canonical-judgment / price / forecast /
  advice / real-data / Japan / LLM tokens that EVERY
  downstream layer forbids;
- per-milestone ``*_DELTA`` frozensets carrying the additions
  each milestone introduced;

and re-composes them under the existing public names. The
module is **additive** at v1.23.1: it does not loosen any
existing forbidden set. The composed run-export set
strictly **closes a leak** (it adds the v1.21.0a stress
tokens that the v1.19.0-era run-export set did not yet
forbid); the composed stress-program / -application /
-readout sets are byte-identical to the existing in-place
declarations.

Discipline:

- ``FORBIDDEN_TOKENS_BASE`` is a subset of every composed
  forbidden set.
- Every ``*_DELTA`` is disjoint from ``FORBIDDEN_TOKENS_BASE``
  (no token appears in both BASE and a delta).
- Adding a forbidden token at a future milestone goes into a
  *new* delta, not into BASE — so composition propagates
  automatically and downstream layers do not regress.

The module is **runtime-book-free**: it imports nothing from
the rest of the codebase and emits no ledger record / dataclass
/ closed-set vocabulary. Tests pin:

- composed sets contain all v1.21.0a stress tokens;
- composed stress-program / -application / -readout sets
  match the existing in-place declarations;
- composed run-export set composes the v1.21.0a stress tokens
  (the leak-fix) and is a superset of the existing in-place
  declaration in ``world/run_export.py``;
- existing test fixtures have zero active forbidden-token
  violations against the composed sets (dry-run scan).
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# BASE — v1.18.0 actor-decision / canonical-judgment / price /
# forecast / advice / real-data / Japan / LLM tokens that EVERY
# downstream layer forbids.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_BASE: frozenset[str] = frozenset(
    {
        # v1.18.0 actor-decision / canonical-judgment names
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        # bare trading verbs / surfaces (caught at exact key
        # equality; substring matches in legitimate label
        # values like ``attention_amplify`` are out of scope)
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        # price / forecast / advice
        "price",
        "market_price",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        # real-data / Japan-calibration / LLM execution
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
    }
)


# ---------------------------------------------------------------------------
# v1.19.0 RUN_EXPORT delta — extra tokens specific to the
# v1.19.0 run-export bundle layer (price-prediction language,
# valuation-target tokens, real-price-series tokens not yet
# named at v1.18.0).
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA: frozenset[str] = frozenset(
    {
        "predicted_path",
        "forecast_index",
        "investment_recommendation",
        "price_prediction",
        "real_price_series",
        "actual_price",
        "quoted_price",
        "last_trade",
        "nav",
        "index_value",
        "benchmark_value",
        "valuation_target",
    }
)


# ---------------------------------------------------------------------------
# v1.19.3 / v1.20.0 stress-layer real-indicator + real-issuer +
# licensed-taxonomy delta — added to the v1.21.0a stress
# program forbidden set so a stress program payload cannot
# smuggle a real Japan indicator value, a real issuer name,
# or a licensed-taxonomy token. These tokens were declared as
# part of FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES at v1.21.0a;
# v1.23.1 names them as a separate delta for clarity.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA: frozenset[str] = (
    frozenset(
        {
            "real_indicator_value",
            "cpi_value",
            "gdp_value",
            "policy_rate",
            "real_release_date",
        }
    )
)


FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA: frozenset[str] = frozenset(
    {
        "real_company_name",
        "real_sector_weight",
        "market_cap",
        "leverage_ratio",
        "revenue",
        "ebitda",
        "net_income",
        "real_financial_value",
    }
)


FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA: frozenset[str] = (
    frozenset(
        {
            "gics",
            "msci",
            "factset",
            "bloomberg",
            "refinitiv",
            "topix",
            "nikkei",
            "jpx",
            "sp_index",
        }
    )
)


# ---------------------------------------------------------------------------
# v1.21.0a STRESS delta — the v1.21.0a stress / aggregate /
# composite / net / dominant / interaction tokens. This is the
# delta the v1.23.1 leak-fix composes into the run-export
# forbidden set so that a non-stress bundle section
# (``manifest`` / ``overview`` / ``timeline`` / etc.) cannot
# smuggle a stress-shaped key that the v1.21.0a discipline
# forbids at the stress-layer surface.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA: frozenset[str] = frozenset(
    {
        # v1.21.0a forecast-shaped stress tokens
        "stress_magnitude",
        "stress_magnitude_in_basis_points",
        "stress_magnitude_in_percent",
        "stress_probability_weight",
        "expected_field_response",
        "expected_stress_path",
        "stress_forecast_path",
        "stress_buy_signal",
        "stress_sell_signal",
        "stress_target_price",
        "stress_expected_return",
        "stress_outcome_label",
        # v1.21.0a aggregate / composite / net / dominant
        # composition-reduction tokens
        "aggregate_shift_direction",
        "aggregate_context_label",
        "combined_context_label",
        "combined_shift_direction",
        "net_pressure_label",
        "net_stress_direction",
        "composite_risk_label",
        "composite_market_access_label",
        "dominant_stress_label",
        "total_stress_intensity",
        "stress_amplification_score",
        "predicted_stress_effect",
        "projected_stress_effect",
        # v1.21.0a interaction-label vocabulary (deferred to
        # v1.22+ as manual_annotation only — never inferred by
        # any helper, classifier, closed-set rule table, or
        # LLM)
        "interaction_label",
        "composition_label",
        "output_context_label",
        "dominant_shift_direction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
        # v1.21.0a generic real_data label (not in BASE because
        # the v1.18.0 BASE only names ``real_data_value``)
        "real_data",
    }
)


# ---------------------------------------------------------------------------
# v1.22.0 EXPORT delta — the v1.22.0 outcome / impact /
# amplification / dampening / dominant-stress / net-pressure /
# composite-risk descriptive-token language that the v1.22.1
# stress-readout export section forbids in addition to the
# stress field-name discipline.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA: frozenset[str] = frozenset(
    {
        # v1.22.0 outcome / impact / risk-score language
        "impact",
        "outcome",
        "risk_score",
        "amplification",
        "dampening",
        "offset_effect",
        "dominant_stress",
        "net_pressure",
        "composite_risk",
        # forecast / prediction / expected_response
        "forecast",
        "expected_response",
        "prediction",
        # v1.21.0a aggregate / combined / net / dominant /
        # composite descriptive tokens (used as v1.22.1
        # forbidden-token boundary scan terms; the
        # ``*_label`` / ``*_score`` variants live in the
        # v1.21.0a stress delta above)
        "aggregate",
        "combined",
        "net",
        "dominant",
        "composite",
    }
)


# ---------------------------------------------------------------------------
# v1.24.0 MANUAL ANNOTATION delta — anti-claim tokens specific
# to the v1.24 manual-annotation interaction layer.
#
# v1.24's binding discipline: manual annotations are
# human-authored, append-only audit overlays on existing
# citation-graph records. The v1.24.0 delta forbids any token
# that would imply automatic / LLM-authored / interaction-
# inference / causal-proof / impact-scoring semantics. The
# combined ``FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES`` set
# composes BASE + v1.19.0 / v1.19.3 / v1.20.0 / v1.21.0a /
# v1.22.0 deltas + this v1.24.0 delta.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA: frozenset[str] = (
    frozenset(
        {
            # v1.24.0 anti-claim tokens — prevent any field /
            # label / value / metadata key / payload key /
            # note_text token from implying that an annotation
            # was emitted by anything other than a human
            # reviewer.
            "auto_annotation",
            "auto_inference",
            "automatic_review",
            "automatic_annotation",
            "llm_annotation",
            "llm_authored",
            "inferred_interaction",
            "interaction_engine_output",
            "interaction_engine_label",
            "causal_effect",
            "causal_proof",
            "impact_score",
            "actor_decision",
        }
    )
)


# ---------------------------------------------------------------------------
# v1.25.0 INVESTOR MANDATE / BENCHMARK PRESSURE delta — anti-
# claim tokens specific to the v1.25 institutional investor
# mandate / benchmark-pressure layer.
#
# v1.25's binding discipline: a mandate profile conditions
# investor attention / review context only — never produces a
# trade, an allocation, a target weight, an expected return,
# a recommendation, or any actor decision. The v1.25.0 delta
# forbids any token that would imply portfolio / allocation /
# performance / benchmark-number / mandate-as-action
# semantics. The combined
# ``FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES`` set composes
# BASE + v1.19.0 / v1.19.3 / v1.20.0 / v1.21.0a / v1.22.0 /
# v1.24.0 deltas + this v1.25.0 delta.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA: frozenset[str] = (
    frozenset(
        {
            # v1.25.0 portfolio / allocation language
            "portfolio_allocation",
            "target_weight",
            "overweight",
            "underweight",
            "rebalance",
            "rebalancing",
            "weight_change",
            "allocation_band",
            # v1.25.0 benchmark-number / performance language
            "tracking_error_value",
            "tracking_error_basis_points",
            "benchmark_weight",
            "benchmark_value",
            "active_share",
            "alpha",
            "performance",
            "expected_alpha",
            # v1.25.0 explicit mandate-as-action prohibitions
            "mandate_action",
            "mandate_decision",
            "mandate_buy_signal",
            "mandate_sell_signal",
        }
    )
)


# ---------------------------------------------------------------------------
# v1.26.0 UNIVERSE / CALENDAR delta — generic, country-neutral
# substrate primitives. Hard-forbids event-to-price /
# earnings-surprise / event-study language; hard-forbids real-
# data adapter names; hard-forbids portfolio / index weight
# tokens.
# ---------------------------------------------------------------------------


FORBIDDEN_TOKENS_V1_26_0_UNIVERSE_CALENDAR_DELTA: frozenset[str] = (
    frozenset(
        {
            # v1.26.0 calendar / event-as-action prohibitions
            "earnings_surprise",
            "earnings_beat",
            "earnings_miss",
            "event_study_alpha",
            "event_window_return",
            "post_event_drift",
            "calendar_arbitrage",
            # v1.26.0 real-data / Japan-specific adapter
            # prohibitions
            "edinet",
            "edinet_xbrl",
            "edinet_filing_id",
            "j_quants",
            "tdnet",
            "fsa_filing",
            # v1.26.0 universe-as-portfolio prohibitions
            "universe_weight",
            "constituent_weight",
            "index_weight_change",
            "rebalance_event",
        }
    )
)


# ---------------------------------------------------------------------------
# Composed canonical sets
#
# These are the canonical re-compositions that the existing
# in-place forbidden frozensets (in ``world/stress_programs.py``,
# ``world/stress_applications.py``, ``world/stress_readout.py``,
# ``world/run_export.py``) are pinned against by v1.23.1
# tests. The composed run-export set strictly closes the
# v1.19.0 leak by adding the v1.21.0a stress tokens; the
# composed stress-layer sets are byte-identical to the
# existing in-place declarations.
# ---------------------------------------------------------------------------


# The v1.21.0a stress program / application / readout
# forbidden set — composes BASE with the v1.19.3 real-
# indicator delta, the v1.20.0 real-issuer + licensed-
# taxonomy deltas, and the v1.21.0a stress delta. Equal to
# the in-place declarations in
# ``world/stress_programs.py:FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES``,
# ``world/stress_applications.py:FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES``,
# and
# ``world/stress_readout.py:FORBIDDEN_STRESS_READOUT_FIELD_NAMES``.
FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
)


FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
)


FORBIDDEN_STRESS_READOUT_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES
)


# The v1.22.1 stress-readout export forbidden-token set —
# composes BASE with the v1.22.0 outcome / impact delta and
# the v1.21.0a stress delta. The composed set is a SUPERSET
# of the in-place declaration in
# ``world/run_export.py:FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS``;
# the in-place set already covers the v1.22.0 / v1.21.0a
# tokens that v1.22.1 actually scans against, so the in-place
# set remains the runtime authority while the composed set
# documents the canonical superset.
FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
)


# The v1.19.0 run-export forbidden-name set — composes BASE
# with the v1.19.0 run-export delta AND the v1.21.0a stress
# delta (the v1.23.1 leak-fix). The composed set is a
# strict superset of the in-place declaration in
# ``world/run_export.py:FORBIDDEN_RUN_EXPORT_FIELD_NAMES``;
# the v1.23.1 test
# ``test_run_export_forbidden_set_composes_stress_tokens``
# pins this composition. The in-place declaration remains the
# runtime authority at v1.23.1 (a future v1.23.x.x sub-
# milestone may migrate the in-place declaration to import
# from this module under a fresh design pin); the composed
# set documents the canonical leak-fixed superset.
FORBIDDEN_RUN_EXPORT_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
)


# The v1.24.0 manual-annotation forbidden-name set — composes
# BASE with the v1.19.0 / v1.19.3 / v1.20.0 / v1.21.0a /
# v1.22.0 deltas plus the v1.24.0 manual-annotation delta.
# v1.24.1 storage scans every dataclass field name, payload
# key, metadata key, label value, and optional ``note_text``
# value against this composed set at construction time.
FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA
)


# The v1.25.0 investor-mandate forbidden-name set — composes
# BASE with the v1.19.0 / v1.19.3 / v1.20.0 / v1.21.0a /
# v1.22.0 / v1.24.0 deltas plus the v1.25.0 mandate delta.
# v1.25.1 storage scans every dataclass field name, payload
# key, metadata key, and label value against this composed
# set at construction time.
FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA
    | FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA
)


# v1.26.0 universe / calendar substrate forbidden-name set —
# composes the v1.25.0 canonical set with the v1.26.0 delta.
# v1.26.1 / v1.26.2 / v1.26.3 / v1.26.4 storage + readout +
# export scan every dataclass field name, payload key,
# metadata key, and label value against this composed set.
FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA
    | FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA
    | FORBIDDEN_TOKENS_V1_26_0_UNIVERSE_CALENDAR_DELTA
)


__all__ = [
    "FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES",
    "FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES",
    "FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES",
    "FORBIDDEN_RUN_EXPORT_FIELD_NAMES",
    "FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES",
    "FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES",
    "FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS",
    "FORBIDDEN_STRESS_READOUT_FIELD_NAMES",
    "FORBIDDEN_TOKENS_BASE",
    "FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA",
    "FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA",
    "FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA",
    "FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA",
    "FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA",
    "FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA",
    "FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA",
    "FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA",
    "FORBIDDEN_TOKENS_V1_26_0_UNIVERSE_CALENDAR_DELTA",
]
