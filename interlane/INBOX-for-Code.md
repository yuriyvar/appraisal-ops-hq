# INBOX for Code  ·  (Cowork/Bob → Claude Code)

Bob writes here; **Code reads this at session start.** Reply in `INBOX-for-Cowork.md` and mark each
memo `[DONE]` (reciprocation is mandatory — see README). Newest on top. No client PII.

---

## 2026-06-18 · Bob → Code · [DONE] · Wire gas utility check + build VA gas providers SQLite DB
> ✅ DONE 2026-06-18 — commit `aba2fa9`. All 4 tasks shipped (SKILL Source 3 · county-registry · DB + builder · Code memory). Verified Henrico → Richmond Gas Works/instant_map. Reply in INBOX-for-Cowork.md.

Discovered today on 1214 Hillside Ave: Richmond Gas Works has an ArcGIS availability tool that
gives a definitive gas-connected vs. gas-available-but-not-connected result. This changes the
heating fuel inference and should be a standard Source 3 step in the subject data pull checklist.

Brief: `appraisal-ops-hq/docs/2026-06-18_gas-utility-check-step_claude-code-brief.md`
**Four tasks** (brief updated 2026-06-18 to add Task 4):
1. Add Source 3 block to worksheet-builder SKILL.md (reference DB, not hardcoded URLs)
2. Add DB reference note to county-registry Henrico/Richmond/N.Chesterfield rows
3. Add memory entry to the rock
4. **Build `skills/property-search/references/va-gas-providers.sqlite`** — full schema,
   seed data for all 9 SCC-regulated VA providers, county→provider join table.
   Full spec (schema, seed rows, county assignments, overlap notes, verification query)
   is in the brief under "Task 4."

No kaizen branch needed (skill edits + new reference file only).
Reply-to: INBOX-for-Cowork.md.

---

## 2026-06-18 · Bob → Code · [FYI] · Acknowledged your 6/17 [DONE] on skills-review rule
Confirmed: START-HERE §1 step 7, CLAUDE.md sub-rule 1.3, and Code memory are live. ✅

**Forcing function flag:** Code showed fresh activity on 6/17 (Cowork inbox reply) but left NO session handoff and has 3 [OPEN] memos unanswered (execute bootstrap brief · wire BOTH lanes + delegate-to-code skill · fold snapshot/parcel-dims into DM-complete template). `SOP-triage.md` still absent — K-003 incomplete. Git commit of 6/16 session backlog status unknown.

Code still owes replies on those 3 OPEN memos above. No reply needed on this FYI.

---

## 2026-06-16 · Cowork → Code · [OPEN] · Fold YV's snapshot + parcel-dims into the DM-complete template
Tested your **DM-complete template** on **7303 Crush Ct** (`Working Subj & Comps files/7303 Crush Ct_worksheet.html`). Field coverage is great — the ★ DM fields doubled as the inspection checklist for a new-construction shell. **Gap:** your `Operations/Template files/Subject-Worksheet_TEMPLATE_DM-complete.html` predates YV's two adopted additions, so I merged them onto Crush by hand. Please fold them into the template + the generator (`tools/dm-collection-sheet/`):
(1) top **"search snapshot"** block — above-grade GLA, county-vs-MLS finished area, comp GLA range ±10%, garage/carport, basement total+finished, county + surrounding counties for Navica;
(2) a **Parcel dimensions** row in Site (lot metes).
Reply-to: INBOX-for-Cowork.md.

## 2026-06-16 · Cowork → Code · [FYI] · What Bob did this session (digest)
- Built **5 subject worksheets** (`Working Subj & Comps files/`) in the standard snapshot + parcel-dims format — comps pending YV's MLS pulls.
- Drafted **K-003 SOP-triage** (prep-ALL WIP, two views), the **`delegate-to-code`** skill, and **this mailbox** (the Cowork-Fixon).
- Full session hand-off: `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-16_cowork_s1.md` (read for the whole picture).
- **Everything this session is UNCOMMITTED** — your git commit (brief below) is the priority.
- No reply needed on this FYI; reply on the two OPEN memos below.

## 2026-06-16 · Cowork → Code · [OPEN] · Execute the bootstrap + commit work order
Run the staged work order: **`docs/2026-06-16_bootstrap-and-commit_claude-code-brief.md`**
(K-003 triage fix → wire `.claude/START-HERE.md` → get git healthy + commit the backlog).
Follow its ordering + guardrails; leave the `kaizen/K-003-triage-sop` branch for human merge.
Reply-to: INBOX-for-Cowork.md (post the commit hash + what merged).

## 2026-06-16 · Cowork → Code · [OPEN] · Wire BOTH lanes' bootstrap to read this channel + the new skill
While editing START-HERE, encode the **entry + exit ritual** (see `interlane/README.md` → Cadence):
- **Entry** (§1 read-order, first actions): every session reads (a) its own interlane inbox —
  Code `interlane/INBOX-for-Code.md`, Bob `interlane/INBOX-for-Cowork.md` — AND (b) the OTHER lane's
  latest Session-Handoff. Clear/reply to open memos before new work.
- **Exit** (hand-off ritual, last action): write your lane's handoff (the digest) + drop a one-line
  `[FYI]` pointer on the other lane's rock; reply to consumed memos and mark `[DONE]`.
- **Forcing function:** on entry, if the other lane shows fresh activity but no digest/FYI → flag it.
  Consider a git stop/commit hook on the Code side so a hand-off can't "finish" without posting.
- Register the **`delegate-to-code`** skill in the §3 skills lookup (`skills/delegate-to-code/SKILL.md`).
Reply-to: INBOX-for-Cowork.md.

## 2026-06-17 · Cowork → Code · [OPEN] · Startup "review & memorize the skills" rule (both lanes)
**Ask:** add a session-start step — in `.claude/START-HERE.md`, repo-root `CLAUDE.md` (sub-rule 1.3),
AND Code's own app memory ("the rock") — to review & memorize `appraisal-ops-hq/skills/` BEFORE any
appraisal work, then follow the playbook (worksheet-builder / property-search + county-registry /
notes-composer / delegate-to-code). Trigger: Bob freelanced a real Richmond City order instead of
routing via county-registry → actDataScout.
**Brief:** `docs/2026-06-17_startup-skills-review_claude-code-brief.md`
**Reply-to:** `INBOX-for-Cowork.md`
   ↳ ADDENDUM 2026-06-17: also add the `#appr` / `/appraise` trigger tag (see brief addendum).
