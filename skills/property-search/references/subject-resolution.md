# Subject resolution — turning an address into an authoritative parcel
*The "brute-force a subject with no clean Tax ID" playbook. Happens regularly
(new construction, builder parcels, address aliases). Streamline + CACHE it.*

## When this triggers
Order arrives as an address only (no GPIN/PID), OR the assessment search returns
nothing, OR the parcel exists but facts look wrong/missing (SF=0, builder owner).

## Procedure
1. **Normalize + expand the address.** Build candidate variants: street-type
   aliases (DR/WAY/CT/PL/CIR/RD/LN/TER), directionals (N/S/E/W), unit forms.
   County, MLS, and postal often disagree on street type/name.
2. **Assessment SOR by address** (per the county-registry adapter). Hit -> capture
   GPIN/PID, then proceed to normal verification.
3. **If no hit, spatial resolve:** geocode the address (US Census onelineaddress;
   run from a census-origin tab to dodge CORS) -> point-in-parcel query against the
   county parcel layer to get the GPIN even when the address attribute differs.
4. **New-construction / builder-parcel check:** search the subdivision name. Units
   may sit under an **undivided builder parcel** (OwnerName = builder, SF=0, not
   subdivided) for 1-2 yrs after construction; individual Tax IDs don't exist yet.
   (Documented case: Hancock Towns DR / Hancock Village condos, Chesterfield.) Use the **nearest assessed neighbor unit** (next unit on the street, or an
   identical floor-plan elsewhere in the subdivision) as the **GLA/spec proxy**
   for the subject.
5. **MLS cross-check (all instances):** search the address in CVR + Bright (Matrix)
   and Navica. The MLS often carries the Tax ID/GPIN and the *alternate* street
   name the county uses, plus the listing facts.
6. **Public-portal cross-check:** Zillow, Realtor.com, Redfin, Homes.com. They
   geocode reliably and often surface APN/parcel + last-sale; useful when MLS/county
   are blank or for new construction.
7. **Resolve aliases & conflicts:** record the canonical parcel (GPIN/PID), lat/long,
   and the **address-alias mapping** (e.g. county "HANCOCK CREST WAY" = MLS
   "HANCOCK TOWNS DR").
8. **If still unestablished** (no parcel exists yet): use builder parcel + recorded
   plat + MLS for subject facts, clearly flag "not yet individually assessed," and
   **andon** if it blocks the order.

## Downstream consequence — DataMaster / ACI (do not skip)
When the subject has **no Tax ID**, DataMaster/CoreLogic cannot auto-pull it.
You must **start the DM file by entering the subject manually** (using the
neighbor-unit / plat / MLS specs from steps 4 & 8), **then** import the comp
CSV. Never import comps into an empty subject. (See SKILL Step 6 new-construction
exception.)

## CACHE every resolution (this is the streamlining win)
Write each hard-won resolution to the SQLite cache (see ADR-002 amendment), keyed
by normalized address:
`{normalized_address, gpin/pid, county, lat, lon, mls_numbers[], aliases[],
source, resolved_on, notes}`. Next time the same property (or its neighbors in a
new subdivision) comes in, it's an instant lookup instead of a re-brute-force.

## Public-portal adapters (cross-check leg — beyond Zillow)
| Portal | Use | Quirk |
|---|---|---|
| Zillow | GLA/beds/baths/yr/last-sold; `livingArea":NNNN` in HTML | CAPTCHA risk; don't solve |
| Realtor.com | facts + sometimes APN/parcel | client-rendered; may need Chrome render |
| Redfin | facts + last-sold + often APN | has a public data export on some pages |
| Homes.com | facts; fills gaps | coverage varies |
Rule unchanged: never present single-source GLA as verified; two+ sources within 5%.
