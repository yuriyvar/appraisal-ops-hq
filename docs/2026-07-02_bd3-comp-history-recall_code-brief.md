<!-- build-plan: name=bd3-comp-history-recall status=active -->
# Code brief — BD3: historical comp recall (Ops file + .dma corpus index)

> Track 3 of the automation roadmap. YV: index all historical properties; a similar subject
> appraised within the last 12 months → surface that report + its comps as CANDIDATES
> (YV decides — never auto-selected; sale dates re-checked against the current effective date).

## Progress tracker
- [x] Phase 0 — this brief committed
- [ ] Phase 1 — Ops-sheet import (Chrome IS connected this session — pull 2025+2026 tabs live
      to the client zone; `import_ops_history.py` is header-driven + refetchable)
- [ ] Phase 2 — `.dma` indexer: `build_index.py` re-extracts per-comp rows path-aware from
      `C:\Users\yuriy\OneDrive\Documents\DataMaster` (READ-ONLY; 194 files) → client-zone SQLite
- [ ] Phase 3 — recall wiring: resolver queries the index (county + GLA ±15%, ≤12 mo) →
      "PRIOR WORK" section on the pull sheet / cache-hit output; QA
- [ ] Phase 4 — wrap: README · SKILL/command notes · refresh ritual · inbox · interlane FYI ·
      handoff · tag done + BD3 ticked

## Recon facts (verified this session)
- Decoder: `tools/dma-decoder/dma_decode.py` (stdlib wire-walker; `decode_dma()` → path tree,
  `extract_schema_names()`); .dma = ZIP(FileVersion, Appraisal-protobuf). **READ-ONLY law.**
- The 2026-06-19 corpus extraction (`corpus_values_raw.json`, 113 files) is name→ONE-value —
  repeated comp rows were flattened, so BD3 re-extracts path-aware. Decoded names include the
  SUBJECT card (PROPERTY_* / COUNTY / APN / BLDG_ABOVE_GRADE_SQFT / YEAR_BUILT / STYLE / BEDROOMS
  / deeds) AND the Matrix comp-grid columns (`Address · Sales Price · Total Finished Area ·
  Status · ML # · PID · Distance · Subdivision …`).
- **No report/effective date inside the .dma** → file mtime = approximate report date (flagged
  "approx"); the Ops sheet carries the real order dates — the two sources JOIN on address.
- Comp SALE DATES are absent (single-line export never has them) → candidates always carry
  "re-verify the close date in MLS before use" — consistent with the 12-mo INFO-flag rule.
- Ops file: Google Sheet `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`, tabs 2026 (gid 1096625839) + 2025;
  pull via the logged-in Chrome session `/gviz/tq?tqx=out:csv&...`. GDrive READ is allowed;
  exports land in the client zone (`Past Reports\_analysis\ops-history\`), NEVER the repo.

## Locked constraints
1. Index DB + sheet exports live in the CLIENT zone
   (`C:\Users\yuriy\VDV Appraisals\Past Reports\_analysis\comp-history.sqlite`); repo gets code
   + synthetic-fixture tests only. Repo-resident DB/output paths raise (Build C pattern).
2. **Never write into the DataMaster folder** (OneDrive) — open files read-only; skip files
   that fail to parse WITH a printed list (fail loud, never silently drop).
3. PII discipline: owner/seller/lender names are NOT indexed; only property facts.
4. Candidates are CANDIDATES: recall output is clearly labeled, never auto-fills the comps
   array; every candidate carries its provenance (which report, which date basis).
5. QA: parser/matcher tested on synthetic fixtures (`*.dma.test` zips in temp — never a real
   `.dma` name); the live 194-file run is a smoke check printing counts only.

## Verify
```powershell
python "appraisal-ops-hq\tools\comp-history\tests_comp_history.py"                # new runner green
python "appraisal-ops-hq\tools\subject-resolution\tests_subject_resolution.py"   # 19/19 intact
python "appraisal-ops-hq\tools\comp-history\build_index.py" --smoke              # live counts, read-only
```
