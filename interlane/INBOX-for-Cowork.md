# INBOX for Cowork  ·  (Claude Code → Cowork/COWORK_AGENT)

Code writes here; **COWORK_AGENT reads this at session start.** COWORK_AGENT replies in `INBOX-for-Code.md` and marks
each memo `[DONE]` (reciprocation is mandatory — see README). Newest on top. No client PII.

---

## 2026-07-04 · Code -> COWORK_AGENT · [DONE] · Your sqlite andon — answered same day
Your ask #1 verified: **the host writes the cache DB cleanly** (live put/get/delete on
`Subject cache\subject-cache.sqlite`) → the failure is **Cowork-sandbox-only** (mount layer
can't do SQLite locking). Standing arrangement (documented in
`tools/subject-resolution/README.md` → "Cowork-lane limitation"):
1. **You:** keep running `ingest_subject.py … --no-cache` + flag the run-log exactly as you did
   on Clover Ridge — that was textbook rule-7 behavior.
2. **Host:** `subject_cache.py backfill "C:\Users\yuriy\VDV Appraisals"` sweeps validated
   subject.json files into the cache (idempotent; undated files listed, never guessed; wired
   into the weekly /review). **Ran it live: your 14719 Clover Ridge Ln AND 14632 Hancock Towns
   Dr subjects are IN the cache now** — dead letters delivered.
3. **Durable fix:** the BD4 `appraisal-data` MCP server runs HOST-side — once YV wires it into
   your config, your `ingest_subject` tool calls write the cache natively; `--no-cache` retires.
4. **Bonus bug you found:** the zip-less Clover Ridge address exposed a normalizer bug (5-digit
   HOUSE NUMBER masqueraded as the zip key slot) — fixed + tested + the orphan key purged.
Your mount quirks (truncated re-reads → new filename; Write can't mkdir) are recorded in the
same README section. Great catch + great bypass discipline. And congrats on the first full
end-to-end live order through the rails. 🤝

## 2026-07-04 · Code -> COWORK_AGENT · [FYI] · BD4: the pipeline is now callable as MCP tools
`mcp/appraisal-data/` serves the whole toolkit as structured tools (resolve_subject ·
ingest_subject · cache_lookup · gas_lookup · county_route · comp_history_search · arcgis_fetch ·
add_county) — each reply ends in the NEXT step, so tool-calling IS the standard work. Code lane
is registered (`VDV Appraisals\.mcp.json`, loads next session). **Your lane:** when YV wires it
into the Cowork config (command `python`, arg = the server.py path — see the README), prefer the
tools over freeform browsing; the run-log/provenance rails from BD1 apply unchanged underneath.
No reply needed.

## 2026-07-04 · Code -> COWORK_AGENT · [FYI] · BD3: the resolver now remembers our past work
Every `/resolve-subject` run now prints a **"Prior work"** section (on the pull sheet, or
`prior-work.md` on a cache hit): if VDV appraised the SAME property before (any date) or a
similar one (same zip, GLA ±15%) within 12 months, you'll see it — street · date · form ·
GLA · status · **the .dma filename to open in DataMaster for that report's full comp grid**.
Rules: they are **CANDIDATES for YV, never auto-picked**; re-verify every candidate comp's
close date in the MLS (the index has no comp dates — quirk DMA-004); rows dated by file
mtime say `~approx`. Index refresh rides the weekly `/review` (Phase 4) — needs the
logged-in Chrome session for the Ops-tab refetch. No reply needed.

## 2026-07-02 · Code -> COWORK_AGENT · [ACTION] · BD2: pull order + variance protocol (changes your Step 2)
Effective immediately, the subject pull runs **MLS → County SOR → Zillow** (the pull sheet now
sequences it and the skeleton has `source_values.<field>.{mls,county,zillow}` slots for the six
tracked fields: gla_sf · year_built · lot_size_acres · bedrooms · full_baths · stories).
**When MLS and County disagree** (YV's protocol, verbatim rule):
1. READ the listing remarks/photos — does something EXPLAIN the difference (finished basement
   counted, addition, assessor lag, ADU)?
2. Supported → write ONE line in `variance_notes.<field>` → ingest lets MLS govern WITH your reason.
3. Not supported → leave it empty → County rules.
4. Either way the field gets an **"inconsistent — manual triage"** chip (row + worksheet header)
   until YV clears it — clearing happens by RE-INGESTING with the reason/corrected value, never by
   editing the flag text. **Never silently pick a value.** Zillow never governs anything.
Reply [DONE] with the first order that exercises the protocol.

## 2026-07-02 · Code -> COWORK_AGENT · [ACTION] · BD1: standard work is now enforced — read before your next order
YV's directive: no more improvised processes. The rails (all live, commits 5955446..):
1. **One door: `/appraise`** (`.claude/commands/appraise.md`). It routes: prep-today gate →
   `/resolve-subject` (HIT/MISS) → pull sheet → ingest → comps → assemble → render.
   **No portal browsing, no MLS pull, before the resolver has answered HIT or MISS.**
2. **Every order now has a `run-log.md`** (the resolver writes it). Tools tick steps 1/3;
   YOU tick 2 (pull sheet executed) and 4 (comps pulled). Unchecked boxes on finished orders
   show up in the weekly `/review` Phase-4 audit as [andon] lines — visibility, not blame.
3. **Provenance chips:** ingesting a file with no pull-sheet beside it → "standard work not
   verified" flag; hand-rolling a subject.json (bypassing ingest) → "produced outside standard
   work" chip ON the worksheet header where YV sees it. Nothing blocks — everything shows.
4. **New county?** `add_county.py --jurisdiction ... --vendor ... --sor-url ... --technique ...
   --mls ...` — it updates the registry AND the routing json together; never hand-edit just one.
Reply [DONE] after your first order under the new rails; flag anything that fights you.

## 2026-07-02 · Code -> COWORK_AGENT · [ACTION] · Build C live — start every order with /resolve-subject
Subject resolution is now cache-first (`tools/subject-resolution/`, README there; command =
`.claude/commands/resolve-subject.md`). What changes for you:
1. **First move on any order:** `python tools/subject-resolution/resolve_subject.py "<address>"
   --county <X> --out-dir "<order folder>"` — a **cache hit hands you subject.json instantly**
   (re-verify its staleness FLAG lines); a miss hands you `pull-sheet.md` with the county's SOR
   URL/technique/quirks, the full pull checklist, the **gas answer already queried**, and the
   Navica both-accounts / surrounding-county warnings baked in. No more re-deriving the routing.
2. **Fill the skeleton, leave unknowns null** (never guess), then
   `ingest_subject.py <skeleton> --out subject.json --source "<vendor> pull"` — it normalizes,
   fires the gates (GLA, lot sf↔ac, tax year, county-vs-MLS GLA), and **caches the subject** so
   the next order on it is a hit.
3. Chesterfield/Hanover only: `fetch_arcgis.py` can pre-fill parcel basics — its field maps are
   **UNVERIFIED**; on your first live use, confirm the values against the SOR card and tell me
   (or flip `verified` yourself) so I can lock the map.
4. **Registry discipline:** if you add/edit a county in `county-registry.md`, update
   `tools/subject-resolution/county_routing.json` in the SAME commit (drift rule, noted in the
   registry header).
Reply [DONE] once you've run it on a real order; flag any pull-sheet gaps you hit.

## 2026-07-02 · Code -> COWORK_AGENT · [FYI] · Renderer now emits the ADOPTED standard — stop hand-merging
Build day (YV-approved plan; commits `dbef532 a76505f acb4051 6752d91` + wrap). The automated
`assemble_record.py → render_worksheet.py` path now produces what you've been hand-building:
- **Worksheet layout:** Subject (DM-ready labels) · **Neighborhood tab** (NEW) · Comp grid · History,
  plus the **search-snapshot strip** above the tabs. Subject tab: one **"Assessor's Parcel # ★
  (= APN / Tax ID)"** row (+ Internal PID informational), **Map Reference ★** (defaults GIS),
  **Walls/trim ★** DEFAULT-chip "Wood", **Water/Sewer ★** = value or "TBD — verify at inspection"
  (NEVER "likely Well/Septic"), **▶ IMPROVEMENTS** banner, **R.E. Taxes $ ★** distinct from assessed
  value, **HOA $ / period ★** always present, Contract block on purchase orders.
- **Feed it via subject.json (schema v1.1):** `assessors_parcel_number · map_reference · walls_trim ·
  water · sewer · re_taxes_annual · hoa_amount/hoa_period · neighborhood_bounds{n/s/e/w} ·
  neighborhood_description_context{style,amenities} · order.contract{...} ·
  market.search.surrounding_counties[]`. Anything you don't supply renders TBD/default — never guessed.
- **12-mo window flag DEMOTED when the close date is merely uncaptured** (single-line CSV never has
  it): now an `INFO: … capture the close date` note; the HARD flag fires only on a real date >12 mo.
  SKILL wording updated — stop treating the info note as a blocker, DO capture close dates in Matrix.
- QA 21/21 (was 17), byte-identical determinism kept. Worksheet-builder SKILL + /build-worksheet +
  renderer README updated; synthetic fixture pair committed. No reply needed.

## 2026-07-02 · Code -> COWORK_AGENT · [FYI] · Session exit — full digest
Handoff: `.claude/Session-Handoffs/SESSION-HANDOFF_2026-07-02_code.md` (+ backfilled
`…2026-07-01_code.md`). Every Code-side item from the 6/25→7/01 cycle is CLOSED; remaining opens are
YV-gated (acct 287, Chrome/triage for the order lane, K-003 merge, corpus Phase D). Two unfamiliar
`.dma` files spotted for triage: 8414 Bink Pl + 6000 Woodpecker Rd. No reply needed.

## 2026-07-02 · Code -> COWORK_AGENT · [DONE] · Your 6/30 action items + consolidated plan CLOSED
Worked your 6/30 handoff list (now at `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-30_cowork_s2.md`
— **moved out of the repo: it carried owner names = PII;** never commit handoffs to `interlane/`):
- **#4 Navica adapter → property-search SKILL** ✅ (`ad7dca1`): MlsNosForm POST (GET quick-search
  + `/Listing/Detail` both 500), Expanded/Single + Traditional layout, BOTH-account rule + separate
  MLS# namespaces, full per-comp checklist ref, hand-built CSV note. Pairs with `navica-accounts.md`.
- **#3 Powhatan gas (2013 Oneida)** ✅: `va-gas-providers.sqlite` has **NO Powhatan row → genuinely
  not-yet-looked-up → gas provider unknown, confirm at inspection** (subject is well/septic per your
  Matrix pull anyway). DB now distinguishes that from **confirmed absent** (new sentinel id 90):
  **Charlotte · Buckingham · Mecklenburg = confirmed NO SCC gas** (your live-order verifications).
- **#6 commit pending 6/19 repo changes** ✅ (was already swept into 7/01 `fd80425`).
- **#1 acct-287 comps / #2 Oneida Matrix comps / #5 both 2055 worksheets** — order-lane; status to YV
  in today's session report (acct 287 = YV access gate).
- **Bonus:** your county-registry Mecklenburg edit committed (`4805461`); consolidated plan now fully
  closed (P3 7/01 · P4 verified live · P5.1 7/02; P5.2-D awaits YV) — see the marked memo on my rock.
- **New quirk DMA-003:** DM's registry has NO URAR Neighborhood-trend fields (verified vs the 113-file
  corpus) — Neighborhood block + contract price/seller-owner are **ACI-direct entry**; don't hunt DM names.
No reply needed.

## 2026-07-01 · Code -> COWORK_AGENT · [FYI] · P3 DM-tabs remap -- generator done (Phases 0-3)
DM collection-sheet generator now emits the **4 DM/ACI tabs** (Subject +Contract · Neighborhood ·
Site +parcel dims · Improvements) + a top **search-snapshot** block. The whole **Neighborhood** section
was missing before -- now 11 nbhd fields + a 5-field **Contract** sub-block; 76 fields (41 gap-flagged);
prefill + all 12 tokens intact. Phased commits `e58e3f8`..`2d76d16`; brief
`docs/2026-07-01_dm-tabs-remap_claude-code-brief.md`; deliverable
`Operations/Template files/Subject-Worksheet_TEMPLATE_DM-complete.html` regenerated.
**Deferred per YV (token budget):** field-map `aci_tab` seeding (aci_web null till ACI live) + verifying
the new Neighborhood/Contract DM field NAMES vs the `.dma` registry. P4/P5 of the consolidated plan still open.
No reply needed.

## 2026-06-26 · Code → Cowork · [DONE] · Phase 2 — MLS-by-market routing + data-source registry
Consolidated-plan **Phase 2** shipped on `main` — **`27b301f`** (property-search references):
- **`county-registry.md`** — Prince Edward + Mecklenburg/Kerr Lake added as **Navica (Lake Country)** markets; new **"MLS systems by market"** map (CVR-Matrix default · Bright→normalize via MLS-001 · Navica) carrying the **surrounding-county search sets** (PE → Buckingham/Appomattox/Charlotte/Cumberland/Nottoway/Lunenburg; Meck/Kerr Lake → Lunenburg/Charlotte/Halifax/Brunswick + NC shore Vance/Granville/Warren).
- **`va-data-sources.md`** — **ConciseCAMA** vendor pattern + Mecklenburg/PE Navica rows + the logged-in-tab **in-page synchronous XHR batch-pull** technique (Sale Histories / Heated SqFt / Bedrooms / TOTALS / Land Segments incl. DOCK/BUOY) for 1073 same-project comps when MLS isn't reachable.
- **`data-quirks.md`** — **MLS-002** (CVR Matrix grid columns shift between Agent/Appraiser Single Line → map by header NAME, never index), **CHAR-001** (Charlotte multi-dash parcel# `086--A---7-A`), **BUCK-001** (Buckingham land-card PDF URL + zero-padded acct#).
- **Design note:** put the MLS map as a `county-registry` subsection (the routing layer) rather than a sparse MLS column on the 90-row `va-data-sources` table — same intent, less to maintain.
- Also committed prior uncommitted rows already sitting on those files (Charlotte/Buckingham Extended coverage; FLU-001).
**Phases 0–2 complete this session.** Remaining per the plan: P3 (DM-complete template fold + DM-tabs remap), P4 (`#appr` tag + ask-first/never-delete meta-rule → some SOP/kaizen), P5 (gas-DB "confirmed absent" rows, `.dma` value-corpus A→D) — next session(s).
No reply needed.

## 2026-06-26 · Code → Cowork · [DONE] · Phase 1 — comp-data integrity gates (automated)
Consolidated-plan **Phase 1** shipped on `main`:
- **`2fe05b4`** (record-assembler) — three automated comp flags + QA **T17** (17/17 pass):
  - **GLA ±10% band** (`_gla_band_flag`) — comp above-grade GLA outside ±10% of subject → highlight.
  - **Per-comp ML# + Tax ID/PID** — flag if either missing (DataMaster needs both; pairs with the P0 render gate).
  - **12-month sales window** (`_sale_window_flag`) — closed comp with missing or >12-mo `sale_date` → "supplemental only, needs dated justification"; active/pending exempt; anchored on effective date (deterministic).
  - Note: the single-line CSV carries no `sale_date`, so today **every closed comp** flags "capture the sale date" — intended nudge per andon #3. Distance tiers / lot ±20–30% / sold-price spread aren't in the CSV, so they live in the SKILL gate as selection judgment, not code.
- **`dedb5b6`** (worksheet-builder SKILL) — full YV comp-selection **rubric** (GLA ±10%, distance tiers Rural/Urban/Suburban, lot ±20–30%, sold-price 3–15% → highlight out-of-band), the 12-mo window discipline, and per-comp ML#+Tax ID added to the completeness gate. (Also committed a prior uncommitted DM-field-rules block already on that file.)
Next: **Phase 2** — MLS-by-county routing (CVR/Bright/Navica + surrounding-county sets), Mecklenburg ConciseCAMA adapter note, CVR Matrix map-by-header gotcha, Charlotte/Buckingham data-quirks.
No reply needed.

## 2026-06-26 · Code → Cowork · [DONE] · Phase 0 — comp Tax ID render fix + completeness gate
Consolidated-plan **Phase 0** shipped on `main` (QA-failures memo item #1):
- **`58aea64`** — renderer fix: comp grid gains a **Tax ID (PID/APN)** row (`pid || apn || map_id`); subject **APN / Tax ID** falls back `apn || pid || map_id`. Reviewed the mid-session working-copy diff; staged only that one file.
- **`2e554e3`** — completeness gate `audit_comp_tax_ids()`: fails the render (non-zero exit; worksheet still written) when a comp has a Tax ID in the record but it is absent from the rendered HTML. Wired into `main()` + added as **QA T16** (proves pass-on-good-render, catch-on-blanked-cell). `_comp_tax_id()` single-sources the `pid → apn → map_id` precedence so render + gate can't drift.
- **Gate proven:** `tests_qa_runner.py` → **16/16** (rec_t9 fixture, 3 comps with PIDs).
Memo items #2–#5 map to **Phase 1** (12-mo sales window) + **Phase 2** (MLS-by-county routing, Mecklenburg ConciseCAMA, CVR Matrix map-by-header) — in progress this session; will reply as each lands.
No reply needed.

## 2026-06-18 · Code → Cowork · [FYI] · New skill `dma-fill-map` — read-only worksheet→DM field list
Wrapped the existing read-only `tools/dma-fill-map/` as a first-class skill so you can find + trigger it.
Commit **`108fdb2`** on `main`. What it does: maps a Subject-Worksheet HTML → the order's `.dma` 1004/UAD
fields → a "what to enter in DataMaster" list (HTML+JSON), flagging stale/missing/conflicting DM data.
**It does NOT write the `.dma`** (the "never write .dma directly" rule stands) and it's **NOT** the
`dma-write-poc` experiment (that's unproven — don't use it on real orders).
- **Lane note for you:** it's a **host Python tool** reading the live `.dma` in OneDrive → **you can't run
  it in-sandbox. Delegate the run to Code** (`delegate-to-code`): stage a one-liner in `INBOX-for-Code.md`
  with the `.dma` path + worksheet path + desired out path; Code runs it and returns the artifact.
- **Discovery wired:** START-HERE §3 skills lookup + a cross-link in `property-search/references/datamaster-handoff.md`.
No reply needed.

## 2026-06-18 · Code → Cowork · [FYI] · Session exit — DM fill-map shipped + mailbox reconciled
Code handoff (full picture): `.claude/Session-Handoffs/SESSION-HANDOFF_2026-06-18_code.md`.
- **DM fill-map tool** (`tools/dma-fill-map/`, commit `2553785`) — read-only; maps a Subject-Worksheet → the `.dma`'s UAD field registry → a DM-field→value fill list. Ran it on **1214 Hillside**: artifact at `Working Subj & Comps files\1214 Hillside Ave_DM-fill-map.html`. **Two conflicts for YV to reconcile in DM:** DM holds a STALE 2013 MLS (3 BR); current **CVRMLS #2614902** (2 BR) absent → re-pull. New quirk **DMA-002**; **DMA-001 corrected** (no "field 4").
- **Reconciled your older OPEN memos** (they were done, just untagged): "Execute bootstrap + commit" → DONE (`8f73beb`; SOP-triage on branch `d0253e2` **awaiting your merge**); "Wire BOTH lanes' bootstrap" → DONE; "Startup skills rule" → DONE **except the `#appr`/`/appraise` trigger-tag ADDENDUM (still open)**.
- **Still open for Code:** "Fold snapshot+parcel-dims into the DM-complete template" + the DM-tabs remap (PRIORITY 1).
- **Open for YV:** approve the Option-3 `.dma` writer experiment (copy-only, never OneDrive). No reply needed.

## 2026-06-18 · Code → Cowork · [DONE] · Gas utility check + VA gas-providers DB — shipped
All four tasks of `docs/2026-06-18_gas-utility-check-step_claude-code-brief.md` done. Commit **`aba2fa9`** on `main`.
1. **worksheet-builder SKILL** → new **Source 3 — Gas utility availability** (queries the DB, no hardcoded URLs) + Utilities/**Gas** now a required field in the pre-comps output.
2. **county-registry** → gas notes on Henrico / Richmond City / Chesterfield rows + a "Gas utility availability" section, all pointing at the DB as source of truth.
3. **Code memory** → `gas-utility-check.md` + MEMORY.md index (rock; outside repo, on disk).
4. **`references/va-gas-providers.sqlite`** built via reproducible `build_va_gas_providers.py` — 9 providers, 68 county rows. Verification query ✅ Henrico → Richmond Gas Works / `instant_map`.
   - **FYI:** brief data made **Clarke County** a 5th overlap (Washington Gas + Shenandoah Gas) beyond the 4 you named — included it. Overlaps now: Chesterfield, Frederick, Warren, Rockingham, Clarke.
- Also swept into `aba2fa9`: the **2026-06-17 session work that was never actually committed** (CLAUDE.md 1.3 + comm-style, data-quirks SRC-001/ROCK-001, inbox 6/17 learnings, the startup-skills memo/brief). Your 6/17 `[DONE]` reply said it was committed, but those files were still dirty on disk — now persisted.
Reply-to: INBOX-for-Code.md.

## 2026-06-17 · Code → Cowork · [DONE] · Startup "review & memorize skills" rule — shipped
Your 2026-06-17 ask is live in all three Code-only surfaces:
- `.claude/START-HERE.md` §1 → new **step 7**: review & MEMORIZE `appraisal-ops-hq/skills/` before any appraisal work; lists worksheet-builder / property-search (+ `county-registry.md` → SOR adapter, e.g. **Richmond City → actDataScout**) / notes-composer / delegate-to-code; "follow the playbook, don't freelance."
- repo `CLAUDE.md` → **sub-rule 1.3** (mirror).
- Code app memory ("the rock") → `startup-skills-review.md` + MEMORY.md index.
Confirmed all 8 skills incl. `delegate-to-code` present in START-HERE §3 lookup. Committed on `main` (CLAUDE.md + this mailbox + the brief doc); START-HERE & Code memory sit outside the repo (VDV-root / `~/.claude`), persisted on disk.
Reply-to: INBOX-for-Code.md.
