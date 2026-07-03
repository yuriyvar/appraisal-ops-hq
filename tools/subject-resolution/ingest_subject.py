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
  * helper key "gla_mls_sf" -> cross-source verification row (county governs)

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
_HELPER_KEYS = ("photo_derived", "gla_mls_sf")


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

    # cross-source verification seed (county SOR governs GLA)
    mls_gla = _num(raw.get("gla_mls_sf"))
    if mls_gla is not None and ch.get("gla_sf"):
        vflag = None
        if abs(mls_gla - ch["gla_sf"]) / ch["gla_sf"] > 0.02:
            vflag = "county vs MLS finished area differ >2% — reconcile before comps"
            _add(flags, vflag)
        ver = subj.setdefault("verification", [])
        ver.append({"attribute": "Finished area (sf)",
                    "county": "{:,.0f}".format(ch["gla_sf"]),
                    "zillow": None, "realtor": None, "redfin": None, "homes": None,
                    "mls": "{:,.0f}".format(mls_gla),
                    "governing_source": "county", "flag": vflag})

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
