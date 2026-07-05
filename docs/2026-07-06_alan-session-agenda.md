# Alan session — 1 hour (2026-07-__)

**Goal:** show what the automation already does, get Alan's 8 decisions, book the ACI hour.

## 0:00–0:10 · Where we are (demo, not slides)
Live on this PC since June: address in → cache/prior-work check → pull sheet (MLS→County→Zillow)
→ variance-checked subject record → DataMaster-ready worksheet (Neighborhood tab + snapshot).
572 past orders indexed — every new order auto-checks "have we appraised this or a neighbor?"
All tools callable by the AI agents in both lanes (MCP, live 7/06). GitHub-backed.

## 0:10–0:20 · Demo one order end-to-end
Pick a recent Chesterfield order: resolve → pull sheet → worksheet in the browser.
Show the fail-loud gates (no guessed GLA, TBD chips, manual-triage flags).

## 0:20–0:40 · Alan's decisions (the 6 standing + 2 new)
1. Output: HTML worksheet copy-paste first, or push ACI/MISMO direct ingestion?
2. DataMaster: long-term bridge to ACI, or bypass it eventually?
3. Navica: which boards/counties is it our SOR for? (287 creds still needed)
4. Luxury subjects: default GLA band +15% and bracket up — confirm?
5. Photo labeling: filename convention ACI should consume?
6. Registry: hybrid OK (Sheet/CSV source-of-truth + derived SQLite)?
7. **NEW — UAD 3.6 / ACI Sky Workbench:** what changes vs legacy forms (fields, dictionary,
   validation)? What does he want the worksheet to mirror?
8. **NEW — Desktop appraisals as volume play:** which products/forms/AMCs qualify? (no
   inspection = pure data assembly = exactly what the pipeline automates)

## 0:40–0:50 · Book the ACI selector hour
BD5 (auto-fill ACI web forms from the record — human reviews, never auto-submit) is blocked
on ONE ~1-hr session: Alan or YV logged into ACI Sky Workbench, walking the 1004 form while
Code captures field selectors. Get a date on the calendar.

## 0:50–1:00 · Housekeeping
- K-003 kaizen branch: 2-min review → merge (prep-ALL-WIP triage rule).
- What Alan wants next from the pipeline (his pain list → exploit backlog).

**Leave with:** 8 answers · ACI hour booked · K-003 merged.
