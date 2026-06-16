# Interlane Comms — "the Cowork-Fixon"

A dedicated, **bidirectional memo channel between the two lanes** — Cowork/Bob ⇄ Claude Code.
Lives in the repo because both lanes can reach it (Cowork is locked out of `.claude/`).

This is NOT the same as:
- **Session-Handoffs** (`Operations/Session-Handoffs/` Cowork · `.claude/Session-Handoffs/` Code) — those are *per-lane cold-start resume* notes.
- **`vault/00-inbox.md`** — shared *learnings/kaizen* capture for the weekly review.
This channel is *directed messages between the agents*, with **mandatory reciprocation**.

## Two one-way inboxes (single writer each → no cross-lane same-file edits)
| File | Written by | Read by |
|---|---|---|
| `INBOX-for-Code.md` | **Cowork/Bob** | Claude Code |
| `INBOX-for-Cowork.md` | **Claude Code** | Cowork/Bob |

Each lane **WRITES only to the other lane's inbox** and **READS only its own**. One writer per file
means the lanes can never collide on the same file (the git-corruption pattern).

## Read at session start (non-negotiable)
Every session, first thing, reads the inbox addressed **to it**:
- Cowork/Bob → reads `INBOX-for-Cowork.md`
- Claude Code → reads `INBOX-for-Code.md`
(Wired into the bootstrap: START-HERE for Code; the Cowork prep flow / START-HERE lookup for Bob.)

## Memo format
```
## <YYYY-MM-DD> · <from> → <to> · [OPEN] · <short title>
<the ask, in 1–3 lines. Link the detailed work order if any, e.g. docs/<date>_<slug>-brief.md>
Reply-to: INBOX-for-<sender>.md
```

## Reciprocation — MUST
When you act on a memo addressed to you:
1. Post a short reply to the **sender's** inbox (status + result, e.g. commit hash / "done" / blocker).
2. Mark the original memo `[DONE]` (or move it to `archive/`).
**No silent consumption.** An unacknowledged memo is treated as still open.

## Cadence — how the exchange stays bidirectional WITHOUT a reminder
Each lane's **Session-Handoff IS its digest**; this mailbox carries directed action items + a short FYI
pointer to that handoff. Keep both lanes honest with an entry + exit ritual, encoded in the bootstrap
each agent always reads (START-HERE / CLAUDE.md):
- **Entry (first actions, every session):** read (a) your own inbox here and (b) the OTHER lane's
  latest handoff. Clear/reply to open memos before starting new work.
- **Exit (last action, every hand-off):** write your lane's handoff (the digest) AND drop a one-line
  `[FYI]` pointer on the other lane's rock; reply to any memo you consumed and mark it `[DONE]`.
- **Forcing function (a miss is loud, not silent):** on entry, if the other lane shows fresh activity
  (new commit / handoff) but left no digest/FYI for you → flag "<lane> went dark — chase it." Any
  unanswered `[OPEN]` memo resurfaces every entry as a standing obligation.
- **Honest limit:** nothing forces a write an aborted/crashed session skipped — the guarantee is
  *detection on next entry*, not that the write always happened. Code can harden its side with a git
  stop/commit hook; Cowork relies on the bootstrap instruction + Yuriy's "hand off" cue.

## Rules
- **No client/order PII** in memos (repo rule). Detailed work orders live as `docs/*-brief.md`; the memo
  is the short notice + path.
- Keep memos append-only and dated; don't rewrite the other lane's text.
- This channel supersedes ad-hoc `[andon→Code]` pointers previously dropped in `vault/00-inbox.md`.
- The `delegate-to-code` skill posts Cowork→Code memos here.
