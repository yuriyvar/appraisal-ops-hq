# Subject Resolution + Cache (Build C)

Automates the slowest manual step: resolving a subject property's data.
Cache-first; on a miss it emits a filled-in **run card** so the browser pull is
mechanical, then the ingester gates the data before anything downstream sees it.

Brief + phase history: `docs/2026-07-02_build-c_subject-resolution-cache_code-brief.md`.

## Flow
```
address ──► resolve_subject.py ──► CACHE HIT ──► subject.json (cached=true + staleness flags)
                    │
                    └► MISS ──► subject.skeleton.json (v1.1, all-null — never guessed)
                            └► pull-sheet.md (SOR vendor/URL/technique · Source-1/2/3
                               checklist · gas-provider answer · MLS + surrounding counties)
                                    │
                       [optional] fetch_arcgis.py — auto-fills what the county
                                  FeatureServer can prove (Chesterfield/Hanover)
                                    │
                       human/Chrome pull fills the skeleton
                                    │
                    ingest_subject.py ──► normalize + gates ──► subject.json ──► CACHE PUT
                                    │
                    assemble_record.py ──► render_worksheet.py (unchanged contract)
```

## Commands
```powershell
# resolve (cache-first). Out-dir must be in the client zone — repo paths refuse.
python tools/subject-resolution/resolve_subject.py "4237 Hall Rd, Boydton, VA 23917" `
    --county Mecklenburg --order-id 26-0099 --form-type 2055 `
    --effective-date 2026-07-02 --out-dir "C:\Users\yuriy\VDV Appraisals\<order>"

# optional ArcGIS auto-fill (Chesterfield / Hanover only)
python tools/subject-resolution/fetch_arcgis.py "<address>" --county Chesterfield `
    --skeleton "<order>\subject.skeleton.json"

# after the pull: normalize, gate, cache
python tools/subject-resolution/ingest_subject.py "<order>\subject.skeleton.json" `
    --out "<order>\subject.json" --source "APEX pull" --resolved-on 2026-07-02

# cache inspection
python tools/subject-resolution/subject_cache.py list
python tools/subject-resolution/subject_cache.py get "<address>" --as-of 2026-07-02
```

## Files
| File | Purpose |
|---|---|
| `subject_cache.py` | SQLite cache + address normalization + staleness flags |
| `resolve_subject.py` | cache-first resolver; emits skeleton + pull sheet on miss |
| `county_routing.json` | committed mirror of the county registry (routing only) |
| `ingest_subject.py` | normalizer + fail-loud gates; the ONLY cache write path |
| `fetch_arcgis.py` | stretch: FeatureServer auto-pull (fill-nulls-only) |
| `add_county.py` | BD1: adds a jurisdiction to registry + routing TOGETHER (all-or-nothing) |
| `tests_subject_resolution.py` | QA runner (17 tests, no network) |

## Multi-source verification (BD2, 2026-07-02)
- Pull order **MLS → County/GIS → Zillow** (the pull sheet walks it). Per-source values
  for the tracked fields (gla_sf · year_built · lot_size_acres · bedrooms · full_baths ·
  stories) go into the skeleton's `source_values.<field>.{mls,county,zillow}` slots.
- **YV's variance protocol:** county-vs-MLS agree → county governs quietly. Disagree →
  read the listing; if it SUPPORTS the variance, one line in `variance_notes.<field>` →
  MLS governs WITH the reason; if not → County rules. **Either way** the field carries
  an "inconsistent — manual triage" chip (verification row + worksheet header) until
  YV clears it. Zillow never governs (informational; lone-source fallback with a
  "weakest source" note only).
- **Clearing a triage chip** = YV decides → re-ingest with `variance_notes` filled
  (supported) or the wrong source value corrected. Never hand-delete the flag string.

## ⚠ Cowork-lane limitation (Ton's andon 2026-07-04 — VERIFIED host-side same day)
The **Cowork sandbox cannot write SQLite over its mounted volumes** (`disk I/O error` on
`CREATE TABLE`/`INSERT` — an advisory-lock limitation of the mount layer; reads and plain-file
writes are fine). The HOST (Code lane / real CLI) writes the same DB cleanly (verified with a
put/get/delete on the real `Subject cache\subject-cache.sqlite`). Standing arrangement:
- **Cowork:** run `ingest_subject.py … --no-cache` (flag the run-log as Ton already does) —
  everything else in the pipeline works from that lane.
- **Host:** sweep the orders afterward: `python tools/subject-resolution/subject_cache.py
  backfill "C:\Users\yuriy\VDV Appraisals"` — validated (stamped) subject.json files enter the
  cache; undated ones are listed, never guessed. Idempotent; add it to the weekly `/review`.
- **Durable fix:** the BD4 MCP server runs as a HOST process — once YV wires `appraisal-data`
  into the Cowork config, Ton's `ingest_subject` tool calls write the cache natively and
  `--no-cache` becomes unnecessary.
- Related mount quirks from the same andon (Cowork-side): bash reads of freshly-written repo
  files can come back TRUNCATED (write under a NEW filename to bust the cache) and Cowork's
  Write can't create nested dirs (write flat, then `mkdir -p` + `cp`).

## Standard-work enforcement (BD1, 2026-07-02)
- Every resolve writes **`run-log.md`** — the order's checklist. Tools tick their own
  steps (resolver=1, ingester=3); humans tick 2 (pull) and 4 (comps). Unchecked boxes
  on finished orders surface in the weekly `/review` Phase-4 audit.
- **Provenance chips (warn loud, never block):** ingest without a `pull-sheet.md`
  sibling → "standard work not verified" flag; a subject.json with no
  `resolution.resolved_on` (i.e. it bypassed ingest) → "produced outside standard
  work" chip on the rendered worksheet header.
- New counties go in via `add_county.py` — never hand-edit only one of
  registry/routing (the drift rule is mechanical now).

## Rules encoded
- **Cache DB lives in the client zone** (`C:\Users\yuriy\VDV Appraisals\Subject cache\
  subject-cache.sqlite`, override `--db` / `$env:VDV_SUBJECT_CACHE`). A repo-resident
  path **raises**. Same guard on resolver/ingester output dirs.
- **Staleness is a flag, never a filter**: hits older than 180 days, or with the
  assessment tax year behind the as-of year, come back WITH warnings attached
  (`resolution.cached=true`, original `resolved_on` preserved = the data's vintage).
- **Never guessed**: skeleton data fields are all null; ingest gates GLA (null+flag),
  lot sf↔acres (>2% → flag both), tax-year sanity, county-vs-MLS GLA (verification
  row, county governs); photo-derived fields carry "confirm at inspection".
- **Only validated data reaches the cache** — `ingest_subject.py` is the single
  write path; the ArcGIS adapter never touches the cache and fills nulls only,
  with `verified:false` field maps flagged until a live pull confirms them.
- **Routing drift rule**: `county-registry.md` coverage edits MUST update
  `county_routing.json` in the same commit.
- Unknown county → loud exit listing coverage. Stdlib only. QA has no network.
