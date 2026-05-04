# v1.20.0 Monthly Scenario Reference Universe — Design Note

> **Status: docs-only.** v1.20.0 ships **no executable code, no
> new tests, no new ledger event types, no new behavior**. The
> living reference world's `living_world_digest` (`quarterly_default`
> = `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`,
> `monthly_reference` = `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`),
> per-period record count, per-run window, default 4-period
> sweep total, and pytest count (`4522 / 4522`) are **unchanged
> from v1.19.last**. v1.20.0 is the design pointer for the v1.20
> sequence; subsequent milestones (v1.20.1 → v1.20.last) will
> land code under this design.

## Purpose

v1.18.last froze the scenario-driver inspection layer:
`ScenarioDriverTemplate` → `ScenarioDriverApplicationRecord` →
`ScenarioContextShiftRecord` → `EventAnnotationRecord` /
`CausalTimelineAnnotation`. v1.19.last froze the local-run-
bundle / monthly-reference layer: `RunExportBundle` JSON +
`monthly_reference` profile + `InformationReleaseCalendar` +
read-only static UI loader.

A reader can now run the engine from a terminal and load a
quarterly_default or monthly_reference JSON bundle in the
static workbench — but the **default fixture is still tiny**:
3 firms, 2 investors, 2 banks. Two adjacent monthly periods
*are* visibly different (the v1.19.3 information-arrival
calendar made sure of that), but the cross-section feels thin.
A reviewer who opens the workbench expects a financial-world
demo — they see a 3-firm sweep that obviously exists for unit
tests.

The v1.20 sequence resolves this by **combining two upgrades**
into a single new opt-in profile:

1. **Temporal granularity** — quarterly_default's 4 periods
   give way to a 12-period monthly run (already shipped at
   v1.19.3, now reused).
2. **Cross-sectional breadth** — the tiny 3-firm fixture is
   replaced by a **generic 11-sector / 11-company synthetic
   reference universe** with a richer investor / bank
   archetype set.

The new profile is named **`scenario_monthly_reference_universe`**.
It composes the v1.19.3 monthly cadence + the v1.19.3
`InformationReleaseCalendar` + the v1.18.2
`apply_scenario_driver(...)` chain on top of a new
`ReferenceUniverseProfile` storage layer. Same hard boundary
as every prior freeze: append-only, label-only, jurisdiction-
neutral, no real data, no real companies, no real sector
weights, no licensed taxonomy, no actor decision logic.

This is **not** a market simulator. It is **not** a price-
formation layer. It is **not** a forecast layer. It is **not**
a daily-frequency economic simulation. It is **not** a real-
data view. It is **not** a Japan calibration. It is **not** an
LLM execution path. It is **not** an investment recommendation
engine. It does **not** use real company names. It does
**not** use real sector index membership. It does **not**
license any real classification taxonomy. The v1.16 / v1.17 /
v1.18 / v1.19 hard boundary applies bit-for-bit at every v1.20
milestone.

## Design constraint pinned at v1.20.0

The v1.18.0 binding intent — *do not overfit corporate /
investor / bank judgment; keep decision criteria modular and
replaceable* — extends to v1.20. v1.20 adds three more
non-negotiable rules:

- **No real company names.** Every firm in the reference
  universe is a synthetic id (`firm:reference_<sector>_a`).
  Real-issuer calibration remains private JFWE territory (v2 /
  v3 only).
- **No GICS / real-taxonomy dependency.** The 11-sector
  vocabulary uses `_like` suffixes
  (`information_technology_like`, `financials_like`, …) so
  the tokens cannot be confused with the licensed GICS
  taxonomy or any other vendor classification. The public-FWE
  module text + tests will pin the absence of bare `GICS` /
  vendor-name tokens. **Japan TSE-33 / Bloomberg / Refinitiv /
  S&P / MSCI / FactSet** taxonomy names are forbidden in
  module text, fixture data, rendered views, and tests.
- **No P × I × F × venue × scenario explosion.** Every loop in
  the v1.20 monthly run must be bounded. Performance budgets
  are pinned at v1.20.0 *before* any code lands; the v1.20.x
  perf-boundary tests pin the upper guardrail.

This translates to seven concrete design rules pinned at
v1.20.0 and enforced for every v1.20.x milestone:

1. **The new profile is opt-in.** `quarterly_default` and
   `monthly_reference` digests are pinned and unchanged.
   `scenario_monthly_reference_universe` runs only when the
   caller explicitly picks it via `--profile` (CLI) or
   `profile=...` (Python).
2. **The 11-sector vocabulary is closed-set and synthetic.**
   Sector labels carry the `_like` suffix; they are not real
   sector membership.
3. **The 11-firm universe is one representative firm per
   sector.** Each firm is a synthetic profile with closed-set
   sensitivity labels (`rate_sensitivity_label`,
   `credit_sensitivity_label`, etc.). No real financial
   statement values, no real market caps, no real leverage
   ratios.
4. **The investor / bank archetype set is bounded.** 4
   investors + 3 banks, each with a synthetic archetype
   label (`benchmark_sensitive_institutional` /
   `active_fund_like` / etc.).
5. **Scenario application stays append-only** (v1.18.2
   discipline). The scenario layer never mutates a pre-
   existing record. Sector sensitivity steers *evidence*
   weight, never actor behavior.
6. **The audit shape carries forward verbatim** —
   `reasoning_mode = "rule_based_fallback"`,
   `reasoning_slot = "future_llm_compatible"`,
   `reasoning_policy_id`, `evidence_ref_ids`,
   `unresolved_ref_count`, `boundary_flags`. Every v1.20
   record carries this block.
7. **Bounded performance.** Per-period record count and total
   ledger size are pinned at v1.20.0; the v1.20.x perf-
   boundary tests refuse to ship if the bound is exceeded.

## Two-line success condition

> By the end of v1.20, a reader can run a single CLI command
> to produce a deterministic local run bundle for the new
> `scenario_monthly_reference_universe` profile (12 monthly
> periods, 11 generic sectors, 11 synthetic representative
> firms, 4 investor archetypes, 3 bank archetypes, scheduled
> information arrivals, one or more scenario driver
> applications, append-only context shifts, closed-loop
> propagation), open the static workbench under `file://`,
> click **Load local bundle**, and inspect a sector / firm /
> month cross-section that visibly differs from the
> `monthly_reference` baseline because of the scenario impact
> *and* the sector sensitivities. The integration-test
> `living_world_digest` for the unmodified `quarterly_default`
> fixture stays byte-identical at
> `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`;
> the `monthly_reference` digest stays at
> `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`.

If a reviewer concludes that v1.20 turned FWE into a real-
company simulator, a Japan-calibrated tool, an investment-
advice surface, a daily price simulator, or a SaaS, v1.20 has
failed — by construction, every v1.20.x milestone is a
synthetic / generic-sector / opt-in-profile / read-only-UI
surface.

## 1. Profile family at v1.20.last

```
RunProfileLabel (closed set, extended at v1.20.1)
─────────────────────────────────────────────────
quarterly_default                       [executable, canonical, unchanged]
monthly_reference                       [executable, opt-in, v1.19.3]
scenario_monthly                        [deferred — not in v1.20]
scenario_monthly_reference_universe     [executable, opt-in, NEW at v1.20.3]
daily_display_only                      [display only, no economic execution]
future_daily_full_simulation            [explicitly out of scope]
unknown                                 [carrier]
```

By **end of v1.20**:

- `quarterly_default` — preserved unchanged. Still the
  canonical regression profile.
- `monthly_reference` — preserved unchanged. The default
  monthly fixture (3 firms, 2 investors, 2 banks, 12 months,
  51 information arrivals) remains the lightweight monthly
  baseline.
- **`scenario_monthly_reference_universe`** — NEW. Opt-in.
  The "rich monthly universe with scenario application" that
  v1.20 introduces.
- `scenario_monthly` — still **deferred**. The v1.20 design
  considered wiring scenario application into
  `monthly_reference` directly but chose the richer-universe
  path instead. A future v1.20.x or v1.21.0 milestone may add
  `scenario_monthly` if a small-fixture variant is wanted.
- `daily_display_only` — still **display-only**. No
  economic execution.
- `future_daily_full_simulation` — still **explicitly out of
  scope**.

## 2. `ReferenceUniverseProfile` — data model

A `ReferenceUniverseProfile` names a synthetic universe shape.
v1.20.1 will land it as an immutable frozen dataclass. The
v1.20.0 design pin:

```
@dataclass(frozen=True)
class ReferenceUniverseProfile:
    reference_universe_id:    str            # plain id, jurisdiction-neutral
    universe_profile_label:   str            # closed-set
    firm_count:               int            # ≥ 1
    sector_count:             int            # ≥ 1
    investor_count:           int            # ≥ 1
    bank_count:               int            # ≥ 1
    period_count:             int            # ≥ 1
    sector_taxonomy_label:    str            # closed-set
    synthetic_only:           bool           # always True
    status:                   str            # closed-set
    visibility:               str            # closed-set
    metadata:                 Mapping[str, Any]
```

### 2.1 `universe_profile_label` (closed set)

| Label                     | Synthetic semantics                                                                |
| ------------------------- | ---------------------------------------------------------------------------------- |
| `tiny_default`            | The 3-firm / 2-investor / 2-bank fixture used by `quarterly_default` / `monthly_reference`. |
| `generic_11_sector`       | The v1.20.3 11-sector / 11-firm universe; one representative firm per sector.       |
| `generic_broad_market`    | Reserved for a future broader universe (v1.21+); not implemented at v1.20.last.    |
| `custom_synthetic`        | Caller-supplied. Test fixtures only — no public default.                            |
| `unknown`                 | Catch-all.                                                                          |

### 2.2 `sector_taxonomy_label` (closed set)

| Label                              | Synthetic semantics                                                              |
| ---------------------------------- | -------------------------------------------------------------------------------- |
| `generic_11_sector_reference`      | The v1.20 generic 11-sector reference taxonomy (see §3).                          |
| `generic_macro_sector_reference`   | A coarser 4-bucket alternative (cyclicals / defensives / financials / others). Reserved for v1.21+. |
| `custom_synthetic`                 | Caller-supplied. Tests only.                                                      |
| `unknown`                          | Catch-all.                                                                        |

The dataclass:

- has **no** real-taxonomy field — `sector_taxonomy_label`
  names a *jurisdiction-neutral / vendor-neutral* category;
- has **no** market-cap / financial-statement field —
  universes name *labels and counts*, not balance-sheet
  numbers;
- has **no** actor-decision field — universes do not decide.

## 3. `GenericSectorReference` — the 11-sector closed-set taxonomy

`GenericSectorReference` records the synthetic sector labels
used inside the `generic_11_sector` universe. v1.20.1 will
land it as an immutable frozen dataclass. The v1.20.0 design
pin:

```
@dataclass(frozen=True)
class GenericSectorReference:
    sector_id:                                  str   # plain id
    sector_label:                               str   # closed-set
    sector_group_label:                         str   # closed-set (coarser)
    demand_sensitivity_label:                   str   # closed-set
    rate_sensitivity_label:                     str   # closed-set
    credit_sensitivity_label:                   str   # closed-set
    input_cost_sensitivity_label:               str   # closed-set
    policy_sensitivity_label:                   str   # closed-set
    technology_disruption_sensitivity_label:    str   # closed-set
    status:                                     str   # closed-set
    visibility:                                 str   # closed-set
    metadata:                                   Mapping[str, Any]
```

### 3.1 The 11 generic sector labels (closed set)

| Sector label                     | Sector group         | Synthetic semantics                                                                 |
| -------------------------------- | -------------------- | ----------------------------------------------------------------------------------- |
| `energy_like`                    | `cyclical_supply`    | Synthetic energy-supply-like sector. Generic; not real-issuer membership.            |
| `materials_like`                 | `cyclical_supply`    | Synthetic materials-like sector.                                                     |
| `industrials_like`               | `cyclical_demand`    | Synthetic industrials-like sector.                                                   |
| `consumer_discretionary_like`    | `cyclical_demand`    | Synthetic discretionary-consumer-like sector.                                        |
| `consumer_staples_like`          | `defensive`          | Synthetic staples-like sector.                                                       |
| `health_care_like`               | `defensive`          | Synthetic health-care-like sector.                                                   |
| `financials_like`                | `financials`         | Synthetic financials-like sector. Note: distinct from the v1.20 *bank archetypes*. |
| `information_technology_like`    | `growth_innovation`  | Synthetic IT-like sector.                                                            |
| `communication_services_like`    | `growth_innovation`  | Synthetic communications-like sector.                                                |
| `utilities_like`                 | `defensive`          | Synthetic utilities-like sector.                                                     |
| `real_estate_like`               | `rate_sensitive`     | Synthetic real-estate-like sector.                                                   |
| `unknown`                        | `unknown`            | Catch-all.                                                                           |

Every label carries the `_like` suffix to make the **non-real-
membership** discipline visible at every read site.
Tests will pin:

- bare `GICS` / `MSCI` / `S&P` / `FactSet` / `Bloomberg` /
  `Refinitiv` / `TOPIX` / `Nikkei` / `JPX` tokens are
  **absent** from the v1.20 module text, fixture data,
  rendered views, and test text;
- the `_like` suffix appears on every public sector label.

### 3.2 `sector_group_label` (closed set)

| Group label                | Members                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| `cyclical_supply`          | `energy_like` · `materials_like`                                                          |
| `cyclical_demand`          | `industrials_like` · `consumer_discretionary_like`                                        |
| `defensive`                | `consumer_staples_like` · `health_care_like` · `utilities_like`                           |
| `financials`               | `financials_like`                                                                         |
| `growth_innovation`        | `information_technology_like` · `communication_services_like`                             |
| `rate_sensitive`           | `real_estate_like`                                                                        |
| `unknown`                  | catch-all                                                                                 |

### 3.3 Sensitivity labels (each closed-set)

Six sensitivity dimensions per sector. Each uses the same
five-rung closed set:

```
SectorSensitivityLabel:
    very_low | low | moderate | high | very_high | unknown
```

Dimensions:

- `demand_sensitivity_label`
- `rate_sensitivity_label`
- `credit_sensitivity_label`
- `input_cost_sensitivity_label`
- `policy_sensitivity_label`
- `technology_disruption_sensitivity_label`

These are **labels**, not numbers. They drive the
**scenario-to-sector impact map** in §8 below.

### 3.4 Default sensitivity matrix (synthetic, jurisdiction-neutral)

The default sensitivity matrix v1.20.1 will pin in code. This
is **not** a calibrated real-world claim; it is a
deliberately legible synthetic mapping that matches a
generic textbook reading of each sector group, so a reader
can see the scenario-to-sector flow without surprise.

| Sector                        | demand   | rate      | credit    | input_cost | policy   | tech_disruption |
| ----------------------------- | -------- | --------- | --------- | ---------- | -------- | ---------------- |
| `energy_like`                 | high     | moderate  | moderate  | very_high  | high     | low              |
| `materials_like`              | high     | moderate  | moderate  | very_high  | moderate | low              |
| `industrials_like`            | high     | moderate  | moderate  | high       | moderate | moderate         |
| `consumer_discretionary_like` | very_high| moderate  | moderate  | moderate   | low      | moderate         |
| `consumer_staples_like`       | low      | low       | low       | high       | low      | low              |
| `health_care_like`            | low      | low       | low       | low        | very_high| moderate         |
| `financials_like`             | moderate | very_high | very_high | low        | high     | moderate         |
| `information_technology_like` | moderate | high      | low       | low        | moderate | very_high        |
| `communication_services_like` | moderate | moderate  | low       | low        | high     | high             |
| `utilities_like`              | low      | very_high | high      | high       | high     | low              |
| `real_estate_like`            | moderate | very_high | very_high | moderate   | moderate | low              |

Tests will pin: every cell ∈ the closed set; every sector has
exactly one label per dimension; the matrix is byte-identical
across runs.

## 4. `SyntheticSectorFirmProfile` — the 11-firm universe

One representative firm per sector. v1.20.1 will land
`SyntheticSectorFirmProfile` as an immutable frozen
dataclass. The v1.20.0 design pin:

```
@dataclass(frozen=True)
class SyntheticSectorFirmProfile:
    firm_id:                          str   # plain id
    sector_id:                        str   # plain-id citation
    sector_label:                     str   # closed-set (must match sector)
    firm_size_label:                  str   # closed-set
    balance_sheet_style_label:        str   # closed-set
    funding_dependency_label:         str   # closed-set
    demand_cyclicality_label:         str   # closed-set
    input_cost_exposure_label:        str   # closed-set
    rate_sensitivity_label:           str   # closed-set
    credit_sensitivity_label:         str   # closed-set
    market_access_sensitivity_label:  str   # closed-set
    status:                           str   # closed-set
    visibility:                       str   # closed-set
    metadata:                         Mapping[str, Any]
```

### 4.1 Firm vocabulary (closed sets)

| Field                              | Closed set                                                                          |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| `firm_size_label`                  | `reference_size_small` / `reference_size_medium` / `reference_size_large` / `unknown` |
| `balance_sheet_style_label`        | `equity_heavy` / `balanced` / `debt_heavy` / `cash_rich` / `unknown`                 |
| `funding_dependency_label`         | `low` / `moderate` / `high` / `very_high` / `unknown`                                |
| `demand_cyclicality_label`         | `very_low` / `low` / `moderate` / `high` / `very_high` / `unknown`                  |
| `input_cost_exposure_label`        | `very_low` / `low` / `moderate` / `high` / `very_high` / `unknown`                  |
| `rate_sensitivity_label`           | `very_low` / `low` / `moderate` / `high` / `very_high` / `unknown` (mirrors §3.3)   |
| `credit_sensitivity_label`         | `very_low` / `low` / `moderate` / `high` / `very_high` / `unknown` (mirrors §3.3)   |
| `market_access_sensitivity_label`  | `very_low` / `low` / `moderate` / `high` / `very_high` / `unknown`                  |

### 4.2 Default firm fixture (one per sector)

| Firm id                                | Sector                          | Size                       | Balance sheet style | Funding dep. | Market-access sens. |
| -------------------------------------- | ------------------------------- | -------------------------- | ------------------- | ------------ | ------------------- |
| `firm:reference_energy_a`              | `energy_like`                   | `reference_size_large`     | `debt_heavy`        | `high`       | `moderate`          |
| `firm:reference_materials_a`           | `materials_like`                | `reference_size_medium`    | `balanced`          | `moderate`   | `moderate`          |
| `firm:reference_industrials_a`         | `industrials_like`              | `reference_size_medium`    | `balanced`          | `moderate`   | `moderate`          |
| `firm:reference_consumer_disc_a`       | `consumer_discretionary_like`   | `reference_size_medium`    | `balanced`          | `moderate`   | `moderate`          |
| `firm:reference_consumer_staples_a`    | `consumer_staples_like`         | `reference_size_medium`    | `cash_rich`         | `low`        | `low`               |
| `firm:reference_health_care_a`         | `health_care_like`              | `reference_size_medium`    | `balanced`          | `low`        | `low`               |
| `firm:reference_financials_a`          | `financials_like`               | `reference_size_large`     | `debt_heavy`        | `very_high`  | `high`              |
| `firm:reference_it_a`                  | `information_technology_like`   | `reference_size_medium`    | `cash_rich`         | `low`        | `low`               |
| `firm:reference_comms_a`               | `communication_services_like`   | `reference_size_medium`    | `balanced`          | `moderate`   | `moderate`          |
| `firm:reference_utilities_a`           | `utilities_like`                | `reference_size_medium`    | `debt_heavy`        | `high`       | `high`              |
| `firm:reference_real_estate_a`         | `real_estate_like`              | `reference_size_medium`    | `debt_heavy`        | `very_high`  | `very_high`         |

**No real names.** Every firm id is a synthetic
jurisdiction-neutral plain-id. Tests will pin the absence of
real-issuer tokens (`toyota`, `mufg`, `smbc`, `mizuho`, `boj`,
`sony`, `apple`, `microsoft`, etc.) in the module text,
fixture data, and rendered views.

## 5. Investor and bank archetypes (closed sets)

The v1.20 reference universe expands actors moderately — not
explosively.

### 5.1 Investor archetypes (4 total)

| Archetype label                          | Synthetic semantics                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------------- |
| `benchmark_sensitive_institutional`      | Track-error aware; reacts to broad-cyclicality / rate-environment evidence.       |
| `active_fund_like`                       | More dispersion appetite; reacts to firm-specific evidence + scenario context.    |
| `liquidity_sensitive_investor`           | Sensitive to market-pressure / financing-window evidence.                         |
| `stewardship_oriented_investor`          | Reacts to engagement / dialogue / governance-style evidence (v1.10 chain).        |

Default fixture id pattern:
`investor:reference_<archetype>_a`.

### 5.2 Bank archetypes (3 total)

| Archetype label                  | Synthetic semantics                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------ |
| `relationship_bank_like`         | Existing-firm-coverage bias; reacts to firm-state evidence.                           |
| `credit_conservative_bank`       | Reacts to credit-environment / market-pressure evidence; tighter watch labels.        |
| `market_liquidity_sensitive_bank`| Reacts to interbank-liquidity / central-bank-policy arrivals (v1.13 substrate).       |

Default fixture id pattern:
`bank:reference_<archetype>_a`.

These are **archetypes**, not real institutions. No real
asset-management firm name, no real bank name, no real
regulator name appears anywhere in v1.20 module text,
fixture data, or rendered views.

## 6. Bounded complexity — performance budget pinned at v1.20.0

### 6.1 Universe scale

| Quantity                      | `scenario_monthly_reference_universe` default |
| ----------------------------- | ---------------------------------------------- |
| Periods                       | 12                                             |
| Firms                         | 11                                             |
| Sectors                       | 11                                             |
| Investors                     | 4                                              |
| Banks                         | 3                                              |
| Information arrivals (total)  | 51 (the v1.19.3 default calendar carried over) |
| Scenario applications         | 1 (default test fixture); ≤ 4 (demo fixture)   |

### 6.2 Allowed loop shapes

Per-period loops the engine may use:

| Phase                              | Loop shape          | Default cardinality           | Bound class           |
| ---------------------------------- | ------------------- | ----------------------------- | --------------------- |
| Sector reference setup             | `O(S)`              | 11                            | once-per-run          |
| Firm setup                         | `O(F)`              | 11                            | once-per-run          |
| Information arrival                | `O(P × release_count)` | 12 × ~4 = 51                 | per-period bounded    |
| Firm financial state               | `O(P × F)`          | 12 × 11 = 132                 | per-period bounded    |
| Investor market intent             | `O(P × I × F)`      | 12 × 4 × 11 = 528             | per-period bounded    |
| Aggregated market interest         | `O(P × F)`          | 132                           | per-period bounded    |
| Indicative market pressure         | `O(P × F)`          | 132                           | per-period bounded    |
| Bank credit review                 | `O(P × B × F)`      | 12 × 3 × 11 = 396             | per-period bounded    |
| Capital structure review           | `O(P × F)`          | 132                           | per-period bounded    |
| Financing path                     | `O(P × F)`          | 132                           | per-period bounded    |
| Attention feedback                 | `O(P × (I + B))`    | 12 × 7 = 84                   | per-period bounded    |
| Scenario application (scheduled)   | `O(scheduled_app_count × F)` | 1 × 11 = 11 (default) | bounded by schedule   |

### 6.3 Forbidden loop shapes (binding)

The v1.20 monthly run must **not** introduce any of:

- `O(P × I × F × venue)` — no per-venue fan-out.
- `O(P × I × F × scenario)` — no per-scenario per-pair fan-out
  (scenarios apply at the firm-level via the v1.18.2 chain).
- `O(P × F × order)` — no order-level loop.
- `O(P × day × …)` — no daily fan-out.

### 6.4 Expected record-count range

The v1.20.0 design budget (refined by the v1.20.x
perf-boundary tests):

- per-period record count: **target 200–280 records** for
  `scenario_monthly_reference_universe` default fixture
  (vs. `monthly_reference` ~110 / `quarterly_default` 108).
- per-run window: **target [2400, 3360] records** for the
  default 12-month sweep.
- upper guardrail (binding): **≤ 4000 records** for the
  default fixture. v1.20.x perf-boundary tests will fail loudly
  if this is exceeded.
- scenario application overhead: **≤ 50 additional records**
  per scenario application (template_recorded +
  application_recorded + per-shift records).

### 6.5 Performance discipline

- v1.20.1 / v1.20.2 storage-only milestones add **zero**
  records to any default sweep — they only pin the new
  vocabularies + storage shapes.
- v1.20.3 introduces the new run profile; per-period record
  count moves to the v1.20 target range.
- v1.20.x perf-boundary tests pin the upper guardrail and
  forbidden loop shapes from §6.3.

## 7. Scenario scheduling

### 7.1 `ScenarioSchedule` — design shape pinned at v1.20.0

v1.20.2 will land a `ScenarioSchedule` storage book + a
`ScheduledScenarioApplication` record:

```
@dataclass(frozen=True)
class ScheduledScenarioApplication:
    scheduled_application_id:        str   # plain id
    scenario_driver_template_id:     str   # plain-id citation
    scheduled_period_index:          int   # 1-based month index
    scheduled_month_label:           str   # synthetic month
    affected_firm_ids:               tuple[str, ...]   # plain-id citations
    affected_sector_ids:             tuple[str, ...]   # plain-id citations
    importance_label:                str   # closed-set
    status:                          str   # closed-set
    visibility:                      str   # closed-set
    metadata:                        Mapping[str, Any]
```

### 7.2 Default test fixture (one scenario per run)

```
schedule_id:        scenario_schedule:reference:default_test
period_count:       12
applications:
    scheduled_application_id:    sched_app:credit_tightening:m4
    scenario_driver_template_id: scenario_driver:credit_tightening:reference
    scheduled_period_index:      4
    scheduled_month_label:       2026-04
    affected_firm_ids:           (every firm where funding_dependency_label
                                  ∈ {high, very_high}: financials_like,
                                  utilities_like, real_estate_like,
                                  energy_like)
    importance_label:            high_attention
```

This is the **default test fixture** — pinned by a v1.20.x
trip-wire test for digest stability.

### 7.3 Optional demo fixture (multi-scenario)

Used only by the v1.20.5 UI demo and by an opt-in test:

```
schedule_id:        scenario_schedule:reference:demo_multi
period_count:       12
applications:
    1) rate_repricing_driver           in month 3
    2) credit_tightening_driver        in month 4
    3) liquidity_stress_driver         in month 6
    4) information_gap_driver          in month 8
```

The multi-scenario demo fixture is **opt-in**. It does not
participate in the default test fixture's digest pin.

## 8. Scenario-to-sector impact map

**This is not actor decision logic. This is context /
evidence preparation.** The map decides *which firms / sectors
receive which kind of v1.18.2 context shift evidence on the
scheduled month*. Downstream actor responses still flow
through the v1.12 / v1.14 / v1.15 / v1.16 mechanisms.

### 8.1 Mapping rules (closed-set, deterministic)

Each scenario driver family maps to a *sensitivity dimension*
on the `GenericSectorReference`. v1.20.3 will land the
mapping rules as a closed-set table:

| Scenario family                        | Sensitivity dimension                  | Trigger threshold                                   | Context surface              |
| -------------------------------------- | -------------------------------------- | --------------------------------------------------- | ---------------------------- |
| `rate_repricing_driver`                | `rate_sensitivity_label`               | sector ∈ {`high`, `very_high`}                     | `market_environment`         |
| `credit_tightening_driver`             | `credit_sensitivity_label` + `funding_dependency_label` (firm) | sector credit ∈ {`high`, `very_high`} OR firm funding_dep ∈ {`high`, `very_high`} | `market_environment` + `financing_review_surface` |
| `funding_window_closure_driver`        | `funding_dependency_label` (firm) + `market_access_sensitivity_label` | firm market_access_sens ∈ {`high`, `very_high`}    | `financing_review_surface`   |
| `liquidity_stress_driver`              | `credit_sensitivity_label` + `market_access_sensitivity_label` | sector credit ∈ {`high`, `very_high`}              | `interbank_liquidity` + `market_environment` |
| `input_cost_pressure_driver`           | `input_cost_sensitivity_label`         | sector ∈ {`high`, `very_high`}                     | `firm_financial_state`       |
| `technology_substitution_driver`       | `technology_disruption_sensitivity_label` | sector ∈ {`high`, `very_high`}                  | `industry_condition`         |
| `regulatory_risk_driver` / `policy_subsidy_driver` | `policy_sensitivity_label` | sector ∈ {`high`, `very_high`}                     | `industry_condition`         |
| `sector_demand_deterioration_driver`   | `demand_sensitivity_label` (sector) + `demand_cyclicality_label` (firm) | sector demand ∈ {`high`, `very_high`} OR firm cyclicality ∈ {`high`, `very_high`} | `industry_condition` + `firm_financial_state` |
| `information_gap_driver`               | (universe-wide)                        | always — synthetic information-gap arrival           | `attention_surface`          |
| (other / unknown)                      | —                                      | falls back to v1.18.2 `no_direct_shift` annotation   | `unknown`                    |

### 8.2 What the impact map is **not**

- **Not actor decision logic.** A sector matching a
  sensitivity threshold receives a `ScenarioContextShiftRecord`
  citing the sector / firm; it does not receive a "firm X
  decides to issue equity" record.
- **Not magnitude.** The map decides **whether** a context
  shift is emitted, not how big the shift is. v1.18.2's
  closed-set `shift_direction_label` carries.
- **Not a forecast.** No sector return is predicted; no firm
  EPS is forecast; no price is set.
- **Not a recommendation.** No actor receives a
  `recommendation` field; no `target_price`; no
  `expected_return`.

## 9. Future-LLM-compatibility audit shape (forward-affordance)

Every v1.20 record type carries the v1.18.0 audit shape verbatim:

- `reasoning_mode = "rule_based_fallback"` (binding at
  v1.20.x).
- `reasoning_slot = "future_llm_compatible"` (architectural
  commitment).
- `reasoning_policy_id` — plain id, e.g.
  `"v1.20.3:scenario_to_sector_impact:rule_based_fallback"`.
- `evidence_ref_ids` — plain-id citations.
- `unresolved_ref_count` — non-negative int.
- `boundary_flags` — Boolean mapping carrying the v1.19.0
  default 8-flag set + any v1.20-specific flags.

A future LLM-mode policy must populate the **same fields**
under a different `reasoning_policy_id`. There is **no**
`prompt_text`, **no** `llm_output`, **no** `llm_prose` field
anywhere — pinned by `FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES`
and inherited from `FORBIDDEN_SCENARIO_FIELD_NAMES`.

## 10. UI requirements (v1.20.5)

The static workbench (the v1.19.4 Load-local-bundle target)
gains four new surfaces by the end of v1.20:

### 10.1 Universe view

- **11-sector grid** showing the 11 generic sector labels
  with their group memberships.
- **11-firm grid** showing one representative firm per sector
  with the firm size / balance-sheet-style / funding-
  dependency labels.
- **Sector sensitivity heatmap** rendering the §3.4 matrix
  (label cells; `_like` suffix on every column header).
- **Selected scenario impact by sector** — the §8 mapping
  result for the loaded bundle's scenario.

### 10.2 Monthly timeline

- **12 months** along the x-axis.
- Information arrivals rendered as event chips (the v1.19.3
  arrival count + v1.19.4 summary card already cover the
  baseline data; v1.20 extends with sector-cited arrivals).
- **Scenario application month** highlighted (vertical line +
  callout).
- Context shifts rendered below the timeline.
- Attention / market-pressure / financing-constraint changes
  rendered as compact KPI deltas on each month.

### 10.3 Sector comparison

- Which sectors received the strongest scenario impact (rank
  by impacted-firm count + impacted-context-surface count).
- Which firms developed higher financing pressure (label-
  delta, not number).
- Which investors changed market intent (label histogram,
  rule-id reference).
- Which banks shifted review posture (watch-label histogram).

### 10.4 Boundary statement (always visible)

- *Synthetic reference universe.*
- *Not real companies.*
- *Not real data.*
- *Not investment advice.*
- *Not Japan calibration.*

## 11. Export bundle requirements (v1.20.4)

The `scenario_monthly_reference_universe` bundle extends the
v1.19.1 `RunExportBundle` shape with a richer `manifest`,
plus several v1.20-specific summary sections. Top-level keys:

| Key                                | Source                                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------- |
| `bundle_id`                        | (v1.19.1 standard)                                                                     |
| `run_profile_label`                | `"scenario_monthly_reference_universe"`                                                |
| `regime_label`                     | regime preset                                                                          |
| `selected_scenario_label`          | the test scenario id                                                                   |
| `period_count`                     | `12`                                                                                   |
| `digest`                           | `living_world_digest` of the run                                                       |
| `generated_at_policy_label`        | `"stable_for_replay"`                                                                 |
| `manifest`                         | extends with `firm_count` / `sector_count` / `investor_count` / `bank_count` / `universe_profile_label` / `sector_taxonomy_label` |
| `overview`                         | label-only summary (v1.17.2 snapshot extended with universe-level labels)              |
| `timeline`                         | monthly_timeline payload (12 months × event chips)                                     |
| `regime_compare`                   | `{}` (single-regime export)                                                             |
| `scenario_trace`                   | (v1.18.3 shape; one entry per scheduled application)                                   |
| `attention_diff`                   | universe-wide attention-diff strip                                                      |
| `market_intent`                    | NEW: per-month per-investor histogram                                                  |
| `financing`                        | NEW: per-month per-firm financing-constraint label histogram                           |
| `ledger_excerpt`                   | bounded at 30 records (extended from v1.19.1's 20 for the richer universe)            |
| `boundary_flags`                   | v1.19.0 default 8-flag set + v1.20-specific flags                                      |
| `metadata.information_arrival_summary` | v1.19.3 / v1.19.3.1 shape                                                          |
| `metadata.sector_summary`          | NEW: per-sector label tuple + sensitivity matrix row                                   |
| `metadata.firm_summary`            | NEW: per-firm sector / size / balance-sheet labels                                      |
| `metadata.scenario_application_summary` | NEW: per-scheduled-application impact payload                                       |
| `metadata.scenario_context_shift_summary` | NEW: per-shift summary (firm / sector / surface / direction)                       |
| `metadata.sector_impact_summary`   | NEW: per-sector total impact count                                                     |
| `metadata.scenario_to_sector_mapping_id` | NEW: plain id naming the §8 mapping policy                                       |

## 12. Validation requirements (binding for v1.20.x)

Every v1.20.x milestone must prove:

1. **`quarterly_default` digest unchanged at
   `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`.**
2. **`monthly_reference` digest unchanged at
   `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**
   unless the new profile is explicitly invoked.
3. `scenario_monthly_reference_universe` is **opt-in** — it
   never moves the canonical digests.
4. **No real company names** anywhere (`firm:reference_*` plain
   ids only).
5. **No real sector weights** — sensitivity labels only.
6. **No real financial values** — labels and bounded ordinals
   only.
7. **No real indicator values** — the v1.19.3
   `FORBIDDEN_INFORMATION_RELEASE_FIELD_NAMES` extends
   verbatim.
8. **No real institutional identifiers** — bank / investor
   archetype labels only.
9. **No licensed taxonomy dependency** — bare `GICS` / `MSCI`
   / `S&P` / `FactSet` / `Bloomberg` / `Refinitiv` / `TOPIX` /
   `Nikkei` / `JPX` tokens absent in module text + tests +
   rendered views.
10. **No price records** — the `PriceBook` is byte-equal pre /
    post run on the new profile.
11. **No trade / order / execution records** — the v1.18.2
    forbidden ledger event list is pinned per book at v1.20.x.
12. **No actor decision fields** — the v1.18.0
    `FORBIDDEN_SCENARIO_FIELD_NAMES` extends to v1.20 records.
13. **No source-of-truth book mutation** — v1.18.2 append-only
    discipline carries forward; cited pre-existing records are
    byte-identical pre / post scenario application.
14. **Scenario context shifts remain append-only** (v1.18.2
    invariant).
15. **Export JSON deterministic** — same `(profile, regime,
    scenario, fixture seed)` → byte-identical bundle (v1.19.1
    invariant).
16. **UI can load the bundle** — v1.19.4 schema validator passes
    on the v1.20.4 bundle.
17. **Record count is bounded** — see §6.4 budget.
18. **Future-LLM-compatibility audit shape carried** — see §9.

## 13. Per-milestone roadmap inside v1.20

| Milestone     | What                                                                                                                                                                                                                 | Status                  |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **v1.20.0**   | **Monthly Scenario Reference Universe design (this document)** — profile family, `ReferenceUniverseProfile`, `GenericSectorReference` (11-sector closed-set vocabulary + sector groups + sensitivity dimensions + default sensitivity matrix), `SyntheticSectorFirmProfile` (11 representative firms), investor / bank archetypes (4 + 3), bounded performance budget, scenario scheduling, scenario-to-sector impact map, future-LLM audit shape, UI requirements, export bundle requirements, validation requirements, per-milestone roadmap, hard boundary. | **Shipped (docs-only)** |
| **v1.20.1**   | **`world/reference_universe.py`** — three immutable frozen dataclasses (`ReferenceUniverseProfile`, `GenericSectorReference`, `SyntheticSectorFirmProfile`) + one append-only `ReferenceUniverseBook` with 17 read methods + twelve closed-set frozensets (`UNIVERSE_PROFILE_LABELS` 5 / `SECTOR_TAXONOMY_LABELS` 4 / `SECTOR_LABELS` 12 / `SECTOR_GROUP_LABELS` 7 / `SENSITIVITY_LABELS` 4 / `FIRM_SIZE_LABELS` 5 / `BALANCE_SHEET_STYLE_LABELS` 6 / `FUNDING_DEPENDENCY_LABELS` 4 / `DEMAND_CYCLICALITY_LABELS` 5 / `INPUT_COST_EXPOSURE_LABELS` 4 / `STATUS_LABELS` 6 / `VISIBILITY_LABELS` 5); the v1.20.0 hard-naming-boundary `FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES` frozenset composing the v1.18.0 actor-decision tokens with the v1.20.0 real-issuer / real-financial / licensed-taxonomy tokens (`real_company_name` / `real_sector_weight` / `market_cap` / `leverage_ratio` / `revenue` / `ebitda` / `net_income` / `real_financial_value` / `gics` / `msci` / `sp_index` / `topix` / `nikkei` / `jpx`); three new `RecordType` enum values (`REFERENCE_UNIVERSE_PROFILE_RECORDED` / `GENERIC_SECTOR_REFERENCE_RECORDED` / `SYNTHETIC_SECTOR_FIRM_PROFILE_RECORDED`); kernel wired with `WorldKernel.reference_universe: ReferenceUniverseBook` empty by default — pinned by `test_empty_reference_universe_does_not_move_quarterly_default_digest` and `test_empty_reference_universe_does_not_move_monthly_reference_digest`; deterministic `build_generic_11_sector_reference_universe(...)` helper that constructs the v1.20.0-pinned default fixture (1 universe profile + 11 sector references + 11 firm profiles) **without** registering anything on a kernel + an explicit `register_generic_11_sector_reference_universe(book, ...)` helper for storage; **storage only** — no run profile, no scenario schedule, no CLI extension, no UI extension; +92 tests in `tests/test_reference_universe.py` covering closed-set vocabularies, hard-naming-boundary disjointness from vocab + dataclass field names + `to_dict` keys + payload keys + metadata keys, frozen immutability, every per-label rejection path, `period_count` / `firm_count` `bool` rejection, duplicate id rejection (no extra ledger record), unknown id `KeyError`, every `list_*` / filter method, `snapshot()` determinism, ledger one-record-per-add, kernel wiring, no-`PriceBook`-mutation, no-`quarterly_default`-digest-move trip-wire, no-`monthly_reference`-digest-move trip-wire, no-actor-decision-event-types, builder produces 11 + 11 records using `_like` sector labels, builder uses no real company names, builder uses no licensed taxonomy dependency, builder does not auto-register, builder is deterministic across runs, explicit registration helper writes to kernel + raises on repeat, jurisdiction-neutral identifier scan + licensed-taxonomy scan over both module + test text. | **Shipped (4614 tests)**       |
| **v1.20.2**   | **`world/scenario_schedule.py`** — two immutable frozen dataclasses (`ScenarioSchedule`, `ScheduledScenarioApplication`) + one append-only `ScenarioScheduleBook` with 17 read methods + six closed-set frozensets (`RUN_PROFILE_LABELS` 5 / `SCHEDULE_POLICY_LABELS` 5 / `APPLICATION_POLICY_LABELS` 6 / `SCHEDULED_MONTH_LABELS` 13 / `STATUS_LABELS` 6 / `VISIBILITY_LABELS` 5); the v1.20.0 hard-naming-boundary `FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES` frozenset composing the v1.18.0 actor-decision tokens with the v1.20.0 real-issuer / real-financial / licensed-taxonomy tokens; two new `RecordType` enum values (`SCENARIO_SCHEDULE_RECORDED` / `SCHEDULED_SCENARIO_APPLICATION_RECORDED`); `MONTHLY_PERIOD_INDEX_MIN` / `MONTHLY_PERIOD_INDEX_MAX` constants pinning the `[0, 11]` bound for monthly profile period indices; kernel wired with `WorldKernel.scenario_schedule: ScenarioScheduleBook` empty by default — pinned by `test_empty_scenario_schedule_does_not_move_quarterly_default_digest` and `test_empty_scenario_schedule_does_not_move_monthly_reference_digest`; deterministic `build_default_scenario_monthly_schedule(...)` helper constructs the v1.20.0 default single-scenario schedule (one `ScenarioSchedule` + one `ScheduledScenarioApplication` — `credit_tightening_driver` at month 4 / period index 3 on `generic_11_sector` universe, `apply_after_information_arrivals` policy) **without** registering anything on a kernel; period-index validation rejects `bool`, negatives, and values > 11; references stored as plain ids only (no resolution at storage level — v1.20.3 will validate at run time); **storage only** — no run profile, no scenario application execution, no CLI extension, no UI extension; +90 tests in `tests/test_scenario_schedule.py` covering closed-set vocabularies, hard-naming-boundary disjointness, frozen immutability, every per-label rejection path, period-index `bool` / negative / `>11` rejection, period-index 0 and 11 acceptance, duplicate id rejection (no extra ledger record), unknown id `KeyError`, every `list_*` / filter method, `snapshot()` determinism, ledger one-record-per-add, kernel wiring, no-`PriceBook`-mutation, no-`quarterly_default`-digest-move trip-wire, no-`monthly_reference`-digest-move trip-wire, no-actor-decision-event-types (incl. no `scenario_driver_application_recorded` / `scenario_context_shift_recorded`), helper produces 1+1 records at month_04 / period 3, helper does not auto-register, helper accepts plain-id citations without resolution, jurisdiction-neutral identifier scan + licensed-taxonomy scan over both module + test text. | **Shipped (4704 tests)**       |
| **v1.20.3**   | **`scenario_monthly_reference_universe` run profile in `world/reference_living_world.py`** — extends `_SUPPORTED_RUN_PROFILE_LABELS` to `{"quarterly_default", "monthly_reference", "scenario_monthly_reference_universe"}` (the `quarterly_default` `f93bdf3f…b705897c` and `monthly_reference` `75a91cfa…91879d` digests stay byte-identical); idempotently registers the v1.20.1 generic 11-sector reference universe (1 + 11 + 11 = 23 setup records), the v1.18.1 credit-tightening scenario template (1 setup record), and the v1.20.2 default scenario schedule (1 + 1 = 2 setup records) **only** under the new profile; reuses the v1.19.3 `InformationReleaseCalendar` for monthly arrivals (3-5 per month, total 51); fires exactly one scheduled scenario application at `period_index == 3` / `month_04` via `apply_scenario_driver(...)` with the credit-tightening template, emitting 1 `ScenarioDriverApplicationRecord` + 2 `ScenarioContextShiftRecord` (`market_environment` + `financing_review_surface`) — bounded by `O(scheduled_app_count × F) = 1 × 11 = 11` shifts; the closed-loop chain (attention → investor market intent → aggregated market interest → indicative market pressure → capital structure review / financing path → next-period attention) runs unchanged on the larger 4-investor / 3-bank fixture; the engagement / dialogue / escalation / strategic-response / valuation / investor-intent / stewardship-themes layer is skipped under the new profile to keep the per-period record count under the v1.20.0 budget; `LivingReferencePeriodSummary` and `LivingReferenceWorldResult` extended with seven new tuple fields (`reference_universe_ids` / `sector_ids` / `firm_profile_ids` / `scenario_schedule_ids` / `scheduled_scenario_application_ids` / `scenario_application_ids` / `scenario_context_shift_ids`); `examples/reference_world/living_world_replay.py` canonical view extended additively (new keys appear in canonical JSON only when non-empty so pre-existing digests stay byte-identical); `world/reference_universe.py`, `world/scenario_drivers.py`, and `world/scenario_schedule.py` `add_*` methods now accept a `simulation_date` kwarg (orchestrator passes `iso_dates[0]` for v1.20.3 setup records); `world/scenario_applications.py::add_application` and `add_context_shift` use `record.as_of_date` as the ledger entry's `simulation_date` so canonical views are byte-deterministic; new pinned `living_world_digest` for the new profile is **`5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`**; **per-period record count 257-261 (within target [200, 280])**; **per-run window 3220 records (within target [2400, 3360]; under hard guardrail ≤ 4000)**; +40 tests across `tests/test_living_reference_world.py` (functional + boundary scans) and `tests/test_living_reference_world_performance_boundary.py` (cardinality budget + forbidden-loop-shape detection + digest pin + determinism). | **Shipped (4744 tests)**       |
| **v1.20.4**   | **`examples/reference_world/export_run_bundle.py` extension** — accepts `--profile scenario_monthly_reference_universe`; `EXECUTABLE_PROFILES` extended additively with `scenario_monthly_reference_universe` (existing labels unchanged); `world.run_export.RUN_PROFILE_LABELS` extended additively; new module-level `SCENARIO_UNIVERSE_PROFILE_SUPPORTED_SCENARIOS = ("none_baseline", "credit_tightening_driver")` — `credit_tightening_driver` is **only** valid under the universe profile, the CLI rejects every other (scenario, profile) combination; `_build_bundle_for_scenario_monthly_reference_universe(...)` mirrors the v1.19.3.1 monthly_reference shape and adds three v1.20.x-specific bundle sections — `reference_universe` (universe profile id + 11 sector ids + 11 firm profile ids + 11 firm ids + 11 sector labels with the `_like` suffix + per-sector sensitivity summary on the v1.20.0 six-dimension five-rung closed set), `scenario_trace` (scheduled-application + applied-application + emitted context-shift ids; merged context-surface labels — `market_environment` + `financing_review_surface` — and shift-direction labels — `tighten`; per-application `affected_sector_ids` (11) + `affected_firm_profile_ids` (11) read from the v1.20.4 orchestrator's application metadata; merged `boundary_flags` AND view; v1.18.0 `reasoning_modes` / `reasoning_slots` audit shape), and `market_intent` / `financing` (compact label-only histograms with counts pinning the closed-loop allowed-shape cardinality — `O(P × I × F) = 528` market intents and `O(P × F) = 132` aggregated interest / indicative pressure / financing path / capital-structure review); reuses the v1.19.3.1 `information_arrival_summary` (1 calendar / 51 scheduled releases / 51 arrivals across 12 months); `ledger_excerpt` bounded at `LEDGER_EXCERPT_LIMIT = 20` with v1.20.x-setup-priority selection; volatile fields (`record_id`, `timestamp`) stripped per v1.19.2 convention; the `world.reference_living_world` orchestrator now stamps the scenario application metadata with universe-wide `affected_sector_ids` (all 11) and `affected_firm_profile_ids` (all 11) so the per-sector / per-firm impact is visible without recomputing the universe — the application stays at exactly 1 record + 2 context shifts (`market_environment` + `financing_review_surface`); the canonical `quarterly_default` `living_world_digest` (`f93bdf3f…b705897c`) and `monthly_reference` `living_world_digest` (`75a91cfa…91879d`) are unchanged; pinned CLI bundle digest for `--profile scenario_monthly_reference_universe --regime constrained --scenario credit_tightening_driver`: **`ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`**; bundle is fully deterministic — same CLI args → byte-identical JSON; no wall-clock timestamp anywhere; no absolute path leakage (`/tmp/` / `/Users/` / `/home/` / the `--out` path itself); +20 CLI tests in `tests/test_run_export_cli.py` (parsable JSON, two-run byte-identity, digest pin, manifest counts, reference_universe section shape, scenario_trace section shape, per-application `affected_sector_ids` / `affected_firm_profile_ids` surfaced, information_arrival_summary, market_intent + financing summaries, ledger excerpt cap + scenario priority, no ISO wall-clock, no absolute paths, no real indicator values, no licensed-taxonomy tokens via `_LICENSED_TAXONOMY_TOKENS` + `_JURISDICTION_TOKENS`, no quarterly_default / monthly_reference digest move, rejects `credit_tightening_driver` under unrelated profiles, rejects unrelated scenario labels under universe profile, accepts `none_baseline` under universe profile, designed-but-not-executable labels still rejected). **CLI-only — no UI rendering changes (deferred to v1.20.5), no backend, no fetch / XHR, no daily simulation, no LLM execution.** | **Shipped (4764 tests)**       |
| v1.20.5       | `examples/ui/fwe_workbench_mockup.html` extension — adds the §10 universe view / sector-sensitivity heatmap / monthly timeline with scenario-application callout / sector comparison surface. The v1.19.4 `<input type="file">` loader gains the new bundle's profile in `BUNDLE_EXECUTABLE_PROFILES`. **Read-only static viewer; no engine execution.** Validate gains audit checks for the new universe / sector / monthly cards. No pytest delta. | Planned                 |
| v1.20.last    | Monthly Scenario Reference Universe freeze (docs-only) — single-page reader-facing summary in `docs/v1_20_monthly_scenario_reference_universe_summary.md`; v1.20.last release-readiness snapshot in `RELEASE_CHECKLIST.md`; v1.20.last freeze-pin section in `docs/performance_boundary.md`; v1.20.last `test_inventory.md` header note; v1.20.last cross-link in `docs/fwe_reference_demo_design.md`, `examples/reference_world/README.md`, and `examples/ui/README.md`. | Planned                 |

## 14. Hard boundary statement

v1.20 increases realism by adding **temporal granularity**
(quarterly → monthly) and **cross-sectional breadth** (3 firms
→ 11 firms / 11 sectors). It does **not** turn FWE into:

- a market simulator;
- a price-formation layer;
- a forecast layer;
- a daily-frequency economic simulation;
- a recommendation engine;
- an investment-advice surface;
- a real-data view;
- a Japan calibration;
- an LLM execution path;
- a real-company simulator;
- a vendor-classification implementation (no GICS / MSCI / S&P
  / FactSet / Bloomberg / Refinitiv / TOPIX / Nikkei / JPX);
- a SaaS, a backend, or a Rails app.

It **remains synthetic, auditable, replayable, future-LLM-
compatible, and read-only-loader-friendly.**

No order submission. No buy / sell labels. No order book. No
matching. No execution. No clearing. No settlement. No quote
dissemination. No bid / ask. No price update. No `PriceBook`
mutation. No target price. No expected return. No
recommendation. No portfolio allocation. No real exchange
mechanics. No financing execution. No loan approval. No bond /
equity issuance. No underwriting. No syndication. No pricing.
No interest rate. No spread. No coupon. No fee. No offering
price. No investment advice. No real data ingestion. No
Japan calibration. No LLM execution. No stochastic behaviour
probabilities. No learned model. **No firm decision rule, no
investor action rule, no bank approval logic, no trading
decision model, no optimal capital structure rule.** **No
real company name, no real sector index membership, no
licensed taxonomy dependency, no real financial-statement
value, no real market-cap value, no real leverage ratio, no
real-issuer mapping.** **No browser-to-Python execution. No
backend server. No Rails. No real-time execution from the UI.
No daily full economic simulation in v1.20.x.**

## 15. Forward pointer

v1.20.1 lands the universe / sector / firm storage. v1.20.2
lands the scenario-schedule storage. v1.20.3 lands the
`scenario_monthly_reference_universe` run profile. v1.20.4
extends the CLI exporter. v1.20.5 extends the static UI.
v1.20.last freezes.

The next sequence (v1.21+) candidates:

- **v1.21 — `scenario_monthly` profile (small fixture
  variant)** — the small-fixture `scenario_monthly` path the
  v1.20 design deferred. Would wire the v1.18.2
  `apply_scenario_driver(...)` chain into the existing 3-firm
  `monthly_reference` profile so a reader can run a quick
  small-universe scenario test.
- **v1.21 — Institutional Investor Mandate / Benchmark
  Pressure design (alternative)** — a synthetic mandate /
  benchmark layer (jurisdiction-neutral, label-only) that
  shapes investor reasoning under the v1.16 closed loop.
  Each new label is a closed-set extension; no new mechanism;
  the v1.18.2 scenario application + v1.19.3 information
  arrivals + v1.20 reference universe remain unchanged.
- **v2.0 — Japan public calibration in private JFWE only.**
  Public FWE remains jurisdiction-neutral and synthetic. The
  v1.20 `_like`-suffixed sector labels remain in public FWE;
  any real-taxonomy mapping moves to private JFWE.
- **Future LLM-mode reasoning policies.** When introduced,
  must populate the same `ActorReasoningInputFrame` /
  `ReasoningPolicySlot` audit shape pinned at v1.18.0 — input
  evidence ids, prompt / policy id, output label, confidence /
  status, rejected / unknown cases — and must **never** hide a
  mutation of any source-of-truth book.
- **Future price formation remains gated** until the v1.16 /
  v1.17 / v1.18 / v1.19 / v1.20 surface is operationally
  legible to a reviewer who has not read this codebase.
  Adding price formation on top of an opaque universe / sector
  / scenario layer would defeat the auditability goal of every
  prior freeze.

The v1.20 chain stays universe-only, sector-label-only, firm-
profile-only, scenario-schedule-only, append-only, and CLI-
first-with-read-only-UI-loader forever. Future milestones may
*cite* v1.20 universe / sector / firm / schedule records
(plain-id cross-references, additional rendering kinds), but
they may **never** mutate the v1.20.0 vocabulary, replace the
deterministic rule-based fallback with a runtime-active LLM
mode without the audit shape, hard-code real company names /
real sector weights / real financial values, license a real
taxonomy, or introduce daily full economic simulation on top
of the universe layer.
