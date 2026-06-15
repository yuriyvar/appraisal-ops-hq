# /build-worksheet — end-to-end appraisal worksheet orchestrator

> **Runtime: CLAUDE CODE.** This command is the automated, programmatic orchestrator
> (runs the tools once `record-assembler` exists). **In Cowork, use the `worksheet-builder`
> skill instead** (`skills/worksheet-builder/SKILL.md`) — the interactive path, same
> deliverable + same completeness gate.

Chains property-search → record-assembler → worksheet-renderer → notes-composer
for a single order. Produces a review-ready HTML worksheet + draft notes.
The licensed appraiser reviews, adjusts, and certifies — Claude never auto-submits.

> **Canonical definition + completeness gate:** `skills/worksheet-builder/SKILL.md`.
> This command is the *automated* path; the skill defines the deliverable and the
> **mandatory completeness gate** (3–5 closed comps · segregate sold vs active ·
> county-tag + verify out-of-county · never emit unverified GLA · flag view/location
> superiority · form-specific required fields · per-comp 3-yr prior sale/DOM · GLA-band sanity). **Run that gate before Step 3 (render)
> — do not render until it passes.** If `record-assembler` isn't built yet, the skill's
> hand-assemble fallback applies.

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

**What this does:** Gathers subject facts from the county assessment portal (SOR) and Zillow,
then selects/confirms comp candidates from Matrix.

**Inputs:** Address (or order folder if subject.json already exists)  
**Outputs:**
- `subject.json` → `C:\Users\yuriy\VDV Appraisals\<order-folder>\subject.json`
- Comp CSV(s) → `C:\Users\yuriy\VDV Appraisals\Comps files\<addr>_comps_appraiser-single-line.csv`
  (and optionally `_agent-single-line.csv` for active/pending listings)

### Step 1a — Subject data pull (county APEX/assessment portal)

Pull in one pass. Do not proceed to comps until every field below is either populated
or explicitly flagged `NOT IN APEX — confirm at inspection`. No silent blanks.

```
Identification:  GPIN · PID · Subdivision · Section/Block/Lot · Zoning
Legal:           Legal description (from parcel detail)
Site:            Acreage/lot sf  ← often blank in Henrico APEX; go to Zillow immediately
Improvements:    Style · Stories · Year Built · Total Rooms · Beds · Full Baths · Half Baths
GLA:             Above-grade finished sf (county SOR governs; note any MLS conflict)
Exterior:        Ext Walls code · Roof type
Foundation:      Type (Crawl / Slab / Basement)  ← material is NOT in APEX; flag for inspection
Mechanical:      Heating code · AC code · Fireplace count
Sketch codes:    WDK=deck · PCO/PCU=covered porch · OP=open porch · GR1/GR2=garage · WS=workshop
                 (record sf for each — these feed DM Amenities and Garage fields)
```

### Step 1b — Zillow supplement (run immediately after APEX, not on request)

```
Lot size        — fill when APEX acreage blank
Legal desc      — often in listing details if APEX didn't have it
Photos — scan for:
  · Floor material   (living/dining shots)
  · Fireplace        (living room photo — presence + surround style)
  · Front porch type (exterior #1 — stoop-only vs. covered porch)
  · Rear deck/patio  (rear exterior shot)
  · Garage           (exterior or interior shots)
Tag all photo-derived values: "Zillow photo — confirm at inspection"
```

### Step 1c — Compile subject profile before moving to comps

Output the subject profile in DM 1004 field order:
Subject → Contract → Site → Improvements (above-grade rooms / GLA / description) →
Foundation → Exterior → Interior → HVAC → Amenities → Garage/Carport

Surface to the appraiser for confirmation before proceeding to comp search.

**Rules:**
- One Matrix/DataMaster session at a time (Identity Conflict / git-corruption risk).
- MLS# normalization: `BRTVA…` → strip `BRT`, keep `VA…` before feeding DataMaster.
- New construction (no APN): flag `resolution.no_tax_id=true`; appraiser enters subject manually.
- Confirm before downloading/exporting from Matrix.

**Stop here** and surface the subject profile + comp list + any flags for appraiser confirmation.

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
- `Missing prior 3-yr sale / DOM / above-grade split` → flag; the 1004 requires a 3-yr prior-sale history per comp.
- `Luxury subject (GLA > 5,000 sf)` → confirm the comp search used the ±15% GLA band and didn't drop a superior same-subdivision comp.

---

## Step 3 — Render worksheet  *(worksheet-renderer)*

**What this does:** Runs `tools/worksheet-renderer/render_worksheet.py` to produce
a self-contained tabbed HTML worksheet for copy-paste into ACI.

```powershell
python tools/worksheet-renderer/render_worksheet.py `
    "C:\Users\yuriy\VDV Appraisals\<order-folder>\appraisal-record.json" `
    -o "C:\Users\yuriy\VDV Appraisals\<order-folder>\worksheet.html"
    # default tabs: Subject · Comp grid · Sale/Listing history
    # Photos & Map are OPTIONAL — add --with-photos / --with-map ONLY if Yuriy approves
```

**Photos & Map tabs:** OFF by default. Ask Yuriy before including them; add `--with-photos`
and/or `--with-map` only on his explicit approval.

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
- Marks judgment slots as **[APPRAISER: ..