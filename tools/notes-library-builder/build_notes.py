#!/usr/bin/env python3
"""Build the de-identified notes library + adjustment playbook into the repo skill.
Reads de-identified notes (gate already applied) + extraction.json (XML amounts).
Stdlib only, deterministic.

Usage: python build_notes.py --base "<VDV Appraisals root>" [--repo <repo root>]
"""
import json, os, re, collections, statistics, argparse, sys

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True, help="VDV Appraisals root (holds 'Past Reports' and 'appraisal-ops-hq')")
ap.add_argument("--repo", help="repo root (default: <base>/appraisal-ops-hq)")
A = ap.parse_args()
BASE = A.base
REPO = A.repo or os.path.join(BASE, "appraisal-ops-hq")
ANALYSIS = os.path.join(BASE, "Past Reports", "_analysis")
LIB = os.path.join(REPO, "skills/notes-composer/references/notes-library")
PLAY = os.path.join(REPO, "skills/notes-composer/references/adjustment-playbook")
for d in (LIB, PLAY): os.makedirs(d, exist_ok=True)

deid = json.load(open(os.path.join(ANALYSIS, "_deid-staging/notes_deidentified.json"), encoding="utf-8"))
raw = json.load(open(os.path.join(ANALYSIS, "extraction.json"), encoding="utf-8"))
FORM_LABEL = {"FNM1004":"1004","FNM1004C":"1004C","FNM2055":"2055","FNM1025":"1025"}
FIELD_MAP = {
 "FORM.AppraisalAddendumText": ("addendum","Addendum narrative","(addendum / multiple)"),
 "NEIGHBORHOOD._Description": ("neighborhood","Neighborhood description","market.neighborhood_notes"),
 "NEIGHBORHOOD._BoundaryAndCharacteristicsDescription": ("neighborhood","Neighborhood boundaries","market.neighborhood_notes"),
 "NEIGHBORHOOD_BOUNDARIES.GSENeighborhoodBoundariesDescription": ("neighborhood","Neighborhood boundaries (GSE)","market.neighborhood_notes"),
 "NEIGHBORHOOD._MarketConditionsDescription": ("neighborhood","Neighborhood market conditions","market.neighborhood_notes"),
 "MARKET.MarketTrendsReconciliationComment": ("market-1004mc","1004MC trends reconciliation","market.neighborhood_notes"),
 "MARKET.NeighborhoodMarketabilityFactorsDescription": ("market-1004mc","1004MC distressed-sales note","market.neighborhood_notes"),
 "MARKET.SalesConcessionDescription": ("market-1004mc","1004MC concessions note","market.neighborhood_notes"),
 "MARKET.DataSourceDescription": ("market-1004mc","1004MC data source","sources"),
 "SALES_COMPARISON._Comment": ("sales-comparison","Sales comparison comment","comps[].flags / review.notes"),
 "SALES_COMPARISON._CurrentSalesAgreementAnalysisComment": ("sales-comparison","Sales/transfer-history analysis","subject.sales_history"),
 "_RECONCILIATION._SummaryComment": ("reconciliation","Reconciliation summary","review.notes"),
 "_RECONCILIATION._ConditionsComment": ("reconciliation","Reconciliation conditions","review.notes"),
 "COST_ANALYSIS._Comment": ("site-cost","Cost approach comment","(cost approach)"),
 "COST_ANALYSIS.SiteEstimatedValueComment": ("site-cost","Site value comment","(cost approach)"),
 "PROPERTY_ANALYSIS._Comment": ("property-analysis","Property condition/observation","subject.flags"),
 "PRIOR_SALE.GSEPriorSaleComment": ("prior-sale","Prior-sale comment","comps[].prior_sale"),
 "VALUATION_METHODS._AdditionalDescription": ("valuation-methods","Intended use/user clarification","order.intended_use"),
}
FORMS_TO_BUILD = ["1004", "1004C"]

def norm(t):
    t = re.sub(r"\{[a-z_]+\}", " ", t.lower())
    return re.sub(r"[^a-z]+", " ", t).strip()

byff = collections.defaultdict(lambda: collections.defaultdict(list))
for r in deid:
    form = FORM_LABEL.get(r.get("form"), r.get("form") or "?")
    for field, txt in (r.get("notes") or {}).items():
        if txt and len(txt.strip()) >= 40:
            byff[form][field].append(txt.strip())

def yblock(text, indent):
    pad = " " * indent
    return "|\n" + "\n".join(pad + ln for ln in text.replace("\r","").split("\n"))

def emit_form(form):
    groups = collections.defaultdict(list)
    for field, vals in byff[form].items():
        grp, label, target = FIELD_MAP.get(field, ("other", field, "—"))
        clusters = collections.Counter(); rep = {}
        for v in vals:
            k = norm(v); clusters[k]+=1
            if k not in rep or len(v) > len(rep[k]): rep[k]=v
        variants = [{"seen":cnt,"conf":("high" if cnt>=10 else "medium" if cnt>=3 else "low"),"text":rep[k]}
                    for k,cnt in clusters.most_common()]
        groups[grp].append((field, label, target, len(vals), variants))
    formdir = os.path.join(LIB, form); os.makedirs(formdir, exist_ok=True)
    for grp, items in groups.items():
        out = [f"# Notes library — form {form} — group: {grp}",
               "# De-identified (strict + locality). Slots: {date} {money} {road} {route} {mls_number} {parcel_id} {subdivision}.",
               f"form: {form}", f"group: {grp}", "fields:"]
        for field, label, target, total, variants in items:
            out += [f"  - note_field: {field}", f"    label: {json.dumps(label)}",
                    f"    render_target: {json.dumps(target)}", f"    seen_total: {total}", "    variants:"]
            kept = [v for v in variants if v['conf'] in ('high','medium')][:4] or variants[:1]
            for i, v in enumerate(kept):
                out += [f"      - id: {field.split('.')[-1].lstrip('_')}-{i+1}",
                        f"        seen_count: {v['seen']}", f"        confidence: {v['conf']}",
                        "        template: " + yblock(v['text'], 10)]
        open(os.path.join(formdir, grp + ".yaml"),"w",encoding="utf-8").write("\n".join(out)+"\n")

for form in FORMS_TO_BUILD:
    if form in byff: emit_form(form)

# adjustment playbook (XML amounts)
def to_int(x):
    try: return int(round(float(str(x).replace(",",""))))
    except: return None
allfeat = collections.defaultdict(list); perform = collections.defaultdict(set)
for r in raw:
    form = FORM_LABEL.get(r.get("form"), r.get("form") or "?")
    for c in r.get("comps", []):
        for a in c.get("adj", []):
            amt = to_int(a.get("amt"))
            if amt and amt != 0: allfeat[a["f"]].append(amt); perform[a["f"]].add(form)
SCHEMA_MAP = {"GrossLivingArea":"gla_sf","SiteArea":"lot_size_sf","Condition":"grade_or_condition",
 "RoomAboveGradeLine2":"bedrooms/full_baths","CarStorage":"garage","BasementArea":"below_grade_finished_sf",
 "BasementFinish":"below_grade_finished_sf","Quality":"grade_or_condition","View":"(view)","Location":"(location)",
 "HeatingCooling":"heating/cooling","Age":"year_built","DesignStyle":"style"}
pb = ["# Adjustment playbook — typical magnitudes from past reports (XML amounts).",
      "# A HINT for the appraiser; schema keeps adjustments.* appraiser-entered.",
      "# GLA rate ~$75/sf corroborated by gPAR grids. Cross-link: adjustments.lines[].feature.","features:"]
for f in sorted(allfeat, key=lambda x:-len(allfeat[x])):
    a = sorted(abs(x) for x in allfeat[f]); common = [c for c,_ in collections.Counter(a).most_common(3)]
    pb += [f"  - feature: {f}", f"    schema_feature: {json.dumps(SCHEMA_MAP.get(f,'—'))}",
           f"    nonzero_count: {len(a)}", f"    typical_abs_usd: {int(statistics.median(a))}",
           f"    range_abs_usd: [{a[0]}, {a[-1]}]", f"    common_abs_usd: {common}",
           f"    forms: {sorted(perform[f])}"]
open(os.path.join(PLAY,"playbook.yaml"),"w",encoding="utf-8").write("\n".join(pb)+"\n")

prov = ["# Provenance — counts only (no client identifiers).",
        f"# Corpus: {len(raw)} XML reports; notes de-identified via tools/deidentify.","note_field_frequency:"]
ff = collections.Counter()
for r in deid:
    for k in (r.get("notes") or {}): ff[k]+=1
for k,v in ff.most_common(): prov.append(f"  {k}: {v}")
open(os.path.join(LIB,"_PROVENANCE.md"),"w",encoding="utf-8").write("\n".join(prov)+"\n")
print("notes library + playbook written under", os.path.relpath(LIB, REPO))
