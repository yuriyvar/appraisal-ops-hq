# Master brief — "insane automation" roadmap (YV 2026-07-02)

> **Goal (YV):** provide a subject address → COWORK_AGENT pulls + verifies the data from reliable
> sources **in order: MLS → County/GIS → Zillow**, comps get pulled (incl. historical recall),
> and everything lands in the web forms platform — with the process GUARD-RAILED so the agent
> can't start "his own process". *"Discipline prevents entropy and ensures consistent high quality."*
>
> This is the queue of future build days. Each track becomes its own phased code-brief (the
> proven pattern: P0 tracker → phases → QA → caveman commits). This file is the map, not the spec.

## YV decisions (asked + answered 2026-07-02)
1. **Target entry system = ACI Sky Workbench (UAD 3.6) — LIVE NOW** → Track 6 unblocked.
2. **Conflict governance:** on source disagreement, read the listing info to analyze whether it
   SUPPORTS the variance (finished basement, addition, assessor lag…). Supported → record the
   justification with the value. Not supported → **County rules**, and the row is flagged
   **"inconsistent — manual triage"** either way until YV clears it.
3. **Registry completion: as orders arrive** — no bulk research; make adding a county frictionless
   and enforce the same-commit drift rule harder.
4. **Historical index sources: Ops file + the `.dma` corpus** (full comp grids via the existing
   decoder). Index lives in the CLIENT zone.

## YV actions (no build can substitute for these)
- **Navica acct 287 (South Central) credentials** — still don't exist anywhere we can read;
  Hall Rd comps + real "outside CVR/Bright" confidence stay gated until then.
- **One live ACI session** (logged-in Chrome) for Track 6 selector discovery — genchi genbutsu;
  selectors can't be invented offline.
- **One logged-in Chrome session** to export the Ops sheet for Track 5's index seed.

## Navica confidence statement (recorded)
Documented + proven once (4237 Hall Rd, acct 397; full workflow + per-comp checklist in
`skills/property-search/references/navica-accounts.md`). Semi-manual (no CSV export; several
fields only in remarks/photos). **Medium** — needs 287 access + 2–3 more live orders to season.
Track 4 wraps the flow as a tool once seasoned.

---

## Track 1 — Standard-work enforcement (BUILD DAY 1 — first, cheapest, sharpest pain)
Make the pipeline the only convenient path; catch freelancing same-session.
- **Run-log gate:** `resolve_subject.py` also emits `run-log.md` (steps + checkboxes + stamps).
  `ingest_subject.py` and `assemble_record.py` WARN LOUD when the expected upstream artifacts
  (pull-sheet/run-log/resolution stamp) are absent — a hand-rolled subject.json gets flagged
  "produced outside standard work" on the worksheet itself.
- **Entry-point hardening:** `/appraise` (and the `#appr` trigger) routes THROUGH
  `/resolve-subject` step 1; boot files + SKILL headers say "no portal browsing before the
  resolver has answered HIT/MISS".
- **New-county intake ritual:** `add_county.py` scaffolds the registry row + `county_routing.json`
  entry together (drift rule made mechanical, not remembered); refuses to add one without the other.
- **Administration:** weekly `/review` gains an order-lane audit item — sample recent order folders
  for pull-sheet/run-log presence; misses become inbox entries (andon over workaround).

## Track 2 — Multi-source verification + variance protocol (BUILD DAY 2)
Encode YV decision #2 into the resolver/ingest layer (renderer already displays `verification[]`).
- Pull order MLS → County/GIS → Zillow baked into the pull sheet; ingest accepts per-source values
  (`gla_mls_sf` pattern generalized: `*_mls` / `*_county` / `*_zillow` helper keys).
- Agreement → single verification row, governing per current SOP.
- Disagreement → run card prompts the variance analysis (read remarks/photos, name the reason);
  supported → value + justification string recorded; unsupported → County governs;
  **both cases flag "inconsistent — manual triage"** until YV clears (hard flag, renderer chip).
- QA: variance matrix cases (supported/unsupported/missing-source).

## Track 3 — Historical comp recall (BUILD DAY 3)
- `tools/comp-history/build_index.py`: decode the Past Reports `.dma` corpus (existing decoder) +
  the Ops-sheet export → client-zone SQLite (`Past Reports/_analysis/comp-history.sqlite`):
  subjects + every report's comp grid (address, GLA, sale date/price, county, style).
- `resolve_subject.py` step: query for a similar subject appraised **≤12 mo** (county + GLA band ±15%
  + property type) → print the prior report + its comps on the run card as **CANDIDATES for YV**
  (never auto-selected; sale dates re-checked against the current effective date).
- Refresh ritual: index rebuild appended to the exit ritual / weekly review.

## Track 4 — MCP server `mcp/appraisal-data` (BUILD DAY 4 — after 1–3 stabilize the surface)
Tools > prose: the agent calls structured tools instead of browsing freestyle, and each tool
returns the next step. Wraps: resolve / ingest / cache get·put / gas lookup / registry route /
arcgis fetch / comp-history search (+ Navica flow once seasoned).
- Decision needed at build time: MCP SDK dependency (venv) vs. bare-JSON stdio server — the
  stdlib-only house rule needs a documented exception either way.
- This is Track 1's guardrail with teeth: freeform browsing becomes the EXCEPTION that stands out.

## Track 5 — ACI Sky Workbench auto-entry (BUILD DAY 5 — needs the YV live session first)
ACI is LIVE (YV decision #1). Kill the double entry: subject + comps flow from
`appraisal-record.json` into the ACI web form.
- Session 1 (with YV): walk the live form, capture `aci_web` selectors into
  `field-map.1004.yaml` (+ `aci_tab` — the old deferral dissolves now ACI is live).
- Then: Chrome-MCP fill script driven by the field map (record → form), per-field verify-after-write,
  human review before ANY submit (USPAP: never certify/submit — unchanged, hard rule).
- UAD 3.6 dictionary work (Alan interview) folds in here when it lands.

## Sequencing + rules of engagement
1 → 2 → 3 → 4 → 5, except Track 5's selector-discovery session happens whenever YV can sit with
the live ACI form (it only needs an hour and unblocks the biggest win). Every track: client data
stays in the client zone; fail loud never guess; stdlib unless a documented exception; each build
day gets its own P0 brief + tracker; commits caveman.
