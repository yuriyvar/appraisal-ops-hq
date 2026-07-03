---
name: worksheet-builder
description: Build the tabbed HTML copy-paste worksheet that helps Yuriy fill out a DataMaster / ACI report from gathered order data. Use whenever Yuriy says "build the worksheet", "make the DM worksheet", "/build-worksheet", "copy-paste worksheet", "worksheet for <address>", "assemble the record and render it", or wants the Subject / Comp-grid / Sale-history / Photos / Map worksheet for an order. Renders `appraisal-record.json` → `worksheet.html` via tools/worksheet-renderer, AFTER passing the comp-quality completeness gate (so previously-seen comp-data gaps never ship again). The appraiser reviews, adjusts, and certifies — this assembles + renders, never submits.
---

# Worksheet Builder

> **Runtime: COWORK (COWORK_AGENT).** This is the interactive path — COWORK_AGENT gathers data, asks Yuriy
> for approvals (e.g. Photos/Map), hand-assembles the record when the assembler isn't available,
> and renders. The **automated** equivalent for **Claude Code** is the `/build-worksheet` command
> (`.claude/commands/build-worksheet.md`). Same deliverable + same completeness gate; two front doors.

> **Triage / prep scope follows `vault/20-standard-work/SOP-triage.md`** — prep ALL in-scope WIP
> (View A, assignee-blind; Alan's orders included, never skipped at prep). One rule, both lanes.

Produces the **tabbed HTML copy-paste worksheet** that Yuriy pastes into
DataMaster / ACI. **Default tabs: Subject · Neighborhood · Comp grid ·
Sale/Listing history, plus the search-snapshot strip above the tabs** (adopted
standard; renderer emits it automatically since 2026-07-02 — no hand-merge).
**Photos and Map are OPTIONAL — include them only with Yuriy's explicit approval**
(ask before adding; omit by default). COWORK_AGENT ASSEMBLES the data and RENDERS it; the
licensed appraiser judges adjustments and certifies. **Never submit.**

Inputs → output: `appraisal-record.json` (per `appraisal-record.schema.json`)
→ `worksheet.html` via `tools/worksheet-renderer/render_worksheet.py`.

## Subject data pull checklist (pull ALL fields in one pass — not iteratively)

Learned from 3355 Darbytown Rd: pulling a subset and then adding fields on request wastes
rounds. Run this checklist in full before declaring subject data complete.
> **Start with `/resolve-subject`** — a cache hit skips this checklist entirely (re-verify its
> staleness flags); a miss prints this checklist as a per-order `pull-sheet.md` with the county's
> SOR URL/technique + gas answer baked in, and gives you the v1.1 skeleton to fill.
> **HARD RULE (BD1): no portal browsing before the resolver answers HIT/MISS, and subject.json
> comes from `ingest_subject.py` only** — hand-rolled ones get a "produced outside standard work"
> chip on the worksheet header. Tick your run-log boxes (steps 2 & 4) as you go.

### Source 1 — County assessment portal (SOR)
Pull in a single session; record every field even if blank (blank is data):
- **Identification:** GPIN, PID, Subdivision, Section/Block/Lot, Zoning
- **Legal description:** from parcel detail (needed for DM Subject tab)
- **Lot:** Acreage *(often blank in Henrico APEX → go to Zillow immediately; don't leave blank)*
- **Improvements:** Style, # Stories, Year Built, Total Rooms, Bedrooms, Full Baths, Half Baths
- **Above-grade GLA** (county SOR governs — note if it conflicts with MLS)
- **Exterior:** Ext Walls code, Roof type
- **Foundation:** Foundation Type *(note: type only — material requires inspection)*
- **Mechanical:** Heating code, AC code, Fireplace count
- **Sketch codes:** read every code — WDK=deck, PCO/PCU=covered porch, OP=open porch,
  GR1/GR2=garage, WS=workshop; record sf for each

### Source 2 — Zillow (supplement + cross-check)
Pull immediately after APEX — don't wait to be asked:
- **Lot size** — always check; fill in when APEX acreage is blank
- **Legal description** — often in listing details if APEX parcel page doesn't show it
- **Photos** — scan the listing photo set for:
  - Floor material (living/dining shots → hardwood, carpet, tile, LVP)
  - Fireplace presence + surround style (living room photo)
  - Front porch type (exterior shot #1: stoop only vs. covered porch)
  - Rear deck/patio (rear exterior shot)
  - Garage (exterior or interior shots)
  *(Flag all photo-derived items as "Zillow — confirm at inspection")*

### Source 3 — Gas utility availability
Check gas availability BEFORE inferring/flagging heating fuel — a "forced air" subject is only a
gas furnace if gas actually reaches the parcel (learned on 1214 Hillside Ave).
- **Find the provider + lookup tool by county** — query the reference DB
  `references/va-gas-providers.sqlite` (the source of truth; **do not hardcode URLs here**):
  ```sql
  SELECT p.provider_name, p.lookup_method, p.lookup_url, p.lookup_notes, p.phone
  FROM va_gas_providers p
  JOIN va_gas_provider_counties c ON c.provider_id = p.id
  WHERE c.county_city = '<Jurisdiction>';   -- e.g. 'Henrico County'
  ```
  (Rebuild with `references/build_va_gas_providers.py` if it ever needs updating.)
- **`lookup_method` tells you how definitive the check is:** `instant_map` (ArcGIS, seconds) ·
  `zip_checker` (instant ZIP yes/no) · `map_only` / `form_callback` / `phone_only` (no instant
  address-level answer → note "gas availability unknown — confirm at inspection").
- **Henrico / Richmond City / N. Chesterfield → Richmond Gas Works** (`instant_map`): from the DB's
  `lookup_url`, search the address → click the **street/parcel area (NOT the result pin)** → read the
  popup. Three outcomes:
  - "Natural gas is available" → gas connected; heating fuel likely **gas**.
  - "…can be brought to it" → gas NOT currently connected → heating fuel is **NOT gas** (heat pump / oil / electric — confirm at inspection).
  - No result / outside boundary → outside service area; no gas.
- **If two providers return** (overlap county — Chesterfield, Frederick, Warren, Rockingham, Clarke):
  present both and note the overlap.
- **No provider row** → note "gas provider unknown — confirm at inspection."
Record the result in the subject's Utilities row — **Gas: Connected / Available-not-connected /
Not available** — and adjust the heating-fuel inference accordingly.

### DM-specific field rules (apply when building the worksheet)
- **Assessor's Parcel #** — this is DM's canonical label for APN / Tax ID / Map#. Use it in the worksheet; never label the field "PID / APN / Tax ID" (confusing). One-time clarifier `(= APN / Tax ID)` is OK on first use.
- **Map Reference** — enter `GIS` when the source doesn't supply a specific map reference. Never leave blank.
- **HOA $ / period** — pull from MLS listing remarks or HOA disclosure docs. Always include amount + frequency (monthly/annually). If not found, flag `TBD — get from HOA docs`; never leave silently blank.
- **RE Taxes $** — pull the actual annual tax bill (not the assessed value). actDataScout and similar portals usually show it; so does the MLS. Tax year must match the tax bill year shown.
- **Census Tract** — DM often imports this from its own data. Mark `TBD — FFIEC geocoder` only if DM didn't fill it; check DM's import first before marking TBD.

### What is NEVER in APEX — always flag for inspection
- Foundation wall material (APEX records type only, e.g. Crawl, Basement)
- Interior finishes (floors in rooms not visible in photos, bath tile, countertops)
- Cooling type (sometimes present as AC code; if blank, confirm at inspection)
- Condition / effective age (appraiser judgment)

### Output before moving to comps
Present the full subject profile in DM 1004 field order (Subject → Site → Improvements →
Foundation → Exterior → Interior → HVAC → Amenities → Garage) with every field either
populated or explicitly flagged `⚠️ confirm at inspection` or `⚠️ not in APEX`. No silent blanks.
The **Site → Utilities** row (Electricity · **Gas** · Water · Sewer) is required — set **Gas** per
Source 3 (`Connected` / `Available-not-connected` / `Not available`); never leave Gas blank.

---

## Workflow
1. **Gather / locate the record.** If an `appraisal-record.json` exists for the order, use it.
   Otherwise run the **Subject data pull checklist above** (APEX → Zillow in one pass), then
   gather comps via `skills/property-search`, and assemble the record.
2. **Apply data-quirks normalizations** from `skills/property-search/references/data-quirks.md`
   (e.g. MLS `BRTVA→VA`, Chesterfield TaxID rounding). Don't render un-normalized values.
3. **Run the COMPLETENESS GATE below — do not render until it passes.**
4. **Render:** `python tools/worksheet-renderer/render_worksheet.py <record.json> -o <order>/worksheet.html`.
   Default tabs = Subject · Neighborhood · Comp grid · Sale/Listing history + the search-snapshot
   strip (all automatic from the record — populate `subject.neighborhood_bounds`,
   `neighborhood_description_context`, `water/sewer`, `re_taxes_annual`, `hoa_amount/period` and
   `market.search.surrounding_counties` in subject.json to pre-fill them; anything absent renders
   TBD/dash, never guessed). **Photos and Map are OFF by default**
   — add `--with-photos` / `--with-map` ONLY after Yuriy explicitly approves including them.
5. **Self-check the output** (tabs populated, flags surfaced, review gate shows NOT CERTIFIED),
   then hand the worksheet to the appraiser to review / adjust / certify.

## ✅ Completeness gate (hard-won comp-quality lessons — never ship these missing)
Block rendering and fix/flag first if any fails:
- **Comp count:** ≥ **3 CLOSED** comps (regulatory minimum); target **3–5**. Present the best
  closed sales, not the whole GLA band.
- **Segregate status:** CLOSED sales are the comps; **Active/Pending are listing analysis only** —
  never let an Active masquerade as a sold comp.
- **County-tag every comp.** Comps in a neighboring VA county are OK but MUST be (a) labeled with
  their county and (b) **verified against THAT county's SOR** (out-of-county comps often arrive with
  missing/unverified GLA — see data-quirks XCO-001).
- **Never emit unverified GLA.** If above-grade GLA is missing/unconfirmed (common on out-of-county
  MLS rows), set it null and add a `flags` entry — do NOT guess or leave it silently blank.
- **Flag superiority/inferiority:** water-view / waterfront / location-superior comps are NOT directly
  comparable to a non-view subject — flag and set aside (don't bury them in the grid).
- **Form-specific required fields:** check the `references/field-map/field-map.<form>.yaml` for the
  order's form and confirm its required fields are present (e.g. **1073 Project Information** — unit
  counts, roof, parking; **1004C** — HUD data plate / manufacturer). Missing → flag, don't omit silently.
- **Per-comp ML# + Tax ID/PID (DataMaster needs both):** every comp carries its **ML#** *and*
  **Tax ID / PID** — the assembler flags either if missing; the renderer gate (`audit_comp_tax_ids`)
  fails the build if a captured Tax ID doesn't actually render. Also carry prior **3-yr sale** history
  (1004), **DOM / contract date**, and the **above/below-grade GLA split** — flag, never silently blank.
- **12-month sales window:** primary CLOSED comps sell **within 12 months** of the effective date.
  Older same-project / same-market sales are **supplemental only, with an explicit dated-sale
  justification — never primary, never unlabeled** (andon 2026-06-26: The Moorings mixed 2023–24
  sales). The assembler **hard-flags** a closed comp only when a captured `sale_date` is genuinely
  >12 mo old; a *missing* date (the single-line CSV never carries one) gets an `INFO:` note —
  "capture the close date" — not a gate (demoted 2026-07-02; a hard flag on every comp was noise).
- **Comp-selection rubric (YV) — any criterion out of band → HIGHLIGHT and let YV decide, never
  silently drop or include:**
  - Above-grade **GLA ±10%** (assembler auto-flags; luxury > 5,000 sf widens to ±15%, see below).
  - **Distance tiers** — Rural: 1, 3, 5, 7, 10, 12 mi (start tight, expand outward only as needed);
    Urban: 0.25, 0.5, 1, 1.5 mi; Suburban: urban tiers up to 3 mi.
  - **Parcel / lot area ±20–30%.**
  - **Sold-price variation 3–15%.**
  - Distance is **not** definitive — weight sale price + prior sale + condition/DOM, not proximity alone.
- **GLA-band sanity:** luxury/large subjects (GLA > 5,000 sf) use the **±15%** band (per `property-search`);
  cross-check a radius pull so the band didn't drop an obviously-superior **same-subdivision** comp.
- **Review gate:** record's `review.human_reviewed=false` and `adjustments` left to the appraiser.

## Rules
- Assemble + render only; **never submit or certify** (USPAP — appraiser is the gate).
- Deterministic renderer (stdlib, no network) — same record → same worksheet.
- Outputs go to the order folder under `VDV Appraisals\`, **never the repo** (client data).
- New data-source gotcha encountered while building → add it to `data-quirks.md` proactively.

## Condition profiles (default Improvements values by tier)
To fill the Improvements section + comp Quality/Condition fast, pull defaults from
`references/condition-profiles/condition-profiles.<form>.yaml` (forms: 1004, 2055,
gpar, 1073) for the matching tier — **new · average · fair**. UAD forms use Q/C codes
+ `material/rating` (e.g. `Q3`, `C3`, `Drywall/Avg`); gPAR uses words (Good/Average/Fair).
**Average + new are grounded in past VDV reports; fair (and all of 1073) are
extrapolated** (`observed_in_corpus: false`) — paste as a scaffold, then EDIT to the
real property and itemize C5 deficiencies. The profile saves typing, not judgment.
See `references/condition-profiles/_model.md`.

**Pick a tier → pre-fill the worksheet** (automated): generates the worksheet with the
tier's Improvements + Q/C defaults already in place (amber = default, verify & edit):
```powershell
python tools/dm-collection-sheet/prefill_worksheet.py --form 1004 --tier average `
    --out "C:\Users\yuriy\VDV Appraisals\<order>\<addr>_worksheet.html"
```
Order-specific tokens ({{ADDRESS}}, IDs) stay blank for you to fill. The banner flags
whether the tier is grounded or extrapolated.

## Related
- Renderer + contract: `tools/worksheet-renderer/` (+ README). Mapping: `references/field-map/`.
- Condition defaults: `references/condition-profiles/` (per-form × new/average/fair).
- DM collection sheet: `tools/dm-collection-sheet/build_collection_sheet.py` builds the blank worksheet now in the **4 DM/ACI tabs** (Subject +Contract · Neighborhood · Site +parcel dims · Improvements) with a top **search-snapshot** block; regenerate `Operations/Template files/…_DM-complete.html` from it (76 fields), tier pre-fill via `prefill_worksheet.py`.
- Narrative + adjustment hints: `skills/notes-composer`. Full automation: the `/build-worksheet`
  orchestrator (see `docs/2026-06-13_build-B-assembler-orchestrator_claude-code-brief.md`).
