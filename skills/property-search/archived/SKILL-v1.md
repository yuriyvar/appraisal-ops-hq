---
name: property-search
archived: true
archived-date: 2026-06-13
superseded-by: ../SKILL.md (v2 — automated MLS# lookup + DM computer-use import)
description: Verify a subject property and find/verify comparable sales using county assessment + GIS data, Zillow, and CVR MLS (Matrix). Use this whenever the user gives a subject property address and wants it verified, asks for comps, nearby sales, recent sales near an address, or wants GLA/floor-area cross-checked across sources. Works for Virginia counties listed in references/va-data-sources.md. Triggers: "find sales near", "pull comps", "verify subject", "look up this property", an address plus a sale-date or GLA range.
---

# Property Search — Subject Verification + Comp Search

Cross-verifies a subject property and finds comparable sales. Three data legs:
**County (assessment + GIS)**, **Zillow**, **CVR MLS (Matrix)**. Sources are never
blindly trusted — every value is shown side by side and conflicts are flagged.

## Inputs
1. **Subject address** (required). Determine county/independent city from it.
2. **Search radius** (ask every run — depends on the area; rural Hanover ≠ suburban
   Mechanicsville). Do not assume.
3. **Sale window**: last 12 months. Fixed; do not shorten or extend unless told.
4. **GLA band**: subject GLA ±10% unless the user gives an explicit sf range.

## Procedure

> **Routing (read first).** This skill has two concerns: (a) **subject
> verification** — always from the county assessment SOR (per-county, via the
> vendor adapter in `references/county-registry.md`) cross-checked with Zillow;
> and (b) **comp pull** — MLS-first (`references/matrix-comp-search.md`), with a
> county sales-GIS layer used only where the registry flags `Comp source =
> GIS+MLS`. Resolve the county in `references/county-registry.md` to pick the
> assessment adapter and the comp source BEFORE running the steps below. The
> ArcGIS-REST technique near the end is just ONE adapter (CivQuest/ArcGIS family),
> not the default for every county (e.g. Henrico has no usable sales layer -> MLS).

### 1. Resolve data sources
- Look up the county in `references/va-data-sources.md` (assessment site, GIS site,
  known live REST endpoints, quirks).
- **Reconcile with the source of truth when needed.** The master list lives in the
  Operational Records Google Sheet, tab "VA Counties Assessment & GIS Records"
  (doc `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`, gid `686822370`) — Yuriy adds counties
  there. Reconcile (fetch via the logged-in Chrome session:
  `/gviz/tq?tqx=out:csv&gid=686822370`, parse, diff against the local file) when:
  (a) the subject's county is missing from the local file, or (b) the file's
  "Last reconciled" date is more than ~2 weeks old. Update the local file with any
  new/changed rows and bump the date.
- If the county is missing from BOTH the file and the sheet: research the county's
  assessment + GIS sites yourself, use them for the run, add them to the local
  file, and offer to add them to the sheet tab (ask before writing to the sheet).

### 2. Verify the subject (all three legs)
- **County GIS/assessment**: parcel ID/GPIN, property address, GLA, year built,
  beds/baths, lot size, zoning, last sale (date, price, deed). Prefer querying the
  GIS REST endpoint directly (see Technique below) over clicking through the map UI.
- **Zillow**: navigate to `zillow.com/homes/<Street-With-Dashes>-<City>,-VA-<zip>_rb/`
  in Chrome; extract living area from page HTML (`livingArea":NNNN` pattern), beds,
  baths, year built, last sold.
- **MLS (Matrix)**: drive `https://cvrmls.mlsmatrix.com/` in the user's Chrome
  session (user must be logged in — check for the "Working As" header; if not
  logged in, ask the user to log in first). Use the shorthand search bar ("Enter
  Shorthand or MLS#") or SEARCH → Residential with the address. Pull GLA, beds,
  baths, year built, sale/list history, MLS#.
  **Never reuse saved Matrix `Results.aspx?c=...` links — they are session-bound
  and return "URL is Invalid" in a new session.** Run a fresh search each time.
- Produce a subject verification table: one row per attribute, one column per
  source. Flag: GLA delta > 5% between any two sources, or any disagreement on
  year built / beds / baths / last sale.

### 3. Comp search
- Pull all sales in the last 12 months from the county sales data, filter to the
  user's radius from the subject parcel centroid (straight-line, haversine on
  parcel centroids — say so in the output).
- Pre-filter by county GLA = target band **±100 sf margin** (county and Zillow
  GLA frequently diverge; Zillow often counts finished basement — e.g. Hanover
  comp 14995 Patrick Meadows: county 3,387 vs Zillow 5,635).
- Drop $0 / no-consideration transfers but report how many were dropped. Keep
  sale-status codes visible; flag below-market prices as possible
  non-arm's-length (verify deed before using).
- Verify each surviving candidate on Zillow (and MLS when the user wants
  listing-level data: DOM, concessions, condition, photos).
- Final table: address, sale date, price, distance, county GLA, Zillow GLA,
  MLS GLA (if pulled), year built, flags. List borderline cases (just outside
  the band on one source, inside on another) separately — never silently drop.

### 4. DataMaster handoff (when the user wants the comps in DataMaster/ACI)
Follow `references/datamaster-handoff.md`: after the appraiser confirms the comp
set, export "Appraiser Single Line" (sales) and "Agent Single Line" (actives)
CSVs from Matrix into the order's job folder, then the CSVs are imported into
DataMaster (which builds the `.dma` and feeds ACI). Never write `.dma` files
directly. When reviewing inside DataMaster, use the skill's verification table
to resolve MLS-vs-public-records field conflicts.

### 5. Output & hygiene
- Results table in chat; offer CSV/XLSX. Save any files to the **client job
  folder** (`C:\Users\yuriy\VDV Appraisals\<job>`), NEVER into this repo
  (cardinal rule: no client/order data in appraisal-ops-hq).
- Per CLAUDE.md rule 2: append any data-source quirk discovered during the run
  (stale mirror, endpoint change, field rename) to `vault/00-inbox.md`.
- If a source in the reference table is broken/moved, that is an andon-worthy
  event if it blocks a real order; otherwise fix the table and log to inbox.

## Technique: county GIS via ArcGIS REST (CivQuest/ArcGIS adapter only)
> Applies to counties whose registry row marks an ArcGIS/CivQuest sales
> layer. For APEX/Vision/actdatascout/MLS-only counties, use the matching
> adapter in `references/county-registry.md` instead.
Most VA county parcel viewers are ArcGIS apps. The fast, reliable path:
1. Open the county parcel map in Chrome; run
   `performance.getEntriesByType('resource')` filtered for `rest/services` to find
   the real FeatureServer/MapServer the app queries.
2. **Beware stale public mirrors**: prefer the endpoint the live app actually
   calls. (Hanover: live = `maps.civ.quest/.../Hanover/Public/FeatureServer`;
   the AGO-hosted "HanoverCivQuest" mirror is months stale.)
3. Inspect layer/table schemas (`?f=json`) — find Parcels (geometry), Sales,
   Improvements/Summary (GLA). Field types vary: SALEDATE may be a date type or
   an ISO string; ISO strings compare correctly with `>=` in SQL where clauses.
4. Query pipeline (run as JS in the browser tab or via web_fetch):
   subject centroid → sales where SALEDATE >= cutoff (paginate at maxRecordCount)
   → batch parcel centroids by GPIN (`IN` chunks of ~80) → haversine distance
   filter → batch GLA lookup from Improvements.
5. Record every endpoint discovery in `references/va-data-sources.md`.

## Rules
- Never present a single-source GLA as verified. Verified = two+ sources agree
  within 5%, or the user has chosen which source governs.
- Distances are centroid-to-centroid straight-line; state this.
- Do not solve CAPTCHAs; if Zillow blocks, report and continue with other legs.
- Matrix is the user's licensed account: read data for their appraisal work only,
  never bulk-scrape, never act in Matrix beyond running searches.
