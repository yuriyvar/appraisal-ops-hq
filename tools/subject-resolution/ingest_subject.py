#!/usr/bin/env python3
"""
Build C — subject ingester/normalizer (Phase 3).

Takes the hand-filled subject.skeleton.json (or any raw subject dict), applies
the pipeline's normalizations + fail-loud gates, writes a validated
subject.json, and — ONLY on valid input — stores it in the subject cache
(single write path into the cache; junk never gets cached).

Normalizations / gates:
  * numeric strings cleaned ("1,856 sf" / "$2,513.40" -> numbers)
  * lot acreage <-> sf cross-check (>2% apart -> flag BOTH, keep both)
  * fractional full_baths split per the Matrix N.M convention (+ flag)
  * Chesterfield APN dashes stripped into assessors_parcel_number (+ flag;
    identifiers.apn keeps the SOR formatting)
  * GLA missing/zero -> null + flag (NEVER estimated)
  * tax_year vs effective-date sanity flags
  * helper key "photo_derived": [field, ...] -> per-field "confirm at
    inspection" flags (Zillow rule); helper keys never reach the output
  * BD2 multi-source verification: helper blocks "source_values"
    {field: {mls, county, zillow}} + "variance_notes" {field: reason} ->
    canonical value + verification row per YV's protocol (listing supports the
    variance -> MLS governs with the reason; else County rules; either way
    "inconsistent — manual triage" until YV clears). "gla_mls_sf" back-compat.

Usage:
    python ingest_subject.py subject.skeleton.json --out subject.json \
        [--resolved-on 2026-07-02] [--source "APEX pull"] [--db PATH] [--no-cache]
"""

import argparse
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from subject_cache import put as cache_put

SF_PER_ACRE = 43560.0
LOT_TOLERANCE = 0.02

_NUM_FIELDS_F = {
    "characteristics": ["gla_sf", "above_grade_sf", "below_grade_finished_sf",
                        "lot_size_sf", "lot_size_acres", "stories"],
    "assessment": ["land_value", "improvements_value", "total_value"],
}
_NUM_FIELDS_I = {
    "characteristics": ["year_built", "bedrooms", "total_rooms", "fireplaces"],
    "assessment": ["tax_year"],
}
_HELPER_KEYS = ("photo_derived", "gla_mls_sf", "source_values", "variance_notes")

# BD2 multi-source verification: field -> (verification label, tolerance).
# tolerance 0 = exact match required; else fractional (0.02 = 2%).
_MULTI_SOURCE = {
    "gla_sf":         ("Finished area (sf)", 0.02),
    "year_built":     ("Year built", 0),
    "lot_size_acres": ("Lot size (ac)", 0.02),
    "bedrooms":       ("Bedrooms", 0),
    "full_baths":     ("Baths (N.M)", 0),
    "stories":        ("Stories", 0),
}


def _num(v):
    """'1,856 sf' / '$2,513.40' / 1856 -> float | None. Non-numeric strings
    raise (fail loud — a typo must not silently become null)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"(?i)[$,]|\bsf\b|\bsq\.? ?ft\.?\b|\bacres?\b|\bac\b", "", str(v)).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError("non-numeric value {!r}".format(v))


def _add(flags, msg):
    if msg not in flags:
        flags.append(msg)


def _fmt_src(field, v):
    if v is None:
        return None
    if field == "gla_sf":
        return "{:,.0f}".format(v)
    return str(int(v)) if float(v) == int(v) else str(v)


def _resolve_sources(subj, raw, flags):
    """BD2 — YV's variance protocol (2026-07-02). Per tracked field with
    per-source values: county-vs-MLS agreement -> county governs quietly;
    disagreement + a variance_notes justification -> MLS governs WITH the reason;
    disagreement without one -> County rules; EITHER WAY the row is flagged
    'inconsistent — manual triage' until YV clears it. Zillow never governs
    unless it's the only source; a lone Zillow disagreement is informational."""
    sv = dict(raw.get("source_values") or {})
    notes = raw.get("variance_notes") or {}
    ch = subj.setdefault("characteristics", {})

    # back-compat: the Build-C-era gla_mls_sf helper folds into source_values
    legacy = _num(raw.get("gla_mls_sf"))
    if legacy is not None:
        entry = dict(sv.get("gla_sf") or {})
        entry.setdefault("mls", legacy)
        sv["gla_sf"] = entry

    ver = subj.setdefault("verification", [])
    for field, (label, tol) in _MULTI_SOURCE.items():
        entry = sv.get(field) or {}
        if not any(v is not None for v in entry.values()):
            continue                        # skeleton's empty slots / untracked pull
        county = _num(entry.get("county"))
        if county is None:
            county = _num(ch.get(field))    # value already pulled = the county card
        mls = _num(entry.get("mls"))
        zil = _num(entry.get("zillow"))
        if county is None and mls is None and zil is None:
            continue

        def differ(a, b):
            if a is None or b is None:
                return False
            if tol == 0:
                return a != b
            base = max(abs(a), abs(b)) or 1.0
            return abs(a - b) / base > tol

        vflag = None
        just = str(notes.get(field) or "").strip()
        if county is not None and mls is not None and differ(county, mls):
            if just:
                canonical, governing = mls, "mls (justified)"
                vflag = ("county vs MLS {} differ — variance SUPPORTED: {} — "
                         "inconsistent, manual triage until YV clears".format(label, just))
            else:
                canonical, governing = county, "county"
                delta = "differ >{:.0f}%".format(tol * 100) if tol else "differ"
                vflag = ("county vs MLS {} {} — inconsistent, manual triage "
                         "(no supporting listing evidence); County rules".format(label, delta))
        elif county is not None:
            canonical, governing = county, "county"
        elif mls is not None:
            canonical, governing = mls, "mls"
            vflag = "county value not captured — verify {} at the SOR".format(label)
        else:
            canonical, governing = zil, "zillow"
            vflag = "Zillow-only {} — weakest source, verify".format(label)

        if zil is not None and differ(zil, canonical) and "manual triage" not in (vflag or ""):
            note = "Zillow differs (informational; Zillow never governs)"
            vflag = (vflag + "; " + note) if vflag else note

        ch[field] = canonical
        ver.append({"attribute": label,
                    "county": _fmt_src(field, county), "zillow": _fmt_src(field, zil),
                    "realtor": None, "redfin": None, "homes": None,
                    "mls": _fmt_src(field, mls),
                    "governing_source": governing, "flag": vflag})
        if vflag and "manual triage" in vflag:
            _add(flags, vflag)              # header chip, not just the row


def ingest(raw, resolved_on=None, source=None, as_of=None):
    """Normalize a raw subject dict in place-safe copy. Returns (subject, flags).
    Raises ValueError on hard errors (bad address, unparseable numerics)."""
    subj = json.loads(json.dumps(raw))  # deep copy
    flags = subj.setdefault("flags", [])

    addr = subj.get("address") or {}
    if not addr.get("full") or not addr.get("county"):
        raise ValueError("address.full and address.county are required "
                         "(assembler contract) — fill them before ingest")

    # numerics
    for section, keys in list(_NUM_FIELDS_F.items()) + list(_NUM_FIELDS_I.items()):
        blk = subj.get(section) or {}
        for k in keys:
            v = _num(blk.get(k))
            if v is not None and section in _NUM_FIELDS_I and k in _NUM_FIELDS_I[section]:
                v = int(round(v))
            if k in blk or v is not None:
                blk[k] = v
    for k in ("re_taxes_annual", "hoa_amount"):
        if k in subj:
            subj[k] = _num(subj.get(k))

    ch = subj.setdefault("characteristics", {})

    # BD2 — multi-source resolution runs BEFORE the gates so they apply to the
    # canonical values (e.g. a resolved 2.1 still gets the baths split below).
    _resolve_sources(subj, raw, flags)

    # fractional full_baths -> Matrix N.M split
    fb = ch.get("full_baths")
    if fb is not None:
        fbf = _num(fb)
        if fbf is not None and fbf != int(fbf):
            full = int(fbf)
            half = int(round((fbf - full) * 10))
            ch["full_baths"], ch["half_baths"] = full, half
            _add(flags, "baths split from {} per the Matrix N.M convention "
                        "— verify full/half counts".format(fb))
        elif fbf is not None:
            ch["full_baths"] = int(fbf)
    hb = _num(ch.get("half_baths"))
    ch["half_baths"] = int(hb) if hb is not None else ch.get("half_baths")

    # GLA gate — never estimated
    if not ch.get("gla_sf"):
        ch["gla_sf"] = None
        _add(flags, "GLA unverified — missing or zero; do not estimate")

    # lot sf <-> acreage cross-check (keep both, flag both)
    sf_v, ac_v = ch.get("lot_size_sf"), ch.get("lot_size_acres")
    if sf_v and ac_v:
        implied = ac_v * SF_PER_ACRE
        if implied > 0 and abs(sf_v - implied) / implied > LOT_TOLERANCE:
            _add(flags, "lot size mismatch: {:,.0f} sf vs {} ac (= {:,.0f} sf) "
                        "— verify at the SOR".format(sf_v, ac_v, implied))

    # county APN quirks
    county = (addr.get("county") or "").lower()
    apn = (subj.get("identifiers") or {}).get("apn")
    if apn and not subj.get("assessors_parcel_number"):
        if "chesterfield" in county and "-" in str(apn):
            subj["assessors_parcel_number"] = str(apn).replace("-", "")
            _add(flags, "Chesterfield TaxID normalized (dashes stripped) for "
                        "DataMaster — SOR formatting kept in identifiers.apn")
        else:
            subj["assessors_parcel_number"] = str(apn)

    # tax-year sanity vs effective date
    eff = ((subj.get("order") or {}).get("effective_date")) or as_of
    eff_year = None
    if eff:
        m = re.match(r"(\d{4})", str(eff))
        eff_year = int(m.group(1)) if m else None
    ty = (subj.get("assessment") or {}).get("tax_year")
    if ty and eff_year:
        if ty < eff_year:
            _add(flags, "assessment tax year {} is behind the effective year {} "
                        "— re-verify the assessment".format(ty, eff_year))
        elif ty > eff_year:
            _add(flags, "assessment tax year {} is AFTER the effective year {} "
                        "— check for a data-entry error".format(ty, eff_year))

    # Zillow / photo-derived rule
    for field in (raw.get("photo_derived") or []):
        _add(flags, "{} derived from Zillow photos — confirm at inspection".format(field))

    # helper keys never reach the output
    for k in _HELPER_KEYS:
        subj.pop(k, None)

    # resolution stamp
    res = subj.setdefault("resolution", {})
    res["cached"] = False
    res["resolved_on"] = resolved_on or res.get("resolved_on") or \
        (str(as_of)[:10] if as_of else date.today().isoformat())
    if source:
        res["method"] = res.get("method") or source

    return subj, flags


def tick_run_log(raw_path, as_of=None):
    """BD1: ingest ticks its own step in the resolver's run-log.md (same dir as
    the raw file). Missing log = nothing to tick (P2's provenance gate handles
    the visibility). Returns True when a tick happened."""
    rl = os.path.join(os.path.dirname(os.path.abspath(raw_path)), "run-log.md")
    if not os.path.isfile(rl):
        return False
    with open(rl, "r", encoding="utf-8-sig") as fh:
        text = fh.read()
    needle = "- [ ] 3. ingest_subject"
    if needle not in text:
        return False
    stamp = str(as_of)[:10] if as_of else date.today().isoformat()
    text = text.replace(
        needle + " — subject.json written + cached",
        "- [x] 3. ingest_subject — subject.json written + cached @ " + stamp, 1)
    with open(rl, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build C — normalize + gate a raw subject pull")
    ap.add_argument("raw", help="subject.skeleton.json (hand-filled)")
    ap.add_argument("--out", help="output subject.json (default: alongside input)")
    ap.add_argument("--resolved-on", help="pull date (default: today)")
    ap.add_argument("--source", help="provenance note for the cache")
    ap.add_argument("--db", help="cache DB override")
    ap.add_argument("--as-of", help="date context for sanity checks (tests)")
    ap.add_argument("--no-cache", action="store_true", help="skip the cache put")
    args = ap.parse_args(argv)

    with open(args.raw, "r", encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    try:
        subject, flags = ingest(raw, resolved_on=args.resolved_on,
                                source=args.source, as_of=args.as_of)
    except ValueError as e:
        sys.stderr.write("INGEST REFUSED: {}\n".format(e))
        return 2

    # BD1 provenance gate — warn loud, never block: a raw file with no resolver
    # pull sheet beside it means the standard work was bypassed upstream.
    ps = os.path.join(os.path.dirname(os.path.abspath(args.raw)), "pull-sheet.md")
    if not os.path.isfile(ps):
        msg = "ingested without a resolver pull sheet — standard work not verified"
        if msg not in subject["flags"]:
            subject["flags"].append(msg)
        sys.stderr.write("WARNING: {} (run resolve_subject.py first next time)\n".format(msg))

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.raw)),
                                   "subject.json")
    ap_out = os.path.abspath(out)
    if ap_out.startswith(REPO + os.sep):
        sys.stderr.write("ERROR: output inside the repo — order files live in "
                         "the client zone: {}\n".format(ap_out))
        return 2
    with open(ap_out, "w", encoding="utf-8") as fh:
        json.dump(subject, fh, indent=2, ensure_ascii=False)
    print("Wrote " + ap_out)
    for f in flags:
        print("FLAG  " + f)

    if not args.no_cache:
        key = cache_put(subject["address"]["full"], subject,
                        args.source or subject["resolution"].get("method") or "ingest",
                        db_path=args.db)
        print("CACHED key=" + key)
    if tick_run_log(args.raw, args.as_of):
        print("run-log.md: step 3 ticked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
