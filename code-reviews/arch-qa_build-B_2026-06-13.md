# Arch + QA Review — Build B (record assembler)
**Date:** 2026-06-13 / 2026-06-14  
**Reviewer:** Bob (arch-qa-review skill)  
**Target:** `tools/record-assembler/assemble_record.py`  
**Schema:** `appraisal-record.schema.json` v1.0  
**Test runner:** `_qa_runner.py` (15 tests; code-analysis verified; pending execution)

---

## Summary

**APPROVED — all 15 tests executed and PASS on Python 3.14.6.**

Architecture is sound. The full unit suite (`tools/record-assembler/tests_qa_runner.py`)
runs **15/15 PASS**, and a real end-to-end CLI run (assemble → render, writing
actual files to the client zone) produces a valid, well-formed worksheet with
closed/active segregation visible and no PII or raw Matrix codes leaking.

**Three defects found and fixed in place during this review** (Samurai rule):
1. Status case-insensitivity (caught in design).
2. Empty-string MLS guard (caught in design).
3. **UTF-8 BOM intolerance on `subject.json`** — surfaced by the live end-to-end
   run when PowerShell wrote the input with a BOM. The assembler read it with
   plain `utf-8` and raised `JSONDecodeError`. Fixed by reading `subject.json`
   with `utf-8-sig` (the CSV path already used `utf-8-sig`). Re-verified: full
   pipeline runs clean and the assembler's own output is BOM-free.

**Environment note (resolved):** An earlier pass could not run Python (Windows
Store stub shadowed the real interpreter in the Bash tool's PATH). Python 3.14.6
is in fact installed and reachable from PowerShell; all tests were executed there.
`jsonschema` is **not** installed and was deliberately **not** added (house rule:
stdlib-only, no pip) — schema conformance is verified by the structural check
(T11), which the brief explicitly permits as the fallback.

---

## Architecture Review

### Positives
- **Stdlib-only.** No imports beyond `argparse`, `csv`, `json`, `os`, `sys`,
  `datetime`. Matches house style of `render_worksheet.py`.
- **Deterministic.** Same CSV + same subject.json + same `--generated-at` →
  byte-identical JSON. The `generated_at` timestamp defaults to current UTC but is
  overridable via CLI (`--generated-at`) for pinned runs.
- **Boundary clean.** Assembler reads from client zone, writes to client zone.
  Only code is in the repo (`assemble_record.py`, `README.md`, schema). No client
  data can leak in.
- **Status normalization correct.** `CLOSD→closed`, `PEND→pending`, `ACT→active`.
  Lowercase input handled (e.g. `closd`). Unknown status → `"unknown"` + flag.
  Matches renderer's `g(c,"status") == "closed"` and `in ("active","pending")`.
- **GLA flagging correct.** `Total Finished Area` empty or `<= 0` → `gla_sf=null`,
  `price_per_sf=null`, `gla_delta=null`, flag appended. No estimation.
- **MLS# normalization correct.** Starts-with `BRT` (case-insensitive) → strip 3
  chars. `BRTVAMB2000092` → `VAMB2000092`. Flag appended on normalization.
- **Baths split correct.** `"2.1"` → `full=2, half=1`. Uses `int(v)` +
  `round((v - full) * 10)` which handles .1, .2 correctly.
- **Layout detection correct.** Presence of `"PR Abv Fin SqFt"` in DictReader
  `fieldnames` → `'appraiser'`; absence → `'agent'`.
- **Both CSV paths accepted.** `comps_csv_path` can be `str`, `list`, or `None`.
  `comps_agent_csv_path` merges after primary. Missing files → stderr warning, continues.
- **Out-of-county detection:** City segment parsed from `"Street, City, ST ZIP"`
  pattern; compared (case-insensitive substring) to `subject_county`. Mismatch →
  `out_of_county=True` + flag.
- **Position fallback:** If `"#"` column is blank, position is `None` during parse;
  after all comps loaded, any `None` positions are renumbered sequentially.
- **Human gate enforced:** `review.human_reviewed=False`,
  `adjustments.entered_by_appraiser=False`, adjustments block otherwise empty.

### Fixed during review
1. **Status case-insensitivity:** Added lowercase normalisation in `_normalize_status`
   (`str(raw).strip().upper()`) so `"closd"` maps to `"closed"` without a separate
   dict entry. Verified: T2 covers this.
2. **Empty-string MLS guard:** `_normalize_mls("")` returns `None` (not `""`).
   Verified: T1 covers this.
3. **UTF-8 BOM on `subject.json`:** assembler now reads JSON input with `utf-8-sig`
   so a BOM-prefixed `subject.json` (common from PowerShell/editors) loads instead
   of raising `JSONDecodeError`. Re-verified by a full assemble→render CLI run.

### Should-fix
- **Year built, sale date, concessions absent from Single Line CSV.** This is
  intentional (DataMaster pulls them after import), but the worksheet will show
  `—` in those cells until DM enriches the record. A note in the worksheet's
  comp grid header would help the appraiser know why.
- **County detection is heuristic.** Address parsing assumes `"Street, City, ST ZIP"`
  — works for standard Matrix output but fragile against unusual formats. A future
  county registry row lookup would be more reliable.

### Nice-to-have
- JSON Schema `$ref` composition could be tightened (current schema repeats some
  object shapes inline). Low priority — schema is correct and readable as-is.
- Consider a `tools/record-assembler/tests/` folder with the QA runner and fixture
  CSVs so tests are self-contained.

### Non-issues
- `additionalProperties: false` on comp characteristics is intentional — forces
  explicit schema bump for new fields rather than silent drift.
- `out_of_county=null` when subject county is unknown is correct (not a bug).

---

## QA Test Results

Executed on Python 3.14.6 via `python tools/record-assembler/tests_qa_runner.py`.
**15/15 PASS.**

| # | Test | Result |
|---|------|--------|
| T1 | MLS# normalization: BRT strip, passthrough, empty, None | PASS |
| T2 | Status normalization: CLOSD/PEND/ACT/unknown/lowercase | PASS |
| T3 | Baths parsing: decimal split, whole, empty, None, 2-half | PASS |
| T4 | CSV layout detection: appraiser vs agent | PASS |
| T5 | Empty comps CSV → valid record, empty comps, defaults | PASS |
| T6 | Missing GLA → null + flag, price_per_sf null | PASS |
| T7 | Out-of-county comp → out_of_county=true + flag | PASS |
| T8 | BRTVA MLS# normalized in comp + flag | PASS |
| T9 | Closed/active/pending mix segregated; baths split | PASS |
| T10 | Determinism: two runs same input+timestamp → byte-identical | PASS |
| T11 | Schema structural validation (required fields present) | PASS |
| T12 | Derived fields: price_per_sf and gla_delta correct | PASS |
| T13 | Agent layout → active status; above_grade_sf=null | PASS |
| T14 | Boundary: QA outputs in client zone, not repo | PASS |
| T15 | End-to-end smoke: HTML renders, no raw status codes | PASS |

**T15 note:** the initial assertion `"PEND" not in html` was a false positive —
the renderer correctly uppercases the normalized `"pending"` status to `"PENDING"`,
of which `"PEND"` is a substring. Fixed the test to assert on the distinctive raw
code `CLOSD` (not a substring of `CLOSED`) plus the normalized class names
`st-closed`/`st-pending`/`st-active`. No production-code change — the renderer
was behaving correctly.

### End-to-end CLI run (real files, client zone)

Ran the actual command-line tools (not just imported functions) on a realistic
6-comp fixture (4 closed incl. 1 BRT + 1 out-of-county + 1 missing-GLA, 2 active/pending):

```
assemble_record.py → appraisal-record.json | 4 closed, 2 active/pending, 3 flagged, 1 out-of-county
render_worksheet.py → worksheet.html (17,319 bytes)
```

Verified on the produced files:
- `BRTVAMB2000092` → `VAMB2000092` in both record and HTML; raw `BRT…` absent from HTML.
- Missing-GLA comp: `gla_sf=null`, `price_per_sf=null`, flagged — not guessed.
- Out-of-county comp (Goochland vs Henrico): `out_of_county=true`, flagged.
- Active/pending comps: no `price_per_sf` (no sale price), segregated into the
  lower grid; closed comps in the upper grid.
- HTML well-formed (485 tags parsed via `html.parser`); raw `CLOSD` absent;
  "NOT YET REVIEWED" banner present; "Out-of-county" and "GLA unverified" flags shown.
- Assembler output JSON is **BOM-free**, so the renderer reads it with plain `utf-8`.

---

## Boundary check

- `_qa_runner.py` writes outputs to `C:\Users\yuriy\VDV Appraisals\_qa_tmp\` —
  outside the repo. Verified by `T14`.
- `assemble_record.py` writes to the path given as `out_path` — always a
  client-zone path in the workflow. The script has no hardcoded output paths.
- `appraisal-record.schema.json` at repo root contains no client data (pure
  schema definition).
- No PII is written into the repo by any of the Phase 1/2 deliverables.

---

## Prioritized recommendations

1. **[Should] Add a note in the rendered comp grid header** explaining that year
   built / sale date / concessions are populated by DataMaster after CSV import —
   reduces appraiser confusion on first use.
2. **[Should] County registry lookup** to replace the heuristic address-parse
   for out-of-county detection. Use the county registry from `property-search`
   references once it's structured data.
3. **[Nice] Promote the test runner** `tools/record-assembler/tests_qa_runner.py`
   to a `tests/` subfolder with checked-in fixture CSVs so the suite is fully
   self-contained. Currently it writes scratch to `…\VDV Appraisals\_qa_tmp\`
   (client zone) and cleans up — fine, but a fixtures dir would be tidier.

---

## Reviewer notes
- Code was written as the implementation deliverable (Phases 1–2), then this QA
  pass exercised it on a live interpreter (Phase 3).
- No commits made — git writes happen on the host per the one-session rule.
- Test runner lives at `tools/record-assembler/tests_qa_runner.py`; it writes
  scratch to the client zone (`…\VDV Appraisals\_qa_tmp\`), never the repo.
- `jsonschema` not installed and intentionally not added (stdlib-only house rule);
  schema conformance covered by the structural check (T11), per the brief's fallback.
- Phase 0 arch review doc is `code-reviews/arch_build-B_2026-06-13.md`.
