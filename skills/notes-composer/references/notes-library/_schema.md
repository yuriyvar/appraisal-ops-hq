# Notes library — data model

Reusable appraiser-note phrasings mined from VDV past reports, **de-identified**
(via `tools/deidentify`), grouped by form type and note field. The model is
**boilerplate skeleton + typed slots**: most of each note repeats verbatim across
reports; the property-specific bits are slots to fill at compose-time.

## Layout
```
notes-library/
  _schema.md            (this file)
  _PROVENANCE.md        (counts only — no client identifiers)
  1004/                 (FNM1004 — 30 reports)
    addendum.yaml  neighborhood.yaml  market-1004mc.yaml  sales-comparison.yaml
    reconciliation.yaml  site-cost.yaml  property-analysis.yaml  prior-sale.yaml
    valuation-methods.yaml  other.yaml
  1004C/                (FNM1004C — 6 reports; manufactured-home deltas)
```

## Record shape (per note field)
```yaml
fields:
  - note_field: NEIGHBORHOOD._MarketConditionsDescription   # MISMO source field
    label: "Neighborhood market conditions"
    render_target: market.neighborhood_notes                # appraisal-record path it feeds
    seen_total: 30                                           # how many reports had this field
    variants:
      - id: MarketConditionsDescription-1
        seen_count: 30          # how many reports used THIS phrasing (verbatim, slot-normalized)
        confidence: high        # high >=10 · medium 3-9 · low <3 (low usually omitted)
        template: |
          There is an ample financing available through local lenders including
          FHA, VA, VHDA, conventional and loan assumption. ...
```

## Slot vocabulary (filled at compose-time)
`{date}` · `{money}` · `{road}` (named road) · `{route}` (Rt/Hwy number) ·
`{mls_number}` · `{parcel_id}` · `{subdivision}`. Locality (county/city) names and
condition/quality codes (C1-C6, Q1-Q6) are KEPT verbatim — they are not PII.

## How an agent uses it (compose-time)
1. Look up `(form_type, note_field)`.
2. Pick the highest-`confidence` variant (or the one whose context fits).
3. Fill the slots from the appraisal-record (address, dates, MLS#, market data).
4. **Never auto-emit a slot left unfilled, and never canned-fill a judgment.**
   Variants encode boilerplate; order-specific reasoning (e.g. "Comparable 1 given
   the most weight because…") is the appraiser's call — present it as a slot/prompt,
   not as fixed text. The licensed appraiser edits and certifies.

## Confidence & over-fitting guard
`seen_count` is the anti-over-fit signal: high-count variants are safe boilerplate;
low-count ones are one-offs and are generally excluded from the committed library.
Do not treat a high-count reconciliation/addendum template as a substitute for
case-specific judgment.
