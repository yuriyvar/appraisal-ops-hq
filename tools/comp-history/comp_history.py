#!/usr/bin/env python3
"""
BD3 — historical comp recall: build + search the comp-history index.

Sources (all READ-ONLY):
  * Ops-sheet CSV exports (2025/2026 tabs; positional layout — a data row has a
    M/D/YYYY date in col 0 and a street in col 3)
  * the June-2026 corpus extraction (corpus_values_raw.json — subject facts +
    a flattened comp HINT per .dma; see quirk DMA-004 for why hints, not rows)
  * the DataMaster folder itself (filename = subject street; mtime = the
    APPROXIMATE report date when no Ops row matches)

Index lives in the CLIENT zone (repo paths raise). PII (owner/seller/lender
names) is never indexed. Recall results are CANDIDATES for YV — never
auto-selected; comp close dates must be re-verified in the MLS.

Usage:
    python comp_history.py build [--ops-csv PATH ...] [--corpus PATH]
                                 [--dma-dir PATH] [--db PATH]
    python comp_history.py search "<address>" [--zip Z] [--county C]
                                 [--gla N] [--as-of YYYY-MM-DD] [--db PATH]
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "subject-resolution"))
from subject_cache import _canon_street   # one canon for the whole pipeline

CLIENT = r"C:\Users\yuriy\VDV Appraisals"
DEFAULT_DB = os.path.join(CLIENT, "Past Reports", "_analysis", "comp-history.sqlite")
DEFAULT_CORPUS = os.path.join(CLIENT, "Past Reports", "_analysis", "_dma-decode",
                              "corpus_values_raw.json")
DEFAULT_DMA_DIR = r"C:\Users\yuriy\OneDrive\Documents\DataMaster"
DEFAULT_OPS = [os.path.join(CLIENT, "Past Reports", "_analysis", "ops-history", f)
               for f in ("ops-2025.csv", "ops-2026.csv")]

# corpus keys that are PII — never copied into the index
_PII_KEYS = ("OWNER", "SELLER", "Lender", "BORROWER")


def street_key(s):
    """Squashed join key: '117 S Main STREET' == '117S_MainSt' == '117 s main st.'
    Canonicalizes suffixes/directionals (subject_cache), then strips everything
    but alphanumerics — tolerant of the .dma filenames' missing spaces."""
    return re.sub(r"[^0-9a-z]", "", _canon_street(str(s or "")).lower())


def _parse_mdy(s):
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(s or "").strip())
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat()
    except ValueError:
        return None


def _money(s):
    v = re.sub(r"[$,\s]", "", str(s or ""))
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _resolve_db(db_path):
    ap = os.path.abspath(db_path or DEFAULT_DB)
    if ap == REPO or ap.startswith(REPO + os.sep):
        raise ValueError("comp-history DB must live in the client zone, "
                         "never the repo: " + ap)
    return ap


def _connect(db_path=None):
    ap = _resolve_db(db_path)
    d = os.path.dirname(ap)
    if d:
        os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(ap)
    con.row_factory = sqlite3.Row
    return con


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def parse_ops_csv(path, year_hint=""):
    """Positional Ops-tab layout: 0 order-date · 1 order# · 2 client · 3 street ·
    4 zip · 5 report type · 6 due/done date · 10 appraised value · 11 status."""
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for cols in csv.reader(fh):
            if len(cols) < 12:
                continue
            odate = _parse_mdy(cols[0])
            street = (cols[3] or "").strip()
            if not odate or not street:
                continue    # summary/header rows
            rows.append({
                "street": street, "street_key": street_key(street),
                "zip": (cols[4] or "").strip() or None,
                "order_no": (cols[1] or "").strip() or None,
                "client": (cols[2] or "").strip() or None,
                "form_type": (cols[5] or "").strip() or None,
                "report_date": _parse_mdy(cols[6]) or odate,
                "order_date": odate,
                "appraised_value": _money(cols[10]),
                "status": (cols[11] or "").strip() or None,
            })
    return rows


def load_corpus_facts(corpus_path):
    """corpus_values_raw.json -> {street_key: facts} (subject card + comp hint).
    PII keys are never read into the result."""
    with open(corpus_path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    facts = {}
    for fname, e in (data.get("files") or {}).items():
        if not isinstance(e, dict):
            continue
        key = street_key(fname[:-4] if fname.lower().endswith(".dma") else fname)
        hint_bits = []
        for col in ("Address", "Sales Price", "Total Finished Area", "Status"):
            v = e.get(col)
            if v:
                hint_bits.append("{}: {}".format(col, v))
        facts[key] = {
            "county": e.get("COUNTY"),
            "zip": e.get("PROPERTY_ZIP_CODE"),
            "city": e.get("PROPERTY_CITY_NAME"),
            "gla": _money(e.get("BLDG_ABOVE_GRADE_SQFT") or e.get("BLDG_TOTAL_SQFT")),
            "year_built": int(e["YEAR_BUILT"]) if str(e.get("YEAR_BUILT") or "").isdigit() else None,
            "style": e.get("STYLE"),
            "beds": int(e["BEDROOMS"]) if str(e.get("BEDROOMS") or "").isdigit() else None,
            "apn": e.get("APN"),
            "comp_hint": "; ".join(hint_bits) or None,
        }
    return facts


def scan_dma_dir(dma_dir):
    """{street_key: (filename, mtime-date-iso)} — names + mtimes only; the
    files are NEVER opened here (read-only law + DMA-004)."""
    out = {}
    if not os.path.isdir(dma_dir):
        return out
    for fn in os.listdir(dma_dir):
        if not fn.lower().endswith(".dma"):
            continue
        p = os.path.join(dma_dir, fn)
        try:
            mt = date.fromtimestamp(os.path.getmtime(p)).isoformat()
        except OSError:
            continue
        out[street_key(fn[:-4])] = (fn, mt)
    return out


def build(ops_csvs=None, corpus_path=None, dma_dir=None, db_path=None):
    """Rebuild the index from scratch (idempotent). Returns count summary."""
    ops_csvs = [p for p in (ops_csvs or DEFAULT_OPS) if os.path.isfile(p)]
    skipped_csvs = [p for p in (DEFAULT_OPS if ops_csvs is None else []) if not os.path.isfile(p)]
    corpus_path = corpus_path or DEFAULT_CORPUS
    dma_dir = dma_dir or DEFAULT_DMA_DIR

    ops_rows = []
    for p in ops_csvs:
        ops_rows.extend(parse_ops_csv(p))
    facts = load_corpus_facts(corpus_path) if os.path.isfile(corpus_path) else {}
    dma = scan_dma_dir(dma_dir)

    rows, matched_keys = [], set()
    for r in ops_rows:
        k = r["street_key"]
        f = facts.get(k, {})
        d = dma.get(k)
        rows.append({
            "street_key": k, "street": r["street"],
            "zip": r["zip"] or f.get("zip"),
            "city": f.get("city"), "county": f.get("county"),
            "gla": f.get("gla"), "year_built": f.get("year_built"),
            "style": f.get("style"), "beds": f.get("beds"), "apn": f.get("apn"),
            "report_date": r["report_date"], "date_basis": "ops",
            "form_type": r["form_type"], "status": r["status"],
            "client": r["client"], "appraised_value": r["appraised_value"],
            "order_no": r["order_no"],
            "dma_file": d[0] if d else None,
            "comp_hint": f.get("comp_hint"),
            "sources": "ops" + ("+corpus" if f else "") + ("+dma" if d else ""),
        })
        matched_keys.add(k)

    for k, (fn, mt) in dma.items():
        if k in matched_keys:
            continue
        f = facts.get(k, {})
        rows.append({
            "street_key": k, "street": fn[:-4],
            "zip": f.get("zip"), "city": f.get("city"), "county": f.get("county"),
            "gla": f.get("gla"), "year_built": f.get("year_built"),
            "style": f.get("style"), "beds": f.get("beds"), "apn": f.get("apn"),
            "report_date": mt, "date_basis": "mtime-approx",
            "form_type": None, "status": None, "client": None,
            "appraised_value": None, "order_no": None,
            "dma_file": fn, "comp_hint": f.get("comp_hint"),
            "sources": "dma" + ("+corpus" if f else ""),
        })

    con = _connect(db_path)
    try:
        con.execute("DROP TABLE IF EXISTS history")
        con.execute("""CREATE TABLE history(
            street_key TEXT, street TEXT, zip TEXT, city TEXT, county TEXT,
            gla REAL, year_built INT, style TEXT, beds INT, apn TEXT,
            report_date TEXT, date_basis TEXT, form_type TEXT, status TEXT,
            client TEXT, appraised_value REAL, order_no TEXT,
            dma_file TEXT, comp_hint TEXT, sources TEXT)""")
        con.execute("CREATE INDEX ix_hist_key ON history(street_key)")
        con.execute("CREATE INDEX ix_hist_zip ON history(zip)")
        cols = ["street_key", "street", "zip", "city", "county", "gla",
                "year_built", "style", "beds", "apn", "report_date", "date_basis",
                "form_type", "status", "client", "appraised_value", "order_no",
                "dma_file", "comp_hint", "sources"]
        con.executemany(
            "INSERT INTO history({}) VALUES({})".format(
                ",".join(cols), ",".join("?" * len(cols))),
            [[r[c] for c in cols] for r in rows])
        con.commit()
    finally:
        con.close()
    return {"ops_rows": len(ops_rows), "corpus_facts": len(facts),
            "dma_files": len(dma), "index_rows": len(rows),
            "csvs_used": ops_csvs, "csvs_missing": skipped_csvs}


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------
def search(address, zip_code=None, county=None, gla=None, as_of=None,
           months=12, band=0.15, db_path=None):
    """Recall tiers: 'exact' = same property (any date — its own history matters);
    'similar' = zip match + GLA within ±band, inside the window;
    'weak' = zip (or county) match inside the window, capped. All CANDIDATES."""
    key = street_key(str(address).split(",")[0])
    as_of_d = (datetime.strptime(str(as_of)[:10], "%Y-%m-%d").date()
               if as_of else date.today())
    cutoff = (as_of_d - timedelta(days=int(months * 30.44))).isoformat()

    ap = _resolve_db(db_path)
    if not os.path.isfile(ap):
        return None    # index not built — caller says so loudly
    con = _connect(db_path)
    try:
        exact = [dict(r) for r in con.execute(
            "SELECT * FROM history WHERE street_key=? ORDER BY report_date DESC",
            (key,))]
        similar, weak = [], []
        if zip_code or county:
            if zip_code:
                cand = con.execute(
                    "SELECT * FROM history WHERE zip=? AND street_key<>? "
                    "AND report_date>=? ORDER BY report_date DESC",
                    (str(zip_code), key, cutoff)).fetchall()
            else:
                cand = con.execute(
                    "SELECT * FROM history WHERE county=? AND street_key<>? "
                    "AND report_date>=? ORDER BY report_date DESC",
                    (str(county), key, cutoff)).fetchall()
            for r in cand:
                r = dict(r)
                if gla and r.get("gla"):
                    if abs(r["gla"] - gla) / gla <= band:
                        similar.append(r)
                else:
                    weak.append(r)
        return {"exact": exact, "similar": similar, "weak": weak[:5],
                "cutoff": cutoff}
    finally:
        con.close()


def format_hits(hits, months=12):
    """Human block for the pull sheet / stdout. hits=None -> not-built notice."""
    L = ["## Prior work (comp-history index)"]
    if hits is None:
        L.append("- index not built — `python tools/comp-history/comp_history.py build`")
        return "\n".join(L) + "\n"

    def line(r):
        d = r["report_date"] or "?"
        basis = " ~approx" if r["date_basis"] == "mtime-approx" else ""
        bits = [r["street"], d + basis]
        if r.get("form_type"):
            bits.append(r["form_type"])
        if r.get("gla"):
            bits.append("{:,.0f} sf".format(r["gla"]))
        if r.get("status"):
            bits.append(r["status"])
        if r.get("dma_file"):
            bits.append("DM: " + r["dma_file"])
        return "- " + " · ".join(bits)

    if hits["exact"]:
        L.append("**SAME PROPERTY appraised before:**")
        L.extend(line(r) for r in hits["exact"][:5])
    if hits["similar"]:
        L.append("**Similar within {} mo (zip + GLA band):**".format(months))
        L.extend(line(r) for r in hits["similar"][:5])
        for r in hits["similar"][:5]:
            if r.get("comp_hint"):
                L.append("    hint: " + r["comp_hint"])
    if hits["weak"]:
        L.append("Weak matches (same area, GLA unknown): " +
                 "; ".join(r["street"] for r in hits["weak"]))
    if not (hits["exact"] or hits["similar"] or hits["weak"]):
        L.append("- none found (window from {}).".format(hits["cutoff"]))
    else:
        L.append("CANDIDATES ONLY - YV decides. Open the DM file for the full comp")
        L.append("grid; re-verify every comp's close date in the MLS (12-mo rule).")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="BD3 — comp-history index")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--ops-csv", action="append")
    b.add_argument("--corpus")
    b.add_argument("--dma-dir")
    b.add_argument("--db")
    s = sub.add_parser("search")
    s.add_argument("address")
    s.add_argument("--zip")
    s.add_argument("--county")
    s.add_argument("--gla", type=float)
    s.add_argument("--as-of")
    s.add_argument("--db")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "build":
            summary = build(args.ops_csv, args.corpus, args.dma_dir, args.db)
            for k, v in summary.items():
                print("{}: {}".format(k, v))
            return 0
        hits = search(args.address, zip_code=args.zip, county=args.county,
                      gla=args.gla, as_of=args.as_of, db_path=args.db)
        print(format_hits(hits))
        return 0
    except ValueError as e:
        sys.stderr.write("ERROR: {}\n".format(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
