---
name: kaizen-retro
description: Run the kaizen retrospective on the Ops Memory vault — analyze the kaizen log, andon flags, and metrics; perform 5-whys root cause analysis; and propose concrete versioned edits to SOPs with PDCA experiment plans. Use whenever the user says "run the retro", "kaizen", "sprint retro", "improve our SOPs", asks why a problem keeps recurring, or at the end of each sprint. This is the system's self-improvement engine — also suggest running it if andon flags or kaizen items have accumulated without a retro in 2+ weeks.
---

# Kaizen Retro

PDCA applied to the company's own standard work. Claude does the analysis and
drafting; a human approves every SOP change (the pull-cord stays human).

## Procedure
1. **Gather (Check):** read `vault/30-kaizen/kaizen-log.md`, all andon files in
   `vault/30-kaizen/`, and `vault/50-metrics/metrics.md`. Also check open PDCA records whose
   Check date has passed — report results FIRST (adopt / adjust / abandon).
2. **Prioritize:** rank open kaizen items by frequency x cost (rework minutes,
   revision requests, missed dates). Take the top 1-3 only. Small batches.
3. **Root cause:** for each, complete `vault/30-kaizen/templates/5-whys.md` with the human,
   citing real instances from notes/andons (genchi genbutsu — no speculation).
4. **Countermeasure (Plan):** draft the exact SOP diff — quote current step,
   proposed step, and the hypothesis ("this reduces X by Y"). Fill a
   `vault/30-kaizen/templates/pdca.md` record with a concrete Check date (typically 2 weeks /
   ~30-45 orders at current volume).
5. **Apply (Do), only after explicit human approval:**
   - Apply the diff, bump `version`, update `last-kaizen`, reset `andon-count`,
     append to the SOP's change log.
   - Mark kaizen items closed with links to the PDCA record.
6. **Close the loop:** append one inbox entry summarizing what changed, so the
   change itself enters organizational memory.

## Rules
- No SOP change without: a kaizen item + 5-whys + PDCA record with a Check date.
- Prefer changing the standard over adding inspection steps; prefer removing
  steps (muda) over adding them.
- If metrics worsen after a change, recommend reverting at Check — abandoning a
  failed experiment is a success of the system, say so explicitly.
- Max 3 SOP changes per retro. Stability between experiments is what makes the
  Check valid.
