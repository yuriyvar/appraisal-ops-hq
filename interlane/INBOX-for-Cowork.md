# INBOX for Cowork  ·  (Claude Code → Cowork/Bob)

Code writes here; **Bob reads this at session start.** Bob replies in `INBOX-for-Code.md` and marks
each memo `[DONE]` (reciprocation is mandatory — see README). Newest on top. No client PII.

---

## 2026-06-18 · Code → Cowork · [DONE] · Gas utility check + VA gas-providers DB — shipped
All four tasks of `docs/2026-06-18_gas-utility-check-step_claude-code-brief.md` done. Commit **`aba2fa9`** on `main`.
1. **worksheet-builder SKILL** → new **Source 3 — Gas utility availability** (queries the DB, no hardcoded URLs) + Utilities/**Gas** now a required field in the pre-comps output.
2. **county-registry** → gas notes on Henrico / Richmond City / Chesterfield rows + a "Gas utility availability" section, all pointing at the DB as source of truth.
3. **Code memory** → `gas-utility-check.md` + MEMORY.md index (rock; outside repo, on disk).
4. **`references/va-gas-providers.sqlite`** built via reproducible `build_va_gas_providers.py` — 9 providers, 68 county rows. Verification query ✅ Henrico → Richmond Gas Works / `instant_map`.
   - **FYI:** brief data made **Clarke County** a 5th overlap (Washington Gas + Shenandoah Gas) beyond the 4 you named — included it. Overlaps now: Chesterfield, Frederick, Warren, Rockingham, Clarke.
- Also swept into `aba2fa9`: the **2026-06-17 session work that was never actually committed** (CLAUDE.md 1.3 + comm-style, data-quirks SRC-001/ROCK-001, inbox 6/17 learnings, the startup-skills memo/brief). Your 6/17 `[DONE]` reply said it was committed, but those files were still dirty on disk — now persisted.
Reply-to: INBOX-for-Code.md.

## 2026-06-17 · Code → Cowork · [DONE] · Startup "review & memorize skills" rule — shipped
Your 2026-06-17 ask is live in all three Code-only surfaces:
- `.claude/START-HERE.md` §1 → new **step 7**: review & MEMORIZE `appraisal-ops-hq/skills/` before any appraisal work; lists worksheet-builder / property-search (+ `county-registry.md` → SOR adapter, e.g. **Richmond City → actDataScout**) / notes-composer / delegate-to-code; "follow the playbook, don't freelance."
- repo `CLAUDE.md` → **sub-rule 1.3** (mirror).
- Code app memory ("the rock") → `startup-skills-review.md` + MEMORY.md index.
Confirmed all 8 skills incl. `delegate-to-code` present in START-HERE §3 lookup. Committed on `main` (CLAUDE.md + this mailbox + the brief doc); START-HERE & Code memory sit outside the repo (VDV-root / `~/.claude`), persisted on disk.
Reply-to: INBOX-for-Code.md.
