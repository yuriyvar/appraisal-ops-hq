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
| `tests_subject_resolution.py` | QA runner (14 tests, no network) |

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
