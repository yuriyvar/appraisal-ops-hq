---
name: property-search
description: Verify a subject property and find/verify comparable sales using county assessment + GIS data, Zillow, and CVR MLS (Matrix). Use this whenever the user gives a subject property address and wants it verified, asks for comps, nearby sales, recent sales near an address, or wants GLA/floor-area cross-checked across sources. Also handles full DataMaster handoff — automated MLS# lookup, CSV generation to Comps files folder, and optional computer-use DataMaster import. Works for Virginia counties listed in references/va-data-sources.md. Triggers: "find sales near", "pull comps", "verify subject", "look up this property", an address plus a sale-date or GLA range, "build the DM file", "get comps into DataMaster".
---

# Property Search — Subject Verification + Comp Search + DataMaster Handoff

Cross-verifies a subject property, finds comparable sales, and delivers a
ready-to-import DataMaster CSV — or drives the full DM import via computer use.
Three data legs: **County (assessment + GIS)**, **Zillow**, **CVR MLS (Matrix)**.
Sources are never blindly trusted — every value is shown side by side and
conflicts are flagged.

## Inputs
1. **Subject address** (required). Determine county/independent city from it.
2. **Search radius** (ask every run — depends on the area; rural Hanover ≠
   suburban Mechanicsville). Do not assume.
3. **Sale window**: last 12 months. Fixed; do not shorten or extend unless told.
4. **GLA band**: subject GLA ±10% unless the user gives an explicit sf range.
   **Exception — luxury/large subjects (GLA > 5,000 sf):** widen to ±15% on the
   upper end; the best comps are often in the +10–15% zone.
5. **DM handoff mode**: ask once per run — "CSV only" (default) or "full DM
   import via computer use". Default to CSV; only switch to computer use when
   user explicitly asks or when they say "get it into DataMaster".

## Procedure

> **Routing (read first).** This skill has two concerns: (a) **subject
> verification** — always from the county assessment SOR (per-county, via the
> vendor adapter in `references/county-registry.md`) cross-checked with Zillow;
> and (b) **comp pull** — MLS-first (`references/matrix-comp-search.md`), with a
> county sales-GIS layer used only where the registry flags `Comp source =
> GIS+MLS`. Resolve the county in `references/county-registry.md` to pick the
> assessment adapter and the comp source BEFORE running the steps below.
>
> **Before pulling any data, skim `references/data-quirks.md`** — the registry of
> source oddities and required fixes (MLS `BRTVA→VA`, Chesterfield Dimensions GLA,
> ArcGIS TaxID rounding, Zillow new-construction parcel mismatch, builder-direct, …).
> When you hit a new quirk on a live order, ADD it there.

### 1. Resolve data sources
- **HARD RULE (BD1): no portal browsing, no MLS pull, before `/resolve-subject` has
  answered HIT or MISS.** Improvised pulls get provenance-flagged on the worksheet
  and caught by the weekly audit. Entry point for the whole order lane = `/appraise`.
- **Run `/resolve-subject` FIRST** (`tools/subject-resolution/resolve_subject.py`):
  a cache hit skips the portal pull entirely (re-verify its staleness flags); a miss
  hands you `pull-sheet.md` with the SOR/technique/gas/MLS routing pre-answered and a
  v1.1 `subject.skeleton.json` to fill. Ingest via `ingest_subject.py` when done —
  that's the only path into the subject cache.
- Look up the county in `references/va-data-sources.md` (assessment site, GIS
  site, known live REST endpoints, quirks).
- Check `references/data-quirks.md` for any source-specific exception that applies
  (county GIS gotchas, MLS-format fixes, portal mismatches) before trusting a value.
- **Reconcile with the source of truth when needed.** The master list lives in the
  Operational Records Google Sheet, tab "VA Counties Assessment & GIS Records"
  (doc `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`, gid `686822370`) — Yuriy adds
  counties there. Reconcile (fetch via the logged-in Chrome session:
  `/gviz/tq?tqx=out:csv&gid=686822370`, parse, diff against the local file) when:
  (a) the subject's county is missing from the local file, or (b) the file's
  "Last reconciled" date is more than ~2 weeks old.
- If the county is missing from BOTH: research it, use it for the run, add to
  the local file, offer to add to the sheet.

### 2. Verify the subject (all three legs)
- **County GIS/assessment**: parcel ID/GPIN/TaxID, property address, GLA, year
  built, beds/baths, lot size, zoning, last sale (date, price, deed). Prefer the
  GIS REST endpoint directly.
  - **New construction with no separate parcel**: if the address returns zero
    results from county GIS AND Matrix Tax Search, check whether the parcel is
    still under a builder/developer entity. Identify the nearest assessed
    neighbor unit to confirm GLA/specs. Flag to user: "subject has no Tax ID yet
    — DM file must be created manually by entering subject data before CSV
    import."
- **Zillow**: navigate to `zillow.com/homes/<Street-With-Dashes>-<City>,-VA-<zip>_rb/`
  in Chrome; extract living area, beds, baths, year built, last sold. Also run
  `document.body.innerText.match(/MLS ID #\d+/gi)` to capture all historical
  MLS IDs from the sale history stack — useful for finding resale MLS#s when
  the listing page only shows the original.
- **MLS (Matrix)**: drive `https://cvrmls.mlsmatrix.com/` in the user's Chrome
  session. Check for the "Working As" header confirming login; if the
  "User Identity Conflict" screen appears, warn user about the one-Matrix-session
  rule and wait — do NOT click Continue (it terminates Yuriy's active session).
  Use the shorthand search bar or SEARCH → Residential with the address. Pull
  GLA, beds, baths, year built, sale/list history, MLS#.
  **Never reuse saved `Results.aspx?c=...` links — session-bound.** Fresh search
  each time.
- Produce a subject verification table: one row per attribute, one column per
  source. Flag: GLA delta > 5% between any two sources, or any disagreement on
  year built / beds / baths / last sale.

### 3. Comp search
- Pull all sales in the last 12 months from the county sales data, filter to the
  user's radius from the subject parcel centroid (straight-line haversine on
  parcel centroids — state this in output).
  - **ArcGIS TaxID field**: if the county uses ArcGIS with TaxID as
    `esriFieldTypeDouble`, always apply `Math.round()` before string conversion
    to prevent floating-point digit corruption.
  - **UseCode filtering for Chesterfield** (and similarly structured counties):
    CD/CN = condo; TH/TN = townhouse fee-simple; SD = single-family detached.
    Apply `UseCode IN ('CD','CN')` for condo comps; `IN ('TH','TN')` for TH
    comps.
- Pre-filter by county GLA = target band **±100 sf margin**.
- Drop $0/$10/no-consideration transfers; report count dropped. Flag below-market
  prices as possible non-arm's-length.
- **Matrix RADIUS search** (when driving Matrix for comps): use the MAP tab
  radius search — it properly geocodes the address and returns a Distance column.
  Do NOT rely on the Criteria-tab map text field (Fm##_Ctrl7_TB) — it does not
  geocode from typed text and silently returns no radius constraint.
- Final candidate table: address, sale date, price, distance, county GLA, Zillow
  GLA, year built, flags. List borderline cases separately — never silently drop.

### 4. Automated MLS# lookup
After comp candidates are identified from GIS, automatically pull MLS numbers
before building the CSV. This eliminates the biggest manual step.

> **`BRTVA*` normalization:** an MLS# like `BRTVAMB2000092` is a Bright MLS listing
> shared into CVR MLS. Strip the `BRT` prefix → `VAMB2000092`. Use the `VA…` form for
> Bright MLS and DataMaster pulls (it's the canonical key); never feed DM the `BRT…` form.

**Step A — Zillow MLS# extraction (fast, no session conflict risk):**
For each candidate, navigate to the Zillow page and run:
```js
document.body.innerText.match(/MLS ID #\d+/gi)
```
This returns all MLS IDs from the sale history stack. Pick the one matching the
resale agent/brokerage (not the builder's original entry). Record result.

**Step B — Matrix address search (for candidates where Zillow has no MLS#):**
1. Check Matrix session: navigate to `cvrmls.mlsmatrix.com` and verify "Working
   As" header. If session conflict screen: STOP, warn user, wait for resolution.
2. For each remaining candidate: type the street address into the shorthand bar.
   Pull: MLS#, list price, sale price, DOM, contract date, above/below grade GLA.
3. If Matrix Tax Search is needed: use the PID/TaxID to cross-reference.

**Builder/off-MLS sales:** If neither Zillow nor Matrix returns an MLS# (Zillow
shows "Source: [Builder Name]" with no MLS ID), flag the comp as
`BUILDER-DIRECT` in the notes column. DataMaster will attempt to use PID only;
if DM cannot pull the comp, it must be entered manually in ACI.

**Do not** bulk-search all 60+ candidates — only search the shortlisted
candidates (typically 8–12) that survived the GLA/distance filter.

### 5. Build and save the DataMaster CSV
After comp set is confirmed by appraiser:

1. Build the **"Appraiser Single Line"** CSV using the exact headers from
   `references/datamaster-handoff.md`. Fill all available fields from GIS +
   Zillow + Matrix. For fields unavailable without a full Matrix pull (Area code,
   Original List Price, DOM), leave blank — DataMaster re-pulls these.
2. Save to: `C:\Users\yuriy\VDV Appraisals\Comps files\<address>_comps_appraiser-single-line.csv`
   (e.g. `14640-Hancock-Towns-Dr_comps_appraiser-single-line.csv`).
   **Never save to the repo** — client/order data stays out of appraisal-ops-hq.
3. Present the file to the user via `mcp__cowork__present_files`.
4. Flag in chat: any comps with blank MLS# (builder-direct), any GLA deltas >5%
   that need Matrix verification before DM import.

### 6. DataMaster import via computer use (optional — when user requests)
When the user asks to "get it into DataMaster" or requests computer use:

1. **Request access**: call `mcp__computer-use__request_access` for DataMaster.
2. **Open DataMaster**: use the shortcut at
   `C:\Users\yuriy\VDV Appraisals\DataMaster - Shortcut.lnk`.
3. **Subject setup**:
   - For normal orders (known APN/parcel): create a new order; enter subject
     address; DataMaster pulls subject data from CoreLogic automatically.
   - **For new construction without APN**: DM cannot pull subject data — warn
     the user and ask them to enter the subject manually in DM before proceeding
     to the import step.
4. **Import comps**: File → Import → Appraiser Single Line → select the CSV from
   `Comps files\`. Confirm the import dialog.
5. **Verify import**: screenshot the DM grid; confirm all 6 comps loaded. Report
   any errors (missing data, MLS# not found) back to user.
6. **Never write `.dma` files directly.** Only DataMaster creates/edits them.
7. Hand off: ask user to do final review in DM and click "Review & Send" to ACI.

### 7. Output & hygiene
- Per CLAUDE.md rule 2: append any data-source quirk discovered during the run
  to `vault/00-inbox.md`.
- If a source in the reference table is broken/moved and it blocks a real order:
  file an andon. Otherwise fix the table and log to inbox.
- Distances are centroid-to-centroid straight-line; state this.
- Do not solve CAPTCHAs; if Zillow blocks, continue with other legs.
- Matrix is the user's licensed account: read data for their appraisal work only,
  never bulk-scrape, never act in Matrix beyond running searches.

## Technique: county GIS via ArcGIS REST (CivQuest/ArcGIS adapter only)
> Applies to counties whose registry row marks an ArcGIS/CivQuest sales layer.
> For Vision/actdatascout/MLS-only counties use the matching adapter instead.

1. Open the county parcel map in Chrome; run
   `performance.getEntriesByType('resource')` filtered for `rest/services` to
   find the live FeatureServer the app queries.
2. **Beware stale public mirrors**: prefer the endpoint the live app actually
   calls. (Hanover: live = `maps.civ.quest/.../Hanover/Public/FeatureServer`;
   AGO mirror is months stale.)
3. Inspect layer schemas (`?f=json`) — find Parcels (geometry), Sales,
   Improvements/Summary (GLA).
4. Query pipeline (run as JS `(async()=>{...})()` in Chrome tab):
   subject centroid → spatial query (point + distance in metres) → haversine
   distance filter → GLA/UseCode/SaleDate filter → batch Zillow + Matrix MLS#
   lookup on shortlist.
5. **TaxID as Double**: `Math.round(a.TaxID)` before `.toString()`.
6. Record every endpoint discovery in `references/va-data-sources.md`.

## Technique: Navica comp pull (Navica-market adapter)
> Applies when `references/county-registry.md` routes the market to **Navica** (Lake Country /
> Southside markets — e.g. Prince Edward, Mecklenburg/Kerr Lake). Matrix steps above do NOT apply.

1. **Resolve the account(s) first** in `references/navica-accounts.md` — some counties (Mecklenburg)
   require searching **TWO accounts** (South Central 287 + Southern Piedmont 397); comps split across
   them. ⚠️ **MLS# namespaces are SEPARATE per account** — the same numeric ID is a *different listing*
   in each; always search a MLS# inside its own account. Credentials/how-to:
   `Operations/Navica MLS basics.docx` (never store creds in the repo).
2. **MLS# search = POST via `MlsNosForm`** (the GET quick search `searchValRC` → 500; direct
   `/Listing/Detail/{id}` URLs → 500 — use neither):
   navigate `next.navicamls.net/<acct>/Search/Index?accountNo=<acct>`, fill `input[name="mlsNo"]`
   fields (numeric only — no `R` prefix / `C` suffix), submit `#MlsNosForm` → results at
   `/<acct>/Search/MlsListToResults`.
3. **Criteria search:** Search → Residential; Status = Active + Pending + Closed; location BROAD
   (rural comps cross county lines — use the surrounding-county set from `county-registry.md`);
   Closing Date 6–12 mo; sort Distance + Close Date. Don't over-filter.
4. **Listing detail:** click the listing photo/row (TR) in results → `/<acct>/Expanded/Single`;
   set layout **Traditional** (shows all fields). **No CSV export exists** — read fields off the
   detail page and extract the FULL per-comp checklist in `references/navica-accounts.md`
   ("Per-comp data to extract"): rooms/beds/baths, pending date, house type, heating/cooling,
   porch/deck/patio, basement finish, garage/carport, financing + seller concessions, GLA
   (**Est Total Htd SqFt**), parcel ID, etc. Fields absent from the summary live in the
   remarks/photos — mark `⚠ confirm`, never guess.
5. **DataMaster CSV is built BY HAND** for Navica comps — match the "Appraiser Single Line"
   headers in `references/datamaster-handoff.md` exactly; save to `Comps files\` as usual.

## Rules
- Never present a single-source GLA as verified. Verified = two+ sources agree
  within 5%, or the user has chosen which source governs.
- Distances are centroid-to-centroid straight-line; always state this.
- One Matrix session at a time. Never click "Continue" on the Identity Conflict
  screen without explicit user permission — it terminates their active session.
- Builder-direct sales (no MLS#) are valid comps but require manual ACI entry if
  DataMaster cannot pull them by PID.
