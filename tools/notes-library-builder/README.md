# Notes-library + field-map build pipeline

Reproducible pipeline that turns past reports into the de-identified
`notes-composer` knowledge (library + playbook + field-map) and the pair-QA.

**Inputs (client zone, OUTSIDE the repo):** `Past Reports\` — ACI/MISMO XML exports,
gPAR PDFs, and the extraction produced into `Past Reports\_analysis\`.

## Steps (run with the VDV root mounted)
1. **Extract** adjustments + notes from XML → `_analysis/extraction.json`
   and gPAR PDFs → `_analysis/extraction_gpar.json`. (`extract_xml.py`, `extract_gpar.py`)
2. **De-identify** (the one-way gate):
   `python tools/deidentify/deidentify.py --in _analysis/extraction.json --out _analysis/_deid-staging --report`
   → review `_deid-staging/scrub_report.json` (human-mandatory) before promoting.
3. **Build library + playbook** from the de-identified notes + XML amounts:
   `python tools/notes-library-builder/build_notes.py --base "<VDV root>"`
   → writes `skills/notes-composer/references/notes-library/<form>/*.yaml`,
     `.../adjustment-playbook/playbook.yaml`, `_PROVENANCE.md`.
4. **Pair-QA** (validate extraction vs delivered PDFs):
   `python tools/pair-qa/pair_qa.py --base "<VDV root>"`
   → `_analysis/_pairs-qa/` (client zone — cites real values).

## Rules
- Client data NEVER enters the repo. Only de-identified library/playbook/field-map +
  counts-only provenance are committable. Raw extraction, de-id staging, and pair-QA
  stay in `Past Reports\_analysis\`.
- Amounts in the playbook come from **XML only**; gPAR corroborates features (its text
  parse is noisy). See ADR-003.
- The de-identify scrub diff must be human-reviewed before any promotion.
