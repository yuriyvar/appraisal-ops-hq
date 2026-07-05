#!/usr/bin/env python3
"""
BD4 — `appraisal-data` MCP server: the VDV pipeline as callable tools.

Every tool returns text that ends in a NEXT step — the agent calling tools
instead of improvising IS the guardrail (roadmap Track 4). Stdlib only.

Wrapping policy (brief, constraint 1):
  * print-heavy CLIs -> subprocess (their stdout must never touch OUR stdout,
    which carries the MCP protocol) — resolve/ingest/cache/arcgis/add_county.
  * pure functions -> direct import — gas_lookup / county routing / comp history.

The cache WRITE path stays ingest-only: there is deliberately no cache-put tool.

Run (registered via .mcp.json at the VDV Appraisals root):
    python mcp/appraisal-data/server.py
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools", "subject-resolution"))
sys.path.insert(0, os.path.join(REPO, "tools", "comp-history"))

from mcp_stdio import ToolError, serve
import resolve_subject as _rs
import comp_history as _ch

PY = sys.executable


def _run(script_parts, args, ok_codes=(0,), timeout=120):
    """Run a pipeline CLI in a subprocess; capture EVERYTHING. Exit codes in
    ok_codes return text; anything else raises ToolError (isError=true) with
    the full output so the caller sees exactly what the tool saw."""
    cmd = [PY, os.path.join(REPO, *script_parts)] + [str(a) for a in args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ToolError("timed out after {}s: {}".format(timeout, " ".join(cmd[1:])))
    out = (p.stdout or "").strip()
    if (p.stderr or "").strip():
        out += "\n[stderr] " + p.stderr.strip()
    out = "[exit {}] ".format(p.returncode) + out
    if p.returncode not in ok_codes:
        raise ToolError(out)
    return out


def _opt(args, flag, key):
    return [flag, str(args[key])] if args.get(key) not in (None, "") else []


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------
def h_resolve(a):
    if not a.get("address") or not a.get("out_dir"):
        raise ToolError("address and out_dir are required (out_dir = the order "
                        "folder in the client zone)")
    cli = [a["address"], "--out-dir", a["out_dir"]]
    for flag, key in (("--county", "county"), ("--order-id", "order_id"),
                      ("--form-type", "form_type"), ("--client", "client"),
                      ("--effective-date", "effective_date"), ("--as-of", "as_of"),
                      ("--db", "cache_db"), ("--history-db", "history_db")):
        cli += _opt(a, flag, key)
    out = _run(("tools", "subject-resolution", "resolve_subject.py"), cli)
    return out + "\nNEXT: HIT -> re-verify flags, pull comps. MISS -> work " \
                 "pull-sheet.md (MLS -> SOR -> Zillow -> gas), then ingest_subject."


def h_ingest(a):
    if not a.get("raw_path"):
        raise ToolError("raw_path (the filled skeleton) is required")
    cli = [a["raw_path"]]
    for flag, key in (("--out", "out"), ("--source", "source"),
                      ("--resolved-on", "resolved_on"), ("--as-of", "as_of"),
                      ("--db", "cache_db")):
        cli += _opt(a, flag, key)
    out = _run(("tools", "subject-resolution", "ingest_subject.py"), cli)
    return out + "\nNEXT: pull comps per property-search, then assemble_record + render."


def h_cache_lookup(a):
    if not a.get("address"):
        raise ToolError("address is required")
    cli = ["get", a["address"]] + _opt(a, "--as-of", "as_of") + _opt(a, "--db", "cache_db")
    out = _run(("tools", "subject-resolution", "subject_cache.py"), cli, ok_codes=(0, 1))
    nxt = ("NEXT: MISS -> run resolve_subject for the pull sheet."
           if out.startswith("[exit 1]") else
           "NEXT: cached subject available — resolve_subject writes it + staleness flags.")
    return out + "\n" + nxt


def h_gas(a):
    county = a.get("county")
    if not county:
        raise ToolError("county is required")
    routing = _rs.load_routing()
    try:
        name, entry = _rs.find_county(routing, county, "")
    except ValueError as e:
        raise ToolError(str(e))
    gas = _rs.gas_lookup(entry.get("gas_key", name))
    if gas is None:
        raise ToolError("va-gas-providers.sqlite not found — query manually per the registry")
    if not gas:
        return ("{}: NO provider row — NOT YET LOOKED UP -> gas unknown, confirm at "
                "inspection; consider adding the county to the gas DB.\n"
                "NEXT: record Gas: unknown on the worksheet.".format(name))
    lines = []
    for p in gas:
        if p["method"] == "confirmed_absent":
            lines.append("{}: CONFIRMED no SCC gas -> heating is NOT gas "
                         "(heat pump/electric/propane; confirm at inspection).".format(name))
        else:
            lines.append("{}: {} ({}) {} {}".format(
                name, p["provider"], p["method"], p["url"] or "", p["phone"] or "").strip())
            if p["notes"]:
                lines.append("  notes: " + p["notes"])
    if len([p for p in gas if p["method"] != "confirmed_absent"]) > 1:
        lines.append("OVERLAP county — two providers; present both.")
    return "\n".join(lines) + "\nNEXT: record Gas: Connected / Available-not-connected / Not available."


def h_route(a):
    county = a.get("county")
    if not county:
        raise ToolError("county is required")
    routing = _rs.load_routing()
    try:
        name, entry = _rs.find_county(routing, county, "")
    except ValueError as e:
        raise ToolError(str(e) + "\nNEXT: add it via the add_county tool (registry + "
                                 "routing together), then retry.")
    return ("{}: {}\nNEXT: resolve_subject handles this automatically — use this "
            "tool only to inspect routing.".format(name, json.dumps(entry, ensure_ascii=False)))


def h_history(a):
    if not a.get("address"):
        raise ToolError("address is required")
    hits = _ch.search(a["address"], zip_code=a.get("zip"), county=a.get("county"),
                      gla=a.get("gla"), as_of=a.get("as_of"),
                      db_path=a.get("history_db"))
    return (_ch.format_hits(hits)
            + "NEXT: candidates only — YV decides; open the DM file for the comp grid; "
              "re-verify close dates in the MLS.")


def h_arcgis(a):
    for k in ("address", "county", "skeleton"):
        if not a.get(k):
            raise ToolError("address, county and skeleton are required")
    cli = [a["address"], "--county", a["county"], "--skeleton", a["skeleton"]]
    out = _run(("tools", "subject-resolution", "fetch_arcgis.py"), cli, timeout=45)
    return out + "\nNEXT: continue the pull sheet for everything else; field map is " \
                 "UNVERIFIED until a live pull confirms attribute names."


def h_add_county(a):
    req = ("jurisdiction", "vendor", "sor_url", "technique", "mls")
    missing = [k for k in req if not a.get(k)]
    if missing:
        raise ToolError("required: " + ", ".join(missing))
    cli = ["--jurisdiction", a["jurisdiction"], "--vendor", a["vendor"],
           "--sor-url", a["sor_url"], "--technique", a["technique"]]
    for m in (a["mls"] if isinstance(a["mls"], list) else [a["mls"]]):
        cli += ["--mls", m]
    for flag, key in (("--gas-key", "gas_key"), ("--aliases", "aliases"),
                      ("--comp-source", "comp_source"), ("--sales-gis", "sales_gis"),
                      ("--quirks", "quirks"), ("--surrounding", "surrounding")):
        cli += _opt(a, flag, key)
    out = _run(("tools", "subject-resolution", "add_county.py"), cli)
    return out + "\nNEXT: COMMIT registry + routing together (drift rule); live-verify " \
                 "the SOR URL on the first order."


# ---------------------------------------------------------------------------
# tool table (schemas hand-written; strings unless noted)
# ---------------------------------------------------------------------------
def _schema(props, required):
    return {"type": "object", "properties": props, "required": required}

S = {"type": "string"}
TOOLS = {
    "resolve_subject": {
        "description": "START EVERY ORDER HERE. Cache-first subject resolution: HIT -> "
                       "subject.json + staleness flags; MISS -> v1.1 skeleton + pull-sheet.md "
                       "+ run-log.md, with prior-work recall either way. out_dir = the order "
                       "folder (client zone; repo paths refuse).",
        "inputSchema": _schema({"address": S, "out_dir": S, "county": S, "order_id": S,
                                "form_type": S, "client": S, "effective_date": S,
                                "as_of": S, "cache_db": S, "history_db": S},
                               ["address", "out_dir"]),
        "handler": h_resolve},
    "ingest_subject": {
        "description": "Normalize + gate a filled subject skeleton -> subject.json, and cache "
                       "it (THE only cache write path). Fires the fail-loud gates (GLA, lot "
                       "mismatch, tax year, variance protocol) and ticks the run-log.",
        "inputSchema": _schema({"raw_path": S, "out": S, "source": S, "resolved_on": S,
                                "as_of": S, "cache_db": S}, ["raw_path"]),
        "handler": h_ingest},
    "cache_lookup": {
        "description": "READ-ONLY subject-cache check (HIT with age + staleness flags, or "
                       "MISS). Writes nothing.",
        "inputSchema": _schema({"address": S, "as_of": S, "cache_db": S}, ["address"]),
        "handler": h_cache_lookup},
    "gas_lookup": {
        "description": "Gas provider + lookup method for a jurisdiction (va-gas-providers "
                       "DB; distinguishes CONFIRMED-absent from not-yet-looked-up).",
        "inputSchema": _schema({"county": S}, ["county"]),
        "handler": h_gas},
    "county_route": {
        "description": "Inspect a county's routing entry (SOR vendor/URL/technique, MLS, "
                       "quirks, surrounding counties). Unknown county lists coverage.",
        "inputSchema": _schema({"county": S}, ["county"]),
        "handler": h_route},
    "comp_history_search": {
        "description": "Prior VDV work recall: same property any-date + similar (zip + GLA "
                       "band) within 12 months. CANDIDATES for YV only.",
        "inputSchema": _schema({"address": S, "zip": S, "county": S,
                                "gla": {"type": "number"}, "as_of": S, "history_db": S},
                               ["address"]),
        "handler": h_history},
    "arcgis_fetch": {
        "description": "Chesterfield/Hanover ONLY: auto-fill parcel basics from the county "
                       "FeatureServer into a skeleton (fill-nulls-only; UNVERIFIED field "
                       "maps; any failure = clean fallback to the pull sheet).",
        "inputSchema": _schema({"address": S, "county": S, "skeleton": S},
                               ["address", "county", "skeleton"]),
        "handler": h_arcgis},
    "add_county": {
        "description": "Add a NEW jurisdiction to the county registry AND the routing table "
                       "together (all-or-nothing; duplicates refused). mls may be a list.",
        "inputSchema": _schema({"jurisdiction": S, "vendor": S, "sor_url": S,
                                "technique": S, "mls": {}, "gas_key": S, "aliases": S,
                                "comp_source": S, "sales_gis": S, "quirks": S,
                                "surrounding": S},
                               ["jurisdiction", "vendor", "sor_url", "technique", "mls"]),
        "handler": h_add_county},
}


if __name__ == "__main__":
    serve(TOOLS)
