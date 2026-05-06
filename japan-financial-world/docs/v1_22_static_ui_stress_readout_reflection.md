# v1.22 Static UI Stress Readout Reflection — Design Note

*v1.22 is the design milestone that lands the **first UI surface
for the v1.21 stress composition layer**, ships in two thin code
sub-milestones (v1.22.1 + v1.22.2) under v1.22.0 design, and
freezes as v1.22.last.*

This document is **docs-only at v1.22.0**. It introduces no new
runtime module, no new dataclass, no new ledger event, no new
test, and no new label vocabulary. It is the binding scope pin
for v1.22.x; v1.22.1 and v1.22.2 must be implemented exactly to
this design or the design must be re-pinned.

The companion documents are:

- [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
  — the v1.21 design pin, including §*UI guidance (binding for
  v1.21.3 / future)*. v1.22 implements that section's binding
  shape; it does not extend it.
- [`world_model.md`](world_model.md) §131 — the constitutional
  position of v1.22 in the FWE sequence.
- [`research_note_001_stress_composition_without_outcome_inference.md`](research_note_001_stress_composition_without_outcome_inference.md)
  — the research framing v1.22 inherits ("stress stimuli are
  append-only inputs to context surfaces; the model does not
  infer combined outcomes").

---

## 1. Scope statement (binding)

v1.22 reflects the existing v1.21 read-only stress readout in
the static UI. **It does not produce a new readout.** v1.21.3
already produces the authoritative `StressFieldReadout` and the
deterministic markdown summary; v1.22 surfaces that same
readout in the v1.20.5 static workbench's existing **Universe**
tab.

The v1.22 surface is built from the following binding moves:

1. **v1.22.1 — bundle schema extension.** The CLI export bundle
   (`RunExportBundle`) gains a new top-level **descriptive-
   only** payload section that mirrors the v1.21.3 readout's
   plain-id citation surface. The browser reads this section
   from local JSON; nothing else reaches the browser.
2. **v1.22.2 — Universe-tab "Active Stresses" strip.** The
   existing Universe tab gains a single horizontal strip with
   12 monthly cells. The strip renders the v1.22.1 section
   verbatim. **No new tab.** No layout shift to existing
   Universe widgets.
3. **v1.22.last — docs-only freeze.** Closes the v1.22 sequence
   under the same digests / record counts / pytest count as
   v1.21.last (no behavior change beyond the export section
   and the UI strip).

What v1.22 is **not** (binding):

- v1.22 is **not** a new readout. It is a reflection of v1.21.3.
- v1.22 is **not** a stress-impact view. It surfaces citation
  ids and direction labels; it never renders an outcome metric.
- v1.22 is **not** a stress-magnitude view. There is no bar
  height, no score, no numeric intensity, no expected response.
- v1.22 is **not** an interaction-inference view. It carries no
  `amplify` / `dampen` / `offset` / `coexist` label; if such an
  annotation ever exists (manual_annotation, v1.22+ or never),
  it lands under a fresh design pin, not under this one.
- v1.22 is **not** a backend-enabled UI. The browser reads
  local JSON via `<input type="file">` + `FileReader` +
  `JSON.parse`. **No backend, no fetch / XHR, no
  file-system write, no Python execution from the browser.**

---

## 2. Sequence map

| Milestone     | Surface                                                                  | What it ships                                                                                                                                |
| ------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **v1.22.0**   | docs-only                                                                | This design note. §131 in `world_model.md`. Roadmap-row refresh in `v1_20_monthly_scenario_reference_universe_summary.md` and `README.md`.   |
| v1.22.1       | export-bundle code: `world/run_export.py` (extend) + `examples/reference_world/export_run_bundle.py` (extend) | New top-level **stress_readout** payload section on `RunExportBundle`. Empty when no v1.21 stress program has been applied to the run.       |
| v1.22.2       | static UI: `examples/ui/fwe_workbench_mockup.html` (extend)              | An **Active Stresses** strip rendered above the existing v1.20.5 Universe-tab sector heatmap. Reads the v1.22.1 section from the loaded JSON. |
| **v1.22.last**| docs-only                                                                | Final freeze section in this document; §131.x freeze in `world_model.md`; refreshed roadmap rows.                                            |

Cardinality (binding, inherited from v1.21.0a):

- ≤ 1 stress program per run (so ≤ 1 entry under
  `stress_readout` per bundle).
- ≤ 3 stress steps per program.
- ≤ 60 v1.21 records added per run.

---

## 3. Bundle schema (binding for v1.22.1)

### 3.1 Section name and placement

Add a new top-level payload key on `RunExportBundle` named
**`stress_readout`** (singular).

Rationale for `stress_readout` over `stress_activity` or
`stress_readouts`:

- The v1.21.3 helper is named `build_stress_field_readout(...)`;
  the dataclass is `StressFieldReadout`. The bundle key should
  echo the helper, not introduce a new word.
- Cardinality is bounded at ≤ 1 per run, so the singular form
  matches reality. (The interior shape is still a list — see
  §3.3 — to leave room for v1.23+ to relax the cardinality
  constraint *under a fresh design pin*; v1.22 always emits a
  list of length 0 or 1.)
- "Activity" implies behavior over time; "readout" implies
  inspection of state. The latter matches v1.21's framing.

The new key sits **alongside** the existing `RunExportBundle`
payload sections (`overview`, `timeline`, `regime_compare`,
`scenario_trace`, `attention_diff`, `market_intent`,
`financing`, `ledger_excerpt`, `metadata`). It is **not** a
sub-key of `metadata` — it is a peer of `scenario_trace`,
because the readout is the v1.21 analogue of the v1.18 scenario
trace.

### 3.2 Empty-by-default (binding)

When **no** v1.21 stress program has been applied to the run,
`stress_readout` is `[]` (an empty list).

When `stress_readout == []`:

- The bundle JSON is **byte-identical** to a pre-v1.22 bundle
  with a sorted-keys serialiser that omits empty payload
  sections (the existing `bundle_to_json` already uses
  `sort_keys=True`). v1.22.1 must preserve byte-identity for
  every existing pinned digest:
  - `quarterly_default` `living_world_digest`:
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` `living_world_digest`:
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` test-fixture
    `living_world_digest`:
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle digest:
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
  Two implementation strategies are acceptable:
  1. Always emit the empty list and re-pin the digests at
     v1.22.1 (digest movement is a regression by default;
     re-pinning would require a fresh design pin).
  2. **Preferred:** emit the section *only* when ≥ 1 stress
     program is in the kernel; otherwise omit it from the
     `bundle.to_dict()` output entirely. This preserves
     byte-identity with pre-v1.22 bundles.
  v1.22.1 **must take strategy (2)**. No digest movement is
  acceptable at v1.22.1.

### 3.3 Section shape

`stress_readout` is a **list of zero or one entry**, where each
entry is a dictionary of **descriptive-only** plain-id citations
and closed-set labels mirroring `StressFieldReadout`:

```jsonc
{
  "stress_readout": [
    {
      // identity
      "stress_program_application_id": "stress_program_application:001",
      "stress_program_template_id":    "stress_program_template:demo",
      "as_of_date":                    "2026-03-31",

      // step resolution (descriptive counts + plain ids only)
      "total_step_count":              3,
      "resolved_step_count":           2,
      "unresolved_step_count":         1,
      "active_step_ids":               ["stress_step:0", "stress_step:1"],
      "unresolved_step_ids":           ["stress_step:2"],
      "unresolved_reason_labels":      ["template_missing"],
      "is_partial":                    true,

      // emitted-record citations (plain ids only, preserved order)
      "scenario_driver_template_ids":  ["scenario_driver_template:credit_tightening_driver",
                                        "scenario_driver_template:industry_condition_driver"],
      "scenario_application_ids":      ["scenario_application:001",
                                        "scenario_application:002"],
      "scenario_context_shift_ids":    ["scenario_context_shift:001",
                                        "scenario_context_shift:002",
                                        "scenario_context_shift:003"],

      // multiset projections (closed-set labels, preserved order)
      "context_surface_labels":        ["interbank_liquidity",
                                        "industry_condition",
                                        "industry_condition"],
      "shift_direction_labels":        ["tightening",
                                        "contracting",
                                        "contracting"],
      "scenario_family_labels":        ["credit_tightening_driver",
                                        "industry_condition_driver",
                                        "industry_condition_driver"],

      // citation trail (plain ids only)
      "source_context_record_ids":     ["interbank_liquidity_state:0001"],
      "downstream_citation_ids":       ["actor_attention_selection:0042",
                                        "investor_market_intent:0007",
                                        "firm_operating_pressure_assessment:0019"],

      // partial-application + warning surface
      "warnings":                      ["one or more steps did not resolve"]
    }
  ]
}
```

All keys above are **descriptive**. None implies an outcome,
magnitude, probability, or interaction.

### 3.4 Required fields (binding for v1.22.1)

| Field                          | Type                  | Source on `StressFieldReadout`                                               |
| ------------------------------ | --------------------- | ---------------------------------------------------------------------------- |
| `stress_program_application_id`| `str`                 | mirror of `StressProgramApplicationRecord.stress_program_application_id`     |
| `stress_program_template_id`   | `str`                 | mirror of `StressProgramApplicationRecord.stress_program_template_id`        |
| `as_of_date`                   | `str` (ISO-8601 date) | from the application record's `as_of_date` field                             |
| `total_step_count`             | `int`                 | `len(StressProgramTemplate.stress_step_ids)`                                 |
| `resolved_step_count`          | `int`                 | `total_step_count - unresolved_step_count`                                   |
| `unresolved_step_count`        | `int`                 | mirror of `StressProgramApplicationRecord.unresolved_step_count`             |
| `active_step_ids`              | `list[str]`           | resolved step ids, preserved order                                           |
| `unresolved_step_ids`          | `list[str]`           | mirror of `StressProgramApplicationRecord.unresolved_step_ids` (sorted)      |
| `unresolved_reason_labels`     | `list[str]`           | closed set: `["template_missing"]`, `["unknown_failure"]`, or both           |
| `is_partial`                   | `bool`                | `unresolved_step_count > 0`                                                  |
| `scenario_driver_template_ids` | `list[str]`           | per-resolved-step, preserved emission order                                  |
| `scenario_application_ids`     | `list[str]`           | mirror of `StressProgramApplicationRecord.scenario_application_ids`          |
| `scenario_context_shift_ids`   | `list[str]`           | per-emitted-shift, preserved emission order                                  |
| `context_surface_labels`       | `list[str]`           | mirror of `StressFieldReadout.context_surface_labels`                        |
| `shift_direction_labels`       | `list[str]`           | mirror of `StressFieldReadout.shift_direction_labels`                        |
| `scenario_family_labels`       | `list[str]`           | mirror of `StressFieldReadout.scenario_family_labels`                        |
| `source_context_record_ids`    | `list[str]`           | mirror of `StressFieldReadout.cited_source_context_record_ids`               |
| `downstream_citation_ids`      | `list[str]`           | mirror of `StressFieldReadout.downstream_citation_ids`                       |
| `warnings`                     | `list[str]`           | mirror of `StressFieldReadout.warnings`                                      |

All list fields preserve emission order (no de-duplication, no
sorting except where the readout's own field is already
canonicalised). The three multiset fields
(`context_surface_labels`, `shift_direction_labels`,
`scenario_family_labels`) are **parallel arrays of equal
length**: index `i` describes the i-th emitted shift.

### 3.5 Forbidden fields (binding)

The following keys MUST NOT appear anywhere under
`stress_readout` (not as fields, not as values, not as nested
keys, not as metadata):

| Forbidden token                  | Reason                                                                                          |
| -------------------------------- | ----------------------------------------------------------------------------------------------- |
| `impact`                         | Implies a magnitude / outcome the engine does not produce.                                      |
| `outcome`                        | Same.                                                                                            |
| `risk_score`                     | Implies a numeric risk metric.                                                                   |
| `amplification`                  | v1.21.0a-deferred interaction language.                                                          |
| `dampening`                      | v1.21.0a-deferred interaction language.                                                          |
| `offset_effect`                  | v1.21.0a-deferred interaction language.                                                          |
| `dominant_stress`                | v1.21.0a-deferred composition reduction.                                                         |
| `net_pressure`                   | v1.21.0a-deferred composition reduction.                                                         |
| `composite_risk`                 | v1.21.0a-deferred composition reduction.                                                         |
| `forecast`                       | No forecast at v1.x.                                                                             |
| `expected_response`              | No predicted response at v1.x.                                                                   |
| `prediction`                     | No prediction at v1.x.                                                                           |
| `recommendation`                 | No advice surface.                                                                               |
| `expected_return`                | No return surface.                                                                               |
| `target_price`                   | No price formation.                                                                              |
| `magnitude` / `severity_score`   | No numeric intensity is exposed in the JSON; severity *labels* live on the underlying records, not on the readout section. |
| `probability`                    | No probability surface.                                                                          |
| `interaction_label`              | v1.21.0a-deferred.                                                                               |
| `composition_label`              | v1.21.0a-deferred.                                                                               |
| `aggregate_*` / `combined_*` / `net_*` / `dominant_*` / `composite_*` | v1.21.0a-deferred prefixes — no field under `stress_readout` may use these prefixes.       |
| `amplify` / `dampen` / `offset` / `coexist` (as labels or values) | v1.21.0a interaction-label vocabulary.                                                       |

The v1.22.1 export builder MUST scan its own emitted section
against this forbidden set at construction time, mirroring the
v1.19 / v1.20 / v1.21 forbidden-set discipline in
`FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES` and
`FORBIDDEN_RUN_EXPORT_FIELD_NAMES`. The forbidden set composes
with — does not replace — those existing sets.

### 3.6 Section-level invariants (binding)

- `len(scenario_context_shift_ids) == len(context_surface_labels) == len(shift_direction_labels) == len(scenario_family_labels)`. The three label arrays are parallel projections of the same emission order.
- `len(active_step_ids) == resolved_step_count`. Plain-id list, preserved order.
- `len(unresolved_step_ids) == unresolved_step_count`. Sorted.
- `set(unresolved_reason_labels) ⊆ {"template_missing", "unknown_failure"}`. (The closed set is the v1.21.2 `UNRESOLVED_REASON_LABELS` frozenset.)
- `is_partial == (unresolved_step_count > 0)`. Derived; not source of truth.
- `total_step_count = resolved_step_count + unresolved_step_count`.

The v1.22.1 export builder MUST NOT emit a section that
violates any of the above invariants. A violation is a
regression and must fail the v1.22.1 test suite before merge.

---

## 4. UI placement (binding for v1.22.2)

### 4.1 No new tab (binding)

The v1.20.5 sheet-tab set is **frozen at 11 tabs** by the
11-tab ↔ 11-sheet bijection pin in
[`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
§*UI guidance*. v1.22.2 MUST NOT add a new tab. The Active
Stresses surface lands inside the **existing Universe tab**.

### 4.2 Strip placement

Add a single **Active Stresses** strip **above** the existing
Universe-tab sector sensitivity heatmap, **below** the
universe-profile header. Layout sketch:

```
Universe tab
├─ Universe-profile header           (existing v1.20.5)
├─ Active Stresses strip             ← v1.22.2 NEW (12 monthly cells)
├─ Sector sensitivity heatmap        (existing v1.20.5)
├─ Firm-profile table                (existing v1.20.5)
└─ 5-step scenario causal trace      (existing v1.20.5)
```

The strip must not displace, resize, or otherwise reflow the
existing widgets. When `stress_readout` is `[]` (or absent),
the strip renders an **empty-state placeholder** (one line,
neutral wording: "No stress program applied to this run.") and
takes no further vertical space.

### 4.3 Strip contents

Each of the 12 monthly cells displays:

1. **Active stress family tokens** — the
   `scenario_family_labels` whose corresponding shifts fall
   within that month's `as_of_date` window. Render verbatim
   as compact tokens (e.g., `credit_tightening_driver`).
   No icons, no colour fill, no shape encoding magnitude.
2. **Resolution counter** — `resolved_step_count /
   total_step_count` rendered as plain text (e.g., `2 / 3`).
3. **Unresolved badge** — a small text badge `partial: N`
   when `unresolved_step_count > 0`, where N is the
   unresolved count. The badge is a static text label; no
   colour change, no animation.
4. **Empty cell** — when no shift falls in the month: a
   single dash character or `—`. No "no-stress" text.

### 4.4 Hover / details panel

A details panel (single shared panel below the strip, or a
hover tooltip — the implementer chooses one in v1.22.2) shows
the per-cell breakdown:

- **Context surfaces touched in this month** — the parallel
  `context_surface_labels` for shifts whose `as_of_date`
  falls in the month. Render as a list of plain tokens with
  multiplicities, e.g.:
  ```
  Context surfaces (multiset):
    industry_condition × 2
    interbank_liquidity × 1
  ```
- **Shift directions (multiset)** — the parallel
  `shift_direction_labels`, same multiset rendering.
- **Scenario families (multiset)** — the parallel
  `scenario_family_labels`, same multiset rendering.
- **Cited source context record ids** — the plain ids from
  `source_context_record_ids` whose corresponding shifts fall
  in this month. List rendering, no decoration.
- **Downstream citations** — the plain ids from
  `downstream_citation_ids` whose corresponding shifts fall
  in this month. List rendering, no decoration.
- **Warnings** — `warnings` list, rendered verbatim.

If the implementer cannot determine which downstream
citation corresponds to which month from the v1.22.1 section
alone (the readout collapses to a single readout per program;
per-month attribution may not be 1:1), v1.22.2 MUST display
the full unsegmented downstream citation list **once, at the
strip level (not per-cell)**, with a note clarifying the
scope. Do not invent a per-month split that is not present in
the JSON.

### 4.5 Visual boundaries (binding)

The strip MUST NOT use any of the following:

- **No bar height.** No vertical encoding of stress magnitude.
- **No score.** No numeric severity / amplification / intensity
  rendered in any cell.
- **No red / green performance encoding.** Cells are
  monochrome; the only allowed colour signal is a single
  neutral accent for the *partial application* badge, and
  even that must work in greyscale.
- **No arrows implying causal propagation.** No "stress X →
  outcome Y" connectors. Citations are listed, not animated.
- **No `impact` / `outcome` / `risk score` wording.** Use the
  neutral phrasing in §4.6.
- **No icons that imply direction of harm.** A neutral
  `partial:` text badge is the only allowed marker.

### 4.6 Required wording (binding)

Use these phrases verbatim in strip labels and headings:

- **Active stresses** (strip title).
- **Context surfaces** (details-panel section).
- **Shift directions** (details-panel section).
- **Cited records** (details-panel section header for source
  context record ids).
- **Downstream citations** (details-panel section header for
  the citation trail).
- **Partial application** (details-panel banner when any
  unresolved step exists; mirrors the v1.21.3 markdown
  renderer's "PARTIAL APPLICATION" banner).
- **Read-only stress readout** (subtitle below the strip
  title; clarifies that the strip is descriptive, not
  predictive).
- **Multiset projection** (caption on the multiset rendering
  in the details panel).

The wording above carries forward unchanged into the v1.22.2
HTML strings and is pinned by §6.2 below.

### 4.7 Loader discipline (binding, carried forward from v1.19.4 / v1.20.5)

- The browser reads the bundle via `<input type="file">` +
  `FileReader` + `JSON.parse`. **No fetch, no XHR, no
  backend, no file-system write, no Python execution from the
  browser.**
- `textContent` only — never `innerHTML` for any field
  rendered from the loaded JSON.
- No `eval`, no dynamic `Function(...)`, no `location.hash`
  mutation during bundle load, no scroll jump, no active-tab
  shift on load.
- The strip MUST gracefully handle a bundle that **lacks**
  `stress_readout` entirely (pre-v1.22 bundle): render the
  empty-state placeholder and proceed.

---

## 5. Visual boundaries (binding, summary)

This section pins the visual contract end-to-end. It is the
shortest-possible reading of §4 a UI implementer or reviewer
should be able to use as a checklist:

**MUST NOT:**

- No bar height (no magnitude encoding).
- No score (no numeric intensity).
- No red / green performance encoding.
- No arrows implying causal propagation.
- No `impact` wording.
- No `outcome` wording.
- No `risk score` wording.
- No `prediction` / `forecast` / `expected response`
  wording.
- No `recommendation` / `investment advice` wording.
- No `magnitude` / `basis points` / `percent` rendered as
  numeric severity.
- No `amplify` / `dampen` / `offset` / `coexist` interaction
  labels rendered anywhere.
- No `aggregate_*` / `combined_*` / `net_*` / `dominant_*` /
  `composite_*` field rendered anywhere.

**MUST USE the following neutral wording:**

- Active stresses
- Context surfaces
- Shift directions
- Cited records
- Partial application
- Read-only stress readout
- Multiset projection

If a reader of the strip cannot tell whether the engine has
made an outcome claim, the strip has failed its discipline.
The v1.22 surface is **descriptive only** — it tells a
reviewer *what was emitted, on what surfaces, in what order*
and *which downstream records cited it*. It says nothing about
what any of that means for any actor.

---

## 6. Test plan

All tests below are **proposed for v1.22.1 / v1.22.2**, not for
v1.22.0. v1.22.0 ships no new tests. Total test count must move
from `4865 → 4865 + N(v1.22.1) + N(v1.22.2)` only at
v1.22.1 / v1.22.2; the v1.22.0 commit must hold pytest at
4865.

### 6.1 v1.22.1 export tests
*(target: `tests/test_run_export_stress_readout.py` — new file)*

1. **Empty section is omitted.** When the kernel has zero
   `StressProgramApplicationRecord` entries, the JSON output
   from `bundle_to_json(...)` MUST NOT contain the
   `stress_readout` key. Pin via:
   ```python
   assert "stress_readout" not in json.loads(bundle_to_json(bundle))
   ```
2. **No-stress digest preservation.** A `quarterly_default`
   bundle without any stress program produces the
   `living_world_digest` byte-identical to v1.21.last
   (`f93bdf3f…b705897c`). Same for `monthly_reference`
   (`75a91cfa…91879d`),
   `scenario_monthly_reference_universe`
   (`5003fdfa…566eb6`), and the v1.20.4 CLI bundle digest
   (`ec37715b…0731aaf`).
3. **Section is present when stress is applied.** When the
   kernel has ≥ 1 `StressProgramApplicationRecord`, the
   `stress_readout` key is present, is a list, and contains
   exactly one entry (cardinality from v1.21.0a).
4. **Required descriptive fields are present.** Each entry
   contains all 19 required keys from §3.4. No required key
   is missing.
5. **No forbidden tokens in the section.** A regression scan
   over the section's keys, nested keys, and string values
   asserts that none of the forbidden tokens from §3.5 appear.
   The scan composes with `FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES`
   and `FORBIDDEN_RUN_EXPORT_FIELD_NAMES`.
6. **Browser bundle stays static JSON.** The bundle JSON is
   parseable by `json.loads(...)`; it contains no embedded
   JavaScript, no embedded HTML, no callable references. (Test
   already implicit in v1.19.x; v1.22.1 re-pins it for the
   new section.)
7. **Plain-id citations only.** Every value under
   `scenario_driver_template_ids` /
   `scenario_application_ids` / `scenario_context_shift_ids` /
   `source_context_record_ids` / `downstream_citation_ids` is
   a string (never an object), and matches the v1.18.1 /
   v1.18.2 / v1.21.x id-prefix conventions.
8. **Parallel-array invariants hold.** `len(scenario_context_shift_ids) == len(context_surface_labels) == len(shift_direction_labels) == len(scenario_family_labels)`.
9. **Resolution counters are consistent.**
   `total_step_count == resolved_step_count + unresolved_step_count`;
   `is_partial == (unresolved_step_count > 0)`.
10. **Unresolved-reason vocabulary is closed.**
    `set(unresolved_reason_labels) ⊆ {"template_missing", "unknown_failure"}`.
11. **No interaction language.** No value under any list
    contains `amplify` / `dampen` / `offset` / `coexist` (case-
    insensitive scan).
12. **No magnitude language.** No value under any list
    contains `magnitude`, `score`, `intensity`, `bps`,
    `basis_points`, `percent`, or any numeric-encoding token
    (case-insensitive scan).
13. **`as_of_date` discipline.** ISO-8601 date string only;
    no time component; no timezone.

### 6.2 v1.22.2 UI tests
*(target: `tests/test_ui_active_stresses_strip.py` — new file;
follows the v1.20.5 / v1.19.4 UI-test convention of parsing
the static HTML and asserting on selectors / text content)*

1. **Universe tab count unchanged.** The HTML still has
   exactly 11 sheet-tab buttons (the v1.20.5 11-tab ↔
   11-sheet bijection). No new `data-sheet="..."` button is
   added.
2. **Active Stresses strip element exists in the Universe
   sheet.** A unique selector — e.g., `data-section="active-stresses"`
   — exists exactly once, and exactly inside the Universe
   sheet. Pin via:
   ```python
   universe = soup.select_one('[data-sheet="universe"]')
   assert universe.select_one('[data-section="active-stresses"]') is not None
   ```
3. **Strip renders 12 monthly cells.** Inside the strip, exactly
   12 cell elements (e.g., `data-active-stresses-cell`) exist.
4. **Strip header carries required wording.** The strip's
   header text contains the verbatim phrase
   `Active stresses` (case-sensitive).
5. **Subtitle wording.** The strip subtitle contains
   `Read-only stress readout`.
6. **Empty-state placeholder.** When `stress_readout` is
   omitted (pre-v1.22 bundle) the strip renders a single
   placeholder line containing `No stress program applied`.
7. **Empty-state still renders 12 cells (each as `—`).**
   The 12-cell skeleton MUST NOT change shape with the empty
   state; cells render an em-dash placeholder.
8. **Partial application badge renders.** When
   `unresolved_step_count > 0` for a cell, that cell contains
   the literal string `partial:`. (v1.22.2 may also surface
   a strip-level "Partial application" banner; if so, that
   banner contains the verbatim phrase `Partial application`.)
9. **Multiset rendering uses the required caption.** The
   details panel (or hover tooltip) carries the verbatim
   phrase `Multiset projection`.
10. **Per-section headers carry required wording.** The
    details panel contains `Context surfaces`, `Shift
    directions`, `Cited records`, and `Downstream citations`
    (each verbatim, case-sensitive).
11. **Forbidden wording is absent from UI strings.** A scan
    over the rendered HTML's text content asserts that the
    following tokens do **not** appear anywhere on the
    Universe tab (case-insensitive):
    - `impact`, `outcome`, `risk score`, `risk_score`
    - `forecast`, `prediction`, `expected return`,
      `target price`
    - `recommendation`, `investment advice`
    - `amplify`, `dampen`, `offset effect`, `coexist`
    - `dominant stress`, `net pressure`, `composite risk`
    - `magnitude`, `basis points`, `bps`, `percent intensity`
    The forbidden-token list composes with the v1.20.5 UI
    forbidden-token list.
12. **Existing Universe heatmap still renders.** The
    11×9 sector sensitivity heatmap selector still exists and
    still has 11 rows × 9 columns. The strip MUST NOT have
    displaced or resized the heatmap.
13. **Existing firm-profile table still renders.** The
    11×6 firm-profile table selector still exists and still
    has 11 rows × 6 columns.
14. **Existing 5-step scenario causal trace still renders.**
    The 5-step trace selector still exists and still has 5
    steps.
15. **No backend / fetch / XHR / eval.** A scan over the
    static HTML asserts the file contains no `fetch(`,
    no `XMLHttpRequest`, no `eval(`, no
    `new Function(`, no `<script src="http`, and no
    `<script src="https`. (Already pinned by v1.19.4 /
    v1.20.5; v1.22.2 re-pins.)
16. **No `innerHTML` on user-loaded JSON paths.** A scan
    over the embedded JS asserts that the paths reading from
    the loaded `stress_readout` use `textContent` only —
    never `innerHTML`. (Convention from v1.20.5.)

### 6.3 What v1.22.0 ships in tests

**Nothing.** v1.22.0 is docs-only. Test count holds at 4865.

---

## 7. Roadmap (binding for the v1.22 sequence)

| Sub-milestone | Surface     | Description                                                                                                              | Status                |
| ------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------- |
| **v1.22.0**   | docs only   | This design note + §131 in `world_model.md` + roadmap-row refresh. Test count: 4865 / 4865 (unchanged).                  | **Design scoped (this PR)** |
| v1.22.1       | export code | New `stress_readout` payload section on `RunExportBundle`. Empty when no stress program; preserves all v1.21.last digests. New tests under `tests/test_run_export_stress_readout.py` (≈ 13 tests per §6.1). | Not started.          |
| v1.22.2       | static UI   | Active Stresses strip in the existing Universe tab. Reads the v1.22.1 section. New tests under `tests/test_ui_active_stresses_strip.py` (≈ 16 tests per §6.2). | Not started.          |
| v1.22.last    | docs only   | Final freeze. Sequence map, what-v1.22-is / what-v1.22-is-NOT, pinned test count, preserved digests, hard-boundary re-pin, future optional candidates. | Not started.          |

The sequence is **strictly serial**: v1.22.2 must not start
until v1.22.1's bundle schema is byte-stable and its tests are
green. v1.22.1 must not start until this v1.22.0 design note
is merged.

**Cardinality (binding for the v1.22 sequence):**

- v1.22 adds **0 new dataclasses** (no new record type, no
  new book).
- v1.22 adds **0 new ledger event types**.
- v1.22 adds **0 new label vocabularies** (every label
  rendered comes from v1.18.1 / v1.21.x closed sets).
- v1.22 adds **1 new bundle payload key** (`stress_readout`).
- v1.22 adds **1 new UI region** (the Active Stresses strip
  inside the existing Universe tab).
- v1.22 adds **0 new tabs** (11-tab ↔ 11-sheet bijection
  preserved).
- v1.22.1 expected test delta: **+ ~ 13** (per §6.1).
- v1.22.2 expected test delta: **+ ~ 16** (per §6.2).
- Final v1.22.last test count target: **~ 4894** (subject to
  exact test-count pin at each sub-milestone).

---

## 8. Hard boundary (re-pinned at v1.22.0)

v1.22 inherits and re-pins the v1.21.last hard boundary in full;
the boundary expands to cover the new bundle section and the new
UI region. The full boundary at v1.22.0 is therefore:

**No real-world output.**
- No price formation, no market price.
- No forecast path, no expected return, no target price.
- No magnitude, no probability, no expected response.
- No firm decision, no investor action, no bank approval logic.
- No order, no trade, no execution, no clearing, no settlement.
- No financing execution, no investment advice, no
  recommendation.

**No real-world input.**
- No real data ingestion.
- No real institutional identifiers.
- No licensed taxonomy dependency.
- No Japan calibration.

**No autonomous reasoning.**
- No LLM execution (browser or backend).
- No LLM prose accepted as source-of-truth.
- `reasoning_mode = "rule_based_fallback"` remains binding.
- No interaction auto-inference.
- No aggregate / combined / net / dominant / composite stress
  output.

**No source-of-truth book mutation.**
- v1.22.1 adds an export-side projection. It does not write to
  any kernel book. Pre-existing book snapshots remain
  byte-identical pre / post any v1.22 export call.

**No backend in the UI.**
- The v1.22.2 strip reads the loaded JSON from
  `<input type="file">` + `FileReader` + `JSON.parse`.
- No `fetch`, no XHR, no backend, no file-system write, no
  `eval`, no Python execution from the browser.

**No digest movement at v1.22.x.**
- Empty-section omission strategy (§3.2) keeps every existing
  digest byte-identical.
- v1.22.last must pin **`pytest -q`: 4865 + Δ / 4865 + Δ**
  with Δ being the v1.22.1 + v1.22.2 test additions, and
  must list every preserved digest verbatim.

---

## 9. Future optional candidates (NOT planned, NOT scoped)

The v1.22 sequence ends at v1.22.last. The following are
**candidates only** — none is on the v1.22 roadmap, none is a
v1.22.x sub-milestone, each requires a fresh design pin if ever
picked up:

- **v1.22.x manual_annotation interaction layer (deferred from
  v1.21.0a §130.7).** A `manual_annotation`-only annotation
  layer over the v1.21.3 multiset readout. MUST NEVER be
  inferred by a helper, a classifier, a closed-set rule
  table, an LLM, or any other automated layer. MUST cite
  explicit evidence from the multiset readout. MUST NOT
  replace the readout.
- **v1.23 Institutional Investor Mandate / Benchmark
  Pressure.** Bounded synthetic mandate / benchmark / peer-
  pressure constraints on the v1.15.5 / v1.16.2 investor-
  intent layer. Decoupled from the v1.21 / v1.22 stress
  surface.

Silent extension of v1.22 — for example, a per-month
downstream-citation split that v1.22.1 does not surface — is
forbidden. Any such extension must land under a fresh design
pin.

---

## 10. Read-in order (for a v1.22 reviewer)

1. [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
   §*UI guidance (binding for v1.21.3 / future)* — the
   binding shape v1.22 implements.
2. This document — the v1.22 design pin.
3. [`world_model.md`](world_model.md) §131 — the
   constitutional position of v1.22.
4. [`research_note_001_stress_composition_without_outcome_inference.md`](research_note_001_stress_composition_without_outcome_inference.md)
   — the research framing v1.22 inherits.
5. [`v1_19_local_run_bundle_and_monthly_reference_summary.md`](v1_19_local_run_bundle_and_monthly_reference_summary.md)
   — the existing CLI export + static-loader contract that
   v1.22.1 / v1.22.2 extend.
6. [`v1_20_monthly_scenario_reference_universe_summary.md`](v1_20_monthly_scenario_reference_universe_summary.md)
   — the existing Universe tab v1.22.2 extends.

A reviewer who has read these six items in order should be
able to read the v1.22.1 / v1.22.2 PRs without surprise: each
PR will land exactly the surface this document pins, no more
and no less.

---

## 11. Deliverables for v1.22.0 (this PR)

- This design note: `docs/v1_22_static_ui_stress_readout_reflection.md`.
- New section §131 in `docs/world_model.md` — "v1.22 Static UI
  Stress Readout Reflection (design pointer, **v1.22.0
  design-only**)".
- Roadmap-row refresh in
  `docs/v1_20_monthly_scenario_reference_universe_summary.md`
  — the optional-candidate "v1.21.3 markdown summary UI strip"
  row is replaced by a v1.22.0 design-scoped row.
- README anchor refresh in `README.md` §9 — the v1.22 candidate
  row is updated from "Optional candidate. Not started.
  Requires a fresh design pin." to "Design scoped at v1.22.0".

No runtime code change. No UI implementation. No new tests. No
new dataclass. No new ledger event. No new label vocabulary. No
digest movement. No record-count change. No pytest-count
change.

---

## v1.22.last freeze (docs-only)

v1.22.last closes the v1.22 sequence as a **read-only
reflection of the v1.21.3 stress readout in the existing
v1.20.5 static workbench**, shipped via:

- **v1.22.1** — descriptive-only `stress_readout` payload
  section on `RunExportBundle`, omitted from JSON when
  empty (preserves all v1.21.last digests byte-identical).
- **v1.22.2** — Active Stresses strip in the existing
  Universe sheet, above the existing sector heatmap. No new
  tab. No backend. No Python execution from the browser.
- **v1.22.last** — this freeze section (docs-only).

v1.22.last itself is **docs-only** on top of the v1.22.0 →
v1.22.1 → v1.22.2 code freezes. No new module. No new test.
No new ledger event. No new label vocabulary. No behavior
change. No record-count change. No digest movement.

### Shipped sequence

| Milestone     | Surface                                                                  | What it shipped                                                                                                                                                                                                                                                                       |
| ------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| v1.22.0       | docs only                                                                | This design note (sections 1–11 above) + §131 in `world_model.md` + roadmap-row refresh in `README.md` and `v1_20_monthly_scenario_reference_universe_summary.md`. Test count: 4865 / 4865 (unchanged).                                                                                |
| v1.22.1       | export code: `world/run_export.py` + `world/stress_readout_export.py` (NEW) + `examples/reference_world/export_run_bundle.py` | New top-level `stress_readout` payload section on `RunExportBundle` (descriptive-only, 19-key whitelist, empty-by-default, omitted from JSON when empty); kernel-aware projection helper `build_stress_readout_export_section`; wired into all three CLI bundle builders. **+13 tests.** |
| v1.22.2       | static UI: `examples/ui/fwe_workbench_mockup.html` (+~650 lines)         | Active Stresses strip inside the existing Universe sheet, above the existing sector heatmap. Read-only static rendering only. `<input type="file">` + `FileReader` + `JSON.parse` discipline preserved. `textContent` only. **+15 tests.**                                            |
| **v1.22.last**| docs only (this section)                                                 | This freeze section + §131.9 freeze in `world_model.md` + refreshed roadmap rows in `README.md` and `v1_20_monthly_scenario_reference_universe_summary.md`.                                                                                                                            |

### What v1.22 is

- A **read-only reflection** of the v1.21.3 stress
  readout. v1.22 produces no new readout; it surfaces the
  v1.21.3 multiset projection and the per-step resolution
  state via two new artifacts (one bundle payload section,
  one UI region).
- An **export-side projection** (`stress_readout`, 19
  descriptive-only keys, empty-by-default with omission
  discipline) that lets a downstream consumer render the
  readout without re-running the engine.
- A **single new UI region** (the Active Stresses strip
  inside the existing Universe sheet) that renders the
  payload section verbatim.

### What v1.22 is NOT (binding)

- v1.22 is **NOT** a new readout. v1.21.3
  `StressFieldReadout` remains the authoritative read-only
  projection.
- v1.22 is **NOT** a stress-impact view — no outcome
  metric, no bar height, no score, no numeric intensity, no
  red / green encoding, no arrows implying causal
  propagation.
- v1.22 is **NOT** an interaction-inference view — no
  `amplify` / `dampen` / `offset` / `coexist` label is
  inferred or rendered as primary UI text.
- v1.22 is **NOT** a backend-enabled UI — no `fetch`, no
  XHR, no WebSocket, no Python execution from the browser,
  no file-system write, no `eval`, no `new Function(`.
- v1.22 does **NOT** change any export digest for a no-
  stress run profile. The empty-section omission strategy
  in `RunExportBundle.to_dict()` keeps every v1.21.last
  digest byte-identical.
- v1.22 does **NOT** mutate any source-of-truth book. The
  v1.22.1 export helpers are read-only by construction;
  the v1.22.2 UI is rendering-only.
- v1.22 does **NOT** introduce a new tab. The v1.20.5
  11-tab ↔ 11-sheet bijection is preserved.

### Final freeze pin (binding)

| Surface                                                                                       | Value                                                                       |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `pytest -q`                                                                                   | **4893 / 4893 passing**                                                     |
| `python -m compileall -q world spaces tests examples`                                         | clean                                                                       |
| `ruff check .`                                                                                | clean                                                                       |
| Test count delta vs. v1.21.last                                                                | **+28 tests** (4865 → 4893): v1.22.1 (+13) / v1.22.2 (+15)                  |
| `quarterly_default` `living_world_digest`                                                     | **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`** (byte-identical to v1.21.last) |
| `monthly_reference` `living_world_digest`                                                     | **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`** (byte-identical to v1.21.last) |
| `scenario_monthly_reference_universe` test-fixture `living_world_digest`                       | **`5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`** (byte-identical to v1.21.last) |
| v1.20.4 CLI export bundle digest (no-stress profile)                                           | **`ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`** (byte-identical to v1.21.last) |
| Source-of-truth book mutation count                                                            | **0**                                                                       |
| Ledger emissions from v1.22.x helpers                                                          | **0**                                                                       |
| New ledger event types                                                                         | **0**                                                                       |
| New label vocabularies                                                                         | **0**                                                                       |
| New dataclasses                                                                                | **0** (v1.21.3 `StressFieldReadout` reused)                                  |
| New tabs                                                                                       | **0** (11-tab ↔ 11-sheet bijection preserved)                               |

### Design-pin vs implementation drift (resolved at v1.22.last)

The original v1.22.0 design note at §4.3 / §4.4 (above)
prescribed a **12 monthly cells** strip layout — one cell
per monthly period, each listing the active stress family
tokens with hover-revealed multisets. The v1.22.2 brief
**simplified** this to **per-readout-entry rendering**: one
block per `stress_readout` entry, with summary cells
(`as_of_date` / template id / `resolved / total` counter),
multiset projections (context surfaces / shift directions /
scenario families), citation lists, warnings, and a Raw
canonical labels technical-details box. The shipped v1.22.2
implementation follows the brief, not the original §4.3 /
§4.4 sketch.

This drift is **resolved at v1.22.last by accepting the
shipped per-entry rendering as the binding v1.22 surface**.
The §4.3 / §4.4 12-monthly-cell text above is **superseded**
and preserved only for git-history continuity. Future
contributors reading this document should treat §4.3 / §4.4
as historical sketch and the v1.22.last freeze section as
the authoritative spec.

The simplification is consistent with the v1.21.0a doctrine
that the audit value is in the **citations + per-step
resolution state**, not in any visualisation that risks
being read as a temporal causal claim. Per-entry rendering
makes the readout's structure (one entry per program
application, citation arrays preserved in emission order)
visible without overlaying a synthetic timeline that would
have invited "this stress happened in month N → that
stress happened in month N+1, therefore …" misreadings.

### Hard boundary (re-pinned at v1.22.last)

v1.22.last carries forward every v1.21.last hard boundary in
full. The boundary list at v1.22.last is therefore identical
to v1.21.last, plus the v1.22.x-specific UI / export
boundaries pinned in §7 / §8 above:

- **No real-world output** — no price formation, no forecast
  path, no expected return, no target price, no order /
  trade / execution / clearing / settlement / financing
  execution, no firm decision / investor action / bank
  approval, no recommendation / investment advice.
- **No real-world input** — no real data, no real
  institutional identifiers, no licensed taxonomy
  dependency, no Japan calibration.
- **No autonomous reasoning** — no LLM execution at runtime,
  no LLM prose as source-of-truth, `reasoning_mode =
  "rule_based_fallback"` binding, no interaction
  auto-inference (`amplify` / `dampen` / `offset` /
  `coexist` deferred to v1.22+ as `manual_annotation`-only).
- **No source-of-truth book mutation** — every pre-existing
  book byte-identical pre / post any v1.22 call.
- **No backend in the UI** — `<input type="file">` +
  `FileReader` + `JSON.parse` only.
- **No digest movement** — empty-section omission
  discipline preserves every v1.21.last digest
  byte-identical for the no-stress run profiles.

### Future optional candidates (NOT planned, NOT scoped)

The v1.22 sequence ends here. None of the following is on
the roadmap; each requires a fresh design pin under a new
milestone:

- **v1.23 candidate — Institutional Investor Mandate /
  Benchmark Pressure.** Bounded synthetic mandate /
  benchmark / peer-pressure constraints on the v1.15.5 /
  v1.16.2 investor-intent layer. Decoupled from the v1.21 /
  v1.22 stress surface.
- **manual_annotation interaction layer (post-v1.22,
  optional).** A `manual_annotation`-only annotation layer
  over the v1.21.3 multiset readout. Human-authored only;
  never auto-inferred by a helper, a classifier, a closed-
  set rule table, an LLM, or any other automated layer.
  MUST cite explicit evidence from the multiset readout.
  MUST NOT replace the readout.
- **A `bundle_schema_version` field on `RunExportBundle`.**
  v1.22.1's omission discipline keeps no-stress bundles
  byte-identical with pre-v1.22 bundles, which means a
  consumer cannot distinguish a v1.21.last-era bundle from
  a v1.22.1+ no-stress bundle. A future schema-version
  field would address this; it is not v1.22.x scope.
- **A consolidated forbidden-name composition.** The four
  v1.21.x forbidden frozensets compose explicitly; the
  v1.19.0 `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` predates v1.21
  and does not yet compose with the stress sets. A future
  consolidation pass could reduce the maintenance burden
  before v1.23 ships.

These are **candidates**, not commitments. The v1.22
sequence is frozen as-is.

### Read-in order (for a v1.22 reviewer)

1. [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
   — the v1.21 layer v1.22 reflects.
2. This document — the v1.22 design pin (this freeze section
   is the authoritative shipped spec; §4.3 / §4.4 above are
   superseded historical sketch).
3. [`world_model.md`](world_model.md) §131.1 — §131.9 — the
   constitutional position of v1.22.
4. [`research_note_001_stress_composition_without_outcome_inference.md`](research_note_001_stress_composition_without_outcome_inference.md)
   — the research framing v1.22 inherits.

The v1.22 sequence is **complete and frozen**. Subsequent
work that touches the stress-readout reflection layer must
explicitly re-open scope under a new design pin (a
v1.22.last-correction or a v1.23+ surface); silent extension
is forbidden.
