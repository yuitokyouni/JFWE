# Release Checklist

A short, runnable checklist to walk before publicly tagging or
announcing a release of this repository. Most items are local
commands; a few are eyes-on review steps. The list is intentionally
short so it is actually used.

For the public / private rules these checks enforce, see
[`SECURITY.md`](SECURITY.md) and
[`japan-financial-world/docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md).

## Public release gate (must be green for a public release)

A **public release tag** (e.g., `v1.8-public-release`) requires CI
to be green on the commit being tagged. CI runs the items below
automatically; this section is the manual mirror so you can
reproduce locally before pushing.

### Latest readiness-review snapshot

Each readiness review records its result here so the next reviewer
can pick up where the last one stopped. Replace the snapshot when a
new review is performed.

- **Date:** 2026-05-05
- **Target:** v1.20.last monthly-scenario-reference-universe
  freeze. The v1.19.last local-run-bundle /
  monthly-reference freeze (snapshot below), the v1.18.last
  scenario-driver-library freeze, the v1.17.last
  inspection-layer freeze, the v1.16.last
  endogenous-market-intent feedback freeze, the v1.15.last
  securities-market-intent aggregation freeze, the
  v1.14.last corporate-financing-intent freeze, the
  v1.13.last settlement-substrate freeze, the v1.12.last
  endogenous-attention-loop freeze, the v1.9.last public-
  prototype freeze, and the v1.8.0 public release
  (`v1.8-public-release` at commit `7fa2c42`) all remain
  unchanged; v1.20.last freezes the v1.20 sequence as the
  **first public-FWE milestone where the engine moves from a
  small closed-loop demo to a richer synthetic market-like
  reference universe** — 12 monthly periods × 11 generic
  sectors × 11 representative synthetic firm profiles × 4
  investor archetypes × 3 bank archetypes × 51 information
  arrivals × 1 scheduled scenario application × 2 scenario
  context shifts × 11 affected sector ids × 11 affected firm
  profile ids; the chain stays CLI-first: a user runs
  `python -m examples.reference_world.export_run_bundle
  --profile scenario_monthly_reference_universe
  --regime constrained --scenario credit_tightening_driver
  --out /tmp/fwe_scenario_universe_bundle.json` to produce a
  deterministic JSON, then loads it in the static workbench
  via `<input type="file">` + `FileReader.readAsText` —
  **no fetch, no XHR, no backend, no engine execution from
  the browser, no file-system write**. The static workbench
  gains a new **Universe** tab between Overview and Timeline
  (11 tabs ↔ 11 sheets — bijection preserved) with an
  11-row × 9-column sector sensitivity heatmap, an 11-row ×
  6-column firm profile table, and a 5-step scenario causal
  trace. Sector labels carry the `_like` suffix and no
  public-FWE module text or test depends on bare `GICS`,
  `MSCI`, `S&P`, `FactSet`, `Bloomberg`, `Refinitiv`,
  `TOPIX`, `Nikkei`, or `JPX` tokens; firm ids follow the
  synthetic `firm:reference_<sector>_a` pattern. v1.20.last
  itself is docs-only on top of the v1.20.0 → v1.20.5 code
  freezes. The chain is **CLI-first / read-only-loader /
  opt-in profile / no-backend** — no price formation, no
  market price, no predicted index, no forecast path, no
  expected return, no target price, no trading, no orders,
  no execution, no clearing, no settlement, no financing
  execution, no direct firm decisions, no direct investor
  actions, no bank approval logic, no investment advice, no
  real data ingestion, no Japan calibration, no LLM
  execution, no daily simulation, no browser-to-Python
  execution, no Rails, no FastAPI, no Flask. Per-period
  record count **257 / 261**, per-run record counts **3220**
  (profile canonical fixture) / **3241** (CLI export bundle
  `manifest.record_count` under `--regime constrained`) —
  both within the v1.20.0 target `[2400, 3360]` and well
  under the hard guardrail `≤ 4000`; the **+21 record delta
  is fully explained by the v1.11.2 `_REGIME_PRESETS["constrained"]`
  preset** and confined to the `observation_set_selected`
  record type. `reasoning_mode = "rule_based_fallback"`
  remains binding at v1.20.x. Known limitations: 11 firms is
  a *reference fixture*, not a real-issuer set; the
  five-rung sensitivity vocabulary is a label set, not a
  numeric calibration; scenario context shifts are bounded
  evidence-level annotations, not direct decisions; no real
  data; no Japan calibration; no investment recommendation
  surface; daily-frequency economic simulation remains
  out-of-scope.
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.20.last):**
  - `pytest -q` → 4764 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.export_run_bundle
    --profile scenario_monthly_reference_universe
    --regime constrained
    --scenario credit_tightening_driver
    --out /tmp/fwe_scenario_universe_bundle.json` → writes a
    deterministic JSON; same args → byte-identical bytes;
    bundle JSON contains no ISO wall-clock, no absolute
    path, no `$USER` / `$HOSTNAME`; bundle digest =
    **`ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`**.
  - `bundle.manifest.record_count` = **3241** (CLI fixture);
    `bundle.manifest.sector_count` = **11**;
    `bundle.manifest.firm_count` = **11**;
    `bundle.manifest.investor_count` = **4**;
    `bundle.manifest.bank_count` = **3**;
    `bundle.manifest.scheduled_scenario_application_count` = **1**;
    `bundle.manifest.scenario_application_count` = **1**;
    `bundle.manifest.scenario_context_shift_count` = **2**;
    `bundle.manifest.information_arrival_count` = **51**.
  - `bundle.scenario_trace.affected_sector_ids` count = **11**
    (universe-wide); `bundle.scenario_trace.affected_firm_profile_ids`
    count = **11** (universe-wide).
  - profile canonical record count under the v1.20.3 default
    test fixture = **3220** (no `market_regime` kwarg);
    `scenario_monthly_reference_universe` `living_world_digest`
    = **`5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`**
    (pinned by
    `tests/test_living_reference_world_performance_boundary.py::test_v1_20_3_living_world_digest_is_pinned`).
  - integration-test fixture `living_world_digest`
    (`quarterly_default`) =
    **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
    (unchanged from v1.18.last across the entire v1.19 +
    v1.20 sequence — pinned across the whole v1.20 chain by
    per-book trip-wire tests).
  - `monthly_reference` `living_world_digest` =
    **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**
    (unchanged from v1.19.last).
  - `examples/ui/fwe_workbench_mockup.html` → opens directly
    under `file://` with no console errors. The bottom-tabs
    nav now lists 11 tabs / 11 sheets with the new
    **Universe** tab between Overview and Timeline; clicking
    each tab activates the matching sheet (bijection holds).
    The **Load local bundle** button accepts the new
    `scenario_monthly_reference_universe` JSON via
    `FileReader` + `JSON.parse`, validates the v1.19.1
    schema + v1.19.0 default 8-flag boundary block + v1.20.5
    profile-conditional schema (`metadata.reference_universe`
    with non-empty `sector_labels` + `firm_profile_ids`
    arrays; `scenario_trace.affected_sector_ids` +
    `affected_firm_profile_ids` arrays;
    `manifest.{sector,firm,investor,bank}_count` exact match
    11/11/4/3); renders the Universe tab's 11-row × 9-column
    sector sensitivity heatmap, 11-row × 6-column firm
    profile table, and 5-step scenario causal trace. The
    profile badge shows in distinct amber colour for the
    universe profile (vs blue for `monthly_reference` and
    green for `quarterly_default`). The pre-existing
    `quarterly_default` and `monthly_reference` rendering
    paths are unchanged. Rejects `scenario_monthly` /
    `daily_display_only` / `future_daily_full_simulation`
    with the v1.19.4 status message. Renders user-loaded
    values via `textContent` only — never `innerHTML` for
    user JSON; no `eval`; no `fetch` / XHR; no backend; no
    file-system write; no `location.hash` mutation during
    bundle load; capture-and-restore around scroll position
    so the load never causes a scroll jump or active-sheet
    shift. `Validate` reports `validation passed · static UI`
    with the seven new v1.20.5 audit checks.
  - Forbidden-token scan + public-wording audit + public /
    private boundary review + no-confidential-content audit +
    no-real-data audit + no-behavior-probability audit — all
    unchanged from v1.19.last; the v1.20-specific forbidden-
    token scan additionally pins the absence of bare
    licensed-taxonomy tokens (`gics` / `msci` / `factset` /
    `bloomberg` / `refinitiv` / `topix` / `nikkei` / `jpx`)
    in `world/reference_universe.py`,
    `world/scenario_schedule.py`, the v1.20.4 CLI module,
    and the rendered v1.20.4 bundle JSON; the v1.20.0
    `_like`-suffix discipline is pinned on every sector
    label except `unknown` by
    `tests/test_reference_universe.py::test_sector_labels_all_carry_like_suffix_except_unknown`.

#### v1.19.last historical snapshot (unchanged)

- **Date:** 2026-05-05
- **Target:** v1.19.last local-run-bundle / monthly-reference
  freeze. The v1.18.last scenario-driver-library freeze
  (snapshot below), the v1.17.last inspection-layer freeze,
  the v1.16.last endogenous-market-intent feedback freeze,
  the v1.15.last securities-market-intent aggregation freeze,
  the v1.14.last corporate-financing-intent freeze, the
  v1.13.last settlement-substrate freeze, the v1.12.last
  endogenous-attention-loop freeze, the v1.9.last public-
  prototype freeze, and the v1.8.0 public release
  (`v1.8-public-release` at commit `7fa2c42`) all remain
  unchanged; v1.19.last freezes the v1.19 sequence as the
  **first public-FWE local-run-bundle inspection layer** —
  CLI generates a deterministic `RunExportBundle` JSON
  (v1.19.1) for either `quarterly_default` (v1.19.2) or the
  new `monthly_reference` profile (v1.19.3 + v1.19.3.1); the
  static workbench reads the JSON via `<input type="file">`
  + `FileReader.readAsText` + `JSON.parse` (v1.19.4) — **no
  fetch, no XHR, no backend, no engine execution from the
  browser, no file-system write**. The `monthly_reference`
  profile reuses the existing v1.16 closed loop on a
  12-month synthetic schedule and emits 3-5 information
  arrivals per month (51 total) from a jurisdiction-neutral
  synthetic `InformationReleaseCalendar` — **information
  arrival is not data ingestion**; no real values, no real
  release dates, no real institutional identifiers; Japan
  release cadence is a design reference only. v1.19.last
  itself is docs-only on top of the v1.19.0 → v1.19.4 code
  freezes (plus the v1.19.3.1 reconciliation follow-up). The
  chain is **CLI-first / read-only-loader / opt-in-monthly /
  no-backend** — no price formation, no market price, no
  predicted index, no forecast path, no expected return, no
  target price, no trading, no orders, no execution, no
  clearing, no settlement, no financing execution, no
  investment advice, no real data ingestion, no Japan
  calibration, no LLM execution, no daily simulation, no
  browser-to-Python execution, no Rails, no FastAPI, no
  Flask. `reasoning_mode = "rule_based_fallback"` remains
  binding at v1.19.x. Known limitations: `monthly_reference`
  is still synthetic (no real CPI / GDP / policy-rate
  values); information arrivals are categories, not values;
  UI loading is read-only; `scenario_monthly` is not yet
  executable; `daily_display_only` is not economic
  simulation; no live run button — the user runs the CLI in
  a terminal, then loads the JSON.
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.19.last):**
  - `pytest -q` → 4522 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → unchanged from v1.18.last on the default `quarterly_default`
    profile; produces the same `[setup]` / `[period N]` /
    `[ledger]` trace and the same default-fixture record set.
  - integration-test fixture `living_world_digest`
    (`quarterly_default`) =
    **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
    (unchanged from v1.18.last across the entire v1.19 sequence
    — pinned by per-book trip-wire tests at v1.19.1 /
    v1.19.2 / v1.19.3 / v1.19.3.1).
  - `monthly_reference` `living_world_digest` =
    **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**
    with **3-5 arrivals / month, 51 / 12 months** (within the
    [36, 60] design budget, pinned by
    `tests/test_living_reference_world.py::test_v1_19_3_monthly_reference_living_world_digest_is_pinned`).
  - `python -m examples.reference_world.export_run_bundle
    --profile quarterly_default --regime constrained
    --scenario none_baseline --out /tmp/q.json` → writes a
    deterministic JSON; same args → byte-identical bytes;
    bundle JSON contains no ISO wall-clock, no absolute
    path, no `$USER` / `$HOSTNAME`.
  - `python -m examples.reference_world.export_run_bundle
    --profile monthly_reference --regime constrained
    --scenario none_baseline --out /tmp/m.json` → writes a
    deterministic monthly bundle whose
    `metadata.information_arrival_summary` carries
    `arrival_count = 51` across 7 indicator families.
  - `examples/ui/fwe_workbench_mockup.html` → opens directly
    under `file://` with no console errors. The new
    **Load local bundle** button reads either the quarterly
    or monthly JSON via `FileReader` + `JSON.parse`,
    validates the v1.19.1 schema + v1.19.0 default 8-flag
    boundary block, accepts `quarterly_default` /
    `monthly_reference`, rejects `scenario_monthly` /
    `daily_display_only` / `future_daily_full_simulation`
    with `bundle profile '<profile>' is not loadable in
    v1.19.4 static UI`. Renders user-loaded values via
    `textContent` only; caps the ledger excerpt at 20 rows.
    `current_data_source` label correctly tracks
    `inline_fixture` / `sample_manifest` / `local_bundle`.
    `Validate` reports `validation passed · static UI`.
  - Forbidden-token scan + public-wording audit + public /
    private boundary review + no-confidential-content audit +
    no-real-data audit + no-behavior-probability audit — all
    unchanged from v1.18.last.

#### v1.18.last historical snapshot (unchanged)

- **Date:** 2026-05-04
- **Target:** v1.18.last scenario-driver-library freeze. The
  v1.17.last inspection-layer freeze (snapshot below), the
  v1.16.last endogenous-market-intent feedback freeze, the
  v1.15.last securities-market-intent aggregation freeze, the
  v1.14.last corporate-financing-intent freeze, the v1.13.last
  settlement-substrate freeze, the v1.12.last endogenous-
  attention-loop freeze, the v1.9.last public-prototype
  freeze, and the v1.8.0 public release
  (`v1.8-public-release` at commit `7fa2c42`) all remain
  unchanged; v1.18.last freezes the v1.18 sequence as the
  **first public-FWE scenario-driver inspection layer** over
  the v1.17 inspection surface and the v1.16 closed loop.
  The layer adds *scenario inspectability*, not new economic
  behaviour — a `ScenarioDriverTemplate` storage book
  (v1.18.1), an append-only `ScenarioDriverApplicationRecord`
  / `ScenarioContextShiftRecord` helper that emits new records
  citing the scenario driver via plain-id citations and never
  mutates a pre-existing context record (v1.18.2), three
  pure-function display helpers + a deterministic markdown
  scenario report driver (v1.18.3), and a static UI scenario
  selector mock with seven options (Baseline / Rate repricing
  / Credit tightening / Funding window closure / Liquidity
  stress / Information gap / Unmapped fallback) on the v1.17.4
  workbench (v1.18.4). v1.18.last itself is docs-only on top
  of the v1.18.0 → v1.18.4 code freezes. The chain is
  **append-only / stimulus-only / inspection-only** — scenario
  driver is the stimulus, never the response; no firm
  decisions, no investor actions, no bank approval logic, no
  price formation, no market price, no predicted index, no
  forecast path, no expected return, no target price, no
  trading, no orders, no execution, no clearing, no
  settlement, no financing execution, no investment advice,
  no real data ingestion, no Japan calibration, no LLM
  execution, no LLM prose as source-of-truth, no stochastic
  behaviour probabilities, no learned model, no mutation of
  pre-existing context records. `reasoning_mode =
  "rule_based_fallback"` is binding at v1.18.x; the
  `future_llm_compatible` slot marker is an architectural
  commitment, not a runtime capability. The static workbench
  scenario selector has no backend, no build, no external
  runtime, no network I/O — `Run mock` switches `(regime,
  scenario)` fixtures, never invokes the Python engine. Known
  limitations: scenario templates are synthetic, not
  forecasts; application is rule-based fallback (5 family→shift
  mappings + a `no_direct_shift` fallback); actor response
  stays in existing / future mechanisms; no scenario is
  calibrated to real data; the UI scenario selector is a mock,
  not live execution; the `no_direct_shift` fallback means
  *stored but not yet mapped to a concrete context surface*
  and is tagged in the report and UI as "this is not an
  error".
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.18.last):**
  - `pytest -q` → 4334 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → unchanged from v1.17.last; produces the same `[setup]` /
    `[period N]` / `[ledger]` trace and the same default-fixture
    record set as at v1.17.last. v1.18 added zero records to
    the per-period sweep when no scenario is applied.
  - integration-test fixture `living_world_digest` =
    **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
    (unchanged from v1.17.last across the entire v1.18 sequence
    when no scenario is applied — pinned by per-book trip-wire
    tests at v1.18.1 / v1.18.2 / v1.18.3:
    `tests/test_scenario_drivers.py::test_empty_scenario_drivers_does_not_move_default_living_world_digest`,
    `tests/test_scenario_applications.py::test_empty_scenario_applications_does_not_move_default_living_world_digest`,
    `…::test_explicit_scenario_application_does_not_touch_default_run`,
    `tests/test_display_timeline.py::test_scenario_helpers_do_not_move_default_living_world_digest`,
    `tests/test_scenario_report.py::test_run_scenario_report_does_not_move_default_living_world_digest`)
  - `python -m examples.reference_world.scenario_report` →
    produces a deterministic markdown report rendering the
    v1.18.2 application chain (template / application /
    context shift / event annotation / causal annotation) for
    a six-template default fixture exercising all five
    v1.18.2 mappings plus the `no_direct_shift` fallback.
    Same fixture + same `as_of_date` → byte-identical
    markdown.
  - `examples/ui/fwe_workbench_mockup.html` → opens directly
    under `file://` with no console errors. Bottom-tab ↔ sheet
    article 1:1 bijection enforced at runtime by the in-page
    `Validate` button. Inline JSON parses; standalone
    `sample_living_world_manifest.json` parses; both carry the
    v1.18.4 `scenario_selector` / `scenario_fixtures` /
    `scenario_trace` / `selected_scenario` keys. `Run mock`
    switches `(regime, scenario)` fixtures across the four
    regimes × seven scenarios; the status line reads
    `mock UI run · <regime> · <scenario> · static fixture · no
    engine execution`. Picking `Unmapped fallback` surfaces
    the `no_direct_shift` callout verbatim. Long plain-id
    citation wrapping fixed at v1.18.4 (`table-layout: fixed`
    + `overflow-wrap: anywhere`); the page no longer overflows
    the viewport when Run mock fills the scenario trace
    tables. `Validate` reports `validation passed · static
    UI`. Constant `static fixture only · no backend execution`
    sub-status visible at all times.
  - Forbidden-token scan + public-wording audit + public /
    private boundary review + no-confidential-content audit +
    no-real-data audit + no-behavior-probability audit — all
    unchanged from v1.17.last.

#### v1.17.last historical snapshot (unchanged)

- **Date:** 2026-05-04
- **Target:** v1.17.last inspection-layer freeze. The
  v1.16.last endogenous-market-intent feedback freeze (snapshot
  below), the v1.15.last securities-market-intent aggregation
  freeze, the v1.14.last corporate-financing-intent freeze, the
  v1.13.last settlement-substrate freeze, the v1.12.last
  endogenous-attention-loop freeze, the v1.9.last public-
  prototype freeze, and the v1.8.0 public release
  (`v1.8-public-release` at commit `7fa2c42`) all remain
  unchanged; v1.17.last freezes the v1.17 sequence as the
  **first public-FWE inspection layer** over the v1.16 closed
  loop. The layer adds *inspectability*, not new economic
  behavior — a `ReportingCalendar` + `SyntheticDisplayPath`
  (v1.17.1), a regime-comparison report (v1.17.2), event /
  causal annotations with environment-subfield enrichment
  (v1.17.3), and a single-file static analyst workbench
  reorganised around the closed loop with ten bottom tabs in
  strict 1:1 bijection with ten sheet articles (v1.17.4).
  v1.17.last itself is docs-only on top of the v1.17.0 →
  v1.17.4 code freezes. The chain is **inspection / rendering
  only** — no price formation, no market price, no predicted
  index, no forecast path, no expected return, no target price,
  no trading, no orders, no execution, no clearing, no
  settlement, no investment advice, no real data, no Japan
  calibration, no LLM execution, no stochastic behaviour
  probabilities, no learned model, no new economic
  source-of-truth records. The static workbench has no backend,
  no build, no external runtime, no network I/O — `Run mock` is
  fixture switching, `Compare Regimes` is display-report
  navigation, `Export HTML` is a non-destructive status update.
- **Status:** historical snapshot, preserved unchanged.
- **Local results (v1.17.last):** `pytest -q` → 4165 passed;
  `compileall` clean; `ruff check .` clean;
  `living_world_digest` =
  `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`.

#### v1.16.last historical snapshot (unchanged)

- **Date:** 2026-05-04
- **Target:** v1.16.last endogenous market intent feedback
  freeze. The v1.15.last securities-market-intent aggregation
  freeze (snapshot below), the v1.14.last corporate-financing-
  intent freeze, the v1.13.last settlement-substrate freeze,
  the v1.12.last endogenous-attention-loop freeze, the
  v1.9.last public-prototype freeze, and the v1.8.0 public
  release (`v1.8-public-release` at commit `7fa2c42`) all
  remain unchanged; v1.16.last freezes the v1.16 endogenous-
  market-intent feedback loop — the **first public-FWE closed
  deterministic loop** in which the actor's prior-period
  attention focus shapes this period's evidence-conditioned
  market intent (via the v1.16.1 pure-function classifier
  rewired in v1.16.2), the resulting market intent flows
  through the v1.15 aggregation chain to indicative pressure
  and the v1.14 financing review, and the same period's
  pressure / financing path then re-shape the next period's
  attention focus (v1.16.3 deterministic rule helpers + new
  source-id slots on `ActorAttentionStateRecord`). v1.16.last
  itself is docs-only on top of the v1.16.0 → v1.16.3 code
  freezes. The chain is **market-interest feedback,
  indicative pressure, financing-review feedback, and
  attention adaptation** — no order submission, no order
  book, no matching, no execution, no clearing, no
  settlement, no quote dissemination, no bid / ask, no price
  update, no `PriceBook` mutation, no target price, no
  expected return, no recommendation, no portfolio
  allocation, no real exchange mechanics, no financing
  execution, no loan approval, no bond / equity issuance, no
  underwriting, no syndication, no pricing, no interest rate,
  no spread, no coupon, no fee, no offering price, no
  investment advice, no real data, no Japan calibration, no
  LLM execution, no stochastic behaviour probabilities, no
  learned model. Known limitation: the v1.16 classifier and
  attention-feedback rule helpers are **deterministic and
  rule-based** — illustrative for auditability and replayable
  causal structure, not calibrated and not predictive.
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.16.last):**
  - `pytest -q` → 4033 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → produces `[setup]` / `[period N]` / `[ledger]` trace with
    v1.15.5 `market_intents= / aggregated_interest= /
    market_pressure=` per-period columns and v1.14.5
    `financing_needs= / funding_options= / capital_reviews= /
    financing_paths=` columns; every `InvestorMarketIntentRecord`
    now carries the v1.16.1 classifier-audit metadata block
    (`classifier_version` / `classifier_rule_id` /
    `classifier_status` / `classifier_confidence` /
    `classifier_unresolved_or_missing_count` /
    `classifier_evidence_summary`); period 1+
    `ActorAttentionStateRecord` payloads now carry the v1.16.3
    `source_indicative_market_pressure_ids` and
    `source_corporate_financing_path_ids` slots citing the
    previous period's full pressure / path id sets; re-run
    yields byte-identical output. Default 4-period sweep emits
    460 records (per-period 108 / 110, **unchanged** from
    v1.15.6 — every v1.16 milestone added zero new records)
  - `... --markdown` → appends v1.9.1 deterministic Markdown
    report including the v1.15.5 `## Securities market intent`
    section (now showing classifier-derived directions instead
    of rotation-derived ones) alongside the v1.14.5
    `## Corporate financing` section; re-run yields byte-
    identical output
  - `... --manifest /tmp/lw.json` → writes
    `living_world_manifest.v1` JSON carrying the perf-fixture
    `living_world_digest`. The integration-test fixture digest
    moved twice in the v1.16 sequence — at v1.16.2 from
    `bd7abdb9…58baf8` (v1.15.6 / v1.16.1) to `0b75e95a…d9398fa`
    (rotation → classifier rewire), and again at v1.16.3 to
    **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
    (attention-feedback union with new source-id slots and
    label widenings). v1.16.0 (docs-only) and v1.16.1 (pure-
    function module) left the digest byte-identical
  - `... --market-regime constructive --markdown`,
    `... --market-regime constrained --markdown`, and
    `... --market-regime tightening --markdown` — three
    regime-preset modes; each pair of consecutive runs of the
    same regime is byte-identical; runs across regimes produce
    different reports deterministically, with classifier-
    derived intent directions now varying with cited evidence
    rather than with positional indices
  - Forbidden-token scan (word-boundary against
    `world/experiment.py::_FORBIDDEN_TOKENS` plus the v1.12.x
    closed-set vocabulary scans for `ALL_FOCUS_LABELS`,
    `ALL_WATCH_LABELS`, intent direction labels, trigger
    labels, and the v1.16.1 classifier rule_id namespace)
    → no hits in any object id, signal id, payload key,
    metadata key, or example output
  - Public-wording audit → no "predicts markets",
    "production-ready", "Japan market simulator", "alpha",
    "buy / sell", "rating", "PD", "LGD", "EAD", "investment
    advice", "buyout-target", or any similar marketing /
    binding-signal framing in `README.md`,
    `docs/v1_16_endogenous_market_intent_feedback_summary.md`,
    `docs/world_model.md`, or
    `examples/reference_world/README.md`
  - Public / private boundary review → no real-system
    identifier in any public-FWE module, test, doc, or
    fixture; jurisdiction-neutral metadata scan passes on
    every `InvestorMarketIntentRecord` and
    `ActorAttentionStateRecord` produced by the default sweep
  - No-confidential-content audit → unchanged from v1.15.last
  - No-real-data audit → unchanged from v1.15.last
  - No-behavior-probability audit → unchanged from v1.15.last;
    additionally the v1.16.1 classifier is deterministic and
    rule-based (no learned model, no probabilistic output —
    the synthetic `confidence` field carries an ordering on
    evidence-deficient / classified / default-fallback paths
    only)

#### v1.15.last historical snapshot (unchanged)

- **Date:** 2026-05-03
- **Target:** v1.15.last securities market intent aggregation
  freeze. The v1.14.last corporate-financing-intent freeze
  (snapshot below), the v1.13.last settlement-substrate freeze,
  the v1.12.last endogenous-attention-loop freeze (2026-05-04
  snapshot further below), the v1.9.last public-prototype
  freeze, and the v1.8.0 public release (`v1.8-public-release`
  at commit `7fa2c42`) all remain unchanged; v1.15.last freezes
  the v1.15 securities-market-interest aggregation chain
  (investor market intent → aggregated market interest →
  indicative market pressure) plus the v1.15.6 feedback wiring
  back into the v1.14 corporate-financing chain (capital-
  structure review and financing path now cite indicative
  market pressure ids). v1.15.last itself is docs-only on top of
  the v1.15.1 → v1.15.6 code freezes. The chain is **market-
  interest aggregation / audit / feedback only** — no order
  submission, no order book, no matching, no execution, no
  clearing, no settlement, no quote dissemination, no bid /
  ask, no price update, no `PriceBook` mutation, no target
  price, no expected return, no recommendation, no portfolio
  allocation, no real exchange mechanics, no financing
  execution, no loan approval, no bond / equity issuance, no
  underwriting, no syndication, no pricing, no investment
  advice, no real data, no Japan calibration. Known
  limitation: v1.15.5 uses a deterministic rotation for
  `intent_direction_label` instead of evidence-conditioned
  classification; v1.16 will replace the rotation.
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.15.last):**
  - `pytest -q` → 3883 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → produces `[setup]` / `[period N]` / `[ledger]` trace with
    v1.15.5 `market_intents= / aggregated_interest= /
    market_pressure=` per-period columns alongside the v1.14.5
    `financing_needs= / funding_options= / capital_reviews= /
    financing_paths=` columns; re-run yields byte-identical
    output. Default 4-period sweep emits 460 records (per-period
    108 / 110)
  - `... --markdown` → appends v1.9.1 deterministic Markdown
    report including the v1.15.5 `## Securities market intent`
    section with four histograms (intent direction / aggregated
    net interest / pressure market access / pressure financing
    relevance) alongside the v1.14.5 `## Corporate financing`
    section; re-run yields byte-identical output
  - `... --manifest /tmp/lw.json` → writes
    `living_world_manifest.v1` JSON carrying the perf-fixture
    `living_world_digest`. The integration-test fixture digest
    moved twice in the v1.15 sequence — at v1.15.5 from
    `3df73fd4…6fa2d71` (v1.14.last) to `041686b0…03403a5`
    (chain on the per-period path), and again at v1.15.6 to
    `bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`
    (phase reorder + new citation slots on every review / path
    payload). Storage-only milestones v1.15.1 → v1.15.4 left
    the digest byte-identical; two runs into different paths
    diff to zero (modulo path)
  - `... --market-regime constructive --markdown`,
    `... --market-regime constrained --markdown`, and
    `... --market-regime tightening --markdown` — three
    regime-preset modes; each pair of consecutive runs of the
    same regime is byte-identical; runs across regimes produce
    different reports deterministically (v1.12 endogenous loop
    visible: firm latent state, intent histogram, valuation
    confidence, watch label, focus labels, memory selection
    composition all shift between regimes)
  - Forbidden-token scan (word-boundary against
    `world/experiment.py::_FORBIDDEN_TOKENS` plus the v1.12.x
    closed-set vocabulary scans for `ALL_FOCUS_LABELS`,
    `ALL_WATCH_LABELS`, intent direction labels, trigger labels)
    → no hits in any object id, signal id, payload key, metadata
    key, or example output
  - Public-wording audit → no "predicts markets",
    "production-ready", "Japan market simulator", "alpha",
    "buy / sell", "rating", "PD", "LGD", "EAD", "investment
    advice", "buyout-target", or any similar marketing /
    binding-signal framing in `README.md`,
    `docs/v1_12_endogenous_attention_loop_summary.md`,
    `docs/world_model.md`, or
    `examples/reference_world/README.md`
  - Public / private boundary review → no `boj`, `mufg`, `smbc`,
    `mizuho`, `fsa`, `jpx`, `tse`, `nikkei`, `topix`, `sony`,
    `jgb`, `gpif`, `nyse`, or any other real-system identifier
    appears in any public-FWE module, test, doc, or fixture
  - No-confidential-content audit → the v1.10.2 dialogue /
    v1.10.3 escalation layer carries restricted-visibility
    metadata, but no transcript, attendees list, named-client
    material, or expert-interview content appears anywhere in
    the public record set; the v1.12.3 `EvidenceResolver`
    surfaces only ids, not content; the v1.12.8 attention-feedback
    record carries only ids, labels, and integer stale_counts
  - No-real-data audit → no real central-bank, exchange, broker,
    audit, vendor, or regulator data appears in any public-FWE
    record; every numeric value is a synthetic illustrative
    scalar; v1.13.0 settlement design is docs-only and stays in
    the public layer's vocabulary, never as Japan-specific
    runtime
  - No-behavior-probability audit → no calibrated probability of
    default, calibrated forecast, calibrated sensitivity, or
    stochastic decay rule appears anywhere; the v1.12.9 decay
    rule is integer-counted and weight-deterministic; the
    closed-set vocabulary contains no `pd` / `lgd` / `ead` /
    `default` / `rating` / `advice` / `recommendation` /
    `underwrite` / `buy` / `sell` token / `selected_option` /
    `optimal_option` / `approved` / `executed` / `commitment` /
    `syndication` / `allocation` / `pricing` / `interest_rate` /
    `spread` / `coupon` / `fee` / `offering_price` /
    `target_price` / `expected_return` / `take_up_probability` /
    `order_id` / `trade_id` / `bid` / `ask` / `quote` /
    `market_price` / `indicative_price` / `order_imbalance`

#### v1.14.last historical snapshot (unchanged)

- **Date:** 2026-05-03
- **Target:** v1.14.last corporate financing intent freeze. The
  v1.14 chain (need / funding option candidate / capital
  structure review candidate / financing path) and the v1.14.5
  living-world integration are **storage / audit / graph-linking
  only** — no financing execution, no loan approval, no bond /
  equity issuance, no underwriting, no syndication, no
  bookbuilding, no allocation, no pricing, no optimal capital
  structure decision, no real leverage / D/E / WACC, no
  investment advice, no Japan calibration.
- **Status:** docs + tests frozen at the v1.14.last commit.
- **Local results (v1.14.last):**
  - `pytest -q` → 3391 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → per-period 96 / 98 records, run total in `[384, 432]`
  - integration-test fixture `living_world_digest` =
    `3df73fd4f152c16d1188f5c15b69bdc8a5cd6061b637ea35af671e86c6fa2d71`
    (moved at v1.14.5 by design; unchanged at v1.15.1 → v1.15.4
    because those milestones were storage / helper only)

#### v1.13.last historical snapshot (unchanged)

- **Date:** 2026-05-02
- **Target:** v1.13.last generic central-bank settlement
  infrastructure freeze. The v1.13 substrate (settlement
  accounts / payment instructions + settlement events /
  interbank-liquidity state / central-bank-operation +
  collateral-eligibility signals / v1.13.5 citation-only
  cross-link to v1.12.x) is **storage and labels only** — no
  payment execution, no real balances, no calibrated liquidity
  model, no policy decision, no Japan calibration.
- **Status:** docs + tests frozen at the v1.13.last commit.
- **Local results (v1.13.last):**
  - `pytest -q` → 2988 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → per-period 81 / 83 records, run total in `[324, 372]`
  - integration-test fixture `living_world_digest` =
    `916e410d829bec0be26b92989fa2d5438b80637a5c56afd785e0b56cfbebb379`
    (moved at v1.13.5 by design, unchanged at v1.13.6 / v1.14.1
    → v1.14.4)

#### v1.9.last historical snapshot (unchanged)

- **Date:** 2026-05-02
- **Target:** v1.9.last public prototype freeze. The v1.8.0 public
  release (`v1.8-public-release` at commit `7fa2c42`) remains
  unchanged; v1.9.last freezes the v1.9 living reference world
  as the headline runnable artifact on top of that earlier
  release.
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.9.last):**
  - `pytest -q` → 1626 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → produces `[setup]` / `[period N]` / `[ledger]` trace;
    re-run yields byte-identical output
  - `... --markdown` → appends v1.9.1 deterministic Markdown report;
    re-run yields byte-identical output
  - `... --manifest /tmp/lw.json` → writes
    `living_world_manifest.v1` JSON; two runs into different
    paths diff to zero (modulo path)
  - Forbidden-token scan (word-boundary against
    `world/experiment.py::_FORBIDDEN_TOKENS`) → no hits in any
    object id, signal id, or example output
  - Public-wording audit → no "predicts markets",
    "production-ready", "Japan market simulator", buyout-target,
    or similar marketing framings in `README.md` or `docs/*.md`

#### v1.8.0 historical snapshot (unchanged)

- **Date:** 2026-05-01
- **Tag:** `v1.8-public-release`, pointing at commit `7fa2c42`
  ("ci: trigger workflow on version-tag pushes"). The same commit
  also carries `v1.8-public-rc2`.
- **Status:** released. All release-gate checks pass locally and
  on CI under the tag ref.
- **Local results:**
  - `pytest -q` → 725 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `examples/reference_world/run_reference_loop.py` → produces
    seven loop record types + day-2 delivery to
    `(banking, investors)`
  - Replay-determinism gate (`tests/test_reference_demo_replay.py`)
    → 6 / 6 passed
  - Manifest gate (`tests/test_reference_demo_manifest.py`) →
    14 / 14 passed
  - Experiment-harness gate (`tests/test_experiment_config.py`) →
    43 / 43 passed
  - Catalog-shape regression (`tests/test_reference_demo_catalog_shape.py`)
    → 8 / 8 passed
  - Manifest sample build → ledger digest matches the digest the
    replay test asserts
  - Public-wording audit → zero hits in the "needs softening"
    category
  - Synthetic-ID audit → zero remaining real-name fixtures in
    `tests/` or `examples/`. Forbidden tokens (`toyota`, `mufg`,
    `boj`, etc.) appear only inside
    `tests/test_reference_demo.py` as the forbidden-list its
    hygiene test asserts must not appear in `object_id`s.
  - `gitleaks detect --redact --log-opts="--all"` (homebrew
    8.30.1, 46 commits, ~1.56 MB) → no leaks found
- **CI on tag ref:**
  - GitHub Actions run for `v1.8-public-release` (push event,
    headBranch=`v1.8-public-release`, sha=`7fa2c42`):
    `Tests + lint + demo` ✅ success, `Secret scan (gitleaks)` ✅
    success.
  - Same commit also passed CI under `main` and
    `v1.8-public-rc2` refs.
- **Notes for the next reviewer:**
  - The `secret-scan` CI job runs gitleaks-action with
    `continue-on-error: true` (license-key independent). Local
    gitleaks is the authoritative pre-tag check until a license
    token is wired.
  - No remaining release-blockers identified for v1.8.

### CI

- [ ] `.github/workflows/ci.yml` ran on the commit being tagged and
  every job is green. A red job blocks the public release; an
  intermittent flake should be investigated and fixed at the root,
  not retried.

## Code health (mirrors CI; reproducible locally)

- [ ] Dependencies installed via `pip install -e ".[dev]"` from
  the repo root. This brings in **PyYAML 6.x** (pinned
  `>=6,<7` as a runtime dep in `pyproject.toml`'s `[project]
  dependencies`) and pytest + ruff (under
  `[project.optional-dependencies] dev`). PyYAML is required for
  the reference demo and the v1.8 harness; the loader's fallback
  parser is a defensive minimal fallback (not a full YAML
  implementation) and will fail loudly via
  `tests/test_reference_demo_catalog_shape.py` if it ends up in
  use. Adopting PyYAML 7.x is a deliberate version-bump milestone
  and should not happen by an unpinned upgrade.
- [ ] `pytest -q` from `japan-financial-world/` reports the expected
  passing total. v1.8 + post-rc1 CI fix: `725 passed`. v1.9.last
  freeze: `1626 passed`. v1.13.last freeze: `2988 passed`.
  v1.14.last freeze: `3391 passed`. v1.15.last freeze:
  `3883 passed`. v1.16.last freeze: `4033 passed`. v1.17.last
  freeze: `4165 passed`. v1.18.last freeze: `4334 passed`.
  v1.19.last freeze: `4522 passed`. Use the count of the
  milestone being tagged; mismatch means the tree is not the
  freeze tree.
- [ ] `python -m compileall world spaces tests examples` from
  `japan-financial-world/` succeeds (no syntax errors anywhere,
  including the reference demo and test files).
- [ ] `ruff check .` from repo root passes against the
  `[tool.ruff]` config in `pyproject.toml`. The starter rule set
  is `select = ["E", "F"]` with `ignore = ["E501", "E402"]`;
  if the release tightens this, note the change in the release
  note.
- [ ] FWE Reference Demo runs end-to-end:
  `python examples/reference_world/run_reference_loop.py`
  from `japan-financial-world/` produces the seven loop
  record types and day-2 delivery to `(banking, investors)`.
- [ ] Replay determinism: two runs of the reference demo
  produce the same canonical ledger trace and the same SHA-256
  digest. The dedicated test
  `tests/test_reference_demo_replay.py` enforces this; if it
  fails, **do not** tag a release until the regression is
  understood. New non-determinism in the kernel is a v0/v1
  invariant violation. Helpers live in
  `examples/reference_world/replay_utils.py`
  (`canonicalize_ledger(kernel)`, `ledger_digest(kernel)`).
- [ ] Reference demo manifest can be generated. From within
  Python (or interactively for a release-note attachment):
  `build_reference_demo_manifest(kernel, summary)` returns a
  dict; `write_manifest(manifest, path)` writes deterministic
  JSON. Helpers live in
  `examples/reference_world/manifest.py`. The dedicated test
  `tests/test_reference_demo_manifest.py` enforces field shape,
  hash format, deterministic writes, and graceful git-absent
  behavior. The manifest is for reproducibility, not proprietary
  provenance — see
  `japan-financial-world/docs/public_private_boundary.md`.
- [ ] No new `print` / debug statements in committed code.
- [ ] No accidentally committed `*.bak`, `*.pyc`, `__pycache__/`,
  `.DS_Store`, IDE settings, or notebook output.

## Secret scanning

- [ ] CI's `secret-scan` job (gitleaks-action) is green for the
  commit being tagged. The job is currently `continue-on-error:
  true` for license-key reasons — a positive find still requires
  manual triage; do **not** treat the green job as a substitute
  for reviewing the action log.
- [ ] If gitleaks is not yet enabled with a license, run
  `gitleaks detect --redact` locally over the working tree and
  the full history (`gitleaks detect --redact --log-opts="--all"`)
  and document a clean run in the release note.
- [ ] Investigate every hit. Do not skip "looks like a false
  positive" without checking.
- [ ] If a real secret is found, treat it as compromised — rotate at
  source, then decide whether to rewrite history.

## Public-repo hygiene review

- [ ] Open the diff for this release and read every changed file.
- [ ] Confirm no expert-interview notes, OB notes, NDA-restricted
  material, or paid-data outputs were added.
- [ ] Confirm no real-institution stress results, named-institution
  scenarios, or client communications were added.
- [ ] Confirm no real ticker codes / real-firm identifiers were
  introduced in synthetic example data, tests, or schemas.
  Synthetic data must use `*_reference_*` style identifiers; see
  [`docs/naming_policy.md`](japan-financial-world/docs/naming_policy.md)
  for accepted forms.
- [ ] Confirm no Japan-calibration claim was made for v0 / v1.
  v0 and v1 are jurisdiction-neutral; mentions of BOJ / MUFG /
  GPIF / etc. should appear only as "what v1 deliberately avoids"
  or "what v2 will populate" — never as present-day capability.

## README and docs review

- [ ] `README.md` at repo root reads correctly. The disclaimer
  section is present and unchanged in spirit.
- [ ] `README.md` test count matches the actual `pytest -q` total.
- [ ] No release-blocking TODOs remain in
  `japan-financial-world/docs/v0_*.md`, `v1_*.md`, or
  `world_model.md` for the milestones being shipped.
- [ ] If a milestone freeze is being tagged, confirm the matching
  release-summary doc lists the freeze surface and that
  `test_inventory.md` reflects the current test counts.
- [ ] No "predicts markets," "production-ready," "enterprise-ready,"
  "Japan market simulator," "buyout target," or similar
  unsubstantiated public-facing claims appear in `README.md` or
  any `docs/*.md`.

## Examples and synthetic data review

- [ ] `examples/minimal_world.yaml` and any new examples use
  fictional, jurisdiction-neutral identifiers.
- [ ] `data/sample/*.yaml` does not introduce real-institution names
  or real-ticker codes since the previous release.
- [ ] Schemas under `schemas/` use neutral example values.

## Final eyes-on

- [ ] Browse the GitHub repo as if you were a researcher seeing it
  for the first time. Does the framing read as research software?
  Does the disclaimer surface early? Are real institutions clearly
  flagged as out-of-scope?
- [ ] If the answer to any of the above is "no," fix before
  releasing.

## Living-world reproducibility (v1.9.2)

A v1.9.x or v1.9.last public release that includes the multi-
period demo should also exercise the v1.9.2 reproducibility
helpers. Each item below mirrors the v1.7-era reference-demo
manifest gate but for the living-world sweep.

- [ ] `python -m examples.reference_world.run_living_reference_world`
  produces the canonical `[setup]` / `[period N]` / `[ledger]`
  trace. Re-running yields byte-identical output.
- [ ] `python -m examples.reference_world.run_living_reference_world --markdown`
  appends the v1.9.1 Markdown report. Re-running yields
  byte-identical output (CLI + Markdown).
- [ ] `python -m examples.reference_world.run_living_reference_world --manifest /tmp/lw.json`
  writes a v1.9.2 manifest. Re-running into a different path and
  diffing the two files shows zero changes (modulo the path).
- [ ] The manifest's `living_world_digest` matches the digest
  produced by
  `examples.reference_world.living_world_replay.living_world_digest(kernel, result)`
  on the same fixture.
- [ ] `manifest_version == "living_world_manifest.v1"` and
  `run_type == "living_reference_world"`.
- [ ] `infra_record_count + per_period_record_count_total ==
  created_record_count` (the v1.9.1-prep algebra).
- [ ] The manifest's `boundary_statement` matches the v1.9.1
  reporter verbatim and includes "no investment advice."
- [ ] `git_status` is `"ok"` (or `"git_unavailable"` /
  `"not_a_repo"` only on environments where that is genuinely
  the case — never `"error"` on a release machine).

## Public prototype gate (v1.9.last)

The **v1.9.last public prototype** is allowed to ship when the
public-release gate above is fully green *and* the prototype-
specific items below are all true. v1.9.last is a public *prototype*
(synthetic-only, CLI-first, explainability-first), not a fresh
public release of unrelated material — see
[`japan-financial-world/docs/public_prototype_plan.md`](japan-financial-world/docs/public_prototype_plan.md)
and the single-page reader summary at
[`japan-financial-world/docs/v1_9_public_prototype_summary.md`](japan-financial-world/docs/v1_9_public_prototype_summary.md).

### Code health (v1.9.last)

- [ ] `pytest -q` from `japan-financial-world/` → `1626 passed`.
- [ ] `python -m compileall world spaces tests examples` → clean.
- [ ] `ruff check .` from repo root → clean.
- [ ] `gitleaks detect --redact --log-opts="--all"` (or
  `--no-git --source .` if the working tree is the artifact)
  → zero leaks. If gitleaks is not installed locally, document
  the equivalent CI run.

### Demo gates (v1.9.last)

- [ ] **One-command demo (operational trace).** From a clean
  clone, after `pip install -e ".[dev]"` and `cd japan-financial-world`:

  ```bash
  python -m examples.reference_world.run_living_reference_world
  ```

  produces a `[setup]` / `[period N]` / `[ledger]` trace;
  two consecutive runs produce byte-identical CLI output.

- [ ] **Markdown report.**

  ```bash
  python -m examples.reference_world.run_living_reference_world --markdown
  ```

  appends the v1.9.1 deterministic Markdown ledger trace
  report; two consecutive runs produce byte-identical CLI +
  Markdown output. The hard-boundary statement appears verbatim
  in the Markdown (`no investment advice`).

- [ ] **Manifest generation.**

  ```bash
  python -m examples.reference_world.run_living_reference_world \
      --manifest /tmp/fwe_living_world_manifest.json
  ```

  writes a v1.9.2 `living_world_manifest.v1` JSON; running twice
  into different paths and diffing yields zero changes (modulo
  path). `manifest_version == "living_world_manifest.v1"`,
  `run_type == "living_reference_world"`,
  `infra_record_count + per_period_record_count_total ==
  created_record_count`, `git_status` is `"ok"` /
  `"git_unavailable"` / `"not_a_repo"` (never `"error"`).

### Scope and wording gates (v1.9.last)

- [ ] **README scope read.** The first ~60 seconds of `README.md`
  state, accurately and without marketing language, that the
  project is research software, not a market predictor or
  investment advisor; that all data is synthetic; that Japan
  calibration is v2 / v3 territory. The "Current public
  prototype (v1.9.last)" section is present and accurate.
- [ ] **Hard-boundary language present.** README, reference-world
  README, public-prototype plan, public-prototype summary, and
  the v1.9.1 Markdown report each state explicitly: no price
  formation, no trading, no lending decisions, no firm
  financial-statement updates, no canonical valuation, no
  Japan calibration, no real data, no investment advice.
- [ ] **Public / private boundary agreement.** `README.md`,
  `SECURITY.md`,
  [`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md),
  [`docs/v1_8_release_summary.md`](japan-financial-world/docs/v1_8_release_summary.md),
  [`docs/public_prototype_plan.md`](japan-financial-world/docs/public_prototype_plan.md),
  and
  [`docs/v1_9_public_prototype_summary.md`](japan-financial-world/docs/v1_9_public_prototype_summary.md)
  agree on what is public, what is private, and where the seam is.
- [ ] **Forbidden-token scan clean.** A word-boundary scan for the
  canonical token list at `world/experiment.py::_FORBIDDEN_TOKENS`
  finds no hits in any object id, signal id, or example output.
  Use `\b` boundaries — naive substring greps mis-flag `tse` ⊂
  `itself`.
- [ ] **No proprietary content.** No expert-interview notes, no
  named-institution stress results, no paid-data references, no
  client-report templates, no NDA-restricted material.
- [ ] **No investment-advice framings.** Neither direct ("buy
  X") nor indirect ("a portfolio with exposure E would
  experience O") forms appear in code, docs, or demo output.
- [ ] **CI green on the tag commit.** `Tests + lint + demo`
  and `Secret scan (gitleaks)` jobs both green.

## Tagging

A release candidate (RC) may be tagged with the public-release
gate not fully green; a final public-release tag may not.

```bash
# from repo root
# Release candidate (CI may have known yellow items, e.g.,
# gitleaks not yet licensed):
git tag -a vX.Y-public-rcN -m "vX.Y-public-rcN — short release note"

# Final public release (CI fully green, every checklist box
# above ticked):
git tag -a vX.Y-public-release -m "vX.Y-public-release — short release note"

git push origin <tag>
```

The release note should briefly state: what changed, what tests
report (e.g., `pytest -q` count, `compileall` clean,
`ruff check .` clean), and any known issues. Do not include
marketing language.
