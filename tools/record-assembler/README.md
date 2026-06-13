# record-assembler — Build B

Assembles `appraisal-record.json` from subject facts + DataMaster comp CSV exports.
Stdlib-only, deterministic, no network calls.

## Quick start

```powershell
python tools/record-assembler/assemble_record.py `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\subject.json" `
    "C:\Users\yuriy\VDV Appraisals\Comps files\<addr>_comps_appraiser-single-line.csv" `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\appraisal-record.json" `
    --comps-agent "C:\Users\yuriy\VDV Appraisals\Comps files\<addr>_comps_agent-single-line.csv" `
    --order-id "26-0042" --client "First National Bank"
```

Then render the worksheet:

```powershell
python tools/worksheet-renderer/render_worksheet.py `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\appraisal-record.json"
```

## Files

| File | Purpose |
|------|---------|
| `assemble_record.py` | Main assembler script |
| `appraisal-record.schema.json` | JSON Schema v1.0 (repo root) |
| `subject.example.json` | Example/template for subject.json |

## Inputs

### subject.json

Subject facts gathered by the `property-search` skill. All fields optional except
`address.full` and `address.county` (needed for county-tagging comps). Shape:

```json
{
  "order": {
    "order_id":       "26-0042",
    "form_type":      "1004",
    "client":         "First National Bank",
    "loan_number":    "FNB-2026-0042",
    "effective_date": "2026-06-13",
    "due_date":       "2026-06-20",
    "inspection":     "2026-06-14",
    "fee":            500,
    "status":         "in-progress"
  },
  "address": {
    "full":   "119 Countryside Ln, Henrico, VA 23229",
    "street": "119 Countryside Ln",
    "city":   "Henrico",
    "state":  "VA",
    "zip":    "23229",
    "county": "Henrico"
  },
  "identifiers": {
    "gpin": "778-744-7716",
    "pid":  null,
    "apn":  "778-744-7716",
    "subdivision": "Countryside",
    "section": null, "block": null, "lot": null,
    "magisterial_district": "Tuckahoe",
    "neighborhood_code": null,
    "legal_description": null
  },
  "characteristics": {
    "property_type": "SFR",
    "use_code":      "10",
    "zoning":        "R-3",
    "gla_sf":        1856,
    "above_grade_sf": 1856,
    "below_grade_finished_sf": null,
    "basement":      "None",
    "year_built":    1972,
    "stories":       1,
    "style":         "Ranch",
    "grade_or_condition": "C3/Q3",
    "bedrooms":      3,
    "full_baths":    2,
    "half_baths":    0,
    "total_rooms":   7,
    "lot_size_sf":   10890,
    "lot_size_acres": 0.25,
    "garage":        "1-car attached",
    "pool":          false,
    "fireplaces":    1,
    "heating":       "FWA",
    "cooling":       "Central A/C",
    "exterior":      "Vinyl"
  },
  "assessment": {
    "tax_year":           2025,
    "land_value":         85000,
    "improvements_value": 210000,
    "total_value":        295000
  },
  "resolution": {
    "input_was_address_only": true,
    "method": "county-assessment",
    "no_tax_id": false,
    "neighbor_unit_proxy": null,
    "cached": false,
    "resolved_on": "2026-06-13"
  },
  "verification": [],
  "listing": null,
  "sales_history": [],
  "flags": [],
  "geo": { "lat": null, "lon": null },
  "market": {
    "search": {
      "radius_mi": 1.0,
      "sale_window_months": 12,
      "gla_band": { "low_sf": 1484, "high_sf": 2228, "luxury_widened": false },
      "mls_systems": ["CVR MLS"]
    },
    "neighborhood_notes": null
  },
  "sources": []
}
```

### comps CSV (DataMaster Single Line exports)

Two layouts supported — auto-detected from header:

**Appraiser Single Line** (closed/pending sales):
```
"Distance","#","ML #","PID","Prop Type","Status","Area","Address","Subdivision","Type",
"PR Abv Fin SqFt","PR Bldg SqFt","PR Living SqFt","# Bedrooms","Total Baths","# Rooms",
"Total Finished Area","SqFtTotal","Original List Price","List Price","Sales Price","",
"Days On Market","MLS"
```

**Agent Single Line** (active/pending listings):
```
"Distance","#","ML #","PID","Status","Area","Address","Subdivision","Type","# Bedrooms",
"Total Baths","# Rooms","Total Finished Area","List Price","Sales Price","",
"Days On Market","","MLS"
```

See `skills/property-search/references/datamaster-handoff.md` for export instructions.

## Rules encoded

| Rule | Implementation |
|------|---------------|
| GLA governing = MLS `Total Finished Area` | PR columns informational only |
| Missing/zero GLA → null + flag | Never estimated |
| `BRTVA…` MLS# → strip `BRT` | e.g. `BRTVAMB2000092` → `VAMB2000092` |
| Status CLOSD/PEND/ACT → closed/pending/active | `status == "unknown"` flagged |
| Out-of-county comp city ≠ subject county | `out_of_county=true` + flag |
| `review.human_reviewed = false` | Appraiser sets after certifying |
| `adjustments.entered_by_appraiser = false` | Appraiser enters adjustments |

## Determinism note

`generated_at` defaults to current UTC time — two back-to-back runs on the same
inputs will have different timestamps. Pass `--generated-at "2026-06-13T12:00:00Z"`
to pin the stamp and get byte-identical output (used in the QA test).

## Data boundary

Client data (`subject.json`, `appraisal-record.json`, comp CSVs) lives under
`C:\Users\yuriy\VDV Appraisals\` — never in the repo. The assembler script
is the only repo-resident file; inputs and outputs are always in the client zone.
