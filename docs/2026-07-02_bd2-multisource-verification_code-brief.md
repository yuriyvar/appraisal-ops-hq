<!-- build-plan: name=bd2-multisource-verification status=active -->
# Code brief — BD2: multi-source verification + variance protocol

> Track 2 of the automation roadmap. Encodes YV's decision (2026-07-02) into the pipeline:
> pull order **MLS → County/GIS → Zillow**; on disagreement *read the listing info* — if it
> SUPPORTS the variance, record the value + justification; if not, **County rules**; either
> way the field is flagged **"inconsistent — manual triage"** until YV clears it.

## Progress tracker
- [x] Phase 0 — this brief committed
- [x] Phase 1 — ingest engine: `source_values` + `variance_notes` helper blocks → canonical
      value + `verification[]` row + triage flags; `gla_mls_sf` back-compat; QA C18 matrix
- [ ] Phase 2 — resolver: pull sheet reordered MLS → County → Zillow + variance-protocol box;
      skeleton seeds the helper blocks; QA C19 (+ e2e triage chip renders)
- [ ] Phase 3 — wrap: docs/SKILL wording · triage-clearing procedure documented · inbox ·
      interlane FYI · handoff · tag done + BD2 ticked in the master queue

## Design (locked)
- **Tracked fields** (`_MULTI_SOURCE`): gla_sf ("Finished area (sf)", ±2%) · year_built (exact) ·
  lot_size_acres (±2%) · bedrooms (exact) · full_baths (exact, Matrix N.M) · stories (exact).
- **Helper blocks in the raw/skeleton** (stripped at ingest, never reach the record):
  `source_values: {field: {mls, county, zillow}}` + `variance_notes: {field: "one-line reason"}`.
- **Resolution rules** (county vs MLS is THE conflict that matters; Zillow never governs):
  - agree (within tolerance) → canonical = county, governing "county", no flag;
  - disagree + justification present → canonical = **MLS**, governing "mls (justified)",
    flag "variance SUPPORTED: <reason> — inconsistent, manual triage until YV clears";
  - disagree, no justification → canonical = **county**, flag "differ … — inconsistent,
    manual triage (no supporting listing evidence); County rules";
  - county missing → MLS value governs (note); only Zillow → value + "weakest source, verify";
  - Zillow differing while county/MLS agree → informational note only, never triage.
- Triage flags land BOTH on the verification row (renderer's row chip) and in
  `subject.flags` (worksheet header chip). **Clearing a triage flag** = YV decides →
  COWORK_AGENT re-ingests with `variance_notes` filled (supported) or the bad source value
  corrected — never by deleting the flag string by hand.
- Canonical lands in `characteristics.<field>` BEFORE the baths-split/GLA gates run, so the
  existing gates apply to the resolved value. No schema change (verification[] is v1.0).

## Out of scope
Auto-reading listing remarks (that judgment is the human's; BD4's tools can assist later) ·
water/sewer multi-source (Change-4 rule already covers: MLS-only, never inferred) ·
comp-side verification (subject only) · Tracks 3–5.

## Verify
```powershell
python "appraisal-ops-hq\tools\subject-resolution\tests_subject_resolution.py"   # 17 -> 19
python "appraisal-ops-hq\tools\record-assembler\tests_qa_runner.py"              # 22/22 intact
```
