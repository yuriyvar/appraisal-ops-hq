# Code Implementation Plan — Consolidated Handoffs (cycle 2026-06-25 → 06-26)

**For:** Claude Code. **From:** Bob (Cowork). **Date:** 2026-06-26.
**Purpose:** single dependency-ordered plan folding every open Code item from the last handoff
cycle into phases. Sources are cited per item so nothing is invented.

**Source memos / records:**
- `interlane/INBOX-for-Code.md` — 2026-06-26 [ACTION] QA failures · 2026-06-26 [FYI] worksheet exit · 2026-06-25 [FYI] Sandstone+Charlotte
- `vault/00-inbox.md` — 2026-06-26 [andon] (full QA detail) · 2026-06-23 [client] comp-selection rubric
- `interlane/INBOX-for-Cowork.md` — Code's 6/18 replies (carried-over OPEN items)
- Briefs: `docs/code-brief_worksheet-renderer-fixes_2026-06-19.md`, `docs/code-brief_dma-value-corpus_2026-06-19.md`

**Guardrail reminder:** skill / tool / registry / DB edits = direct commit on `main`. Anything under
`vault/20-standard-work/` (SOP) = kaizen branch `kaizen/K-NNN-*`, version bump, change log, human merges
(CLAUDE.md cardinal rule #1). Phases below mark which path each item takes.

---

## Phase 0 — Stop the bleeding (do first, today)
Live defect already fixed in the working copy; only the commit + a guard remain.

1. **Commit the renderer Tax ID fix.** `tools/worksheet-renderer/render_worksheet.py`: `COMP_ROWS`
   now includes a **"Tax ID (PID/APN)"** comp row (`identifiers.pid || apn || map_id`) and the subject
   **"APN / Tax ID"** falls back `apn || pid || map_id`. Review the diff, commit on `main`.
   *(Source: 06-26 [ACTION] #1 / andon #1.)*
2. **Add a completeness-gate assertion** that each comp's Tax ID actually **renders in the HTML**, not
   just present in the JSON. Fails the render/QA if any comp grid cell is blank where a PID/APN exists.
   *(Same source — the "gate check" half of #1.)*

**Exit:** commit hash posted to `INBOX-for-Cowork.md`; gate proven on a sample record.

---

## Phase 1 — Comp-data integrity gates (process hardening)
Convert the QA defects into automated guards so they can't recur. Worksheet-builder + renderer; no SOP edit.

1. **12-month sales-window gate.** Flag any comp with `sale_date` older than 12 months **or** `sale_date: null`.
   Default window = 12 mo; older same-project sales are **supplemental only, explicitly dated-justified,
   never primary/unlabeled.** *(Source: 06-26 [ACTION] #3 / andon #3 — The Moorings mixed 2023–24 sales.)*
2. **Comp-selection rubric → worksheet-builder gate.** Bake YV's rubric into comp-selection logic:
   above-grade GLA **±10%**; distance tiers (Rural 1/3/5/7/10/12 mi, Urban 0.25/0.5/1/1.5 mi,
   Suburban urban tiers→3 mi); parcel/lot **±20–30%**; sold-price variation **3–15%**; **any criterion
   out of band → HIGHLIGHT and let YV decide, never silently drop or include.**
   *(Source: vault 2026-06-23 [client] comp-selection rubric.)*
3. **Enforce per-comp ML# + Tax ID capture** in the worksheet-builder gate (already a standing rule;
   the Tax ID render gate in Phase 0 is its renderer half). *(Source: vault 2026-06-17 [learn] process fix.)*

**Exit:** gates green on a re-run of a known-good record; post results.

---

## Phase 2 — MLS market routing & data-source registry
Pure registry/reference edits. Fixes the root cause behind the wrong-MLS pull. Direct commit.

1. **MLS-by-county map (CVR / Bright / Navica)** added as an explicit column to `county-registry.md`
   and to `va-data-sources`. Confirmed **Navica (Lake Country Assn of Realtors)** markets:
   **Prince Edward** and **Mecklenburg / Kerr Lake** (CVR returned 0 condo sales for 23927 over 5 yr).
2. **Surrounding-county search sets** for rural orders:
   - Prince Edward → Buckingham, Appomattox, Charlotte, Cumberland, Nottoway, Lunenburg
   - Mecklenburg / Kerr Lake → Lunenburg, Charlotte, Halifax, Brunswick **+ NC Kerr Lake shore (Vance / Granville / Warren NC)**
3. **Mecklenburg ConciseCAMA adapter note → `va-data-sources`** (or new adapter note):
   `mecklenburg.cama.concisesystems.com` is searchable (Address/Owner/Map); parcel detail =
   `PropertyPage.aspx?id=<PRN>`. `web_fetch` blocked by Disclaimer.aspx cookie gate, but a **logged-in
   browser tab works** and supports **in-page synchronous XHR batch-pull** of a whole condo project's
   sale histories (Heated Sq Ft / Bedrooms / TOTALS / Sales History / Land Segments incl. **DOCK/BUOY** premium).
   Use for 1073 same-project comps when MLS isn't reachable.
4. **CVR Matrix column-mapping gotcha → `data-quirks.md`.** Result-grid `<td>` indices **shift** between
   display formats (Agent vs Appraiser Single Line). **Re-read the header row and map by name**
   (`Address`/`ML #`/`PID`/`TtlFinAr`) every time — never hardcode indices.
5. **Charlotte Co + Buckingham Co `data-quirks.md` entries** (low priority) — county-registry rows already
   updated this cycle; the matching data-quirks notes are still missing.

*(Sources: 06-26 [ACTION] #2/#4/#5; 06-26 [FYI] county-registry update.)*

---

## Phase 3 — Template + tooling alignment (carried PRIORITY-1)
Re-flagged in the 6/25 Sandstone handoff; originally 6/15–6/16. Skill/tool edits, direct commit.

1. **Fold YV's snapshot + parcel-dims into the DM-complete template + generator.**
   `Operations/Template files/Subject-Worksheet_TEMPLATE_DM-complete.html` predates the two adopted
   additions; fold them into the template **and** `tools/dm-collection-sheet/`:
   (a) top **search-snapshot** block (above-grade GLA, county-vs-MLS finished area, comp GLA range ±10%,
   garage/carport, basement total+finished, county + surrounding counties for Navica);
   (b) a **Parcel dimensions** row in Site (lot metes). *(Source: 06-25 [FYI] PRIORITY-1; vault 2026-06-16.)*
2. **DM-tabs remap of `build_collection_sheet.py`.** Remap the CATALOG into the 4 ACI/DM tabs
   (Subject · Neighborhood · Site · Improvements, + Contract sub-block) and **add the missing Neighborhood
   section** (location type, built-up %, growth, values trend, demand/supply, marketing time, present
   land-use %, boundaries, market conditions); regenerate template + reference; populate field-map
   `aci_web` column from the same structure. *(Source: vault 2026-06-15 [client] PRIORITY-1.)*

---

## Phase 4 — Bootstrap & guardrail polish (some SOP → kaizen)
1. **`#appr` / `/appraise` trigger-tag addendum** — still OPEN from the 6/17 startup-skills-review brief.
   Add the trigger tag so a leading `#appr` / `/appraise` routes straight into the playbook.
   *(Source: INBOX-for-Cowork 6/18 reply — "ADDENDUM still open".)*
2. **Encode the meta-rule: "when in doubt, ask — never delete/strip YV's data."** On an ambiguous
   instruction, keep found work as **candidates** for YV to confirm/extend; ask before destructive edits.
   If this lands in a `vault/20-standard-work/` SOP → **kaizen branch + 5-whys + PDCA**, human merges.
   *(Source: 06-26 andon #4 — the meta-failure.)*

---

## Phase 5 — Optional / async (no urgency)
1. **`va-gas-providers.sqlite` "confirmed absent" rows** for Charlotte Co + Buckingham Co — genuinely no
   SCC-regulated provider. If the schema supports a "confirmed absent" row type, add it to distinguish
   from "not yet looked up." *(Source: 06-26 [FYI] optional task.)*
2. **`.dma` value-corpus extraction track (A→B→C→D)** — separate, non-blocking. Per
   `docs/code-brief_dma-value-corpus_2026-06-19.md`: A decode 113 `.dma` → raw corpus; B de-identify
   (strip PII, year-only dates, pseudonymize); C analyze (field completeness, default-value candidates,
   adjustment medians/p25/p75, neighborhood text by county, water/sewer breakdown) — **YV reviews before D**;
   D update condition profiles, $/feature ranges, county neighborhood templates, water/sewer defaults
   (`.bak` + diff before every repo edit). Three stdlib-only scripts, no new deps. A–C outputs stay in
   `Past Reports/_analysis/` (client zone); only D touches the repo.

---

## Not Code's work (tracked here so it isn't lost)
- **Charlotte Co 16560 Kings Hwy zoning** — Bob/YV task; finish on `charlotte.civ.quest` (enable zoning
  layer on Record 086-A-7-A; expected A-1 Agricultural, unconfirmed).
- **319 N Sandstone MLS#** — pending YV's Valley MLS pull (assessor has none — SRC-001).
- **Richmond City actDataScout pulls** (2320 Burton St, 2304 Yorktown Ave) — YV must pull, **VPN OFF**;
  Matrix Identity Conflict is a YV gate.

## Suggested order
Phase 0 → 1 → 2 in one Code session (defect + the gates that prevent its recurrence + the routing fix that
caused it). Phase 3 next session (bigger template/generator work). Phase 4 alongside whichever session
touches the bootstrap. Phase 5 when idle. Reply per memo in `INBOX-for-Cowork.md`; mark each consumed
`[ACTION]`/`[FYI]` `[DONE]`.
