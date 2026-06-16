# 5 Whys — root cause

Required before any SOP change that responds to a defect.

- **Kaizen item:** K-003
- **Problem statement:** The daily triage rule (`/prep-today` command + the Code-side
  `wip-triage-rule.md` memory) instructs "`Alan to do` → skip," which conflicts with YV's directive to
  **prep ALL WIP (YV + Alan)** for throughput. Compounding it, the rule lives only in Claude Code's
  app-internal memory, which Cowork/Bob cannot read → the two lanes drifted.

1. Why did the rule skip Alan's orders? -> "Skip Alan" was written as a hard filter on the whole rule, not as a property of one view.
2. Why a hard filter? -> The "what to PREP" scope (all WIP) and the "what YV finalizes today" list (YV rows) were conflated into a single output.
3. Why conflated? -> There was no canonical triage SOP separating the prep board (assignee-blind) from YV's daily finalize list.
4. Why no canonical SOP? -> The rule was authored in Claude Code's per-tool memory, never homed in the shared repo, so it never went through the SOP/kaizen process and Cowork couldn't align to it.
5. Why per-tool memory? -> No standing convention that **cross-lane operating rules must live in the shared repo and be referenced by both lanes**.

- **Root cause:** Cross-lane operating rules weren't homed in the shared repo as SOPs, so scope got conflated (prep vs YV-list) and the lanes drifted.
- **Countermeasure (the SOP edit, specifically):** Create `SOP-triage` in the shared repo (staged draft `K-003-SOP-triage.DRAFT.md`) with an explicit **two-view** model — View A PREP (all in-scope WIP, assignee-blind) and View B YV daily finalize list. Reword `/prep-today` Step 3 so "`Alan to do`" means "not on YV's personal list," NOT "don't prep." Point both `/prep-today` and the Cowork worksheet-builder prep flow at `SOP-triage`.
