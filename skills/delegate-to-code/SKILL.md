---
name: delegate-to-code
description: Use whenever Bob (Cowork) needs something done that Cowork CANNOT do or reach — git commits/branches/merges/push, writing or editing anything under `.claude/`, Claude Code's app-internal memory, SOP changes that need a kaizen branch, anything outside the connected folder, or any privileged/irreversible host operation. Do NOT attempt it, and do NOT work around the protection. Instead: write a Code brief FILE, log an inbox pointer, and produce a short copy-paste PROMPT (with the brief's path) for Yuriy to pass to Claude Code. Triggers — "Code needs to…", "commit this", "edit START-HERE", "merge the kaizen branch", "I can't write there", "that's host-only", or any "serious" task Cowork can't safely finish itself.
---

# Delegate-to-Code

Cowork/Bob and Claude Code are two lanes over the same repo. Some things are **structurally
Code-only**. When Bob hits one, the move is never to force it or route around the guardrail — it's to
**hand Code a clean, self-contained work order** and let Yuriy pass it over.

## Trigger — the "Cowork can't reach / shouldn't do" list
- **Git writes:** commit, branch, merge, push, stale-lock cleanup. (Host only.)
- **`.claude/` writes:** `START-HERE.md`, `Session-Handoffs/`, `commands/`, `settings*`. (Protected — read-only to Cowork.)
- **Claude Code's app-internal memory:** `~/.claude/projects/.../memory/*`. (Outside the connected folder.)
- **SOP changes** under `vault/20-standard-work/` — require a `kaizen/*` branch + human merge (Cowork can't branch).
- **Anything outside the connected folder**, or any **privileged / irreversible host op**.
- Rule of thumb: if it's "serious" and Bob can't safely + reversibly finish it in-sandbox → delegate.

## Procedure (3 steps — always all three)
1. **Write the brief file.** `appraisal-ops-hq/docs/<YYYY-MM-DD>_<slug>_claude-code-brief.md`.
   Make it self-contained: context, exact ordered steps, full file paths, and guardrails (kaizen
   branch for SOPs; one-session git rule; the 4-file lock cleanup; never circumvent a protection).
   **No client/order PII in the repo brief** (addresses-as-examples only, per CLAUDE.md).
2. **Post a memo to the interlane mailbox** — append to `interlane/INBOX-for-Code.md` (the
   Cowork→Code lane; Code reads it at session start). Format:
   `## <date> · Cowork → Code · [OPEN] · <title>` + the ask + the brief path + `Reply-to: INBOX-for-Cowork.md`.
   (Reciprocation: Code replies in `INBOX-for-Cowork.md` and marks the memo `[DONE]`.)
3. **Produce the prompt for Yuriy** — short, with the path; the brief carries the detail. Template:
   > Read `appraisal-ops-hq/docs/<file>` and execute it. It's a Code-only work order Bob staged
   > (git / `.claude/` / host ops Cowork can't reach). Follow its ordering and guardrails; stop where
   > it says a human merges.

## Never
- Never **circumvent a protection** to do it yourself (no shelling around `.claude`, git locks, or the
  human gate). The protection is the point.
- Never put **client/order PII** in the repo brief.
- Never have Code **submit or certify** an appraisal (USPAP human gate stands in both lanes).
- SOP edits: the brief tells Code to branch + **let a human merge** — Code doesn't merge to `main` itself.

## Related
- Memo channel: `interlane/` ("the Cowork-Fixon") — `INBOX-for-Code.md` (Bob→Code) / `INBOX-for-Cowork.md` (Code→Bob); see its README + reciprocation rule.
- Brief pattern lives in `docs/` (e.g. `2026-06-16_bootstrap-and-commit_claude-code-brief.md`).
- Two-lane handoffs: Cowork `Operations/Session-Handoffs/` · Code `.claude/Session-Handoffs/`.
- Discovery: this skill must be listed in `START-HERE.md`'s skills lookup so Bob triggers it (Code wires
  that — Cowork can't edit START-HERE). For global effect, Yuriy may also add a one-liner to Settings → Profile.
