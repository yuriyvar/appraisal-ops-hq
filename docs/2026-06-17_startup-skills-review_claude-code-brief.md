# Code brief — Startup "review & memorize the skills" rule (both lanes)
2026-06-17 · Cowork → Code · staged by Bob per the `delegate-to-code` skill

## Why
On a real order (three Richmond City subjects), Bob **freelanced** the data-gathering — went to a
University-of-Richmond parcel copy + Zillow regex — instead of running the standard process:
`worksheet-builder` → `property-search` → `references/county-registry.md` routing, which routes
**Richmond City → actDataScout** (the authoritative city tax records). Yuriy had to redirect twice.

**Directive (Yuriy):** every session / wake-up, in BOTH lanes, must START by reviewing and
**memorizing** the process skills in `appraisal-ops-hq/skills/` BEFORE any appraisal work — and then
follow them, not improvise.

## Do (Code-only — `.claude/` + Code's own memory)
1. **`.claude/START-HERE.md`** — add a startup step, high in the read-order (right after the handoff/
   inbox/Pipeline reads):
   > **Before any appraisal work, review & MEMORIZE the process skills in `appraisal-ops-hq/skills/`.**
   > List them, then read the relevant `SKILL.md` + references — especially **worksheet-builder**
   > (DM/ACI worksheet + completeness gate), **property-search** (subject verification + comp pull +
   > `references/county-registry.md` → the county's SOR adapter), **notes-composer**, and
   > **delegate-to-code**. Follow the playbook; do NOT freelance the appraisal process.
   Also confirm **delegate-to-code** and the other skills are present in START-HERE's skills lookup.
2. **Repo-root `CLAUDE.md`** — add sub-rule **1.3** mirroring the above (one line: review+memorize
   `skills/` before appraisal work; follow, don't freelance).
3. **Code's app-internal memory ("the rock")** — `~/.claude/...` project memory / Code's own CLAUDE.md:
   add the same standing instruction so Claude Code self-orients on `skills/` at session start too.

## Guardrails
- These are config / cardinal-rules files, **not** a `vault/20-standard-work/` SOP → **no kaizen branch
  required**; a direct edit + commit on `main` is fine.
- One-session git rule; if locks block, clear all FOUR `.lock` files (incl. `.git/refs/heads/main.lock`).
- Never circumvent a protection; no client/order PII in the repo.

## Reply-to
`interlane/INBOX-for-Cowork.md` — reply + mark the memo `[DONE]` when shipped.

## Addendum — appraisal trigger tag
Add a recognized trigger **`#appr`** (alias `/appraise`) in START-HERE.md + CLAUDE.md + Code memory:
when a user message leads with/contains it, treat everything following as APPRAISAL WORK → immediately
load & follow `skills/` (property-search + `county-registry.md` routing → worksheet-builder completeness
gate → record-assembler → worksheet-renderer). No freelancing, no skipping the county SOR adapter.
