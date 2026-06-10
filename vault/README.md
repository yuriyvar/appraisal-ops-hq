# Ops Memory — a self-improving knowledge system

A plain-markdown vault (Obsidian-compatible) that captures what your team learns,
turns it into standard work, and improves itself on a fixed cadence using
Toyota Production System (TPS) principles. Claude runs the loops via the skills
in the repo's `skills/` directory.

## The three loops

**Daily — Capture (Karpathy append-and-review)**
Everything goes to the top of `00-inbox.md`. No sorting, no tagging, no friction.
One line is enough. The only rule: if it surprised you, cost you time, or you'd
want a new hire to know it — append it.

**Weekly — Review (distill)**
Claude (memory-review skill) processes the inbox top-down:
- Promote durable knowledge → atomic note in `10-notes/`
- Promote repeatable process → SOP in `20-standard-work/` (new or revision proposal)
- Recurring problem → kaizen item in `30-kaizen/kaizen-log.md`
- Stale/duplicate → delete (muda — waste — is pruned, not hoarded)
Notes carry `last-reviewed` and `review-interval` frontmatter; the review skill
resurfaces notes whose interval has lapsed (spaced repetition for the org).

**Weekly/Monthly — Kaizen (improve the standard)**
Claude (kaizen-retro skill) reads the kaizen log, andon flags, and metrics, runs
PDCA, and proposes *specific edits* to SOPs. A human approves; the SOP version
increments. The new standard becomes the baseline for the next cycle. This is
the self-improvement: the system rewrites its own standard work, with evidence.

## TPS principles → mechanisms

| TPS principle | Mechanism in this vault |
|---|---|
| Standard work | `20-standard-work/` — versioned SOPs; no improvement without a standard |
| Kaizen | `30-kaizen/kaizen-log.md` + weekly retro proposing SOP diffs |
| Jidoka / Andon | `templates/andon.md` — anyone (or Claude) flags when an SOP fails in use; flagged SOPs get priority in retro |
| Genchi genbutsu | Capture rule: log problems at the moment they happen, with the real example attached |
| 5 Whys | `templates/5-whys.md` — required before any SOP change driven by a defect |
| PDCA | `templates/pdca.md` — every SOP change is an experiment with a check date |
| Muda elimination | Review skill prunes stale notes; metrics track rework and touch-time |

## Directory map

```
00-inbox.md          Append-and-review capture (newest on top)
10-notes/            Atomic, linked knowledge notes ([[wikilinks]])
20-standard-work/    Versioned SOPs (the standards)
30-kaizen/           Improvement log + andon/5-whys/PDCA templates
40-reviews/          Daily + weekly review checklists/templates
50-metrics/          The numbers kaizen is judged against
(repo root) skills/  Claude skills that run the loops
(repo root) BACKLOG.md  Agile backlog — how we build and extend this system
```

## Ground rules

1. Capture is sacred: never let process slow down appending to the inbox.
2. One idea per note; link instead of duplicating.
3. SOPs are the only "true" process docs. If reality differs from the SOP,
   either fix reality or file an andon — never silently diverge.
4. Every SOP change cites evidence (kaizen item, andon, or metric).
5. Claude proposes; a human approves SOP changes (jidoka has a human pull-cord).
