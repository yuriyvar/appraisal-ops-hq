#!/usr/bin/env python3
"""
Build C — subject resolver (Phase 2).

Cache-first subject resolution:
  HIT  -> writes subject.json from the cache (resolution.cached=true, original
          resolved_on preserved, staleness flags attached — flag, never hide).
  MISS -> writes subject.skeleton.json (v1.1 shape, everything unknown = null,
          NEVER guessed) + pull-sheet.md (the per-order run card: SOR vendor/URL/
          technique, the full Source-1/2/3 checklist with the address baked in,
          the gas-provider answer from va-gas-providers.sqlite, MLS routing +
          surrounding-county sets).

Routing source: county_routing.json (committed mirror of
skills/property-search/references/county-registry.md — same-commit drift rule).

Stdlib only. No network. Output dir must be in the CLIENT zone (repo refused).

Usage:
    python resolve_subject.py "4237 Hall Rd, Boydton, VA 23917" --county Mecklenburg \
        --order-id 26-0099 --form-type 2055 --effective-date 2026-07-02 \
        --out-dir "C:\\Users\\yuriy\\VDV Appraisals\\<order-folder>"
"""

import argparse
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from subject_cache import get as cache_get, staleness_flags, normalize_address

ROUTING_PATH = os.path.join(HERE, "county_routing.json")
GAS_DB = os.path.join(REPO, "skills", "property-search", "references",
                      "va-gas-providers.sqlite")


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------
def load_routing(path=None):
    with open(path or ROUTING_PATH, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)["jurisdictions"]


def find_county(routing, county_arg, address):
    """Resolve --county (or the address's locality segment) against the routing
    table. Unknown -> ValueError listing coverage (fail loud, never guess)."""
    candidates = []
    if county_arg:
        candidates.append(county_arg)
    parts = [p.strip() for p in str(address).split(",") if p.strip()]
    if len(parts) >= 3:
        candidates.append(parts[-2])
    elif len(parts) == 2:
        candidates.append(parts[1])
    for cand in candidates:
        c = cand.strip().lower()
        for name, entry in routing.items():
            if c == name.lower() or c in (a.lower() for a in entry.get("aliases", [])):
                return name, entry
    raise ValueError(
        "county {!r} not in the routing table. Covered: {}. Add it to "
        "county-registry.md + county_routing.json (same commit) first.".format(
            county_arg or (candidates[-1] if candidates else "?"),
            ", ".join(sorted(routing))))


def gas_lookup(gas_key):
    """Query the gas reference DB (read-only). Returns a list of provider dicts,
    [] = no row = NOT YET LOOKED UP (distinct from confirmed_absent rows)."""
    if not os.path.isfile(GAS_DB):
        return None  # DB missing entirely — surfaced on the pull sheet
    con = sqlite3.connect(GAS_DB)
    try:
        rows = con.execute(
            "SELECT p.provider_name, p.lookup_method, p.lookup_url, "
            "       p.lookup_notes, p.phone "
            "FROM va_gas_providers p "
            "JOIN va_gas_provider_counties c ON c.provider_id = p.id "
            "WHERE c.county_city = ?", (gas_key,)).fetchall()
    finally:
        con.close()
    return [{"provider": r[0], "method": r[1], "url": r[2],
             "notes": r[3], "phone": r[4]} for r in rows]


# ---------------------------------------------------------------------------
# skeleton (v1.1 subject.json shape — unknown = null, never a guess)
# ---------------------------------------------------------------------------
def parse_address(address):
    parts = [p.strip() for p in str(address).split(",") if p.strip()]
    street = parts[0] if parts else None
    city = parts[-2] if len(parts) >= 3 else (parts[1] if len(parts) == 2 else None)
    state = zipc = None
    if parts:
        m = re.search(r"\b([A-Z]{2})\b", parts[-1].upper())
        state = m.group(1) if m else None
        z = re.findall(r"\b(\d{5})(?:-\d{4})?\b", parts[-1])
        zipc = z[-1] if z else None
    return {"full": str(address), "street": street, "city": city,
            "state": state, "zip": zipc}


def build_skeleton(address, county_name, entry, order_meta):
    addr = parse_address(address)
    addr["county"] = county_name
    order = {
        "order_id":       order_meta.get("order_id"),
        "form_type":      order_meta.get("form_type"),
        "client":         order_meta.get("client"),
        "loan_number":    order_meta.get("loan_number"),
        "effective_date": order_meta.get("effective_date"),
        "due_date":       order_meta.get("due_date"),
        "inspection":     order_meta.get("inspection"),
        "fee":            order_meta.get("fee"),
        "status":         "in-progress",
        "contract": {"contract_price": None, "contract_date": None,
                     "seller_is_owner_of_record": None, "concessions": None,
                     "financing_type": None},
    }
    ch_keys = ["property_type", "use_code", "zoning", "gla_sf", "above_grade_sf",
               "below_grade_finished_sf", "basement", "year_built", "stories",
               "style", "grade_or_condition", "bedrooms", "full_baths",
               "half_baths", "total_rooms", "lot_size_sf", "lot_size_acres",
               "garage", "pool", "fireplaces", "heating", "cooling", "exterior"]
    id_keys = ["gpin", "pid", "apn", "subdivision", "section", "block", "lot",
               "magisterial_district", "neighborhood_code", "legal_description"]
    return {
        "order": order,
        "address": addr,
        "identifiers": {k: None for k in id_keys},
        "characteristics": {k: None for k in ch_keys},
        "assessment": {"tax_year": None, "land_value": None,
                       "improvements_value": None, "total_value": None},
        "resolution": {"input_was_address_only": True,
                       "method": entry["vendor"],
                       "no_tax_id": None, "neighbor_unit_proxy": None,
                       "cached": False, "resolved_on": None},
        "verification": [],
        "listing": None,
        "sales_history": [],
        "flags": [],
        "geo": {"lat": None, "lon": None},
        "market": {
            "search": {
                "radius_mi": None,
                "sale_window_months": 12,
                "gla_band": {"low_sf": None, "high_sf": None,
                             "luxury_widened": False},
                "mls_systems": list(entry.get("mls", [])),
                "surrounding_counties": list(entry.get("surrounding_counties", [])),
            },
            "neighborhood_notes": None,
        },
        "sources": [],
        "assessors_parcel_number": None,
        "map_reference": None,
        "walls_trim": None,
        "water": None,
        "sewer": None,
        "re_taxes_annual": None,
        "hoa_amount": None,
        "hoa_period": None,
        "neighborhood_bounds": None,
        "neighborhood_description_context": None,
    }


# ---------------------------------------------------------------------------
# pull sheet
# ---------------------------------------------------------------------------
def build_pull_sheet(address, county_name, entry, gas):
    L = []
    L.append("# Subject pull sheet — {}".format(address))
    L.append("")
    L.append("County: **{}** · comp source: {} · sales-GIS: {}".format(
        county_name, entry.get("comp_source", "?"), entry.get("sales_gis", "?")))
    L.append("")
    L.append("## Source 1 — county SOR ({})".format(entry["vendor"]))
    L.append("- URL: {}".format(entry["sor_url"]))
    L.append("- Technique: {}".format(entry["technique"]))
    if entry.get("quirks"):
        L.append("- ⚠ Quirks: {}".format(entry["quirks"]))
    L.append("- Pull in ONE pass (blank is data — record it):")
    L.append("  - Identification: GPIN, PID, Subdivision, Section/Block/Lot, Zoning")
    L.append("  - Legal description (needed for DM Subject tab)")
    L.append("  - Lot acreage (often blank -> go to Zillow immediately)")
    L.append("  - Improvements: Style, # Stories, Year Built, Total Rooms, Bedrooms, Full/Half Baths")
    L.append("  - Above-grade GLA (county SOR governs; note conflicts with MLS)")
    L.append("  - Exterior: Ext Walls code, Roof type · Foundation type")
    L.append("  - Mechanical: Heating code, AC code, Fireplace count")
    L.append("  - Sketch codes (WDK=deck, PCO/PCU=covered porch, OP=open porch, GR1/GR2=garage, WS=workshop) + sf each")
    L.append("  - Tax bill $ (R.E. Taxes — distinct from assessed value) + tax year")
    L.append("")
    L.append("## Source 2 — Zillow (supplement + cross-check, immediately after SOR)")
    L.append("- Lot size when SOR blank · legal description · photo scan:")
    L.append("  floors / fireplace / porch type / rear deck-patio / garage")
    L.append("  (flag photo-derived items 'Zillow — confirm at inspection')")
    L.append("")
    L.append("## Source 3 — gas availability (BEFORE inferring heating fuel)")
    if gas is None:
        L.append("- ⚠ va-gas-providers.sqlite NOT FOUND — query it manually per the registry.")
    elif not gas:
        L.append("- **No provider row for {} — NOT YET LOOKED UP** -> gas provider unknown, "
                 "confirm at inspection; consider adding the county to the gas DB.".format(county_name))
    else:
        for p in gas:
            if p["method"] == "confirmed_absent":
                L.append("- **CONFIRMED: no SCC gas provider serves {}** -> heating is NOT gas "
                         "(heat pump / electric / propane — confirm at inspection).".format(county_name))
            else:
                L.append("- Provider: **{}** ({}) — {}".format(
                    p["provider"], p["method"], p["url"] or p["phone"] or ""))
                if p["notes"]:
                    L.append("  - {}".format(p["notes"]))
        if len([p for p in gas if p["method"] != "confirmed_absent"]) > 1:
            L.append("- ⚠ OVERLAP county — two providers returned; present both.")
    L.append("- Record: Gas = Connected / Available-not-connected / Not available.")
    L.append("")
    L.append("## MLS / comps routing")
    L.append("- MLS: {}".format(" + ".join(entry.get("mls", ["?"]))))
    if entry.get("navica_both_accounts"):
        L.append("- ⚠ {}".format(entry["navica_both_accounts"]))
    sc = entry.get("surrounding_counties") or []
    if sc:
        L.append("- Surrounding-county search set: {}".format(", ".join(sc)))
    L.append("")
    L.append("## v1.1 extras the worksheet renders (TBD if you skip them)")
    L.append("- water / sewer (MLS/Matrix ONLY — never inferred from the county)")
    L.append("- re_taxes_annual + hoa_amount/hoa_period (HOA docs)")
    L.append("- neighborhood_bounds (N/S/E/W roads) + description context (style/amenities)")
    L.append("")
    L.append("Fill `subject.skeleton.json`, then: "
             "`python tools/subject-resolution/ingest_subject.py <skeleton> --out subject.json`")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# run log (BD1 standard-work enforcement)
# ---------------------------------------------------------------------------
def build_run_log(address, order_meta, hit_info, as_of=None):
    """The per-order standard-work checklist. Tools tick their own steps
    (resolver = 1, ingester = 3); humans tick 2 and 4. Bypassing a step leaves
    an unchecked box that the weekly review audits."""
    from datetime import date as _date
    stamp = str(as_of)[:10] if as_of else _date.today().isoformat()
    oid = order_meta.get("order_id") or "-"
    L = ["# Run log — {} (order {})".format(address, oid),
         "",
         "Standard work: resolve → pull → ingest → comps → assemble → render.",
         "Do NOT improvise — gaps stay null + flagged, never guessed.",
         ""]
    if hit_info:
        resolved_on, age = hit_info
        L.append("- [x] 1. resolve_subject — CACHE HIT @ {} (vintage {}, {} days; "
                 "staleness flags are in subject.json)".format(stamp, resolved_on, age))
        L.append("- [x] 2. pull sheet — n/a on a cache hit; RE-VERIFY the flagged items instead")
        L.append("- [x] 3. ingest — n/a; cached subject.json written")
    else:
        L.append("- [x] 1. resolve_subject — MISS @ {} (skeleton + pull-sheet written)".format(stamp))
        L.append("- [ ] 2. pull sheet executed (SOR → Zillow → gas; unknowns left null)")
        L.append("- [ ] 3. ingest_subject — subject.json written + cached")
    L.append("- [ ] 4. comps pulled per property-search SKILL (GLA band · 12-mo · ML#+TaxID gates)")
    L.append("- [ ] 5. assemble_record — appraisal-record.json built")
    L.append("- [ ] 6. render_worksheet — comp Tax-ID gate exit 0")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------
def _check_out_dir(out_dir):
    ap = os.path.abspath(out_dir)
    if ap == REPO or ap.startswith(REPO + os.sep):
        raise ValueError("out-dir is inside the repo — order files live in the "
                         "client zone: " + ap)
    os.makedirs(ap, exist_ok=True)
    return ap


def resolve(address, county=None, out_dir=".", db_path=None, as_of=None,
            ttl_days=180, routing_path=None, **order_meta):
    routing = load_routing(routing_path)
    county_name, entry = find_county(routing, county, address)
    out = _check_out_dir(out_dir)

    hit = cache_get(address, db_path=db_path, as_of=as_of)
    if hit:
        subject, resolved_on, age = hit
        subject = json.loads(json.dumps(subject))  # never mutate the cached copy
        subject.setdefault("resolution", {})["cached"] = True
        subject["resolution"].setdefault("resolved_on", resolved_on)
        flags = subject.setdefault("flags", [])
        for f in staleness_flags(subject, resolved_on, as_of, ttl_days):
            if f not in flags:
                flags.append(f)
        order = subject.setdefault("order", {})
        for k, v in order_meta.items():
            if v is not None:
                order[k] = v
        path = os.path.join(out, "subject.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(subject, fh, indent=2, ensure_ascii=False)
        with open(os.path.join(out, "run-log.md"), "w", encoding="utf-8") as fh:
            fh.write(build_run_log(address, order_meta, (resolved_on, age), as_of))
        print("CACHE HIT (resolved {}, {} days old) -> {}".format(resolved_on, age, path))
        for f in flags:
            print("FLAG  " + f)
        print("Next: assemble comps as usual; re-verify flagged items.")
        return 0

    skeleton = build_skeleton(address, county_name, entry, order_meta)
    gas = gas_lookup(entry.get("gas_key", county_name))
    sheet = build_pull_sheet(address, county_name, entry, gas)
    sk_path = os.path.join(out, "subject.skeleton.json")
    ps_path = os.path.join(out, "pull-sheet.md")
    with open(sk_path, "w", encoding="utf-8") as fh:
        json.dump(skeleton, fh, indent=2, ensure_ascii=False)
    with open(ps_path, "w", encoding="utf-8") as fh:
        fh.write(sheet)
    rl_path = os.path.join(out, "run-log.md")
    with open(rl_path, "w", encoding="utf-8") as fh:
        fh.write(build_run_log(address, order_meta, None, as_of))
    print("CACHE MISS -> pull needed. Wrote:")
    print("  " + sk_path)
    print("  " + ps_path)
    print("  " + rl_path)
    print("Run the pull sheet, fill the skeleton, then ingest_subject.py.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build C — cache-first subject resolver")
    ap.add_argument("address")
    ap.add_argument("--county", help="jurisdiction (else parsed from the address)")
    ap.add_argument("--out-dir", default=".", help="order folder (client zone)")
    ap.add_argument("--db", help="cache DB path override")
    ap.add_argument("--as-of", help="date for staleness math (YYYY-MM-DD)")
    ap.add_argument("--ttl-days", type=int, default=180)
    ap.add_argument("--routing", help="routing JSON override (tests)")
    ap.add_argument("--order-id")
    ap.add_argument("--form-type")
    ap.add_argument("--client")
    ap.add_argument("--loan-number")
    ap.add_argument("--effective-date")
    ap.add_argument("--due-date")
    ap.add_argument("--inspection")
    ap.add_argument("--fee", type=float)
    args = ap.parse_args(argv)
    try:
        return resolve(
            args.address, county=args.county, out_dir=args.out_dir,
            db_path=args.db, as_of=args.as_of, ttl_days=args.ttl_days,
            routing_path=args.routing,
            order_id=args.order_id, form_type=args.form_type, client=args.client,
            loan_number=args.loan_number, effective_date=args.effective_date,
            due_date=args.due_date, inspection=args.inspection, fee=args.fee)
    except ValueError as e:
        sys.stderr.write("ERROR: {}\n".format(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
