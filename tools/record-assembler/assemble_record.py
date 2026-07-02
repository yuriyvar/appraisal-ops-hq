#!/usr/bin/env python3
"""
Build B — Appraisal record assembler.

Turns a subject.json + DataMaster comp CSV(s) into a single
appraisal-record.json conforming to appraisal-record.schema.json v1.0.

Design rules (per build brief 2026-06-13 / ADR-002 / ADR-003):
  * Deterministic. Same inputs + same --generated-at -> byte-identical output.
  * Stdlib only. No pip installs, no network calls.
  * Never emits unverified GLA — missing/zero GLA -> null + flag, never guessed.
  * MLS# normalized: BRTVA… -> strip BRT, keep VA… (CVR/Bright sharing).
  * Status normalized: CLOSD/PEND/ACT -> closed/pending/active.
  * Closed vs active/pending segregated in output (status field).
  * Out-of-county comps flagged for SOR verification.
  * Adjustments block left empty (entered_by_appraiser=false).
  * Human gate: review.human_reviewed=false until appraiser certifies.

Inputs:
  subject.json   — subject facts (see README.md for the shape)
  comps.csv      — Appraiser Single Line or Agent Single Line export from Matrix,
                   saved in C:\\Users\\yuriy\\VDV Appraisals\\Comps files\\

Output:
  appraisal-record.json written to the per-order folder; path + summary printed.

Usage:
    python assemble_record.py subject.json comps.csv output/appraisal-record.json
    python assemble_record.py subject.json comps_appraiser.csv out.json \\
        --comps-agent comps_agent.csv \\
        --order-id "26-0042" --client "First National Bank"
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "1.1"
GENERATOR = "claude-cowork"

# Matrix status codes -> canonical record values
_STATUS_MAP = {
    "CLOSD": "closed",
    "CLOSED": "closed",
    "PEND": "pending",
    "PENDING": "pending",
    "ACT": "active",
    "ACTIVE": "active",
}

# Appraiser Single Line has public-records columns absent in Agent Single Line
_APPRAISER_MARKER = "PR Abv Fin SqFt"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _normalize_status(raw):
    """Map Matrix status codes to 'closed' | 'active' | 'pending' | 'unknown'."""
    v = str(raw).strip().upper() if raw else ""
    return _STATUS_MAP.get(v, "unknown")


def _normalize_mls(raw):
    """Strip BRT prefix from CVR/Bright shared listings: BRTVA… -> VA…"""
    if not raw:
        return None
    s = str(raw).strip()
    if s.upper().startswith("BRT"):
        s = s[3:]
    return s or None


def _parse_float(raw):
    """Parse numeric string (strips $, commas). Returns float or None."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(raw):
    """Parse integer string. Returns int or None."""
    v = _parse_float(raw)
    return int(round(v)) if v is not None else None


def _parse_baths(raw):
    """
    'Total Baths' convention in Matrix exports: 2.1 = 2 full / 1 half.
    Returns (full_baths, half_baths) or (None, None).
    """
    v = _parse_float(raw)
    if v is None:
        return None, None
    full = int(v)
    half = int(round((v - full) * 10))
    return full, half


def _detect_layout(fieldnames):
    """Return 'appraiser' or 'agent' based on CSV header."""
    return "appraiser" if _APPRAISER_MARKER in (fieldnames or []) else "agent"


def _add_flag(flags, msg):
    """Append flag message if not already present."""
    if msg not in flags:
        flags.append(msg)


def _city_from_address(addr_str):
    """
    Best-effort: extract city/county segment from 'Street, City, ST ZIP' pattern.
    Returns the second-to-last comma segment, or None.
    """
    if not addr_str:
        return None
    parts = [p.strip() for p in str(addr_str).split(",")]
    return parts[-2].strip() if len(parts) >= 3 else None


def _parse_date(raw):
    """Best-effort parse of a sale-date string to a date. Handles YYYY-MM-DD,
    ISO datetimes (...Z), MM/DD/YYYY, and MM/YYYY (-> 1st of month). None on miss."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%m/%d/%Y", "%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _months_before(d, months):
    """The date `months` calendar-months before date d (day clamped to month end)."""
    import calendar
    total = (d.year * 12 + (d.month - 1)) - months
    y, m = divmod(total, 12)
    m += 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.__class__(y, m, day)


def _sale_window_flag(status, sale_date, anchor_date, window_months=12):
    """12-month sales-window gate (vault andon 2026-06-26 #3; demoted 2026-07-02).
    For a CLOSED comp: a sale genuinely older than the window -> HARD flag; a
    missing date -> INFO-prefixed note only (the single-line CSV never carries a
    close date, so a hard flag there fired on every comp = noise). Active/pending
    comps are not sold, so they are exempt."""
    if status != "closed":
        return None
    if not sale_date:
        return ("INFO: close date not captured in the single-line export — capture "
                "the close date (12-month window not yet verified)")
    sd = _parse_date(sale_date)
    if sd is None:
        return "Sale date '{}' is unparseable — verify the 12-month window".format(sale_date)
    if anchor_date and sd < _months_before(anchor_date, window_months):
        return ("Sale {} is outside the {}-month window — supplemental only, needs an "
                "explicit dated justification (never primary/unlabeled)"
                .format(sale_date, window_months))
    return None


def _gla_band_flag(comp_gla, subject_gla, pct=10):
    """Comp-selection rubric #1 (vault 2026-06-23): above-grade GLA within +/-pct%
    of subject. Returns a flag string when out of band, else None."""
    if comp_gla is None or not subject_gla:
        return None
    diff = (comp_gla - subject_gla) / subject_gla * 100.0
    if abs(diff) > pct:
        return ("Above-grade GLA {:+.0f}% vs subject — outside the ±{}% rubric band; "
                "highlight for YV (never silently include or drop)".format(diff, pct))
    return None


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------
def _parse_comp_row(row, layout, subject_county, subject_gla_sf, window_anchor=None):
    """Parse one DictReader row into a comp dict with flags populated."""
    flags = []

    # --- identifiers ---
    raw_mls = (row.get("ML #") or "").strip()
    mls_number = _normalize_mls(raw_mls) if raw_mls else None
    if raw_mls and raw_mls.upper().startswith("BRT"):
        _add_flag(flags, "MLS# normalized: BRT prefix stripped (Bright MLS via CVR)")

    pid = (row.get("PID") or "").strip() or None
    mls_system = (row.get("MLS") or "").strip() or None
    subdivision = (row.get("Subdivision") or "").strip() or None

    # --- address + county detection ---
    address_full = (row.get("Address") or "").strip() or None
    comp_city = _city_from_address(address_full)
    out_of_county = None
    if subject_county and comp_city:
        sc_l = subject_county.lower()
        cc_l = comp_city.lower()
        if sc_l not in cc_l and cc_l not in sc_l:
            out_of_county = True
            _add_flag(flags,
                      "Out-of-county: comp area '{}' vs subject county '{}' "
                      "— verify SOR".format(comp_city, subject_county))
        else:
            out_of_county = False

    # --- status ---
    raw_status = (row.get("Status") or "").strip()
    status = _normalize_status(raw_status)
    if status == "unknown" and raw_status:
        _add_flag(flags, "Unknown status '{}' — verify".format(raw_status))

    # --- position ---
    position = _parse_int(row.get("#"))

    # --- characteristics ---
    bedrooms = _parse_int(row.get("# Bedrooms"))
    full_baths, half_baths = _parse_baths(row.get("Total Baths"))
    total_rooms = _parse_int(row.get("# Rooms"))
    prop_type = (row.get("Prop Type") or "").strip() or None  # appraiser layout only

    # GLA: use Total Finished Area (MLS-reported) as the governing value.
    # PR Living SqFt (public records) is informational only; needs separate verification.
    gla_raw = (row.get("Total Finished Area") or "").strip()
    gla_sf = _parse_float(gla_raw)
    if gla_sf is None or gla_sf <= 0:
        gla_sf = None
        _add_flag(flags, "GLA unverified — missing or zero in MLS; do not estimate")

    above_grade_sf = None
    if layout == "appraiser":
        above_grade_sf = _parse_float(row.get("PR Abv Fin SqFt")) or None

    # --- sale ---
    distance_mi = _parse_float(row.get("Distance"))
    dom = _parse_int(row.get("Days On Market"))
    list_price = _parse_float(row.get("List Price"))
    sale_price = _parse_float(row.get("Sales Price"))
    orig_list = _parse_float(row.get("Original List Price")) if layout == "appraiser" else None
    sale_date = None  # not in single-line CSV; populated from CAMA/MLS elsewhere

    # --- derived ---
    price_per_sf = None
    if sale_price and gla_sf and gla_sf > 0:
        price_per_sf = round(sale_price / gla_sf, 2)

    gla_delta = None
    if gla_sf is not None and subject_gla_sf is not None:
        gla_delta = round(gla_sf - subject_gla_sf, 0)

    # --- comp-quality gates (interlane 2026-06-26 [ACTION] #3/#5; vault 2026-06-17/06-23) ---
    if not mls_number:
        _add_flag(flags, "ML# missing — required for DataMaster; capture from Matrix")
    if not pid:
        _add_flag(flags, "Tax ID / PID missing — required for DataMaster; capture from Matrix")
    gla_flag = _gla_band_flag(gla_sf, subject_gla_sf)
    if gla_flag:
        _add_flag(flags, gla_flag)
    window_flag = _sale_window_flag(status, sale_date, window_anchor)
    if window_flag:
        _add_flag(flags, window_flag)

    return {
        "position": position,
        "status": status,
        "address": {
            "full": address_full,
            "county": comp_city,
        },
        "distance_mi": distance_mi,
        "identifiers": {
            "mls_number": mls_number,
            "mls_system": mls_system,
            "pid": pid,
            "subdivision": subdivision,
        },
        "characteristics": {
            "gla_sf": gla_sf,
            "above_grade_sf": above_grade_sf,
            "year_built": None,   # not in single-line CSV; DataMaster pulls it
            "bedrooms": bedrooms,
            "full_baths": full_baths,
            "half_baths": half_baths,
            "total_rooms": total_rooms,
            "property_type": prop_type,
        },
        "sale": {
            "sale_price": sale_price,
            "list_price": list_price,
            "original_list_price": orig_list,
            "dom": dom,
            "sale_date": sale_date,
            "concessions": None,  # not in single-line CSV
        },
        "price_per_sf": price_per_sf,
        "gla_delta_vs_subject_sf": gla_delta,
        "flags": flags,
        "out_of_county": out_of_county,
        "prior_sale": None,  # not in single-line CSV; appraiser supplies
        "geo": {"lat": None, "lon": None},
    }


def parse_comps_csv(csv_path, subject_county, subject_gla_sf, window_anchor=None):
    """
    Parse a DataMaster Single Line CSV (either layout).
    Returns list of comp dicts, preserving row order.
    """
    comps = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        layout = _detect_layout(reader.fieldnames)
        for row in reader:
            comp = _parse_comp_row(row, layout, subject_county, subject_gla_sf, window_anchor)
            comps.append(comp)
    return comps


# ---------------------------------------------------------------------------
# record assembly
# ---------------------------------------------------------------------------
def assemble(subject_json_path, comps_csv_path, out_path,
             comps_agent_csv_path=None, generated_at=None, **order_meta):
    """
    Assemble appraisal-record.json from subject.json + comp CSV(s).

    Args:
        subject_json_path:   Path to subject.json
        comps_csv_path:      Path to Appraiser Single Line CSV (or list of paths)
        out_path:            Destination path for appraisal-record.json
        comps_agent_csv_path:Optional Agent Single Line CSV (active/pending listings)
        generated_at:        ISO timestamp string (default: current UTC). Fix this
                             for byte-identical deterministic runs.
        **order_meta:        Override order fields (order_id, client, fee, etc.)

    Returns:
        dict — the assembled record
    """
    # -- load subject --
    # utf-8-sig tolerates a UTF-8 BOM, which some editors / PowerShell add when
    # writing subject.json. Plain utf-8 would raise on the BOM.
    with open(subject_json_path, "r", encoding="utf-8-sig") as fh:
        subj = json.load(fh)

    subject_county = (subj.get("address") or {}).get("county")
    subject_gla_sf = (subj.get("characteristics") or {}).get("gla_sf")

    # Resolve generated_at up front so it can anchor the 12-mo sales-window gate
    # (deterministic: fixed input -> fixed anchor).
    if not generated_at:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    eff_raw = order_meta.get("effective_date") or (subj.get("order") or {}).get("effective_date")
    window_anchor = _parse_date(eff_raw) or _parse_date(generated_at[:10])

    # -- parse comps ---
    # Accept a single path, a list of paths, or None
    if isinstance(comps_csv_path, (list, tuple)):
        csv_paths = list(comps_csv_path)
    elif comps_csv_path:
        csv_paths = [comps_csv_path]
    else:
        csv_paths = []

    if comps_agent_csv_path:
        csv_paths.append(comps_agent_csv_path)

    all_comps = []
    for cp in csv_paths:
        if cp and os.path.isfile(cp):
            all_comps.extend(parse_comps_csv(cp, subject_county, subject_gla_sf, window_anchor))
        elif cp:
            sys.stderr.write("WARNING: comps CSV not found: {}\n".format(cp))

    # renumber positions sequentially if any are None
    for i, comp in enumerate(all_comps):
        if comp["position"] is None:
            comp["position"] = i + 1

    # -- order section: subject.json base + CLI overrides --
    order_base = subj.get("order") or {}
    order = {
        "order_id":       order_meta.get("order_id",       order_base.get("order_id")),
        "form_type":      order_meta.get("form_type",      order_base.get("form_type")),
        "client":         order_meta.get("client",         order_base.get("client")),
        "loan_number":    order_meta.get("loan_number",    order_base.get("loan_number")),
        "effective_date": order_meta.get("effective_date", order_base.get("effective_date")),
        "due_date":       order_meta.get("due_date",       order_base.get("due_date")),
        "inspection":     order_meta.get("inspection",     order_base.get("inspection")),
        "fee":            order_meta.get("fee",            order_base.get("fee")),
        "status":         order_meta.get("status",         order_base.get("status", "in-progress")),
    }

    # Contract block (v1.1, 6/19 brief) — passthrough from CLI/kwargs, else
    # subject.json's order.contract; all-null for refi orders.
    contract_base = order_base.get("contract") or {}
    order["contract"] = {
        "contract_price":            order_meta.get("contract_price",            contract_base.get("contract_price")),
        "contract_date":             order_meta.get("contract_date",             contract_base.get("contract_date")),
        "seller_is_owner_of_record": order_meta.get("seller_is_owner_of_record", contract_base.get("seller_is_owner_of_record")),
        "concessions":               order_meta.get("concessions",               contract_base.get("concessions")),
        "financing_type":            order_meta.get("financing_type",            contract_base.get("financing_type")),
    }

    # -- subject section --
    ch   = subj.get("characteristics") or {}
    ids  = subj.get("identifiers") or {}
    addr = subj.get("address") or {}

    subject = {
        "address": {
            "full":   addr.get("full"),
            "street": addr.get("street"),
            "city":   addr.get("city"),
            "state":  addr.get("state"),
            "zip":    addr.get("zip"),
            "county": addr.get("county"),
        },
        "flags": subj.get("flags") or [],
        "characteristics": {
            "property_type":           ch.get("property_type"),
            "use_code":                ch.get("use_code"),
            "zoning":                  ch.get("zoning"),
            "gla_sf":                  ch.get("gla_sf"),
            "above_grade_sf":          ch.get("above_grade_sf"),
            "below_grade_finished_sf": ch.get("below_grade_finished_sf"),
            "basement":                ch.get("basement"),
            "year_built":              ch.get("year_built"),
            "stories":                 ch.get("stories"),
            "style":                   ch.get("style"),
            "grade_or_condition":      ch.get("grade_or_condition"),
            "bedrooms":                ch.get("bedrooms"),
            "full_baths":              ch.get("full_baths"),
            "half_baths":              ch.get("half_baths"),
            "total_rooms":             ch.get("total_rooms"),
            "lot_size_sf":             ch.get("lot_size_sf"),
            "lot_size_acres":          ch.get("lot_size_acres"),
            "garage":                  ch.get("garage"),
            "pool":                    ch.get("pool"),
            "fireplaces":              ch.get("fireplaces"),
            "heating":                 ch.get("heating"),
            "cooling":                 ch.get("cooling"),
            "exterior":                ch.get("exterior"),
        },
        "identifiers": {
            "gpin":                 ids.get("gpin"),
            "pid":                  ids.get("pid"),
            "apn":                  ids.get("apn"),
            "subdivision":          ids.get("subdivision"),
            "section":              ids.get("section"),
            "block":                ids.get("block"),
            "lot":                  ids.get("lot"),
            "magisterial_district": ids.get("magisterial_district"),
            "neighborhood_code":    ids.get("neighborhood_code"),
            "legal_description":    ids.get("legal_description"),
        },
        "assessment": subj.get("assessment") or {
            "tax_year": None, "land_value": None,
            "improvements_value": None, "total_value": None,
        },
        "resolution": subj.get("resolution") or {
            "input_was_address_only": None, "method": None,
            "no_tax_id": False, "neighbor_unit_proxy": None,
            "cached": False, "resolved_on": None,
        },
        "verification":  subj.get("verification") or [],
        "listing":       subj.get("listing"),
        "sales_history": subj.get("sales_history") or [],
        "geo":           subj.get("geo") or {"lat": None, "lon": None},

        # -- v1.1 DM-ready fields (6/19 brief). Defaults ONLY when the source
        #    value is absent; a supplied value always wins.
        "assessors_parcel_number": subj.get("assessors_parcel_number"),
        "map_reference": subj.get("map_reference") or "GIS",   # Change 2
        "walls_trim":    subj.get("walls_trim") or "Wood",     # Change 3
        # Change 4: passthrough or null. NEVER inferred from county/ZIP —
        # rural does not mean Well/Septic; renderer shows TBD when null.
        "water": subj.get("water"),
        "sewer": subj.get("sewer"),
        "re_taxes_annual": subj.get("re_taxes_annual"),        # Change 7: bill, not assessment
        "hoa_amount": subj.get("hoa_amount"),                  # Change 8
        "hoa_period": subj.get("hoa_period"),
        "neighborhood_bounds": subj.get("neighborhood_bounds"),
        "neighborhood_description_context": subj.get("neighborhood_description_context"),
    }

    # Change 8: HOA is always a DM field — a missing amount must surface, never vanish.
    if subject["hoa_amount"] is None:
        _add_flag(subject["flags"], "HOA TBD — get from HOA docs (amount + period not captured)")

    # -- market section --
    market_base = subj.get("market") or {}
    market = {
        "search": market_base.get("search") or {
            "radius_mi": None,
            "sale_window_months": None,
            "gla_band": {"low_sf": None, "high_sf": None, "luxury_widened": False},
            "mls_systems": [],
        },
        "neighborhood_notes": market_base.get("neighborhood_notes"),
    }

    # -- stamp -- (generated_at already resolved above, to anchor the sales-window gate)

    # -- assemble record --
    record = {
        "schema_version": SCHEMA_VERSION,
        "generated_at":   generated_at,
        "generated_by":   GENERATOR,
        "order":          order,
        "subject":        subject,
        "comps":          all_comps,
        "market":         market,
        "photos":         [],
        "sources":        subj.get("sources") or [],
        "review":         {"human_reviewed": False, "notes": None},
        "adjustments":    {"entered_by_appraiser": False},
    }

    # -- write output --
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)

    closed_n  = sum(1 for c in all_comps if c.get("status") == "closed")
    active_n  = sum(1 for c in all_comps if c.get("status") in ("active", "pending"))
    flagged_n = sum(1 for c in all_comps if c.get("flags"))
    ooc_n     = sum(1 for c in all_comps if c.get("out_of_county"))

    print("Wrote {} | {} closed, {} active/pending, {} flagged, {} out-of-county".format(
        out_path, closed_n, active_n, flagged_n, ooc_n))

    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Build B — assemble appraisal-record.json from subject.json + comps CSV(s)")
    ap.add_argument("subject",   help="Path to subject.json")
    ap.add_argument("comps",     help="Path to Appraiser Single Line comps CSV")
    ap.add_argument("output",    help="Output path for appraisal-record.json")
    ap.add_argument("--comps-agent", metavar="PATH",
                    help="Optional Agent Single Line CSV (active/pending listings)")
    ap.add_argument("--generated-at", metavar="ISO",
                    help="Fix the generated_at timestamp for deterministic runs")
    # order overrides
    ap.add_argument("--order-id")
    ap.add_argument("--form-type")
    ap.add_argument("--client")
    ap.add_argument("--loan-number")
    ap.add_argument("--effective-date")
    ap.add_argument("--due-date")
    ap.add_argument("--inspection")
    ap.add_argument("--fee", type=float)
    ap.add_argument("--status")
    # contract block (v1.1) — purchase orders only
    ap.add_argument("--contract-price", type=float)
    ap.add_argument("--contract-date")
    ap.add_argument("--seller-owner", choices=["yes", "no"],
                    help="Is the seller the owner of record?")
    ap.add_argument("--concessions")
    ap.add_argument("--financing-type")
    args = ap.parse_args(argv)

    order_meta = {}
    if args.order_id:       order_meta["order_id"]       = args.order_id
    if args.form_type:      order_meta["form_type"]      = args.form_type
    if args.client:         order_meta["client"]         = args.client
    if args.loan_number:    order_meta["loan_number"]    = args.loan_number
    if args.effective_date: order_meta["effective_date"] = args.effective_date
    if args.due_date:       order_meta["due_date"]       = args.due_date
    if args.inspection:     order_meta["inspection"]     = args.inspection
    if args.fee is not None:order_meta["fee"]            = args.fee
    if args.status:         order_meta["status"]         = args.status
    if args.contract_price is not None: order_meta["contract_price"] = args.contract_price
    if args.contract_date:  order_meta["contract_date"]  = args.contract_date
    if args.seller_owner:   order_meta["seller_is_owner_of_record"] = (args.seller_owner == "yes")
    if args.concessions:    order_meta["concessions"]    = args.concessions
    if args.financing_type: order_meta["financing_type"] = args.financing_type

    assemble(
        subject_json_path=args.subject,
        comps_csv_path=args.comps,
        out_path=args.output,
        comps_agent_csv_path=args.comps_agent,
        generated_at=args.generated_at,
        **order_meta,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
