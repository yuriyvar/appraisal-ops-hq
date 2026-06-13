#!/usr/bin/env python3
"""Phase 3 QA test runner for Build B (assemble_record.py)."""

import csv
import glob
import hashlib
import json
import os
import sys

# -- path setup --
# This file lives in tools/record-assembler/; repo root is two levels up.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "record-assembler"))
sys.path.insert(0, os.path.join(REPO, "tools", "worksheet-renderer"))

from assemble_record import (assemble, _normalize_mls, _normalize_status,
                              _parse_baths, _detect_layout)
from render_worksheet import render

results = []


def ok(name):
    results.append(("PASS", name))
    print("PASS  " + name)


def fail(name, reason):
    results.append(("FAIL", name, reason))
    print("FAIL  {} | {}".format(name, reason))


TMP = os.path.join("C:\\Users\\yuriy\\VDV Appraisals", "_qa_tmp")
os.makedirs(TMP, exist_ok=True)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
APPRAISER_HEADERS = [
    "Distance", "#", "ML #", "PID", "Prop Type", "Status", "Area", "Address",
    "Subdivision", "Type", "PR Abv Fin SqFt", "PR Bldg SqFt", "PR Living SqFt",
    "# Bedrooms", "Total Baths", "# Rooms", "Total Finished Area", "SqFtTotal",
    "Original List Price", "List Price", "Sales Price", "", "Days On Market", "MLS",
]
AGENT_HEADERS = [
    "Distance", "#", "ML #", "PID", "Status", "Area", "Address", "Subdivision",
    "Type", "# Bedrooms", "Total Baths", "# Rooms", "Total Finished Area",
    "List Price", "Sales Price", "", "Days On Market", "", "MLS",
]

BASE_SUBJECT = {
    "order": {"order_id": "TEST-001", "form_type": "1004", "client": "Test Bank",
              "loan_number": None, "effective_date": "2026-06-13", "due_date": None,
              "inspection": None, "fee": 500, "status": "in-progress"},
    "address": {"full": "119 Countryside Ln, Henrico, VA 23229",
                "street": "119 Countryside Ln", "city": "Henrico",
                "state": "VA", "zip": "23229", "county": "Henrico"},
    "identifiers": {"gpin": "778-744-7716", "pid": None, "apn": "778-744-7716",
                    "subdivision": "Countryside", "section": None, "block": None,
                    "lot": None, "magisterial_district": "Tuckahoe",
                    "neighborhood_code": None, "legal_description": None},
    "characteristics": {"property_type": "SFR", "use_code": "10", "zoning": "R-3",
                        "gla_sf": 1856, "above_grade_sf": 1856,
                        "below_grade_finished_sf": None, "basement": "None",
                        "year_built": 1972, "stories": 1, "style": "Ranch",
                        "grade_or_condition": "C3/Q3", "bedrooms": 3,
                        "full_baths": 2, "half_baths": 0, "total_rooms": 7,
                        "lot_size_sf": 10890, "lot_size_acres": 0.25,
                        "garage": "1-car attached", "pool": False,
                        "fireplaces": 1, "heating": "FWA", "cooling": "Central A/C",
                        "exterior": "Vinyl"},
    "assessment": {"tax_year": 2025, "land_value": 85000,
                   "improvements_value": 210000, "total_value": 295000},
    "resolution": {"input_was_address_only": True, "method": "county-assessment",
                   "no_tax_id": False, "neighbor_unit_proxy": None,
                   "cached": False, "resolved_on": "2026-06-13"},
    "verification": [], "listing": None, "sales_history": [], "flags": [],
    "geo": {"lat": None, "lon": None},
    "market": {"search": {"radius_mi": 1.0, "sale_window_months": 12,
                          "gla_band": {"low_sf": 1484, "high_sf": 2228,
                                       "luxury_widened": False},
                          "mls_systems": ["CVR MLS"]},
               "neighborhood_notes": None},
    "sources": [],
}


def write_subject(fname, overrides=None):
    import copy
    s = copy.deepcopy(BASE_SUBJECT)
    if overrides:
        s.update(overrides)
    p = os.path.join(TMP, fname)
    with open(p, "w") as f:
        json.dump(s, f)
    return p


def write_csv(fname, rows, layout="appraiser"):
    headers = APPRAISER_HEADERS if layout == "appraiser" else AGENT_HEADERS
    p = os.path.join(TMP, fname)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return p


def out(fname):
    return os.path.join(TMP, fname)


# ---------------------------------------------------------------------------
# T1: MLS# normalization
# ---------------------------------------------------------------------------
try:
    assert _normalize_mls("BRTVAMB2000092") == "VAMB2000092"
    assert _normalize_mls("VA1234567") == "VA1234567"
    assert _normalize_mls("") is None
    assert _normalize_mls(None) is None
    assert _normalize_mls("BRTXXXXXXXXX") == "XXXXXXXXX"
    ok("T1: MLS# normalization (BRT strip, passthrough, empty, None)")
except AssertionError as e:
    fail("T1", str(e))

# ---------------------------------------------------------------------------
# T2: Status normalization
# ---------------------------------------------------------------------------
try:
    assert _normalize_status("CLOSD") == "closed"
    assert _normalize_status("PEND") == "pending"
    assert _normalize_status("ACT") == "active"
    assert _normalize_status("closd") == "closed"
    assert _normalize_status("GARBAGE") == "unknown"
    ok("T2: Status normalization (CLOSD/PEND/ACT/unknown/lowercase)")
except AssertionError as e:
    fail("T2", str(e))

# ---------------------------------------------------------------------------
# T3: Baths parsing
# ---------------------------------------------------------------------------
try:
    assert _parse_baths("2.1") == (2, 1), str(_parse_baths("2.1"))
    assert _parse_baths("3") == (3, 0)
    assert _parse_baths("") == (None, None)
    assert _parse_baths(None) == (None, None)
    assert _parse_baths("2.2") == (2, 2)
    ok("T3: Baths parsing (decimal split, whole, empty, None, 2-half)")
except AssertionError as e:
    fail("T3", str(e))

# ---------------------------------------------------------------------------
# T4: CSV layout detection
# ---------------------------------------------------------------------------
try:
    assert _detect_layout(APPRAISER_HEADERS) == "appraiser"
    assert _detect_layout(AGENT_HEADERS) == "agent"
    assert _detect_layout([]) == "agent"
    ok("T4: CSV layout detection")
except AssertionError as e:
    fail("T4", str(e))

# ---------------------------------------------------------------------------
# T5: Empty comps CSV
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t5.json")
    cp = write_csv("empty.csv", [])
    rec = assemble(sp, cp, out("rec_t5.json"), generated_at="2026-06-13T12:00:00Z")
    assert rec["comps"] == []
    assert rec["schema_version"] == "1.0"
    assert rec["review"]["human_reviewed"] is False
    assert rec["adjustments"]["entered_by_appraiser"] is False
    assert rec["generated_by"] == "claude-cowork"
    ok("T5: Empty comps CSV -> valid record, empty comps, correct defaults")
except Exception as e:
    fail("T5", str(e))

# ---------------------------------------------------------------------------
# T6: Missing GLA -> null + flag, price_per_sf null
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t6.json")
    cp = write_csv("no_gla.csv", [
        {"#": "1", "ML #": "VA1234", "PID": "P1", "Status": "CLOSD",
         "Address": "100 Main St, Henrico, VA 23229",
         "Distance": "0.5", "Total Finished Area": "",
         "# Bedrooms": "3", "Total Baths": "2",
         "Sales Price": "300000", "List Price": "305000",
         "Days On Market": "10", "MLS": "CVR"},
    ])
    rec = assemble(sp, cp, out("rec_t6.json"), generated_at="2026-06-13T12:00:00Z")
    c = rec["comps"][0]
    assert c["characteristics"]["gla_sf"] is None, "GLA should be null; got " + str(c["characteristics"]["gla_sf"])
    assert c["price_per_sf"] is None
    assert c["gla_delta_vs_subject_sf"] is None
    gla_flags = [f for f in c["flags"] if "GLA unverified" in f]
    assert gla_flags, "GLA flag missing; flags=" + str(c["flags"])
    ok("T6: Missing GLA -> null + flag, no price_per_sf, no gla_delta")
except Exception as e:
    fail("T6", str(e))

# ---------------------------------------------------------------------------
# T7: Out-of-county comp flagged
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t7.json")
    cp = write_csv("ooc.csv", [
        {"#": "1", "ML #": "VA9999", "PID": "P2", "Status": "CLOSD",
         "Address": "55 Blue Ridge Dr, Goochland, VA 23063",
         "Distance": "8.2", "Total Finished Area": "1900",
         "# Bedrooms": "3", "Total Baths": "2",
         "Sales Price": "320000", "List Price": "325000",
         "Days On Market": "15", "MLS": "CVR"},
    ])
    rec = assemble(sp, cp, out("rec_t7.json"), generated_at="2026-06-13T12:00:00Z")
    c = rec["comps"][0]
    assert c["out_of_county"] is True, "out_of_county not flagged: " + str(c["out_of_county"])
    ooc_flags = [f for f in c["flags"] if "Out-of-county" in f]
    assert ooc_flags, "out-of-county flag missing; flags=" + str(c["flags"])
    ok("T7: Out-of-county comp -> out_of_county=true + flag")
except Exception as e:
    fail("T7", str(e))

# ---------------------------------------------------------------------------
# T8: BRTVA MLS# normalized
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t8.json")
    cp = write_csv("brt.csv", [
        {"#": "1", "ML #": "BRTVAMB2000092", "PID": "P3", "Status": "CLOSD",
         "Address": "120 Countryside Ln, Henrico, VA 23229",
         "Distance": "0.1", "Total Finished Area": "1800",
         "# Bedrooms": "3", "Total Baths": "2",
         "Sales Price": "340000", "List Price": "345000",
         "Days On Market": "7", "MLS": "CVR"},
    ])
    rec = assemble(sp, cp, out("rec_t8.json"), generated_at="2026-06-13T12:00:00Z")
    c = rec["comps"][0]
    assert c["identifiers"]["mls_number"] == "VAMB2000092", "BRT not stripped: " + str(c["identifiers"]["mls_number"])
    brt_flags = [f for f in c["flags"] if "BRT prefix stripped" in f]
    assert brt_flags, "BRT normalization flag missing; flags=" + str(c["flags"])
    ok("T8: BRTVA MLS# normalized in comp + flag")
except Exception as e:
    fail("T8", str(e))

# ---------------------------------------------------------------------------
# T9: Closed/active/pending mix; baths split
# ---------------------------------------------------------------------------
MIX_ROWS = [
    {"#": "1", "ML #": "VA001", "PID": "P1", "Status": "CLOSD",
     "Address": "121 Countryside Ln, Henrico, VA 23229",
     "Distance": "0.1", "Total Finished Area": "1900",
     "# Bedrooms": "3", "Total Baths": "2",
     "Sales Price": "350000", "List Price": "355000", "Days On Market": "5", "MLS": "CVR"},
    {"#": "2", "ML #": "VA002", "PID": "P2", "Status": "ACT",
     "Address": "122 Countryside Ln, Henrico, VA 23229",
     "Distance": "0.2", "Total Finished Area": "1850",
     "# Bedrooms": "3", "Total Baths": "2",
     "Sales Price": "", "List Price": "360000", "Days On Market": "3", "MLS": "CVR"},
    {"#": "3", "ML #": "VA003", "PID": "P3", "Status": "PEND",
     "Address": "123 Countryside Ln, Henrico, VA 23229",
     "Distance": "0.3", "Total Finished Area": "1820",
     "# Bedrooms": "3", "Total Baths": "2.1",
     "Sales Price": "", "List Price": "348000", "Days On Market": "12", "MLS": "CVR"},
]
try:
    sp = write_subject("subj_t9.json")
    cp = write_csv("mix.csv", MIX_ROWS)
    rec = assemble(sp, cp, out("rec_t9.json"), generated_at="2026-06-13T12:00:00Z")
    statuses = [c["status"] for c in rec["comps"]]
    assert "closed" in statuses
    assert "active" in statuses
    assert "pending" in statuses
    pend = next(c for c in rec["comps"] if c["status"] == "pending")
    assert pend["characteristics"]["full_baths"] == 2, str(pend["characteristics"])
    assert pend["characteristics"]["half_baths"] == 1, str(pend["characteristics"])
    ok("T9: Closed/active/pending mix segregated; baths split on decimal")
except Exception as e:
    fail("T9", str(e))

# ---------------------------------------------------------------------------
# T10: Determinism
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t10.json")
    cp = write_csv("mix_det.csv", MIX_ROWS)
    assemble(sp, cp, out("det_a.json"), generated_at="2026-06-13T12:00:00Z")
    assemble(sp, cp, out("det_b.json"), generated_at="2026-06-13T12:00:00Z")
    with open(out("det_a.json"), "rb") as f:
        ha = hashlib.md5(f.read()).hexdigest()
    with open(out("det_b.json"), "rb") as f:
        hb = hashlib.md5(f.read()).hexdigest()
    assert ha == hb, "non-deterministic: {} != {}".format(ha, hb)
    ok("T10: Determinism — two runs same input+timestamp -> byte-identical JSON")
except Exception as e:
    fail("T10", str(e))

# ---------------------------------------------------------------------------
# T11: Schema structural validation
# ---------------------------------------------------------------------------
try:
    with open(os.path.join(REPO, "appraisal-record.schema.json")) as f:
        schema = json.load(f)
    required = schema.get("required", [])
    with open(out("rec_t9.json")) as f:
        rec_s = json.load(f)
    missing_top = [k for k in required if k not in rec_s]
    assert not missing_top, "Missing required fields: " + str(missing_top)
    comp_req = schema["properties"]["comps"]["items"].get("required", [])
    for c in rec_s["comps"]:
        miss = [k for k in comp_req if k not in c]
        assert not miss, "Comp missing required: " + str(miss)
    ok("T11: Schema structural validation (all required fields present)")
except Exception as e:
    fail("T11", str(e))

# ---------------------------------------------------------------------------
# T12: Derived fields correct
# ---------------------------------------------------------------------------
try:
    with open(out("rec_t9.json")) as f:
        rec_d = json.load(f)
    closed_comp = next(c for c in rec_d["comps"] if c["status"] == "closed")
    expected_ppsf = round(350000 / 1900, 2)
    assert closed_comp["price_per_sf"] == expected_ppsf, \
        "price_per_sf={}, expected={}".format(closed_comp["price_per_sf"], expected_ppsf)
    expected_delta = round(1900 - 1856, 0)
    assert closed_comp["gla_delta_vs_subject_sf"] == expected_delta, \
        "gla_delta={}".format(closed_comp["gla_delta_vs_subject_sf"])
    ok("T12: Derived fields — price_per_sf and gla_delta_vs_subject_sf correct")
except Exception as e:
    fail("T12", str(e))

# ---------------------------------------------------------------------------
# T13: Agent Single Line layout
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t13.json")
    agent_p = write_csv("agent.csv", [
        {"#": "1", "ML #": "VA010", "PID": "P10", "Status": "ACT",
         "Address": "200 Test Ln, Henrico, VA 23229",
         "Distance": "0.5", "Total Finished Area": "1780",
         "# Bedrooms": "3", "Total Baths": "2",
         "List Price": "355000", "Sales Price": "", "Days On Market": "4", "MLS": "CVR"},
    ], layout="agent")
    rec = assemble(sp, None, out("rec_t13.json"),
                   comps_agent_csv_path=agent_p,
                   generated_at="2026-06-13T12:00:00Z")
    assert len(rec["comps"]) == 1
    assert rec["comps"][0]["status"] == "active"
    assert rec["comps"][0]["characteristics"]["above_grade_sf"] is None  # no PR col
    ok("T13: Agent layout -> active status; above_grade_sf=null (no PR col in agent)")
except Exception as e:
    fail("T13", str(e))

# ---------------------------------------------------------------------------
# T14: Boundary — QA tmp output is in client zone, not repo
# ---------------------------------------------------------------------------
try:
    tmp_abs = os.path.abspath(TMP)
    repo_abs = os.path.abspath(REPO)
    assert not tmp_abs.startswith(repo_abs), \
        "TMP is inside repo! TMP={}, REPO={}".format(tmp_abs, repo_abs)
    ok("T14: Boundary — QA temp outputs are in client zone, not repo")
except Exception as e:
    fail("T14", str(e))

# ---------------------------------------------------------------------------
# T15: End-to-end smoke — render to HTML and sanity-check
# ---------------------------------------------------------------------------
try:
    with open(out("rec_t9.json")) as f:
        rec_smoke = json.load(f)
    html_doc = render(rec_smoke)
    assert "<!DOCTYPE html>" in html_doc
    assert "tab-comps" in html_doc
    assert "tab-subject" in html_doc
    assert "NOT YET REVIEWED" in html_doc
    # Raw Matrix codes must not leak. CLOSD is the distinctive misspelled raw
    # code (NOT a substring of the normalized "CLOSED"), so it is the reliable
    # canary. Note: "PEND"/"ACT" are substrings of the legitimately rendered
    # "PENDING"/"ACTIVE", so they cannot be tested by bare substring search.
    assert "CLOSD" not in html_doc, "raw Matrix status code CLOSD leaked into HTML"
    # The renderer normalizes status to lowercase classes + uppercase display.
    assert "st-closed" in html_doc, "normalized closed status class missing"
    assert "st-pending" in html_doc, "normalized pending status class missing"
    assert "st-active" in html_doc, "normalized active status class missing"
    assert "<script>" in html_doc

    # parse for well-formedness (basic)
    import html.parser
    class Counter(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = 0
        def handle_starttag(self, t, a):
            self.tags += 1
    c2 = Counter()
    c2.feed(html_doc)
    assert c2.tags > 50, "HTML suspiciously small: {} tags".format(c2.tags)
    ok("T15: End-to-end smoke — HTML renders, parses, no raw status codes, well-formed")
except Exception as e:
    fail("T15", str(e))

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
print()
print("=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
print("RESULT: {}/{} tests passed".format(passed, passed + failed))
if failed:
    print("\nFailed tests:")
    for r in results:
        if r[0] == "FAIL":
            print("  FAIL  {}  |  {}".format(r[1], r[2]))
sys.exit(0 if failed == 0 else 1)
