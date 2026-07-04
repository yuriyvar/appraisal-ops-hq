#!/usr/bin/env python3
"""BD3 QA runner — comp-history index (synthetic fixtures only; no client data)."""

import csv
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from comp_history import (street_key, parse_ops_csv, load_corpus_facts,
                          scan_dma_dir, build, search, format_hits, _resolve_db)

results = []


def ok(name):
    results.append(("PASS", name))
    print("PASS  " + name)


def fail(name, reason):
    results.append(("FAIL", name, reason))
    print("FAIL  {} | {}".format(name, reason))


TMP = tempfile.mkdtemp(prefix="vdv_comphist_")
DB = os.path.join(TMP, "hist.sqlite")

# ---- synthetic fixtures ----------------------------------------------------
OPS = os.path.join(TMP, "ops.csv")
with open(OPS, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["", "WIP Volume", "Unpaid"] + [""] * 15)          # summary junk
    w.writerow(["", "Index", "Client", "Property Address"] + [""] * 14)
    w.writerow(["1/10/2026", "545001", "Class", "117 S Main St", "23901", "1004",
                "1/14/2026", "$350", "$10", "$340", "$310,000", "Paid and Xfered",
                "", "", "", "", "1", "1"])
    w.writerow(["2/20/2026", "645002", "Voxtur", "88 Lake View Dr", "23917", "2055",
                "2/24/2026", "$300", "$0", "$300", "$255,000", "Paid - Xfer Pending",
                "", "", "", "", "1", "1"])
    w.writerow(["3/05/2024", "745003", "Class", "9 Old Order Rd", "23901", "1004",
                "3/09/2024", "$400", "$0", "$400", "$200,000", "Paid and Xfered",
                "", "", "", "", "1", "1"])                        # out of window

CORPUS = os.path.join(TMP, "corpus.json")
with open(CORPUS, "w") as f:
    json.dump({"n_files": 2, "extracted": "test", "files": {
        "117S_MainSt.dma": {
            "COUNTY": "Prince Edward", "PROPERTY_ZIP_CODE": "23901",
            "PROPERTY_CITY_NAME": "Farmville", "BLDG_ABOVE_GRADE_SQFT": "1500",
            "YEAR_BUILT": "1965", "STYLE": "Ranch", "BEDROOMS": "3",
            "APN": "111-22-33", "OWNER_NAME": "MUST NOT INDEX",
            "Address": "120 Sample St, Farmville", "Sales Price": "$300,000",
            "Total Finished Area": "1480", "Status": "CLSD"},
        "88 Lake View Dr.dma": {
            "COUNTY": "Mecklenburg", "PROPERTY_ZIP_CODE": "23917",
            "BLDG_ABOVE_GRADE_SQFT": "1300", "YEAR_BUILT": "1988",
            "BEDROOMS": "2"},
    }}, f)

DMA = os.path.join(TMP, "dma")
os.makedirs(DMA, exist_ok=True)
for fn, mts in (("117S_MainSt.dma", "2026-01-12"), ("88 Lake View Dr.dma", "2026-02-22"),
                ("77 Orphan Ct.dma", "2026-06-01")):
    p = os.path.join(DMA, fn)
    with open(p, "wb") as f:
        f.write(b"")   # scanner reads names+mtimes only — never opens these
    import time as _t
    from datetime import datetime as _dt
    ts = _t.mktime(_dt.strptime(mts, "%Y-%m-%d").timetuple())
    os.utime(p, (ts, ts))

# ---------------------------------------------------------------------------
# H1: street_key squash matching
# ---------------------------------------------------------------------------
try:
    assert street_key("117 S Main St") == street_key("117S_MainSt")
    assert street_key("1114 Skipwith Rd") == street_key("1114 SKIPWITH RD.")
    assert street_key("105GreenhavenDr") == street_key("105 Greenhaven Dr")
    assert street_key("88 Lake View Dr") != street_key("88 Lakeview Ct")
    ok("H1: street_key — squashes case/punct/spacing; distinct streets stay distinct")
except Exception as e:
    fail("H1", str(e))

# ---------------------------------------------------------------------------
# H2: ops CSV parse skips junk, corpus facts skip PII, dma scan reads names only
# ---------------------------------------------------------------------------
try:
    rows = parse_ops_csv(OPS)
    assert len(rows) == 3, "expected 3 data rows, got {}".format(len(rows))
    assert rows[0]["street"] == "117 S Main St" and rows[0]["zip"] == "23901"
    assert rows[0]["report_date"] == "2026-01-14"      # col6 preferred
    assert rows[0]["appraised_value"] == 310000.0
    facts = load_corpus_facts(CORPUS)
    k = street_key("117 S Main St")
    assert facts[k]["gla"] == 1500.0 and facts[k]["county"] == "Prince Edward"
    assert "Sales Price: $300,000" in facts[k]["comp_hint"]
    assert not any("MUST NOT INDEX" in str(v) for v in facts[k].values()), "PII leaked"
    dma = scan_dma_dir(DMA)
    assert len(dma) == 3 and dma[k][0] == "117S_MainSt.dma"
    ok("H2: ops parse (junk skipped, col6 date, $ parse) · corpus facts (no PII) · dma scan")
except Exception as e:
    fail("H2", str(e))

# ---------------------------------------------------------------------------
# H3: build — join across the three sources; orphan .dma gets mtime-approx
# ---------------------------------------------------------------------------
try:
    s = build([OPS], CORPUS, DMA, DB)
    assert s["ops_rows"] == 3 and s["dma_files"] == 3
    assert s["index_rows"] == 4        # 3 ops + 1 orphan dma
    import sqlite3
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    r = dict(con.execute("SELECT * FROM history WHERE street='117 S Main St'").fetchone())
    assert r["sources"] == "ops+corpus+dma" and r["gla"] == 1500.0
    assert r["dma_file"] == "117S_MainSt.dma" and r["date_basis"] == "ops"
    orphan = dict(con.execute("SELECT * FROM history WHERE street='77 Orphan Ct'").fetchone())
    assert orphan["date_basis"] == "mtime-approx" and orphan["report_date"] == "2026-06-01"
    con.close()
    ok("H3: build joins ops+corpus+dma on street key; orphan .dma = mtime-approx row")
except Exception as e:
    fail("H3", str(e))

# ---------------------------------------------------------------------------
# H4: search tiers + 12-mo window + formatting
# ---------------------------------------------------------------------------
try:
    # exact: same property, regardless of window
    h = search("117 S Main Street, Farmville, VA 23901", zip_code="23901",
               gla=1520, as_of="2026-07-02", db_path=DB)
    assert len(h["exact"]) == 1 and h["exact"][0]["street"] == "117 S Main St"
    # similar: same zip + GLA in band, in window — none (only exact in 23901 is itself;
    # 9 Old Order Rd is 23901 but out of window AND has no GLA)
    assert h["similar"] == [] and h["weak"] == []
    # different subject in 23901: finds 117 S Main as similar (GLA 1500 vs 1520)
    h2 = search("500 New Subject Ln", zip_code="23901", gla=1520,
                as_of="2026-07-02", db_path=DB)
    assert len(h2["similar"]) == 1 and h2["similar"][0]["street"] == "117 S Main St"
    # out-of-window row (2024) never appears
    assert not any(r["street"] == "9 Old Order Rd"
                   for r in h2["similar"] + h2["weak"])
    # weak: zip match without GLA on either side
    h3 = search("500 New Subject Ln", zip_code="23917", as_of="2026-07-02", db_path=DB)
    assert any(r["street"] == "88 Lake View Dr" for r in h3["weak"] + h3["similar"])
    # formatting carries the guardrail line + the comp hint
    txt = format_hits(h2)
    assert "CANDIDATES ONLY" in txt and "YV decides" in txt
    assert "hint: Address: 120 Sample St" in txt
    assert "Prior work" in txt
    # missing index -> None -> not-built notice
    assert search("1 X St", db_path=os.path.join(TMP, "nope.sqlite")) is None
    assert "index not built" in format_hits(None)
    ok("H4: tiers exact/similar/weak, 12-mo window, hints + guardrail text, not-built notice")
except Exception as e:
    fail("H4", str(e))

# ---------------------------------------------------------------------------
# H5: repo-path guard
# ---------------------------------------------------------------------------
try:
    try:
        _resolve_db(os.path.join(REPO, "tools", "evil.sqlite"))
        raise AssertionError("repo DB path did not raise")
    except ValueError:
        pass
    assert not os.path.abspath(TMP).startswith(REPO)
    ok("H5: boundary — repo DB path raises; fixtures live outside the repo")
except Exception as e:
    fail("H5", str(e))

# ---------------------------------------------------------------------------
print()
print("=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
print("RESULT: {}/{} tests passed".format(passed, passed + failed))
if failed:
    for r in results:
        if r[0] == "FAIL":
            print("  FAIL  {}  |  {}".format(r[1], r[2]))
sys.exit(0 if failed == 0 else 1)
