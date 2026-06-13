# /build-worksheet — end-to-end appraisal worksheet orchestrator

Chains property-search → record-assembler → worksheet-renderer → notes-composer
for a single order. Produces a review-ready HTML worksheet + draft notes.
The licensed appraiser reviews, adjusts, and certifies — Claude never auto-submits.

---

## Before you start

Read `CLAUDE.md` cardinal rules. Key constraints for this command:
- **Client data never enters the repo.** All outputs go to `C:\Users\yuriy\VDV Appraisals\<order-folder>\`.
- **Confirm before any side effect** (downloads, Matrix exports, DataMaster imports).
- **One Matrix/DataMaster session at a time** (Identity Conflict / git-corruption andon).
- **GDrive is read-only by default.** Never write there without an explicit request.

---

## Usage

```
/build-worksheet <address>
/build-worksheet <address> --order-id 26-0042 --client "First National Bank"
```

Or, if subject.json and comps CSVs already exist on disk:

```
/build-worksheet --subject "C:\...\subject.json" --comps "C:\...\comps_appraiser.csv"
```

---

## Step 1 — Resolve subject + pull comps  *(property-search skill)*

**What this does:** Runs the `property-search` skill to gather subject facts from
the county assessment portal (governing SOR), cross-check with Zillow/Realtor/Redfin,
pull MLS# history, and select/confirm comp candidates from Matrix.

**Inputs:** Address (or order folder if subject.json already exists)  
**Outputs:**
- `subject.json` → `C:\Users\yuriy\VDV Appraisals\<order-folder>\subject.json`
- Comp CSV(s) → `C:\Users\yuriy\VDV Appraisals\Comps files\<addr>_comps_appraiser-single-line.csv`
  (and optionally `_agent-single-line.csv` for active/pending listings)

**Rules:**
- Obey the one-session rule: only one Matrix/DataMaster login active at a time.
- MLS# normalization: `BRTVA…` → strip `BRT`, keep `VA…` before feeding DataMaster.
- New construction (no APN): flag `resolution.no_tax_id=true`; appraiser enters subject manually in DataMaster.
- Confirm with the user before downloading/exporting from Matrix.

**Stop here** and surface the comp list + any flags for appraiser confirmation before proceeding.

---

## Step 2 — Assemble record  *(record-assembler)*

**What this does:** Runs `tools/record-assembler/assemble_record.py` to merge
subject.json + comps CSV(s) into `appraisal-record.json`.

```powershell
python tools/record-assembler/assemble_record.py `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\subject.json" `
    "C:\Users\yuriy\VDV Appraisals\Comps files\<addr>_comps_appraiser-single-line.csv" `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\appraisal-record.json" `
    [--comps-agent "..._agent-single-line.csv"] `
    [--order-id <ID>] [--client <CLIENT>] [--effective-date <DATE>]
```

**Output:** `appraisal-record.json` → per-order folder  
**Surface to appraiser:** the printed summary line (closed/active counts, flags, out-of-county).

**Review flags before proceeding:**
- `GLA unverified` → appraiser must supply GLA; do not guess.
- `Out-of-county` → verify comp in county SOR before using.
- `MLS# normalized` → confirm the stripped VA… number resolves in DataMaster.
- `Unknown status` → appraiser determines closed vs active.

---

## Step 3 — Render worksheet  *(worksheet-renderer)*

**What this does:** Runs `tools/worksheet-renderer/render_worksheet.py` to produce
a self-contained tabbed HTML worksheet for copy-paste into ACI.

```powershell
python tools/worksheet-renderer/render_worksheet.py `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\appraisal-record.json" `
    -o "C:\Users\yuriy\VDV Appraisals\<order-folder>\worksheet.html"
```

**Output:** `worksheet.html` → per-order folder  
Open in browser and confirm: Subject tab shows correct GLA/year/baths, Comp grid shows
closed comps in the top grid and active/pending in the lower grid.

---

## Step 4 — Draft notes + adjustment hints  *(notes-composer skill)*

**What this does:** Runs the `notes-composer` skill using the assembled record to
draft narrative notes (neighborhood, market conditions, sales-comparison comments,
reconciliation) and surface typical adjustment magnitudes from the playbook.

**Form-type routing:**
- 1004: full library coverage (neighborhood, 1004MC market, prior-sale, reconciliation, addendum)
- 1004C: condo sections covered
- 2055 / 1025: partial coverage — flag gaps to appraiser

**Output:** draft notes text (in chat) for each note field. Each draft:
- Fills `{date}`, `{county}`, `{subdivision}`, `{mls_number}` slots from the record.
- Marks judgment slots as **[APPRAISER: ...]** — never fills these with canned text.
- Cites the playbook range for each adjustment category (e.g., "GLA: ~$75/sf typical").

**Important:** Notes-composer drafts; the licensed appraiser edits and certifies.

---

## Step 5 — Hand off

Present the appraiser with:
1. `worksheet.html` path — open in browser; use tabs for review.
2. Draft notes — for each field, paste into ACI after editing.
3. Adjustment hints — appraiser enters final $ amounts; never auto-filled.
4. Flag list — any `GLA unverified`, `Out-of-county`, or `Unknown status` items requiring action.

**STOP. Never submit to ACI or any portal. The appraiser reviews, adjusts, and certifies.**

---

## Conflict / flag protocol

Surface these explicitly at each step rather than silently continuing:
- GLA conflict (county vs MLS vs PR) → stop, show all three values, ask appraiser which governs.
- Out-of-county comp → ask whether to keep or drop; if keep, note SOR verification needed.
- Fewer than 3 closed comps → flag; appraiser may need to widen search or add sales.
- `no_tax_id=true` → remind appraiser to enter subject manually in DataMaster before import.
