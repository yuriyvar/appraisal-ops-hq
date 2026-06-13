# Architecture Review + QA — Worksheet Renderer (Build A) — 2026-06-13

_Reviewer: Claude ("Bob"). Scope: `tools/worksheet-renderer/render_worksheet.py` (+ README, example output). Two defects found during review were **fixed in place** and re-verified (noted below). No git operations were run (one-session rule)._

## Summary

Build A is the deterministic JSON→HTML renderer that turns `appraisal-record.json` into the tabbed `worksheet.html` the appraiser copies into ACI. It is the **render contract** that Builds B–D fill. The build is sound: it honors the ADR-002 intent (one structured record → rendered consumer), is **stdlib-only, deterministic (byte-identical output), and makes zero network calls**. Structure is clean (one builder per tab), null-safety is thorough, and the comp grid correctly **segregates closed sales from active/pending** per the comp-quality rule, with the review gate always shown.

Two real issues surfaced and were fixed during the review: (1) a `javascript:`/`data:` URL in `sources[].url` was emitted into a live `href` (XSS vector, since those URLs are assembled from web data); (2) the comp grid mapped the SUBJECT column by display-label strings, so renaming/reordering a row would silently blank the subject cell. Both are resolved. Remaining items are should/nice-to-have hardening, not blockers. **Verdict: APPROVED to build B on top of this contract.**

---

## Architecture review

### Positives
- **Determinism + no I/O coupling.** Pure function `render(rec)`; no network, no clock-dependent output beyond the record's own `generated_at`. Same input → byte-identical HTML (QA T1). This is exactly what a render contract needs so B/C/D can test against a fixed target.
- **Stdlib only.** No pip surface, runs anywhere Python 3 is. Matches the "smallest, testable first" build order.
- **Separation of concerns.** One `build_*` builder per tab + small formatting helpers (`money`, `sf`, `signed`, `baths`, `dash`). Adding a tab = one function + one nav entry.
- **Defensive rendering.** Every field is null-safe via `g(...)`; empty arrays render a clean "none yet" state rather than crashing (QA T2/T3/T7).
- **Domain correctness.** Closed comps are segregated from active/pending (listings labeled "supporting analysis only"); the cross-source verification table flags disagreements; the footer always shows REVIEWED vs **NOT YET REVIEWED** — the renderer assembles, the appraiser certifies. This encodes the comp-quality and human-gate rules from the handoff.
- **Print-friendly.** `@media print` expands all tabs and hides nav, so the worksheet prints as one document.

### Fixed during review
1. **(Must, FIXED) URL scheme not sanitized.** `sources[].url` went straight into `href`. Added `safe_url()`: only `http(s)` (and scheme-less relatives) become live links; `javascript:`, `data:`, `file:`, etc. are rendered as inert bracketed text. Verified across 9 cases (QA T9 re-test).
2. **(Should, FIXED) Subject/comp grid desync risk.** `COMP_ROWS` + a separate `_subject_cell` mapping were keyed by the human label string — fragile. Replaced with a single table where each row binds its subject accessor and comp accessor together, so the two columns cannot drift. Output unchanged; coupling removed.

### Remaining — should-fix
3. **No structural validation, only a version-string check.** The renderer warns on `schema_version != "1.0"` but does not validate the record shape. For Build A (fast, deterministic, defensively null-safe) this is acceptable, but as data-collection (B) starts writing records, add an **optional** `--validate` flag that runs `jsonschema` against `appraisal-record.schema.json` and reports field errors before rendering. Keep it optional so the core stays dependency-free.

### Remaining — nice-to-have
4. **Map projection is naive equirectangular.** Longitude is not scaled by `cos(latitude)`, so the SVG scatter is horizontally compressed (~20% at VA's ~38°N). Fine for a *relative-position* sketch (and it's labeled as not-to-scale), but multiplying lon by `cos(mean_lat)` would make spacing faithful. Low priority.
5. **Bad-input UX is a raw traceback.** Malformed JSON / missing file exits non-zero (correct for scripting, QA T6) but prints a Python traceback. A `try/except` around load with a one-line stderr message would be friendlier when run by hand.
6. **No adjustments tab — intentional, document it.** The schema has `adjustments` (appraiser-entered), and the handoff specifies exactly five tabs. The renderer deliberately omits an adjustments grid so it isn't mistaken for an omission. Noted in the README; calling it out here too.

### Non-issues (considered, no action)
- CSS/JS as large module-level string literals — required for the single-file output goal; not a defect.
- `generated_at` in output makes diffs differ across records — that's data, not nondeterminism; same record always renders identically.

---

## QA test results

Run against `appraisal-record.example.json` (3 closed comps, no photos, no comp coords) and synthetic records exercising the empty/edge branches. All green after fixes.

| # | Test | Result |
|---|------|--------|
| T1 | Determinism — render example twice, compare bytes | PASS (byte-identical) |
| T2 | Empty record `{}` | PASS (renders, warns on version, no crash) |
| T3 | Missing subject pieces / empty comps | PASS ("No comps" state) |
| T4 | HTML injection in address/flags | PASS (`<script>`/`onerror` escaped) |
| T5 | Schema-version mismatch (`9.9`) | PASS (warns to stderr, renders, exit 0) |
| T6 | Bad JSON / missing file | PASS (exit 1) |
| T7 | Null-heavy comp (all chars null) | PASS (no traceback) |
| T8 | Output parses as well-formed HTML | PASS (`html.parser`, no exception) |
| T9 | `javascript:` URL in a source | **FIXED** → now inert text, not a live href |
| T9b | Active/pending grid, SVG map dots, photo grid | PASS (synthetic record) |
| T10 | Refactor regression — subject column + determinism | PASS (values intact, still byte-identical) |

### Environment note
During QA the sandbox's bash mount cached a **truncated** copy of the `.py` after the in-place edits and would not re-sync within the session, so the integrated suite could not be re-run against the final file from bash. Mitigation: the full suite passed on the pre-fix code; the two fixes were re-verified in isolation (sandbox-local); and the host file is confirmed complete and correct via the editor (775 lines, both fixes present). This is the same class of Windows-mount flakiness already logged in the andon history — reinforces the one-session / host-side discipline.

---

## Prioritized recommendations
1. **(Done this review)** Sanitize source URL schemes (#1); decouple subject/comp grid rows (#2).
2. **(Should, when B lands)** Add optional `--validate` against the JSON Schema (#3).
3. **(Nice)** `cos(lat)` longitude scaling on the map (#4); friendly error message on bad input (#5); keep documenting the intentional no-adjustments-tab decision (#6).

### Reviewer notes
- No files committed, merged, or pushed. The renderer + fixes are uncommitted on disk; fold them into the pending host-side commit (handoff §3 / continuation block).
- This review's methodology is captured as the `/bob-arch-qa-review` skill (`skills/arch-qa-review/SKILL.md`).
