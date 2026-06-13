# VDV automation — session summary & action plan (for Alan)
*2026-06-13 · prepared by Yuriy + Claude ("Bob") · drafted on branch kaizen/K-002*

## 1. What we did
Ran a full property search on **119 Countryside Ln, Henrico 23229** as a live
test of the `property-search` skill, end to end: subject verification, comp
search, and a DataMaster-ready CSV.

## 2. Findings on the test order
- **Subject verified across three sources** — Henrico assessment, Zillow, and the
  CVR MLS listing all agree: **6,662 sf GLA, built 2002, 5 BR / 5 full + 2 half,
  Grade AAA, pool + pool house**, ~0.5 ac, zoned R-2. Last transfer 06/01/2022
  was $0 (intra-family, non-qualified); last arm's-length sale 2005 @ $999K;
  currently listed $2.5M, **Pending**. 2026 assessment $2,240,300.
- **Comp market is thin and the subject tops it.** Of the 45 homes within 1 mile
  (Alan's radius search), ~37 are 2,600–5,200 sf selling $1.0–1.8M — a smaller,
  cheaper product than the subject.
- **Recommended closed comps:** 8721 Ruggles Rd (0.6 mi, 7,560 sf, **$3.10M**,
  same Countryside subdivision — best comp), 200 Westham Pkwy (0.8 mi, 6,279 sf,
  $2.345M, sold over list), 7007 Lakewood Dr (1.08 mi, 7,280 sf, $2.80M).
  Support: 403 Berwickshire (active $2.285M), 8705 Raleigh Manor (pending $1.899M).
- **Deliverables produced:** `2026-06-13_119-Countryside-Ln\119-Countryside-Ln_comp-search_2026-06-13.xlsx`
  (Subject / Recommended comps / Alan's 45 / Notes) and a DataMaster CSV in
  `Comps files\`.

## 3. Lessons captured (now in the vault)
- Henrico = **assessment site, not GIS** (the county open-data parcel layer is a
  735-record sample; unusable for comps).
- Matrix **map-radius** search is the reliable radius method; the criteria-tab
  address field does not geocode.
- CVR Matrix allows **one concurrent session per login** — parallel jobs collide.
- **Widen the GLA band (~+15%) for luxury subjects** — ±10% dropped the best comp.
- DataMaster CSVs now live in `C:\Users\yuriy\VDV Appraisals\Comps files\`.

## 4. Readiness for an unattended agent (latest Sonnet)
The model is capable; the **build** has one weak link.
- **Subject extraction:** ~80% — reliable once per-county assessment quirks are in
  the registry.
- **CSV for DataMaster:** good — format is exact; just keep ML#/PID.
- **Comp pull:** **not production-ready** — no documented MLS procedure, so the
  agent re-derives Matrix's brittle bits each run. This is the thing to harden.

## 5. Architecture decision (ADR-002)
- Split into **subject-verification** (county assessment SOR, per-vendor adapter,
  + Zillow) and **comp-pull** (MLS-first: Matrix + Navica; county sales-GIS only
  where it exists).
- **Adapters by vendor family**, not per county (~8 families cover the state).
- **Promote the county sheet to a routing registry** with Sales-GIS? / Comp-source
  columns. Build coverage **by order volume** (Richmond metro first).
- **MLS is the backbone** regardless of GIS — only the MLS has DOM, concessions,
  condition, list-vs-sold, prior-listing chain.

## 6. The bigger goal — final-output assembly
Two viable end states (not mutually exclusive):
- **A. HTML tabbed worksheet (near-term):** a DataMaster-style HTML file with tabs
  (Subject · Comps grid · Listing history · Photos · Map) that Alan or an
  apprentice copy-pastes into ACI. Fast to build, no ACI integration risk.
- **B. Direct ACI ingestion (stretch):** emit a format ACI imports (research
  needed — ACI/MISMO; DataMaster already bridges Matrix→ACI today, so the
  pragmatic path may be "feed DataMaster" rather than write ACI directly).
- **Photos pipeline (both):** intake → auto-label (subject front/rear/street,
  per-comp, interior rooms) → rename to ACI/report convention → place in job
  folder / the HTML Photos tab. Needs a labeling step (filename or light vision).

## 7. Action plan (phased)
**Phase 0 — Decide (this session).** ADR-002 + K-002 kaizen branch drafted;
GitHub remote prep. *Alan: review & merge K-002.*
**Phase 1 — Registry + skill routing.** Merge the two-module/adapter restructure;
finish metro-county registry rows; reconcile new columns into the Google Sheet.
**Phase 2 — Harden comp-pull.** Turn `matrix-comp-search.md` into tested standard
work; build the **Navica** adapter; evaluate a Matrix/Navica **exporter or broker
session** so comps don't depend on DOM scraping.
**Phase 3 — Output assembly.** Build the **HTML tabbed worksheet** generator
(Subject + comp grid + history + map) for copy-paste into ACI.
**Phase 4 — Photos.** Intake → label → rename → place; wire into the HTML Photos
tab.
**Phase 5 — ACI ingestion (stretch).** Research ACI import; decide direct-ingest
vs DataMaster bridge; pilot on one order.

## 8. Open questions for Alan
1. Output preference: HTML-tabbed copy-paste (A) first, or push toward ACI/MISMO
   direct ingestion (B)?
2. Is DataMaster the intended bridge to ACI long-term, or do we want to bypass it?
3. Navica priority — which boards/counties is it our SOR for?
4. For luxury subjects, confirm default policy: widen GLA to +15% and bracket up?
5. Photo labeling — filename convention you want ACI to consume?

---

## 9. Plan update — 2026-06-13b (Yuriy additions)

**Scope changes**
- **Public leg is multi-portal:** Zillow + Realtor.com + Redfin + Homes.com (+future), adapter-based.
- **Three MLSs now:** CVR (Matrix), Bright (Matrix), Navica — more expected. CVR+Bright share one
  parameterized Matrix adapter; Navica needs its own. Comp-pull stays MLS-agnostic.
- **Registry storage:** recommend a **hybrid** — keep the human SOR as the Google Sheet / in-repo
  CSV (editable, git-diffable, PR-reviewable), **derive SQLite** for fast queries, and use **SQLite
  as the resolution cache**. Not SQLite-as-SOR (binary breaks PR review + casual editing).
- **Subject resolution / no-Tax-ID brute-force** is now an explicit, documented sub-process
  (`references/subject-resolution.md`) with a SQLite cache so we never brute-force the same
  property twice. Directly streamlines a recurring pain.
- **ACI going fully web-based:** plan for **browser auto-fill** from one structured appraisal
  record via a swappable field-map (human-reviewed, no auto-submit). Web entry is *easier* to
  automate than the desktop app — a real win, not a threat.

**Revised phases**
- **Phase 1 — Registry + routing:** ship two-module/adapter restructure; build the CSV/sheet SOR
  with routing columns; generate the derived SQLite + stand up the resolution-cache table.
- **Phase 2 — Subject resolution:** implement the address->parcel brute-force playbook + cache.
- **Phase 3 — Comp-pull hardening:** Matrix adapter (CVR+Bright) tested standard work; **Navica
  adapter**; multi-portal public leg; exporter/broker session.
- **Phase 4 — Output assembly:** one structured appraisal record (JSON) -> HTML tabbed worksheet.
- **Phase 5 — Photos:** intake -> auto-label -> rename -> place into the record/Photos tab.
- **Phase 6 — ACI web auto-fill:** field-map record -> ACI web form via Claude-in-Chrome,
  human-reviewed; fall back to HTML copy-paste.

**New open question for Alan**
6. Registry: OK with hybrid (Sheet/CSV SOR + derived SQLite + SQLite cache), or do you want a
   single SQLite store with a small editing form?

---

## 10. Note — current SKILL already does more than the test showed (2026-06-13c)
A parallel edit added to `property-search/SKILL.md`: **Step 4** automated MLS# lookup
(Zillow `MLS ID #` regex -> Matrix fallback -> BUILDER-DIRECT flag), **Step 5** CSV to
`Comps files\` + file-card + builder-direct/GLA-delta flags, and **Step 6** full
DataMaster import via computer use (with the new-construction no-APN manual-subject
exception). Plus inline Chesterfield UseCode filtering, ArcGIS TaxID `Math.round()`,
Matrix MAP-tab radius, luxury GLA widening, and the one-session rule.

These are now the baseline behavior. The refactor **migrates** them, doesn't discard:
county/MLS specifics move into adapters/registry; Step 4 becomes comp-pull enrichment
(multi-portal + multi-MLS); **Step 6 is the existing DataMaster->ACI bridge that Phase 6
grows into web auto-fill.** All captured by the pending K-002 commit.
