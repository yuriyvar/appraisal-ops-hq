---
sop: SOP-{{name}}
version: 0.1
effective: {{date}}
owner:
last-kaizen:        # date + kaizen item ID of the last change
andon-count: 0      # open andon flags against this SOP (reset on revision)
---

# SOP-{{name}} (v0.1)

**Purpose:** what outcome this standardizes, in one sentence.
**Trigger:** when this SOP starts.
**Takt expectation:** target time for the whole procedure.

## Steps
1. ...
2. ...

## Quality checks (jidoka)
- If X is missing/inconsistent -> STOP, file an andon (30-kaizen/templates/andon.md), do not work around silently.

## Change log
- v0.1 ({{date}}): initial standard.
