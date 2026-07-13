# Claude Code Brief — 2026-07-11
## Standardize worksheet header: county in MLS format + surrounding counties with relative direction on EVERY entry

**Requested by:** Yuriy, via Cowork/Ton, 2026-07-11 session
**Urgency:** Next Code session — low urgency, no blocker. Pairs with the still-uncommitted
2026-07-11 renderer change (see below) — commit both together.

---

## What happened (context)

Earlier today's Cowork session added the header feature both lanes have been circling:
`build_header()` in `tools/worksheet-renderer/render_worksheet.py` now renders
`{subject address} | {subject.address.county}` in the H1, plus a
`"Surrounded by: {market.search.surrounding_counties joined}"` line underneath (CSS
`.county-line`). QA 22/22 before/after. **Still uncommitted** (git is host-only for Cowork).

Yuriy reviewed it and wants two things locked in as the **permanent standard**, not a
one-off, using this worked example (486 Possum Hollow Rd, Saltville, Smyth Co order):

```
VDV Appraisal Worksheet
486 Possum Hollow Rd, Saltville, VA 24370 | Smyth Co
Surrounded by: Washington Co, Russell Co, Tazewell Co (NW), Bland Co (NE), Wythe Co (E), Grayson Co.
```

**Standard #1 — county string = however MLS displays it.** Not "Smyth County" — "Smyth Co",
matching the MLS/Matrix listing's own abbreviation convention. Capture `subject.address.county`
in that exact short form during subject pull; don't reformat it going into the renderer.

**Standard #2 — every surrounding county gets its relative direction in parentheses.** Format:
`{County Name} ({DIR})`, e.g. `Bland Co (NE)`. No entry ships without one — Yuriy's example
above actually omits directions on 3 of the 6 (Washington, Russell, Grayson), which is the
gap to close, not the target format. **All six need a direction**, every time, on every county.

---

## Tasks

### Task 1 — Data contract: `market.search.surrounding_counties` entries must carry a direction
Update the schema/skill docs so every string in `market.search.surrounding_counties` is
`"{County Name} ({DIR})"` — e.g. `"Bland Co (NE)"`, not `"Bland Co"` alone. `DIR` is one of
N/NE/E/SE/S/SW/W/NW, relative to the subject county, sourced the same way the 2026-07-11
session did it (verified against the county's own Wikipedia infobox / official state map —
never guessed).

### Task 2 — Renderer format gate (`tools/worksheet-renderer/render_worksheet.py`)
`build_header()` currently does `esc(", ".join(surrounding))` — a bare join, no validation.
Add a lightweight lint: if any entry does **not** match `.*\(.+\)$` (i.e., missing a
parenthetical direction), append a visible `⚠` marker or a `chip-warn` flag next to the
header rather than silently rendering it bare. Warn-loud-never-block, per BD1 convention —
same pattern as the existing provenance chips. Re-run `tests_qa_runner.py` after.

### Task 3 — County format capture (subject pull)
In `skills/property-search/SKILL.md` (subject verification, Step 2) and
`skills/worksheet-builder/SKILL.md` (subject checklist), add a line: capture
`subject.address.county` in the **same short form the MLS listing itself uses**
(e.g. "Smyth Co", "Chesterfield Co") rather than the county's full legal name — this is
what lands verbatim in the worksheet header, so get the form right at the source.

### Task 4 — RESOLVED: Tazewell direction confirmed, no data fix needed
Re-verified against Wikipedia's Smyth County, VA infobox (2026-07-12): Smyth County's
adjacent counties are Russell (NW), **Tazewell (N)**, Bland (NE), Wythe (E), Grayson (S),
Washington (SW). Yuriy's "(NW)" in the 486 Possum Hollow Rd example message was a recall
slip, not a correction — **the live record already has it right**: `subject.json` and
`appraisal-record.json` both read `"Tazewell Co (N)"`, and the rendered worksheet
(`486-Possum-Hollow-Rd_worksheet.html`) shows `Tazewell Co (N)` with all six directions
present. Yuriy separately confirmed the general rule: **all directions are relative to the
subject's own county.** Nothing to change here — carry on with Tasks 1–3/5/6 as written.

### Task 5 — Commit
Commit Task 1–3 together with the still-outstanding 2026-07-11 header/renderer change
(`build_header()`, `.county-line` CSS, the Chesterfield/Smyth `surrounding_counties`
backfill) — same feature, one commit is cleaner than splitting it.

### Task 6 — Add to Code memory ("the rock")
```
Worksheet header standard (2026-07-11, Yuriy-confirmed):
- subject.address.county = the county string AS MLS DISPLAYS IT (e.g. "Smyth Co"), captured
  at subject pull, not reformatted downstream.
- market.search.surrounding_counties: EVERY entry = "{County Name} ({DIR})" — no bare county
  names, no exceptions. Directions verified (Wikipedia infobox / state map), never guessed.
- Renderer (build_header, render_worksheet.py) flags any surrounding-county entry missing a
  "(DIR)" suffix rather than rendering it silently bare.
```
Update `MEMORY.md` index if one exists.

---

## What NOT to do
- Do NOT open a kaizen branch — these are skill-doc + renderer edits, not
  `vault/20-standard-work/` SOP changes.
- Do NOT resolve the Tazewell Co N vs. NW conflict by picking one without asking Yuriy —
  flag it (Task 4) and wait for his answer, same as any other MLS-vs-county variance.
- Do NOT reformat past/backfilled `surrounding_counties` values wholesale in this pass — just
  make the direction-suffix mandatory for new data going forward and patch the Tazewell entry
  once confirmed.

---

## Reply-to
`interlane/INBOX-for-Cowork.md` — confirm tasks done + commit hash + Tazewell direction resolved.
