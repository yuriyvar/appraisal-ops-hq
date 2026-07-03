# Code brief — Build C: subject-resolution + cache (phased)

> Durable resume doc for a token/context-limited build. Each phase is committable; if a session
> resets, read this + `git log --oneline -10`, continue from the first unchecked phase.
> Build C was decided as "the next build day's plan" on 2026-07-02 (YV), after the 6/19 renderer
> brief closed (`dbef532..72b7633`). Companion context in Code app memory: `renderer-buildday-plan.md`.

## Progress tracker
- [x] Phase 0 — this brief committed
- [x] Phase 1 — cache core: `tools/subject-resolution/subject_cache.py` + address normalization
      + staleness-as-flag + QA runner `tests_subject_resolution.py`
- [x] Phase 2 — resolver skeleton + per-county pull sheet: `resolve_subject.py` (cache-first →
      routing → `subject.skeleton.json` + `pull-sheet.md`)
- [x] Phase 3 — ingest + normalize: `ingest_subject.py` (raw pull → validated subject.json →
      cache put) + fix the assembler-README phantom `subject.example.json`
- [x] Phase 4 (STRETCH — landed) — ArcGIS adapter, canned-fixture tested; FIELD_MAPS ship
      `verified: false` — first live pull must confirm the attribute names + flip the flag
- [x] Phase 5 — wrap: `/resolve-subject` command · SKILL wiring (property-search +
      worksheet-builder cache-first step) · README · inbox · interlane [ACTION] · handoff
- **ALL PHASES DONE 2026-07-02 (same-day build).** First live pull must verify the ArcGIS
  FIELD_MAPS attribute names (ship `verified: false`) and COWORK_AGENT owes a [DONE] after
  running `/resolve-subject` on a real order.

## Context — the muda being killed
Subject data pull is the slowest manual step on every order (~65–90/mo): COWORK_AGENT hand-browses
the county SOR + Zillow + the gas map, transcribes into `subject.json`, re-learning "which portal,
which fields, which quirks" each time. Nothing is reused between orders — a repeat order or a
same-subdivision subject redoes 100% of the work. Build C gives the pipeline:
1. **Cache** — resolved subjects persist; repeat lookups are instant and *flagged as cached, never
   silently reused stale*.
2. **Routing** — address → county → SOR vendor/URL/technique + gas provider + MLS system, printed
   as a ready-to-run **pull sheet** (kills the per-order "where do I even look" overhead).
3. **Normalization** — raw pulled values → schema-valid `subject.json` with the same fail-loud
   gates the rest of the pipeline has (null+flag, never guessed).

Downstream stays untouched: `subject.json` (v1.1 shape) remains the assembler's input contract.

## Locked constraints
1. **Client data never enters the repo.** The cache DB lives in the CLIENT zone:
   `C:\Users\yuriy\VDV Appraisals\Subject cache\subject-cache.sqlite` (created on first put).
   Repo holds code + synthetic-fixture tests only. QA temp dirs outside the repo (T14 pattern).
2. **Stdlib only** (sqlite3, json, re, urllib). No bs4/requests — which is exactly why APEX/vgsi
   HTML scraping is OUT of scope (brittle regex soup); browser-bound vendors get a pull sheet, not
   a scraper.
3. **Fail loud, never guess** (CLAUDE.md #7): cache hits always set `resolution.cached=true` +
   `resolution.resolved_on`; hits older than **180 days** (or with `assessment.tax_year` behind the
   effective year) add a subject flag "cached subject data N days old — re-verify assessment / tax
   year before use", and are still returned (flag, don't hide). Normalizer emits null+flag for
   missing GLA, unknown codes, acreage↔sf mismatches — never a filled-in guess.
4. **Registry is the routing source of truth** (`skills/property-search/references/county-registry.md`
   mirrors the Google Sheet). The resolver reads a compact committed mirror
   `tools/subject-resolution/county_routing.json` seeded from the registry (vendor, SOR URL,
   technique note, MLS, gas note, quirks). Drift rule: registry.md edits MUST touch the JSON in the
   same commit (note added to registry header in Phase 2).
5. **No credentials anywhere** in code or routing JSON. Navica/Matrix stay in their existing
   documented flows.
6. **Deterministic where testable**: cache + normalizer are pure/deterministic (QA byte-checks);
   only the stretch ArcGIS adapter touches the network, and it must degrade to the pull-sheet path
   on any failure (clear message, non-zero exit, no crash, no partial cache write).
7. Existing record paths and the v1.1 schema are NOT changed by Build C. (The skeleton emits the
   v1.1 subject.json shape incl. `assessors_parcel_number`, `water/sewer: null`, `re_taxes_annual`,
   `hoa_*`, `neighborhood_bounds`, `market.search.surrounding_counties` from the registry's
   Navica-market sets where known.)

## Phases (each = edit → run QA → caveman commit; independently stoppable)

### Phase 1 — cache core
`tools/subject-resolution/subject_cache.py`:
- `normalize_address(raw) -> key`: uppercase; strip punctuation + unit/apt/suite suffixes; collapse
  whitespace; USPS suffix canon (STREET→ST, ROAD→RD, LANE→LN, DRIVE→DR, COURT→CT, CIRCLE→CIR,
  AVENUE→AVE, PLACE→PL, TERRACE→TER, HIGHWAY→HWY, PARKWAY→PKWY); directionals (NORTH→N …).
  Key = `"<street>|<city-or-county>|<zip?>"` — tolerant of the county/city slot differing.
- Schema: `subjects(key TEXT PK, address_full TEXT, county TEXT, subject_json TEXT,
  resolved_on TEXT, source TEXT, put_at TEXT)` + `meta(schema_version)`.
- API: `get(addr) -> (subject_dict, resolved_on, age_days) | None` (age computed vs an explicit
  `--as-of` date for determinism; CLI defaults to today), `put(addr, subject_dict, source)`,
  `list_entries()`, `delete(key)`. CLI: `get|put|list|delete`.
- QA `tests_subject_resolution.py` (same PASS/FAIL pattern as Build B): normalization table
  (≥10 cases incl. "119 Example Ridge Lane" == "119 EXAMPLE RIDGE LN."), roundtrip put/get
  byte-stable, miss returns None, staleness flag at 180d boundary + tax-year-behind case,
  DB-path-outside-repo boundary test, determinism with `--as-of`.

### Phase 2 — resolver skeleton + pull sheet
`tools/subject-resolution/resolve_subject.py "<address>" --county <X> [--order-id … --form-type …
--effective-date … --out-dir <order-folder>]`:
- Cache-first (Phase 1). Hit → write `subject.json` from cache with `resolution.cached=true` +
  staleness flag per rule 3, print summary, done.
- Miss → `county_routing.json` lookup (seed it this phase from the registry's two coverage tables:
  Henrico/Chesterfield/Hanover/Richmond City/Goochland/Powhatan/New Kent/Chesapeake/Charlotte/
  Buckingham/Prince Edward/Mecklenburg) → emit:
  - `subject.skeleton.json` — v1.1 shape; order/address/resolution blocks filled
    (`method`, `input_was_address_only`, `resolved_on=null`), every data field null,
    `market.search.surrounding_counties` pre-filled for the Navica markets (registry sets),
    `mls_systems` from routing.
  - `pull-sheet.md` — the per-order run card: SOR vendor + URL + technique line, the FULL
    worksheet-builder Source-1/2/3 checklist rendered with the subject's address baked in, the gas
    DB query + provider answer for the county (read
    `skills/property-search/references/va-gas-providers.sqlite` — read-only, note the
    no-row = "not yet looked up" rule), county quirks from routing, MLS + both-accounts warnings
    where applicable.
- Unknown county → loud exit listing covered counties (never a generic guess).
- QA: routing covers all registry rows (count assert), skeleton validates against schema required
  shape, pull sheet contains vendor URL + gas line + checklist anchors for 2 fixture counties,
  cache-hit path exercised.

### Phase 3 — ingest + normalize
`tools/subject-resolution/ingest_subject.py raw_subject.json [--out subject.json]`:
- Accepts the hand-filled skeleton (or any partial raw dict), normalizes: `$`/comma/`sf` strip on
  numerics; acreage↔sf cross-check (|sf − ac×43560| ≤ 2% else flag both); baths split; APN
  formatting per county quirk (Chesterfield strip-dashes; Charlotte `086--A---7-A` passthrough);
  `use_code`/heat/AC codes passthrough (unknown → keep + flag); GLA missing/zero → null + flag;
  tax_year vs effective-date sanity; photo-derived fields forced to carry "confirm at inspection"
  flags (Zillow rule); verification rows auto-seeded when both county+MLS GLA supplied.
- On success: writes `subject.json` AND `subject_cache.put()` (single write path into the cache —
  only validated data gets cached).
- Fix while here: assembler README's "Files" table lists `subject.example.json` which never
  existed — commit a synthetic v1.1 one (adapt today's renderer-fixture input) into
  `tools/record-assembler/` and point both READMEs at it.
- QA: normalization cases, mismatch flags fire, cache-write happens only on valid input,
  round-trip skeleton→ingest→assemble→render exits 0 on a synthetic order.

### Phase 4 — STRETCH (droppable without shame): ArcGIS FeatureServer adapter
The one vendor family with clean JSON (no HTML parsing): Chesterfield
(`services3.arcgis.com/.../Cadastral_ProdA/FeatureServer/3`) + Hanover (`maps.civ.quest/...`).
`fetch_arcgis.py --county Chesterfield "<address>"` → address query → parcel attributes → mapped
into the skeleton fields it can prove (APN, legal, acreage, year built, sale hist where layered) —
everything else stays TBD for the pull sheet. urllib + timeout; ANY failure (offline, endpoint
moved, 0 rows, >1 candidate row) → loud fallback message + normal pull-sheet path, non-zero exit,
no cache write. QA: mapping unit-tested against a canned JSON response fixture (no network in QA).

### Phase 5 — wrap
`.claude/commands/resolve-subject.md` (cache-first → pull sheet → ingest → assemble chain);
property-search SKILL Step 1 gains "run resolve_subject first — cache hit may skip the portal";
worksheet-builder SKILL checklist header points at the pull sheet; `tools/subject-resolution/README.md`;
registry header gains the routing-JSON same-commit drift rule; vault inbox line; interlane FYI
(COWORK_AGENT starts every order with `/resolve-subject`); session handoff.

## Out of scope
APEX/vgsi/actdatascout/InteractiveGIS HTML scraping (browser lane + pull sheet cover them) ·
MCP server wrapper · Google-Sheet registry writes (YV-gated, logged-in Chrome) · Zillow scraping
(TOS + brittle; stays a manual checklist step) · comp caching (different lifecycle — comps expire
with the market; subjects don't) · any schema change.

## Verify (per phase)
```powershell
python "appraisal-ops-hq\tools\subject-resolution\tests_subject_resolution.py"   # all green
python "appraisal-ops-hq\tools\record-assembler\tests_qa_runner.py"              # 21/21 stays green
```
Phase 2+: run resolve→ingest→assemble→render end-to-end on a synthetic Henrico order in %TEMP%;
renderer exit 0; cache DB created under `VDV Appraisals\Subject cache\`, never under the repo.
