You are Claude Code working on the FWE / JFWE repository.

You are allowed to work serially from v1.24.0 through v1.25.last, but you must obey the milestone gates below.

Critical instruction:
Do not implement everything in one commit.
Do not skip freeze milestones.
Do not combine v1.24 and v1.25 in one PR.
Do not start v2 Japan calibration implementation.
Do not use real data.
Do not add Japan calibration.
Do not add investment advice.
Do not add price prediction.
Do not add trading, orders, execution, clearing, or settlement.
Do not add LLM execution.
Do not add actor decisions.
Do not add bank approval logic.
Do not add StressInteractionRule auto-inference.
Do not infer amplify / dampen / offset / coexist.
Do not add aggregate / composite / net / dominant stress outputs.
Do not use GICS / MSCI / S&P / FactSet / Bloomberg / Refinitiv / TOPIX / Nikkei / JPX as dependencies or taxonomies.

Current state:
v1.23 is expected to be frozen as:
- v1.23.1 substrate hardening
- v1.23.2 validation foundation
- v1.23.3 attention-crowding / uncited-stress case study
- v1.23.last freeze

If v1.23.last is not yet committed and passing, stop and ask for confirmation.

Public v1.x boundary:
FWE v1.x is a jurisdiction-neutral synthetic financial world engine.
It is audit-first.
It uses append-only ledger records, context surfaces, actor attention, stress programs, read-only projections, and downstream citation trails.
It is not a prediction engine.
It is not investment advice.
It is not Japan-calibrated.
It does not use real data.
It does not execute LLM reasoning.
It does not perform actor decisions.

Overall target:
v1.24 = Manual Annotation Layer
v1.25 = Institutional Investor Mandate / Benchmark Pressure
After v1.25.last, only prepare v2.0 Japan public calibration design. Do not implement v2.0 data ingestion.

============================================================
GLOBAL AUTOPILOT RULES
============================================================

1. Every milestone must be strictly serial.
2. Each milestone must end with:
   - pytest -q
   - python -m compileall -q world spaces tests examples
   - ruff check .
3. Do not push if tests fail.
4. Do not continue to next milestone if any boundary is violated.
5. Each milestone must produce a final report with:
   - final test count
   - changed files
   - digest status
   - scope kept / scope rejected
   - next milestone recommendation
6. Existing canonical digests must remain byte-identical unless an explicit new fixture is introduced and pinned.
7. No milestone may introduce price, forecast, expected return, target price, trading, recommendation, real data, Japan calibration, LLM execution, or actor decisions.
8. If unsure, stop and write a design note rather than implementing.

============================================================
v1.24 — MANUAL ANNOTATION LAYER
============================================================

Purpose:
Allow a human reviewer to attach explicit, auditable annotations to existing citation graph records.

Manual annotation is NOT:
- auto-inference
- causal proof
- price prediction
- stress interaction engine
- LLM reasoning
- investment advice
- a source-of-truth world mutation

Manual annotation IS:
- a human-authored, append-only audit note over existing record ids
- read-only with respect to the world
- a way to mark citation gaps, shared review frames, partial application notes, and reviewer follow-up needs

Allowed annotation ideas:
- same_review_frame
- shared_context_surface
- uncited_stress_candidate
- partial_application_note
- citation_gap_note
- needs_followup_review
- reviewer_disagreement_placeholder
- unknown

Forbidden annotation ideas:
- amplify
- dampen
- offset
- coexist
- causal_effect
- impact_score
- risk_score
- forecast
- recommendation
- expected_return
- target_price
- buy
- sell
- order
- trade
- execution
- investment_advice
- real_data
- japan_calibration
- llm_output

------------------------------------------------------------
v1.24.0 — Manual Annotation Design, docs-only
------------------------------------------------------------

Goal:
Design the Manual Annotation Layer.

Do not implement runtime code.

Deliverables:
- docs/v1_24_manual_annotation_layer.md
- docs/world_model.md update
- README roadmap update if needed

Design must specify:
1. What manual annotation is.
2. What it is not.
3. Why v1.24 follows v1.23 validation foundation.
4. ManualAnnotationRecord shape.
5. ManualAnnotationBook shape.
6. Read-only annotation readout.
7. Optional static UI display in v1.24.3.
8. Boundary flags.
9. Forbidden tokens.
10. Tests for v1.24.1 / v1.24.2 / v1.24.3.
11. Freeze plan.

Proposed dataclass shape:

ManualAnnotationRecord
- annotation_id: str
- annotation_scope_label: str
- annotation_label: str
- cited_record_ids: tuple[str, ...]
- source_kind: str = "human"
- reasoning_mode: str = "human_authored"
- reviewer_role_label: str
- case_study_id: str | None
- created_for_record_id: str | None
- note_text: str | None
- boundary_flags: Mapping[str, bool]
- metadata: Mapping[str, Any]

Design constraints:
- note_text is optional.
- note_text must be forbidden-token scanned.
- note_text is not source-of-truth.
- cited_record_ids must be existing plain ids if kernel context is available.
- annotation must never mutate cited records.
- annotation must never trigger downstream actor behavior.
- annotation must never be generated automatically.
- annotation must never be LLM-authored in public v1.x.

Run:
- pytest -q
- compileall
- ruff

Expected:
- docs-only
- no digests move
- no runtime modules touched

Commit and push as v1.24.0.

------------------------------------------------------------
v1.24.1 — Manual Annotation Storage
------------------------------------------------------------

Goal:
Implement storage only.

Required files:
- world/manual_annotations.py
- tests/test_manual_annotations.py

Implement:
- ManualAnnotationRecord
- ManualAnnotationBook
- exceptions:
  - DuplicateManualAnnotationError
  - UnknownManualAnnotationError
- optional constants:
  - MANUAL_ANNOTATION_SOURCE_KIND = "human"
  - MANUAL_ANNOTATION_REASONING_MODE = "human_authored"

RecordType:
Add only if project convention requires ledger storage:
- MANUAL_ANNOTATION_RECORDED

Rules:
- append-only
- one ledger record per add_annotation(...)
- duplicate emits no extra ledger record
- no source-of-truth mutation
- no apply_stress_program
- no apply_scenario_driver
- no stress interaction
- no UI
- no export yet
- no LLM execution
- no automatic annotation helper

Closed sets:
Keep small.
Do not introduce broad taxonomies.

Potential labels:
ANNOTATION_SCOPE_LABELS:
- stress_readout
- stress_program_application
- scenario_context_shift
- validation_report
- case_study
- citation_graph
- unknown

ANNOTATION_LABELS:
- same_review_frame
- shared_context_surface
- uncited_stress_candidate
- partial_application_note
- citation_gap_note
- needs_followup_review
- reviewer_disagreement_placeholder
- unknown

SOURCE_KIND_LABELS:
- human

REASONING_MODE_LABELS:
- human_authored

Tests:
1. test_manual_annotation_record_validates_required_fields
2. test_manual_annotation_rejects_auto_or_llm_source_kind
3. test_manual_annotation_rejects_forbidden_field_names
4. test_manual_annotation_rejects_forbidden_metadata_keys
5. test_manual_annotation_rejects_forbidden_note_text
6. test_manual_annotation_book_add_get_list_snapshot
7. test_duplicate_annotation_emits_no_extra_ledger_record
8. test_annotation_storage_does_not_mutate_source_of_truth_books
9. test_annotation_storage_does_not_call_apply_helpers
10. test_world_kernel_manual_annotations_empty_by_default
11. test_existing_digests_unchanged_with_empty_annotation_book

Run all gates.
Commit and push as v1.24.1.

------------------------------------------------------------
v1.24.2 — Manual Annotation Readout / Validation Hooks
------------------------------------------------------------

Goal:
Expose manual annotations as read-only audit overlays.

Required files:
- world/manual_annotation_readout.py
- tests/test_manual_annotation_readout.py

Implement:
ManualAnnotationReadout
- readout_id
- annotation_ids
- cited_record_ids
- annotation_label_counts
- annotations_by_scope
- unresolved_cited_record_ids
- warnings
- metadata

Rules:
- read-only
- no ledger emission
- no mutation
- no automatic interpretation
- no aggregation into causal conclusions
- counts are counts of labels only, not scores
- unresolved cited ids must be visible
- note_text must not be used as source-of-truth

Validation hook:
Add a small hook into stress validation if safe:
- validation report may include manual_annotation_count
- validation report may include unresolved_annotation_citation_count
But do not make manual annotation required for existing validation.

Tests:
1. test_manual_annotation_readout_is_read_only
2. test_readout_counts_annotation_labels_without_scores
3. test_readout_surfaces_unresolved_cited_record_ids
4. test_readout_does_not_emit_ledger_records
5. test_readout_does_not_mutate_kernel
6. test_readout_does_not_infer_interactions
7. test_readout_rejects_forbidden_metadata
8. test_validation_hook_optional_and_backward_compatible
9. test_existing_validation_tests_still_pass_without_annotations

Run gates.
Commit and push as v1.24.2.

------------------------------------------------------------
v1.24.3 — Manual Annotation Export / Optional Static UI Display
------------------------------------------------------------

Goal:
Make manual annotations visible, but only as read-only audit overlays.

Decide whether to implement export only or export + UI.
Prefer export first.
If UI is implemented, keep it minimal.

Export:
- Add optional manual_annotation_readout section to RunExportBundle.
- Omit when empty to preserve existing bundle digests.
- descriptive-only fields.

Allowed export keys:
- annotation_ids
- cited_record_ids
- annotation_label_counts
- annotations_by_scope
- unresolved_cited_record_ids
- warnings

Forbidden:
- impact
- outcome
- risk_score
- forecast
- expected_return
- recommendation
- causal_effect
- amplify
- dampen
- offset
- dominant
- net
- composite

UI:
If implemented:
- no new tab
- add small “Manual annotations” panel to existing relevant sheet
- read JSON only
- no Python in browser
- no LLM
- show annotation ids, cited record ids, labels, unresolved citations
- do not show note_text prominently unless forbidden-token scanned and escaped
- textContent only for loaded values

Tests:
1. export omits manual annotations when absent
2. existing no-annotation bundle digests unchanged
3. export includes annotations when present
4. export keys descriptive-only
5. forbidden wording absent
6. UI, if touched, does not add tab
7. UI, if touched, uses textContent only
8. existing stress readout UI still renders

Run gates.
Commit and push as v1.24.3.

------------------------------------------------------------
v1.24.last — Freeze
------------------------------------------------------------

Goal:
Docs-only freeze.

Update:
- docs/v1_24_manual_annotation_layer.md
- docs/world_model.md
- README roadmap
- docs/test_inventory.md

State:
- v1.24 manual annotation layer complete
- human-authored only
- no auto inference
- no LLM
- no causal proof
- no interaction engine
- no world mutation

Run gates.
Commit and push as v1.24.last.

============================================================
v1.25 — INSTITUTIONAL INVESTOR MANDATE / BENCHMARK PRESSURE
============================================================

Purpose:
Make investor attention selection more realistic by adding mandate / benchmark / constraint context.

This layer must not create:
- trades
- orders
- portfolio allocation
- rebalancing
- overweight / underweight
- expected returns
- target weights
- buy / sell labels
- investment advice

It may create:
- investor mandate profiles
- benchmark pressure labels
- liquidity need labels
- liability horizon labels
- stewardship priority labels
- attention bias labels
- review posture conditioning labels
- read-only mandate readout

Core framing:
Mandate affects what an investor is likely to review or pay attention to.
Mandate does not decide what the investor does.

------------------------------------------------------------
v1.25.0 — Mandate / Benchmark Pressure Design, docs-only
------------------------------------------------------------

Goal:
Design the institutional investor mandate layer.

Deliverables:
- docs/v1_25_institutional_investor_mandate_benchmark_pressure.md
- docs/world_model.md update
- README roadmap update

Design:
InvestorMandateProfile
- mandate_profile_id
- investor_id
- mandate_type_label
- benchmark_pressure_label
- liquidity_need_label
- liability_horizon_label
- stewardship_priority_labels
- review_frequency_label
- concentration_tolerance_label
- visibility
- metadata

Possible labels:
mandate_type_label:
- pension_like
- insurance_like
- active_manager_like
- passive_manager_like
- sovereign_like
- endowment_like
- unknown

benchmark_pressure_label:
- none
- low
- moderate
- high
- unknown

liquidity_need_label:
- low
- moderate
- high
- unknown

liability_horizon_label:
- short
- medium
- long
- unknown

stewardship_priority_labels:
- capital_discipline
- governance_review
- climate_disclosure
- liquidity_resilience
- funding_access
- unknown

Boundary:
No portfolio allocation.
No target weights.
No benchmark tracking error values.
No expected return.
No buy/sell.
No rebalancing.
No order.
No trade.

Run gates.
Commit and push as v1.25.0.

------------------------------------------------------------
v1.25.1 — Mandate Storage
------------------------------------------------------------

Goal:
Storage only.

Required files:
- world/investor_mandates.py
- tests/test_investor_mandates.py

Implement:
- InvestorMandateProfile
- InvestorMandateBook
- DuplicateInvestorMandateProfileError
- UnknownInvestorMandateProfileError

Rules:
- append-only
- one profile per investor unless explicitly allowed by design
- no investor action
- no portfolio allocation
- no market intent generation
- no attention mutation yet
- no UI
- no export yet

RecordType:
- INVESTOR_MANDATE_PROFILE_RECORDED if convention requires

Tests:
1. validates labels
2. rejects forbidden fields
3. metadata forbidden scan
4. add/get/list/snapshot
5. duplicate behavior
6. empty-by-default kernel wiring
7. no mutation of investor intents / ownership / prices / ledgers except own storage event
8. existing digests unchanged

Run gates.
Commit and push as v1.25.1.

------------------------------------------------------------
v1.25.2 — Mandate-conditioned Attention Input Frame, read-only
------------------------------------------------------------

Goal:
Make mandate visible to attention/review selection without generating actions.

Implement carefully:
- MandateAttentionContext
or
- InvestorMandateReadout

Allowed:
- read investor mandate profile
- produce context labels
- expose which evidence dimensions become more salient
- append readout only if project convention requires, but prefer read-only

Forbidden:
- changing portfolio
- changing holdings
- creating orders
- creating investor actions
- target weights
- expected return
- recommendation

Possible fields:
- investor_id
- mandate_profile_id
- selected_attention_bias_labels
- review_context_labels
- cited_mandate_fields
- warnings
- metadata

Tests:
1. mandate readout is read-only
2. no investor action emitted
3. no portfolio mutation
4. no market order / trade wording
5. attention context labels deterministic
6. no forbidden words
7. existing stress readout still works

Run gates.
Commit and push as v1.25.2.

------------------------------------------------------------
v1.25.3 — Mandate Export / UI Reflection
------------------------------------------------------------

Goal:
Expose mandate context descriptively.

Export:
- optional investor_mandate_readout section
- omitted when empty
- descriptive-only

UI:
- no new tab
- small “Investor mandate context” panel in existing investor / universe relevant area
- show mandate type, benchmark pressure label, liquidity need label, stewardship priorities
- no performance, no allocation, no recommendation

Tests:
1. export omitted when empty
2. no-mandate bundle unchanged
3. export present when mandate exists
4. UI renders if bundle section present
5. no forbidden wording
6. no new tab
7. existing UI still renders

Run gates.
Commit and push as v1.25.3.

------------------------------------------------------------
v1.25.4 — Mandate Case Study / Demo Note
------------------------------------------------------------

Goal:
Show one read-only case where two investor archetypes review the same stress context differently because mandate context changes what they inspect.

Not allowed:
- no trade
- no order
- no allocation
- no expected return
- no benchmark outperformance
- no recommendation

Deliverables:
- docs/case_study_002_investor_mandate_attention_context.md
- optional read-only helper if needed
- tests pin deterministic output and boundary preservation

The case study should show:
- same stress readout
- two investor mandate profiles
- different selected review context labels
- no action
- no market result

Run gates.
Commit and push as v1.25.4.

------------------------------------------------------------
v1.25.last — Freeze
------------------------------------------------------------

Docs-only freeze.

Update:
- docs/v1_25_institutional_investor_mandate_benchmark_pressure.md
- docs/world_model.md
- README roadmap
- docs/test_inventory.md

State:
- v1.25 mandate / benchmark pressure complete
- it conditions attention/review context only
- no trades
- no allocations
- no recommendations
- no real data
- no Japan calibration

Run gates.
Commit and push as v1.25.last.

============================================================
AFTER v1.25.last — v2 JAPAN PUBLIC CALIBRATION PREP ONLY
============================================================

Do not implement v2 in this autopilot run.

After v1.25.last, create only a docs-only design packet if time remains:

docs/v2_0_japan_public_calibration_boundary.md

Purpose:
Prepare the transition from public v1.x synthetic reference system to v2.x Japan public calibration.

Must cover:
1. What counts as public data.
2. Data license / redistribution boundary.
3. No proprietary data.
4. No paid terminal dependency.
5. No TOPIX / Nikkei / JPX / GICS dependency unless license and redistribution are explicitly designed.
6. What Japan-specific structures may be represented:
   - sectors using generic labels first
   - disclosure calendar
   - fiscal year / reporting patterns
   - broad institution types
   - public policy / macro labels
7. What must remain forbidden:
   - real company recommendations
   - price prediction
   - trading advice
   - non-public data
   - proprietary calibration
8. Difference between:
   - v2 Japan public calibration
   - v3 Japan proprietary calibration

Do not ingest data.
Do not download data.
Do not add datasets.
Do not add real company names unless design explicitly scopes a later public-data phase and licensing is clear.

Run gates.
Commit only if docs-only and safe.
Otherwise stop after v1.25.last.

============================================================
FINAL REPORT REQUIRED
============================================================

At the end, produce a final report:

- milestones completed
- commits pushed
- final test count
- validation commands and results
- digest status
- files changed by milestone
- any skipped milestone and why
- any intentional exceptions
- recommended next step toward v2 Japan public calibration