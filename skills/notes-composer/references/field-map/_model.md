# Field-map model — one mapping, multiple lenses

The appraisal-record JSON (`appraisal-record.schema.json`) is the hub. Every
consumer is a *projection* of it, so the field map is **one table keyed on
`record_path`** with a column per consumer — not separate, divergent files.

```
record_path  →  mismo     (ACI/MISMO 2.6 element[attribute] — the structured source)
                pdf       (delivered report: { section, label, kind: grid-cell|narrative })
                aci_web   (selector/field-id for ACI web auto-fill — null until new ACI is live)
                worksheet (which Build A render_worksheet.py tab/row surfaces it)
```

## Why one table
ADR-002 called for a **swappable field-map (record→form), kept as config not code**.
Building the XML→PDF mapping now (to QA the extraction) *is* the seed of the future
record→ACI map — same artifact, you just fill the `aci_web` column later. Two separate
files would drift. A DOM change in ACI becomes a data edit in `aci_web`, not code.

## Source of truth vs documentation
- The **renderer code** (`render_worksheet.py` `COMP_ROWS` / `build_*_tab`) remains the
  source of truth for *rendering*. The `worksheet` column here **documents** that contract
  so drift is visible; the renderer does not load this YAML (a later refactor may, once the
  map is proven stable — see ADR-003).
- **Worksheet-lens note (2026-07-02, schema v1.1):** the renderer now also surfaces a
  `Neighborhood` tab + search-snapshot strip and the DM-ready subject rows
  (`subject.assessors_parcel_number`, `map_reference`, `walls_trim`, `water/sewer`,
  `re_taxes_annual`, `hoa_amount/period`, `neighborhood_bounds`,
  `neighborhood_description_context`, `order.contract`,
  `market.search.surrounding_counties`). When seeding `worksheet` cells for these
  record paths, point them at the Subject/Neighborhood tabs accordingly. Existing
  record paths were NOT renamed.
- `mismo` + `pdf` columns are **validated** for FNM1004 against the 3 URAR pairs (pair-QA,
  100% value match). Other forms are seeded or stubbed per sample availability.

## Files & status
| File | Form | Status |
|---|---|---|
| field-map.1004.yaml | FNM1004 | seeded-validated (30 XML + 3 pairs) |
| field-map.1004C.yaml | FNM1004C | seeded (6 XML) |
| field-map.2055.yaml | FNM2055 | low-confidence (1 XML) |
| field-map.1025.yaml | FNM1025 | low-confidence (1 XML) |
| field-map.1073.yaml | FNM1073 | unsupported — no samples |
| field-map.1004-fha.yaml | 1004 + HUD | unsupported — no samples |

Don't fabricate rows for unsupported forms; the stubs exist so the gap is explicit.
