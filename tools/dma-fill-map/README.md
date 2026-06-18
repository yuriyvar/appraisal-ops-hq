# dma-fill-map (read-only)

Matches a **Subject-Worksheet HTML** against a **DataMaster `.dma`**'s field vocabulary and
emits a *"what to enter in DataMaster"* list. **It never writes the `.dma`** (writing is a
separate, sandboxed POC — see below). This is the safe "Option 2" bridge between the
worksheet and DM.

## What it does
1. Reads the `.dma` **read-only** via `../dma-decoder/dma_decode.py`:
   - field 3 → DM's 1004/UAD field **registry** (e.g. `YearBuilt`, `GasPublic`, `AboveGradeGla`);
   - fields 7–10 → everything DM **already imported** (CoreLogic + MLS RESO + deed history),
     as key/value pairs (see data-quirks **DMA-001**).
2. Parses the worksheet's **Subject** + **History** panels (`td.f` / `td.v` / `td.s` rows).
3. Maps each worksheet field → the DM registry field(s) it belongs in (curated table in `MAP`).
4. Tags each row: **ENTER** (ready) · **CONFIRM@INSP** (⚠ inspection) · **MANUAL** (no 1004 field /
   appraiser narrative), and whether the value is **already in the `.dma`** (so stale/missing data shows).
5. Auto-flags headline **conflicts** (e.g. DM bedroom count vs worksheet; current MLS# absent → DMA-002).
6. Writes an **HTML + JSON** fill-map.

## Usage
```powershell
python tools\dma-fill-map\dma_fill_map.py `
  --dma "C:\Users\yuriy\OneDrive\Documents\DataMaster\<Subject>.dma" `
  --worksheet "C:\Users\yuriy\VDV Appraisals\Working Subj & Comps files\<Subject>_worksheet.html" `
  --out "C:\Users\yuriy\VDV Appraisals\Working Subj & Comps files\<Subject>_DM-fill-map.html"
```
Stdlib only. Run via PowerShell (memory: `python-env`).

## Rules
- **Output goes under `VDV Appraisals\` (client zone), NEVER the repo** — it carries client values.
- The `.dma` is read **only**. Reads from OneDrive are fine; nothing is ever written there.
- The curated `MAP` covers the standard 1004 Subject + History worksheet fields; unrecognized
  labels render as `unmapped` — add them to `MAP` when a new worksheet field appears.

## Related
- `../dma-decoder/` — the read-only protobuf decoder this builds on (DMA-001).
- Quirks: **DMA-001** (.dma structure), **DMA-002** (stale MLS import) in
  `skills/property-search/references/data-quirks.md`.
- Worksheet source: `skills/worksheet-builder/`. DM field list: `../dm-collection-sheet/`.
- **Writing a `.dma` (Option 3)** — not built. Any POC must operate on a **copy under
  `VDV Appraisals\`**, write only a few unambiguous free-text fields, and be validated by
  opening in DataMaster. Never the live OneDrive file.
