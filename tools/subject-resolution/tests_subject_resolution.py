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
    # a 5-digit HOUSE NUMBER in a zip-less address must not become the zip slot
    assert normalize_address("14719 Clover Ridge Ln, Chesterfield, VA") == \
        "14719 CLOVER RIDGE LN|CHESTERFIELD", \
        normalize_address("14719 Clover Ridge Ln, Chesterfield, VA")
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
# C7: routing table loads, covers the registry, entries complete
# ---------------------------------------------------------------------------
try:
    from resolve_subject import load_routing, find_county, resolve
    routing = load_routing()
    assert len(routing) >= 12, "expected >=12 jurisdictions, got " + str(len(routing))
    for name, e in routing.items():
        for k in ("vendor", "sor_url", "technique", "mls", "gas_key"):
            assert e.get(k), "{} missing {}".format(name, k)
    # alias + address-segment resolution
    assert find_county(routing, "Henrico County", "x")[0] == "Henrico"
    assert find_county(routing, None, "4237 Hall Rd, Boydton, VA 23917")[0] == "Mecklenburg"
    assert find_county(routing, "N. Chesterfield", "x")[0] == "Chesterfield"
    try:
        find_county(routing, "Narnia", "1 Wardrobe Ln, Narnia, VA 00000")
        raise AssertionError("unknown county did not raise")
    except ValueError as e:
        assert "Henrico" in str(e), "coverage list missing from the error"
    ok("C7: routing — 12 jurisdictions, complete entries, aliases, loud unknown")
except Exception as ex:
    fail("C7", str(ex))

# ---------------------------------------------------------------------------
# C8: resolver MISS -> skeleton + pull sheet (Henrico APEX + gas provider)
# ---------------------------------------------------------------------------
try:
    out8 = os.path.join(TMP, "order8")
    rc = resolve("456 Fresh Pull Rd, Henrico, VA 23229", county="Henrico",
                 out_dir=out8, db_path=DB, as_of="2026-07-02",
                 order_id="T-8", form_type="1004", effective_date="2026-07-02")
    assert rc == 0
    with open(os.path.join(out8, "subject.skeleton.json")) as f:
        sk = json.load(f)
    assert sk["address"]["county"] == "Henrico" and sk["address"]["zip"] == "23229"
    assert sk["order"]["order_id"] == "T-8" and sk["order"]["form_type"] == "1004"
    assert sk["resolution"]["cached"] is False and sk["resolution"]["method"] == "APEX"
    assert sk["characteristics"]["gla_sf"] is None            # never guessed
    assert sk["water"] is None and sk["assessors_parcel_number"] is None  # v1.1 keys present
    assert sk["market"]["search"]["mls_systems"] == ["CVR-Matrix"]
    with open(os.path.join(out8, "pull-sheet.md"), encoding="utf-8") as f:
        ps = f.read()
    assert "realestate.henrico.gov" in ps and "APEX" in ps
    assert "Above-grade GLA" in ps and "Sketch codes" in ps
    assert "Richmond Gas Works" in ps                          # gas DB row surfaced
    assert "Zillow" in ps and "confirm at inspection" in ps
    ok("C8: miss -> v1.1 skeleton (all-null data) + pull sheet w/ APEX + gas + checklist")
except Exception as ex:
    fail("C8", str(ex))

# ---------------------------------------------------------------------------
# C9: resolver HIT -> subject.json cached=true + staleness flag, original date kept
# ---------------------------------------------------------------------------
try:
    stale = json.loads(json.dumps(SUBJ))
    stale["resolution"]["resolved_on"] = "2026-01-01"
    stale["assessment"]["tax_year"] = 2025
    put("300 Stale Ct, Henrico, VA 23229", stale, "county-assessment",
        db_path=DB, put_at="2026-01-01T09:00:00")
    out9 = os.path.join(TMP, "order9")
    rc = resolve("300 Stale Court, Henrico County, VA 23229", county="Henrico",
                 out_dir=out9, db_path=DB, as_of="2026-07-02", order_id="T-9")
    assert rc == 0
    with open(os.path.join(out9, "subject.json")) as f:
        sj = json.load(f)
    assert sj["resolution"]["cached"] is True
    assert sj["resolution"]["resolved_on"] == "2026-01-01"     # vintage preserved
    assert any("days old" in fl for fl in sj["flags"]), sj["flags"]
    assert any("tax year 2025 is behind 2026" in fl for fl in sj["flags"]), sj["flags"]
    assert sj["order"]["order_id"] == "T-9"                    # override merged
    assert sj["characteristics"]["gla_sf"] == 1856             # cached data intact
    assert not os.path.exists(os.path.join(out9, "pull-sheet.md")), "hit wrote a pull sheet"
    ok("C9: hit -> cached=true, vintage kept, staleness+tax-year flags, order merged")
except Exception as ex:
    fail("C9", str(ex))

# ---------------------------------------------------------------------------
# C10: Mecklenburg pull sheet — both-accounts warning, NC surrounding set,
#      confirmed-absent gas; out-dir inside repo refused
# ---------------------------------------------------------------------------
try:
    out10 = os.path.join(TMP, "order10")
    rc = resolve("1234 Kerr Lake Dr, Boydton, VA 23917", county="Mecklenburg",
                 out_dir=out10, db_path=DB, as_of="2026-07-02")
    assert rc == 0
    with open(os.path.join(out10, "pull-sheet.md"), encoding="utf-8") as f:
        ps = f.read()
    assert "BOTH Navica accounts" in ps and "R57xxx" in ps
    assert "Vance NC" in ps and "Halifax" in ps
    assert "CONFIRMED: no SCC gas" in ps                      # sentinel row honored
    assert "ConciseCAMA" in ps and "manufactured homes" in ps
    with open(os.path.join(out10, "subject.skeleton.json")) as f:
        sk10 = json.load(f)
    assert "Vance NC" in sk10["market"]["search"]["surrounding_counties"]
    try:
        resolve("1 Evil St, Henrico, VA 23229", county="Henrico",
                out_dir=os.path.join(REPO, "tools"), db_path=DB)
        raise AssertionError("repo out-dir did not raise")
    except ValueError:
        pass
    ok("C10: Mecklenburg sheet — both-accounts, NC set, gas confirmed-absent; repo out-dir refused")
except Exception as ex:
    fail("C10", str(ex))

# ---------------------------------------------------------------------------
# C11: ingest — normalization happy path
# ---------------------------------------------------------------------------
try:
    from ingest_subject import ingest
    raw = {
        "order": {"effective_date": "2026-07-02"},
        "address": {"full": "9400 Sample Trace Dr, North Chesterfield, VA 23237",
                    "county": "Chesterfield"},
        "identifiers": {"apn": "123-45-67"},
        "characteristics": {"gla_sf": "1,856 sf", "lot_size_sf": "10,890",
                            "lot_size_acres": 0.25, "full_baths": "2.1",
                            "year_built": "1972"},
        "assessment": {"total_value": "$295,000", "tax_year": "2026"},
        "re_taxes_annual": "$2,513.40",
        "resolution": {"method": "ArcGIS"},
        "photo_derived": ["garage"],
        "gla_mls_sf": "1,850",
    }
    subj, flags = ingest(raw, resolved_on="2026-07-02")
    ch = subj["characteristics"]
    assert ch["gla_sf"] == 1856.0 and ch["year_built"] == 1972
    assert subj["assessment"]["total_value"] == 295000.0
    assert subj["re_taxes_annual"] == 2513.4
    assert ch["full_baths"] == 2 and ch["half_baths"] == 1
    assert any("Matrix N.M convention" in f for f in flags)
    assert subj["assessors_parcel_number"] == "1234567"       # dashes stripped
    assert subj["identifiers"]["apn"] == "123-45-67"          # SOR format kept
    assert any("Chesterfield TaxID normalized" in f for f in flags)
    assert any("garage derived from Zillow photos" in f for f in flags)
    ver = subj["verification"]
    assert ver and ver[0]["county"] == "1,856" and ver[0]["mls"] == "1,850"
    assert ver[0]["governing_source"] == "county" and ver[0]["flag"] is None  # <2% apart
    assert "photo_derived" not in subj and "gla_mls_sf" not in subj
    assert subj["resolution"]["resolved_on"] == "2026-07-02"
    assert not any("lot size mismatch" in f for f in flags)   # 10890 == 0.25 ac exactly
    ok("C11: ingest — numerics, baths split, APN quirk, photo flags, verification seed")
except Exception as ex:
    fail("C11", str(ex))

# ---------------------------------------------------------------------------
# C12: ingest — gates fire; hard errors refuse
# ---------------------------------------------------------------------------
try:
    bad = {
        "order": {"effective_date": "2026-07-02"},
        "address": {"full": "1 Gate Ln, Henrico, VA 23229", "county": "Henrico"},
        "characteristics": {"gla_sf": "", "lot_size_sf": 10890,
                            "lot_size_acres": 0.5},
        "assessment": {"tax_year": 2025},
    }
    subj, flags = ingest(bad, resolved_on="2026-07-02")
    assert subj["characteristics"]["gla_sf"] is None
    assert any("GLA unverified" in f for f in flags)
    assert any("lot size mismatch" in f for f in flags)       # 10890 vs 21780
    assert any("tax year 2025 is behind" in f for f in flags)
    # county+MLS GLA >2% apart -> verification row carries the flag
    tw = {"address": {"full": "2 Twist Rd, Henrico, VA 23229", "county": "Henrico"},
          "characteristics": {"gla_sf": 2000}, "gla_mls_sf": 1800}
    s2, f2 = ingest(tw, resolved_on="2026-07-02")
    assert any("differ >2%" in f for f in f2)
    assert s2["verification"][0]["flag"]
    # no county -> refuse (and nothing to cache)
    try:
        ingest({"address": {"full": "3 Nowhere St"}}, resolved_on="2026-07-02")
        raise AssertionError("missing county did not raise")
    except ValueError:
        pass
    # junk numeric -> refuse
    try:
        ingest({"address": {"full": "4 Junk St, Henrico, VA 23229", "county": "Henrico"},
                "characteristics": {"gla_sf": "about two thousand"}},
               resolved_on="2026-07-02")
        raise AssertionError("junk numeric did not raise")
    except ValueError:
        pass
    ok("C12: ingest gates — GLA null+flag, lot mismatch, tax-year, GLA-diff; refusals raise")
except Exception as ex:
    fail("C12", str(ex))

# ---------------------------------------------------------------------------
# C13: end-to-end — resolve(miss) -> fill -> ingest -> cache -> resolve(hit)
#      -> assemble -> render (full pipeline on a synthetic order)
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, os.path.join(REPO, "tools", "record-assembler"))
    sys.path.insert(0, os.path.join(REPO, "tools", "worksheet-renderer"))
    from assemble_record import assemble
    from render_worksheet import render, audit_comp_tax_ids
    import csv as _csv

    out13 = os.path.join(TMP, "order13")
    resolve("777 Pipeline Way, Henrico, VA 23229", county="Henrico",
            out_dir=out13, db_path=DB, as_of="2026-07-02",
            order_id="T-13", form_type="1004", effective_date="2026-07-02")
    with open(os.path.join(out13, "subject.skeleton.json")) as f:
        sk = json.load(f)
    # simulate the human pull filling the skeleton
    sk["characteristics"].update({"gla_sf": "1,700", "year_built": 1985,
                                  "bedrooms": 3, "full_baths": 2,
                                  "style": "Colonial", "property_type": "SFR"})
    sk["identifiers"]["apn"] = "777-000-1111"
    sk["assessment"].update({"tax_year": 2026, "total_value": 250000})
    sk["water"] = "Public"
    raw13 = os.path.join(out13, "filled.json")
    with open(raw13, "w") as f:
        json.dump(sk, f)
    subj13, _ = ingest(sk, resolved_on="2026-07-02", source="APEX pull")
    sj_path = os.path.join(out13, "subject.json")
    with open(sj_path, "w") as f:
        json.dump(subj13, f)
    put(subj13["address"]["full"], subj13, "APEX pull", db_path=DB,
        put_at="2026-07-02T15:00:00")
    # second order on the same subject -> HIT, no pull sheet
    out13b = os.path.join(TMP, "order13b")
    resolve("777 Pipeline Way, Henrico, VA 23229", county="Henrico",
            out_dir=out13b, db_path=DB, as_of="2026-07-02", order_id="T-13b")
    assert os.path.exists(os.path.join(out13b, "subject.json"))
    assert not os.path.exists(os.path.join(out13b, "pull-sheet.md"))
    # assemble (empty comps) + render — the whole chain holds
    empty_csv = os.path.join(out13, "comps.csv")
    with open(empty_csv, "w", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["Distance", "#", "ML #", "PID", "Status", "Address",
                    "Total Finished Area", "MLS"])
    rec = assemble(sj_path, empty_csv, os.path.join(out13, "record.json"),
                   generated_at="2026-07-02T15:00:00Z")
    html13 = render(rec)
    assert audit_comp_tax_ids(rec, html13) == []
    assert "777 Pipeline Way" in html13
    assert "1,700 sf" in html13 and "Colonial" in html13
    assert "Public" in html13                                  # water passthrough
    assert "TBD — verify at inspection" in html13              # sewer still TBD
    ok("C13: e2e — miss->fill->ingest->cache->hit->assemble->render, gates green")
except Exception as ex:
    fail("C13", str(ex))

# ---------------------------------------------------------------------------
# C14: ArcGIS adapter — canned-fixture mapping, no network, loud failures
# ---------------------------------------------------------------------------
try:
    from fetch_arcgis import (query_layer, map_features, apply_to_skeleton,
                              FetchError, FIELD_MAPS)
    canned = {"features": [{"attributes": {
        "SITEADDRESS": "9400 SAMPLE TRACE DR",
        "TAXID": "770-68-91-23-456", "LEGALDESC": "SAMPLE TRACE SEC A LT 9",
        "YEARBUILT": 1998, "ACREAGE": 0.31, "ZONING": "R-9",
        "TOTALVALUE": 315000, "SUBDIVISION": None,
    }}]}
    mapped, missing = map_features("Chesterfield", canned)
    assert mapped["identifiers.apn"] == "770-68-91-23-456"
    assert mapped["characteristics.year_built"] == 1998
    assert "SUBDIVISION" in missing                    # null attr -> pull manually
    # merge fills nulls only, never overwrites, flags the pull as unverified
    sk = {"identifiers": {"apn": None, "legal_description": "KEEP ME"},
          "characteristics": {"year_built": None}, "flags": []}
    filled, set_paths = apply_to_skeleton(sk, mapped, "Chesterfield")
    assert filled["identifiers"]["apn"] == "770-68-91-23-456"
    assert filled["identifiers"]["legal_description"] == "KEEP ME"
    assert "identifiers.legal_description" not in set_paths
    assert any("FIELD MAP UNVERIFIED" in f for f in filled["flags"])
    assert sk["identifiers"]["apn"] is None            # input not mutated
    # 0 rows / >1 rows / all-attrs-missing all raise (never auto-pick)
    for bad in ({"features": []},
                {"features": [{"attributes": {}}, {"attributes": {}}]},
                {"features": [{"attributes": {"UNRELATED": 1}}]}):
        try:
            map_features("Chesterfield", bad)
            raise AssertionError("bad response did not raise: " + str(bad))
        except FetchError:
            pass
    # network failure path via injected opener -> FetchError, nothing written
    def dead_opener(url):
        raise OSError("no route to host")
    try:
        query_layer("Chesterfield", "1 X St", opener=dead_opener)
        raise AssertionError("dead opener did not raise")
    except FetchError as e:
        assert "manual pull sheet" in str(e)
    # server-side error payload also raises
    def err_opener(url):
        return json.dumps({"error": {"code": 400, "message": "Invalid query"}})
    try:
        query_layer("Chesterfield", "1 X St", opener=err_opener)
        raise AssertionError("server error did not raise")
    except FetchError:
        pass
    assert all("layer_url" in v and "attrs" in v for v in FIELD_MAPS.values())
    ok("C14: ArcGIS — canned mapping, fill-nulls-only, unverified flag, loud failures")
except Exception as ex:
    fail("C14", str(ex))

# ---------------------------------------------------------------------------
# C15: run-log — resolver writes it (MISS + HIT variants), ingest ticks step 3
# ---------------------------------------------------------------------------
try:
    from ingest_subject import main as ingest_main
    out15 = os.path.join(TMP, "order15")
    resolve("42 Runlog Rd, Henrico, VA 23229", county="Henrico", out_dir=out15,
            db_path=DB, as_of="2026-07-02", order_id="T-15")
    rl_path = os.path.join(out15, "run-log.md")
    with open(rl_path, encoding="utf-8") as f:
        rl = f.read()
    assert "order T-15" in rl
    assert "- [x] 1. resolve_subject — MISS @ 2026-07-02" in rl
    assert "- [ ] 2. pull sheet executed" in rl
    assert "- [ ] 3. ingest_subject" in rl and "- [ ] 6. render_worksheet" in rl
    # ingest ticks its own box
    sk15 = os.path.join(out15, "subject.skeleton.json")
    rc = ingest_main([sk15, "--out", os.path.join(out15, "subject.json"),
                      "--db", DB, "--resolved-on", "2026-07-02",
                      "--source", "APEX pull", "--as-of", "2026-07-02"])
    assert rc == 0
    with open(rl_path, encoding="utf-8") as f:
        rl2 = f.read()
    assert "- [x] 3. ingest_subject — subject.json written + cached @ 2026-07-02" in rl2
    assert "- [ ] 3." not in rl2 and "- [ ] 4." in rl2       # only its own box
    # HIT variant: steps 1-3 pre-ticked, re-verify wording present
    out15b = os.path.join(TMP, "order15b")
    resolve("42 Runlog Road, Henrico County, VA 23229", county="Henrico",
            out_dir=out15b, db_path=DB, as_of="2026-07-02")
    with open(os.path.join(out15b, "run-log.md"), encoding="utf-8") as f:
        rlh = f.read()
    assert "- [x] 1. resolve_subject — CACHE HIT @ 2026-07-02" in rlh
    assert "RE-VERIFY" in rlh and "- [x] 3. ingest — n/a" in rlh
    assert "- [ ] 4." in rlh and "- [ ] 6." in rlh           # human steps stay open
    ok("C15: run-log — MISS/HIT variants, ingest ticks only step 3, human steps stay open")
except Exception as ex:
    fail("C15", str(ex))

# ---------------------------------------------------------------------------
# C16: provenance gate — ingest without a pull-sheet sibling flags the subject
# ---------------------------------------------------------------------------
try:
    lone_dir = os.path.join(TMP, "order16_lone")
    os.makedirs(lone_dir, exist_ok=True)
    lone_raw = os.path.join(lone_dir, "handmade.json")
    with open(lone_raw, "w") as f:
        json.dump({"address": {"full": "5 Rogue St, Henrico, VA 23229",
                               "county": "Henrico"},
                   "characteristics": {"gla_sf": 1500}}, f)
    rc = ingest_main([lone_raw, "--out", os.path.join(lone_dir, "subject.json"),
                      "--db", DB, "--resolved-on", "2026-07-02", "--source", "hand"])
    assert rc == 0                                            # warn, never block
    with open(os.path.join(lone_dir, "subject.json")) as f:
        rogue = json.load(f)
    assert any("standard work not verified" in fl for fl in rogue["flags"]), rogue["flags"]
    # the standard path (order15: pull-sheet present) must NOT carry the flag
    with open(os.path.join(TMP, "order15", "subject.json")) as f:
        clean = json.load(f)
    assert not any("standard work not verified" in fl for fl in clean["flags"]), clean["flags"]
    ok("C16: provenance — pull-sheet-less ingest flags + warns (rc 0); standard path clean")
except Exception as ex:
    fail("C16", str(ex))

# ---------------------------------------------------------------------------
# C17: add_county — all-or-nothing add to registry + routing together
# ---------------------------------------------------------------------------
try:
    import shutil
    from add_county import main as addc_main
    reg_src = os.path.join(REPO, "skills", "property-search", "references",
                           "county-registry.md")
    rt_src = os.path.join(HERE, "county_routing.json")
    reg_t = os.path.join(TMP, "registry.md")
    rt_t = os.path.join(TMP, "routing.json")
    shutil.copy(reg_src, reg_t)
    shutil.copy(rt_src, rt_t)

    rc = addc_main(["--jurisdiction", "Halifax", "--vendor", "qPublic",
                    "--sor-url", "https://qpublic.example/halifax",
                    "--technique", "address search; tax card on parcel page",
                    "--mls", "CVR-Matrix", "--mls", "Navica",
                    "--surrounding", "Mecklenburg,Charlotte",
                    "--registry", reg_t, "--routing", rt_t])
    assert rc == 0
    with open(reg_t, encoding="utf-8") as f:
        reg_after = f.read()
    assert "| Halifax | qPublic" in reg_after
    ext_pos = reg_after.index("## Extended coverage")
    assert reg_after.index("| Halifax |") > ext_pos, "row landed outside Extended coverage"
    routing_t = load_routing(rt_t)
    assert "Halifax" in routing_t and routing_t["Halifax"]["gas_key"] == "Halifax County"
    assert find_county(routing_t, "Halifax County", "x")[0] == "Halifax"
    assert "Mecklenburg" in routing_t["Halifax"]["surrounding_counties"]

    # duplicate -> refused, BOTH files untouched
    with open(rt_t, "rb") as f:
        rt_bytes = f.read()
    rc2 = addc_main(["--jurisdiction", "Henrico", "--vendor", "X",
                     "--sor-url", "u", "--technique", "t", "--mls", "M",
                     "--registry", reg_t, "--routing", rt_t])
    assert rc2 == 2
    with open(rt_t, "rb") as f:
        assert f.read() == rt_bytes, "routing changed on a refused add"

    # missing routing file -> refused, registry untouched
    with open(reg_t, "rb") as f:
        reg_bytes = f.read()
    rc3 = addc_main(["--jurisdiction", "Nottoway", "--vendor", "X",
                     "--sor-url", "u", "--technique", "t", "--mls", "M",
                     "--registry", reg_t,
                     "--routing", os.path.join(TMP, "nope.json")])
    assert rc3 == 2
    with open(reg_t, "rb") as f:
        assert f.read() == reg_bytes, "registry changed on a refused add"
    ok("C17: add_county — both files together; duplicates + missing-file refused untouched")
except Exception as ex:
    fail("C17", str(ex))

# ---------------------------------------------------------------------------
# C18: BD2 variance matrix — supported / unsupported / missing-source / zillow
# ---------------------------------------------------------------------------
try:
    base18 = {"address": {"full": "8 Variance Way, Henrico, VA 23229",
                          "county": "Henrico"},
              "characteristics": {}}

    # (a) disagree + justification -> MLS governs WITH the reason, triage flag
    a = dict(base18, source_values={"gla_sf": {"county": 1856, "mls": 2256}},
             variance_notes={"gla_sf": "MLS includes the 400sf finished basement per remarks"})
    s, f = ingest(json.loads(json.dumps(a)), resolved_on="2026-07-02")
    assert s["characteristics"]["gla_sf"] == 2256
    row = s["verification"][0]
    assert row["governing_source"] == "mls (justified)"
    assert "variance SUPPORTED" in row["flag"] and "finished basement" in row["flag"]
    assert any("manual triage" in fl for fl in f)             # header chip too

    # (b) disagree, no justification -> County rules, triage flag
    b = dict(base18, source_values={"gla_sf": {"county": 1856, "mls": 2256}})
    s, f = ingest(json.loads(json.dumps(b)), resolved_on="2026-07-02")
    assert s["characteristics"]["gla_sf"] == 1856
    assert s["verification"][0]["governing_source"] == "county"
    assert "County rules" in s["verification"][0]["flag"]
    assert any("manual triage" in fl for fl in f)

    # (c) agree within tolerance -> county governs quietly
    c = dict(base18, source_values={"gla_sf": {"county": 1856, "mls": 1850}})
    s, f = ingest(json.loads(json.dumps(c)), resolved_on="2026-07-02")
    assert s["verification"][0]["flag"] is None
    assert not any("manual triage" in fl for fl in f)

    # (d) exact-tolerance field: year built off by one = triage
    d = dict(base18, source_values={"year_built": {"county": 1972, "mls": 1973}})
    s, f = ingest(json.loads(json.dumps(d)), resolved_on="2026-07-02")
    assert s["characteristics"]["year_built"] == 1972
    assert "manual triage" in s["verification"][0]["flag"]

    # (e) county missing -> MLS governs with a verify note (no triage)
    e18 = dict(base18, source_values={"bedrooms": {"mls": 3}})
    s, f = ingest(json.loads(json.dumps(e18)), resolved_on="2026-07-02")
    assert s["characteristics"]["bedrooms"] == 3
    assert s["verification"][0]["governing_source"] == "mls"
    assert "verify" in s["verification"][0]["flag"] and "triage" not in s["verification"][0]["flag"]

    # (f) Zillow-only -> weakest-source note; Zillow lone disagreement stays informational
    f18 = dict(base18, source_values={"lot_size_acres": {"zillow": 0.25}})
    s, _ = ingest(json.loads(json.dumps(f18)), resolved_on="2026-07-02")
    assert s["verification"][0]["governing_source"] == "zillow"
    assert "weakest source" in s["verification"][0]["flag"]
    g18 = dict(base18, source_values={"gla_sf": {"county": 1856, "mls": 1856, "zillow": 2100}})
    s, f = ingest(json.loads(json.dumps(g18)), resolved_on="2026-07-02")
    assert s["characteristics"]["gla_sf"] == 1856
    assert "informational" in s["verification"][0]["flag"]
    assert not any("manual triage" in fl for fl in f)

    # (g) canonical 2.1 baths still gets the Matrix split downstream
    h18 = dict(base18, source_values={"full_baths": {"county": 2.1}})
    s, f = ingest(json.loads(json.dumps(h18)), resolved_on="2026-07-02")
    assert s["characteristics"]["full_baths"] == 2 and s["characteristics"]["half_baths"] == 1

    # (h) helper blocks never reach the output
    assert "source_values" not in s and "variance_notes" not in s
    ok("C18: variance matrix — supported/unsupported/agree/exact/missing/zillow/split/strip")
except Exception as ex:
    fail("C18", str(ex))

# ---------------------------------------------------------------------------
# C19: BD2 resolver — pull order, helper seeds, e2e triage chip on the worksheet
# ---------------------------------------------------------------------------
try:
    out19 = os.path.join(TMP, "order19")
    resolve("15 Triage Ter, Henrico, VA 23229", county="Henrico", out_dir=out19,
            db_path=DB, as_of="2026-07-02", order_id="T-19",
            effective_date="2026-07-02")
    with open(os.path.join(out19, "pull-sheet.md"), encoding="utf-8") as f:
        ps19 = f.read()
    assert (ps19.index("Source 1 — MLS") < ps19.index("Source 2 — county SOR")
            < ps19.index("Source 3 — Zillow") < ps19.index("Source 4 — gas")), \
        "pull order is not MLS -> County -> Zillow -> gas"
    assert "Variance protocol" in ps19 and "variance_notes" in ps19
    assert "NEVER silently pick a value" in ps19
    with open(os.path.join(out19, "subject.skeleton.json")) as f:
        sk19 = json.load(f)
    assert set(sk19["source_values"]) == {"gla_sf", "year_built", "lot_size_acres",
                                          "bedrooms", "full_baths", "stories"}
    assert sk19["source_values"]["gla_sf"] == {"mls": None, "county": None, "zillow": None}
    assert sk19["variance_notes"] == {}
    with open(os.path.join(out19, "run-log.md"), encoding="utf-8") as f:
        assert "MLS → SOR → Zillow" in f.read()

    # e2e: unsupported variance -> triage chip visible on the rendered worksheet
    sk19["characteristics"].update({"property_type": "SFR", "style": "Ranch"})
    sk19["source_values"]["gla_sf"] = {"mls": 2256, "county": 1856, "zillow": None}
    sk19["identifiers"]["apn"] = "191-919-1919"
    subj19, f19 = ingest(sk19, resolved_on="2026-07-02")
    assert subj19["characteristics"]["gla_sf"] == 1856      # County rules
    assert "source_values" not in subj19
    sj19 = os.path.join(out19, "subject.json")
    with open(sj19, "w") as f:
        json.dump(subj19, f)
    empty19 = os.path.join(out19, "comps.csv")
    with open(empty19, "w", newline="") as f:
        _csv.writer(f).writerow(["Distance", "#", "ML #", "PID", "Status",
                                 "Address", "Total Finished Area", "MLS"])
    rec19 = assemble(sj19, empty19, os.path.join(out19, "record.json"),
                     generated_at="2026-07-02T18:00:00Z")
    html19 = render(rec19)
    assert "manual triage" in html19, "triage chip missing from the worksheet"
    assert "row-flagged" in html19                           # verification row highlighted
    assert "1,856" in html19 and "2,256" in html19           # both values visible
    ok("C19: pull order + seeds + e2e — County ruled, triage chip renders, both values shown")
except Exception as ex:
    fail("C19", str(ex))

# ---------------------------------------------------------------------------
# C20: BD3 prior-work recall wired into the resolver (assist, never a gate)
# ---------------------------------------------------------------------------
try:
    import csv as _csv20
    sys.path.insert(0, os.path.join(REPO, "tools", "comp-history"))
    from comp_history import build as hist_build
    hops = os.path.join(TMP, "hist_ops.csv")
    with open(hops, "w", newline="", encoding="utf-8") as f:
        w = _csv20.writer(f)
        w.writerow(["1/15/2026", "900001", "Class", "40 Recall Rd", "23229", "1004",
                    "1/19/2026", "$350", "$0", "$350", "$305,000", "Paid and Xfered",
                    "", "", "", "", "1", "1"])
    hcorpus = os.path.join(TMP, "hist_corpus.json")
    with open(hcorpus, "w") as f:
        json.dump({"files": {"40 Recall Rd.dma": {
            "COUNTY": "Henrico", "PROPERTY_ZIP_CODE": "23229",
            "BLDG_ABOVE_GRADE_SQFT": "1800"}}}, f)
    hdb = os.path.join(TMP, "hist.sqlite")
    hist_build([hops], hcorpus, os.path.join(TMP, "no_dma_dir"), hdb)

    # MISS on the SAME street -> exact prior work lands on the pull sheet
    out20 = os.path.join(TMP, "order20")
    resolve("40 Recall Road, Henrico, VA 23229", county="Henrico", out_dir=out20,
            db_path=DB, as_of="2026-07-02", history_db=hdb)
    with open(os.path.join(out20, "pull-sheet.md"), encoding="utf-8") as f:
        ps20 = f.read()
    assert "Prior work (comp-history index)" in ps20
    assert "SAME PROPERTY appraised before" in ps20 and "40 Recall Rd" in ps20
    assert "CANDIDATES ONLY" in ps20 and "YV decides" in ps20

    # cache HIT path writes prior-work.md (uses the cached GLA for the band)
    put("41 Recall Rd, Henrico, VA 23229",
        dict(SUBJ, address={"full": "41 Recall Rd, Henrico, VA 23229",
                            "county": "Henrico"},
             characteristics={"gla_sf": 1810}),
        "test", db_path=DB, put_at="2026-06-01T09:00:00")
    out20b = os.path.join(TMP, "order20b")
    resolve("41 Recall Rd, Henrico, VA 23229", county="Henrico", out_dir=out20b,
            db_path=DB, as_of="2026-07-02", history_db=hdb)
    with open(os.path.join(out20b, "prior-work.md"), encoding="utf-8") as f:
        pw = f.read()
    assert "Similar within 12 mo" in pw and "40 Recall Rd" in pw  # 1800 vs 1810 in band

    # absent index -> notice, never a crash
    out20c = os.path.join(TMP, "order20c")
    resolve("42 Recall Rd, Henrico, VA 23229", county="Henrico", out_dir=out20c,
            db_path=DB, as_of="2026-07-02",
            history_db=os.path.join(TMP, "missing.sqlite"))
    with open(os.path.join(out20c, "pull-sheet.md"), encoding="utf-8") as f:
        assert "index not built" in f.read()
    ok("C20: recall — exact hit on pull sheet, similar via cached GLA, absent index safe")
except Exception as ex:
    fail("C20", str(ex))

# ---------------------------------------------------------------------------
# C21: backfill — host sweeps Cowork's --no-cache subject.json files into the cache
# ---------------------------------------------------------------------------
try:
    from subject_cache import backfill
    scan = os.path.join(TMP, "orders_scan")
    for name, subj21 in (
        ("orderA", {"address": {"full": "70 Backfill Ave, Henrico, VA 23229",
                                "county": "Henrico"},
                    "characteristics": {"gla_sf": 1400},
                    "resolution": {"resolved_on": "2026-07-04"}}),
        ("orderB", {"address": {"full": "71 Backfill Ave, Henrico, VA 23229",
                                "county": "Henrico"},
                    "resolution": {"resolved_on": None}}),          # undated
    ):
        d = os.path.join(scan, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "subject.json"), "w") as f:
            json.dump(subj21, f)
    s = backfill(scan, db_path=DB)
    assert s["put"] == 1 and s["skipped_undated"] == 1, s
    assert any("orderB" in u for u in s["undated_list"])
    hit = get("70 Backfill Avenue, Henrico County, VA 23229", db_path=DB)
    assert hit and hit[0]["characteristics"]["gla_sf"] == 1400
    s2 = backfill(scan, db_path=DB)                       # idempotent second sweep
    assert s2["put"] == 0 and s2["already_current"] == 1, s2
    ok("C21: backfill — validated file cached, undated listed not guessed, re-sweep idempotent")
except Exception as ex:
    fail("C21", str(ex))

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
