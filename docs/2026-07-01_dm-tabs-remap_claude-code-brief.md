# Code brief — P3: DM-tabs remap + DM-complete worksheet fold (phased)

> Durable resume doc for a token/context-limited build. Each phase is committable; if a
> session resets, read this + `git log` to see where we are, then continue. Plan approved
> by Yuriy 2026-07-01.

## Progress tracker
- [ ] Phase 0 — persist this brief (in progress)
- [ ] Phase 1 — restructure CATALOG into 4 tabs (pure refactor, no field changes)
- [ ] Phase 2 — add Neighborhood section + Contract sub-block (new fields)
- [ ] Phase 3 — search-snapshot top block + parcel dimensions
- [ ] Phase 4 — seed field-map `aci_tab` + refresh deliverable + wrap (droppable)

## Context
`tools/dm-collection-sheet/build_collection_sheet.py` emits ONE flat "Subject" tab with 9
ad-hoc sections. DataMaster + the incoming ACI Sky Workbench (UAD 3.6, web) organize subject
data into four tabs — **Subject · Neighborhood · Site · Improvements** (+ a Contract sub-block).
Reorganize the worksheet to match: filled tab-by-tab with no hunting, and maps 1:1 onto the ACI
web form for next month's auto-fill. Gaps: **no Neighborhood section exists**, and the adopted
**search-snapshot + parcel-dimensions** block isn't in the template. PRIORITY-1 since 2026-06-15.

## Locked constraints
1. **Never rename a worksheet token.** `prefill_worksheet.py` fills these by `{{TOKEN}}`
   string-replace, tab-agnostic: `QUALITY CONDITION EFF_AGE EXT_WALLS ROOF WINDOWS GUTTERS
   FOUNDATION FLOORS WALLS_BATH BATH_FIN KITCHEN`. Regroup freely; keep ids stable.
2. **Generator = committed repo source.** HTML deliverable lives in CLIENT ZONE
   `…\VDV Appraisals\Operations\Template files\Subject-Worksheet_TEMPLATE_DM-complete.html`
   (NOT repo). Commit the `.py` each phase; regenerate-to-temp = per-phase check; refresh the
   Operations/ deliverable once at the end (Phase 4).
3. **`aci_web` stays `null`** (per `field-map/_model.md` — it's the real ACI selector, null
   until ACI live). Seed structural placement with a NEW `aci_tab` column instead.
4. Stdlib-only, deterministic. Verify by regenerate + prefill smoke test each phase.

## Target tab structure (URAR/DM order)
- **Subject** ← current "Identification" (Zoning moves out → Site) + NEW Contract sub-block
  (contract price · date · seller-is-owner-of-record · concessions $ + paid-by · financing type).
- **Neighborhood** ← NEW: Location (Urban/Suburban/Rural) · Built-up % · Growth · Property-values
  trend · Demand/Supply · Marketing time · Boundaries (N/S/E/W) · Present land-use %
  (1-unit/2-4/multi/commercial/other) · One-unit housing (price lo/hi/pred, age lo/hi/pred) ·
  Market conditions.
- **Site** ← current "Site" + Zoning (moved in) + Parcel dimensions (Phase 3).
- **Improvements** ← current General Description + Foundation/Basement + Exterior + Interior +
  Heating/Cooling + Amenities/Car Storage + Room-Count/Quality/Condition (h3 sub-groups in one tab).

Top tab bar → Subject · Neighborhood · Site · Improvements · Sale/Listing History · Comp Grid ·
Form-specific.

## Phases (edit → regenerate-to-temp → verify → commit)

**Phase 1 — restructure into 4 tabs (PURE REFACTOR).** `build_collection_sheet.py`: `CATALOG`
`[(section,[fields])]` → `[(tab,[(section,[fields])])]`; redistribute the 9 sections; empty
Neighborhood + Contract placeholders; Zoning → Site. `subject_tab_html()` emits 4 panels;
`build_html()` top bar gains the 4 tabs; `build_md()` groups by tab. Every field tuple + token
preserved. Verify (a) exit 0 (b) 12 tokens present (c) prefill fills (d) field count unchanged.
Commit `restructure DM collection sheet into 4 DM/ACI tabs (no field change)`.

**Phase 2 — Neighborhood + Contract fields (NEW).** Add tuples (label, NEW token e.g.
`NBHD_LOCATION`, `CONTRACT_PRICE`, dm_names best-effort via `dma_decode`—mark unverified, mismo
where known, src, gap=True, note). Verify. Commit `add Neighborhood section + Contract sub-block`.

**Phase 3 — snapshot + parcel dims.** `build_html()` top "search snapshot" block (GLA governing
at top, county-vs-MLS finished area, comp GLA ±10%, garage/carport, basement total+finished,
county + surrounding counties) + Parcel dimensions row in Site. New order-specific `{{TOKEN}}`s.
Verify. Commit `add search-snapshot block + parcel dimensions`.

**Phase 4 — field-map aci_tab + refresh + wrap (droppable).** `field-map.1004.yaml`: add
`aci_tab:` per subject-side row, keep `aci_web: null`; note column in `_model.md`. Regenerate the
Operations/ deliverable + MD reference. Update `worksheet-builder/SKILL.md` pointer + adopt/merge
note. Inbox [done] + `.claude/Session-Handoffs/` handoff + reply on `INBOX-for-Cowork.md`.
Commit `seed field-map aci_tab + refresh DM-complete template + docs`.

## Verify (PowerShell, temp only)
```
python tools\dm-collection-sheet\build_collection_sheet.py --html $env:TEMP\cs.html --md $env:TEMP\cs.md
python tools\dm-collection-sheet\prefill_worksheet.py --form 1004 --tier average --out $env:TEMP\pf.html
```
Pass = exit 0 · 12 prefill tokens present · prefill fills fields · no field dropped vs prior phase.

## Out of scope
Real `aci_web` selectors (ACI not live); adopt/merge decision (human); other forms' field-maps.
