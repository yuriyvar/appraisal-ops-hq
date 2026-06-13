# ADR-002: Data-source architecture — two modules, vendor-family adapters, county registry

Date: 2026-06-13 · Status: proposed (drafted on kaizen/K-002; human to review/merge)

## Context
The property-search skill led with one headline technique ("query the county's
live ArcGIS sales FeatureServer"). A live test on 119 Countryside Ln (Henrico)
showed that technique has no working target in Henrico: the county open-data
parcel layer is a 735-record sample, and there is no public queryable sales
layer. The subject had to be pulled from the APEX assessment site, and comps
from the MLS. Generalizing per-county is not viable (~95 VA jurisdictions), and
a second MLS (Navica) is coming.

## Decision
1. **Split the skill into two concerns:**
   - `subject-verification` — always from the county assessment **SOR**
     (per-county), cross-checked with Zillow.
   - `comp-pull` — **MLS-first** (CVR Matrix today, Navica next); a county
     sales-GIS layer is an *optional accelerator* only where one exists.
2. **Adapters by vendor family, not per county.** County specifics collapse into
   ~8 assessment-vendor families (CivQuest, Vision/vgsi, actdatascout,
   ArcGIS-Experience, webgis, interactivegis, qPublic, APEX) and ~2 MLS
   platforms (Matrix, Navica). The skill resolves county -> family -> technique.
3. **Promote the county sheet to a structured registry** (the SOR) with explicit
   routing columns: assessment vendor + technique, whether a queryable sales-GIS
   layer exists (+ endpoint), and the comp source (GIS vs MLS-only).
4. **Keep all county/MLS specifics in data** (registry), never duplicated prose.

## Why MLS is the backbone regardless of GIS coverage
Even where a sales-GIS layer exists (Hanover, Chesterfield), county data lacks
DOM, concessions, condition, and the list-vs-sold / prior-listing chain the 1004
needs. So MLS is always in the loop; county GIS only accelerates the *universe*
and spatial filter. The highest-leverage build is therefore a rock-solid,
MLS-agnostic comp-pull module — not GIS coverage.

## Consequences
- One skill scales to the whole state; new counties = a registry row, not code.
- Comp-pull needs a per-MLS adapter behind a common interface that emits the
  DataMaster CSV.
- Registry coverage is built by **order volume first** (Richmond metro), not all
  95 jurisdictions at once.

## Revisit when
A third MLS appears, or ACI direct-ingestion replaces the CSV/HTML handoff.

---

## Amendment 2026-06-13 (scope expansion)

### Public data leg = multi-portal, not just Zillow
The cross-check leg uses an adapter set: **Zillow, Realtor.com, Redfin,
Homes.com** (+ future). Same interface (address -> facts/APN/last-sold); pick
best-available and reconcile. See `references/subject-resolution.md`.

### MLS = 3+ platforms via two adapter shapes
Active MLSs: **CVR MLS (Matrix), Bright MLS (Matrix), Navica** — more likely.
Key fact: **CVR and Bright both run on the Cotality Matrix platform**, so a single
parameterized "Matrix adapter" (instance URL + login) covers both; **Navica is a
different platform needing its own adapter**. The comp-pull module stays
MLS-agnostic behind a common interface that emits the identical DataMaster CSV.

### Registry storage — recommendation: hybrid, not SQLite-as-SOR
- Keep the **human-authored SOR diff-friendly and editable**: the Google Sheet
  (or a CSV/markdown mirror in-repo). This preserves Yuriy/Alan editing, git diffs,
  and the kaizen-via-PR review (ADR-001). A binary SQLite file as the SOR would
  break PR review and casual editing.
- **Derive a SQLite database** from that source for the agent: fast typed queries,
  relational tables (counties, vendors, MLS instances, portals, adapters, quirks).
- **Use SQLite as the RESOLUTION CACHE** (resolved subjects/parcels/comps) — a
  growing operational asset that directly streamlines subject-resolution and
  avoids re-brute-forcing. This is where SQLite earns its keep.
- Net: **CSV/sheet = source of truth (human); SQLite = built index + cache (machine).**

### ACI is going fully web-based — treat it as the final consumer
Build one structured **appraisal record (JSON)** as the single internal output,
then render two consumers: (a) the **HTML tabbed worksheet** for manual copy-paste
(near-term), and (b) a **browser auto-fill** of ACI's web form via Claude-in-Chrome
driven by a separate, swappable **field-map** (record field -> ACI web field).
Guardrails: human review, never auto-submit, field-map kept as config so a DOM
change is a data edit not a code change. Web-based ACI is actually *friendlier* to
automate than a desktop app.

---

## Reconciliation with concurrent SKILL.md updates (2026-06-13)
While this ADR was drafted, a parallel session enriched `property-search/SKILL.md`.
The two edit sets merged cleanly. The skill now also contains:
- **Step 4 — automated MLS# lookup:** Zillow first (`innerText.match(/MLS ID #\d+/gi)`
  off the sale-history stack), Matrix fallback for gaps, **BUILDER-DIRECT** flag when
  no MLS# exists.
- **Step 6 — DataMaster import via computer use:** open DM, create order, import the
  `Comps files\` CSV, screenshot, hand back for Review & Send; **new-construction
  exception** = user enters subject manually first (no APN).
- **Inline county/MLS specifics:** Chesterfield UseCode filter, ArcGIS TaxID
  `Math.round()`, Matrix MAP-tab radius rule, luxury GLA widening, one-session /
  Identity-Conflict rule.

**Mapping into the target architecture (migrate, don't delete):**
- Inline county/MLS specifics -> **extract** into registry rows + vendor/MLS adapters
  (the skill body shouldn't hardcode Chesterfield/ArcGIS/Matrix quirks long-term).
- Step 4 MLS# lookup -> **comp-pull enrichment** stage; generalize Zillow->multi-portal
  and Matrix->multi-MLS (CVR/Bright/Navica).
- Step 6 DM-import-via-computer-use -> this **is** the current DataMaster->ACI bridge;
  Phase 6 (ACI web auto-fill) evolves from it rather than replacing it day one.
- New-construction / no-APN handling -> the **subject-resolution** module + SQLite cache.
