# Claude Code build brief — Build B (record assembler) + `/build-worksheet` orchestrator

**For:** Claude Code, working in `C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq`.
**Goal:** close the one gap that blocks end-to-end automation — *nothing assembles a real
`appraisal-record.json` from a live order yet* — then chain the existing pieces into one
runnable flow. **Work the phases in order: Architecture Review first, QA test last.**

## Operating rules (do not violate)
- **Client data NEVER enters the repo.** Order/comp data lives under `C:\Users\yuriy\VDV Appraisals\`
  (e.g. `Comps files\`, per-order folders). Only code/config/skills are committed.
- **`VDV Appraisals` is the system of record; Google Drive is read-only by default**
  (CLAUDE.md cardinal rule #6). Never create/write/copy/move files on GDrive or any external
  cloud without an explicit per-task request. All outputs land under `C:\Users\yuriy\VDV Appraisals\`
  first. If anything is ever written to GDrive without that request: copy into VDV Appraisals,
  verify, then delete from GDrive.
- **Deterministic + stdlib-only** for the assembler (match `tools/worksheet-renderer/render_worksheet.py`
  house style: no network, no pip, same input → same output).
- **Human gate / USPAP:** the agent ASSEMBLES and DRAFTS; the licensed appraiser judges
  adjustments and certifies. Never auto-submit, never write final `adjustments.*`.
- **One Cowork/Matrix session at a time** (the git-corruption andon). Git writes on host only.
- **Confirm before side effects** (downloads, sending, form submits).
- Read `docs/ADR-002` + `docs/ADR-003` and `appraisal-record.schema.json` before designing.
- **Proactive quirk capture applies to you too (CLAUDE.md rule #2):** if you hit any data-source
  exception or important handling detail while implementing/testing, add a row to
  `skills/property-search/references/data-quirks.md` immediately — no reminder needed — and wire its
  fix into the assembler's normalization pass.

---

## Phase 0 — Architecture Review (do this BEFORE coding)
Run the architecture-review pass from `skills/arch-qa-review/SKILL.md` against the *design*
below and the existing contracts. Produce `code-reviews/arch_build-B_<date>.md` answering:
1. **Contract fit** — does the assembler's output validate against `appraisal-record.schema.json`
   v1.0 with no schema changes? List any field the inputs can't fill (leave null, don't invent).
2. **Input reality** — confirm the real input shapes: the DataMaster comp CSV
   (columns documented in `skills/property-search/references/datamaster-handoff.md`) and how
   subject facts arrive from `skills/property-search` (county assessment + portals). Build the
   parser around the *observed* CSV header, not an assumed one.
3. **Boundary** — confirm inputs are read from the client zone and outputs (record + worksheet)
   are written to the per-order folder, never the repo.
4. **Reuse vs new** — the renderer (Build A) and `notes-composer` already consume the record;
   the assembler must produce exactly what they expect. Flag any mismatch.
5. **Decision:** approve or list blockers. Do not start Phase 1 until blockers are resolved.

---

## Phase 1 — Build B: the record assembler
Create `tools/record-assembler/assemble_record.py` (stdlib, deterministic).

**Function:** `assemble(subject_json_path, comps_csv_path, out_path, **order_meta) -> appraisal-record.json`

**Inputs**
- `subject.json` — subject facts (address, identifiers, characteristics, assessment, resolution).
  Define a minimal schema-aligned shape; document it in the tool README.
- `comps.csv` — the DataMaster single-line appraiser CSV in `Comps files\` (parse by the
  documented header; tolerate the two layouts in `datamaster-handoff.md`).

**Behavior (encode the comp-quality rules from SESSION-HANDOFF §8):**
- Map CSV rows → `comps[]` (address, status, distance, identifiers, characteristics, sale).
- **Segregate** `status` closed vs active/pending (don't drop active — mark them).
- **County-tag** every comp; flag out-of-county comps for SOR verification.
- **Never emit unverified GLA** — if GLA is missing/unverified, set null + add a `flags` entry,
  do not guess.
- **Apply the data-quirks registry programmatically.** Read
  `skills/property-search/references/data-quirks.md` and ENFORCE its fixes in code — don't rely on
  a human having read them. At minimum: MLS# `BRTVA…` → strip `BRT`, keep `VA…` (MLS-001);
  Chesterfield ArcGIS `TaxID` `Math.round()` (CHE-002); flag builder-direct / new-construction blanks.
  Structure this as a small, testable normalization pass so new registry rows are easy to wire in.
- Compute derived fields where deterministic (`price_per_sf`, `gla_delta_vs_subject_sf`).
- Set `review.human_reviewed=false`, `adjustments.entered_by_appraiser=false` (leave adjustments empty).
- Stamp `generated_at`, `generated_by="claude-cowork"`, `schema_version="1.0"`.

**Output:** write `appraisal-record.json` to the per-order folder; print path + a 1-line summary.

**Acceptance:** output validates against the schema; round-trips through the renderer to a
valid `worksheet.html`.

---

## Phase 2 — `/build-worksheet` orchestrator
**Already exists** — do NOT recreate: `.claude/commands/build-worksheet.md` (**this is YOUR — Claude
Code's — runtime path**, the automated orchestrator) and `skills/worksheet-builder/SKILL.md` (the
Cowork/Bob interactive path + the canonical deliverable & mandatory completeness gate). Both share one
contract & gate. Your job is to (a) build the `record-assembler` they depend on (Phase 1), and
(b) ensure the `/build-worksheet` command **enforces the completeness gate in code/flow** before render. Confirm the existing command's steps
match what you built; update only to wire in the assembler and the gate. The flow, for an order:
1. **Resolve subject + pull comps** via `skills/property-search` (county/GIS/Matrix; obey the
   one-session rule; MLS#s normalized). Output → subject facts + `Comps files\<addr>_comps...csv`.
2. **Assemble** → `tools/record-assembler/assemble_record.py` → `appraisal-record.json`.
3. **Render** → `tools/worksheet-renderer/render_worksheet.py` → `worksheet.html`.
4. **Draft notes/adjustment hints** via `skills/notes-composer` (templates + playbook),
   leaving slots/judgment for the appraiser.
5. **Hand off** the worksheet + drafts to the appraiser to review, adjust, and certify.
   **Stop there — never submit.**
Each step: state what it's doing, confirm before any side effect, and surface conflicts/flags.

---

## Phase 3 — QA test (conclude here)
Run the full QA pass from `skills/arch-qa-review/SKILL.md` and write
`code-reviews/arch-qa_build-B_<date>.md`. Minimum tests:
- **Schema conformance:** assembled record validates against `appraisal-record.schema.json`
  (use jsonschema if available; else a structural check).
- **Determinism:** assemble twice from the same inputs → byte-identical JSON.
- **Edge inputs:** empty comps CSV; a comp missing GLA (→ null + flag, no guess); an out-of-county
  comp (→ flagged); a `BRTVA…` MLS# (→ normalized); active + closed mix (→ segregated).
- **End-to-end smoke:** real-ish CSV → `assemble_record.py` → `render_worksheet.py` → HTML parses,
  closed/active segregation visible, no PII written into the repo.
- **Boundary check:** confirm nothing under the repo contains client order data after a run.
- Fix cheap defects in place and re-verify (Samurai rule). Conclude with an approve/blockers verdict.

---

## Deliverables checklist
- [ ] `code-reviews/arch_build-B_<date>.md` (Phase 0)
- [ ] `tools/record-assembler/assemble_record.py` + `README.md` + subject.json shape doc
- [ ] `.claude/commands/build-worksheet.md`
- [ ] `code-reviews/arch-qa_build-B_<date>.md` (Phase 3, with test results)
- [ ] Inbox line in `vault/00-inbox.md`; do NOT commit (host-side git per the handoff)

## Pre-req
Repo git must be healthy and committed first (SESSION-HANDOFF §3 + SESSION-SUMMARY must-do).
