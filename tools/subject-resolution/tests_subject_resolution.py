#!/usr/bin/env python3
"""Build C QA runner — subject-resolution cache (+ later phases append here)."""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from subject_cache import (normalize_address, get, put, delete, list_entries,
                           staleness_flags, _resolve_db_path)

results = []


def ok(name):
    results.append(("PASS", name))
    print("PASS  " + name)


def fail(name, reason):
    results.append(("FAIL", name, reason))
    print("FAIL  {} | {}".format(name, reason))


# scratch dir ALWAYS outside the repo (T14 pattern from Build B)
TMP = tempfile.mkdtemp(prefix="vdv_subjres_")
DB = os.path.join(TMP, "cache.sqlite")

SUBJ = {
    "address": {"full": "119 Example Ridge Ln, Henrico, VA 23229",
                "county": "Henrico"},
    "characteristics": {"gla_sf": 1856, "style": "Ranch"},
    "assessment": {"tax_year": 2026, "total_value": 295000},
    "resolution": {"method": "county-assessment", "cached": False,
                   "resolved_on": "2026-07-02"},
}

# ---------------------------------------------------------------------------
# C1: address normalization equivalence table
# ---------------------------------------------------------------------------
try:
    same = [
        ("119 Example Ridge Lane, Henrico, VA 23229",
         "119 EXAMPLE RIDGE LN., Henrico County, VA 23229"),
        ("4237 North Hall Road, Boydton, VA 23917",
         "4237 N HALL RD, Boydton, VA 23917"),
        ("12 Oak Avenue Apt 4B, Richmond, VA 23220",
         "12 OAK AVE, Richmond, VA 23220"),
        ("88 Main Street Suite 200, Farmville, VA 23901",
         "88 Main St, Farmville, VA 23901"),
        ("7 Pine Drive # 2, Henrico, VA 23229",
         "7 Pine Dr, Henrico, VA 23229"),
        ("5 Lake Circle, Clarksville, VA 23927",
         "5 Lake Cir, Clarksville, VA 23927"),
        ("9 Ridge Parkway, Henrico, VA 23233",
         "9 Ridge Pkwy, Henrico, VA 23233"),
        ("3 Cedar Terrace, Richmond, VA 23225",
         "3 Cedar Ter., Richmond, VA 23225"),
        ("21 Mill Place, Ashland, VA 23005",
         "21 Mill Pl, Ashland, VA 23005"),
        ("60 River Highway, Powhatan, VA 23139",
         "60 River Hwy, Powhatan, VA 23139"),
        ("34 Chatham Ln", "34 Chatham Lane"),  # street-only, no zip
        ("15 South Boulevard, Richmond, VA 23220",
         "15 S BLVD, Richmond, VA 23220"),
    ]
    for a, b in same:
        ka, kb = normalize_address(a), normalize_address(b)
        assert ka == kb, "{!r} -> {!r} != {!r} -> {!r}".format(a, ka, b, kb)
    # different zip must NOT collide
    assert normalize_address("1 Main St, X, VA 23220") != \
        normalize_address("1 Main St, X, VA 23221"), "zip should split keys"
    # empty input fails loud
    try:
        normalize_address("   ")
        raise AssertionError("empty address did not raise")
    except ValueError:
        pass
    ok("C1: address normalization — {} equivalence pairs, zip split, empty raises".format(len(same)))
except Exception as e:
    fail("C1", str(e))

# ---------------------------------------------------------------------------
# C2: put/get roundtrip + deterministic age vs --as-of
# ---------------------------------------------------------------------------
try:
    key = put("119 Example Ridge Ln, Henrico, VA 23229", SUBJ,
              "county-assessment", db_path=DB, put_at="2026-07-02T12:00:00")
    hit = get("119 EXAMPLE RIDGE LANE, Henrico County, VA 23229",
              db_path=DB, as_of="2026-07-12")
    assert hit is not None, "normalized variant missed the cache"
    subject, resolved_on, age = hit
    assert subject == SUBJ, "roundtrip mutated the subject dict"
    assert resolved_on == "2026-07-02" and age == 10, \
        "resolved_on={} age={}".format(resolved_on, age)
    hit2 = get("119 Example Ridge Ln, Henrico, VA 23229", db_path=DB, as_of="2026-07-12")
    assert hit2 == hit, "same as_of should be deterministic"
    ok("C2: put/get roundtrip — variant spelling hits, dict intact, age deterministic")
except Exception as e:
    fail("C2", str(e))

# ---------------------------------------------------------------------------
# C3: miss returns None; delete works
# ---------------------------------------------------------------------------
try:
    assert get("999 Nowhere Ct, Henrico, VA 23229", db_path=DB) is None
    put("77 Gone St, Henrico, VA 23229", SUBJ, "test", db_path=DB,
        put_at="2026-07-02T12:00:00")
    assert delete("77 Gone Street, Henrico, VA 23229", db_path=DB) == 1
    assert get("77 Gone St, Henrico, VA 23229", db_path=DB) is None
    ok("C3: miss -> None; delete via normalized variant removes the row")
except Exception as e:
    fail("C3", str(e))

# ---------------------------------------------------------------------------
# C4: staleness flags — TTL boundary + tax-year-behind
# ---------------------------------------------------------------------------
try:
    # 180 days exactly -> NOT stale; 181 -> stale
    f180 = staleness_flags(SUBJ, "2026-01-03", as_of="2026-07-02")  # 180 days
    assert not any("days old" in f for f in f180), "180d flagged: " + str(f180)
    f181 = staleness_flags(SUBJ, "2026-01-02", as_of="2026-07-02")  # 181 days
    assert any("days old" in f for f in f181), "181d not flagged"
    # tax year behind the as-of year
    old = dict(SUBJ, assessment={"tax_year": 2025})
    fty = staleness_flags(old, "2026-06-30", as_of="2026-07-02")
    assert any("tax year 2025 is behind 2026" in f for f in fty), str(fty)
    # fresh + current year -> no flags
    assert staleness_flags(SUBJ, "2026-06-30", as_of="2026-07-02") == []
    ok("C4: staleness — 180d boundary exact, 181d flags, tax-year-behind flags, fresh clean")
except Exception as e:
    fail("C4", str(e))

# ---------------------------------------------------------------------------
# C5: boundary — DB inside the repo refuses; default path is client zone
# ---------------------------------------------------------------------------
try:
    try:
        _resolve_db_path(os.path.join(REPO, "tools", "evil.sqlite"))
        raise AssertionError("repo-resident DB path did not raise")
    except ValueError:
        pass
    default = _resolve_db_path(None) if "VDV_SUBJECT_CACHE" not in os.environ else None
    if default is not None:
        assert not default.startswith(REPO), "default DB inside repo!"
        assert "Subject cache" in default, "unexpected default: " + default
    assert os.path.abspath(TMP) != REPO and not os.path.abspath(TMP).startswith(REPO)
    ok("C5: boundary — repo DB path raises; default + QA tmp live in client zone")
except Exception as e:
    fail("C5", str(e))

# ---------------------------------------------------------------------------
# C6: put replaces (no dupes); put without resolved_on fails loud
# ---------------------------------------------------------------------------
try:
    upd = json.loads(json.dumps(SUBJ))
    upd["characteristics"]["gla_sf"] = 1900
    upd["resolution"]["resolved_on"] = "2026-07-03"
    put("119 Example Ridge Ln, Henrico, VA 23229", upd, "re-pull", db_path=DB,
        put_at="2026-07-03T09:00:00")
    rows = [r for r in list_entries(DB) if r[0].startswith("119 EXAMPLE RIDGE LN")]
    assert len(rows) == 1, "duplicate rows: " + str(rows)
    subject, resolved_on, _ = get("119 Example Ridge Ln, Henrico, VA 23229", db_path=DB)
    assert subject["characteristics"]["gla_sf"] == 1900 and resolved_on == "2026-07-03"
    try:
        bad = {"address": {"full": "1 X St"}}
        put("1 X St, Henrico, VA 23229", bad, "no-date", db_path=DB)
        raise AssertionError("put without resolved_on did not raise")
    except ValueError:
        pass
    ok("C6: put replaces in place (1 row), newest wins; undated put raises")
except Exception as e:
    fail("C6", str(e))

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
