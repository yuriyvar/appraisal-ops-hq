<!-- build-plan: name=bd3-comp-history-recall status=active -->
# Code brief — BD3: historical comp recall (Ops file + .dma corpus index)

> Track 3 of the automation roadmap. YV: index all historical properties; a similar subject
> appraised within the last 12 months → surface that report + its comps as CANDIDATES
> (YV decides — never auto-selected; sale dates re-checked against the current effective date).

## Progress tracker
- [x] Phase 0 — this brief committed
- [x] Phase 1 — Ops-sheet import: 2025+2026 tabs pulled LIVE via Chrome/gviz →
      `Past Reports\_analysis\ops-history\ops-202{5,6}.csv` (client zone); layout is POSITIONAL
      (col0 order-date · 1 order# · 2 client · 3 street · 4 zip · 5 form · 6 due/done ·
      10 appraised value · 11 status) — parser in `comp_history.py` skips the summary junk
- [x] Phase 2 — index builder (SCOPE AMENDED after live recon — see below): filename + mtime +
      Ops join + June-corpus subject facts + comp HINTS → client-zone SQLite. **Structured
      per-comp re-extraction DEFERRED:** the .dma value slots carry unique numeric IDs
      (`3.5[k].1` / `4.5[k].1`, 560 unique in the probe file) but the schema-name entries
      (`3.3[k]`/`4.3[k]`) carry no matching ID — positional pairing provably misaligns, and the
      June extractor that DID pair them was never committed. Reverse-engineering the link is its
      own build day (quirk DMA-004 filed).
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
