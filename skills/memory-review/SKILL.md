---
name: memory-review
description: Run the weekly review of the Ops Memory vault — distill the inbox into notes/SOPs/kaizen items, prune stale content, and resurface notes due for spaced review. Use whenever the user says "run the review", "process the inbox", "weekly review", "clean up the vault", or asks what's due for review, and at the start of the weekly retro meeting.
---

# Memory Review

Turns raw captures into durable, linked knowledge and keeps the vault healthy.
Claude proposes; the human approves before files change (except pure inbox
processing, which Claude may do directly).

## Phase 1 — Process the inbox (top-down)
For each entry in `vault/00-inbox.md`, classify and act:
- **Durable knowledge** → create an atomic note in `vault/10-notes/` using
  `_note-template.md`. One idea per note. Search existing notes first; if one
  exists, update it instead (and halve its `review-interval` if it was wrong).
  Add [[wikilinks]] both ways.
- **Repeatable process** → if no SOP exists, draft one from
  `vault/20-standard-work/_sop-template.md` at v0.1 and flag for human approval.
  If an SOP exists, draft a proposed diff — do NOT apply; hand to kaizen-retro.
- **Problem/defect** → ensure a row exists in `vault/30-kaizen/kaizen-log.md`.
- **Noise/duplicate/expired** → delete (muda).
Remove processed entries from the inbox. Report counts: promoted / merged /
kaizen'd / pruned.

## Phase 2 — Spaced repetition pass
1. Scan `vault/10-notes/` frontmatter. A note is DUE if
   `today >= last-reviewed + review-interval`.
2. Present due notes to the human in batches of <= 10 with a one-line gist each.
   For each, the human (or Claude, if confident from recent vault evidence) marks:
   - **Still true** → `strength += 1`, `review-interval = min(interval*2, 180)`
   - **Needs edit** → fix it, `interval = max(interval/2, 7)`
   - **Obsolete** → `status: archived` (don't delete; supersede with a link)
3. Update `last-reviewed` on everything touched.

## Phase 3 — Health report (one short paragraph)
Inbox throughput, notes due vs reviewed, SOPs with open andon flags, and the
single biggest gap noticed (e.g., "QC has no SOP but generated 4 kaizen items").

## Phase 4 — Order-lane standard-work audit (BD1, 2026-07-02)
Sample the week's order folders under `C:\Users\yuriy\VDV Appraisals\` (client zone —
read-only look, nothing copied into the repo):
1. Each worked order should carry `run-log.md` + `pull-sheet.md` (or a cache-HIT run-log)
   from `/resolve-subject`. Missing = the pipeline was bypassed.
2. In each `run-log.md`: unchecked boxes for steps already done = ticks skipped;
   worksheets carrying the "produced outside standard work" / "standard work not
   verified" chips = hand-rolled inputs.
3. Every miss becomes ONE inbox line (`[andon] standard-work bypass: <order> — <what>`)
   for the retro — the point is visibility, not blame. Repeat offenders → kaizen item.

## Rules
- Never silently change an SOP — that path runs only through kaizen-retro + human approval.
- Bias to pruning: a small accurate vault beats a large stale one.
