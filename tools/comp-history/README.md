# Comp-History Index (BD3)

Recalls prior VDV work when a new subject comes in: same property appraised before,
or a similar one (zip + GLA ±15%) within 12 months — surfaced as **CANDIDATES for YV**
on the resolver's pull sheet (`prior-work.md` on a cache hit). Never auto-selected.

## Sources → one `history` table (all read-only)
| Source | Gives | Join |
|---|---|---|
| Ops-sheet CSVs (2025/2026 tabs, gviz export → `Past Reports\_analysis\ops-history\`) | real order dates · form · status · appraised value · zip | squashed **street key** (shared canon with the subject cache: "117 S Main STREET" == "117S_MainSt") |
| `corpus_values_raw.json` (June .dma extraction, 113 files) | county · zip · GLA · year built · style · beds · APN · a flattened comp HINT | " |
| `C:\Users\yuriy\OneDrive\Documents\DataMaster\*.dma` | filename = subject street · mtime = APPROX report date (orphans only) | " |

Live build 2026-07-04: **572 ops rows + 113 corpus facts + 191 .dma files → 592 index rows**
(only 20 orphan .dma). PII (owner/seller/lender) is never indexed.

## Commands
```powershell
python tools/comp-history/comp_history.py build     # rebuild (idempotent; refetch the ops CSVs first when Chrome is up)
python tools/comp-history/comp_history.py search "<address>" --zip 23917 --gla 1500 --as-of 2026-07-04
```
DB: `C:\Users\yuriy\VDV Appraisals\Past Reports\_analysis\comp-history.sqlite` (client zone;
repo paths raise). The resolver queries it automatically — no extra step per order.

## Known limitation (quirk DMA-004)
Structured per-comp extraction from `.dma` is DEFERRED: the protobuf's value slots carry
unique IDs the schema names don't reference, and the June pairing script was never
committed. Until that reverse-engineering build: the index carries a one-comp HINT per
report; **open the `.dma` in DataMaster for the full comp grid** of a recalled report.
Comp close dates are never in the index — re-verify in the MLS (12-mo rule) always.

## Refresh ritual
Weekly `/review` (Phase 4): refetch the ops CSVs (gviz, logged-in Chrome) → `build`.
The .dma dir + corpus parts refresh in the same run automatically.
