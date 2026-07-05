# Brief — Cowork can't write live SQLite over mounted folders (Build C cache dead letter)

**Date:** 2026-07-04 · **From:** Cowork/Ton · **Order that surfaced it:** 14719 Clover Ridge Ln, Chesterfield VA

## Context
Ran `/resolve-subject`-equivalent on a brand-new address (no existing order folder, so a cache
hit was never in play). `resolve_subject.py`'s `cache_get()` calls `subject_cache._connect()`,
which unconditionally runs `CREATE TABLE IF NOT EXISTS` before any read. That write raised
`sqlite3.OperationalError: disk I/O error` — reproduced on:
- the real client-zone path (`VDV Appraisals\Subject cache\subject-cache.sqlite`, mounted into
  the Cowork sandbox), AND
- the sandbox's own outputs mount (its private scratch dir, also a mounted volume).

Plain-file read/write on both mounts works fine (confirmed: wrote subject.json, pull-sheet.md,
run-log.md straight to the client zone without issue). SQLite READS also work fine over the
mount — I queried `va-gas-providers.sqlite` (an existing file) with a plain `SELECT` with no
error. It's specifically **schema-creation / INSERT** (anything needing SQLite's file locking)
that fails on these mounted volumes. This smells like a FUSE/network-mount limitation on
POSIX advisory locks, not a data or code bug.

## What this means
**The entire Build-C subject-resolution cache cannot be written from Cowork, on any order,
until this is resolved.** Every Cowork-run order will hit this the same way BD1's provenance
gate would expect (`cached=false` forever from Cowork's side), silently losing the whole point
of Build C (repeat-order speedup) for the Cowork lane specifically.

## What I did this session (workaround, not a fix)
1. Copied `resolve_subject.py` + `subject_cache.py` + `ingest_subject.py` + `county_routing.json`
   + `va-gas-providers.sqlite` into the sandbox's outputs mount (unrelated pre-existing issue:
   `resolve_subject.py` was also reading TRUNCATED via bash on the client-zone mount — see the
   separate `[problem]` inbox entry same date; re-Writing it in place did NOT fix that one, only
   copying to outputs did).
2. Called the resolver's MISS-path helper functions directly (`build_skeleton`, `gas_lookup`,
   `build_pull_sheet`, `build_run_log`) — same shapes/logic as the real tool — **skipping only**
   `cache_get`/`cache_put`. Safe here because this address had never been resolved before, so a
   cache hit was never possible anyway.
3. Filled the skeleton from a live County SOR pull (Chesterfield ArcGIS `ParcelsEnriched`
   FeatureServer, public REST, no auth needed) and ran `ingest_subject.py --out-dir ... --no-cache`
   to get the normalization/gates without the cache write.
4. Flagged the bypass explicitly in `subject.json.flags` and `run-log.md` (step 1 = `[x]` manual;
   step 3 ingest = `[x]` no-cache) so it's visible on the worksheet header, per CLAUDE.md rule 7.

## Ask for Code
1. **Confirm whether the live host (real Claude Code CLI, not sandboxed) has the same limitation**
   against `VDV Appraisals\Subject cache\`. If the host writes fine, this is Cowork-sandbox-only —
   worth documenting in `tools/subject-resolution/README.md` as a lane limitation (Cowork must
   always pass `--no-cache` / equivalent, or delegate cache writes to Code).
2. **If the host has the SAME problem** (unlikely, but check — maybe the DB itself got corrupted
   by a previous partial write), that's a bigger issue: consider whether the cache needs a
   lock-free format (e.g. one JSON file per address, hashed filename) instead of SQLite, since
   plain-file writes are reliably fine on this environment and SQLite specifically is not.
3. Either way, update `tools/subject-resolution/resolve_subject.py` / SKILL docs with whichever
   answer applies, so future Cowork sessions don't have to re-discover this.

## Guardrails followed
- No client git/`.claude/` writes attempted (this brief + the vault inbox entries are the only
  repo-side writes Cowork made).
- No cache data was fabricated — the bypass only skips the cache step; all subject VALUES are
  either real (pulled from the live ArcGIS feed) or explicitly null+flagged.
- No PII beyond a public tax-record owner name already visible on the county's own public GIS
  (Jenkins Joseph Edward Estate) — consistent with what a licensed appraiser would see anyway.
