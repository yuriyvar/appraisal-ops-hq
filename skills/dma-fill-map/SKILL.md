---
name: dma-fill-map
description: Map a Subject-Worksheet HTML to a DataMaster `.dma`'s 1004/UAD fields and emit a "what to enter in DataMaster" list (HTML + JSON), flagging stale/missing/conflicting DM data. READ-ONLY — it never writes the `.dma` (DataMaster owns that file). Use when the user asks to "fill the DM file / .dma", "populate DataMaster from the worksheet", "what do I enter in DataMaster", "map the worksheet to DM", "DM fill-map", or has both a built subject worksheet AND the order's `.dma`. If you are Bob/Cowork (sandboxed), you CANNOT run this against the live OneDrive `.dma` — delegate the run to Code (see delegate-to-code). Does NOT replace the sanctioned DataMaster CSV-import flow; it covers the fields DM doesn't auto-populate.
---

# DM fill-map — worksheet → DataMaster field list (read-only)

Reads the order's `.dma` **read-only** and the subject worksheet, then emits a
field-by-field "enter this in DataMaster" list. **It does not write the `.dma`** —
the standing rule stands (`property-search/references/datamaster-handoff.md`):
*never write `.dma` files directly; only DataMaster creates/edits them.* This tool
just tells you/the appraiser what to type for the fields DM doesn't pull on its own,
and surfaces where DM's imported data is stale, missing, or conflicting.

## When to use vs. not
- **Use** after a subject worksheet exists AND the order already has a `.dma` (DM
  has done its CSV import + record pull). The fill-map closes the gap between the
  worksheet and the form.
- **Not a substitute** for the sanctioned flow: comps still go in via DataMaster
  **CSV import** of Matrix exports (`datamaster-handoff.md`). DM pulls full MLS +
  public records itself; the fill-map only maps the *subject* worksheet fields.
- **Not the write-POC.** `tools/dma-write-poc/` is a separate, **unproven** sandbox
  experiment (byte round-trip + same-length patch). Do **not** use it to fill a real
  order — nothing there is trusted until validated in DataMaster.

## Lane note (READ FIRST if you're Bob/Cowork)
This is a **host Python tool** that reads the live `.dma` from
`C:\Users\yuriy\OneDrive\Documents\DataMaster\` and writes output under
`VDV Appraisals\`. **Cowork is sandboxed and cannot run it against those paths.**
Do not work around that. Instead **delegate the run to Code** (`delegate-to-code`
skill): stage a one-line ask in `interlane/INBOX-for-Code.md` with the `.dma` path
+ worksheet path + desired output path, and Code runs the command below and returns
the artifact. (Code runs it directly on the host.)

## Run it (Code / host — PowerShell)
```powershell
python "appraisal-ops-hq\tools\dma-fill-map\dma_fill_map.py" `
  --dma       "C:\Users\yuriy\OneDrive\Documents\DataMaster\<Subject>.dma" `
  --worksheet "Working Subj & Comps files\<Subject>_worksheet.html" `
  --out       "Working Subj & Comps files\<Subject>_DM-fill-map.html"
```
Stdlib only; run via PowerShell (see Code memory `python-env`). It also writes a
sibling `<out>.json`. Prints a one-line summary: `rows= enter= confirm= manual= unmapped= conflicts=`.

## Output — how to read it
HTML (+ JSON) with one row per worksheet field. Status badges:
| Badge | Meaning | Action |
|---|---|---|
| **ENTER** | Mapped to a DM field, value ready | Type it into DataMaster now |
| **CONFIRM@INSP** | Mapped, but value needs inspection (⚠ / appraiser judgment) | Hold until the inspection confirms it |
| **MANUAL** | No direct 1004 field (narrative / Remarks) | Handle by hand; not a form field |
| **UNMAPPED** | Worksheet label the mapper didn't recognize | Map by hand; consider adding to the tool's `MAP` |
- **"In .dma?"** column = whether that value already appears in the `.dma` blob
  (so stale/missing data is visible at a glance).
- **Red "Reconcile first" box** = auto-flagged conflicts, e.g. DM imported a
  different bedroom count than the worksheet, or the current listing's MLS# is
  absent from the `.dma` (DM holds an older record → re-pull in DataMaster). See
  quirks **DMA-001** (.dma structure) and **DMA-002** (stale MLS) in
  `property-search/references/data-quirks.md`.

## Hard rules
- **Read-only on the `.dma`.** Never edit it; the tool only reads.
- **Output carries client values → keep it under `C:\Users\yuriy\VDV Appraisals\`,
  NOT in the repo.** (`Working Subj & Comps files\` is the standing spot.)
- **Never have Code submit/certify the appraisal** — USPAP human gate (per
  `delegate-to-code`). The fill-map is data prep only.

## Related
- Tool: `tools/dma-fill-map/` (this skill wraps it) · decoder it builds on:
  `tools/dma-decoder/` (read-only protobuf wire-walker).
- `property-search/references/datamaster-handoff.md` — the sanctioned CSV-import flow + "never write .dma" rule.
- `property-search/references/data-quirks.md` — **DMA-001**, **DMA-002**.
- `delegate-to-code` — how Bob hands a host-only run to Code.
