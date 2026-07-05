#!/usr/bin/env python3
"""
BD4 — minimal MCP stdio protocol shim (stdlib only).

Implements the TOOLS-ONLY subset of the Model Context Protocol over stdio:
newline-delimited JSON-RPC 2.0; handshake (initialize / notifications/initialized),
ping, tools/list, tools/call. Nothing else — by design (BD4 locked decision).

Separation contract: this module knows NOTHING about appraisal tools. `serve()`
takes a {name: {description, inputSchema, handler}} table; swapping this shim
for the official MCP SDK must touch only this file + the serve() call site.

SDK-migration triggers (pre-agreed 2026-07-04): resources/prompts needed ·
remote/HTTP transport needed · a Claude client drops rev 2024-11-05 ·
>15 tools or streaming results.

Wire discipline: stdout carries ONLY protocol JSON lines; every log/traceback
goes to stderr. A tool that printed to stdout would corrupt the channel — which
is exactly why server.py wraps print-heavy CLIs in subprocesses.
"""

import json
import sys
import traceback

PROTOCOL_VERSION = "2024-11-05"


class ToolError(Exception):
    """Raised by a tool handler: the message becomes the tool result text with
    isError=true (the model sees WHY, the call is not a protocol failure)."""


def serve(tools, server_name="appraisal-data", server_version="1.0.0",
          instream=None, outstream=None):
    """Blocking request loop. Returns on EOF. Streams injectable for QA."""
    fin = instream if instream is not None else sys.stdin
    fout = outstream if outstream is not None else sys.stdout

    def send(obj):
        fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fout.flush()

    def ok(mid, res):
        send({"jsonrpc": "2.0", "id": mid, "result": res})

    def err(mid, code, message):
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}})

    for line in fin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            err(None, -32700, "parse error: not a JSON line")
            continue
        mid = msg.get("id")
        method = msg.get("method")
        is_notification = "id" not in msg
        try:
            if method == "initialize":
                ok(mid, {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": server_name, "version": server_version},
                })
            elif method == "notifications/initialized":
                pass                                    # ack-less by spec
            elif method == "ping":
                if not is_notification:
                    ok(mid, {})
            elif method == "tools/list":
                ok(mid, {"tools": [
                    {"name": n, "description": t["description"],
                     "inputSchema": t["inputSchema"]}
                    for n, t in tools.items()]})
            elif method == "tools/call":
                params = msg.get("params") or {}
                name = params.get("name")
                if name not in tools:
                    err(mid, -32602, "unknown tool: {!r}".format(name))
                    continue
                try:
                    text = tools[name]["handler"](params.get("arguments") or {})
                    ok(mid, {"content": [{"type": "text", "text": text}],
                             "isError": False})
                except ToolError as e:
                    ok(mid, {"content": [{"type": "text", "text": str(e)}],
                             "isError": True})
            elif is_notification:
                pass                                    # ignore unknown notifications
            else:
                err(mid, -32601, "method not found: " + str(method))
        except Exception as e:                          # never kill the loop
            sys.stderr.write("mcp_stdio internal error: {}\n{}".format(
                e, traceback.format_exc()))
            if not is_notification:
                err(mid, -32603, "internal error: {}".format(e))
