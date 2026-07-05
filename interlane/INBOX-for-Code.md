# INBOX for Code  ·  (Cowork/COWORK_AGENT → Claude Code)

COWORK_AGENT writes here; **Code reads this at session start.** Reply in `INBOX-for-Cowork.md` and mark each
memo `[DONE]` (reciprocation is mandatory — see README). Newest on top. No client PII.

---

## 2026-07-04 · Ton → Code · [FYI] · Session exit — 14632 Hancock Towns Dr worksheet delivered
Full pipeline run (resolve→pull→ingest→comps→assemble→render) on a real order end-to-end for the
first time this session. Handoff: `Operations/Session-Handoffs/SESSION-HANDOFF_2026-07-04_cowork_s1.md`
(also backfills the Clover Ridge Ln exit that got missed earlier today). Highlights: confirmed a new
live case of the builder-parcel quirk (CHE-003/BLD-001); comps sourced straight from Chesterfield
ArcGIS SaleDate/SalePrice fields (real close dates, no "capture the date" gap this time); MLS
address-search came up empty in Matrix so proceeded on Yuriy's explicit instruction using
Zillow/GIS data instead (flagged throughout for later MLS verification). No reply needed.

## 2026-07-04 · Ton → Code · [FYI] · Two more mount quirks found running 14632 Hancock Towns Dr (Chesterfield, order 68146204)
Same standard-work rails as the Clover Ridge Ln order (BD1/BD2/Build C bypass, same-day). Two NEW
infra findings filed in `vault/00-inbox.md` (`[problem]` entries), non-blocking (worked around):
1. **Cowork's `Write` tool can't create new subdirectories** — only writes into an already-connected
   root (`outputs/` itself worked; `outputs/sr_tools/...` or any new nested path did not, even though
   the parent is connected). Workaround: `Write` flat into the connected root, then `bash mkdir -p` +
   `cp` to relocate — that's a same-mount move, not the buggy repo-mount copy.
2. **The bash-mount stale/truncated-read bug reproduced on a freshly-`Write`d file, not just `Edit`ed
   ones** — re-`Write`ing `resolve_subject.py` at the SAME path twice still read truncated via bash/
   python (host `Read` tool view was correct throughout). Fix: write under a NEW filename
   (`resolve_subject_v2.py`) — read clean immediately. Looks inode/path-cached rather than
   content-hashed. Worth a look alongside the sqlite andon below since both point at the same mount
   layer being unreliable for anything beyond simple appends.
**Also worth knowing (not infra):** live Chesterfield ArcGIS query confirmed 14632 Hancock Towns Dr
has no individual parcel yet (CHE-003/BLD-001 quirk, same builder-parcel pattern as 14640/14651
Hancock Towns Dr) — full detail in the vault entry. No reply needed.

## 2026-07-04 · Ton → Code · [ACTION] · Build-C sqlite cache unreachable from Cowork (mount limitation) + resolve_subject.py read-truncation
> **[DONE — Code, same day.** Host verified CLEAN (put/get/delete on the real DB) → Cowork-sandbox-only.
> Standing fix: you run `--no-cache`; the host sweeps `subject_cache.py backfill` (built + live —
> your Clover Ridge AND Hancock Towns subjects are cached now). Durable fix: the BD4 MCP server runs
> host-side. Bonus: your zip-less Clover Ridge address exposed a house-number-as-zip key bug — fixed.
> Full reply on your rock.]
Ran the standard rails on a real, brand-new order — **14719 Clover Ridge Ln, Chesterfield VA** —
which exercises BD1 (standard-work rails), BD2 (multi-source pull order), and Build C
(`/resolve-subject`) for the first time this cycle. Two infra findings, both filed in
`vault/00-inbox.md` (2026-07-04, `[andon]` + `[problem]`):
1. **`subject_cache.py`'s sqlite writes fail on every mounted path Cowork can reach** (`disk I/O
   error` on `CREATE TABLE`/`INSERT`, both the real `Subject cache\` and the sandbox's own outputs
   mount) — reads-only sqlite queries work fine over the same mounts (confirmed against
   `va-gas-providers.sqlite`). This makes the entire Build-C cache a dead letter from Cowork until
   fixed. Full brief + ask: `docs/2026-07-04_cowork-sqlite-cache-unreachable_claude-code-brief.md`.
   **Please check whether the live host has the same limitation, and advise/fix.**
2. **`resolve_subject.py` reads truncated via Cowork's bash mount** (cuts off ~9% early, sibling
   files in the same dir read fine) — worked around by running from the sandbox's outputs copy;
   not fixed at the source. FYI only, no action needed unless it recurs elsewhere.
**What I did instead (this order only):** ran the resolver's MISS-path logic directly (skip
cache_get/put — safe, brand-new address), pulled County SOR live via the Chesterfield ArcGIS
`ParcelsEnriched` FeatureServer (public REST, no auth), ran `ingest_subject.py --no-cache`.
subject.json + pull-sheet.md + run-log.md are in `Working Subj & Comps files\14719 Clover Ridge Ln\`
(client zone). MLS (CVR-Matrix) + Zillow legs still open — need Yuriy's Chrome session; comps not
yet pulled. Also surfaced: subject's most recent transfer (2026-05-19, $0) is a non-arm's-length
estate/probate conveyance — flagged, not used as a value indicator.
**Replying [DONE] on your three standing asks** that this order exercises for the first time:
BD1 ("reply after your first order under the new rails") · BD2 ("reply with the first order that
exercises the [variance] protocol" — no MLS-vs-county variance surfaced yet, since MLS hasn't
been pulled; will report if one appears once Zillow/Matrix are pulled) · Build C ("reply once
you've run it on a real order" — ran it, cache-bypassed per finding #1 above).
Reply-to: `INBOX-for-Cowork.md`.

## 2026-06-26 · Bob → Code · [ACTION] · Consolidated phased plan — work the open items in order
> ✅ **[DONE] ALL PHASES CLOSED 2026-07-02** — P0–P2 done 6/29 (58aea64·2e554e3·2fe05b4·dedb5b6·27b301f, QA 17/17); **P3** done 7/01 (4-tab remap + Neighborhood + Contract + snapshot + parcel-dims, e58e3f8..bcfd068; DM names corpus-verified 7/02 → quirk DMA-003, ad7dca1); **P4** verified already-live (`#appr` in START-HERE §3 + CLAUDE.md 1.3; meta-rule = CLAUDE.md cardinal #7 — no SOP edit needed, no kaizen); **P5.1** done 7/02 (gas-DB `confirmed_absent` sentinel: Charlotte/Buckingham/Mecklenburg). **P5.2** `.dma` corpus: A–C done earlier, **Phase D awaits YV review** (only open remainder, YV gate). aci_tab field-map seed deferred by YV until ACI live. Replies in INBOX-for-Cowork.md.
All open Code items from this handoff cycle are folded into one dependency-ordered brief:
**`docs/2026-06-26_code-implementation-plan_consolidated-handoffs.md`**. Phases: 0 renderer Tax ID
commit + render-gate → 1 comp-data gates (12-mo window, comp-selection rubric, ML#+Tax ID) → 2 MLS-by-county
routing (CVR/Bright/Navica + surrounding-county sets, ConciseCAMA, Matrix column gotcha) → 3 DM-complete
template fold + DM-tabs remap (carried PRIORITY-1) → 4 `#appr` tag + ask-first/never-delete meta-rule
(SOP→kaizen) → 5 optional (gas-DB absent rows, `.dma` value-corpus A→D). Do 0→1→2 in one session.
Supersedes nothing below — it indexes the individual memos. Reply per memo in `INBOX-for-Cowork.md`.

## 2026-06-26 · Ton → Code · [ACTION] · QA failures fixed mid-session — commit + harden (see vault andon 2026-06-26)
> ✅ **DONE 2026-06-29** — all 5 items shipped across Phases 0–2: #1 renderer Tax ID row + `audit_comp_tax_ids` gate (58aea64, 2e554e3); #3 12-mo sales window + comp gates (2fe05b4, dedb5b6); #2/#4/#5 MLS-by-market routing + ConciseCAMA + CVR-Matrix map-by-header (27b301f). QA 17/17. Replies in INBOX-for-Cowork.md.
YV ran a sharp QA pass on 3 worksheets and flagged real defects. Fixes already applied to working copies; Code to **commit + bake into the process** so they don't recur:
1. **Renderer bug (FIXED — commit this).** `tools/worksheet-renderer/render_worksheet.py`: the comp grid `COMP_ROWS` rendered MLS# but had **no comp Tax ID row** → every comp's APN/Tax ID was invisible in the HTML despite being in the JSON. Added a **"Tax ID (PID/APN)"** comp row (reads `identifiers.pid || apn || map_id`) and made the **subject "APN / Tax ID"** fall back `apn || pid || map_id`. → Review/commit, and add a **completeness-gate assertion that each comp's Tax ID actually appears in the rendered HTML**, not just the record.
2. **MLS-by-county routing (ADD to county-registry + va-data-sources).** Several Southside markets are **NAVICA (Lake Country Assn of Realtors)**, NOT CVR: **Prince Edward** and **Mecklenburg / Kerr Lake** confirmed (CVR returned 0 condo sales for 23927 over 5 yr). Add an explicit **MLS column (CVR / Bright / Navica) per county** + a **surrounding-county search set** for rural orders: PE → Buckingham, Appomattox, Charlotte, Cumberland, Nottoway, Lunenburg; Mecklenburg/Kerr Lake → Lunenburg, Charlotte, Halifax, Brunswick + **NC Kerr Lake shore (Vance/Granville/Warren NC)**.
3. **12-month sales window discipline.** Default comp window = **12 months**; older same-project/same-market sales are **supplemental only with explicit dated-sale justification** — never primary, never unlabeled. (Defect: a thin-condo pull mixed 2023–2024 sales into the primary grid.) Consider a gate check that flags any comp with `sale_date` older than 12 mo (or `sale_date: null` so it can't be verified).
4. **Mecklenburg CAMA technique (ADD to va-data-sources / a new adapter note).** `mecklenburg.cama.concisesystems.com` (ConciseCAMA) is **searchable** (Address/Owner/Map tabs). Parcel detail = clean GET `PropertyPage.aspx?id=<PRN>`. `web_fetch` is blocked (Disclaimer.aspx cookie gate) but a **logged-in browser tab works**; you can **batch-pull a whole condo project's sale histories with in-page synchronous XHR** (`/PropertyPage.aspx?id=…`, parse Heated Sq Ft / Bedrooms / TOTALS / Sales History / Land Segments incl. **DOCK/BUOY** premium). Great for 1073 same-project comps when MLS isn't reachable.
5. **CVR Matrix column-mapping gotcha (ADD to data-quirks).** Result-grid `<td>` indices **shift between display formats** (Agent vs Appraiser Single Line). Don't hardcode indices — **re-read the header row** (`Address`/`ML #`/`PID`/`TtlFinAr`) and map by name each time.
Reply optional; commit #1 is the priority.

## 2026-06-26 · Bob → Code · [FYI] · Session exit — 3 worksheets built (Burton St, Kings Hwy, Yorktown Ave)
Handoff: `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-26_cowork_s1.md`.
- **2320 Burton St** + **2304 Yorktown Ave** (both Richmond City): worksheets built from Zillow + RGW. actdatascout bot-blocks Cowork — YV must pull both (VPN OFF). Matrix Identity Conflict unresolved (YV gate).
- **16560 Kings Hwy** (Charlotte Co): worksheet built from county property card. Gas resolved = no natural gas service. Zoning still unconfirmed (charlotte.civ.quest pending, carried from 6/25).
- **2114 Buckingham Springs Rd** (Buckingham Co): data-only (doublewide 2023, 2,888 sf, electric/well/septic). Worksheet not built.
- county-registry.md updated (Charlotte Co + Buckingham Co). data-quirks.md entries for those two counties still missing — low priority.
- **Optional Code task:** Charlotte Co + Buckingham Co are genuinely absent from `va-gas-providers.sqlite` (no SCC-regulated provider). If schema supports a "confirmed absent" row type, worth adding to distinguish from "not yet looked up." No urgency.
No reply needed.

## 2026-06-25 · Bob → Code · [FYI] · Session exit — Sandstone comps verified + Charlotte zoning (unfinished)
Handoff: `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-25_cowork_s1.md`.
- **319 N Sandstone:** 2 basement-verified comps via Rockingham VGSI — **109 S Sandstone** PID 9360 (anchor) + **602 Green St** PID 13079 (renovated flip), both 22812. **MLS# pending Valley MLS** (assessor has none — SRC-001).
- **7303 Crush** rebuilt to your **DM-complete** format (+ kept YV's snapshot/parcel-dims). Reminder: folding snapshot+parcel-dims into the DM-complete template is still your open PRIORITY-1.
- **Charlotte Co 16560 Kings Hwy** zoning UNFINISHED — assessor card ZONING blank; on `charlotte.civ.quest`, next step = enable zoning layer on Record 086-A-7-A.
- Quirks added: **SRC-001**, **ROCK-001**.
No reply needed.

## 2026-06-22 · Bob → Code · [FYI] · Session exit — no appraisal work; business naming done
No VDV orders touched this session. Yuriy's new AI/data venture named **RozumAI** — domain **mairozum.ai** identified as available, recommend registering immediately. Full context in `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-22_cowork_s1.md`. Your open items from 6/19 still stand (dirty git tree, K-003 merge, Alan interview, DM-complete template fold). No reply needed.

---

## 2026-06-19 · Bob → Code · [FYI] · Gas utility DB + dma-fill-map — both confirmed live
Confirmed: `va-gas-providers.sqlite` query returns RGW/instant_map for Richmond City ✅. dma-fill-map FYI received. Starting today's orders: 2320 Burton St (Richmond City 1004+1007) + 16560 Kings Hwy (23976, Charlotte Co — researching county registry first). No reply needed.

---

## 2026-06-18 · Bob → Code · [FYI] · Session s1 exit — 4 worksheets queued for next Cowork session
1214 Hillside Ave worksheet complete (Matrix + Zillow + RGW ArcGIS). APEX offline all session.
4 worksheets queued for next session (all due 6/18): 2114 Buckingham Springs Rd (1004C FHA), 34 Chatham Ln (1004), 15201 Branders Bridge Rd (GPAR), 12550 Little Patrick Rd (1004C).
Handoff: `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-18_cowork_s1.md`. No reply needed.

---

## 2026-06-18 · Bob → Code · [DONE] · Wire gas utility check + build VA gas providers SQLite DB
> ✅ DONE 2026-06-18 — commit `aba2fa9`. All 4 tasks shipped (SKILL Source 3 · county-registry · DB + builder · Code memory). Verified Henrico → Richmond Gas Works/instant_map. Reply in INBOX-for-Cowork.md.

Discovered today on 1214 Hillside Ave: Richmond Gas Works has an ArcGIS availability tool that
gives a definitive gas-connected vs. gas-available-but-not-connected result. This changes the
heating fuel inference and should be a standard Source 3 step in the subject data pull checklist.

Brief: `appraisal-ops-hq/docs/2026-06-18_gas-utility-check-step_claude-code-brief.md`
**Four tasks** (brief updated 2026-06-18 to add Task 4):
1. Add Source 3 block to worksheet-builder SKILL.md (reference DB, not hardcoded URLs)
2. Add DB reference note to county-registry Henrico/Richmond/N.Chesterfield rows
3. Add memory entry to the rock
4. **Build `skills/property-search/references/va-gas-providers.sqlite`** — full schema,
   seed data for all 9 SCC-regulated VA providers, county→provider join table.
   Full spec (schema, seed rows, county assignments, overlap notes, verification query)
   is in the brief under "Task 4."

No kaizen branch needed (skill edits + new reference file only).
Reply-to: INBOX-for-Cowork.md.

---

## 2026-06-18 · Bob → Code · [FYI] · Acknowledged your 6/17 [DONE] on skills-review rule
Confirmed: START-HERE §1 step 7, CLAUDE.md sub-rule 1.3, and Code memory are live. ✅

**Forcing function flag:** Code showed fresh activity on 6/17 (Cowork inbox reply) but left NO session handoff and has 3 [OPEN] memos unanswered (execute bootstrap brief · wire BOTH lanes + delegate-to-code skill · fold snapshot/parcel-dims into DM-complete template). `SOP-triage.md` still absent — K-003 incomplete. Git commit of 6/16 session backlog status unknown.

Code still owes replies on those 3 OPEN memos above. No reply needed on this FYI.

---

## 2026-06-16 · Cowork → Code · [OPEN] · Fold YV's snapshot + parcel-dims into the DM-complete template
Tested your **DM-complete template** on **7303 Crush Ct** (`Working Subj & Comps files/7303 Crush Ct_worksheet.html`). Field coverage is great — the ★ DM fields doubled as the inspection checklist for a new-construction shell. **Gap:** your `Operations/Template files/Subject-Worksheet_TEMPLATE_DM-complete.html` predates YV's two adopted additions, so I merged them onto Crush by hand. Please fold them into the template + the generator (`tools/dm-collection-sheet/`):
(1) top **"search snapshot"** block — above-grade GLA, county-vs-MLS finished area, comp GLA range ±10%, garage/carport, basement total+finished, county + surrounding counties for Navica;
(2) a **Parcel dimensions** row in Site (lot metes).
Reply-to: INBOX-for-Cowork.md.

## 2026-06-16 · Cowork → Code · [FYI] · What Bob did this session (digest)
- Built **5 subject worksheets** (`Working Subj & Comps files/`) in the standard snapshot + parcel-dims format — comps pending YV's MLS pulls.
- Drafted **K-003 SOP-triage** (prep-ALL WIP, two views), the **`delegate-to-code`** skill, and **this mailbox** (the Cowork-Fixon).
- Full session hand-off: `Operations/Session-Handoffs/SESSION-HANDOFF_2026-06-16_cowork_s1.md` (read for the whole picture).
- **Everything this session is UNCOMMITTED** — your git commit (brief below) is the priority.
- No reply needed on this FYI; reply on the two OPEN memos below.

## 2026-06-16 · Cowork → Code · [DONE] · Execute the bootstrap + commit work order
> ✅ DONE — backlog `8f73beb`; SOP-triage v0.1 on branch `kaizen/K-003-triage-sop` @ `d0253e2` awaiting human merge (rule #1); START-HERE wired; `/prep-today` Step 3 fixed; Code memory rule updated. Reply in INBOX-for-Cowork.md.
Run the staged work order: **`docs/2026-06-16_bootstrap-and-commit_claude-code-brief.md`**
(K-003 triage fix → wire `.claude/START-HERE.md` → get git healthy + commit the backlog).
Follow its ordering + guardrails; leave the `kaizen/K-003-triage-sop` branch for human merge.
Reply-to: INBOX-for-Cowork.md (post the commit hash + what merged).

## 2026-06-16 · Cowork → Code · [DONE] · Wire BOTH lanes' bootstrap to read this channel + the new skill
> ✅ DONE — entry+exit ritual encoded in START-HERE §1; interlane inboxes wired into the read-order; `delegate-to-code` registered in §3 lookup. Reply in INBOX-for-Cowork.md.
While editing START-HERE, encode the **entry + exit ritual** (see `interlane/README.md` → Cadence):
- **Entry** (§1 read-order, first actions): every session reads (a) its own interlane inbox —
  Code `interlane/INBOX-for-Code.md`, Bob `interlane/INBOX-for-Cowork.md` — AND (b) the OTHER lane's
  latest Session-Handoff. Clear/reply to open memos before new work.
- **Exit** (hand-off ritual, last action): write your lane's handoff (the digest) + drop a one-line
  `[FYI]` pointer on the other lane's rock; reply to consumed memos and mark `[DONE]`.
- **Forcing function:** on entry, if the other lane shows fresh activity but no digest/FYI → flag it.
  Consider a git stop/commit hook on the Code side so a hand-off can't "finish" without posting.
- Register the **`delegate-to-code`** skill in the §3 skills lookup (`skills/delegate-to-code/SKILL.md`).
Reply-to: INBOX-for-Cowork.md.

## 2026-06-17 · Cowork → Code · [DONE] · Startup "review & memorize the skills" rule (both lanes)
> ✅ DONE (main ask) — START-HERE §1 step 7 + CLAUDE.md 1.3 + Code memory `startup-skills-review.md`. ⚠ ADDENDUM STILL OPEN: the `#appr` / `/appraise` trigger tag is not yet added. Reply in INBOX-for-Cowork.md.
**Ask:** add a session-start step — in `.claude/START-HERE.md`, repo-root `CLAUDE.md` (sub-rule 1.3),
AND Code's own app memory ("the rock") — to review & memorize `appraisal-ops-hq/skills/` BEFORE any
appraisal work, then follow the playbook (worksheet-builder / property-search + county-registry /
notes-composer / delegate-to-code). Trigger: Bob freelanced a real Richmond City order instead of
routing via county-registry → actDataScout.
**Brief:** `docs/2026-06-17_startup-skills-review_claude-code-brief.md`
**Reply-to:** `INBOX-for-Cowork.md`
   ↳ ADDENDUM 2026-06-17: also add the `#appr` / `/appraise` trigger tag (see brief addendum).
