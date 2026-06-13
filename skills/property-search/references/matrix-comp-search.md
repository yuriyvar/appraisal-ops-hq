# MLS comp-pull playbook (Matrix adapter = CVR + Bright; Navica = TODO)
> CVR MLS and Bright MLS both run on the Cotality **Matrix** platform — the
> steps below cover both (parameterize instance URL + login). **Navica** is a
> different platform and needs its own adapter. Public cross-check portals
> (Zillow/Realtor/Redfin/Homes) are in `subject-resolution.md`.

Turns the "comp-pull" module into standard work. Subject must be verified first.

## CVR Matrix — radius comp search
1. **Session:** one concurrent session per CVR login. If a second Cowork/job is
   using Matrix you'll hit "User Identity Conflict" and ping-pong. Work one at a
   time. Confirm login via the "Working As" header.
2. **Open a CLEAN search** from the SEARCH menu -> Residential (the MyMatrix
   hotsheet widget injects a stray "Change Type History" timestamp filter — don't
   use it). URL: `/Matrix/Search/Residential/ResidentialFull`.
3. **Radius:** use the **map-radius** search ("within N mi of <address>"). The
   criteria-tab address text box does **NOT** geocode from typed text and
   silently returns no radius — do not rely on it. (Alan's saved 1.0-mi search is
   the reference.) Control IDs differ by page (`Fm18_` results-embedded vs
   `Fm11_` full form) — detect, don't hardcode.
4. **Criteria:** Status = Sold (set the sold-date sub-field to a 12-mo range) plus
   Active/Pending for context; Type = Single Family Residence; set the GLA band.
   - **GLA band:** subject +/-10% by default, but **widen to ~+15% for luxury/large
     subjects** — a tight band drops bracket-up comps (119 Countryside: the best
     comp, 8721 Ruggles 7,560 sf, fell just past +10%).
5. **Display:** switch to "Appraiser Single Line", page size 100, to expose
   PR Abv Fin / PR Bldg / PR Living / TtlFinAr / SqFtTotal + prices + DOM.
6. **Scrape gotchas:** result data rows have a fixed cell count (e.g. 31 direct
   `<td>`); target those, skip the giant wrapper row, and strip any cell with a
   URL/`?c=`/`.aspx` (the chat content-filter blocks otherwise). Output truncates
   ~12 rows/read — page through with slices.
7. **Distance:** if you used the map-radius, Matrix gives a Distance column. If
   not, geocode addresses with the US Census `onelineaddress` API — but it is
   **CORS-blocked from the matrix.com origin**; run it from a tab on
   `geocoding.geo.census.gov`, then haversine to the subject centroid.

## DataMaster output
- Save the CSV to `C:\Users\yuriy\VDV Appraisals\Comps files\` (standing folder)
  named `<address>_comps_appraiser-single-line.csv`. Headers per
  `datamaster-handoff.md`. Keep ML#/PID — DataMaster's key fields.

## Navica MLS — TODO adapter
Next integration. Needs its own login/session model, radius-search flow, and
field map, behind the same interface so it emits the identical DataMaster CSV.
Capture the procedure on the first real Navica order.
