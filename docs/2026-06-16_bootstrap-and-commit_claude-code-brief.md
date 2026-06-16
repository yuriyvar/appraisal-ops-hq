# Claude Code brief — 2026-06-16: triage-rule fix + bootstrap wiring + commit

**Read at session start.** These are things only Code can do (host git + write access to `.claude/`);
Cowork/Bob is sandboxed out of both. Bob staged the inputs in the repo this session.

Do them in order: **Task 1 (K-003) creates `SOP-triage`; Task 2 wires START-HERE to point at it and
commits everything.** Respect CLAUDE.md cardinal rule #1 (SOP changes on a `kaizen/*` branch; a human
merges) and the one-session git rule (no git writes while another session has the repo open — concurrent
access corrupted git before, the K-002 andon).

---

## Task 1 — Implement kaizen K-003 (triage-rule fix)

Bob staged the package — read first:
- `vault/30-kaizen/K-003-SOP-triage.DRAFT.md` (proposed canonical SOP)
- `vault/30-kaizen/K-003-5whys.md` and `K-003-pdca.md`
- `vault/30-kaizen/kaizen-log.md` (K-003 row)
- top of `vault/00-inbox.md` (the `[problem]` conflict entry + decisions)

PROBLEM: `/prep-today` and the Code memory file `wip-triage-rule.md` say "`Alan to do` → skip / backup."
That conflicts with YV's directive to **PREP ALL in-scope WIP (YV + Alan)** — the YV/Alan note is
SEQUENCING ONLY, never a prep filter. And the rule lived only in Code's app-internal memory, so
Cowork couldn't read or share it → the lanes drifted.

On a branch `kaizen/K-003-triage-sop` (don't edit `vault/20-standard-work` on main; bump version +
change log; then STOP for human merge):
1. Promote the draft to `vault/20-standard-work/SOP-triage.md` from `K-003-SOP-triage.DRAFT.md`.
   Frontmatter: version 0.1, effective <today>, owner Operations, last-kaizen "K-003 (2026-06-16)",
   andon-count 0; delete the DRAFT `status:` line. Keep the two-view model verbatim — View A PREP =
   ALL in-scope WIP (assignee-blind); View B = YV daily finalize/build list.
2. Reword `.claude/commands/prep-today.md` Step 3 to implement View B only: replace
   "`Alan to do` → skip / backup only" with "`Alan to do` → NOT on YV's daily list (Alan finalizes),
   but the order is STILL prepped (SOP-triage View A) — never drop from prep." Add a header line:
   "Implements SOP-triage (vault/20-standard-work/SOP-triage.md) View B; prep scope = View A."
   Leave the hard rule, gviz/Chrome access method, column map, and 10-day scope intact.
3. Update the Code memory rule `~/.claude/projects/C--Users-yuriy-VDV-Appraisals/memory/wip-triage-rule.md`
   to match SOP-triage (two views; Alan prepped, not skipped) and point to the repo SOP as source of truth.
4. In `skills/worksheet-builder/SKILL.md` add a one-line pointer that triage/prep scope follows
   `vault/20-standard-work/SOP-triage.md` (one rule, both lanes).
5. Sanity-check the 0-indexed column map (Status=11, Notes=12) against the live 2026 tab; fix in the SOP if drifted.
6. Update `kaizen-log.md` K-003 status on merge; keep the PDCA Check date (2026-06-30).

---

## Task 2 — Wire the bootstrap + commit the backlog

### A) Wire the bootstrap (Cowork can't write `.claude/`)
Edit `.claude/START-HERE.md` §1 read-order (it's in `.claude/`, not a vault SOP — edit directly; keep
it concise, point don't duplicate):
1. Read the LATEST handoff from BOTH lanes, newest-first:
   - Code lane: `.claude/Session-Handoffs/`
   - Cowork lane: `Operations/Session-Handoffs/` (see its README — naming
     `SESSION-HANDOFF_<date>_<cowork|code>[_sN].md`; one file per session; never edit another's)
2. Before prepping/building any worksheet: read `vault/20-standard-work/SOP-triage.md` and produce its
   two views — View A PREP = all in-scope WIP; View B = YV's day.
3. In §3 "where things are": standard deliverable = the Subject-Worksheet HTML; blank template at
   `Operations/Template files/Subject-Worksheet_TEMPLATE.html`.
4. Register the new Cowork skill in START-HERE's skills lookup table (§3):
   `delegate-to-code` → `skills/delegate-to-code/SKILL.md` (so Bob triggers it whenever he hits a
   Code-only task — git / `.claude/` writes / host ops / kaizen-branch SOP changes).
5. Wire the **interlane mailbox** (`interlane/`, "the Cowork-Fixon") into the read-order: EVERY session
   reads its own inbox first — Code reads `interlane/INBOX-for-Code.md` (and replies in
   `INBOX-for-Cowork.md`, marking memos [DONE]); Bob reads `interlane/INBOX-for-Cowork.md`. Enforce the
   reciprocation rule (see `interlane/README.md`). NOTE: `INBOX-for-Code.md` already has your open memos.

### B) Get git healthy + commit (one-session/one-commit rule is overdue; work is at risk)
With NO other Cowork/Code session writing the repo:
- If a commit is blocked by stale locks, delete all FOUR (documented K-002 andon fix):
  `.git/HEAD.lock`, `.git/config.lock`, `.git/index.lock`, `.git/refs/heads/main.lock` — then retry.
- Stage + commit pending repo work: K-003 package (`vault/30-kaizen/K-003-*`, kaizen-log row),
  POW-001/POW-002 rows in `skills/property-search/references/data-quirks.md`, the new
  `vault/00-inbox.md` entries, and any earlier uncommitted tools/edits. Message references K-003 +
  "2026-06-16 Cowork session capture."
- Confirm `git status` is clean and report the commit hash.

---

## Sequencing & guardrails
- Task 1 before Task 2A (START-HERE must point at a real `SOP-triage`).
- Commit Task 1's non-SOP files + Task 2 changes on main; leave the `kaizen/K-003-triage-sop` branch
  for human merge per cardinal rule #1.
- Do not run git writes concurrently with another open session.

## Separate flag for Yuriy (not a Code task)
CLAUDE.md still notes the **client jobs folder is not backed up** anywhere — the biggest latent risk in
the setup. Needs YV's backup decision.
