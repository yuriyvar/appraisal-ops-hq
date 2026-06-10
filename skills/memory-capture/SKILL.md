---
name: memory-capture
description: Append learnings, problems, client preferences, and ideas to the team's Ops Memory inbox (00-inbox.md). Use this whenever the user says "remember this", "log this", "add to inbox", "note for the team", mentions something that surprised them, a mistake, a client quirk, or a revision request — and also proactively at the end of any work session where Claude itself learned something reusable about this company's workflows (a data source quirk, a client preference, a step that failed). When in doubt, capture; the weekly review prunes.
---

# Memory Capture

Append-and-review capture into the Ops Memory vault. Friction must stay near zero.

## Procedure
1. Locate the vault's `vault/00-inbox.md`.
2. Compose one entry per distinct item, single line preferred:
   `- YYYY-MM-DD [tag] one-line statement (real example / order # if available)`
   Tags: `[learn] [problem] [idea] [client] [andon]`.
3. Insert new entries at the TOP of the list, directly under the `---` separator.
   Never edit or reorder existing entries.
4. If the item describes standard work FAILING (a defect, a revision request, an
   SOP that didn't match reality), tag it `[andon]` and ALSO create an andon file
   in `vault/30-kaizen/` from `vault/30-kaizen/templates/andon.md`, then add a row to
   `vault/30-kaizen/kaizen-log.md`. Tell the user you pulled the cord.
5. Confirm to the user in one short sentence what was captured. Do not summarize
   the whole inbox.

## Rules
- Capture verbatim facts; do not editorialize or generalize at capture time —
  distillation happens at weekly review.
- Genchi genbutsu: always try to attach the concrete instance (order #, client,
  file) the learning came from.
- Never block on missing details; capture what exists and move on.
