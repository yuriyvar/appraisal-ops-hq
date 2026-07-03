#!/usr/bin/env python3
"""
Build C — ArcGIS FeatureServer adapter (Phase 4, STRETCH).

The one SOR vendor family with clean JSON (no HTML scraping): county parcel
FeatureServers (Chesterfield; Hanover via civ.quest). Queries the layer by
address and maps attributes into an existing subject.skeleton.json — filling
ONLY fields that are still null, never overwriting, always flagging the pull
for verification.

Fail-loud contract (Build C brief, constraint 6):
  * ANY failure — offline, endpoint moved, 0 rows, >1 candidate rows, missing
    attributes — prints a clear message, exits non-zero, touches NOTHING, and
    the normal pull-sheet path continues to apply.
  * Field maps ship UNVERIFIED (attribute names can't be confirmed offline);
    every auto-filled skeleton carries a "verify against the SOR card" flag,
    and unverified maps say so loudly. Verify + flip `verified` on the first
    live pull.
  * No cache writes here — only ingest_subject.py writes the cache.

Usage:
    python fetch_arcgis.py "<address>" --county Chesterfield \
        --skeleton <order>/subject.skeleton.json [--out <path>] [--timeout 15]
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# Attribute maps: record-path -> layer attribute. UNVERIFIED until a live pull
# confirms the names; unknown attributes are skipped + reported, never guessed.
FIELD_MAPS = {
    "Chesterfield": {
        "verified": False,
        "layer_url": ("https://services3.arcgis.com/TsynfzBSE6sXfoLq/arcgis/"
                      "rest/services/Cadastral_ProdA/FeatureServer/3"),
        "address_field": "SITEADDRESS",
        "attrs": {
            "identifiers.apn":                    "TAXID",
            "identifiers.legal_description":      "LEGALDESC",
            "identifiers.subdivision":            "SUBDIVISION",
            "characteristics.year_built":         "YEARBUILT",
            "characteristics.lot_size_acres":     "ACREAGE",
            "characteristics.zoning":             "ZONING",
            "assessment.total_value":             "TOTALVALUE",
        },
    },
    "Hanover": {
        "verified": False,
        "layer_url": "https://maps.civ.quest/arcgis/rest/services/Hanover/Public/FeatureServer/0",
        "address_field": "SITEADDRESS",
        "attrs": {
            "identifiers.apn":                "GPIN",
            "identifiers.legal_description":  "LEGALDESC",
            "characteristics.year_built":     "YEARBUILT",
            "characteristics.lot_size_acres": "ACREAGE",
        },
    },
}


class FetchError(Exception):
    """Any condition where the manual pull sheet must take over."""


def query_layer(county, address, timeout=15, opener=None):
    """GET the FeatureServer query endpoint. Returns the parsed JSON.
    opener is injectable for tests; the default uses urllib."""
    fm = FIELD_MAPS.get(county)
    if not fm:
        raise FetchError("no ArcGIS field map for {!r} (have: {})".format(
            county, ", ".join(sorted(FIELD_MAPS))))
    street = str(address).split(",")[0].strip().upper()
    params = urllib.parse.urlencode({
        "where": "UPPER({}) LIKE '%{}%'".format(
            fm["address_field"], street.replace("'", "''")),
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    })
    url = fm["layer_url"] + "/query?" + params
    try:
        if opener is not None:
            body = opener(url)
        else:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
        data = json.loads(body)
    except FetchError:
        raise
    except Exception as e:
        raise FetchError("query failed ({}: {}) — use the manual pull sheet"
                         .format(type(e).__name__, e))
    if isinstance(data, dict) and data.get("error"):
        raise FetchError("server error {} — endpoint may have moved; update "
                         "county_routing.json + FIELD_MAPS".format(data["error"]))
    return data


def map_features(county, data):
    """Exactly one feature -> ({record_path: value}, [missing_attr_names]).
    0 or >1 features raise (never pick a candidate silently)."""
    fm = FIELD_MAPS[county]
    feats = (data or {}).get("features") or []
    if len(feats) == 0:
        raise FetchError("no parcel matched — check the address or use the pull sheet")
    if len(feats) > 1:
        raise FetchError("{} candidate parcels matched — refine the address; "
                         "never auto-picking one".format(len(feats)))
    attrs = feats[0].get("attributes") or {}
    mapped, missing = {}, []
    for path, attr in fm["attrs"].items():
        if attr in attrs and attrs[attr] not in (None, ""):
            mapped[path] = attrs[attr]
        else:
            missing.append(attr)
    if not mapped:
        raise FetchError("feature had none of the mapped attributes — field map "
                         "is wrong; verify names and update FIELD_MAPS")
    return mapped, missing


def apply_to_skeleton(skeleton, mapped, county):
    """Fill nulls only; never overwrite; flag the pull. Returns (skeleton, set_paths)."""
    sk = json.loads(json.dumps(skeleton))
    set_paths = []
    for path, value in mapped.items():
        parts = path.split(".")
        node = sk
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        if node.get(parts[-1]) is None:
            node[parts[-1]] = value
            set_paths.append(path)
    flags = sk.setdefault("flags", [])
    fm = FIELD_MAPS[county]
    note = ("auto-filled from the {} ArcGIS layer ({}) — verify against the SOR "
            "card{}".format(county, ", ".join(set_paths) or "nothing",
                            "" if fm["verified"] else "; FIELD MAP UNVERIFIED"))
    if note not in flags:
        flags.append(note)
    return sk, set_paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build C — ArcGIS parcel auto-pull (stretch)")
    ap.add_argument("address")
    ap.add_argument("--county", required=True)
    ap.add_argument("--skeleton", required=True, help="subject.skeleton.json to fill")
    ap.add_argument("--out", help="output path (default: overwrite the skeleton)")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args(argv)
    try:
        data = query_layer(args.county, args.address, timeout=args.timeout)
        mapped, missing = map_features(args.county, data)
        with open(args.skeleton, "r", encoding="utf-8-sig") as fh:
            skeleton = json.load(fh)
        sk, set_paths = apply_to_skeleton(skeleton, mapped, args.county)
        out = args.out or args.skeleton
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(sk, fh, indent=2, ensure_ascii=False)
        print("Auto-filled {} field(s): {}".format(len(set_paths), ", ".join(set_paths)))
        if missing:
            print("Not present on the layer (pull manually): " + ", ".join(missing))
        if not FIELD_MAPS[args.county]["verified"]:
            print("NOTE: field map UNVERIFIED — confirm values against the SOR "
                  "card and flip 'verified' in FIELD_MAPS.")
        print("Continue with the pull sheet for everything else, then ingest_subject.py.")
        return 0
    except FetchError as e:
        sys.stderr.write("ARCGIS FALLBACK: {}\n".format(e))
        sys.stderr.write("Nothing was written — continue with the manual pull sheet.\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
