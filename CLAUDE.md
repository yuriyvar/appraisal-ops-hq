# CLAUDE.md — appraisal-ops-hq

Rule #1: at the start of every session, read latest handoff + vault/00-inbox.md + Pipeline Records before doing anything.

1.1. Each session handoff is stored in "C:\Users\yuriy\VDV Appraisals\.claude\Session-Handoffs" - read more than one if necessary.
1.2 Also read "C:\Users\yuriy\VDV Appraisals\.claude\claude-preferences.md"



Operations hub for a residential appraisal company (~65–90 orders/month).
This repo holds **process and knowledge only** — never client order files,
engagement letters, borrower data, or report PDFs. Those live in external
file storage. If a task produces such files, keep them OUT of the repo.

## Environment (Yuriy's PC — primary workstation)
- **This repo:** `C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq\` — local folder,
  NOT inside OneDrive. Synced and backed up via GitHub (private repo).
- **Client job files:** `C:\Users\yuriy\VDV Appraisals\` — orders, engagement
  letters, report PDFs, anything with borrower/client data. NOTE: currently NOT
  cloud-backed-up — backup decision pending (Sprint 1 item). Contents NEVER get
  copied into the repo.
- New machines: `git clone` the repo; never copy the folder through OneDrive.

## Layout
- `vault/` — Ops Memory system (Obsidian-compatible markdown). Read
  `vault/README.md` before touching anything inside it.
- `skills/` — Claude skills. `memory-capture`, `memory-review`, `kaizen-retro`
  run the vault's loops. New automation skills also go here.
- `.claude/commands/` — slash commands wrapping the common workflows.
- `mcp/` — custom MCP servers (one folder per server, each with its own README).
- `scripts/` — small standalone utilities (Python preferred, stdlib-first).
- `docs/` — architecture decision records (ADR-NNN-title.md) and onboarding.
- `BACKLOG.md` — Agile backlog. Sprints are 2 weeks; tags `sprint-N` mark each review.

## Cardinal rules
1. **SOPs change only via kaizen.** Never edit files in `vault/20-standard-work/`
   on `main`. Open a branch `kaizen/K-NNN-short-name`, apply the diff, bump the
   SOP `version` frontmatter, update its change log, and stop — a human merges.
   Every such change needs a kaizen item, a 5-whys, and a PDCA record with a
   Check date (see `skills/kaizen-retro/SKILL.md`).
2. **Capture is frictionless.** Learnings go to the top of `vault/00-inbox.md`,
   one line each, newest first, never reorganized at capture time. When you
   (Claude) learn something reusable during a session — a data-source quirk, a
   client preference, a failed step — append it without being asked.
3. **Andon over workaround.** If standard work fails on a real order, file an
   andon (`vault/30-kaizen/templates/andon.md`) the same session. Don't silently
   route around a broken SOP.
4. **Prune freely, archive SOP knowledge.** Notes can be deleted as muda;
   superseded SOP content gets `status: archived`, not deletion.
5. **No secrets in the repo.** API keys and credentials go in untracked `.env`
   files; `.gitignore` already blocks them.

## Conventions
- Branches: `kaizen/K-NNN-*` for SOP changes, `feat/*` for new skills/scripts/MCP,
  `fix/*` for corrections. Commit messages reference kaizen IDs or backlog items.
- Notes: one idea per file, frontmatter per `vault/10-notes/_note-template.md`,
  link with [[wikilinks]].
- Skills: follow Anthropic skill format (SKILL.md with name + pushy description).
- Dates: ISO (YYYY-MM-DD). Job-folder naming standard lives in
  `vault/20-standard-work/SOP-order-intake.md`.

## Cadence (whose job is what)
- Daily: humans append to inbox; Claude appends session learnings.
- Weekly: run `/review` (memory-review skill) — Claude distills, human approves.
- Bi-weekly: run `/retro` (kaizen-retro skill) — Claude analyzes and drafts SOP
  diffs as kaizen branches; human merges; tag the sprint.
