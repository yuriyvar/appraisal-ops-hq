<!-- build-plan: name=bd1-standard-work-enforcement status=active -->
# Code brief — BD1: standard-work enforcement (guardrails)

> Track 1 of the automation roadmap (`2026-07-02_automation-roadmap_master-brief.md`).
> YV's driver: COWORK_AGENT "starts his own process" instead of following the setup —
> *"Discipline prevents entropy."* Fix = move the process from prose into tools that
> refuse to be skipped, and make bypasses VISIBLE on the worksheet itself.

## Progress tracker
- [x] Phase 0 — this brief committed
- [x] Phase 1 — run-log: `resolve_subject.py` emits `run-log.md` (HIT and MISS variants);
      `ingest_subject.py` ticks its own step; QA C15
- [x] Phase 2 — provenance gates: ingest warns + flags when no pull-sheet sibling;
      assembler flags subject.json lacking a resolution stamp ("produced outside standard
      work" — renders as a header chip); QA C16 + Build B T22
- [x] Phase 3 — `add_county.py`: scaffolds the registry row + `county_routing.json` entry
      TOGETHER (drift rule mechanical; refuses partial adds); QA C17
- [ ] Phase 4 — wrap: `/appraise`+boot/SKILL hard wording ("no portal browsing before the
      resolver answers HIT/MISS") · weekly `/review` order-lane audit item · docs · inbox ·
      interlane [ACTION] · handoff · flip tag to done + tick BD1 in the master queue

## Design (locked)
- **run-log.md** (written by the resolver next to the skeleton/subject.json):
  numbered standard-work checklist — 1 resolve (auto-ticked, HIT/MISS + date) ·
  2 pull sheet executed (human ticks) · 3 ingest (auto-ticked by `ingest_subject.py`
  when a run-log sits next to the raw file) · 4 comps per property-search ·
  5 assemble · 6 render gate exit 0. Dates use `--as-of` when given (determinism in QA).
- **Provenance gates — warn loud, never block** (a blocked pipeline invites workarounds;
  a flagged worksheet invites questions from YV):
  - ingest without `pull-sheet.md` next to the input → stderr warning + subject flag
    `ingested without a resolver pull sheet — standard work not verified`.
  - assembler: `subject.json` with no `resolution.resolved_on` = it bypassed
    resolve→ingest entirely → subject flag `produced outside standard work
    (resolve→pull→ingest); verify provenance` → renders as a warn chip in the
    worksheet header where YV sees it.
- **add_county.py**: `--jurisdiction --vendor --sor-url --technique --mls ... [--registry PATH
  --routing PATH]` (path overrides for QA temps) → appends the Extended-coverage table row
  AND the routing JSON entry in one run; either file missing/unwritable → NOTHING is
  written (all-or-nothing). Prints the live-verify reminder + same-commit rule.
- Existing QA stays green: Build B fixtures all carry resolution stamps, so no false flags.

## Out of scope
Tick-automation inside assembler/renderer (BD4's MCP wrapper is the right home) ·
any Cowork-side hook enforcement (no hook surface in that lane) · registry bulk-fill
(YV: as orders arrive) · Tracks 2–5.

## Verify
```powershell
python "appraisal-ops-hq\tools\subject-resolution\tests_subject_resolution.py"   # 14 -> 17
python "appraisal-ops-hq\tools\record-assembler\tests_qa_runner.py"              # 21 -> 22
```
