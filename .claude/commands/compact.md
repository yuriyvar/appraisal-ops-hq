Perform an end-of-session compact. Do the following in order:

1. **Flush learnings** — scan this conversation for anything reusable (data-source quirks,
   client preferences, SOP gaps, failed steps, tool tricks). Append each as a one-liner
   to the TOP of `vault/00-inbox.md` (newest-first, under the `---` line), tagged
   [learn], [problem], [idea], [client], or [andon]. Skip anything already in the inbox.

2. **File andons** — if any standard work failed on a real order this session, create an
   andon entry using the template at `vault/30-kaizen/templates/andon.md`.

3. **Confirm** — reply with a bullet list of what was appended (or "nothing new to flush"
   if the inbox already has it all), then say: "Session compacted — safe to start a new
   conversation."

Note: Cowork has no context-window reset. Starting a new conversation is the only way
to actually shrink the context. This command just ensures nothing is lost before you do.
