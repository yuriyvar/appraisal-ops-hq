# /appraise — THE order-lane entry point (also triggered by `#appr`)

One door into appraisal work. No portal browsing, no MLS pulls, no worksheet edits
before Step 1 has answered HIT or MISS — improvised processes are what the
provenance chips and the weekly audit catch. (YV: "Discipline prevents entropy.")

## Step 0 — Gates (skip nothing)
- `/prep-today` triage has run this session (WIP rule — never work done/submitted orders).
- Skills reviewed per CLAUDE.md 1.3 (worksheet-builder, property-search, notes-composer).

## Step 1 — Resolve the subject (ALWAYS first)
`/resolve-subject` → `tools/subject-resolution/resolve_subject.py "<address>" --county <X>
--out-dir "<order folder>" [order meta]`
- **HIT** → subject.json + run-log.md written; re-verify the staleness FLAG lines; go to Step 3.
- **MISS** → skeleton + pull-sheet.md + run-log.md written; go to Step 2.
- **Unknown county** → `tools/subject-resolution/add_county.py` (adds registry + routing
  together), then re-run. Never hand-edit just one of the two files.

## Step 2 — Pull + ingest (MISS only)
Work `pull-sheet.md` top to bottom (**MLS → County SOR → Zillow → gas**; unknowns stay null —
never guessed). Tracked fields: per-source values into `source_values`, county-vs-MLS conflicts
per the sheet's variance protocol (`variance_notes` reason or County rules; triage chip either way).
Chesterfield/Hanover: `fetch_arcgis.py` may pre-fill parcel basics first.
Tick run-log step 2 by hand, then:
`ingest_subject.py <skeleton> --out subject.json --source "<vendor> pull"` (ticks step 3,
caches the subject — the next order on it is a HIT).

## Step 3 — Comps
`property-search` SKILL (registry routing, MLS-first, both-Navica-accounts where flagged,
GLA-band / 12-mo / ML#+TaxID gates). Tick run-log step 4.

## Step 4 — Assemble + render
`/build-worksheet`: `assemble_record.py` → `render_worksheet.py` (Tax-ID gate must exit 0).
Steps 5–6 tick when their artifacts exist. Worksheet goes to the appraiser — NEVER
submit/certify (USPAP; hard rule).

## Non-negotiables
- A subject.json not produced by ingest gets flagged "produced outside standard work"
  on the worksheet header — YV will see it. Don't create one by hand.
- Unchecked run-log boxes on finished orders surface in the weekly `/review` audit.
- Client data never enters the repo. Fail loud, never guess (CLAUDE.md #7).
