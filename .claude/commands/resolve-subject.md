# /resolve-subject — cache-first subject resolution (Build C)

Start EVERY order's subject work here — a cache hit skips the county portal
entirely; a miss hands you a ready-to-run pull sheet.

Input: subject address (+ county if the address doesn't carry it) + order meta.

## Step 1 — Resolve
```powershell
python tools/subject-resolution/resolve_subject.py "<address>" --county <Jurisdiction> `
    --order-id <id> --form-type <1004|2055|...> --effective-date <YYYY-MM-DD> `
    --out-dir "C:\Users\yuriy\VDV Appraisals\<order-folder>"
```
- **CACHE HIT** → `subject.json` + `run-log.md` written (`resolution.cached=true`, original
  pull date preserved). **Read the FLAG lines** — stale (>180d) or tax-year-behind data must
  be re-verified before use, per CLAUDE.md rule 7. Then skip to comps (property-search).
- **CACHE MISS** → `subject.skeleton.json` + `pull-sheet.md` + `run-log.md` written. Continue
  below. The run-log is the order's standard-work checklist: tools tick steps 1/3, you tick
  2/4 — unchecked boxes on finished orders surface in the weekly `/review` audit.
- **Both paths query the comp-history index (BD3):** a "Prior work" section (on the pull
  sheet, or `prior-work.md` on a hit) lists prior/similar VDV appraisals ≤12 mo as
  **candidates for YV** — open the listed `.dma` in DataMaster for that report's comp grid;
  re-verify every candidate comp's close date in the MLS.
- Unknown county → add it to `skills/property-search/references/county-registry.md`
  AND `tools/subject-resolution/county_routing.json` (same commit), then re-run.

## Step 2 — (Chesterfield/Hanover only, optional) ArcGIS auto-fill
```powershell
python tools/subject-resolution/fetch_arcgis.py "<address>" --county Chesterfield `
    --skeleton "<order-folder>\subject.skeleton.json"
```
Fills only what the FeatureServer proves; anything else stays null. On ANY failure it
prints a fallback note and touches nothing — just continue with the pull sheet.
Field maps are UNVERIFIED until the first live pull confirms attribute names.

## Step 3 — Run the pull sheet
Open `pull-sheet.md` — it has the SOR URL + technique + quirks, the full Source-1/2/3
checklist (county card → Zillow → gas), the MLS routing (incl. Navica both-accounts
warnings + surrounding-county sets). Fill `subject.skeleton.json` as you go; leave
unknowns null (the pipeline flags them — never guess).

## Step 4 — Ingest (normalize + gate + cache)
```powershell
python tools/subject-resolution/ingest_subject.py "<order-folder>\subject.skeleton.json" `
    --out "<order-folder>\subject.json" --source "<vendor> pull" --resolved-on <YYYY-MM-DD>
```
Gates fire loud (GLA, lot mismatch, tax year, county-vs-MLS GLA). Only valid output
reaches the cache — the next order on this subject becomes a Step-1 hit.

## Step 5 — Continue the standard chain
`/build-worksheet`: property-search comps → assemble_record.py → render_worksheet.py.
