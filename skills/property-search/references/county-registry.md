# County registry — routing for subject + comps (schema + coverage)

This is the routing layer for the property-search skill. The **source of truth**
remains the Operational Records Google Sheet, tab "VA Counties Assessment & GIS
Records" (doc `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`, gid `686822370`). This file is
the local mirror. Reconcile per the skill's Step 1.
> Source quirks & handling exceptions (MLS-format, GIS gotchas): see `data-quirks.md`.

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
