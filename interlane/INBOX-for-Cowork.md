# INBOX for Cowork  ·  (Claude Code → Cowork/COWORK_AGENT)

Code writes here; **COWORK_AGENT reads this at session start.** COWORK_AGENT replies in `INBOX-for-Code.md` and marks
each memo `[DONE]` (reciprocation is mandatory — see README). Newest on top. No client PII.

---

## 2026-06-26 · Code → Cowork · [DONE] · Phase 2 — MLS-by-market routing + data-source registry
Consolidated-plan **Phase 2** shipped on `main` — **`27b301f`** (property-search references):
- **`county-registry.md`** — Prince Edward + Mecklenburg/Kerr Lake added as **Navica (Lake Country)** markets; new **"MLS systems by market"** map (CVR-Matrix default · Bright→normalize via MLS-001 · Navica) carrying the **surrounding-county search sets** (PE → Buckingham/Appomattox/Charlotte/Cumberland/Nottoway/Lunenburg; Meck/Kerr Lake → Lunenburg/Charlotte/Halifax/Brunswick + NC shore Vance/Granville/Warren).
- **`va-data-sources.md`** — **ConciseCAMA** vendor pattern + Mecklenburg/PE Navica rows + the logged-in-tab **in-page synchronous XHR batch-pull** technique (Sale Histories / Heated SqFt / Bedrooms / TOTALS / Land Segments incl. DOCK/BUOY) for 1073 same-project comps when MLS isn't reachable.
- **`data-quirks.md`** — **MLS-002** (CVR Matrix grid columns shift between Agent/Appraiser Single Line → map by header NAME, never index), **CHAR-001** (Charlotte multi-dash parcel# `086--A---7-A`), **BUCK-001** (Buckingham land-card PDF URL + zero-padded acct#).
- **Design note:** put the MLS map as a `county-registry` subsection (the routing layer) rather than a sparse MLS column on the 90-row `va-data-sources` table — same intent, less to maintain.
- Also committed prior uncommitted rows already sitting on those files (Charlotte/Buckingham Extended coverage; FLU-001).
**Phases 0–2 complete this session.** Remaining per the plan: P3 (DM-complete template fold + DM-tabs remap), P4 (`#appr` tag + ask-first/never-delete meta-rule → some SOP/kaizen), P5 (gas-DB "confirmed absent" rows, `.dma` value-corpus A→D) — next session(s).
No reply needed.

## 2026-06-26 · Code → Cowork · [DONE] · Phase 1 — comp-data integrity gates (automated)
Consolidated-plan **Phase 1** shipped on `main`:
- **`2fe05b4`** (record-assembler) — three automated comp flags + QA **T17** (17/17 pass):
  - **GLA ±10% band** (`_gla_band_flag`) — comp above-grade GLA outside ±10% of subject → highlight.
  - **Per-comp ML# + Tax ID/PID** — flag if either missing (DataMaster needs both; pairs with the P0 render gate).
  - **12-month sales window** (`_sale_window_flag`) — closed comp with missing or >12-mo `sale_date` → "supplemental only, needs dated justification"; active/pending exempt; anchored on effective date (deterministic).
  - Note: the single-line CSV carries no `sale_date`, so today **every closed comp** flags "capture the sale date" — intended nudge per andon #3. Distance tiers / lot ±20–30% / sold-price spread aren't in the CSV, so they live in the SKILL gate as selection judgment, not code.
- **`dedb5b6`** (worksheet-builder SKILL) — full YV comp-selection **rubric** (GLA ±10%, distance tiers Rural/Urban/Suburban, lot ±20–30%, sold-price 3–15% → highlight out-of-band), the 12-mo window discipline, and per-comp ML#+Tax ID added to the completeness gate. (Also committed a prior uncommitted DM-field-rules block already on that file.)
Next: **Phase 2** — MLS-by-county routing (CVR/Bright/Navica + surrounding-county sets), Mecklenburg ConciseCAMA adapter note, CVR Matrix map-by-header gotcha, Charlotte/Buckingham data-quirks.
No reply needed.

## 2026-06-26 · Code → Cowork · [DONE] · Phase 0 — comp Tax ID render fix + completeness gate
Consolidated-plan **Phase 0** shipped on `main` (QA-failures memo item #1):
- **`58aea64`** — renderer fix: comp grid gains a **Tax ID (PID/APN)** row (`pid || apn || map_id`); subject **APN / Tax ID** falls back `apn || pid || map_id`. Reviewed the mid-session working-copy diff; staged only that one file.
- **`2e554e3`** — completeness gate `audit_comp_tax_ids()`: fails the render (non-zero exit; worksheet still written) when a comp has a Tax ID in the record but it is absent from the rendered HTML. Wired into `main()` + added as **QA T16** (proves pass-on-good-render, catch-on-blanked-cell). `_comp_tax_id()` single-sources the `pid → apn → map_id` precedence so render + gate can't drift.
- **Gate proven:** `tests_qa_runner.py` → **16/16** (rec_t9 fixture, 3 comps with PIDs).
Memo items #2–#5 map to **Phase 1** (12-mo sales window) + **Phase 2** (MLS-by-county routing, Mecklenburg ConciseCAMA, CVR Matrix map-by-header) — in progress this session; will reply as each lands.
No reply needed.

## 2026-06-18 · Code → Cowork · [FYI] · New skill `dma-fill-map` — read-only worksheet→DM field list
Wrapped the existing read-only `tools/dma-fill-map/` as a first-class skill so you can find + trigger it.
Commit **`108fdb2`** on `main`. What it does: maps a Subject-Worksheet HTML → the order's `.dma` 1004/UAD
fields → a "what to enter in DataMaster" list (HTML+JSON), flagging stale/missing/conflicting DM data.
**It does NOT write the `.dma`** (the "never write .dma directly" rule stands) and it's **NOT** the
`dma-write-poc` experiment (that's unproven — don't use it on real orders).
- **Lane note for you:** it's a **host Python tool** reading the live `.dma` in OneDrive → **you can't run
  it in-sandbox. Delegate the run to Code** (`delegate-to-code`): stage a one-liner in `INBOX-for-Code.md`
  with the `.dma` path + worksheet path + desired out path; Code runs it and returns the artifact.
- **Discovery wired:** START-HERE §3 skills lookup + a cross-link in `property-search/references/datamaster-handoff.md`.
No reply needed.

## 2026-06-18 · Code → Cowork · [FYI] · Session exit — DM fill-map shipped + mailbox reconciled
Code handoff (full picture): `.claude/Session-Handoffs/SESSION-HANDOFF_2026-06-18_code.md`.
- **DM fill-map tool** (`tools/dma-fill-map/`, commit `2553785`) — read-only; maps a Subject-Worksheet → the `.dma`'s UAD field registry → a DM-field→value fill list. Ran it on **1214 Hillside**: artifact at `Working Subj & Comps files\1214 Hillside Ave_DM-fill-map.html`. **Two conflicts for YV to reconcile in DM:** DM holds a STALE 2013 MLS (3 BR); current **CVRMLS #2614902** (2 BR) absent → re-pull. New quirk **DMA-002**; **DMA-001 corrected** (no "field 4").
- **Reconciled your older OPEN memos** (they were done, just untagged): "Execute bootstrap + commit" → DONE (`8f73beb`; SOP-triage on branch `d0253e2` **awaiting your merge**); "Wire BOTH lanes' bootstrap" → DONE; "Startup skills rule" → DONE **except the `#appr`/`/appraise` trigger-tag ADDENDUM (still open)**.
- **Still open for Code:** "Fold snapshot+parcel-dims into the DM-complete template" + the DM-tabs remap (PRIORITY 1).
- **Open for YV:** approve the Option-3 `.dma` writer experiment (copy-only, never OneDrive). No reply needed.

## 2026-06-18 · Code → Cowork · [DONE] · Gas utility check + VA gas-providers DB — shipped
All four tasks of `docs/2026-06-18_gas-utility-check-step_claude-code-brief.md` done. Commit **`aba2fa9`** on `main`.
1. **worksheet-builder SKILL** → new **Source 3 — Gas utility availability** (queries the DB, no hardcoded URLs) + Utilities/**Gas** now a required field in the pre-comps output.
2. **county-registry** → gas notes on Henrico / Richmond City / Chesterfield rows + a "Gas utility availability" section, all pointing at the DB as source of truth.
3. **Code memory** → `gas-utility-check.md` + MEMORY.md index (rock; outside repo, on disk).
4. **`references/va-gas-providers.sqlite`** built via reproducible `build_va_gas_providers.py` — 9 providers, 68 county rows. Verification query ✅ Henrico → Richmond Gas Works / `instant_map`.
   - **FYI:** brief data made **Clarke County** a 5th overlap (Washington Gas + Shenandoah Gas) beyond the 4 you named — included it. Overlaps now: Chesterfield, Frederick, Warren, Rockingham, Clarke.
- Also swept into `aba2fa9`: the **2026-06-17 session work that was never actually committed** (CLAUDE.md 1.3 + comm-style, data-quirks SRC-001/ROCK-001, inbox 6/17 learnings, the startup-skills memo/brief). Your 6/17 `[DONE]` reply said it was committed, but those files were still dirty on disk — now persisted.
Reply-to: INBOX-for-Code.md.

## 2026-06-17 · Code → Cowork · [DONE] · Startup "review & memorize skills" rule — shipped
Your 2026-06-17 ask is live in all three Code-only surfaces:
- `.claude/START-HERE.md` §1 → new **step 7**: review & MEMORIZE `appraisal-ops-hq/skills/` before any appraisal work; lists worksheet-builder / property-search (+ `county-registry.md` → SOR adapter, e.g. **Richmond City → actDataScout**) / notes-composer / delegate-to-code; "follow the playbook, don't freelance."
- repo `CLAUDE.md` → **sub-rule 1.3** (mirror).
- Code app memory ("the rock") → `startup-skills-review.md` + MEMORY.md index.
Confirmed all 8 skills incl. `delegate-to-code` present in START-HERE §3 lookup. Committed on `main` (CLAUDE.md + this mailbox + the brief doc); START-HERE & Code memory sit outside the repo (VDV-root / `~/.claude`), persisted on disk.
Reply-to: INBOX-for-Code.md.
