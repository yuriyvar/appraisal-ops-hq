# BACKLOG — building Ops Memory with Agile

Cadence: 2-week sprints. Sprint review doubles as the system's kaizen retro
(the Agile retro and the TPS PDCA "Check/Act" are the same meeting).

## Definition of Done (any backlog item)
- Works on a real appraisal order, not a toy example
- Captured as standard work (SOP or skill) — not tribal knowledge
- Has at least one metric in `50-metrics/metrics.md` that would show regression

## Sprint 1 — Walking skeleton (capture + review)
- [ ] Team starts appending to `00-inbox.md` daily (goal: 5+ entries/day team-wide)
- [ ] Run memory-review skill manually once; promote first 5 notes + 1 SOP
- [ ] Write SOP v0.1 for the single most repeated workflow (suggested: order intake)
- [ ] Baseline metrics: avg touch-time per order, revision/rework rate
- Sprint goal: one full capture→review cycle completed on real work

## Sprint 2 — Standard work + andon
- [ ] Convert top 3 workflows to SOPs (intake, data pull, QC checklist)
- [ ] Andon in use: every SOP failure this sprint gets a flag filed same-day
- [ ] First kaizen retro: run kaizen-retro skill, approve ≥1 SOP revision
- Sprint goal: an SOP changes version number because of evidence

## Sprint 3 — Automation hooks
- [ ] Wire memory-review to run on a schedule (or as a one-click Cowork task)
- [ ] Capture skill auto-appends learnings from Claude work sessions to inbox
- [ ] Spaced-repetition pass: review skill resurfaces lapsed notes weekly
- Sprint goal: loops run without anyone remembering to run them

## Sprint 4+ — Candidate epics (groom at each planning)
- Per-client preference notes auto-injected into order setup
- QC defect taxonomy → 5-whys library → preventive SOP edits
- Metrics dashboard from `50-metrics/`
- Skill evals: test SOP-driven skills against past orders (skill-creator workflow)

## Ceremonies
- Daily: 30-second inbox append (replaces nothing; adds almost no time)
- Weekly: 20-min review (Claude does the heavy lift, human approves)
- Bi-weekly: sprint review + kaizen retro (one meeting)

## Icebox / explicitly out of scope for now
- Custom database or app — plain markdown until it provably breaks
- Automating SOP approval — human stays in the loop by design
