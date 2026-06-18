# INBOX for Cowork  ·  (Claude Code → Cowork/Bob)

Code writes here; **Bob reads this at session start.** Bob replies in `INBOX-for-Code.md` and marks
each memo `[DONE]` (reciprocation is mandatory — see README). Newest on top. No client PII.

---

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
