# Financial World Engine (FWE) / Japan Financial World Engine (JFWE)

FWE is a public, jurisdiction-neutral **synthetic financial world**
simulation substrate. It models a financial economy through layered
"spaces" (Corporate, Banking, Investors, Exchange, Real Estate,
Information, Policy, External) coordinated by a single world kernel,
and records every state-changing event in an **append-only ledger**
that is byte-deterministic across runs and reconstructable as a
causal graph.

This is **research software**. The public v1.x line ships only a
synthetic reference world; it is not calibrated to any real economy
or institution and contains no real prices, real holdings, or real
data feeds. The repository keeps its legacy directory name
`japan-financial-world/` for git history; renaming is a separate
migration.

---

## 1. What FWE is

FWE is an **audit-first** financial-world engine. Each layer is
designed so that:

- Every state-changing record is written to an **append-only
  ledger**, with stable world identifiers and explicit source /
  target citations.
- Every output is a **deterministic function of inputs**: same
  fixture → same records → same SHA-256 `living_world_digest`.
- Every actor decision is **explicit, traceable, and bounded**:
  a closed set of `reasoning_mode` values, a closed set of
  evidence reference ids, and explicit `unresolved_ref_count` /
  `boundary_flags` audit fields on every reasoning record.
- Every action follows a **four-property contract**: explicit
  inputs, explicit outputs, ledger record, no cross-space
  mutation.

The current concrete capabilities at v1.22.last:

- An **endogenous routine + heterogeneous attention chain** that
  produces auditable ledger traces from internal cycles —
  corporate quarterly reporting, **actor attention** building
  with a finite budget, and review routines — without external
  shocks.
- A **scenario-driver library** (v1.18) that lets a caller apply
  a synthetic stimulus to the world by emitting append-only
  context-shift records that cite the driver. The driver is the
  stimulus; nothing in the engine produces the *response*.
- A **monthly reference universe** (v1.20): 12 monthly periods
  × 11 generic sectors × 11 representative synthetic firm
  profiles × 4 investor archetypes × 3 bank archetypes × 51
  synthetic information arrivals from a jurisdiction-neutral
  release calendar.
- A **stress composition layer** (v1.21): one `StressProgramTemplate`
  + up to three `StressStep` entries → a thin
  `apply_stress_program(...)` orchestrator that walks the steps
  and reuses the v1.18.2 `apply_scenario_driver(...)` helper →
  a **read-only multiset projection** (`StressFieldReadout`)
  describing what was emitted on each **context surface**, in
  what direction, by which scenario family → a deterministic
  markdown summary suitable for an audit note.
- A **CLI export bundle** (v1.19.2 / v1.20.4) and a **static
  HTML analyst workbench** (v1.18.4 / v1.19.4 / v1.20.5) that
  loads the bundle locally — the browser never executes Python,
  never calls a backend, never writes files.

---

## 2. What FWE is not

FWE is **not**:

- A price-prediction engine. There is no price formation, no
  market microstructure, no order matching, no expected return,
  no target price.
- A forecasting model. There is no forecast path, no scenario
  probability, no expected response.
- A causal-proof engine. The ledger records *what was emitted*
  and *which records cite which sources*; it does not claim
  that any input *causes* any output in the real world.
- An interaction inference engine. Overlapping stresses are
  preserved as an ordered multiset on each context surface;
  the engine never auto-classifies them as
  `amplify` / `dampen` / `offset` / `coexist`.
- A composition reducer. There is no `aggregate_*` /
  `combined_*` / `net_*` / `dominant_*` / `composite_*`
  field anywhere in the v1.21 surface.
- An investment system. No trading, no order, no execution, no
  clearing, no settlement, no financing execution, no firm
  decision, no investor action, no bank approval logic, no
  investment advice.
- A real-data pipeline. No real prices, no real holdings, no
  real institutional identifiers, no licensed taxonomies, no
  paid feeds, no client communications.
- A Japan-calibrated model. v1.x is fully jurisdiction-neutral.
  Japan calibration begins in v2.x (public data) and v3.x
  (proprietary data). Any reference to BOJ / MUFG / GPIF /
  Toyota / TSE / TOPIX / Nikkei / JPX in the v1.x docs appears
  only to mark what is *prohibited* in v1.x or *deferred* to
  v2.x / v3.x.
- An LLM-driven system. No LLM execution at runtime; no LLM
  prose accepted as source-of-truth. The
  `reasoning_slot = "future_llm_compatible"` marker is an
  architectural commitment, not a runtime capability.

---

## 3. Why this exists

The public motivation is narrow and structural: most production
financial systems do not expose a single, append-only causal trace
that a reviewer who has never seen the codebase can read end-to-end.
FWE is an attempt to make the *engine* legible — to fix the
substrate before any layer that produces a market view sits on top
of it.

That goal implies four hard discipline rules:

1. **Audit-first, behavior-second.** Storage shape, citation
   shape, and ledger shape are designed before any actor
   behavior is written.
2. **Append-only ledger.** Pre-existing source-of-truth books
   (`PriceBook`, `ContractBook`, `ConstraintBook`,
   `OwnershipBook`, …) are never mutated by a later layer; new
   information is added as new records that cite the originals.
3. **Closed-set vocabularies.** Every label that influences a
   downstream record (sensitivity rung, severity, direction,
   surface, family) is drawn from an explicit frozenset
   enforced at construction time.
4. **Boundary as code.** Forbidden tokens (real institutions,
   real taxonomies, price-formation language, interaction-
   inference language) are scanned in tests; a regression that
   smuggles one in fails CI.

The audit value of v1.21 is in the **downstream citation trail**
— per-program / per-step plain-id citations + per-shift surface /
direction / family multisets + per-step resolution state +
warnings — not in any reduction or interpretive label.

---

## 4. Current milestone: v1.27.last

**v1.27.last Generic Strategic Relationship Network +
Annotation Provenance Hardening freeze (shipped, docs-
only).** Closes the v1.27 sequence — and with it, the
**last generic substrate addition** in public v1.x. v1.27
adds two independent primitives: (1) a generic, country-
neutral strategic relationship record type
(`strategic_holding_like` / `supplier_customer_like` /
`group_affiliation_like` / `lender_relationship_like` /
`governance_relationship_like` /
`commercial_relationship_like` / `unknown` — all `_like`
archetype labels, no real company names, no percentages,
no voting power, no market value, no centrality score),
and (2) annotation provenance hardening over the v1.24
manual-annotation surface (pseudonymous reviewer-role /
authority / audit-context companion records, anti-email-
leak guard rejecting any `@` in `annotator_id_label`, no
real-person identity, no compliance claim, no LLM
authoring). v1.27 is **NOT Japan calibration**, **NOT** a
real-data adapter, **NOT** a real-company relationship
claim, **NOT** an ownership-percentage / voting-power /
market-value / centrality / systemic-importance surface,
**NOT** a real-person identity / compliance attestation /
LLM authoring surface. The next milestone is **v2.0
Japan Public Calibration Boundary Design** (docs-only).

Shipped runtime / UI / loop / settlement set:

- **Runtime milestone — v1.9.last public prototype.**
- **UI prototype — v1.20.5 static workbench**
  (with the v1.22.2 Active Stresses strip).
- **Frozen loop — v1.16.last closed-loop freeze**
  + **v1.12.last endogenous attention loop freeze**.
- **Settlement substrate — v1.13.last generic
  central-bank settlement infrastructure freeze.**

v1.27 sequence:

| Milestone | Surface |
| --------- | ------- |
| v1.27.0 | Docs-only design pin in [`docs/v1_27_generic_relationship_network_annotation_provenance.md`](japan-financial-world/docs/v1_27_generic_relationship_network_annotation_provenance.md) + §136 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md). |
| v1.27.1 | `StrategicRelationshipRecord` + `StrategicRelationshipBook` storage in [`world/strategic_relationships.py`](japan-financial-world/world/strategic_relationships.py); closed-set `RELATIONSHIP_TYPE_LABELS` + `DIRECTION_LABELS` + 22 default boundary flags + `STRATEGIC_RELATIONSHIP_RECORDED` ledger event type; `strategic_relationships: StrategicRelationshipBook` field on `WorldKernel` (empty by default). **+13 tests.** |
| v1.27.2 | `StrategicRelationshipReadout` + read-only `build_strategic_relationship_readout(...)` in [`world/strategic_relationship_readout.py`](japan-financial-world/world/strategic_relationship_readout.py); optional descriptive-only `strategic_relationship_readout` payload section on `RunExportBundle` (cardinality 0 or 1; empty-by-default; omitted from JSON when empty so pre-v1.27 bundles stay byte-identical) via [`world/strategic_relationship_export.py`](japan-financial-world/world/strategic_relationship_export.py). **+13 tests.** |
| v1.27.3 | `ManualAnnotationProvenanceRecord` + `ManualAnnotationProvenanceBook` storage in [`world/manual_annotation_provenance.py`](japan-financial-world/world/manual_annotation_provenance.py); closed-set `AUTHORITY_LABELS` + `EVIDENCE_ACCESS_SCOPE_LABELS` + 22 default boundary flags + anti-email-leak guard + `MANUAL_ANNOTATION_PROVENANCE_RECORDED` ledger event type; `manual_annotation_provenance: ManualAnnotationProvenanceBook` field on `WorldKernel` (empty by default). **+11 tests.** |
| **v1.27.last** | Docs-only freeze. Final pin section §7 in [`docs/v1_27_generic_relationship_network_annotation_provenance.md`](japan-financial-world/docs/v1_27_generic_relationship_network_annotation_provenance.md); §136.6 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md); this README. |

**Pinned at v1.27.last:**

- `pytest -q`: **5113 / 5113 passing** (+37 vs v1.26.last)
- `ruff check .`: clean
- `python -m compileall -q world spaces tests examples`:
  clean
- All v1.21.last canonical living-world digests preserved
  byte-identical at every v1.27.x sub-milestone.
- Source-of-truth book mutations from v1.27.x helpers: **0**
- Ledger emissions from v1.27.x helpers (other than the
  one `STRATEGIC_RELATIONSHIP_RECORDED` /
  `MANUAL_ANNOTATION_PROVENANCE_RECORDED` event per
  caller-initiated `add_relationship` /
  `add_provenance` call): **0**
- New `RecordType` values: **2**
- New dataclasses: **3** (`StrategicRelationshipRecord`,
  `StrategicRelationshipReadout`,
  `ManualAnnotationProvenanceRecord`)
- New tabs: **0**
- Export schema changes: **1 optional /
  omitted-when-empty field**
  (`strategic_relationship_readout`)

**v1.27 closes the last generic substrate addition in
public v1.x.** The next milestone is **v2.0 — Japan
Public Calibration Boundary Design** (docs-only design
pin), which begins the explicit Japan calibration work
that v1.24 / v1.25 / v1.26 / v1.27 prepared the substrate
for.

---

### Earlier concrete code milestone: v1.25.last (frozen)

**v1.25.last Generic Institutional Investor Mandate /
Benchmark Pressure freeze (shipped, docs-only).** Closes
the v1.25 sequence as a **generic, jurisdiction-neutral
attention-context conditioning surface**. v1.25
conditions what an investor reviews — never what an
investor does. v1.25 is **NOT Japan calibration**, **NOT**
a portfolio, **NOT** a trade / order / execution surface,
**NOT** a recommendation, **NOT** an actor-behavior
trigger, **NOT** a source-of-truth mutation. v1.25
explicitly does NOT make the system Japan-ready;
that gating work is v1.26 (entity lifecycle + reporting
calendar) → v1.27 (generic strategic relationship
network) → v2.0 (Japan public calibration boundary
design only).

Shipped sequence:

| Milestone | Surface |
| --------- | ------- |
| v1.25.0 | Docs-only design pin in [`docs/v1_25_institutional_investor_mandate_benchmark_pressure.md`](japan-financial-world/docs/v1_25_institutional_investor_mandate_benchmark_pressure.md) + §134 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md). |
| v1.25.1 | `InvestorMandateProfile` + `InvestorMandateBook` storage in [`world/investor_mandates.py`](japan-financial-world/world/investor_mandates.py); closed-set vocabularies (mandate type / benchmark pressure / liquidity need / liability horizon / stewardship priority / review frequency / concentration tolerance) + 19 default boundary flags + `INVESTOR_MANDATE_PROFILE_RECORDED` ledger event type; `investor_mandates: InvestorMandateBook` field on `WorldKernel` (empty by default). **+10 tests.** |
| v1.25.2 | `InvestorMandateReadout` + read-only `build_investor_mandate_readout(...)` + deterministic markdown renderer in [`world/investor_mandate_readout.py`](japan-financial-world/world/investor_mandate_readout.py). Closed-set `MANDATE_ATTENTION_BIAS_LABELS` + `MANDATE_REVIEW_CONTEXT_LABELS`. **+8 tests.** |
| v1.25.3 | Optional descriptive-only `investor_mandate_readout` payload section on `RunExportBundle` (one entry per mandate profile; empty-by-default; omitted from JSON when empty so v1.21.last digests stay byte-identical) via [`world/investor_mandate_export.py`](japan-financial-world/world/investor_mandate_export.py) + minimal "Investor mandate context" panel inside the existing Universe sheet of [`examples/ui/fwe_workbench_mockup.html`](japan-financial-world/examples/ui/fwe_workbench_mockup.html) (no new tab; `textContent` only). **+15 tests.** |
| v1.25.4 | Read-only mandate case study showing two archetypes reviewing the same v1.21.3 stress readout differently. [`world/investor_mandate_case_study.py`](japan-financial-world/world/investor_mandate_case_study.py) + [`docs/case_study_002_investor_mandate_attention_context.md`](japan-financial-world/docs/case_study_002_investor_mandate_attention_context.md). **+8 tests.** |
| **v1.25.last** | Docs-only freeze. Final pin section §21 in [`docs/v1_25_institutional_investor_mandate_benchmark_pressure.md`](japan-financial-world/docs/v1_25_institutional_investor_mandate_benchmark_pressure.md); §134.6 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md); this README. |

**Pinned at v1.25.last:**

- `pytest -q`: **5032 / 5032 passing** (+41 vs v1.24.last)
- `ruff check .`: clean
- `python -m compileall -q world spaces tests examples`: clean
- All v1.21.last canonical living-world digests preserved
  byte-identical at every v1.25.x sub-milestone.
- Source-of-truth book mutations from v1.25.x helpers: **0**
- Ledger emissions from v1.25.x helpers (other than the one
  `INVESTOR_MANDATE_PROFILE_RECORDED` event per
  caller-initiated `add_profile` call): **0**
- New `RecordType` values: **1**
  (`INVESTOR_MANDATE_PROFILE_RECORDED`)
- New dataclasses: **2** (`InvestorMandateProfile`,
  `InvestorMandateReadout`)
- New tabs: **0**
- Export schema changes: **1 optional /
  omitted-when-empty field** (`investor_mandate_readout`)
- New investor / market intent records emitted: **0**

**v1.25 is generic and jurisdiction-neutral.** The
`_like` archetype suffix (`pension_like` /
`active_manager_like` / `sovereign_like` etc.) is binding;
none of the labels names any real-world institutional
category. The benchmark-pressure label is a closed-set
descriptive band — **no numeric tracking-error budget**.
The closed `ANNOTATION` / `MANDATE` vocabularies
explicitly exclude `amplify` / `dampen` / `offset` /
`coexist`, `portfolio_allocation` / `target_weight` /
`rebalance`, `expected_return` / `target_price` /
`forecast` / `recommendation`, and every actor-decision /
LLM / Japan-calibration token. Storage rejects all of
them at construction.

---

### Earlier concrete code milestone: v1.24.last (frozen)

**v1.24.last Manual Annotation Interaction Layer freeze
(shipped, docs-only).** Closes the v1.24 sequence as a
**human-authored, append-only audit overlay** on existing
citation-graph records (v1.21.3 stress readouts, v1.22.1
export entries, v1.23.3 case-study reports, v1.18.2
scenario applications + context shifts). v1.24 is **NOT**
auto-inference, **NOT** causal proof, **NOT** stress
interaction inference, **NOT** an actor-behavior trigger,
**NOT** a source-of-truth mutation. Storage closed-singleton
discipline (`source_kind = "human"` /
`reasoning_mode = "human_authored"`) is enforced at
construction time, not as a soft convention.

Shipped sequence:

| Milestone | Surface |
| --------- | ------- |
| v1.24.0 | Docs-only design pin in [`docs/v1_24_manual_annotation_layer.md`](japan-financial-world/docs/v1_24_manual_annotation_layer.md) + §133 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md). |
| v1.24.1 | `ManualAnnotationRecord` + `ManualAnnotationBook` storage in [`world/manual_annotations.py`](japan-financial-world/world/manual_annotations.py); closed-set vocabularies + 15 default boundary flags + `MANUAL_ANNOTATION_RECORDED` ledger event type; `manual_annotations: ManualAnnotationBook` field on `WorldKernel` (empty by default). **+16 tests.** |
| v1.24.2 | `ManualAnnotationReadout` + `build_manual_annotation_readout(...)` + deterministic markdown renderer + optional non-mandatory v1.23.2 validation hook in [`world/manual_annotation_readout.py`](japan-financial-world/world/manual_annotation_readout.py). Counts are counts, not scores. **+13 tests.** |
| v1.24.3 | Optional descriptive-only `manual_annotation_readout` payload section on `RunExportBundle` (cardinality 0 or 1; empty-by-default; omitted from JSON when empty so v1.21.last digests stay byte-identical) via [`world/manual_annotation_export.py`](japan-financial-world/world/manual_annotation_export.py) + minimal "Manual annotations" panel inside the existing Universe sheet of [`examples/ui/fwe_workbench_mockup.html`](japan-financial-world/examples/ui/fwe_workbench_mockup.html) (no new tab; `textContent` only). **+15 tests.** |
| **v1.24.last** | Docs-only freeze. Final pin section §24 in [`docs/v1_24_manual_annotation_layer.md`](japan-financial-world/docs/v1_24_manual_annotation_layer.md); §133.6 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md); this README. |

**Pinned at v1.24.last:**

- `pytest -q`: **4991 / 4991 passing** (+44 vs v1.23.last)
- `ruff check .`: clean
- `python -m compileall -q world spaces tests examples`: clean
- All v1.21.last canonical living-world digests preserved
  byte-identical at every v1.24.x sub-milestone:
  `quarterly_default` (`f93bdf3f…b705897c`),
  `monthly_reference` (`75a91cfa…91879d`),
  `scenario_monthly_reference_universe` test-fixture
  (`5003fdfa…566eb6`), v1.20.4 CLI bundle
  (`ec37715b…0731aaf`).
- Source-of-truth book mutations from v1.24.x helpers: **0**
- Ledger emissions from v1.24.x helpers (other than the one
  `MANUAL_ANNOTATION_RECORDED` event per caller-initiated
  `add_annotation` call): **0**
- New `RecordType` values: **1**
  (`MANUAL_ANNOTATION_RECORDED`)
- New dataclasses: **2** (`ManualAnnotationRecord`,
  `ManualAnnotationReadout`)
- New label vocabularies: **0** outside the four
  design-pinned closed sets (scope / label / reviewer-role
  / source-kind=human + reasoning-mode=human_authored
  singletons)
- New tabs: **0** (v1.20.5 11-tab ↔ 11-sheet bijection
  preserved)
- Export schema changes: **1 optional /
  omitted-when-empty field**
  (`manual_annotation_readout`) on `RunExportBundle`

**v1.24 is a human-authored audit overlay, not an
inference engine.** No annotation is generated by a
helper, classifier, closed-set rule table, LLM, or any
other automated layer; the storage layer rejects
non-human source-kinds at construction. The closed
`ANNOTATION_LABELS` set explicitly excludes
`amplify` / `dampen` / `offset` / `coexist` — interaction-
label inference remains forbidden across the entire
surface.

---

### Earlier concrete code milestone: v1.23.last (frozen)

**v1.23.last Substrate Hardening + Validation Foundation freeze
(shipped, docs-only).** Closes the v1.23 sequence as a
**substrate-hardening + validation-foundation milestone** with
one read-only attention-crowding / uncited-stress case study
attached. v1.23 is **NOT** a new runtime behavior, **NOT** a
new export schema, **NOT** an interaction-inference layer,
**NOT** a UI rebuild, **NOT** a validation *proof* — every pin
is a property of the audit object, never a comparison to a
real-world series.

Shipped sequence:

| Milestone | Surface |
| --------- | ------- |
| v1.23.0 | Docs-only design pin in [`docs/v1_23_substrate_hardening_validation_foundation.md`](japan-financial-world/docs/v1_23_substrate_hardening_validation_foundation.md) + §132 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md). |
| v1.23.1 | Substrate hardening: canonical digest module ([`tests/_canonical_digests.py`](japan-financial-world/tests/_canonical_digests.py)), composable forbidden-token vocabulary ([`world/forbidden_tokens.py`](japan-financial-world/world/forbidden_tokens.py)), cross-layer metadata stamp constants in [`world/stress_applications.py`](japan-financial-world/world/stress_applications.py), runtime cardinality cap `STRESS_PROGRAM_RUN_RECORD_CAP = 60` + trip-wire, test inventory currency pin. **+20 tests.** |
| v1.23.2 | Validation foundation: four pinnable categories — determinism, boundary preservation, citation completeness, partial-application visibility — across [`tests/test_validation_*.py`](japan-financial-world/tests/) + two placeholder categories (inter-reviewer reproducibility, null-model comparison) at [`tests/fixtures/inter_reviewer/`](japan-financial-world/tests/fixtures/inter_reviewer/). Companion [`docs/research_note_002_validating_stress_citation_graphs_without_price_prediction.md`](japan-financial-world/docs/research_note_002_validating_stress_citation_graphs_without_price_prediction.md). **+15 tests.** |
| v1.23.2a | Static UI behavior fix in [`examples/ui/fwe_workbench_mockup.html`](japan-financial-world/examples/ui/fwe_workbench_mockup.html): consolidated `Run` button, `Compare Regimes` no longer hijacks the active sheet, ribbon overflow hardened, version pills refreshed. **No new tab. No runtime / export change.** |
| v1.23.2b | Static UI staleness fix: inline sample fixture explicitly labelled `legacy_sample_fixture`, Meta milestone trail extended through v1.23.x, Active Stresses strip reset on Run, tooltip + Status block refresh. **+10 pin tests. No new tab. No runtime / export change.** |
| v1.23.3 | Attention-crowding / uncited-stress case study: read-only helper [`world/stress_case_study.py`](japan-financial-world/world/stress_case_study.py) + deterministic markdown renderer + companion narrative [`docs/case_study_001_attention_crowding_uncited_stress.md`](japan-financial-world/docs/case_study_001_attention_crowding_uncited_stress.md). **+9 tests.** |
| **v1.23.last** | Docs-only freeze. Final pin section §12 in [`docs/v1_23_substrate_hardening_validation_foundation.md`](japan-financial-world/docs/v1_23_substrate_hardening_validation_foundation.md); §132.9 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md); this README. |

**Pinned at v1.23.last:**

- `pytest -q`: **4947 / 4947 passing** (+54 vs v1.22.last)
- `ruff check .`: clean
- `python -m compileall -q world spaces tests examples`: clean
- All v1.21.last canonical living-world digests preserved
  byte-identical at every v1.23.x sub-milestone:
  `quarterly_default` (`f93bdf3f…b705897c`),
  `monthly_reference` (`75a91cfa…91879d`),
  `scenario_monthly_reference_universe` test-fixture
  (`5003fdfa…566eb6`), v1.20.4 CLI bundle
  (`ec37715b…0731aaf`).
- Source-of-truth book mutations from v1.23.x helpers: **0**
- Ledger emissions from v1.23.x helpers: **0**
- New `RecordType` values: **0**
- New dataclasses: **0**
- New label vocabularies: **0**
- New tabs: **0** (v1.20.5 11-tab ↔ 11-sheet bijection
  preserved)
- Export schema changes: **0**

**v1.23 ships a validation foundation, not a validation
proof.** Every v1.23.2 pin asserts a *property* of the audit
object — determinism, boundary preservation, citation
completeness, partial-application visibility — not a
predictive-accuracy claim against any external series. The
v1.23.3 case study is a research-defensible read-only
demonstration of what the citation graph reveals; it makes no
forecast / outcome / impact / recommendation claim.

---

### Earlier concrete code milestone: v1.22.last (frozen)

**v1.22.last Static UI Stress Readout Reflection freeze
(shipped, docs-only).** Closes the v1.22 sequence as a
**read-only reflection of the v1.21.3 stress readout** in the
existing v1.20.5 static workbench. v1.22 is **NOT** a new
readout, **NOT** a stress-impact view, **NOT** an interaction-
inference view, **NOT** a backend-enabled UI; it does not
introduce a new tab.

Shipped sequence:

| Milestone     | Surface                                                        |
| ------------- | -------------------------------------------------------------- |
| v1.22.0       | Docs-only design pin in [`docs/v1_22_static_ui_stress_readout_reflection.md`](japan-financial-world/docs/v1_22_static_ui_stress_readout_reflection.md) + §131 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md). |
| v1.22.1       | Descriptive-only `stress_readout` payload section on `RunExportBundle` (19-key whitelist, empty-by-default, omitted from JSON when empty). New module [`world/stress_readout_export.py`](japan-financial-world/world/stress_readout_export.py); extended [`world/run_export.py`](japan-financial-world/world/run_export.py); wired into the CLI exporter. **+13 tests.** |
| v1.22.2       | Active Stresses strip inside the existing Universe sheet, above the existing sector heatmap. Per-readout-entry rendering: `as_of_date` / template id / `resolved / total` counter / Partial application badge / context-surface · shift-direction · scenario-family multisets / Cited records / Downstream citations / Warnings / Raw canonical labels technical-details box. Read-only static rendering only — `<input type="file">` + `FileReader` + `JSON.parse`; `textContent` only. **+15 tests.** |
| **v1.22.last**| Docs-only freeze. Final pin section in [`docs/v1_22_static_ui_stress_readout_reflection.md`](japan-financial-world/docs/v1_22_static_ui_stress_readout_reflection.md); §131.9 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md); refreshed roadmap row in [`docs/v1_20_monthly_scenario_reference_universe_summary.md`](japan-financial-world/docs/v1_20_monthly_scenario_reference_universe_summary.md); this README. |

**Pinned at v1.22.last:**

- `pytest -q`: **4893 / 4893 passing** (+28 vs v1.21.last)
- `ruff check .`: clean
- `python -m compileall -q world spaces tests examples`: clean
- All v1.21.last canonical digests preserved
  byte-identical: `quarterly_default` (`f93bdf3f…b705897c`),
  `monthly_reference` (`75a91cfa…91879d`),
  `scenario_monthly_reference_universe` test-fixture
  (`5003fdfa…566eb6`), v1.20.4 CLI bundle
  (`ec37715b…0731aaf`).
- Source-of-truth book mutations: **0**
- Ledger emissions from v1.22.x helpers: **0**
- New tabs: **0** (v1.20.5 11-tab ↔ 11-sheet bijection
  preserved)

v1.22.last sits **alongside** the parallel-track freezes;
none is modified:

- **Stress composition layer — v1.21.last freeze.** Thin
  orchestrator + read-only multiset readout over the
  v1.18 / v1.20 chain. v1.22 reflects this layer; it does
  not extend it.
- **Runtime milestone — v1.9.last public prototype.** The
  runnable living reference world (3 firms × 2 investors ×
  2 banks × 3 industries × 4 quarters), reconstructable
  from the append-only ledger.
- **UI prototype — v1.20.5 static workbench.** HTML / CSS /
  JS only, loaded under `file://`; renders the v1.20.4
  bundle in 11 tabs with no backend, no fetch / XHR, no
  file-system write. v1.22.2 added the Active Stresses
  strip inside the existing Universe sheet without
  introducing a new tab.
- **Frozen loop — v1.16.last closed-loop freeze** +
  **v1.12.last endogenous attention loop freeze.** Time-
  crossing firm latent state, attention-conditioned
  mechanisms, finite **actor attention** budget with
  deterministic decay / crowding / saturation.
- **Settlement substrate — v1.13.last generic central-bank
  settlement infrastructure freeze.** Storage and labels
  only; no payment system, no real balances, no monetary-
  policy decisions.

**Earlier concrete code milestone: v1.21.last Stress Composition Layer freeze
(shipped, docs-only).** Closed the v1.21 sequence as a **thin orchestrator
+ read-only multiset readout** over the existing v1.18 / v1.20 chain.

Shipped sequence:

| Milestone     | Surface                                                        |
| ------------- | -------------------------------------------------------------- |
| v1.21.0       | Original design (superseded; preserved only in git history).   |
| v1.21.0a      | Scope correction. `StressInteractionRule` deferred to v1.22+ (or never); aggregate / composite / net / dominant fields removed; cardinality tightened (≤ 1 program / run, ≤ 3 steps / program, ≤ 60 added records). |
| v1.21.1       | `StressProgramTemplate` + `StressStep` storage in [`world/stress_programs.py`](japan-financial-world/world/stress_programs.py). +35 tests. |
| v1.21.2       | `apply_stress_program(...)` thin orchestrator in [`world/stress_applications.py`](japan-financial-world/world/stress_applications.py); walks `StressStep` entries by dense `step_index` order; reuses the v1.18.2 `apply_scenario_driver(...)` helper. +33 tests. |
| v1.21.3       | `StressFieldReadout` + `build_stress_field_readout(...)` + `render_stress_field_summary_markdown(...)` in [`world/stress_readout.py`](japan-financial-world/world/stress_readout.py). Read-only; no ledger emission. +33 tests. |
| **v1.21.last**| Docs-only freeze. Final pin section in [`docs/v1_21_stress_composition_layer.md`](japan-financial-world/docs/v1_21_stress_composition_layer.md); §130.8 in [`docs/world_model.md`](japan-financial-world/docs/world_model.md); refreshed roadmap row in [`docs/v1_20_monthly_scenario_reference_universe_summary.md`](japan-financial-world/docs/v1_20_monthly_scenario_reference_universe_summary.md); this README. |

**Pinned at v1.21.last:**

- `pytest -q`: **4865 / 4865 passing** (+101 vs v1.20.last)
- `ruff check .`: clean
- `python -m compileall -q world spaces tests examples`: clean
- `quarterly_default` `living_world_digest`:
  `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  (byte-identical to v1.20.last)
- `monthly_reference` `living_world_digest`:
  `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  (byte-identical to v1.20.last)
- `scenario_monthly_reference_universe` test-fixture
  `living_world_digest`:
  `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  (byte-identical to v1.20.last)
- v1.20.4 CLI bundle digest:
  `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
  (byte-identical to v1.20.last)
- Source-of-truth book mutations: **0**

(The full parallel-track freeze list is in §4 above under
v1.22.last; v1.21.last is itself listed there as a parallel
track.)

---

## 5. Architecture overview

FWE layers from substrate to reference behavior:

| Layer    | Owns                                                          | Examples                                                                       |
| -------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| v0.x     | Structural contract: books, projections, transport, identity, scheduler, append-only ledger, event bus, the four-property `bind()` contract | `BalanceSheetView`, `EventBus`, `DomainSpace`, `OwnershipBook`, `Clock`, `Ledger` |
| v1.0–1.7 | Reference content: valuation / institution / external-process / relationship / closed-loop record types and their books | `ValuationBook`, `InstitutionBook`, `RelationshipCapitalBook`, `ReferenceLoopRunner` |
| v1.8.x   | Endogenous activity: interactions, routines, attention, reference variables, exposures, the chain harness, the ledger trace report | `RoutineBook`, `AttentionBook`, `WorldVariableBook`, `ExposureBook`            |
| v1.9.x   | Living reference world + three review-only mechanisms + performance-boundary discipline | `run_living_reference_world`, `firm_operating_pressure_assessment`             |
| v1.10–11 | Stewardship / industry-condition / market-condition record types + capital-market readout | `IndustryConditionBook`, `MarketConditionBook`, `CapitalMarketReadoutBook`     |
| v1.12.x  | Time-crossing latent state + attention-conditioned mechanisms + finite attention budget | `FirmFinancialStateBook`, `MarketEnvironmentBook`, `EvidenceResolver`, `ActorContextFrame` |
| v1.13.x  | Generic central-bank settlement substrate (label-only)        | `InterbankLiquidityStateBook`                                                  |
| v1.16.x  | First **closed-loop** between firm decision-postures and downstream books | `FinancingPathBook`                                                            |
| v1.17.x  | Inspection layer over the v1.16 closed loop                   | display surface, audit views                                                   |
| v1.18.x  | Synthetic scenario-driver inspection layer; stimulus-only, append-only | `ScenarioDriverTemplate`, `ScenarioDriverApplicationRecord`, `ScenarioContextShiftRecord` |
| v1.19.x  | CLI run-bundle export + read-only static UI loader + monthly reference profile + information release calendar | `RunExportBundle`, `InformationReleaseCalendar`                                |
| v1.20.x  | Monthly scenario reference universe + sector / firm sensitivity surface + Universe-tab UI | `scenario_monthly_reference_universe` profile                                  |
| v1.21.x  | Stress composition layer (this milestone)                     | `StressProgramBook`, `StressApplicationBook`, `StressFieldReadout`             |

The constitutional design document is
[`docs/world_model.md`](japan-financial-world/docs/world_model.md);
every milestone has a section. The boundary inventory is
[`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md);
the naming policy is
[`docs/naming_policy.md`](japan-financial-world/docs/naming_policy.md);
the performance-boundary discipline is
[`docs/performance_boundary.md`](japan-financial-world/docs/performance_boundary.md).

---

## 6. Stress programs in v1.21

A v1.21 **stress program** is a small, ordered bundle of synthetic
stimuli applied to the v1.20 monthly reference universe. The
shape is intentionally narrow:

```
StressProgramTemplate
    stress_program_template_id
    program_label                  (closed-set vocabulary)
    program_purpose_label          (closed-set vocabulary)
    horizon_label                  (closed-set vocabulary)
    step_count                     ∈ {1, 2, 3}
    stress_step_ids                (ordered list, dense step_index)
    severity_label                 (closed-set vocabulary)
    affected_actor_scope_label     (closed-set vocabulary)
    reasoning_mode = "rule_based_fallback"
    reasoning_policy_id
    reasoning_slot = "future_llm_compatible"
    status, visibility, metadata

StressStep
    stress_step_id
    step_index                     (0..step_count-1, dense)
    scenario_driver_template_id    (cites a v1.18.1 template)
    severity_label                 (closed-set vocabulary)
    metadata
```

The orchestrator is **thin**:

```python
record = apply_stress_program(
    kernel=kernel,
    stress_program_template_id="stress_program_template:demo",
    issued_at=clock.now(),
)
# record.unresolved_step_count == 0  → all steps resolved
# record.unresolved_step_ids       == ()
# record.unresolved_reason_labels  == ()
# record.scenario_application_ids  → cites underlying v1.18.2 receipts
```

It walks `stress_step_ids` by dense `step_index` order, calls the
existing v1.18.2 `apply_scenario_driver(...)` helper once per step,
emits exactly **one** program-level
`StressProgramApplicationRecord`, and surfaces partial application
via a closed-set `unresolved_reason_labels` vocabulary
(`template_missing` / `unknown_failure`).

The readout is a **read-only multiset projection**:

```python
readout = build_stress_field_readout(kernel=kernel)
markdown = render_stress_field_summary_markdown(readout)
```

The readout describes — for each **context surface** touched by
the program — which `shift_direction_label` values were emitted,
in what scenario family, and which downstream records cite them.
It does **not** reduce the multiset to a single label; preserved
emission order is the audit value. The renderer emits 11 markdown
sections (9 pinned by the required-sections test as load-bearing).

What the readout does **not** do:

- It does not call `apply_stress_program(...)` or
  `apply_scenario_driver(...)` — it only reads what is already in
  the books.
- It does not emit a ledger record.
- It does not mutate any source-of-truth book.
- It does not auto-infer interaction labels. If an
  interaction-style annotation is ever introduced (no earlier
  than v1.22, possibly never), it must be `manual_annotation`-
  only — written by a human reviewer with their own analyst id
  and timestamp on the annotation record, citing explicit
  evidence from the multiset readout. It must never be inferred
  by a helper, a classifier, a closed-set rule table, an LLM, or
  any other automated layer.

For the full design discussion see
[`docs/v1_21_stress_composition_layer.md`](japan-financial-world/docs/v1_21_stress_composition_layer.md)
and §130 of
[`docs/world_model.md`](japan-financial-world/docs/world_model.md).

---

## 7. Public v1.x boundaries

Every public-FWE milestone preserves the same hard boundary. v1.21
re-pins the full list:

**No real-world output.**

- No price formation, no market price, no order, no execution,
  no clearing, no settlement, no financing execution.
- No forecast path, no expected return, no target price, no
  scenario probability weight, no magnitude.
- No firm decision, no investor action, no bank approval logic,
  no investment recommendation, no investment advice.

**No real-world input.**

- No real data ingestion, no public-data licenses are wired.
- No real institutional identifiers (BOJ / MUFG / GPIF / Toyota
  / TSE / TOPIX / Nikkei / JPX appear only as prohibited or
  deferred tokens in v1.x docs).
- No licensed taxonomy dependency (no bare GICS / MSCI / S&P /
  FactSet / Bloomberg / Refinitiv / TOPIX / Nikkei / JPX
  tokens in module text or test names; sector labels carry the
  `_like` suffix).
- No Japan calibration (deferred to v2.x / v3.x).

**No autonomous reasoning.**

- No LLM execution at runtime; no LLM prose accepted as
  source-of-truth.
- `reasoning_mode = "rule_based_fallback"` is binding across
  v1.18.x → v1.21.x; the `future_llm_compatible` slot is an
  architectural commitment, not a runtime capability.
- No interaction auto-inference (`amplify` / `dampen` /
  `offset` / `coexist` are forbidden as helper-emitted field
  names).
- No aggregate / combined / net / dominant / composite stress
  output.

**No source-of-truth book mutation.** Every pre-existing book
(`PriceBook`, `ContractBook`, `ConstraintBook`, `OwnershipBook`,
`InstitutionsBook`, `MarketEnvironmentBook`,
`FirmFinancialStateBook`, `InterbankLiquidityStateBook`,
`IndustryConditionBook`, `MarketConditionBook`,
`InvestorMarketIntentBook`, `FinancingPathBook`) is byte-identical
pre / post any v1.21 call.

**No backend in the UI.** The static workbench is HTML / CSS / JS
only, loaded under `file://`; the browser never executes Python,
never calls a backend, never fetches over XHR, never writes files.

For the public / restricted artifact rules see
[`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md).

---

## 8. How to run tests / export a local bundle / open the static UI

**Install** (from the repo root):

```bash
pip install -e ".[dev]"
```

This brings in PyYAML 6.x (pinned `>=6,<7` in `pyproject.toml`),
pytest, and ruff. CI runs the same step.

**Run the full test suite** (from `japan-financial-world/`):

```bash
python -m pytest -q
```

Expected at v1.22.last: **`4893 passed`**.

**Run the v1.9.last living reference world** (from
`japan-financial-world/`):

```bash
# Compact operational trace:
python -m examples.reference_world.run_living_reference_world

# + deterministic Markdown ledger trace report:
python -m examples.reference_world.run_living_reference_world --markdown

# + reproducibility manifest (JSON, SHA-256 living_world_digest):
python -m examples.reference_world.run_living_reference_world \
    --manifest /tmp/fwe_living_world_manifest.json
```

Each mode is byte-identical across consecutive runs.

**Export a CLI bundle for the static UI** (from
`japan-financial-world/`):

```bash
# Quarterly default profile (4 periods):
python -m examples.reference_world.export_run_bundle \
    --profile quarterly_default \
    --out /tmp/fwe_quarterly_bundle.json

# Monthly reference profile (12 monthly periods, 51 information arrivals):
python -m examples.reference_world.export_run_bundle \
    --profile monthly_reference \
    --out /tmp/fwe_monthly_bundle.json

# Monthly scenario reference universe (12 monthly periods, scenario applied):
python -m examples.reference_world.export_run_bundle \
    --profile scenario_monthly_reference_universe \
    --regime constrained \
    --scenario credit_tightening_driver \
    --out /tmp/fwe_scenario_universe_bundle.json
```

**Open the static workbench:**

Open
[`japan-financial-world/examples/ui/fwe_workbench_mockup.html`](japan-financial-world/examples/ui/fwe_workbench_mockup.html)
directly in a browser (under `file://`). Use the bundle picker
to load a JSON exported above. The browser renders 11 tabs over
the bundle and **never** executes Python, calls a backend, or
writes files.

**Lint and compile checks:**

```bash
ruff check .
python -m compileall -q world spaces tests examples
```

Both should report clean at v1.22.last.

---

## 9. Roadmap

The v1.25 sequence is **complete and frozen** at v1.25.last. The
next steps are candidates, not commitments; each requires a fresh
design pin before any code lands. Silent extension of v1.25 is
forbidden.

**Public-v1.x → v2 path (binding direction):**

- **v1.26 candidate** — Entity Lifecycle + Reporting Calendar
  Foundation (generic, country-neutral; no real data).
- **v1.27 candidate** — Generic Strategic Relationship Network +
  Annotation Provenance Hardening (no percentages, no real
  company names, no EDINET).
- **v2.0 candidate** — Japan Public Calibration Boundary Design
  ONLY (docs-only; no data ingestion).
- **v2.1 candidate** — Japan Universe + Disclosure Calendar
  Public Calibration (gated by v2.0).
- **v2.2 candidate** — Japan Cross-Shareholding Public Data
  Adapter (gated by v2.0 + v1.27).
- **v3.x** — proprietary Japan calibration, not public.

| Version    | Goal                                                                                                        | Status                                                          |
| ---------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| v0.x       | Structural contract                                                                                         | **Frozen at v0.16**                                             |
| v1.0–v1.7  | Reference content + first closed loop                                                                       | **Frozen at v1.7**                                              |
| v1.8.x     | Endogenous activity stack                                                                                   | **Shipped (v1.8.16 freeze)**                                    |
| v1.9.last  | Public prototype (living reference world)                                                                   | **Shipped**                                                     |
| v1.12.last | Endogenous attention loop                                                                                   | **Shipped**                                                     |
| v1.13.last | Generic central-bank settlement substrate                                                                   | **Shipped**                                                     |
| v1.16.last | First closed-loop reference economy                                                                         | **Shipped**                                                     |
| v1.17.last | Inspection layer                                                                                            | **Shipped**                                                     |
| v1.18.last | Synthetic scenario-driver library                                                                           | **Shipped**                                                     |
| v1.19.last | Local run bundle + monthly reference profile                                                                | **Shipped**                                                     |
| v1.20.last | Monthly scenario reference universe                                                                         | **Shipped**                                                     |
| v1.21.last | Stress Composition Layer freeze                                                                         | **Shipped**                                                          |
| v1.22.last | Static UI Stress Readout Reflection freeze (descriptive-only `stress_readout` payload section + Active Stresses strip in the existing Universe sheet; no new tab). | **Shipped**                                                     |
| v1.23.last | Substrate Hardening + Validation Foundation freeze (canonical digest module, composable forbidden-token vocabulary, metadata-stamp constants, runtime cardinality cap, four pinnable validation categories + two placeholders, attention-crowding / uncited-stress case study). | **Shipped.** |
| v1.24.last | Manual Annotation Interaction Layer freeze (human-authored append-only audit overlay; `source_kind = "human"` / `reasoning_mode = "human_authored"`; no auto-annotation; no causal proof; no interaction inference). | **Shipped.** |
| v1.25.last | **Generic Institutional Investor Mandate / Benchmark Pressure freeze.** v1.25.0 design pin (docs-only); v1.25.1 storage (`InvestorMandateProfile` + `InvestorMandateBook`, closed-set vocabularies, `INVESTOR_MANDATE_PROFILE_RECORDED` ledger event type, empty-by-default kernel field); v1.25.2 read-only `InvestorMandateReadout` projecting closed-set `MANDATE_REVIEW_CONTEXT_LABELS` + `MANDATE_ATTENTION_BIAS_LABELS`; v1.25.3 optional descriptive-only `investor_mandate_readout` payload section + minimal "Investor mandate context" panel inside the existing Universe sheet (no new tab; `textContent` only); v1.25.4 read-only case study; v1.25.last freeze. **Generic and jurisdiction-neutral** — `_like` archetype labels only; **NOT Japan calibration**; no real Japanese issuer ids; no JPX / TOPIX / Nikkei / GICS / EDINET dependency. **No portfolio allocation. No target weight. No rebalancing. No buy / sell / order / trade / execution. No expected return / target price / recommendation. No tracking-error value. No benchmark identifier. No actor decision. No investor / market intent emitted from the mandate surface. No source-of-truth mutation beyond the one `investor_mandate_profile_recorded` ledger event per caller-initiated `add_profile` call. No digest movement.** | **Shipped.** See [`docs/v1_25_institutional_investor_mandate_benchmark_pressure.md`](japan-financial-world/docs/v1_25_institutional_investor_mandate_benchmark_pressure.md) §21 "v1.25.last freeze" and [`docs/world_model.md`](japan-financial-world/docs/world_model.md) §134.6. |
| v1.26.last | **Entity Lifecycle + Reporting Calendar Foundation freeze (generic).** v1.26.0 design pin; v1.26.1 `UniverseEventRecord` storage (closed-set `UNIVERSE_EVENT_TYPE_LABELS`: entity_listed / delisted / merged / renamed / split / status_changed / unknown; `UNIVERSE_EVENT_RECORDED` ledger event); v1.26.2 `ReportingCalendarProfile` storage (closed-set `MONTH_LABELS` 1-12 + unknown; `DISCLOSURE_CLUSTER_LABELS`; `REPORTING_INTENSITY_LABELS`; `REPORTING_CALENDAR_PROFILE_RECORDED` ledger event); v1.26.3 read-only `UniverseCalendarReadout` (active/inactive entity walk; reporting-due via deterministic month-label extraction); v1.26.4 optional descriptive-only `universe_calendar_readout` payload section + minimal "Universe / calendar" panel inside the existing Universe sheet (no new tab; textContent only); v1.26.last freeze. **Empty-by-default rule preserves every existing fixed fixture byte-identically** — a kernel without UniverseEventRecord + ReportingCalendarProfile records continues to behave as a static universe exactly as it did at v1.25.last. **Synthetic only. No real data. No Japan calibration. No EDINET / TDnet / J-Quants / JPX / TOPIX / Nikkei / GICS / MSCI / S&P / FactSet / Bloomberg / Refinitiv dependency. No event-to-price mapping. No earnings-surprise / event-study / calendar-arbitrage inference. No portfolio / universe weight / constituent weight / rebalance event. No actor decision. No source-of-truth book mutation. No digest movement.** | **Shipped.** See [`docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md`](japan-financial-world/docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md) §15 and [`docs/world_model.md`](japan-financial-world/docs/world_model.md) §135.6. |
| **v1.27.last** | **Generic Strategic Relationship Network + Annotation Provenance Hardening freeze.** v1.27.0 design pin; v1.27.1 `StrategicRelationshipRecord` storage (closed-set `RELATIONSHIP_TYPE_LABELS`: strategic_holding_like / supplier_customer_like / group_affiliation_like / lender_relationship_like / governance_relationship_like / commercial_relationship_like / unknown; closed-set `DIRECTION_LABELS`; `STRATEGIC_RELATIONSHIP_RECORDED` ledger event; empty-by-default kernel field; 13 tests); v1.27.2 read-only `StrategicRelationshipReadout` (counts only — no centrality, no rank, no risk score) + optional descriptive-only `strategic_relationship_readout` payload section omitted-when-empty (13 tests); v1.27.3 `ManualAnnotationProvenanceRecord` storage (pseudonymous; closed-set `AUTHORITY_LABELS`: self_review / delegated_review / supervisory_review / audit_review / unknown; closed-set `EVIDENCE_ACCESS_SCOPE_LABELS`: public_synthetic / internal_synthetic / restricted_synthetic / unknown; anti-email-leak guard rejects `@` in `annotator_id_label`; `MANUAL_ANNOTATION_PROVENANCE_RECORDED` ledger event; 11 tests); v1.27.last freeze. **v1.27 closes the last generic substrate addition in public v1.x.** Next milestone is v2.0 Japan Public Calibration Boundary Design (docs-only). **Empty-by-default kernel fields. Synthetic only. No real data. No Japan calibration. No EDINET / TDnet / J-Quants / EDGAR. No real-company name / relationship claim. No ownership percentage / voting power / market value / fair value / centrality score / systemic-importance score. No real-person name / email / phone / national-id / employee-id. No SOC2 / FISC / ISO27001 / regulatory-attestation compliance claim. No LLM authoring. No source-of-truth book mutation. No digest movement.** | **Shipped — current.** See [`docs/v1_27_generic_relationship_network_annotation_provenance.md`](japan-financial-world/docs/v1_27_generic_relationship_network_annotation_provenance.md) §7 "v1.27.last freeze" and [`docs/world_model.md`](japan-financial-world/docs/world_model.md) §136.6. |
| v2.0 candidate | **Japan Public Calibration Boundary Design (docs-only)** — design packet only; no data ingestion. Public data only; license / redistribution policy gated. EDINET adapter is candidate; JPX / TOPIX / Nikkei / GICS dependencies forbidden unless license + redistribution policy is explicitly designed. | Optional candidate. Not started. Gated by license review and boundary design. |
| v2.1 candidate | **Japan Universe + Disclosure Calendar Public Calibration** — synthetic v1.26 universe + reporting calendar substrate calibrated to public Japanese data (license-permitting). Real Japanese issuer ids only after v2.0 boundary design pins them. | Optional candidate. Not started. Gated by v2.0. |
| v2.2 candidate | **Japan Cross-Shareholding Public Data Adapter** — public extraction adapter design for v1.27 strategic-relationship substrate. Adapter design first; implementation only after license / redistribution policy is pinned. | Optional candidate. Not started. Gated by v2.0 + v1.27. |
| v2.x       | Japan public calibration — only after data / license boundaries are designed.                              | Not started. Gated by license review and boundary design.       |
| v3.x       | Japan proprietary calibration — not public; would live in a private repository and would preserve every public-FWE boundary. | Not started. Not public.                                        |

**Deferred (or never).** `StressInteractionRule` and the
`amplify` / `dampen` / `offset` / `coexist` interaction-label
family are deferred to v1.22+ or never. If interaction-style
annotation is ever reconsidered, it must be
`manual_annotation`-only — never auto-inferred. See §130.7 of
[`docs/world_model.md`](japan-financial-world/docs/world_model.md).

---

## 10. Research direction

The longer arc this substrate is built for, stated honestly and
without overclaiming:

- **Make the engine legible before claiming any output is
  useful.** The v1.x line is deliberately useless as a market
  view. It is meant to be useful as a *foundation* — a layer on
  which higher layers can be added one at a time, each with the
  same audit discipline.
- **Replace narrative with citations.** A reviewer reading a
  v1.21 stress readout should be able to trace any line of the
  markdown summary back to the specific records on the specific
  context surfaces in the specific period that produced it,
  without reading the source code.
- **Preserve a hard boundary between substrate and behavior.**
  Behavior layers (price formation, allocation, lending
  decisions, policy reaction functions) are explicitly *not* in
  v1.x. If they are ever added, they will land as new
  milestones with their own design pins, their own boundary
  inventories, and their own forbidden-token lists; they will
  not retrofit existing v1.x records.
- **Keep public and private cleanly separated.** Public v1.x is
  jurisdiction-neutral and synthetic. Public v2.x will add only
  *public, licensed* Japanese data, with the license review
  done first. Private v3.x — proprietary calibration — would
  live in a private repository and would preserve every
  public-FWE boundary listed in §7.

What this substrate is *not* trying to be: a competitor to any
existing risk system, a market-view product, or an automated
trader. The current public release is a deliberately constrained
design exercise. Whether higher layers eventually justify a
practical claim is a question for later milestones, after the
substrate has been used in anger by readers other than the
author.

---

## License

See `LICENSE`.

## Disclaimer

This project is research software intended for engine design,
simulation methodology, and structural exploration of how
financial worlds can be modeled. It is **not investment
advice**, **not a calibrated real-world model**, and **not
production software**. No SLA. No support commitment. No
guarantee of API stability beyond what each milestone's freeze
document explicitly promises. See
[`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md)
for the public / restricted artifact rules.
