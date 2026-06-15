# Condition profiles — model & provenance

Reusable **default field-value sets** for a subject (and the comp Quality/Condition
columns), keyed by **form** and **condition tier**. The appraiser picks the tier that
matches what they see, drops the defaults into the worksheet / DataMaster, then edits
to the actual property. **These are starting points, not findings** — the licensed
appraiser verifies at inspection and certifies. Never ship a profile value unedited
where the real property differs.

## Tiers
- **new** — recently built or fully renovated; no deferred maintenance.
- **average** — well maintained, typical for the neighborhood; the VDV default.
- **fair** — dated finishes + deferred maintenance (worn flooring, aged systems).

## Rating systems (differ by form)
- **UAD** (1004, 2055, 1073): Quality = `Q1`–`Q6`, Condition = `C1`–`C6`, and feature
  descriptions use the `material/rating` convention, e.g. `Drywall/Avg`, `Vinyl/New`,
  `Comp/Avg`. Rating tokens seen in VDV reports: `/New`, `/Avg`. (`/Fair`, `/Poor` are
  **not** in the corpus — see provenance.)
- **words** (gPAR): no Q/C codes — Quality and Condition are words (`Good`, `Average`,
  `Fair`, `Poor`); features read `material/Average` or plain narrative.

## YAML shape
```yaml
form: "1004"
rating_system: "UAD"        # or "words"
default_tier: "average"
quality_note: >             # quality is construction GRADE, independent of wear
  Quality reflects how the home was built, not its current condition. It usually
  stays constant across tiers; set it from construction grade, not age.
profiles:
  average:
    observed_in_corpus: true     # grounded in past VDV reports
    quality: "Q3"
    condition: "C3"
    effective_age_hint: "moderate; typical remaining economic life"
    exterior: { walls: "Vinyl/Avg", roof: "Comp/Avg", windows: "Vinyl/Avg", ... }
    interior: { floors: "Cpt,Vnl/Avg", walls: "Drywall/Avg", trim: "Wood/Avg", ... }
    condition_comment: "Average condition; well maintained; no significant deferred maintenance."
  new: { observed_in_corpus: true, ... }
  fair: { observed_in_corpus: false, ... }   # EXTRAPOLATED — flagged
```

## Provenance (genchi genbutsu — mined 2026-06-15 from `Past Reports`)
Counts are across all subject + comp rows in the 38 ACI/MISMO XML + 22 gPAR reports.

- **Quality:** Q3 ×144 · Q2 ×15 · Q4 ×14 · Q1 ×7. No Q5/Q6 — VDV's stock is
  predominantly Q3 average construction.
- **Condition:** C3 ×85 · C2 ×45 · C4 ×29 · C1 ×20 · **C5 ×1** · no C6.
- **Rating suffix:** `/Avg` ×326 · `/New` ×29. **No `/Fair` or `/Poor` anywhere.**
- **Exterior (modal):** Walls `Vinyl/Avg`; Roof `Comp/Avg`; Window `Vinyl/Avg`;
  Gutters `Alum/Avg`; Storm sash `Yes/Ins/Avg`; Foundation `Concrete/Avg`,`Block/Avg`,`Brick/Avg`; Doors `Wood/Avg`.
- **Interior (modal):** Floors `Cpt,Vnl/Avg`/`HW,Vinyl/Avg`; Walls `Drywall/Avg`;
  Trim `Wood/Avg`; Bath floors `Vinyl/Avg`/`Tile/Avg`; Bath wainscot `Fib/Avg`/`Tile/Avg`.
- **gPAR words:** average ×200 · good ×121 · fair ×22 · poor ×17; condition narrative
  words `dated` ×45, `updated` ×39.

### What is grounded vs. extrapolated
- **average** and **new** values are taken from the observed modal vocabulary above
  (`observed_in_corpus: true`).
- **fair** values are **extrapolated** from UAD convention (swap rating → `/Fair`,
  Condition → `C5`) because VDV's past reports contain essentially no fair/worn
  properties. Marked `observed_in_corpus: false`. Treat as a scaffold; the appraiser
  itemizes the actual C5 deficiencies.
- **1073 (condo):** the corpus has **no 1073 XML** (condo reports were PDF-only), so the
  whole 1073 set is extrapolated from UAD convention + condo PDFs. Marked accordingly.

## How the appraiser uses a profile
1. Pick the form's YAML and the tier matching the property.
2. Paste the defaults into the Subject worksheet / DataMaster Improvements section,
   and the `Q?`/`C?` into the comp grid Quality/Condition rows.
3. **Edit every value to the real property** — change materials, fix the rating,
   itemize deficiencies. The profile saves typing, not judgment.
4. For **fair**, expect to write specific C5 deferred-maintenance items (the canned
   text is deliberately generic).

Related: `skills/notes-composer` (narrative for the condition comment),
`references/field-map/field-map.<form>.yaml` (where each value lands on the form),
`tools/dm-collection-sheet/` (the blank worksheet these fill).
