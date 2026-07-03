#!/usr/bin/env python3
"""Phase 3 QA test runner for Build B (assemble_record.py)."""

import csv
import glob
import hashlib
import json
import os
import sys
import tempfile

# -- path setup --
# This file lives in tools/record-assembler/; repo root is two levels up.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "record-assembler"))
sys.path.insert(0, os.path.join(REPO, "tools", "worksheet-renderer"))

from assemble_record import (assemble, _normalize_mls, _normalize_status,
                              _parse_baths, _detect_layout,
                              _sale_window_flag, _gla_band_flag)
from render_worksheet import render, audit_comp_tax_ids, esc

results = []


def ok(name):
    results.append(("PASS", name))
    print("PASS  " + name)


def fail(name, reason):
    results.append(("FAIL", name, reason))
    print("FAIL  {} | {}".format(name, reason))


# Scratch dir in the OS temp location — cross-platform and ALWAYS outside the repo
# (a hardcoded "C:\\Users\\..." path is not absolute on Linux/sandbox and would
# create a literal junk dir inside the repo — see inbox 2026-06-15).
TMP = tempfile.mkdtemp(prefix="vdv_qa_")
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
    "address": {"full": "119 Example Ridge Ln, Henrico, VA 23229",
                "street": "119 Example Ridge Ln", "city": "Henrico",
                "state": "VA", "zip": "23229", "county": "Henrico"},
    "identifiers": {"gpin": "778-744-7716", "pid": None, "apn": "778-744-7716",
                    "subdivision": "Example Ridge", "section": None, "block": None,
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
    assert rec["schema_version"] == "1.1"
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
         "Address": "120 Example Ridge Ln, Henrico, VA 23229",
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
     "Address": "121 Example Ridge Ln, Henrico, VA 23229",
     "Distance": "0.1", "Total Finished Area": "1900",
     "# Bedrooms": "3", "Total Baths": "2",
     "Sales Price": "350000", "List Price": "355000", "Days On Market": "5", "MLS": "CVR"},
    {"#": "2", "ML #": "VA002", "PID": "P2", "Status": "ACT",
     "Address": "122 Example Ridge Ln, Henrico, VA 23229",
     "Distance": "0.2", "Total Finished Area": "1850",
     "# Bedrooms": "3", "Total Baths": "2",
     "Sales Price": "", "List Price": "360000", "Days On Market": "3", "MLS": "CVR"},
    {"#": "3", "ML #": "VA003", "PID": "P3", "Status": "PEND",
     "Address": "123 Example Ridge Ln, Henrico, VA 23229",
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
# T16: Comp Tax ID completeness gate (interlane 2026-06-26 [ACTION] #1)
# ---------------------------------------------------------------------------
try:
    with open(out("rec_t9.json")) as f:
        rec_tax = json.load(f)

    def _pid(c):
        return (c.get("identifiers") or {}).get("pid")

    assert any(_pid(c) for c in rec_tax["comps"]), "fixture has no comp PID"
    html_tax = render(rec_tax)
    assert "Tax ID (PID/APN)" in html_tax, "comp grid missing the Tax ID row"
    assert not audit_comp_tax_ids(rec_tax, html_tax), "gate should pass on a good render"
    victim = next(_pid(c) for c in rec_tax["comps"] if _pid(c))
    broken = html_tax.replace(esc(str(victim)), "&mdash;")
    assert audit_comp_tax_ids(rec_tax, broken), \
        "gate failed to detect a comp Tax ID missing from the HTML"
    ok("T16: Comp Tax ID gate — passes good render, catches a blanked comp cell")
except Exception as e:
    fail("T16", str(e))

# ---------------------------------------------------------------------------
# T17: Comp-quality gates — GLA ±10% band, ML#/Tax ID capture, 12-mo window
# ---------------------------------------------------------------------------
try:
    from datetime import date
    sp = write_subject("subj_t17.json")  # subject GLA 1856
    cp = write_csv("quality.csv", [
        {"#": "1", "ML #": "VA100", "PID": "Q1", "Status": "CLOSD",
         "Address": "130 Example Ridge Ln, Henrico, VA 23229",
         "Distance": "0.2", "Total Finished Area": "2200",  # +18.5% -> band flag
         "# Bedrooms": "4", "Total Baths": "3",
         "Sales Price": "420000", "List Price": "425000", "Days On Market": "8", "MLS": "CVR"},
        {"#": "2", "ML #": "", "PID": "Q2", "Status": "CLOSD",  # missing ML#
         "Address": "131 Example Ridge Ln, Henrico, VA 23229",
         "Distance": "0.3", "Total Finished Area": "1900",
         "# Bedrooms": "3", "Total Baths": "2",
         "Sales Price": "360000", "List Price": "365000", "Days On Market": "6", "MLS": "CVR"},
        {"#": "3", "ML #": "VA102", "PID": "", "Status": "CLOSD",  # missing PID
         "Address": "132 Example Ridge Ln, Henrico, VA 23229",
         "Distance": "0.4", "Total Finished Area": "1850",
         "# Bedrooms": "3", "Total Baths": "2",
         "Sales Price": "352000", "List Price": "355000", "Days On Market": "9", "MLS": "CVR"},
    ])
    rec = assemble(sp, cp, out("rec_t17.json"), generated_at="2026-06-13T12:00:00Z")
    c1, c2, c3 = rec["comps"]
    assert any("rubric band" in f for f in c1["flags"]), "GLA band flag missing: " + str(c1["flags"])
    assert any("ML# missing" in f for f in c2["flags"]), "ML# flag missing: " + str(c2["flags"])
    assert any("Tax ID / PID missing" in f for f in c3["flags"]), "Tax ID flag missing: " + str(c3["flags"])
    # missing close date on a CLOSED comp = INFORMATIONAL note only (demoted
    # 2026-07-02: single-line CSV never carries the date, so a hard flag there
    # fired on every comp). Hard flag reserved for a REAL date outside the window.
    for c in rec["comps"]:
        info = [f for f in c["flags"] if "capture the close date" in f]
        assert info, "missing-date info note absent: " + str(c["flags"])
        assert all(f.startswith("INFO:") for f in info), \
            "missing-date note not INFO-prefixed: " + str(info)
        assert not any("month window — supplemental only" in f for f in c["flags"]), \
            "hard window flag fired without a sale date: " + str(c["flags"])
    # direct check of the window logic with real dates
    assert _sale_window_flag("closed", "05/2023", date(2026, 6, 13)), "old sale not flagged"
    hard = _sale_window_flag("closed", "05/2023", date(2026, 6, 13))
    assert not hard.startswith("INFO:") and "outside the 12-month window" in hard, \
        "genuinely-old sale must stay a HARD flag: " + hard
    assert _sale_window_flag("closed", None, date(2026, 6, 13)).startswith("INFO:"), \
        "missing date must be informational"
    assert _sale_window_flag("closed", "2026-03-01", date(2026, 6, 13)) is None, "in-window sale flagged"
    assert _sale_window_flag("active", None, date(2026, 6, 13)) is None, "active comp should be exempt"
    # GLA band helper boundaries
    assert _gla_band_flag(2100, 1856) and _gla_band_flag(1850, 1856) is None
    ok("T17: Comp-quality gates — GLA ±10% band, ML#/Tax ID capture, 12-mo sales window")
except Exception as e:
    fail("T17", str(e))

# ---------------------------------------------------------------------------
# T18: v1.1 defaults + HOA flag + contract passthrough (6/19 brief data layer)
# ---------------------------------------------------------------------------
try:
    # (a) source values ABSENT -> defaults land, HOA flag raised
    sp = write_subject("subj_t18a.json")  # BASE_SUBJECT has none of the v1.1 keys
    cp = write_csv("t18.csv", MIX_ROWS)
    rec = assemble(sp, cp, out("rec_t18a.json"), generated_at="2026-06-13T12:00:00Z")
    s = rec["subject"]
    assert rec["schema_version"] == "1.1"
    assert s["map_reference"] == "GIS", "map_reference default: " + str(s["map_reference"])
    assert s["walls_trim"] == "Wood", "walls_trim default: " + str(s["walls_trim"])
    assert s["assessors_parcel_number"] is None
    assert s["re_taxes_annual"] is None and s["hoa_amount"] is None and s["hoa_period"] is None
    assert any("HOA TBD" in f for f in s["flags"]), "HOA flag missing: " + str(s["flags"])
    assert rec["order"]["contract"]["contract_price"] is None  # refi: all-null block present

    # (b) source values SUPPLIED -> passthrough wins, no HOA flag
    sp2 = write_subject("subj_t18b.json", overrides={
        "assessors_parcel_number": "778-744-7716",
        "map_reference": "Tax Map 42-A", "walls_trim": "Plaster",
        "re_taxes_annual": 2513.0, "hoa_amount": 75.0, "hoa_period": "monthly",
        "neighborhood_bounds": {"north": "Rt. 53", "south": "Rt. 6",
                                "east": "Rt. 15", "west": "Rt. 20"},
        "neighborhood_description_context": {"style": "Ranch", "amenities": "lake access"},
        "order": dict(BASE_SUBJECT["order"],
                      contract={"contract_price": 350000, "contract_date": "2026-06-01",
                                "seller_is_owner_of_record": True, "concessions": 5000,
                                "financing_type": "Conventional"}),
    })
    rec2 = assemble(sp2, cp, out("rec_t18b.json"), generated_at="2026-06-13T12:00:00Z")
    s2 = rec2["subject"]
    assert s2["map_reference"] == "Tax Map 42-A", "supplied map_reference overridden"
    assert s2["walls_trim"] == "Plaster", "supplied walls_trim overridden"
    assert s2["hoa_amount"] == 75.0 and s2["hoa_period"] == "monthly"
    assert not any("HOA TBD" in f for f in s2["flags"]), "HOA flag on supplied HOA"
    assert s2["neighborhood_bounds"]["north"] == "Rt. 53"
    assert s2["neighborhood_description_context"]["amenities"] == "lake access"
    ct = rec2["order"]["contract"]
    assert ct["contract_price"] == 350000 and ct["seller_is_owner_of_record"] is True
    assert ct["financing_type"] == "Conventional"
    ok("T18: v1.1 defaults only-when-absent (GIS/Wood), HOA TBD flag, contract passthrough")
except Exception as e:
    fail("T18", str(e))

# ---------------------------------------------------------------------------
# T19: water/sewer — null stays null, passthrough works, no 'likely' guess ever
# ---------------------------------------------------------------------------
try:
    with open(out("rec_t18a.json")) as f:
        rec_ws = json.load(f)
    assert rec_ws["subject"]["water"] is None, "water invented: " + str(rec_ws["subject"]["water"])
    assert rec_ws["subject"]["sewer"] is None, "sewer invented: " + str(rec_ws["subject"]["sewer"])
    html_ws = render(rec_ws)
    assert "likely Well" not in html_ws and "likely Septic" not in html_ws, \
        "renderer emitted a directional utilities guess"

    sp3 = write_subject("subj_t19.json", overrides={"water": "Public", "sewer": "Public"})
    rec3 = assemble(sp3, write_csv("t19.csv", MIX_ROWS), out("rec_t19.json"),
                    generated_at="2026-06-13T12:00:00Z")
    assert rec3["subject"]["water"] == "Public" and rec3["subject"]["sewer"] == "Public"
    ok("T19: water/sewer null-stays-null + passthrough; no 'likely Well/Septic' in HTML")
except Exception as e:
    fail("T19", str(e))

# ---------------------------------------------------------------------------
# T20: DM-ready subject tab (6/19 brief Changes 1,2,3,4,5,7,8 render side)
# ---------------------------------------------------------------------------
try:
    with open(out("rec_t18a.json")) as f:
        rec_a = json.load(f)   # defaults case (nothing supplied)
    with open(out("rec_t18b.json")) as f:
        rec_b = json.load(f)   # everything supplied
    with open(out("rec_t19.json")) as f:
        rec_c = json.load(f)   # water/sewer = Public
    html_a, html_b, html_c = render(rec_a), render(rec_b), render(rec_c)

    # Change 1 — merged parcel row + informational PID row (kv_table esc()'s
    # labels, so the apostrophe is entity-encoded in the HTML — compare esc'd)
    assert esc("Assessor's Parcel # ★ (= APN / Tax ID)") in html_a
    assert "Internal PID (county portal)" in html_a
    # Change 2 — Map Reference always renders; GIS default, supplied value wins
    assert "Map Reference ★" in html_a and ">GIS<" in html_a
    assert "Tax Map 42-A" in html_b
    # Change 3 — Wood default carries the DEFAULT chip + confirm note. Target
    # the walls-specific markup: the Neighborhood tab legitimately puts DEFAULT
    # chips (Demand/Supply, land use) on every page.
    walls_default = 'Wood <span class="chip chip-default">DEFAULT</span>'
    assert walls_default in html_a and "confirm at inspection" in html_a
    assert "Plaster" in html_b and walls_default not in html_b
    # Change 4 — null utilities say TBD (no guessing); supplied passthrough shows
    assert "Water ★" in html_a and "Sewer ★" in html_a
    assert html_a.count("TBD — verify at inspection") >= 2
    assert "TBD — verify at inspection" not in html_c or "Public" in html_c
    assert "Public" in html_c
    # Change 5 — IMPROVEMENTS banner with the brief's CSS class
    assert 'class="section-banner"' in html_a and "▶ IMPROVEMENTS" in html_a
    assert ".section-banner" in html_a  # CSS block present
    # Change 7 — tax bill its own row, distinct from assessed value
    assert "R.E. Taxes $ ★" in html_a and "Total assessed" in html_a
    assert "$2,513.00" in html_b and "(tax year 2025)" in html_b
    # Change 8 — HOA always present + starred; TBD chip when missing
    assert "HOA $ / period ★" in html_a
    assert "TBD — get from HOA docs" in html_a
    assert "$75 / monthly" in html_b and "TBD — get from HOA docs" not in html_b
    # Contract block renders only when supplied
    assert "Contract (purchase)" in html_b and "$350,000" in html_b
    assert "Contract (purchase)" not in html_a
    ok("T20: DM-ready subject tab — labels, defaults, TBDs, banner, taxes, HOA, contract")
except Exception as e:
    fail("T20", str(e))

# ---------------------------------------------------------------------------
# T21: Neighborhood tab + search-snapshot (6/19 brief Change 6 + adopted standard)
# ---------------------------------------------------------------------------
try:
    with open(out("rec_t17.json")) as f:
        rec_n = json.load(f)   # 3 closed comps w/ prices 352/360/420k; style Ranch
    html_n = render(rec_n)

    # tab registered between Subject and Comp grid, nav + pane both present
    assert 'data-tab="tab-neighborhood"' in html_n and 'id="tab-neighborhood"' in html_n
    assert (html_n.index('data-tab="tab-subject"')
            < html_n.index('data-tab="tab-neighborhood"')
            < html_n.index('data-tab="tab-comps"')), "neighborhood tab out of order"
    # Broad Market: Demand/Supply default; the rest TBD
    assert "In Balance" in html_n and "Demand/Supply" in html_n
    # Boundaries template with [ROAD] placeholders + inspection caution
    assert "[ROAD] to the East" in html_n and "Verify bounding roads at inspection" in html_n
    # Present Land Use % — SFR heuristic zeros
    assert "2-4 Unit" in html_n and "Multi-Family" in html_n and "0%" in html_n
    # One-Unit Housing price range derived from the 3 closed comps
    assert "$352,000" in html_n and "$420,000" in html_n and "$360,000" in html_n
    assert "derived from 3 closed comps" in html_n
    # age column TBD (single-line CSV carries no year_built)
    assert "needs ≥3 closed comps with year built" in html_n
    # Market Description template: style falls back to subject Ranch; amenities generic
    assert "mix of Ranch and Custom Built homes" in html_n
    assert "parks, schools, and local businesses" in html_n
    assert "Draft via notes-composer" in html_n

    # snapshot strip sits above the tab nav, carries governing GLA + band + county
    assert 'class="snapshot"' in html_n
    assert html_n.index('class="snapshot"') < html_n.index('<nav class="tabs">')
    assert "1,856 sf" in html_n                       # above-grade GLA big number
    assert "1,484 sf" in html_n and "2,228 sf" in html_n  # band from market.search
    assert "surrounding: &mdash;" in html_n           # registry lookup NOT done here

    # bounds + surrounding counties render when supplied
    with open(out("rec_t18b.json")) as f:
        rec_nb = json.load(f)
    rec_nb["market"]["search"]["surrounding_counties"] = ["Goochland", "Powhatan"]
    html_nb = render(rec_nb)
    assert "Rt. 53 to the North" in html_nb and "Rt. 20 to the West" in html_nb
    assert "Goochland, Powhatan" in html_nb
    # computed band fallback when market.search has none
    rec_nb["market"]["search"]["gla_band"] = {"low_sf": None, "high_sf": None,
                                              "luxury_widened": False}
    html_nc = render(rec_nb)
    assert "computed ±10%" in html_nc and "1,670 sf" in html_nc and "2,042 sf" in html_nc

    # determinism — same record renders byte-identical
    assert render(rec_n) == html_n, "renderer is not deterministic"
    ok("T21: Neighborhood tab + snapshot — templates, derived ranges, TBDs, determinism")
except Exception as e:
    fail("T21", str(e))

# ---------------------------------------------------------------------------
# T22: BD1 provenance gate — unstamped subject.json flagged on the worksheet
# ---------------------------------------------------------------------------
try:
    sp = write_subject("subj_t22.json", overrides={"resolution": {}})  # no stamp
    cp = write_csv("t22.csv", MIX_ROWS)
    rec = assemble(sp, cp, out("rec_t22.json"), generated_at="2026-06-13T12:00:00Z")
    assert any("produced outside standard work" in f for f in rec["subject"]["flags"]), \
        rec["subject"]["flags"]
    html_t22 = render(rec)
    assert "produced outside standard work" in html_t22, "flag not visible on the worksheet"
    # stamped subjects (the standard path) stay clean
    with open(out("rec_t9.json")) as f:
        rec_ok = json.load(f)
    assert not any("produced outside standard work" in f for f in rec_ok["subject"]["flags"])
    ok("T22: provenance — unstamped subject flagged + rendered; stamped path clean")
except Exception as e:
    fail("T22", str(e))

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
