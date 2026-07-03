#!/usr/bin/env python3
"""
BD1 — new-county intake (Phase 3).

Adds a jurisdiction to BOTH routing surfaces in one all-or-nothing run:
  * skills/property-search/references/county-registry.md  (Extended-coverage table row)
  * tools/subject-resolution/county_routing.json          (resolver entry)

The same-commit drift rule stops being something to remember — this script IS
the rule. It refuses partial adds: both files must exist and be writable, and
the jurisdiction must be new to both, or NOTHING is written.

Usage:
    python add_county.py --jurisdiction "Halifax" --vendor "qPublic" \
        --sor-url "https://qpublic.schneidercorp.com/..." \
        --technique "address search; tax card on parcel page" \
        --mls "CVR-Matrix" --mls "Navica" \
        [--gas-key "Halifax County"] [--aliases "Halifax County,Halifax Co"] \
        [--comp-source MLS-only] [--sales-gis N] [--quirks "..."] \
        [--surrounding "Mecklenburg,Charlotte"] \
        [--registry PATH --routing PATH]   (test overrides)

After it runs: live-verify the URL on the next order, and COMMIT BOTH FILES TOGETHER.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_REGISTRY = os.path.join(REPO, "skills", "property-search", "references",
                                "county-registry.md")
DEFAULT_ROUTING = os.path.join(HERE, "county_routing.json")

EXTENDED_HEADER = "## Extended coverage (added as orders arrive)"


def add_county(jurisdiction, vendor, sor_url, technique, mls,
               gas_key=None, aliases=None, comp_source="MLS-only",
               sales_gis="N", quirks="", surrounding=None,
               registry_path=None, routing_path=None, verified_note="added via add_county.py — live-verify on first order"):
    registry_path = registry_path or DEFAULT_REGISTRY
    routing_path = routing_path or DEFAULT_ROUTING
    aliases = aliases or ["{} County".format(jurisdiction), "{} Co".format(jurisdiction)]
    gas_key = gas_key or "{} County".format(jurisdiction)
    surrounding = surrounding or []

    # ---- read + validate BOTH before touching EITHER (all-or-nothing) ----
    for p in (registry_path, routing_path):
        if not os.path.isfile(p):
            raise ValueError("missing file — refusing a partial add: " + p)
    with open(registry_path, "r", encoding="utf-8-sig") as fh:
        reg = fh.read()
    with open(routing_path, "r", encoding="utf-8-sig") as fh:
        routing_doc = json.load(fh)
    jur = routing_doc.get("jurisdictions", {})

    if jurisdiction in jur:
        raise ValueError("{!r} already in county_routing.json — edit it there "
                         "(and the registry) instead of re-adding".format(jurisdiction))
    # duplicate = an existing TABLE ROW for the jurisdiction (a mention inside
    # another county's surrounding-set or notes is fine)
    import re
    if re.search(r"^\|\s*{}\s*\|".format(re.escape(jurisdiction)), reg,
                 re.MULTILINE | re.IGNORECASE):
        raise ValueError("{!r} already has a coverage row in county-registry.md — "
                         "reconcile manually; refusing a duplicate".format(jurisdiction))
    if EXTENDED_HEADER not in reg:
        raise ValueError("registry is missing the Extended-coverage section header — "
                         "file layout changed; update add_county.py")

    # ---- build both changes in memory ----
    row = ("| {j} | {v} ({u}) | {g} | {c} | {m} | {q} {note} |".format(
        j=jurisdiction, v=vendor, u=sor_url, g=sales_gis, c=comp_source,
        m=" / ".join(mls), q=(quirks + " ") if quirks else "",
        note="[" + verified_note + "]"))
    # append the row right after the Extended-coverage table's header rows
    lines = reg.splitlines()
    idx = None
    in_section = False
    for i, ln in enumerate(lines):
        if ln.strip() == EXTENDED_HEADER:
            in_section = True
            continue
        if in_section and ln.startswith("|"):
            idx = i          # last table line inside the section
        elif in_section and idx is not None and not ln.startswith("|"):
            break
    if idx is None:
        raise ValueError("could not locate the Extended-coverage table — update add_county.py")
    lines.insert(idx + 1, row)
    new_reg = "\n".join(lines) + ("\n" if reg.endswith("\n") else "")

    jur[jurisdiction] = {
        "aliases": aliases,
        "gas_key": gas_key,
        "vendor": vendor,
        "sor_url": sor_url,
        "technique": technique,
        "sales_gis": sales_gis,
        "comp_source": comp_source,
        "mls": list(mls),
        "surrounding_counties": list(surrounding),
        "quirks": (quirks + (" " if quirks else "") + "[" + verified_note + "]").strip(),
    }

    # ---- write BOTH (registry first; roll it back if the JSON write fails) ----
    with open(registry_path, "w", encoding="utf-8") as fh:
        fh.write(new_reg)
    try:
        with open(routing_path, "w", encoding="utf-8") as fh:
            json.dump(routing_doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    except Exception:
        with open(registry_path, "w", encoding="utf-8") as fh:
            fh.write(reg)    # roll back — never leave the two files split
        raise
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description="BD1 — add a county to registry + routing together")
    ap.add_argument("--jurisdiction", required=True)
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--sor-url", required=True)
    ap.add_argument("--technique", required=True)
    ap.add_argument("--mls", action="append", required=True,
                    help="repeatable: --mls CVR-Matrix --mls Navica")
    ap.add_argument("--gas-key")
    ap.add_argument("--aliases", help="comma-separated")
    ap.add_argument("--comp-source", default="MLS-only")
    ap.add_argument("--sales-gis", default="N")
    ap.add_argument("--quirks", default="")
    ap.add_argument("--surrounding", help="comma-separated surrounding counties")
    ap.add_argument("--registry", help="registry path override (tests)")
    ap.add_argument("--routing", help="routing path override (tests)")
    args = ap.parse_args(argv)
    try:
        row = add_county(
            args.jurisdiction, args.vendor, args.sor_url, args.technique, args.mls,
            gas_key=args.gas_key,
            aliases=[a.strip() for a in args.aliases.split(",")] if args.aliases else None,
            comp_source=args.comp_source, sales_gis=args.sales_gis,
            quirks=args.quirks,
            surrounding=[s.strip() for s in args.surrounding.split(",")] if args.surrounding else None,
            registry_path=args.registry, routing_path=args.routing)
    except ValueError as e:
        sys.stderr.write("REFUSED: {}\n".format(e))
        return 2
    print("Added to BOTH files:")
    print("  " + row)
    print("NOW: commit county-registry.md + county_routing.json TOGETHER (drift rule),")
    print("     live-verify the SOR URL on the first real order, and check the gas DB")
    print("     has a row for '{}' (build_va_gas_providers.py if not).".format(
        args.gas_key or args.jurisdiction + " County"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
