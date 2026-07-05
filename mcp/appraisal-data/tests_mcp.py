#!/usr/bin/env python3
"""BD4 QA runner — MCP shim (in-memory) + server e2e (real subprocess over stdin)."""

import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from mcp_stdio import ToolError, serve, PROTOCOL_VERSION

results = []


def ok(name):
    results.append(("PASS", name))
    print("PASS  " + name)


def fail(name, reason):
    results.append(("FAIL", name, reason))
    print("FAIL  {} | {}".format(name, reason))


TMP = tempfile.mkdtemp(prefix="vdv_mcp_")


def drive_shim(tools, messages):
    """Run serve() over in-memory streams; return the decoded response lines."""
    fin = io.StringIO("\n".join(json.dumps(m) if isinstance(m, dict) else m
                                for m in messages) + "\n")
    fout = io.StringIO()
    serve(tools, instream=fin, outstream=fout)
    return [json.loads(l) for l in fout.getvalue().splitlines() if l.strip()]


# ---------------------------------------------------------------------------
# M1: shim — handshake, list, call, errors, notifications, purity
# ---------------------------------------------------------------------------
try:
    dummy = {"echo": {"description": "echo", "inputSchema": {"type": "object"},
                      "handler": lambda a: "you said " + str(a.get("msg"))},
             "boom": {"description": "always fails", "inputSchema": {"type": "object"},
                      "handler": lambda a: (_ for _ in ()).throw(ToolError("nope: bad input"))},
             "crash": {"description": "raises raw", "inputSchema": {"type": "object"},
                       "handler": lambda a: 1 / 0}}
    out = drive_shim(dummy, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "echo", "arguments": {"msg": "hi"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "boom", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "nosuch", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 6, "method": "wat/wat"},
        {"jsonrpc": "2.0", "method": "notifications/cancelled"},
        "this is not json",
        {"jsonrpc": "2.0", "id": 7, "method": "ping"},
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
         "params": {"name": "crash", "arguments": {}}},
    ])
    by_id = {o.get("id"): o for o in out}
    assert by_id[1]["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert by_id[1]["result"]["capabilities"] == {"tools": {}}
    assert [t["name"] for t in by_id[2]["result"]["tools"]] == ["echo", "boom", "crash"]
    r3 = by_id[3]["result"]
    assert r3["isError"] is False and r3["content"][0]["text"] == "you said hi"
    r4 = by_id[4]["result"]
    assert r4["isError"] is True and "nope: bad input" in r4["content"][0]["text"]
    assert by_id[5]["error"]["code"] == -32602
    assert by_id[6]["error"]["code"] == -32601
    assert any(o.get("error", {}).get("code") == -32700 for o in out)  # parse error
    assert by_id[7]["result"] == {}
    assert by_id[8]["error"]["code"] == -32603          # raw crash -> internal error
    # notifications never get responses; every line was valid JSON (drive_shim decoded)
    assert len(out) == 9, "expected 9 responses (2 notifications silent), got " + str(len(out))
    ok("M1: shim — handshake, list/call, isError, -32601/-32602/-32700/-32603, silence, purity")
except Exception as e:
    fail("M1", str(e))

# ---------------------------------------------------------------------------
# M2: server e2e — real subprocess, real tools, temp DBs; stdout purity
# ---------------------------------------------------------------------------
try:
    cache_db = os.path.join(TMP, "cache.sqlite")
    hist_db = os.path.join(TMP, "hist.sqlite")
    out_dir = os.path.join(TMP, "order_mcp")

    # seed a comp-history fixture through the real builder
    sys.path.insert(0, os.path.join(REPO, "tools", "comp-history"))
    import csv as _csv
    from comp_history import build as hist_build
    hops = os.path.join(TMP, "ops.csv")
    with open(hops, "w", newline="", encoding="utf-8") as f:
        _csv.writer(f).writerow(["1/15/2026", "1", "Class", "9 Mcp Way", "23229",
                                 "1004", "1/19/2026", "$1", "$0", "$1", "$300,000",
                                 "Paid and Xfered"] + [""] * 6)
    with open(os.path.join(TMP, "corpus.json"), "w") as f:
        json.dump({"files": {}}, f)
    hist_build([hops], os.path.join(TMP, "corpus.json"),
               os.path.join(TMP, "nodma"), hist_db)

    def call(i, name, args):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": name, "arguments": args}}

    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        call(3, "cache_lookup", {"address": "9 Nowhere Ct, Henrico, VA 23229",
                                 "cache_db": cache_db, "as_of": "2026-07-04"}),
        call(4, "county_route", {"county": "Mecklenburg"}),
        call(5, "gas_lookup", {"county": "Mecklenburg"}),
        call(6, "comp_history_search", {"address": "9 Mcp Way, Henrico, VA 23229",
                                        "zip": "23229", "as_of": "2026-07-04",
                                        "history_db": hist_db}),
        call(7, "resolve_subject", {"address": "9 Mcp Way, Henrico, VA 23229",
                                    "county": "Henrico", "out_dir": out_dir,
                                    "as_of": "2026-07-04", "cache_db": cache_db,
                                    "history_db": hist_db, "order_id": "MCP-1"}),
        call(8, "county_route", {"county": "Narnia"}),
        call(9, "gas_lookup", {}),
    ]
    payload = "\n".join(json.dumps(m) for m in msgs) + "\n"
    p = subprocess.run([sys.executable, os.path.join(HERE, "server.py")],
                       input=payload, capture_output=True, text=True, timeout=180)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    parsed = [json.loads(l) for l in lines]          # purity: every line is JSON
    by_id = {o.get("id"): o for o in parsed}

    assert by_id[1]["result"]["serverInfo"]["name"] == "appraisal-data"
    names = [t["name"] for t in by_id[2]["result"]["tools"]]
    assert len(names) == 8 and "resolve_subject" in names and "add_county" in names
    t3 = by_id[3]["result"]
    assert t3["isError"] is False and "MISS" in t3["content"][0]["text"]
    assert "run resolve_subject" in t3["content"][0]["text"]        # NEXT step present
    t4 = by_id[4]["result"]["content"][0]["text"]
    assert "ConciseCAMA" in t4 and "R57xxx" in t4
    t5 = by_id[5]["result"]["content"][0]["text"]
    assert "CONFIRMED no SCC gas" in t5
    t6 = by_id[6]["result"]["content"][0]["text"]
    assert "SAME PROPERTY" in t6 and "CANDIDATES" in t6
    t7 = by_id[7]["result"]
    assert t7["isError"] is False and "CACHE MISS" in t7["content"][0]["text"]
    assert os.path.isfile(os.path.join(out_dir, "pull-sheet.md"))
    assert os.path.isfile(os.path.join(out_dir, "run-log.md"))
    t8 = by_id[8]["result"]
    assert t8["isError"] is True and "Henrico" in t8["content"][0]["text"]  # coverage list
    t9 = by_id[9]["result"]
    assert t9["isError"] is True and "county is required" in t9["content"][0]["text"]
    ok("M2: server e2e — 8 tools listed; cache/route/gas/history/resolve live; "
       "errors isError=true; stdout pure JSON")
except Exception as e:
    fail("M2", str(e))

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
