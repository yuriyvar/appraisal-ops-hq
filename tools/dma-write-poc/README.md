# dma-write-poc — DataMaster `.dma` write experiment (SANDBOX)

Tests whether a **hand-edited `.dma` copy round-trips through DataMaster**. This is the "Option 3"
probe from the 2026-06-18 Code handoff — **not** a production writer.

## Hard rules
- **Never the live OneDrive file.** `--out` is guarded: it must be under `VDV Appraisals\` and must
  NOT contain `onedrive`. Reads may come from OneDrive (the source `.dma`); writes go to the copy only.
- **Same-length only** for `patch` — replaces value bytes in place, so there is **no protobuf
  length-prefix surgery** and zero structural change. (Arbitrary-length writes would need a real
  re-encoder; not built until the round-trip is proven.)
- The zip is rewritten preserving entry names, order, and per-entry compression. (Python's DEFLATE
  level differs from DM's, so the *file* is a few hundred bytes larger though the *content* is identical.)

## Commands
```powershell
$t = "appraisal-ops-hq\tools\dma-write-poc\dma_write_poc.py"
python $t inspect   --src "<copy>.dma" --find "Sterlingwwod"     # list entries + count a string
python $t roundtrip --src "<copy>.dma" --out "<copy>.RT.dma"     # rezip, blob byte-identical
python $t patch     --src "<copy>.dma" --out "<copy>.PATCHED.dma" --old "Sterlingwwod" --new "Sterlingwood"
```
Each command verifies itself (blob identity / replacement count / decode-leaf stability via
`../dma-decoder`). Stdlib only; run via PowerShell.

## The experiment (what we still need DM to tell us)
1. Open the **`.RT.dma`** (byte-identical content) in DataMaster → does DM accept a Python-rewritten
   zip container at all?
2. Open the **`.PATCHED.dma`** → does it open AND does the legal description show the corrected
   `Sterlingwood`? That answers whether DM re-derives form values from the source records we edited
   (fields 7–10) — or caches/ignores them (`HumanModifiedYN`). See data-quirks **DMA-001**.

If (1) fails → blocker is the zip container (try matching DM's exact bytes). If (1) passes but (2)
doesn't surface → writing must target a different record/flag, not just the string. **YV validates in
DataMaster; nothing here is trusted until then.**

## Related
- `../dma-decoder/` (read-only decode), `../dma-fill-map/` (read-only worksheet→DM mapping).
- Quirks **DMA-001** (.dma structure), **DMA-002** (stale MLS) in `skills/property-search/references/data-quirks.md`.
