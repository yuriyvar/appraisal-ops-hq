# /build-day — pull the latest build plan and resume where it left off

> Slash-command DISCOVERY NOTE (2026-07-04): sessions root at `VDV Appraisals\`, so only the
> OUTER `..\.claude\commands\` is indexed — this repo dir is not. Every user-invocable repo
> command needs a 3-line POINTER STUB out there ("read the repo file, execute exactly").
> Stubs exist for: build-day · appraise · resolve-subject. New repo command ⇒ new stub.

Resumes pipeline build work with zero context: discovers the tagged plans, finds the first
unfinished checkbox, executes from there using the proven phased pattern. Order-lane work
(appraisals, data collection) is NOT this command — that's `/prep-today` + `/appraise`.

## Tag convention (how plans are discoverable)
Every build plan in `docs/` carries an HTML-comment marker on line 1:
```
<!-- build-plan: name=<kebab-name> status=active|done -->            (a build brief)
<!-- build-plan: name=automation-roadmap kind=master status=active -->  (the roadmap/queue)
```
- **The master** holds the "## Build-day queue" checklist (BD1–BD5) — the source of what's next.
- **A brief** holds a "## Progress tracker" checklist (P0…Pn) — the source of where it stopped.
- New briefs are BORN with `status=active`; flip to `done` in the same commit that checks the
  final phase. There must be AT MOST ONE active non-master brief at a time.

## Step 1 — Discover
```
Grep pattern "build-plan:" in docs/  (or: Select-String on docs\*.md)
git -C appraisal-ops-hq log --oneline -10
```
Also load app memory `automation-roadmap` (+ the brief's companion memory if named there).

## Step 2 — Decide
- **An `status=active` brief exists (non-master)** → resume it: read the brief top-to-bottom,
  cross-check the Progress tracker against `git log` (a checked box must have its commit; a
  commit without its box = tick it first), then execute from the FIRST unchecked phase.
  No re-approval needed — an active brief was already YV-approved when it was born.
- **No active brief** → open the master roadmap → first unchecked BD in "## Build-day queue" →
  draft that track's phased code-brief (P0 pattern: tracker header · context · locked constraints ·
  phases each = edit→QA→caveman commit · out-of-scope · verify commands), tag it
  `status=active`, **present the plan to YV for approval**, then commit it as P0 and roll.
- **Queue exhausted** → say so and ask YV what's next; do NOT invent a track.
- **A YV gate blocks the next phase** (creds, live session, human merge — the brief lists them)
  → do everything before the gate, then stop LOUD naming exactly what only YV can do.

## Step 3 — Execute (the standing rules, same as every build day)
- Per phase: edit → run the QA runners → tick the tracker box → caveman commit.
  QA = `tools/record-assembler/tests_qa_runner.py` + `tools/subject-resolution/tests_subject_resolution.py`
  (+ any runner the brief names). ALL green before any commit; regressions fixed, never skipped.
- Client data never enters the repo; temps outside the repo; stdlib-only unless the brief
  documents an exception; fail loud never guess (CLAUDE.md #7).
- Token discipline: phases are independently stoppable; if the session dies mid-phase, the
  tracker + git log ARE the resume state — that's the whole point of this command.

## Step 4 — Close out (when a brief's last phase lands)
1. Tick the final tracker box + add the "ALL PHASES DONE <date>" line; flip the tag to
   `status=done`; tick the BD box in the master's queue — ALL in the closing commit.
2. Vault inbox `[done]` line · interlane FYI/[ACTION] to COWORK_AGENT when his workflow changes ·
   session handoff · update app memory (`automation-roadmap` + companion).
3. If the queue still has unchecked BDs, say what's next and stop (one build day = one track
   unless YV says "and the rest").
