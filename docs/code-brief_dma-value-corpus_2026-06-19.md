# Code Brief — .dma Value Corpus: Batch Extract → De-identify → Analyze → Integrate
**Date:** 2026-06-19  
**Requested by:** Bob (Cowork) on behalf of Yuriy  
**Scope:** `tools/` additions + downstream updates to existing skills/tools  
**Cardinal rules:** client data never enters the repo; read-only on `.dma` (no DMA-write production path)

---

## Why

113 real, Alan-submitted `.dma` files sit in `Past Reports/Past DM files/`. Code already
extracted **field names** (368 names, frequencies in `corpus_field_names.json`). Field **values**
were never extracted at scale — only one file (1114 Skipwith) was fully decoded.

Those values are the ground truth for:
- what DataMaster fields Alan consistently fills vs. leaves blank
- what default values recur (walls, condition tiers, neighborhood text, water/sewer)
- what adjustment magnitudes were accepted in delivered reports (validates/replaces playbook estimates)
- what Neighborhood Boundary and Market Description language Alan used per county

Three downstream consumers already exist and will benefit without further work once the corpus lands:
- `tools/dm-collection-sheet/prefill_worksheet.py` + condition profiles (YAML) — already wired to profiles; update profiles, prefill improves
- `skills/notes-composer/references/adjustment-playbook/playbook.yaml` — update $ amounts from real data
- `skills/worksheet-builder/SKILL.md` — DM-specific field rules section

---

## What already exists — do not rebuild

| Asset | Location | Status |
|---|---|---|
| Decoder (single file) | `tools/dma-decoder/dma_decode.py` | ✅ stdlib, `--json` flag |
| Field-name corpus | `Past Reports/_analysis/_dma-decode/corpus_field_names.json` | ✅ 113 files, union_counts + per_file |
| Field reference (orderly) | `Past Reports/_analysis/_dma-decode/DM-field-reference_2026-06-15.md` | ✅ DM name ↔ MISMO ↔ collect-from |
| Single full decode w/ values | `Past Reports/_analysis/_dma-decode/1114_skipwith_decode.json` | ✅ reference/validate against |
| Deidentify gate | `tools/deidentify/` | ✅ one-way, strict + locality — extend for structured DM values |
| Condition profiles | `skills/worksheet-builder/references/condition-profiles/condition-profiles.1004.yaml` | ✅ mined from 38 XML + 22 gPAR; validate + update from .dma corpus |
| Prefill tool | `tools/dm-collection-sheet/prefill_worksheet.py` | ✅ reads condition profiles; no changes needed if profiles update correctly |
| Collection sheet builder | `tools/dm-collection-sheet/build_collection_sheet.py` | ✅ field names only; leave as-is |
| dma-write-poc | `tools/dma-write-poc/dma_write_poc.py` | 🧪 experimental — validation pending (see Bonus phase) |
| Notes-composer library | `skills/notes-composer/references/notes-library/` | ✅ update adjustment playbook only |

---

## Phase A — Batch value extraction

**New script:** `tools/dma-decoder/dma_batch_extract.py`

Runs `dma_decode.py` on every `.dma` in a given directory tree and writes a raw value
corpus. Stdlib-only. This is the only new script in Phase A.

### What to extract per file

Use the **field registry** (the inline dict already decoded — protobuf field 3 in the
`Appraisal` blob) to name each value. For each file emit a flat dict of
`{ dm_field_name: value_string }`. Only extract string/text leaves (skip raw byte blobs).

Priority field groups (drives de-identification in Phase B and analysis in Phase C):

```
GROUP A — PII (will be STRIPPED):
  AddressLine1, HouseNumber, StreetName, StreetSuffix, StreetDirectional
  OwnerOfPublicRecord, OwnerOfPublicRecord1
  Borrower, CoBorrower
  LenderName, ClientName, ClientAddress
  AppraiserName, SupervisingAppraiserName
  CertificationNumber, LicenseNumber, StateCertification, StateLicense
  SignatureDate, InspectionDate   ← dates (keep year only)

GROUP B — KEEP (analysis targets):
  City, State, Zip, County, NeighborhoodName, Subdivision
  Apn, CensusTract, ZoningClassification, ZoningDescription, LegalDescription*
  YearBuilt, ActualAge, NumberOfStories, ArchitecturalStyleTypes
  AboveGradeGla, BasementTotalSqFt, BasementFinishedPercent
  TotalAboveGradeRooms, TotalAboveGradeBedrooms, TotalAboveGradeFullBaths, TotalAboveGradeHalfBaths
  GrossLivingAreaIndicator
  ExteriorWalls, RoofSurface, Foundation (all foundation type flags)
  HeatingType, CoolingType, FuelType, GasPublic, GasOther, ElectricityPublic
  WaterPublic, WaterOther, SewerPublic, SewerOther
  WallsAndTrimFinish, FloorsDescription, BathFloorDescription, BathWainscotDescription
  Fireplace*, NumberOfFireplaces
  GarageTypes, GarageSquareFeet, PorchTypes, PorchSquareFeet, DeckTypes, DeckSquareFeet
  PoolOnSite, FenceOnSite, PatioPorchDeck (all amenity flags)
  HoaAmount, HoaPeriod, HoaPerYear, HoaPerMonth
  TaxYear, RETaxes, AssessmentLand, AssessmentImprovement, AssessmentTotal
  QualityRating (Q1-Q6), ConditionRating (C1-C6), EffectiveAge
  MapReference, PropertyRightsAppraised, Occupancy (all variants)
  NeighborhoodDescription, MarketConditionsDescription, BoundaryDescription  ← free text; high value
  -- Comp adjustment amounts (from comp grid fields): all GlaAdjustment*, SiteAdjustment*,
     ConditionAdjustment*, etc. — keep $ values, strip comp address fields

GROUP C — KEEP for provenance, pseudonymize address:
  City + County + Zip + NeighborhoodName (keep; not PII)
  SaleDate, SalePrice (public record — keep)
  MlsNumber (public — keep)
```

*LegalDescription: keep subdivision/lot portion; strip deed-book/page if they risk identifying the owner.

### Output

```
Past Reports/_analysis/_dma-decode/corpus_values_raw.json    ← client zone, never in repo
```

Schema:
```json
{
  "n_files": 113,
  "extracted": "2026-...",
  "files": {
    "1114 Skipwith Rd.dma": {
      "County": "Henrico",
      "YearBuilt": "1992",
      "AboveGradeGla": "1546",
      "WallsAndTrimFinish": "Drywall/Avg",
      ...
    },
    ...
  }
}
```

### CLI
```powershell
python tools/dma-decoder/dma_batch_extract.py \
    --src "C:\Users\yuriy\VDV Appraisals\Past Reports\Past DM files" \
    --out "C:\Users\yuriy\VDV Appraisals\Past Reports\_analysis\_dma-decode\corpus_values_raw.json"
```

Print a progress line per file (`[n/113] filename → N fields extracted`) and a summary at end.
Exit non-zero if any file fails to parse; log the failure and continue (don't abort the batch).

### Validate against known decode
After running, spot-check: `1114 Skipwith Rd.dma` values in the new corpus must match
`1114_skipwith_decode.json` for every GROUP B field. Assert this programmatically.

---

## Phase B — De-identification

**New script:** `tools/dma-decoder/dma_deidentify_corpus.py`

Reads `corpus_values_raw.json`. Applies the following rules per field and writes the
clean corpus. Reuses logic from `tools/deidentify/` where applicable; extend it for
structured DM key-value input (the existing tool handles free text, not key-value dicts).

| Action | Fields |
|---|---|
| **STRIP** (omit field entirely) | All GROUP A fields |
| **YEAR-ONLY** (keep `YYYY`, drop month/day) | `SignatureDate`, `InspectionDate`, `SaleDate` |
| **KEEP AS-IS** | All GROUP B fields |
| **PSEUDONYMIZE** | File key: replace filename with `report_NNN` (stable hash — same file → same ID across runs, so downstream joins work) |

After stripping: run a **residual PII scan** across all remaining string values using the
same heuristics as `tools/deidentify/` (name patterns, SSN, phone, email, full address
strings). Anything that matches goes into a `_pii_suspect` log for review — do not auto-strip.

### Output
```
Past Reports/_analysis/_dma-decode/corpus_values_deidentified.json   ← client zone
Past Reports/_analysis/_dma-decode/corpus_deid_audit.json             ← any _pii_suspect entries
```

Corpus schema matches `corpus_values_raw.json` but file keys become `report_001` … `report_113`
and all GROUP A fields are absent. Add a `_meta` block:
```json
"_meta": {
  "n_files": 113,
  "deid_date": "2026-...",
  "stripped_fields": ["AddressLine1", ...],
  "pii_suspect_count": 0
}
```

---

## Phase C — Analysis

**New script:** `tools/dma-decoder/dma_corpus_analyze.py`

Reads `corpus_values_deidentified.json`. Produces one Markdown report and one JSON
summary. Both go to `_analysis/_dma-decode/`. The Markdown report is the human-readable
deliverable; the JSON feeds downstream tools programmatically.

### Report sections

**1. Field completeness** — for each of the 172 "always-present" fields (from `corpus_field_names.json`),
what % of 113 files have a non-null, non-empty value? Table: field | present % | modal value (if categorical).
Flag fields where present < 50% — those are candidates to drop from the worksheet template.

**2. Default value candidates** — for categorical/short-string fields where one value
appears in ≥ 60% of files, surface it as a "safe default." Key fields:

```
WallsAndTrimFinish          → expected: "Wood/Avg" or "Drywall/Avg"
ExteriorWalls               → expected: "Vinyl/Avg", "Brick/Avg"
RoofSurface                 → expected: "Comp/Avg"
WaterPublic (bool)          → true/false split
SewerPublic (bool)          → true/false split
MapReference                → validate "GIS" default
PropertyRightsAppraised     → expected: "Fee Simple" ~100%
QualityRating (modal)       → expected: Q3 dominant
ConditionRating (modal)     → expected: C3/C4
```

**3. Adjustment amount calibration** — for each non-zero adjustment type found in the
comp grid fields, emit: feature | n reports used | median $ | p25 | p75 | min | max.
Compare to current `playbook.yaml` values. Flag where playbook is >20% off the median.

Key features: GLA ($/sf), Site area, Condition ($/step), Garage, Basement (finished sf),
Porch/Deck, Date of sale (monthly rate), Location, View, Quality.

**4. Neighborhood text mining** — extract all non-empty values of:
`NeighborhoodDescription`, `MarketConditionsDescription`, `BoundaryDescription`
Group by County. For each county with ≥ 3 examples, output the examples verbatim
(de-identified — no address/name in these fields after Phase B scrub).
These become the raw material for county-specific Neighborhood tab templates.

**5. Water/Sewer breakdown by county** — cross-tab: County × WaterPublic/SewerPublic.
This tells us which counties are predominantly public vs. well/septic so we can set
smarter defaults in the worksheet (not just "TBD — likely Well" for any rural county).

**6. HOA coverage** — % of files with non-zero HoaAmount, amount distribution,
HoaPeriod split (monthly vs annual). Confirms HOA is a minority case and what amounts are typical.

### Output files
```
Past Reports/_analysis/_dma-decode/corpus_analysis_report.md   ← human deliverable
Past Reports/_analysis/_dma-decode/corpus_analysis.json        ← machine-readable
```

`corpus_analysis.json` schema (top-level keys):
```json
{
  "field_completeness":   { "FieldName": {"present_pct": 0.94, "modal_value": "Wood/Avg"}, ... },
  "default_candidates":   { "WallsAndTrimFinish": "Wood/Avg", ... },
  "adjustment_stats":     { "GLA":       {"n":89, "median_per_sf": 78, "p25": 65, "p75": 90}, ... },
  "neighborhood_text":    { "Henrico":   ["...", "..."], "Chesterfield": ["..."], ... },
  "water_sewer_by_county":{ "Henrico":   {"water_public_pct":0.98, "sewer_public_pct":0.96}, ... },
  "hoa_stats":            { "has_hoa_pct": 0.22, "median_monthly": 122, "median_annual": 1464 }
}
```

---

## Phase D — Downstream integration

Run after Phase C is reviewed and approved by Yuriy. **Do not auto-apply — present diffs first.**

### D1. Update condition profiles
File: `skills/worksheet-builder/references/condition-profiles/condition-profiles.1004.yaml`

For each tier (new / average / fair):
- Replace any `# estimated` comments with `# corpus: N/113 files` provenance
- Update `walls`, `floors`, `trim_finish`, `roof`, `foundation` values where corpus modal
  differs from current profile default
- Add `corpus_validated: true` flag to each tier if corpus confirms it; `corpus_sparse: true`
  if < 5 examples (keep current estimate, flag for caution)

Do NOT touch `quality_note` or the "Profiles save typing, not judgment" header — those are
deliberate editorial choices.

### D2. Update adjustment playbook
File: `skills/notes-composer/references/adjustment-playbook/playbook.yaml`

For each adjustment feature in `corpus_analysis.json.adjustment_stats`:
- Replace the current single `typical_amount` estimate with `median`, `p25`, `p75`
  and a `corpus_n` count
- Add `corpus_source: "113 VDV .dma files, 2026-06-19"` to the file header
- Flag any feature where corpus_n < 10 as `low_confidence: true`

### D3. Neighborhood text templates
File: `skills/notes-composer/references/notes-library/1004/neighborhood-templates.yaml`
(create if it doesn't exist; follow the existing notes-library YAML format)

For each county with ≥ 3 examples in `neighborhood_text`:
- Write a `boundary_template` (Roads N/S/E/W in the Alan wording pattern)
- Write a `market_description_template` (1-2 sentence Alan-style market summary)
- Tag with `county`, `corpus_examples_n`, `source: "dma-corpus-2026-06-19"`

**This directly feeds the Neighborhood tab** added in the worksheet renderer brief
(`docs/code-brief_worksheet-renderer-fixes_2026-06-19.md`, Change 6).

### D4. Water/Sewer county defaults
File: `skills/property-search/references/data-quirks.md`

Add entries for any county where water_public_pct ≥ 0.90 or ≤ 0.10 — those are
strong enough to be a workflow default rather than "TBD." Format: new quirk row
`WTR-NNN | County | Public/Well default | corpus evidence`.

---

## Bonus — dma-write-poc validation (prerequisite for any future write path)

`tools/dma-write-poc/dma_write_poc.py` exists but the round-trip has NOT been confirmed
in DataMaster by Yuriy. Before Phase D ships (or any future write automation), this gate
must close:

1. Run `python dma_write_poc.py roundtrip --src "...1114 Skipwith Rd.dma" --out "...1114_RT.dma"`
2. **Yuriy opens `1114_RT.dma` in DataMaster** — confirm it opens cleanly, all fields intact
3. Run `python dma_write_poc.py patch --src "...1114 Skipwith Rd.dma" --out "...1114_PATCHED.dma" --old <old_string> --new <new_string>`
4. **Yuriy opens `1114_PATCHED.dma`** — confirm the patched value surfaces in DM

Until both (2) and (4) pass, the write path stays POC only. Record result in `data-quirks.md`
DMA-001 update.

---

## Constraints and rules

- **Stdlib-only** — no pip installs. All three new scripts: `dma_batch_extract.py`,
  `dma_deidentify_corpus.py`, `dma_corpus_analyze.py`.
- **All outputs stay in client zone** (`Past Reports/_analysis/`). Nothing from Phase A–C
  enters the repo. Only the YAML/MD updates in Phase D (field names and anonymized patterns
  only — zero client values) go into the repo.
- **Read-only on `.dma`** throughout. The batch extractor opens files as `zipfile` → reads
  the blob → never writes back. Assert this in the script header.
- **Non-destructive Phase D** — every file updated in D1–D4 gets a backup copy
  (`<file>.pre-corpus-2026-06-19.bak`) before edits. Present diffs to Yuriy before applying.
- **One-session rule** — do not run these scripts while another Cowork session is active on
  the repo (git-corruption risk if D phases touch repo files).

---

## QA checklist

- [ ] Phase A: all 113 files extracted; 0 parse failures (or failures logged + understood)
- [ ] Phase A: 1114 Skipwith values match `1114_skipwith_decode.json` for all GROUP B fields
- [ ] Phase B: `corpus_deid_audit.json` pii_suspect_count = 0 (or each flagged entry reviewed)
- [ ] Phase B: spot-check 5 random `report_NNN` entries — no names, addresses, cert numbers visible
- [ ] Phase C: `corpus_analysis_report.md` reviewed by Yuriy before Phase D begins
- [ ] Phase D: diffs for each updated YAML/MD file shown to Yuriy; no auto-apply
- [ ] Phase D: `prefill_worksheet.py` produces valid HTML after condition profile update (existing test)
- [ ] Phase D: notes-composer adjustment hints changed to median/p25/p75 format — verify no test regressions
- [ ] Bonus: dma-write-poc round-trip validated by Yuriy in DataMaster (async — does not block A–D)

---

## Deliverable summary

| Phase | Output | Location |
|---|---|---|
| A | `corpus_values_raw.json` | `Past Reports/_analysis/_dma-decode/` (client zone) |
| B | `corpus_values_deidentified.json`, `corpus_deid_audit.json` | same |
| C | `corpus_analysis_report.md`, `corpus_analysis.json` | same |
| D1 | updated `condition-profiles.1004.yaml` | `skills/worksheet-builder/references/condition-profiles/` |
| D2 | updated `playbook.yaml` | `skills/notes-composer/references/adjustment-playbook/` |
| D3 | new `neighborhood-templates.yaml` | `skills/notes-composer/references/notes-library/1004/` |
| D4 | new quirk rows in `data-quirks.md` | `skills/property-search/references/` |
| Bonus | dma-write-poc result → DMA-001 update | `data-quirks.md` |
