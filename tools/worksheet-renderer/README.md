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
- Exits non-zero only on bad JSON / missing file. A schema_version mismatch
  prints a warning but still renders.

Example:
```bash
python tools/worksheet-renderer/render_worksheet.py appraisal-record.example.json \
  -o tools/worksheet-renderer/worksheet.example.html
```

## Output tabs
- **Subject** — characteristics (governing), identifiers, assessment, subject
  resolution, and the cross-source verification table (disagreements flagged).
- **Comp grid** — URAR-style: features as rows, SUBJECT + comps as columns.
  **Closed sales are segregated from Active/Pending** (listings are supporting
  analysis only, per the comp-quality rule). Per-comp flags shown.
- **Sale / Listing history** — subject sales history + current listing; comp
  prior sales.
- **Photos** — card grid; placeholder until the photo-organizer build lands.
- **Map** — inline SVG scatter of subject vs comps from lat/lon (no map tiles,
  to stay deterministic) + a coordinate/proximity table.

## Contract notes
- Renders defensively: every field is null-safe; empty arrays produce a clean
  "none yet" state rather than a crash.
- The footer always shows the **review gate** (REVIEWED vs NOT YET REVIEWED) —
  the renderer assembles data; the licensed appraiser certifies. Nothing files
  automatically.
- Built for `schema_version` **1.0** (`appraisal-record.schema.json`).

## Tested branches
Verified against `appraisal-record.example.json` (3 closed comps, no photos,
no comp coords) and a synthetic record adding an active comp, photos, and
geocoded comps — exercising the active/pending grid, the SVG map, and the
photo grid.

## Next builds (depend on this contract)
- **B** — comp-pull standard work that fills the record automatically.
- **C** — subject-resolution + SQLite cache.
- **D** — Photos tab wiring (after photo-organizer decisions land).
