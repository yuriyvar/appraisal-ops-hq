# `appraisal-data` MCP server (BD4)

The VDV pipeline as callable tools over MCP stdio — the agent calls structured tools
instead of improvising, and every reply ends in a NEXT step (roadmap Track 4:
"discipline with teeth").

## Architecture (locked decision 2026-07-04)
**Bare stdlib.** `mcp_stdio.py` = a ~200-line newline-delimited JSON-RPC shim
implementing the TOOLS-ONLY subset (initialize/initialized/ping/tools list+call,
protocol rev 2024-11-05), fully separated from `server.py` (the tool table).
**SDK-migration triggers (any one ⇒ swap the shim for the official SDK, touch nothing
else):** resources/prompts needed · remote/HTTP transport · a client drops our protocol
rev · >15 tools or streaming.

Wire discipline: **stdout carries only protocol JSON** — print-heavy pipeline CLIs run
as subprocesses (resolve/ingest/cache/arcgis/add_county); pure functions import directly
(gas/routing/comp-history). The cache WRITE path stays `ingest_subject.py` only — there
is deliberately no cache-put tool.

## Tools
resolve_subject · ingest_subject · cache_lookup (read-only) · gas_lookup · county_route ·
comp_history_search · arcgis_fetch (Chesterfield/Hanover, unverified field maps) ·
add_county (registry+routing together). Failures return `isError:true` WITH the full
output — the caller always sees why.

## Registration
- **Code lane:** `C:\Users\yuriy\VDV Appraisals\.mcp.json` (outer root — same discovery
  rule as slash commands; servers load at session START, so a new session is needed
  after registration).
- **Cowork lane (Ton):** YV adds the same command/args in the Cowork/desktop MCP config
  when ready.

## Live-verify checklist (run in the FIRST session after registration)
1. Tools visible? (`mcp__appraisal-data__*` in the tool list)
2. `county_route` Mecklenburg → ConciseCAMA + both-accounts warning
3. `gas_lookup` Mecklenburg → CONFIRMED no SCC gas
4. `cache_lookup` any address → HIT/MISS text
5. `comp_history_search` a known past subject → prior work found
6. `resolve_subject` a synthetic address + temp out_dir → skeleton/pull-sheet/run-log
7. `county_route` Narnia → isError with the coverage list
Tick the brief's LIVE VERIFY box + note results in the handoff.

## QA
`python mcp/appraisal-data/tests_mcp.py` — M1 shim transcript (in-memory streams),
M2 server e2e (real subprocess over stdin, temp DBs, stdout-purity assert).
