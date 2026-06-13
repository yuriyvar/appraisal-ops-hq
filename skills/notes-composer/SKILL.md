---
name: notes-composer
description: Compose appraiser narrative notes and suggest comp adjustments in VDV's own voice, learned from past reports. Use whenever the user is writing or revising the narrative sections of an appraisal — neighborhood description/boundaries/market conditions, site & improvement comments, sales-comparison comment, sales/transfer-history analysis, reconciliation summary, 1004MC market/concession notes, cost-approach comments, or the addendum — or asks "what adjustment should I use for X", "draft the reconciliation", "write the neighborhood narrative", "fill the comments", "1004MC notes". Pulls reusable phrasings from references/notes-library (by form type + note field) and typical adjustment magnitudes from references/adjustment-playbook. The appraiser edits and certifies — this drafts, it never finalizes.
---

# Notes Composer

Drafts the narrative + suggests adjustments the way VDV's past reports do, then
hands off to the licensed appraiser to edit and certify. Knowledge is **data, not
prose hardcoded here**: `references/notes-library/` (phrasings) and
`references/adjustment-playbook/playbook.yaml` (typical $).

## When composing a note
1. Identify the **form type** (1004, 1004C, 2055, 1025) and the **note field**
   needed (e.g. reconciliation summary, neighborhood market conditions).
2. Open `references/notes-library/<form>/<group>.yaml`, find the `note_field`,
   pick the highest-`confidence` variant (see `_schema.md`).
3. Fill the slots (`{date}`, `{money}`, `{road}`, `{mls_number}`, `{subdivision}`,
   …) from the appraisal-record / order data.
4. Replace any judgment placeholder with the appraiser's actual reasoning — never
   ship canned text where a case-specific call belongs (e.g. which comp got the
   most weight and why). Present those as prompts.
5. Output the draft for the appraiser to edit. **Never finalize or certify.**

## When suggesting an adjustment
1. Look up the feature in `references/adjustment-playbook/playbook.yaml`
   (`typical_abs_usd`, `range_abs_usd`, `common_abs_usd`, `forms`).
2. Offer it as a **hint** with the basis ("Condition typically ~$15k/step; GLA ~$75/sf").
   The appraisal-record keeps `adjustments.*` appraiser-entered — do not write final
   adjustments into the record; surface the hint for the appraiser.

## Rules
- **Draft, don't certify.** USPAP: the licensed appraiser is the final gate.
- **No client data in, no client data out.** The library is de-identified. If you
  ingest new past reports to grow it, they go through `tools/deidentify` first and a
  human reviews the scrub diff before anything is committed (one-way gate).
- **Respect confidence.** Prefer high-`seen_count` boilerplate; flag low-confidence.
- **Locality OK, street-level not.** County/city names are fine in drafts; specific
  addresses/MLS#/parcels come from the live order, not from the library.

## Provenance & coverage
Built from 38 XML reports (30× 1004, 6× 1004C, 1× 2055, 1× 1025) + 22 gPAR PDFs.
No 1073/FHA samples yet — those note sets are not covered. See
`references/notes-library/_PROVENANCE.md` and `references/field-map/_model.md`.
