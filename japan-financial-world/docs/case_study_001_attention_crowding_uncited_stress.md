# Case Study 001 — Attention Crowding / Uncited Stress

*Companion case study to v1.23.3 (Attention-crowding /
uncited-stress milestone). Demonstrates what the v1.21.3
stress citation graph can reveal — and, equally important,
what it cannot — using only the existing v1.21.3 readout +
v1.22.1 export + v1.23.2 validation pins.*

This case study is a **research-defensible read-only
demonstration**, not a prediction. It pins, in code:

- which stress steps entered the v1.18.2 citation trail,
- which stress steps remained uncited or unresolved,
- whether partial application is visible at the v1.21.3
  markdown summary + v1.22.1 export entry,
- whether the export-shape preserves the v1.21.0a / v1.22.0
  forbidden-name boundary,
- whether every cited plain-id resolves to an extant kernel
  record.

The case study **does not** claim:

- a price prediction, a forecast, or an expected response;
- a magnitude, a probability, or a target;
- a recommendation, an investment-advice surface, or any
  actor-decision logic;
- a real-world stress episode, a real-world institution, or
  a real-world reviewer panel;
- an interaction-inference label (no `amplify` / `dampen` /
  `offset` / `coexist`);
- an aggregate / combined / net / dominant / composite stress
  output.

The companion documents are:

- [`v1_23_substrate_hardening_validation_foundation.md`](v1_23_substrate_hardening_validation_foundation.md)
  §5 — the v1.23.3 design pin.
- [`research_note_002_validating_stress_citation_graphs_without_price_prediction.md`](research_note_002_validating_stress_citation_graphs_without_price_prediction.md)
  — the validation framing the case study inherits.
- [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
  — the v1.21 stress layer the citation graph is built on.
- [`v1_22_static_ui_stress_readout_reflection.md`](v1_22_static_ui_stress_readout_reflection.md)
  — the v1.22 export-side payload section the case study
  inspects.

---

## 1. Problem framing

The v1.12 finite attention budget combined with the v1.18 /
v1.20 / v1.21 stimulus chain produces a graph in which a
reviewer can in principle see whether one stress's downstream
citations crowd out another's in the same period. Research
note 001 §5 named this the "attention-crowding question" and
declined to answer it with an aggregate metric; research note
002 §2 reframes it as a property of the citation graph that
the engine emits.

Concretely, when `apply_stress_program(...)` walks a v1.21.1
:class:`StressProgramTemplate` whose steps each cite a v1.18.1
:class:`ScenarioDriverTemplate`, two things can happen per
step:

- **Cited.** The cited template resolves; the v1.18.2 helper
  emits a :class:`ScenarioDriverApplicationRecord` and one
  or more :class:`ScenarioContextShiftRecord` records. The
  v1.21.2 program-level receipt collects the new ids; the
  v1.21.3 readout surfaces them under
  ``active_step_ids`` / ``scenario_application_ids`` /
  ``scenario_context_shift_ids``.
- **Uncited.** The cited template does not resolve (it is
  not registered in
  ``kernel.scenario_drivers.ScenarioDriverTemplateBook``,
  or the v1.18.2 helper raises for some other reason). The
  v1.21.2 program-level receipt records the step as
  unresolved; the v1.21.3 readout surfaces it under
  ``unresolved_step_ids`` with a closed-set reason
  label (``template_missing`` or ``unknown_failure``).

A reviewer that wants to ask "did this stress step actually
land in the citation graph?" can answer the question by
reading the v1.21.3 readout — and that is exactly what the
case study renders.

---

## 2. What the case study report contains

The v1.23.3 helper
:func:`world.stress_case_study.build_attention_crowding_case_study_report`
takes a stress-applied kernel and a
``stress_program_application_id`` and returns a deterministic
``dict`` with the following keys:

| Key | Type | Source |
| --- | ---- | ------ |
| `case_study_id` | `str` | derived from the program-application id |
| `stress_program_application_id` | `str` | caller-supplied |
| `stress_program_template_id` | `str` | from v1.21.3 readout |
| `stress_step_ids` | `list[str]` | cited + uncited (in step-order) |
| `cited_step_ids` | `list[str]` | from v1.21.3 ``active_step_ids`` |
| `uncited_step_ids` | `list[str]` | from v1.21.3 ``unresolved_step_ids`` |
| `scenario_application_ids` | `list[str]` | from v1.21.3 readout |
| `scenario_context_shift_ids` | `list[str]` | from v1.21.3 readout |
| `stress_readout_summary` | `dict` | selected v1.21.3 fields (counts + multiset labels) |
| `validation_report_summary` | `dict` | v1.23.2 Cat 1–4 pin results |
| `warnings` | `list[str]` | from v1.21.3 ``warnings`` |
| `boundary_statement` | `str` | pinned anti-claim block |

The companion renderer
:func:`world.stress_case_study.render_attention_crowding_case_study_markdown`
emits a deterministic 8-section markdown summary; same
report → byte-identical bytes.

---

## 3. What the validation report summary pins

The `validation_report_summary` sub-dict carries one entry per
v1.23.2 pinnable category from research note 002:

- **Cat 1 — Determinism.** The case study is itself a
  deterministic projection over the v1.21.3 readout; the test
  suite asserts byte-identity across two consecutive
  ``build_attention_crowding_case_study_report`` calls.
- **Cat 2 — Boundary preservation.** The helper scans the
  v1.22.1 export entry against the v1.23.1 canonical
  ``world.forbidden_tokens.FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS``
  composition. ``satisfied = True`` iff zero forbidden tokens
  appear at any key + zero appear as whole-string values at
  any depth.
- **Cat 3 — Citation completeness.** The helper walks every
  cited plain-id in the readout (scenario-application ids,
  scenario-context-shift ids, the program-application
  receipt id) and asserts each resolves to an extant record
  in the corresponding kernel book. ``satisfied = True`` iff
  every category has zero dangling ids.
- **Cat 4 — Partial-application visibility.** The helper
  re-asserts the v1.21.3 dataclass-level invariants (length
  parity between ``unresolved_step_ids`` and
  ``unresolved_reason_labels``; a "partial application"
  warning surfaces when ``is_partial`` is True).

Each pin returns a small dict with a ``satisfied`` flag and
diagnostic counts. The report carries no pin/fail decision
about Cat 5 (inter-reviewer reproducibility) or Cat 6
(null-model comparison) — those remain placeholders per
research note 002 §4.2.

---

## 4. Two scenarios the case study illuminates

### 4.1 All steps cited

A program where every cited template is registered on the
kernel produces:

- ``cited_step_ids`` populated with every step;
- ``uncited_step_ids`` empty;
- ``stress_readout_summary.is_partial_application`` = False;
- ``warnings`` empty;
- every Cat 1–4 pin satisfied.

A reviewer reading the report sees a fully-resolved citation
graph and can rely on ``scenario_context_shift_ids`` as the
audit object for downstream consumers (e.g., a future v1.x
manual-annotation layer).

### 4.2 At least one step uncited

A program where one cited template is missing (or the v1.18.2
helper raises for some other reason) produces:

- ``cited_step_ids`` covering only the resolved steps;
- ``uncited_step_ids`` listing every unresolved step;
- ``stress_readout_summary.unresolved_reason_labels``
  paralleling the uncited list with closed-set reason
  labels;
- ``stress_readout_summary.is_partial_application`` = True;
- ``warnings`` containing a "partial application" entry plus
  one "step ... unresolved (...)" entry per uncited step;
- the Cat 4 visibility pin satisfied (the v1.21.3 readout
  legibly surfaces the partial application).

A reviewer reading the report sees the partial application
without having to interpret a number — the citation graph
itself reports its own gaps. This is the v1.23.x scenario
that "attention crowding" is most legibly captured in: when
multiple stress steps compete for resolution and not every
one lands, the report names exactly which steps did not.

---

## 5. Read-only / no-mutation discipline

The helper is read-only:

- It does **not** call
  :func:`world.stress_applications.apply_stress_program` —
  the case study runs after the program has already been
  applied, and the helper only projects the existing
  records.
- It does **not** call
  :func:`world.scenario_applications.apply_scenario_driver`.
- It does **not** mutate any kernel book — every relevant
  snapshot is byte-identical pre / post call.
- It does **not** emit a ledger record. v1.23.3 ships **no**
  new RecordType.

Re-running the helper on the same kernel state produces a
byte-identical report. This is exactly the v1.23.2 Cat 1
(determinism) pin extended to one more deterministic
projection.

---

## 6. Hard boundary (re-pinned at v1.23.3)

v1.23.3 inherits and re-pins the v1.22.last + v1.23.0 hard
boundary in full:

**No real-world output.**
- No price formation, no market price, no order, no trade,
  no execution, no clearing, no settlement, no financing
  execution.
- No forecast path, no expected return, no target price, no
  recommendation, no investment advice.
- No magnitude, no probability, no expected response.
- No firm decision, no investor action, no bank approval
  logic.

**No real-world input.**
- No real data ingestion.
- No real institutional identifiers.
- No licensed taxonomy dependency.
- No Japan calibration.

**No autonomous reasoning.**
- No LLM execution at runtime.
- No LLM prose accepted as source-of-truth.
- No interaction auto-inference.
- No aggregate / combined / net / dominant / composite
  stress output.

**No source-of-truth book mutation.**
- v1.23.3 is read-only over an already stress-applied
  kernel. Pre-existing book snapshots remain byte-identical
  pre / post any v1.23.3 helper call.

**No new UI region.**
- v1.23.3 does not touch the static UI mockup. The v1.20.5
  / v1.22.2 / v1.23.2a / v1.23.2b discipline is preserved.

**No digest movement.**
- All v1.18.last / v1.19.last / v1.20.last / v1.21.last /
  v1.22.last canonical ``living_world_digest`` values
  remain byte-identical at v1.23.3.

---

## 7. What the case study supports

The case study is a research artifact: it shows, in code,
that the v1.21.3 stress citation graph is **legible enough
to support audit-object validation without predictive
accuracy scoring**. A reviewer reading
``build_attention_crowding_case_study_report``'s output can:

1. Identify exactly which stress steps the engine surfaced
   under the cited program-application receipt.
2. Identify exactly which stress steps did not land in the
   citation graph and why (closed-set reason label).
3. Re-run the helper and verify byte-identity (Cat 1).
4. Inspect every cited plain-id and verify it resolves to
   an extant record (Cat 3).
5. Confirm the export-shape carries no v1.21.0a / v1.22.0
   forbidden token (Cat 2).
6. Confirm the partial-application banner / counts / reason
   labels propagate through both the v1.21.3 markdown
   summary and the v1.22.1 export entry (Cat 4).

That is the v1.23.3 contribution: a research-defensible
demonstration of what the citation graph reveals, without
inventing any new audit semantics.

---

## 8. Future work

Future milestones may extend the case study to:

- the **citation-graph diff format** (research note 002
  §4.2 Cat 6 placeholder) — comparing the cited / uncited
  sets between two stress programs applied to the same
  kernel state;
- the **inter-reviewer reproducibility** layer (research
  note 002 §4.2 Cat 5 placeholder) — pairing each report
  with a signed reviewer note from
  ``tests/fixtures/inter_reviewer/``;
- the **v1.24 candidate manual_annotation interaction
  layer** — adding a closed-set human-authored annotation
  surface over the cited / uncited list.

None of these are in scope at v1.23.3. The case study ships
the substrate they will build on.
