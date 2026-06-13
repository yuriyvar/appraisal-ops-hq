# DataMaster handoff — CSV formats and flow

DataMaster (desktop app; shortcut in `C:\Users\yuriy\VDV Appraisals`) ingests
comps via **CSV import** of CVR MLS Matrix grid exports. Per-order project files
(`<subject address>.dma`) live in `C:\Users\yuriy\OneDrive\Documents\DataMaster\`
— they are zip-wrapped proprietary binaries. **Never write .dma files directly**;
only DataMaster creates/edits them. After import, DataMaster pulls full MLS +
public records itself and transfers to ACI.

## The two CSVs (Matrix custom displays)

**"Appraiser Single Line"** — closed/pending comps (the sales grid):

```
"Distance","#","ML #","PID","Prop Type","Status","Area","Address","Subdivision","Type","PR Abv Fin SqFt","PR Bldg SqFt","PR Living SqFt","# Bedrooms","Total Baths","# Rooms","Total Finished Area","SqFtTotal","Original List Price","List Price","Sales Price","","Days On Market","MLS"
```

**"Agent Single Line"** — actives/pendings for the 1004 listing analysis:

```
"Distance","#","ML #","PID","Status","Area","Address","Subdivision","Type","# Bedrooms","Total Baths","# Rooms","Total Finished Area","List Price","Sales Price","","Days On Market","","MLS"
```

Notes:
- `ML #` = MLS number (the key DataMaster uses). `PID` = county parcel ID — in
  Hanover this equals the GPIN, so it joins directly to our county verification.
- **`BRTVA*` MLS# normalization (CVR↔Bright data sharing):** an MLS# of the form
  `BRTVA…` is a **Bright MLS** listing surfaced through CVR MLS (the two share data).
  **Strip the `BRT` prefix and keep the `VA…` portion** — e.g. `BRTVAMB2000092` →
  `VAMB2000092`. The `VA…` number is the canonical key that works in Bright MLS **and**
  in DataMaster for pulling data; feed DM the stripped `VA…` value, not the `BRT…` one.
- `PR *` columns are public-records values; `Total Finished Area`/`SqFtTotal`
  are MLS values — they can differ (our county-vs-Zillow-vs-MLS conflict checks
  apply here too).
- Distance is from the subject (Matrix proximity search).
- Status codes seen: CLOSD, PEND, ACT. MLS column = "CVR".

## Flow (per order)
1. Comps confirmed by appraiser (from property-search results).
2. In Matrix (logged-in Chrome session): search the comp MLS#s / run the
   proximity search; select the comp rows; Export with the **"Appraiser Single
   Line"** display. Repeat with actives/pendings using **"Agent Single Line"**.
   Exports are downloads — confirm with the user before downloading, and save
   DataMaster CSVs into **`C:\Users\yuriy\VDV Appraisals\Comps files\`** (the
   standing folder for DataMaster comp CSVs, per YV 2026-06-13). Name them
   `<subject-address>_comps_appraiser-single-line.csv` (and `_agent-single-line`
   for actives).
   (Generating the CSV by hand is a fallback — match the headers above exactly —
   but prefer a real Matrix export so DataMaster sees canonical values.)
3. User (or Claude via computer use, with permission) imports the CSVs into
   DataMaster, which pulls full data and builds the `.dma`.
4. Review in DataMaster: for each field where MLS and public records disagree,
   check against the skill's county/Zillow verification before sending to ACI.
