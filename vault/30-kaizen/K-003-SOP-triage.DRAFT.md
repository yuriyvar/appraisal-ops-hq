---
sop: SOP-triage
version: 0.1
effective: PENDING-MERGE
owner: Operations
last-kaizen: K-003 (2026-06-16)
andon-count: 0
status: DRAFT — staged in 30-kaizen for human merge onto a kaizen branch into vault/20-standard-work/SOP-triage.md. Do NOT treat as live until merged.
---

# SOP-triage (v0.1 DRAFT) — daily WIP triage + prep scope

**Purpose:** turn the Operational Records 2026 tab into (a) the **prep board** — every in-scope
WIP order to stage for a fast DM build — and (b) **YV's daily finalize/build list**. Two views of
one board. North star: **highest throughput at best, sustainable quality.**
**Trigger:** start of a work session, BEFORE building/editing any worksheet.
**Takt expectation:** < 5 min to produce both views.

## Hard rule — never work completed/submitted
`Submitted - *`, `Cancelled`, `Paid`, and **`WIP - Review for Submission`** are OFF LIMITS
(the last is already finished by YV or Alan). When status/assignment is ambiguous: **ASK, don't guess.**

## Source of truth
The **2026 tab of the Operational Records Google Sheet** (id `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`,
gid `1096625839`). The local `Operations/Operation Records.xlsx` is **stale (≤ Dec 2025) — do not use.**
**Google Drive is READ-ONLY** (CLAUDE.md #6).

### Access method (the Drive connector can't see this account)
Use the **Chrome extension** on YV's logged-in browser, against the **gviz HTML export**:
`https://docs.google.com/spreadsheets/d/12zZgU1ULHasOrgh_WHDOME40HdqEkKIL/gviz/tq?tqx=out:html&gid=1096625839`
- If a sign-in / "need access" page loads, the browser's default account is wrong → retry with an
  account-routed path `…/spreadsheets/u/1/d/…` (bump `u/1` → `u/2` …).
- Parse the DOM `<table>` with the JS tool. **Do NOT** credentialed-`fetch` the export (harness blocks it).
- Gotchas: the JS tool blocks any returned string containing `=` (build output with ` | ` separators,
  no URLs); output is size-capped → pre-filter and paginate (`arr.slice(n)`), don't dump ~400 rows.
- When the year rolls over, read the new tab's gid from its URL.

### Column map (2026 tab, 0-indexed)
`0` order date · `1` order # · `2` Client · `3` Subject Address · `4` ZIP · `5` Report Type ·
`6` Due date · `11` Report Status · `12` Notes (assignment lives here).

## Scope filter
- Keep rows whose Status contains **`WIP`** and **not** `Review for Submission` (and none of the
  off-limits statuses above).
- **Last 10 days** of order dates (≥ today − 10); older is already handled — ignore, don't surface as overdue.

## The two views
**View A — PREP BOARD (engine; assignee-blind).** EVERY in-scope WIP row, regardless of
`YV`/`Alan`, gets staged: subject worksheet (standard format) + comps staging. This is what feeds
lightning-fast DM builds for the whole shop. **Alan's orders are prepped too — never skipped at prep.**

**View B — YV DAILY LIST (sequencing).** From the prep board, the orders YV personally
finalizes/builds in DM today, read from Notes:
- `YV to do <date>` → YV's; `<date>` is when YV must do it (can differ from the official Due date).
  **Today's YV list = every `YV to do <today>`.**
- `Alan to do` → **not on YV's personal list** (Alan finalizes) — but it STILL gets prepped (View A).
- `Alan to do or YV to do if time allows` → YV backup.
- `YV done …` → YV's part finished; do not redo.

## Quality checks (jidoka)
- Ambiguous/missing status or assignment → STOP, ASK; do not guess.
- Conflicting address / can't confirm the order → andon (`30-kaizen/templates/andon.md`).
- Present both views and **build nothing until YV approves** what to start.

## Both lanes reference this SOP
`/prep-today` (Claude Code command) and the Cowork/Bob prep flow (`skills/worksheet-builder`) both
read this SOP so the two lanes can't drift. `/prep-today` produces **View B**; its Step 3 wording
must say "Alan to do = not on YV's list," NOT "skip" (don't drop from prep).

## Change log
- v0.1 (2026-06-16, DRAFT/K-003): initial standard — separates PREP-all (View A) from YV-daily-list
  (View B); fixes the `/prep-today` "skip Alan" conflict; homes the rule in the shared repo so both
  lanes share it.
