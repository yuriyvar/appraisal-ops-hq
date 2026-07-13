# County registry — routing for subject + comps (schema + coverage)

This is the routing layer for the property-search skill. The **source of truth**
remains the Operational Records Google Sheet, tab "VA Counties Assessment & GIS
Records" (doc `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`, gid `686822370`). This file is
the local mirror. Reconcile per the skill's Step 1.
> Source quirks & handling exceptions (MLS-format, GIS gotchas): see `data-quirks.md`.
> **Drift rule (Build C):** any edit to the coverage tables below MUST update
> `tools/subject-resolution/county_routing.json` in the SAME commit — the resolver
> routes orders from that mirror.

## Proposed sheet/registry columns (extend the existing tab)
| Column | Meaning |
|---|---|
| Jurisdiction | County / independent city |
| Assessment SOR URL | Where the subject card lives (authoritative) |
| Assessment vendor | One of the families below |
| Subject technique | How to pull the card for that family (see Adapters) |
| Sales-GIS layer? | Y / N — is there a queryable county SALES layer |
| Sales-GIS endpoint | FeatureServer/MapServer URL if Y |
| Comp source | `GIS+MLS` (universe from GIS, detail from MLS) or `MLS-only` |
| MLS | `CVR-Matrix` / `Navica` / `both` |
| Last verified | ISO date |
| Quirks | gotchas discovered on real orders |

## Assessment vendor adapters (how to pull the subject card)
- **APEX** (Henrico `realestate.henrico.gov`): enter at the **root** (deep link
  `f?p=...:1` 410s on the URL firewall); search via the form (`apex.submit`
  with `{request:'SEARCH'}`); open the result detail page (`f?p=510101:5...`).
- **Vision/vgsi** (`gis.vgsi.com/<county>`): search by address -> `Parcel.aspx?Pid=N`.
- **actdatascout** (`actdatascout.com/RealProperty/Virginia/<county>`): portal search.
- **ArcGIS-Experience / CivQuest** (`*.civ.quest`, `experience.arcgis.com/...`):
  find the live FeatureServer via `performance.getEntriesByType('resource')`
  filtered for `rest/services`; query parcel/improvements/sales layers (see
  SKILL "Technique" section). Beware stale AGO mirrors.
- **webgis / interactivegis / qPublic**: lightweight county GIS portals; address search.

## Comp-source rule
- If **Sales-GIS layer = Y** -> use it for the comp universe + spatial filter,
  then MLS for comp detail (DOM, concessions, condition, prior sale).
- If **MLS-only** -> MLS does both universe and detail; use the assessment SOR
  per-parcel for cross-verification. See `matrix-comp-search.md`.

## Priority coverage (Richmond metro — build by order volume)
| Jurisdiction | Assessment vendor | Sales-GIS? | Comp source | MLS | Notes |
|---|---|---|---|---|---|
| Henrico Co | APEX (realestate.henrico.gov) | **N** (open-data parcel layer is a 735-row SAMPLE) | **MLS-only** | CVR-Matrix | corrected 2026-06-13; do NOT use AGO "Tax Parcels 0322". Gas: Richmond Gas Works (`instant_map`) — query `references/va-gas-providers.sqlite` (see Gas section) |
| Chesterfield Co | (ArcGIS) | **Y** — `services3.arcgis.com/TsynfzBSE6sXfoLq/.../Cadastral_ProdA/FeatureServer/3` has SaleDate/SalePrice | GIS+MLS | CVR-Matrix | strip dashes from TaxID. Gas OVERLAP: N. Chesterfield = Richmond Gas Works (`instant_map`); S. Chesterfield = Columbia Gas — query `references/va-gas-providers.sqlite` returns both (see Gas section) |
| Hanover Co | CivQuest (parcel map) | **Y** — `maps.civ.quest/.../Hanover/Public/FeatureServer` Sales=38 | GIS+MLS | CVR-Matrix | AGO mirror stale; use civ.quest |
| Richmond City | actdatascout | TODO | MLS-only (assume) | CVR-Matrix | verify sales layer on next order. Gas: Richmond Gas Works (`instant_map`) — query `references/va-gas-providers.sqlite` (see Gas section) |
| Goochland Co | (gis.co.goochland.va.us) | TODO | MLS-only (assume) | CVR-Matrix | River Notch/Rivergate area |
| Powhatan Co | CivQuest | TODO (AGO Vision_Powhatan has SALEHIST — verify) | TBD | CVR-Matrix | |
| New Kent Co | Vision + CivQuest | TODO | TBD | CVR-Matrix | |
| Chesapeake City | CivQuest | TODO | TBD | both? | confirm MLS (Navica?) |

> Reconcile this table into the Google Sheet (add the new columns) on the next
> logged-in Chrome session — ask before writing to the sheet.

## Extended coverage (added as orders arrive)
| Jurisdiction | Assessment vendor | Sales-GIS? | Comp source | MLS | Notes |
|---|---|---|---|---|---|
| Charlotte Co | charlottecountypropertycards.com (InteractiveGIS-style portal) | N (no known sales layer) | MLS-only | CVR-Matrix / Navica | Search by address or record#. Tax card shows building sections (A/B), foundation, ext walls, heat/AC, sketch. Parcel# format: 086--A---7-A. No SCC gas provider (rural Southside VA) — well/septic typical. County phone: (434) 542-5546. Verified 2026-06-19. |
| Buckingham Co | buckcova.interactivegis.com (InteractiveGIS, public access — accept terms → Go to Map → Quick Search by address → click parcel → Tax Cards icon opens PDF at `/resources/landcards/000{ACCT#}.pdf`) | N (GIS parcel only, no sales layer) | MLS-only | CVR-Matrix / Navica | Parcel# format: 188-2-6A. Acct# zero-padded 9-digits + 3-digit suffix (e.g. 000011611-001). No SCC gas provider — heat pump/electric typical. Well/septic typical rural. Verified 2026-06-19. |
| Prince Edward Co | epayments.co.prince-edward.va.us (TXApps property cards) | N | MLS-only | Navica (Lake Country) | Southside; CVR returns ~0 sales here, pull comps in Navica. Surrounding-county set: see "MLS systems by market" below. Verified 2026-06-26 (andon). |
| Mecklenburg Co / Kerr Lake | ConciseCAMA (`mecklenburg.cama.concisesystems.com`) | N | MLS-only | Navica — **BOTH** South Central (acct 287) + Southern Piedmont (acct 397) | CVR returns ~0 sales here. **Must search both Navica accounts** — comps split: R57xxx = South Central; R70xxx–R71xxx = Southern Piedmont. ConciseCAMA may have NO building record for manufactured homes — get GLA from client or MLS history. No SCC gas (rural Southside VA). Full workflow + login → `references/navica-accounts.md`. Surrounding set: see MLS section below. Verified 2026-06-30. |
| Spotsylvania Co | Custom county app (apps.spotsylvaniacountyva.gov, ColdFusion .cfm) (https://apps.spotsylvaniacountyva.gov/assessment/assessment/index.cfm) | TODO - not yet verified | MLS-only (no verified sales-GIS layer yet) | TBD - likely Bright MLS (Fredericksburg market, unconfirmed - verify before relying on it) | First live pull 2026-07-08 (9508 Whiteheart Dr). Valuations current as of 01/01/2026. Owner mailing address on the card can differ from subject physical address (neighbor-owner pattern) - don't assume a mismatch is a data error.  [added via add_county.py — live-verify on first order] |
| Smyth Co | Vision/vgsi (https://gis.vgsi.com/smythcountyva/) | N â€” no bulk-queryable sales layer confirmed; each VGSI parcel card shows its own last Sale Date/Price/Book&amp;Page only (per-parcel, not a searchable universe) | MLS-only (assumed, unverified â€” first live order) | TBD â€” unconfirmed. Smyth County (Saltville/Marion) is 250+ mi SW of VDV's normal Richmond-metro/Southside footprint; NOT CVR-Matrix or Navica coverage. Likely a SW-VA/NE-TN regional MLS (e.g. Highlands Assn of Realtors / NeTREIS) â€” verify before any comp pull. | SMYTH-001: VGSI's own Search.aspx address search can MISS a current E911 address even though the parcel exists â€” confirmed on 486 Possum Hollow Rd (order 67546202, 2026-07-09): VGSI address search returned "No Data", and the county's own Streets.aspx street index jumped straight from #470 to #523 with no #486 listed. The county's separate parcel/GIS site (webgis.net/va/smyth/, switch dropdown to "Address Search") DID resolve house# 486 + street "Possum Hollow" to a real E911 site-address point, which spatially falls inside parcel Tax ID 30-A-10 / Acct 84450 (owner HAYTON GORDON TRIGG) â€” but that same parcel's CAMA "Physical Address" field still reads the STALE address "185 Possum Hollow Rd" (its VGSI card is titled/located under 185, not 486). Net: CAMA physical-address text lags E911 site-address renumbering here. Workflow fix: when VGSI address search comes up empty, always cross-check webgis.net/va/smyth/'s Address Search (separate site, same county, more current E911 layer) and take the PARCEL the point falls inside, not the CAMA card's own address label â€” flag the mismatch on the record, never silently rename it. Building on 30-A-10 per its 2026 CAMA card: 1925, 2,576 sf, 6bd/1fb+1hb, 2-story wood frame, brick foundation, Grade D / Building % Good 20 (poor condition), no garage, no basement, wood/space heat only, 3.88 ac. UNCONFIRMED as the actual 486 subject â€” pending Yuriy's owner-name/FSBO-listing confirmation.  [added via add_county.py — live-verify on first order] |

## MLS systems by market (CVR-Matrix / Bright / Navica)
**Confirm the market's MLS before pulling comps** — a wrong-MLS pull (e.g. CVR for a Navica market)
returns near-zero and burns the order (andon 2026-06-26: Prince Edward + The Moorings were pulled in
CVR and came back empty).
- **CVR-Matrix** — default for Richmond metro + Central VA (the coverage rows above).
- **Bright** — NoVA / Shenandoah / panhandle; `BRTVA…` MLS#s are Bright listings shared into CVR, so
  normalize per data-quirks **MLS-001** (strip `BRT`, keep `VA…`).
- **Navica** (Lake Country Assn of Realtors) — Southside lake/rural markets. **Confirmed: Prince Edward
  and Mecklenburg / Kerr Lake** (CVR is thin-to-empty there). For any Navica market, ALWAYS hand YV the
  **surrounding-county search set** — rural comps routinely cross county lines:
  - **Prince Edward** → Buckingham, Appomattox, Charlotte, Cumberland, Nottoway, Lunenburg.
  - **Mecklenburg / Kerr Lake** → Lunenburg, Charlotte, Halifax, Brunswick **+ NC Kerr Lake shore
    (Vance / Granville / Warren NC)**.

## Gas utility availability (worksheet-builder Source 3)
**Source of truth = `references/va-gas-providers.sqlite`** (not inline URLs here). Query by
jurisdiction to get the provider + lookup method/URL + how-to notes:
```sql
SELECT p.provider_name, p.lookup_method, p.lookup_url, p.lookup_notes, p.phone
FROM va_gas_providers p JOIN va_gas_provider_counties c ON c.provider_id = p.id
WHERE c.county_city = 'Henrico County';
```
- **Richmond metro (Henrico, Richmond City, N. Chesterfield) → Richmond Gas Works** (`instant_map`):
  search address → click the **street/parcel area (NOT the result pin)** → popup gives gas-connected
  vs. "can be brought to it" (= **not** gas) vs. outside-area. Drives the heating-fuel inference.
- **Overlap counties** (Chesterfield, Frederick, Warren, Rockingham, Clarke) return **two** providers
  — present both. `lookup_method` `phone_only`/`map_only`/`form_callback` = no instant answer; flag
  "confirm at inspection." Rebuild the DB via `references/build_va_gas_providers.py`.
