<!-- build-plan: name=bd4-mcp-server status=done -->
# Code brief — BD4: MCP server `appraisal-data`

> Track 4 of the automation roadmap: the pipeline's tools become CALLABLE TOOLS with
> next-step returns — freeform browsing becomes the exception that stands out
> (Track 1's guardrail with teeth).

## Locked decision (YV delegated 2026-07-04, Code chose)
**Bare-stdlib stdio server.** Protocol shim (`mcp_stdio.py`, newline-delimited JSON-RPC,
tools-only subset, protocol rev 2024-11-05) lives SEPARATE from the tool functions
(`server.py`) — swapping the shim for the official SDK touches nothing else.
**SDK-migration triggers (any one ⇒ migrate):** need MCP resources/prompts · need
remote/HTTP transport · a Claude client drops our protocol rev · >15 tools or streaming.

## Progress tracker
- [x] Phase 0 — this brief committed
- [x] Phase 1 — `mcp_stdio.py` shim + in-memory transcript QA (initialize / initialized /
      ping / tools list+call / unknown-method −32601 / parse −32700 / notifications silent /
      stdout purity — stderr is the only log channel)
- [x] Phase 2 — `server.py`: 8 tools + subprocess-vs-import policy + e2e QA driving the real
      server over stdin with temp DBs (M1+M2 green first run)
- [x] Phase 3 — wrap: `.mcp.json` registered (outer root, new file) · README w/ live-verify
      checklist · inbox · interlane FYI · handoff · tag done + BD4 ticked
- [ ] **LIVE VERIFY (next session — servers load at session start): run the README checklist
      through the real client, then tick this box.** All phases otherwise DONE 2026-07-04.

## Tools (each returns text ending in a NEXT step)
| tool | wraps | how |
|---|---|---|
| resolve_subject | tools/subject-resolution/resolve_subject.py | subprocess (print-heavy) |
| ingest_subject | ingest_subject.py | subprocess |
| cache_lookup | subject_cache.py get (READ ONLY — put stays ingest-only) | subprocess, MISS exit 1 = ok |
| gas_lookup | resolve_subject.gas_lookup + routing | direct import (pure fn) |
| county_route | resolve_subject.find_county/load_routing | direct import |
| comp_history_search | comp_history.search/format_hits | direct import |
| arcgis_fetch | fetch_arcgis.py | subprocess; fallback exit 1 ⇒ isError=true (correct semantics) |
| add_county | add_county.py | subprocess; refusal exit 2 ⇒ isError=true |

## Locked constraints
1. **stdout is the wire** — the server never prints anything but protocol JSON lines;
   logs/tracebacks go to stderr. Subprocess wrapping (not import) for every CLI that prints.
2. The cache **write** path stays `ingest_subject.py` only — no cache-put tool.
3. Optional `cache_db` / `history_db` / `as_of` args pass through to the underlying CLIs
   (same test-injection pattern the QA runners use; defaults = client-zone paths).
4. Stdlib only (json/sys/subprocess). QA runners: existing 3 suites stay green + new
   `tests_mcp.py` (drives the server as a real subprocess over stdin — protocol e2e, no client).
5. Registration = `.mcp.json` at the OUTER root (`VDV Appraisals\` — same discovery lesson as
   the slash-command stubs); merge if one exists. Cowork-lane wiring = YV step (desktop config),
   documented in the README.

## Verify
```powershell
python "appraisal-ops-hq\mcp\appraisal-data\tests_mcp.py"                          # new suite green
python "appraisal-ops-hq\tools\subject-resolution\tests_subject_resolution.py"    # 20/20 intact
python "appraisal-ops-hq\tools\comp-history\tests_comp_history.py"                # 5/5 intact
```
