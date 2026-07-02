# Code Brief — Worksheet Renderer & Assembler Fixes
**Date:** 2026-06-19  
**Affects:** `tools/worksheet-renderer/render_worksheet.py` · `tools/record-assembler/assemble_record.py`  
**Source:** Field review of 34 Chatham Ln worksheet; corrections validated against live DataMaster session.

## Progress tracker (added 2026-07-02 — plan approved by YV; durable resume doc for a token-limited build)
> If a session resets: read this + `git log --oneline -10`, continue from the first unchecked phase.
> Plan detail: `C:\Users\yuriy\.claude\plans\woolly-dazzling-rivest.md` (Code-side copy in app memory).
- [x] Phase 0 — this tracker committed
- [x] Phase 1 — data layer: schema v1.1 (subject += assessors_parcel_number · map_reference "GIS" ·
      walls_trim "Wood" · water/sewer · re_taxes_annual · hoa_amount/period · neighborhood_bounds ·
      neighborhood_description_context; order += contract{}) + assembler defaults (only-when-absent;
      water/sewer NEVER inferred) + HOA-TBD flag + 12-mo flag demotion (missing sale_date →
      informational; hard flag only when a real date is >12 mo) + QA T18/T19, T17 adjusted
- [x] Phase 2 — renderer subject tab: Changes 1,2,3,4,5,7,8 render side (APN merge · Map Ref · DEFAULT
      chip walls · TBD utilities · IMPROVEMENTS banner · RE-taxes row · starred HOA) + QA T20
- [x] Phase 3 — renderer: Neighborhood tab (Change 6) + search-snapshot block + QA T21
- [ ] Phase 4 — wrap: example fixture regenerated (v1.1) · QA 21/21 · docs/SKILL/README/field-map
      notes · inbox [done] · interlane FYI · handoff
- NOTE: brief's `subject.tax_year` NOT added — reuse existing `subject.assessment.tax_year`.

---

## Background
Several field-level gaps and display issues were found during DataMaster entry from the rendered
worksheet HTML. These fixes make future worksheets DataMaster-ready without manual correction.

---

## Change 1 — Field label: "Assessor's Parcel #"

**Problem:** Worksheet used "Parcel ID / PID / GPIN" and "APN / Tax ID" on separate rows, creating
confusion about which value goes in which DM field.

**Fix — renderer:**
- Merge into one row: label = `Assessor's Parcel # ★ (= APN / Tax ID)`
- Second row (non-DM, informational only): `Internal PID (county portal)` — no star
- Third row: `Map Reference ★` — see Change 2

**Schema field:** `subject.assessors_parcel_number` (string, formatted with hyphens per county)

---

## Change 2 — Map Reference default = "GIS"

**Problem:** Map Reference field left blank; DM requires a value.

**Fix — assembler:** if `subject.map_reference` is null/absent, default to `"GIS"`.  
**Fix — renderer:** always render the Map Reference row; never omit it.

---

## Change 3 — Walls / trim & finish default = "Wood"

**Problem:** Field rendered as TBD. "Wood" is safe and correct for the vast majority of
residential interiors in the VA market; appraiser confirms/overrides at inspection.

**Fix — assembler:** if `subject.walls_trim` is null/absent, default to `"Wood"`.  
**Fix — renderer:** render "Wood" with source tag `DEFAULT` (not `INSP`) and a small note
"confirm at inspection."

---

## Change 4 — Water / Sewer: never default to "likely Well/Septic"

**Problem:** When Water/Sewer were blank in county data, renderer wrote "likely Well/Septic
(rural county; verify at inspection)." This is wrong when Matrix shows Public utilities.

**Fix — assembler:**
- Pull `subject.water` and `subject.sewer` from MLS/Matrix RESO fields:
  `PublicSurveySection` → utilities; or map from Matrix export columns.
- If confirmed from MLS: populate as-is (e.g. `"Public"`).
- If truly unknown: render as `TBD — verify at inspection` (no guessing direction).
- **Never infer utility type from county name or ZIP.** Rural ≠ Well/Septic.

---

## Change 5 — Improvements section: large visual header

**Problem:** Improvements section (General Desc → Exterior → Interior → HVAC → Amenities →
Room Count/Quality/Condition) has no top-level visual anchor; easy to miss during DM entry.

**Fix — renderer:** inject a full-width section banner immediately before the first
`<h3>General Description</h3>` inside the Subject panel:

```html
<h2 class="section-banner">
  ▶ IMPROVEMENTS — General Desc → Exterior → Interior → HVAC → Amenities → Room Count / Quality / Condition
</h2>
```

CSS for `.section-banner`:
```css
.section-banner {
  margin: 18px 0 4px;
  padding: 10px 14px;
  background: #1a5276;
  color: #fff;
  border-radius: 4px;
  font-size: 1.15em;
  letter-spacing: .02em;
}
```

---

## Change 6 — Neighborhood tab (NEW)

**Problem:** Worksheet had no Neighborhood tab. DM's Neighborhood tab has several fields
that need to be pre-populated or templated before entry.

**Fix — renderer:** add a `Neighborhood` tab (inserted between Subject and Sale/Listing History).

### Tab sections and content rules:

**Broad Market Characteristics**
- Location: derive from MLS area (Urban/Suburban/Rural)
- Built-Up, Growth, Property Values, Marketing Time: render as TBD (appraiser judgment)
- Demand/Supply: pull from MLS market stats if available; default `In Balance`

**Broad Market Boundaries ★**  
Template (substitute roads from `subject.neighborhood_bounds` if populated; else use placeholder):
```
The subject is bound by [ROAD] ([RT #]) to the North, [ROAD] ([RT #]) to the South,
[ROAD] to the East, and [ROAD] to the West.
```
- Add a caution note: "⚠ Verify bounding roads at inspection."
- Store bounding roads in `subject.neighborhood_bounds` as `{north, south, east, west}` strings.
- For Fluvanna / Lake Monticello orders: Rt. 53 (N), Rt. 6 (S), Rt. 15 (E), Rt. 20 (W) — pre-populate from county-registry or notes.

**Present Land Use %**  
- 2-4 Unit / Multi-Family: default 0% for SFR-only neighborhoods; render as TBD otherwise.
- One-Unit, Commercial, Other: TBD (appraiser fills at inspection).

**One-Unit Housing (Price / Age)**  
- Pull Low/High/Predominant from comp range once comps are assembled.
- If comps not yet assembled: TBD.

**Broad Market Description ★**  
Template (substitute housing style from `subject.style` and neighborhood name):
```
Neighborhood with a mix of [STYLE] and Custom Built homes. Amenities include
[AMENITIES]. Recent sales data is personally verified for accurate market representation.
```
- Common style substitutions: Split Foyer, Ranch, Colonial, Cape Cod, Contemporary.
- Amenities: pull from subject data (lake access, community pool, parks, etc.) or use
  "parks, schools, and local businesses" as a safe fallback.
- Store template fields in `subject.neighborhood_description_context`.

**Market Conditions ★**  
- TBD at this stage; `notes-composer` fills this after comps are assembled.
- Render a placeholder: "Draft via notes-composer after comps assembled. Include DOM trend,
  list-to-sale ratio, and any view/waterfront premium observation."

---

## Change 7 — RE Taxes: bill vs. assessment

**Problem:** Renderer surfaced the assessed value (land + improvements) but not the annual
tax bill amount, which is what DM's "R.E. Taxes $" field wants.

**Fix — assembler:** add `subject.re_taxes_annual` (number, dollars) as a distinct field
from `subject.assessed_value`. Source: actDataScout tax-bill section, or MLS `TaxAnnualAmount`.

**Fix — renderer:** render both:
- `R.E. Taxes $ ★` → `subject.re_taxes_annual` (Tax Year `subject.tax_year`)
- `Assessed Value` → `subject.assessed_value` (Land + Improvements breakdown)

---

## Change 8 — HOA always a DM field

**Problem:** HOA row was present but not consistently marked as a DM field (★).

**Fix — renderer:** HOA row always gets ★. Label: `HOA $ / period ★`.  
**Fix — assembler:** `subject.hoa_amount` (number) + `subject.hoa_period` ("monthly"/"annually").  
If not found in MLS: render `TBD — get from HOA docs`; never omit the row.

---

## Schema additions (appraisal-record.schema.json)

Add to `subject` object:
```json
"assessors_parcel_number": { "type": ["string","null"] },
"map_reference":           { "type": "string", "default": "GIS" },
"walls_trim":              { "type": "string", "default": "Wood" },
"water":                   { "type": ["string","null"] },
"sewer":                   { "type": ["string","null"] },
"re_taxes_annual":         { "type": ["number","null"] },
"tax_year":                { "type": ["integer","null"] },
"hoa_amount":              { "type": ["number","null"] },
"hoa_period":              { "type": ["string","null"], "enum": ["monthly","annually",null] },
"neighborhood_bounds":     {
  "type": ["object","null"],
  "properties": {
    "north": {"type":"string"}, "south": {"type":"string"},
    "east":  {"type":"string"}, "west":  {"type":"string"}
  }
},
"neighborhood_description_context": {
  "type": ["object","null"],
  "properties": {
    "style":     {"type":"string"},
    "amenities": {"type":"string"}
  }
}
```

---

## QA checklist (after implementing)

- [ ] Render a test worksheet; confirm "Assessor's Parcel #" label present, PID row is separate/no-star
- [ ] Confirm Map Reference renders "GIS" when `map_reference` absent from input
- [ ] Confirm Walls/trim renders "Wood" when `walls_trim` absent
- [ ] Confirm Water/Sewer render "TBD — verify at inspection" (no directional guess) when null
- [ ] Confirm Improvements banner renders with correct CSS
- [ ] Confirm Neighborhood tab appears between Subject and Sale/Listing History
- [ ] Confirm RE Taxes and Assessed Value render on separate rows
- [ ] Confirm HOA row always present and starred
- [ ] Run existing QA suite (15 tests) — all should still pass
