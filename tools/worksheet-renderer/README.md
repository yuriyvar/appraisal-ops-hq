# Worksheet Renderer (Build A)

Turns an `appraisal-record.json` into a single, self-contained, tabbed
`worksheet.html` the appraiser can open and copy-paste into ACI.

This is **Build A** of the Worksheet Builder pipeline (handoff 2026-06-13 §7).
It is the *target* that data-collection (Builds B–D) fills.

## Why this first
It is deterministic, has **no external/network calls**, uses **stdlib only**,
and can be tested immediately against `appraisal-record.example.json`. It turns
the schema into a visible artifact and locks the render contract before any
data-collection automation is built.

## Usage
```bash
python render_worksheet.py RECORD.json [-o OUTPUT.html]
```
- Default output: `worksheet.html` next to the input record.
- Exits non-zero on bad JSON / missing file, or when the **comp Tax ID
  completeness gate** fails (a comp has a PID/APN/map_id in the record but it
  did not render in the HTML — see `audit_comp_tax_ids`). The worksheet is still
  written so it can be inspected. A schema_version mismatch prints a warning but
  still renders.

Example:
```bash
python tools/worksheet-renderer/render_worksheet.py appraisal-record.example.json \
  -o tools/worksheet-renderer/worksheet.example.html
```

## Output layout (adopted standard since 2026-07-02 — 6/19 brief implemented)
**Search-snapshot strip** (above the tabs): governing above-grade GLA · county-vs-MLS
finished area (from `verification`) · comp GLA band (record's, else computed ±10%) ·
garage/carport · basement total/finished · county + surrounding counties (dash until
the orchestrator fills `market.search.surrounding_counties` — the renderer never looks
anything up).

**Default tabs:**
- **Subject** — DM-ready: one **"Assessor's Parcel # ★ (= APN / Tax ID)"** row
  (`assessors_parcel_number || apn || pid || map_id`) + informational Internal PID +
  **Map Reference ★** (defaults "GIS"); Site table carries **Water ★ / Sewer ★**
  (value or "TBD — verify at inspection" — never a directional guess); the
  **▶ IMPROVEMENTS banner** splits site from improvements rows; **Walls/trim ★**
  shows a `DEFAULT` chip on the assembler's "Wood" stand-in; **R.E. Taxes $ ★** is
  its own row (bill ≠ assessment); **HOA $ / period ★** always renders (TBD chip when
  missing); a **Contract (purchase)** block appears when `order.contract` has data.
- **Neighborhood** — 6/19 brief Change 6: Broad Market Characteristics (TBD +
  Demand/Supply "In Balance" default), Boundaries ★ template from
  `subject.neighborhood_bounds` (+ verify-at-inspection caution), Present Land Use %
  (0% defaults for SFR), One-Unit Housing price/age derived from ≥3 CLOSED comps
  (else TBD), Market Description ★ template, Market Conditions ★ notes-composer
  placeholder.
- **Comp grid** — URAR-style: features as rows, SUBJECT + comps as columns.
  **Closed sales are segregated from Active/Pending** (listings are supporting
  analysis only, per the comp-quality rule). Per-comp flags shown.
- **Sale / Listing history** — subject sales history + current listing; comp
  prior sales.

**Optional (OFF by default — require Yuriy's approval; opt in with flags):**
- **Photos** (`--with-photos`) — card grid; placeholder until the photo-organizer build lands.
- **Map** (`--with-map`) — inline SVG scatter of subject vs comps from lat/lon (no map tiles,
  to stay deterministic) + a coordinate/proximity table.

## Contract notes
- Renders defensively: every field is null-safe; empty arrays produce a clean
  "none yet" state rather than a crash.
- The footer always shows the **review gate** (REVIEWED vs NOT YET REVIEWED) —
  the renderer assembles data; the licensed appraiser certifies. Nothing files
  automatically.
- Built for `schema_version` **1.0 and 1.1** (`appraisal-record.schema.json`).
  v1.1 adds the DM-ready subject fields + `order.contract` +
  `market.search.surrounding_counties` (6/19 brief).

## Tested branches
QA = `tools/record-assembler/tests_qa_runner.py` (21 e2e tests, assemble→render,
determinism byte-identical). The committed fixture pair is synthetic:
`appraisal-record.example.json` (v1.1; 3 closed + 1 active comp, purchase contract,
bounds, sewer null → TBD, HOA missing → flag) → `worksheet.example.html`,
regenerated deliberately via the Usage command above.

## Next builds (depend on this contract)
- **B** — comp-pull standard work that fills the record automatically. ✅ live.
- **C** — subject-resolution + SQLite cache. ✅ live 2026-07-02
  (`tools/subject-resolution/` — cache-first resolver, pull sheets, ingest gates).
- **D** — Photos tab wiring (after photo-organizer decisions land).
