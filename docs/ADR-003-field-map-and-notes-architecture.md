# ADR-003: Field-map ("one mapping, multiple lenses") + notes-library architecture

Date: 2026-06-13 · Status: proposed (drafted this session; human to review/merge) · Extends ADR-002

## Context
We extracted 60 past VDV reports (38 ACI/MISMO 2.6 XML + 22 gPAR PDF) to learn (a)
how report fields map between the structured XML, the delivered PDF, and our
appraisal-record schema, and (b) VDV's reusable note phrasings and adjustment
magnitudes. ADR-002 already decided on "one structured appraisal record (JSON) →
rendered consumers" and a "swappable field-map (record→ACI field), kept as config
not code." This ADR records how that field-map and the notes knowledge are structured.

## Decision

### 1. One mapping, multiple lenses
The field map is a **single table keyed on the appraisal-record `record_path`**, with
a column per consumer: `mismo` (XML source), `pdf` (delivered report location),
`aci_web` (ACI web auto-fill selector — null until new ACI is live), `worksheet`
(Build A render tab/row). The XML→PDF mapping we built to QA the extraction **is** the
seed of the record→ACI field-map — same artifact, fill `aci_web` later. This prevents
two divergent mapping files; a DOM change becomes a data edit, not code.
Files: `skills/notes-composer/references/field-map/field-map.<form>.yaml` (+ `_model.md`).

### 2. Renderer code stays the source of truth for rendering
`render_worksheet.py` remains authoritative for *how* the worksheet renders. The
field-map's `worksheet` column **documents** that contract so drift is visible; the
renderer does **not** load the YAML yet. A later refactor may make the renderer
data-driven from the map once it's proven stable. Until then, two sources of truth are
avoided by making the YAML documentation-only.

### 3. Notes library = boilerplate skeleton + typed slots
Reusable phrasings live as YAML keyed on `(form_type, note_field)`, each variant tagged
`seen_count`/`confidence` and carrying a `template` with typed slots. `confidence` is
the anti-over-fit guard: high-count = safe boilerplate; judgment content stays a slot,
never canned. Consumed by the `notes-composer` skill at compose-time. The schema's
`adjustments.*` stays appraiser-entered; the **adjustment-playbook** is a *hint* surfaced
to the appraiser, cross-linked via `schema_feature`.

### 4. De-identification is the one-way gate into the repo
`tools/deidentify/deidentify.py` (strict + keep-locality) is the only path from the
client zone to the repo. It scrubs addresses, roads, MLS#, parcels, money, dates,
subdivisions → typed slots; keeps county/city, condition/quality codes, and adjustment
rates. It writes de-identified candidates to a **client-zone staging dir** for a
mandatory human scrub-diff review; it never writes into the repo. Raw extraction +
pair-QA reports (which cite real values) stay in `Past Reports\_analysis\` (client zone).

## Consequences
- New forms = new `field-map.<form>.yaml` + library folder, not code. 1073/FHA are
  scaffolded `unsupported — no samples` (no fabrication). 1025 needs a schema income
  block before real support.
- Growing the library on new orders is a repeatable pipeline: extract → deidentify →
  human-review diff → promote.
- The field-map doubles as documentation that QA's the renderer against real forms.

## Validation
FNM1004 `mismo`+`pdf` columns validated against the 3 URAR XML↔PDF pairs — pair-QA
shows **100% value match** (extraction is faithful). The gPAR pair (11597 leeds chapel)
also matched 100%, corroborating the gPAR text parse for values.

## Revisit when
1073/FHA samples arrive; 1025 volume justifies a schema income block; or the field-map
proves stable enough to make the renderer load it directly (collapse decision #2).

## Risks
gPAR text-parse is noisy → adjustment **amounts come from XML only**, gPAR corroborates
features. Notes over-fitting → `confidence`/slots. PII under-scrub → mandatory human
diff review before promotion (the single biggest boundary risk).
