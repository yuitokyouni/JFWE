# v1.19.0 Local Run Bridge / Report Export / Temporal Run Profile — Design Note

> **Status: docs-only.** v1.19.0 ships **no executable code, no
> new tests, no new ledger event types, no new behavior**. The
> living reference world's `living_world_digest`, per-period
> record count (`108 / 110`), per-run window (`[432, 480]`),
> default 4-period sweep total (`460 records`), and pytest count
> (`4334 / 4334`) are **unchanged from v1.18.last**. v1.19.0 is
> the design pointer for the v1.19 sequence; subsequent
> milestones (v1.19.1 → v1.19.last) will land code under this
> design.

## Purpose

v1.16.last froze the closed deterministic endogenous-market-
intent feedback loop. v1.17.last froze the inspection layer
(display timelines, regime comparison, causal annotations,
static analyst workbench). v1.18.last froze the scenario-driver
inspection layer — synthetic scenario templates can be stored,
applied as append-only context shifts, rendered into scenario
reports, and selected in the static workbench UI. The system
is **inspectable** and **stimulus-aware**, but two remaining
limitations narrow its usefulness for a reader:

1. **The static UI cannot load a fresh run.** The v1.18.4
   workbench reads only the inline `SAMPLE_RUNS` regime fixture
   + the inline `SCENARIO_FIXTURES`. A reader who runs the
   Python engine locally has no path to surface that run in the
   UI without editing the inline JSON.
2. **The default sweep is quarterly-only.** The living world
   produces one record set per quarter. Readers expect more
   visible monthly / daily-like movement on the timeline; the
   v1.17.1 `daily_like` calendar gives them a display axis but
   no extra economic records to plot, and the natural
   temptation — making the engine emit records every day — is
   exactly the trap (full daily simulation = price formation
   layer = real data tie = trading proximity) that v1.16 / v1.17
   / v1.18 deferred.

The v1.19 sequence resolves both **without breaking the
boundary**. It introduces:

- A clear separation of four layers (engine run profile /
  report export bundle / UI loading mode / local run bridge)
  so each can evolve independently.
- A small set of named **temporal run profiles** —
  `quarterly_default`, `monthly_reference`, `scenario_monthly`,
  `daily_display_only`, `future_daily_full_simulation` — with
  the last one explicitly **out of scope** for v1.19.
- A jurisdiction-neutral **`InformationReleaseCalendar`**
  layer so the `monthly_reference` profile is *not* a naive
  12× quarterly loop. The calendar names the *categories* of
  public information that arrive on different cadences
  (central-bank policy, inflation, labour market, GDP
  national accounts, etc.) — but stores no real values, no
  real dates, no real institutional identifiers.
- A **`RunExportBundle`** data shape and **CLI-first** local
  bridge so a reader can run `python -m
  examples.reference_world.export_run_bundle` to a JSON file
  and the static workbench can later load it.

This is **not** a market simulator, **not** a price-formation
layer, **not** a forecast layer, **not** a trading dashboard,
**not** a recommendation surface, **not** a real-data view,
**not** a Japan calibration, **not** an LLM execution path,
**not** a backend server, **not** Ruby on Rails, **not**
FastAPI, **not** Flask, **not** browser-to-Python execution.
The v1.16 / v1.17 / v1.18 hard boundary applies bit-for-bit at
every v1.19 milestone.

## Design constraint pinned at v1.19.0

The v1.18.0 binding intent — *do not overfit corporate /
investor / bank judgment; keep decision criteria modular and
replaceable* — extends to v1.19. v1.19 adds two more
non-negotiable rules:

- **Do not turn FWE into a daily price simulator.** The
  monthly profile may emit *more lightweight closed-loop
  records* (env, firm latent state, attention, intent,
  market pressure, financing review, scenario application);
  it must **not** emit price records, order records, trade
  records, execution records, daily decision records, or
  daily real data. `daily_full_simulation` is named only so a
  future milestone has a clear gating point — it ships in
  **v2+ at the earliest**, gated on the future market
  mechanism / price formation design.
- **Do not require a backend.** The default v1.19 path is
  CLI-first (`python -m examples.reference_world.export_run_bundle
  …`) writing a JSON file the static UI can later load. If a
  local server bridge is ever needed, it must be a tiny local
  helper (FastAPI / Flask / `http.server`) — **never** Rails,
  never a deployed SaaS, never a network-facing service. The
  static workbench remains `file://`-runnable.

This translates to five concrete design rules pinned at v1.19.0
and enforced for every v1.19.x milestone:

1. **Run profiles are labels over the existing closed loop.**
   `monthly_reference` and `scenario_monthly` reuse the v1.16
   closed-loop mechanisms (attention → market intent →
   aggregated interest → indicative pressure → financing
   review → next-period attention) and the v1.18.2 scenario
   application helper at a different cadence. They do **not**
   add a new mechanism, **not** add a new label vocabulary
   inside the closed loop, and **not** introduce a new actor
   reasoning rule.
2. **Information arrival is not data ingestion.** An
   `InformationArrivalRecord` records *that a class of public
   information became available* — by `IndicatorFamilyLabel`
   ∈ a closed-set vocabulary — at a synthetic month. It
   stores no real value, no real date, no real institutional
   identifier. It can be cited by closed-loop records as
   evidence; it never decides actor behaviour.
3. **Report export is deterministic.** A `RunExportBundle`
   produced from the same `(profile, regime, scenario, fixture
   seed)` inputs is byte-identical across runs. `generated_at`
   is a closed-set policy label
   (`stable_for_replay` / `non_deterministic_local_clock` /
   `unknown`), not a live `datetime.now()` call by default.
4. **UI loading is read-only.** The static workbench may
   eventually have a "Load local run bundle" button; it
   reads a user-supplied JSON file via `<input type="file">`
   and renders the bundle into the existing tabs. It does
   **not** write to disk, does **not** invoke the engine,
   does **not** call out to a server, does **not** require a
   build step.
5. **Local run bridge is CLI-first.** The default path is
   `python -m examples.reference_world.export_run_bundle …`
   writing JSON. A local FastAPI / Flask helper is a v1.19.4+
   *optional* affordance for power users; it never becomes
   the headline path. **Rails is forbidden by name** — the
   v1.x architecture has no Ruby dependency and will never
   acquire one.

## Two-line success condition

> By the end of v1.19, a reader can run a single CLI command
> to produce a deterministic local run bundle (JSON) for a
> chosen `(run profile, regime, scenario)` triple, then open
> the static workbench under `file://`, click **Load local run
> bundle**, pick the JSON, and inspect a monthly-profile
> synthetic FWE run — including any scenario applications and
> any cited `InformationArrivalRecord` ids — in the existing
> Overview / Timeline / Regime Compare / Scenario / Ledger
> tabs. The workbench introduces no backend, no build, no
> network I/O. The integration-test default `living_world_digest`
> for the unmodified default fixture stays byte-identical at
> `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`.

If a reviewer concludes that v1.19 turned FWE into a daily
price simulator, a real-data view, a Japan-calibrated tool, an
investment-advice surface, or a SaaS, v1.19 has failed — by
construction, every v1.19.x milestone is a synthetic /
label-only / append-only / static-UI surface.

## 1. Four layers — kept structurally separate

```
A. Engine run profile      ← controls how often the engine creates records
   ──────────────────────────
   quarterly_default | monthly_reference | scenario_monthly |
   daily_display_only | future_daily_full_simulation

B. Report export bundle    ← deterministic local artefact (JSON)
   ──────────────────────────
   bundle_id · run_profile_label · regime_label · selected_scenario_label
   period_count · digest · generated_at_policy_label · manifest /
   overview / timeline / regime_compare / scenario_trace /
   attention_diff / market_intent / financing / ledger_excerpt

C. UI loading mode         ← browser reads JSON, never executes Python
   ──────────────────────────
   inline_fixture | sample_living_world_manifest | local_run_bundle |
   uploaded_run_bundle

D. Local run bridge        ← CLI-first; optional tiny local server later
   ──────────────────────────
   python -m examples.reference_world.export_run_bundle …
   (later, optional) python -m examples.reference_world.local_bridge_serve
```

The four layers compose end-to-end:

```
    user
      │  CLI command (Layer D)
      ▼
    engine run profile (Layer A)
      │  emits closed-loop records on the chosen cadence
      ▼
    JSON writer            (Layer B → file system)
      │  RunExportBundle.to_dict() + json.dump
      ▼
    examples/ui/run_bundle.local.json
      │  user opens fwe_workbench_mockup.html under file://
      │  clicks "Load local run bundle"
      ▼
    UI loader              (Layer C)
      │  parses JSON, renders into existing tabs
      ▼
    static inspection (Overview / Timeline / Regime Compare /
                       Scenario / Ledger / …)
```

Each layer is **replaceable independently**. Adding a new run
profile does not require touching the bundle schema; adding a
new bundle field does not require touching the run profile;
adding a UI loader option does not require touching the CLI;
adding a local server bridge does not require touching the
runtime.

## 2. Engine run profile

Five named profiles. Only the first three may emit closed-loop
records; the fourth is display-only; the fifth is gated.

### 2.1 `quarterly_default`

- The current stable default. **Preserves the canonical
  digest** for the public reference fixture.
- 4 periods × 1 year (e.g. 2026-Q1 → 2026-Q4).
- Used for regression and the public baseline. Every existing
  test that pins `living_world_digest =
  f93bdf3f…b705897c` runs under this profile.
- Adding a new run profile **must not** change this digest.

### 2.2 `monthly_reference`

- Opt-in. 12 monthly periods (e.g. 2026-01 → 2026-12).
- Runs the existing closed loop at monthly cadence:
  market environment state → firm latent state → investor
  intent → valuation lite → bank credit review lite →
  investor market intent → aggregated market interest →
  indicative market pressure → capital structure review /
  financing path → attention feedback.
- Each monthly period may also receive cited
  `InformationArrivalRecord` ids from the
  `InformationReleaseCalendar` (see §4 below).
- **No price formation. No order books. No daily decisions.
  No real data.** The closed loop is unchanged in vocabulary;
  only the cadence and the scheduled-information layer are
  new.
- Useful for demos and UI movement; produces ~12 months of
  closed-loop records that the v1.17 inspection layer can
  render as a richer timeline.

### 2.3 `scenario_monthly`

- Opt-in. `monthly_reference` + explicit
  `apply_scenario_driver(...)` invocations on chosen months.
- The scenario application chain remains
  **append-only** (v1.18.2). The chosen monthly period gains
  one or more `ScenarioContextShiftRecord` entries; cited
  pre-existing context records remain byte-identical pre /
  post call.
- The default-fixture `living_world_digest` is **unchanged**
  unless this profile is explicitly invoked. Each
  `scenario_monthly` run produces its own scenario-specific
  digest (a future v1.19.x trip-wire test will pin the
  per-scenario digest set).

### 2.4 `daily_display_only`

- Display / report only. Uses the v1.17.1
  `ReportingCalendar` with `frequency_label = daily_like`
  and the v1.17.1 `SyntheticDisplayPath` for interpolation.
- **No daily economic records. No daily actor decisions. No
  prices, no trades, no orders, no executions, no clearings,
  no settlements.** The daily axis is a *display* refinement
  of the underlying monthly / quarterly run.
- Useful for reading-aid timelines on the v1.17.4 / v1.18.4
  workbench when the underlying engine ran on
  `monthly_reference` or `quarterly_default`.

### 2.5 `future_daily_full_simulation`

- **Explicitly out of scope for v1.19.** Named only so a
  future milestone has a clear gating point.
- Daily full simulation requires the future market-mechanism
  / price-formation design that the v1.16 freeze deferred.
  Until that design lands and is reviewed, no v1.19.x
  milestone may emit daily economic records.
- This profile is documented here so a reviewer can see, in
  one place, what is allowed to ship under v1.19 and what is
  not.

### 2.6 Expected scale

| Profile                            | Periods   | Closed-loop records / period (default fixture) | Digest target                                                                                  |
| ---------------------------------- | --------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `quarterly_default`                | 4         | 108 / 110                                       | **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`** (preserved)             |
| `monthly_reference`                | 12        | bounded — same per-period count shape, monthly  | new digest, pinned by a v1.19.3 trip-wire test once the profile lands                          |
| `scenario_monthly`                 | 12        | `monthly_reference` + 1 scenario-application set per cited month | per-scenario digest pinned                                                                   |
| `daily_display_only`               | up to 365 | **0 economic records** (display only)           | no engine digest movement; the synthetic display path digest is pinned separately              |
| `future_daily_full_simulation`     | —         | **deferred**                                    | gated on future market-mechanism / price-formation design                                     |

The `monthly_reference` profile must remain bounded — no
`P × I × F × venue` explosion, no order-level loops, no per-day
record fan-out. The v1.9.8 sparse-gating discipline carried
forward in `docs/performance_boundary.md` applies in full.

## 3. `RunExportBundle` — deterministic local artefact

A `RunExportBundle` is a single JSON file produced by Python
that the static workbench can load via `<input type="file">`.
Same `(profile, regime, scenario, fixture seed)` inputs →
byte-identical bundle.

### 3.1 Field set pinned at v1.19.0

```
@dataclass(frozen=True)
class RunExportBundle:
    bundle_id:                      str            # plain id
    run_profile_label:              str            # closed-set
    regime_label:                   str            # closed-set
    selected_scenario_label:        str            # closed-set
    period_count:                   int            # ≥ 1
    digest:                         str            # SHA-256 hex
    generated_at_policy_label:      str            # closed-set
    manifest:                       Mapping[str, Any]
    overview:                       Mapping[str, Any]
    timeline:                       Mapping[str, Any]
    regime_compare:                 Mapping[str, Any]
    scenario_trace:                 Mapping[str, Any]
    attention_diff:                 Mapping[str, Any]
    market_intent:                  Mapping[str, Any]
    financing:                      Mapping[str, Any]
    ledger_excerpt:                 Mapping[str, Any]
    boundary_flags:                 Mapping[str, bool]
    metadata:                       Mapping[str, Any]
```

### 3.2 `RunProfileLabel` (closed-set)

| Label                              | Meaning                                                              |
| ---------------------------------- | -------------------------------------------------------------------- |
| `quarterly_default`                | the canonical 4-period sweep                                         |
| `monthly_reference`                | the v1.19.3 monthly profile                                          |
| `scenario_monthly`                 | monthly + explicit scenario application                              |
| `daily_display_only`               | display-only daily axis on top of a quarterly / monthly run          |
| `future_daily_full_simulation`     | reserved; **out of scope** for v1.19                                 |
| `unknown`                          | catch-all                                                            |

### 3.3 `GeneratedAtPolicyLabel` (closed-set)

| Label                              | Meaning                                                              |
| ---------------------------------- | -------------------------------------------------------------------- |
| `stable_for_replay`                | a pinned synthetic timestamp; required for deterministic export      |
| `non_deterministic_local_clock`    | `datetime.now()` at export time; explicitly opt-in                   |
| `unknown`                          | catch-all                                                            |

The default at v1.19.x is **`stable_for_replay`** — same inputs
produce a byte-identical bundle (modulo dict ordering, which
the JSON writer pins via `sort_keys=True`).

### 3.4 Boundary-flag default (mirrors v1.18.2)

```
{
  "no_actor_decision":         True,
  "no_llm_execution":          True,
  "no_price_formation":        True,
  "no_trading":                True,
  "no_financing_execution":    True,
  "no_investment_advice":      True,
  "no_real_data_ingestion":    True,
  "no_japan_calibration":      True,
  "synthetic_only":            True,
  "stable_for_replay":         True,    # default unless explicit override
}
```

The static UI must visibly render these flags so a reader can
see, at a glance, that the loaded bundle obeys the boundary.

### 3.5 What the bundle is **not**

- **Not a forecast.** The `timeline` block contains the
  `SyntheticDisplayPath` rendered from the run; it is **not**
  a price prediction.
- **Not real data.** No real exchange / index / regulator /
  issuer / venue identifier appears anywhere in the bundle.
- **Not a Japan calibration.** Public bundles are
  jurisdiction-neutral; private JFWE bundles (v2 / v3) sit in
  a private repo only.
- **Not an LLM payload.** No prompt text, no LLM output, no
  generated prose. The bundle is the same closed-set labels
  + plain-id citations the v1.18.x layer already produces.

## 4. `InformationReleaseCalendar` — monthly profile is **not** a naive 12× loop

A naive `monthly_reference` profile that just runs the
quarterly closed loop 12 times would produce 12 indistinct
months — the very problem the user flagged. A reader expects
month-to-month variation that *reflects different information
arriving in different months*: central-bank policy meetings,
inflation prints, labour-market reports, capex surveys,
quarterly GDP, etc.

The v1.19 design names this layer explicitly so it can be
designed jurisdiction-neutrally and never tied to real data.

### 4.1 Design rule (binding)

The `InformationReleaseCalendar` is a **scheduled-information
layer** that announces *which categories of public information
become available in which month*. It stores **no real values**,
**no real dates**, **no real institutional identifiers**. The
public abstraction is jurisdiction-neutral; **Japan is used
only as a design reference for release cadence**, never
encoded as canonical data.

### 4.2 Vocabulary pinned at v1.19.0

#### `InformationReleaseCalendar`

A storage-only book of `ScheduledIndicatorRelease` records.
One calendar per `(run_profile_label, regime_label)` pair, by
default. The book mirrors v1.17.1 / v1.18.x storage-book
conventions: append-only, plain-id citations only, ledger
emission per `add_release` call, idempotent on duplicate id.

#### `ScheduledIndicatorRelease`

```
@dataclass(frozen=True)
class ScheduledIndicatorRelease:
    scheduled_release_id:       str            # plain id
    indicator_family_label:     str            # closed-set
    release_cadence_label:      str            # closed-set
    release_importance_label:   str            # closed-set
    scheduled_period_label:     str            # e.g. "2026-04" — synthetic
    affected_actor_scope_label: str            # closed-set, mirrors v1.18.1
    visibility:                 str            # closed-set
    metadata:                   Mapping[str, Any]
```

The dataclass:

- has **no** real-value field — releases announce categories,
  not numbers;
- has **no** institutional-identifier field — releases
  reference *families* (`central_bank_policy`, `inflation`),
  never named institutions;
- has **no** actor-decision field — releases do not decide.

#### `InformationArrivalRecord`

```
@dataclass(frozen=True)
class InformationArrivalRecord:
    information_arrival_id:     str            # plain id
    scheduled_release_id:       str            # plain-id citation
    indicator_family_label:     str            # closed-set
    release_importance_label:   str            # closed-set
    as_of_period_label:         str            # synthetic month
    affected_actor_scope_label: str            # closed-set
    reasoning_mode:             str            # default "rule_based_fallback"
    reasoning_policy_id:        str            # plain id
    reasoning_slot:             str            # default "future_llm_compatible"
    evidence_ref_ids:           tuple[str, ...]
    unresolved_ref_count:       int
    boundary_flags:             Mapping[str, bool]
    visibility:                 str
    metadata:                   Mapping[str, Any]
```

The record:

- carries the v1.18.0 audit-metadata block verbatim;
- is **append-only** — never mutates a pre-existing record;
- can be **cited** by closed-loop records as evidence;
- never decides actor behaviour.

### 4.3 Closed-set vocabularies

#### `ReleaseCadenceLabel`

| Label                | Meaning (jurisdiction-neutral)                                              |
| -------------------- | --------------------------------------------------------------------------- |
| `monthly`            | one synthetic release per month (e.g. inflation, labour market, retail)     |
| `quarterly`          | one synthetic release per quarter (e.g. national accounts, capex survey)    |
| `meeting_based`      | irregular, tied to a synthetic policy schedule                              |
| `weekly`             | finer cadence, used only for indicators where it matters                    |
| `daily_operational`  | very fine; used only for `market_liquidity` flow indicators                 |
| `ad_hoc`             | unscheduled / event-driven                                                  |
| `display_only`       | a label that exists for UI rendering; never drives engine records           |
| `unknown`            | catch-all                                                                   |

#### `IndicatorFamilyLabel`

| Label                       | Synthetic semantics                                                                          |
| --------------------------- | -------------------------------------------------------------------------------------------- |
| `central_bank_policy`       | a central-bank policy event (synthetic; no rate value)                                       |
| `inflation`                 | inflation indicator release (synthetic; no CPI value)                                        |
| `labor_market`              | labour-market indicator release (synthetic; no unemployment value)                           |
| `production_supply`         | production / supply-side indicator (synthetic; no IP-index value)                            |
| `consumption_demand`        | consumption / retail-demand indicator (synthetic)                                            |
| `capex_investment`          | capex / investment intention indicator (synthetic)                                           |
| `gdp_national_accounts`     | quarterly national-accounts release (synthetic; no GDP figure)                               |
| `market_liquidity`          | market-liquidity / interbank operational indicator (synthetic; no rate / price)              |
| `fiscal_policy`             | fiscal / budget policy event (synthetic)                                                     |
| `sector_specific`           | sector observation (e.g. semiconductor demand survey, retail traffic) — synthetic            |
| `information_gap`           | the explicit absence of a release in a month where one was scheduled (audit signal)          |
| `unknown`                   | catch-all                                                                                    |

#### `ReleaseImportanceLabel`

| Label              | Meaning                                                              |
| ------------------ | -------------------------------------------------------------------- |
| `routine`          | scheduled, no special weight                                          |
| `high_attention`   | flagged for attention; cited by `ActorAttentionState` widening rules  |
| `regime_relevant`  | a release that matters for the active regime preset                   |
| `stress_relevant`  | a release that matters under stress regimes                           |
| `unknown`          | catch-all                                                             |

### 4.4 Monthly profile rule

At each monthly period, the `monthly_reference` engine
profile may:

- **Read** the `InformationReleaseCalendar` to find the
  releases scheduled for that month;
- **Create** one `InformationArrivalRecord` per scheduled
  release (append-only, plain-id citation back to the
  scheduled release);
- **Cite** the resulting arrival ids on closed-loop records
  whose existing rules already attend to information /
  attention / market-environment / firm-state changes.

The **citation graph** the calendar layer is allowed to
participate in:

```
ScheduledIndicatorRelease     (calendar)
        │  cited by
        ▼
InformationArrivalRecord      (per-month, append-only)
        │  cited by — never mutated
        ├──▶ ActorAttentionState         (focus_labels widened by
        │                                 the v1.16.3 deterministic rule
        │                                 on `release_importance_label`
        │                                 ∈ {high_attention,
        │                                    regime_relevant,
        │                                    stress_relevant})
        ├──▶ InvestorMarketIntent        (rule_id branching may consume
        │                                 the cited arrival ids; the
        │                                 v1.16.1 classifier output
        │                                 stays in
        │                                 INTENT_DIRECTION_LABELS)
        ├──▶ MarketEnvironmentState      (subfield labels may shift on
        │                                 cited central-bank /
        │                                 inflation / liquidity arrivals)
        ├──▶ FirmFinancialState          (latent-state pressure labels
        │                                 may shift on cited
        │                                 production / capex /
        │                                 sector-specific arrivals)
        ├──▶ BankCreditReviewLite        (watch labels may widen on
        │                                 cited central-bank / market-
        │                                 liquidity arrivals)
        └──▶ ScenarioContextShiftRecord  (a v1.18.2 application may
                                          cite an arrival id under
                                          source_context_record_ids;
                                          the cited arrival is
                                          byte-identical pre / post
                                          call)
```

The release layer is **information-arrival, not data
ingestion**:

- It does **not** store real indicator values.
- It does **not** forecast.
- It does **not** create prices, trades, orders, executions,
  or any monetary flow.
- It only records that a *category* of public information
  became available.

### 4.5 Why this matters

A 12-month sweep without an information layer collapses to
"the same closed-loop snapshot twelve times". With the
calendar, two adjacent months become *visibly different*:

- April: `inflation` (monthly), `labor_market` (monthly),
  `capex_investment` (quarterly = April for some calendars),
  `central_bank_policy` (meeting-based, scheduled in this
  month).
- May: `inflation` (monthly), `labor_market` (monthly).
- August: `inflation` (monthly), `labor_market` (monthly),
  `gdp_national_accounts` (quarterly = August in some
  release schedules), `production_supply` (monthly).
- October: `inflation`, `labor_market`,
  `capex_investment` (quarterly), `central_bank_policy`
  (meeting-based, scheduled).

This is the scaffold; the public default fixture's release
schedule will live in `examples/reference_world/`
configuration data and stay synthetic.

### 4.6 Jurisdiction-neutrality discipline

- **Japan release cadence is a design reference only.** A
  reviewer who has read the BOJ / METI / MIC / MOF release
  schedule will recognise the *cadence pattern* (BOJ MPM,
  CPI, employment, IIP, retail sales, capex / Tankan, GDP /
  national accounts). v1.19 documents that influence here so
  it cannot accidentally calibrate in.
- **No real institution name appears in any v1.19.x
  module, fixture, test, or rendered view.** The
  jurisdiction-neutral identifier scan that runs on
  v1.18.x modules extends to the v1.19 calendar and
  arrival modules.
- **No real value, no real date.** A
  `ScheduledIndicatorRelease.scheduled_period_label` is a
  synthetic month label (`"2026-04"`); a
  `ScheduledIndicatorRelease` carries no data field.
- **All Japan-shaped concepts are private JFWE.** Real-
  institution / real-cadence / real-value calibration
  remains private JFWE territory (v2 / v3 only).

## 5. Local run bridge (CLI-first)

The default v1.19 path is a pure-Python CLI.

### 5.1 Example CLI shape

```
$ python -m examples.reference_world.export_run_bundle \
    --profile monthly_reference \
    --regime constrained \
    --scenario credit_tightening_driver \
    --out examples/ui/run_bundle.local.json

[exporting]    profile=monthly_reference regime=constrained
               scenario=credit_tightening_driver periods=12
[engine]       running closed loop on the chosen profile…
[engine]       12 monthly periods produced
[scenario]     applied at 2026-04 and 2026-09
[bundle]       writing examples/ui/run_bundle.local.json
[bundle]       digest = …
[done]         bundle_id = run_bundle:monthly_reference:…
               static_for_replay = true
```

- The exporter is a thin module that wires the existing
  v1.16 / v1.17.1 / v1.17.2 / v1.17.3 / v1.18.x helpers and
  the v1.19.3 monthly profile.
- Running the exporter twice with identical args produces a
  **byte-identical JSON file** under the
  `stable_for_replay` policy.

### 5.2 Optional local server bridge (v1.19.4+, low priority)

If — and only if — interactive UI execution becomes necessary,
a tiny local helper can be added:

```
$ python -m examples.reference_world.local_bridge_serve --port 8888
[serving]   http://127.0.0.1:8888
[serving]   GET /run?profile=…&regime=…&scenario=…  → run_bundle JSON
```

- **FastAPI / Flask / `http.server` only** — never Rails,
  never a deployed SaaS.
- **127.0.0.1 only** — never network-facing by default.
- **No persistent state, no auth, no DB** — the bridge is a
  single-shot wrapper around the same CLI.
- Deferred. v1.19.4 ships a UI loader that consumes the JSON
  file directly; a bridge server is a v1.19.4+ optional
  affordance for power users who want a button instead of a
  CLI.

### 5.3 What the local bridge is **not**

- **Not Rails.** The v1.x architecture has no Ruby
  dependency and will never acquire one.
- **Not SaaS.** No hosted service, no cloud, no auth.
- **Not a backend in the v1.18.4 workbench's meaning.** The
  static workbench remains `file://`-runnable; the bridge is
  optional, local, and bypassable.
- **Not browser-to-Python execution.** The browser never
  invokes Python; it reads JSON files via `<input
  type="file">` or via a local fetch in the optional bridge
  case.

## 6. UI loading mode (read-only)

The static workbench should eventually offer four loading
modes, **all read-only**:

| Mode                          | Source                                                  | When                                           |
| ----------------------------- | ------------------------------------------------------- | ---------------------------------------------- |
| `inline_fixture`              | inline `SAMPLE_RUNS` + `SCENARIO_FIXTURES` (v1.17.4 / v1.18.4) | default; survives offline                      |
| `sample_living_world_manifest` | `examples/ui/sample_living_world_manifest.json`        | parsed via `<input type="file">` or `fetch()` (file://-aware) |
| `local_run_bundle`             | `examples/ui/run_bundle.local.json` (v1.19.2 CLI output) | user has run the CLI and dropped the file in   |
| `uploaded_run_bundle`          | user-supplied JSON via `<input type="file">`           | drag-and-drop / file picker; no fetch          |

Adding a fourth top-ribbon button (`Load local run bundle`)
fits the v1.17.4 / v1.18.4 pattern. The button:

- **Parses** the JSON file with `JSON.parse` (no `eval`).
- **Validates** the bundle shape against the v1.19.1 schema
  via the existing `Validate` button's audit pass.
- **Renders** the bundle into the existing tabs (Overview /
  Timeline / Regime Compare / Scenario / Ledger / Attention
  / Market Intent / Financing).
- **Does not** write to disk, **does not** invoke the engine,
  **does not** call out to a server (in the default,
  no-bridge case), **does not** require a build step.

## 7. Boundary recap (carried forward verbatim from v1.18.0)

This is **bridge / report / profile design**, not market
behaviour. This is **scheduled information categories**, not
data ingestion. This is **synthetic closed-loop records at a
finer cadence**, not price formation.

- `monthly_reference` is still **synthetic reference
  simulation**, not prediction.
- `daily_display_only` is **display**, not daily simulation.
- The local run bridge is **local artefact generation**, not
  SaaS.
- Report export is **inspection**, not investment advice.

No price formation. No market price. No predicted index. No
forecast path. No expected return. No target price. No
recommendation. No portfolio allocation. No real exchange
mechanics. No order book. No matching. No execution. No
clearing. No settlement. No quote dissemination. No bid /
ask. No `PriceBook` mutation. No financing execution. No loan
approval. No bond / equity issuance. No underwriting. No
syndication. No pricing. No interest rate. No spread. No
coupon. No fee. No offering price. No investment advice. No
real data ingestion. No Japan calibration. No LLM execution.
No stochastic behaviour probabilities. No learned model. **No
firm decision rule, no investor action rule, no bank approval
logic, no trading decision model, no optimal capital
structure rule. No browser-to-Python execution. No backend
server in v1.19.0. No Rails. No real-time execution from UI.
No daily full economic simulation in v1.19.x.**

## 8. Per-milestone roadmap inside v1.19

| Milestone     | What                                                                                                                                                                                           | Status                  |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **v1.19.0**   | **Local Run Bridge / Report Export / Temporal Run Profile design (this document)** — four-layer separation; five run profiles (`quarterly_default` / `monthly_reference` / `scenario_monthly` / `daily_display_only` / `future_daily_full_simulation`); `RunExportBundle` data shape; `InformationReleaseCalendar` + `ScheduledIndicatorRelease` + `InformationArrivalRecord` + `ReleaseCadenceLabel` + `IndicatorFamilyLabel` + `ReleaseImportanceLabel` closed-set vocabularies; CLI-first local bridge (no Rails, no backend); read-only UI loading; per-milestone roadmap; success condition. | **Shipped (docs-only)** |
| **v1.19.1**   | **`world/run_export.py`** — `RunExportBundle` immutable frozen dataclass + four module-level helpers (`build_run_export_bundle` / `bundle_to_dict` / `bundle_to_json` / `write_run_export_bundle` / `read_run_export_bundle`); deterministic JSON via `sort_keys=True` and `stable_for_replay` default (the dataclass carries **no** wall-clock timestamp field, so `stable_for_replay` is declarative); four closed-set frozensets — `RUN_PROFILE_LABELS` (6: `quarterly_default` / `monthly_reference` / `scenario_monthly` / `daily_display_only` / `future_daily_full_simulation` / `unknown`), `GENERATED_AT_POLICY_LABELS` (4: `stable_for_replay` / `explicit_timestamp` / `omitted` / `unknown`), `STATUS_LABELS` (6: `draft` / `exported` / `stale` / `superseded` / `archived` / `unknown`), `VISIBILITY_LABELS` (5: `public` / `restricted` / `internal` / `private` / `unknown`); v1.19.0 hard-naming-boundary `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` frozenset (35+ entries — composes the v1.18.0 actor-decision / canonical-judgment names with the v1.17.0 forbidden display names + Japan-calibration / LLM names) scanned **recursively** at any depth across every payload + boundary-flag + metadata mapping; v1.19.0 default boundary-flag set carried on every bundle (`synthetic_only` / `no_price_formation` / `no_trading` / `no_investment_advice` / `no_real_data` / `no_japan_calibration` / `no_llm_execution` / `display_or_export_only`); `period_count` validation rejects `bool` and negative ints; `read_run_export_bundle(path)` returns a plain dict (full dataclass restoration is **deferred** — the v1.19.4 read-only UI loader walks the dict; v1.19.2 CLI exporter will produce a real bundle from a kernel run); +56 tests in `tests/test_run_export.py` covering closed-set vocabularies, hard-naming-boundary disjointness from vocab + dataclass field names + `to_dict` keys + section payload keys + boundary-flag keys + metadata keys, default boundary flags, immutability, every per-label rejection path, every payload-type rejection path, byte-deterministic JSON output regardless of insertion order, write/read JSON round-trip via `tmp_path`, `stable_for_replay` no-current-timestamp invariant, `explicit_timestamp` / `omitted` policy labels accepted, `monthly_reference` / `scenario_monthly` / `daily_display_only` / `future_daily_full_simulation` profile labels accepted as carriers without engine execution, runtime-book-free module-text scan (no `from world.kernel` / `from world.prices` / `from world.scenario_drivers` / `from world.scenario_applications` / etc. imports), no-ledger-emission, no-`PriceBook`-mutation, no-default-`living_world_digest`-move trip-wire (digest stays at `f93bdf3f…b705897c`), jurisdiction-neutral identifier scan over both module and test text; **export infrastructure only** — no engine run, no monthly profile, no CLI, no UI bridge yet; per-period record count (`108 / 110`), per-run window (`[432, 480]`), default 4-period sweep total (`460 records`), and `living_world_digest` (**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**) all unchanged from v1.18.last. | **Shipped (4390 tests)**       |
| v1.19.2       | `examples/reference_world/export_run_bundle.py` — CLI module (`python -m examples.reference_world.export_run_bundle …`) wiring the existing v1.16 / v1.17 / v1.18 helpers; emits a `run_bundle.local.json` next to `examples/ui/sample_living_world_manifest.json`. Default profile `quarterly_default` produces a bundle whose digest matches the canonical fixture digest. | Planned                 |
| v1.19.3       | `monthly_reference` run profile (the lightweight closed-loop monthly cadence) **+** `world/information_release.py` (`InformationReleaseCalendar` book + `ScheduledIndicatorRelease` + `InformationArrivalRecord` + closed-set frozensets); kernel wired with empty default calendar; jurisdiction-neutral default schedule fixture in `examples/reference_world/`. Trip-wire tests pin: per-book byte-equality pre / post information arrival; no real institution names; no real values; `monthly_reference` digest pinned per regime preset. | Planned                 |
| v1.19.4       | UI local bundle loader mock — adds **Load local run bundle** to the top ribbon of `examples/ui/fwe_workbench_mockup.html`; `<input type="file">` + `JSON.parse` + render into existing tabs; `Validate` extended to check the loaded bundle's shape; **no engine execution from the UI** preserved. Optional: a stub `local_bridge_serve` module under `examples/reference_world/` that 127.0.0.1-serves the same CLI output (FastAPI / Flask / `http.server`; never Rails). | Planned                 |
| v1.19.last    | Local Run Bridge / Temporal Profile freeze (docs-only) — single-page reader-facing summary in `docs/v1_19_local_run_bridge_and_temporal_profiles_summary.md`; v1.19.last release-readiness snapshot in `RELEASE_CHECKLIST.md`; v1.19.last freeze-pin section in `docs/performance_boundary.md`; v1.19.last `test_inventory.md` header note; v1.19.last cross-link in `docs/fwe_reference_demo_design.md`, `examples/reference_world/README.md`, and `examples/ui/README.md`. | Planned                 |

## 9. Performance boundary at v1.19.0

v1.19.0 is **docs-only**. Nothing changes:

- per-period record count: **108 / 110** (unchanged from
  v1.18.last);
- per-run window: **`[432, 480]`** (unchanged);
- default 4-period sweep total: **460 records** (unchanged);
- integration-test `living_world_digest` for the **default
  fixture without any scenario applied**:
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (unchanged across the entire v1.18 sequence and the v1.19.0
  design pass);
- pytest count: **4334 / 4334** passing (unchanged).

v1.19.1 → v1.19.last will land code, but the **default
fixture, default profile (`quarterly_default`), no scenario
applied** digest stays byte-identical by design:

- `monthly_reference` is opt-in. Only when the caller picks
  the profile do new monthly records appear; the canonical
  digest under `quarterly_default` does not move.
- `scenario_monthly` is opt-in on top of `monthly_reference`.
  Each scenario application produces its own scenario-specific
  digest; the default-fixture canonical digest is unchanged.
- `daily_display_only` adds zero economic records.
- `future_daily_full_simulation` is gated, not implemented.
- The `RunExportBundle` writer is read-only — it walks the
  kernel's existing `list_*` / `get_*` / `snapshot` methods
  and writes JSON. It mutates no kernel book.
- The CLI exporter builds its own *fresh* kernel per invocation,
  so running the CLI cannot influence a separately seeded
  default sweep.

## 10. Hard boundary recap (carried forward verbatim from v1.18.last)

This is **scenario inspection / report export / monthly
reference**, not prediction. This is **scheduled-information
categories**, not data ingestion. This is **synthetic closed-
loop records at a finer cadence**, not price formation. This
is **a CLI + JSON file + read-only UI loader**, not a SaaS.

No order submission. No buy / sell labels. No order book. No
matching. No execution. No clearing. No settlement. No quote
dissemination. No bid / ask. No price update. No `PriceBook`
mutation. No target price. No expected return. No
recommendation. No portfolio allocation. No real exchange
mechanics. No financing execution. No loan approval. No bond
/ equity issuance. No underwriting. No syndication. No
pricing. No interest rate. No spread. No coupon. No fee. No
offering price. No investment advice. No real data ingestion.
No Japan calibration. No LLM execution. No stochastic
behaviour probabilities. No learned model. **No firm decision
rule, no investor action rule, no bank approval logic, no
trading decision model, no optimal capital structure rule.**
**No browser-to-Python execution. No backend server in v1.19.0.
No Rails. No real-time execution from UI. No daily full
economic simulation in v1.19.x.**

## 11. Forward pointer

v1.19.1 lands the `RunExportBundle` data model + JSON writer
(**shipped**). v1.19.2 lands the CLI exporter. v1.19.3 lands
the `monthly_reference` profile *and* the
`InformationReleaseCalendar` layer. v1.19.4 lands the UI local
bundle loader (and an optional stub local server). v1.19.last
freezes.

The next sequence (v1.20+) candidates:

- **v1.20 — additional run profiles (conditional).** If the
  v1.19 surface is operationally legible, additional profiles
  may be added (e.g. `monthly_with_attention_stress_test` or
  `quarterly_with_capital_policy_uncertainty`). Each new
  profile is a label over the existing closed loop — never a
  new mechanism, never a new actor decision rule.
- **v2.0 — Japan public calibration in private JFWE only.**
  Public FWE remains jurisdiction-neutral and synthetic. The
  v1.19 release-cadence vocabulary is jurisdiction-neutral by
  design; private JFWE may calibrate it to BOJ / METI / MIC /
  MOF schedules without changing the public surface.
- **Future LLM-mode reasoning policies.** When introduced,
  must populate the same `ActorReasoningInputFrame` /
  `ReasoningPolicySlot` audit shape pinned at v1.18.0 — input
  evidence ids, prompt / policy id, output label, confidence /
  status, rejected / unknown cases, and must never hide a
  mutation of any source-of-truth book. The v1.19 monthly
  profile + information-arrival layer **does not** unlock LLM
  execution; the rule-based fallback remains binding at
  v1.19.x.
- **Future price formation remains gated** until the v1.16 /
  v1.17 / v1.18 / v1.19 surface is operationally legible to a
  reviewer who has not read this codebase. Adding price
  formation on top of an opaque calendar / profile / bundle
  layer would defeat the auditability goal of every prior
  freeze.

The v1.19 chain stays profile-only, calendar-only, bundle-only,
and CLI-first forever. Future milestones may *cite* v1.19
profiles / bundles / arrival records (plain-id cross-references,
additional rendering kinds), but they may **never** mutate the
v1.19.0 vocabulary, replace the deterministic CLI export with a
runtime-active server bridge as the headline path, hard-code
real institution names / real release dates / real indicator
values, or introduce daily full economic simulation on top of
the calendar layer.
