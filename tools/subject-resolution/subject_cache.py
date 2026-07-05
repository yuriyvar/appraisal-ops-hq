#!/usr/bin/env python3
"""
Build C — subject-resolution cache (Phase 1).

SQLite cache of resolved subjects so repeat orders / repeat lookups never redo
the county-portal pull. Stdlib only.

Design rules (Build C brief 2026-07-02):
  * The DB lives in the CLIENT zone (default below) — NEVER inside the repo.
    A repo-resident path raises. Repo holds code + synthetic tests only.
  * Staleness is a FLAG, not a filter: get() always returns the hit with its
    age; staleness_flags() produces the warnings the resolver attaches
    (fail loud, never silently reuse stale data — CLAUDE.md rule 7).
  * Deterministic where testable: age is computed against an explicit as_of
    date (defaults to today only at the CLI edge).

Usage:
    python subject_cache.py get  "119 Example Ridge Ln, Henrico, VA 23229"
    python subject_cache.py put  "<address>" --file subject.json --source "county-assessment 2026-07-02"
    python subject_cache.py list
    python subject_cache.py delete "<address>"
Common flags: --db PATH (default: client zone / $env:VDV_SUBJECT_CACHE),
              --as-of YYYY-MM-DD, --ttl-days N (default 180).
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime

DEFAULT_DB = r"C:\Users\yuriy\VDV Appraisals\Subject cache\subject-cache.sqlite"
DEFAULT_TTL_DAYS = 180

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))

# ---------------------------------------------------------------------------
# address normalization -> cache key
# ---------------------------------------------------------------------------
_SUFFIX = {
    "STREET": "ST", "ROAD": "RD", "LANE": "LN", "DRIVE": "DR", "COURT": "CT",
    "CIRCLE": "CIR", "AVENUE": "AVE", "PLACE": "PL", "TERRACE": "TER",
    "HIGHWAY": "HWY", "PARKWAY": "PKWY", "BOULEVARD": "BLVD", "TRAIL": "TRL",
    "CROSSING": "XING", "SQUARE": "SQ", "POINT": "PT",
}
_DIRECTIONAL = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
}
# trailing unit designators on the street segment ("Apt 4B", "# 2", "Suite 200").
# NOTE: '#' sits outside the \b group — no word boundary exists before a non-word char.
_UNIT_RE = re.compile(r"(?:\b(?:APT|UNIT|SUITE|STE|BLDG|RM)|#)\s*[\w-]*\s*$", re.IGNORECASE)
_ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


def _canon_street(seg):
    s = seg.upper().strip()
    s = _UNIT_RE.sub("", s)
    s = re.sub(r"[^\w\s]", " ", s)          # punctuation -> space
    tokens = []
    for t in s.split():
        tokens.append(_DIRECTIONAL.get(t) or _SUFFIX.get(t) or t)
    return " ".join(tokens)


def _canon_city(seg):
    s = seg.upper().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+(COUNTY|CITY|CO)$", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def normalize_address(raw):
    """Canonical cache key. ZIP is the stable second slot when present (city vs
    county wording then can't split the key); street-only inputs still key."""
    if raw is None or not str(raw).strip():
        raise ValueError("empty address")
    s = str(raw).strip()
    parts = [p.strip() for p in s.split(",") if p.strip()]
    # ZIP only from the LAST segment — a 5-digit HOUSE NUMBER in a zip-less
    # address must never masquerade as the zip slot (live bug: "14719 Clover
    # Ridge Ln, Chesterfield, VA" keyed as ...|14719).
    zipc = ""
    if len(parts) >= 2:
        zips = _ZIP_RE.findall(parts[-1])
        zipc = zips[-1] if zips else ""
    street = _canon_street(parts[0])
    if not street:
        raise ValueError("no street segment in address: {!r}".format(raw))
    if zipc:
        return street + "|" + zipc
    city = _canon_city(parts[1]) if len(parts) >= 2 else ""
    return street + "|" + city


# ---------------------------------------------------------------------------
# db plumbing
# ---------------------------------------------------------------------------
def _resolve_db_path(db_path):
    p = db_path or os.environ.get("VDV_SUBJECT_CACHE") or DEFAULT_DB
    ap = os.path.abspath(p)
    if ap == _REPO or ap.startswith(_REPO + os.sep):
        raise ValueError(
            "cache DB must live in the client zone, NEVER in the repo: " + ap)
    return ap


def _connect(db_path=None):
    ap = _resolve_db_path(db_path)
    d = os.path.dirname(ap)
    if d:
        os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(ap)
    con.execute("""CREATE TABLE IF NOT EXISTS subjects(
        key          TEXT PRIMARY KEY,
        address_full TEXT,
        county       TEXT,
        subject_json TEXT NOT NULL,
        resolved_on  TEXT NOT NULL,
        source       TEXT,
        put_at       TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT OR IGNORE INTO meta(k, v) VALUES('schema_version','1')")
    return con


def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _age_days(resolved_on, as_of=None):
    r = _parse_date(resolved_on)
    a = _parse_date(as_of) or date.today()
    if r is None:
        return None
    return (a - r).days


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def get(addr, db_path=None, as_of=None):
    """Cache lookup. Returns (subject_dict, resolved_on, age_days) or None.
    Never filters on staleness — callers attach staleness_flags()."""
    key = normalize_address(addr)
    con = _connect(db_path)
    try:
        row = con.execute(
            "SELECT subject_json, resolved_on FROM subjects WHERE key=?",
            (key,)).fetchone()
    finally:
        con.close()
    if not row:
        return None
    return json.loads(row[0]), row[1], _age_days(row[1], as_of)


def put(addr, subject, source, db_path=None, resolved_on=None, put_at=None):
    """Store a VALIDATED subject dict. resolved_on comes from the subject's
    resolution block unless passed explicitly; missing on both -> error
    (fail loud — an undated cache entry can never be staleness-checked)."""
    if not isinstance(subject, dict):
        raise ValueError("subject must be a dict")
    key = normalize_address(addr)
    resolved_on = resolved_on or ((subject.get("resolution") or {}).get("resolved_on"))
    if not _parse_date(resolved_on):
        raise ValueError("resolved_on required (ISO date) — set it in "
                         "subject.resolution.resolved_on or pass explicitly")
    county = ((subject.get("address") or {}).get("county"))
    full = ((subject.get("address") or {}).get("full")) or str(addr)
    put_at = put_at or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    con = _connect(db_path)
    try:
        con.execute(
            "INSERT OR REPLACE INTO subjects"
            "(key, address_full, county, subject_json, resolved_on, source, put_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (key, full, county,
             json.dumps(subject, sort_keys=True, ensure_ascii=False),
             str(resolved_on)[:10], source, put_at))
        con.commit()
    finally:
        con.close()
    return key


def delete(addr, db_path=None):
    key = normalize_address(addr)
    con = _connect(db_path)
    try:
        cur = con.execute("DELETE FROM subjects WHERE key=?", (key,))
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def list_entries(db_path=None):
    con = _connect(db_path)
    try:
        rows = con.execute(
            "SELECT key, address_full, county, resolved_on, source "
            "FROM subjects ORDER BY key").fetchall()
    finally:
        con.close()
    return rows


def backfill(scan_dir, db_path=None):
    """Cowork-lane bridge (Ton's andon 2026-07-04): the Cowork SANDBOX cannot
    write SQLite over its mounted volumes (advisory-lock failure on
    CREATE/INSERT; reads + plain files are fine), so Cowork ingests with
    --no-cache and the HOST sweeps validated subject.json files in here.
    Only files with a resolution stamp qualify (same rule as ingest — junk
    never enters the cache); undated ones are LISTED, never guessed."""
    put_n = current_n = 0
    undated = []
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in
                   (".git", "appraisal-ops-hq", "Subject cache", "__pycache__",
                    "node_modules", "OneDrive")]
        if "subject.json" not in files:
            continue
        p = os.path.join(root, "subject.json")
        try:
            with open(p, "r", encoding="utf-8-sig") as fh:
                subj = json.load(fh)
        except (ValueError, OSError):
            undated.append(p + "  (unreadable/unparseable)")
            continue
        addr = ((subj.get("address") or {}).get("full"))
        resolved_on = ((subj.get("resolution") or {}).get("resolved_on"))
        if not addr or not _parse_date(resolved_on):
            undated.append(p)
            continue
        hit = get(addr, db_path=db_path)
        if hit and str(hit[1]) >= str(resolved_on)[:10]:
            current_n += 1
            continue
        put(addr, subj, "backfill:" + p, db_path=db_path)
        put_n += 1
    return {"put": put_n, "already_current": current_n,
            "skipped_undated": len(undated), "undated_list": undated}


def staleness_flags(subject, resolved_on, as_of=None, ttl_days=DEFAULT_TTL_DAYS):
    """Warnings the resolver must attach to a cache hit. Flag, never hide."""
    flags = []
    age = _age_days(resolved_on, as_of)
    if age is not None and age > ttl_days:
        flags.append("cached subject data {} days old — re-verify assessment / "
                     "tax year before use".format(age))
    as_of_d = _parse_date(as_of) or date.today()
    tax_year = ((subject.get("assessment") or {}).get("tax_year"))
    if tax_year and as_of_d.year > tax_year:
        flags.append("cached assessment tax year {} is behind {} — re-verify"
                     .format(tax_year, as_of_d.year))
    return flags


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Build C — subject cache")
    ap.add_argument("action", choices=["get", "put", "list", "delete", "backfill"])
    ap.add_argument("address", nargs="?",
                    help="subject address (for backfill: the folder to scan)")
    ap.add_argument("--db", help="cache DB path (default: client zone)")
    ap.add_argument("--as-of", help="date for age math (YYYY-MM-DD; default today)")
    ap.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS)
    ap.add_argument("--file", help="put: subject.json to store")
    ap.add_argument("--source", help="put: provenance note")
    ap.add_argument("--resolved-on", help="put: override resolution date")
    args = ap.parse_args(argv)

    if args.action == "list":
        for r in list_entries(args.db):
            print(" | ".join(str(x) if x is not None else "-" for x in r))
        return 0

    if not args.address:
        ap.error("address required for get/put/delete (scan folder for backfill)")

    if args.action == "backfill":
        s = backfill(args.address, db_path=args.db)
        print("backfill: {} put, {} already current, {} skipped (no resolution stamp)"
              .format(s["put"], s["already_current"], s["skipped_undated"]))
        for u in s["undated_list"]:
            print("SKIPPED  " + u)
        return 0

    if args.action == "get":
        hit = get(args.address, args.db, args.as_of)
        if hit is None:
            print("MISS  key={}".format(normalize_address(args.address)))
            return 1
        subject, resolved_on, age = hit
        print("HIT   key={} resolved_on={} age_days={}".format(
            normalize_address(args.address), resolved_on, age))
        for f in staleness_flags(subject, resolved_on, args.as_of, args.ttl_days):
            print("FLAG  " + f)
        print(json.dumps(subject, indent=2, ensure_ascii=False))
        return 0

    if args.action == "put":
        if not args.file or not args.source:
            ap.error("put requires --file and --source")
        with open(args.file, "r", encoding="utf-8-sig") as fh:
            subject = json.load(fh)
        key = put(args.address, subject, args.source, args.db,
                  resolved_on=args.resolved_on)
        print("PUT   key=" + key)
        return 0

    if args.action == "delete":
        n = delete(args.address, args.db)
        print("DELETED {} row(s)".format(n))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
