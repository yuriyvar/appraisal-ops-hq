# Navica — County-to-Account Mapping

Search strategy for Navica MLS markets. **Always check ALL accounts listed for a county** — listings are not consolidated across associations.

| County | State | Association | Account # | URL | Search Both? | Notes |
|---|---|---|---|---|---|---|
| Mecklenburg | VA | South Central Association of Realtors | 287 | next.navicamls.net/287 | **YES** | Must search both 287 AND 397 — comps split across systems |
| Mecklenburg | VA | Southern Piedmont Land & Lake Assn of Realtors | 397 | next.navicamls.net/397 | **YES** | Shared search includes participant boards: Dan River Regional, Martinsville/Henry Co, South Central VA, Southwest VA |

## MLS# prefix patterns observed
| Prefix range | Association |
|---|---|
| R57xxx | South Central (287) |
| R70xxx–R71xxx | Southern Piedmont (397) |

> ⚠️ **MLS# namespaces are NOT shared between accounts.** The same numeric ID resolves to a *different* listing in each account. Searching a 287 MLS# (e.g., 57050) via account 397's MlsNosForm returns whatever record 397 happens to have at that number — a completely different property. **Always search within the correct account for a given MLS#.** Verified 2026-06-30.

> ⚠️ **Account 287 access:** The `alanvar` login credential lands on account 397 by default. Navigating to `next.navicamls.net/287/...` while logged in as alanvar redirects to the login page — the session is NOT valid for account 287. To pull South Central (287) comps, YV must either: (a) log in to acct 287 manually and relay data, or (b) confirm whether separate 287 credentials exist (check the docx).

## How to search
Full workflow documented in `C:\Users\yuriy\VDV Appraisals\Operations\Navica MLS basics.docx`. Summary:
1. Log into Navica (credentials in the docx above — do NOT store here)
2. Click Search → Residential
3. Status: check **Active, Pending, Closed** — do NOT include Withdrawn/Expired
4. Location: **keep broad** — rural Southside VA comps routinely cross county lines; use Map Search when available (preferred)
5. Closing Date range: 6–12 months (expand only if needed)
6. Key filters: Bedrooms min/max · GLA range · Lot size (if relevant) · Year Built (if age-sensitive) — **do not over-filter**
7. Sort results by **Distance** then **Close Date (newest first)**
8. For each account in the county row above, run the search separately and combine results — do not stop after one account

## Per-comp data to extract (pull ALL of these for EVERY comp)
Navica has **no Matrix-style CSV export** — comps are read off the **Expanded → Single** listing
detail (`/<acct>/Expanded/Single`; layout **Traditional** shows all fields). Capture the full
comp-grid set so DataMaster / the worksheet aren't missing fields (**YV rule 2026-06-30**):

| Comp-grid field | Where on the listing | Notes |
|---|---|---|
| Address + Tax Parcel ID | header / detail | join to county SOR |
| MLS # (+ which account) | header | namespace differs per account (287 vs 397) |
| Sale / Selling price | detail | |
| Closing date (Closed) **· Pending (under-contract) date** | detail / status | capture the **Pending Date** on pendings; list/contract dates for sale history |
| **Financing type · Closing cost paid by seller** (Seller Paid Conc) | detail | concessions adjust the sale price |
| Days on market | detail | |
| **Type of house** (Style / property type) | detail (Style) | detached / attached / manufactured / condo |
| Design / # stories | detail | |
| Year built | detail | |
| **Total rooms · Bedrooms · Baths (full / half)** | detail (Rooms / Beds / Baths) | the **full room count**, not just beds |
| GLA above grade (**Est Total Htd SqFt**) | detail | cross-check vs county SOR |
| **Basement — total sf + finished / unfinished** | detail / remarks | note finished vs unfinished split |
| **Heating / Cooling** | detail / remarks | fuel + system type |
| **Garage / Carport** (type + # cars) | detail / remarks | att / det, space count |
| **Porch / Deck / Patio** | detail / remarks | |
| Lot / Total Acreage | detail | |
| View / Waterfront | detail | flag superiority (Kerr Lake DOCK/BUOY premium) |
| HOA $ / period | detail | |
| Prior sale (3-yr) | sale history | 1004 requirement |

> ⚠️ **Heating/Cooling, Basement finish, Garage/Carport, and Porch/Deck/Patio are often NOT in the
> field summary** — read the **property description / public remarks** (and the photos) to get them.
> If the listing doesn't state a field, mark it `⚠ confirm`, never guess (CLAUDE.md rule #7).

## To expand
Add a row each time a new county/association is confirmed on a live order.
Last updated: 2026-06-30
