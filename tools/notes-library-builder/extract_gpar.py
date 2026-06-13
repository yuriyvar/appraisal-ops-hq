#!/usr/bin/env python3
"""Raw extraction from gPAR PDFs (no XML): comment/prose fields, adjustment-grid
blocks, addendum. Heuristic text parse (pdftotext -layout). Stdlib + pdftotext.
NOTE: gPAR text parse is noisy — use for NOTES/feature corroboration only, never
for adjustment AMOUNTS (those come from XML; see ADR-003).
Usage: python extract_gpar.py --base "<VDV Appraisals root>"
Writes to <base>/Past Reports/_analysis/ (client zone)."""
import subprocess, re, os, glob, json, argparse

ap = argparse.ArgumentParser(); ap.add_argument("--base", required=True); A = ap.parse_args()
SRC = os.path.join(A.base, "Past Reports", "GPAR PDFs")
OUT = os.path.join(A.base, "Past Reports", "_analysis"); os.makedirs(OUT, exist_ok=True)
def text_of(p): return subprocess.run(["pdftotext","-layout",p,"-"],capture_output=True,text=True).stdout
ANCHORS=[("Neighborhood Description","Neighborhood description"),("Market Conditions (including support","Market conditions"),
 ("Site Comments","Site comments"),("Comments on the Improvements","Improvements comments"),
 ("Summary of Sales Comparison Approach","Sales comparison summary"),("Site Value Comments","Site value comment"),
 ("Comments on Cost Approach","Cost approach comment"),("Reconciliation comments:","Reconciliation comments"),
 ("Neighborhood Boundaries","Neighborhood boundaries")]
BOUND=re.compile(r'^[\s]*[A-Z][A-Z /]{6,}\s*$|Indicated Value|Net Adjustment|VALUE ADJUSTMENTS')
def grab(lines,i):
    out=[re.sub(r'\s{2,}',' ',lines[i]).strip()]; j=i+1
    while j<len(lines) and j<i+8:
        ln=lines[j]
        if not ln.strip() or BOUND.search(ln) or any(a in ln for a,_ in ANCHORS): break
        out.append(re.sub(r'\s{2,}',' ',ln).strip()); j+=1
    return " ".join(out).strip()
def extract(pdf):
    txt=text_of(pdf); lines=txt.split("\n")
    rec={"file":os.path.basename(pdf),"subtype":None,"notes":{},"grids":[],"addendum":""}
    rec["subtype"]="Land gPAR" if "land appraisal" in txt.lower() else "Residential gPAR"
    for i,ln in enumerate(lines):
        for anc,lab in ANCHORS:
            if anc in ln and lab not in rec["notes"]:
                val=grab(lines,i).replace(anc,"").strip(" :")
                if len(val)>=25: rec["notes"][lab]=val[:4000]
    iv=re.findall(r'Indicated Value by Sales Comparison Approach\s*\$?\s*([\d,]+)',txt); rec["indicated_value"]=iv[0] if iv else None
    for blk in re.findall(r'(VALUE ADJUSTMENTS.*?Net Adjustment \(Total\).*?\$[^\n]*)',txt,re.S)[:2]:
        rec["grids"].append("\n".join(re.sub(r'\s{2,}','  ',x.rstrip()) for x in blk.split("\n") if x.strip())[:3000])
    m=re.search(r'(Supplemental Addendum|ADDENDUM)(.*)',txt,re.S)
    if m: rec["addendum"]=re.sub(r'\s{2,}',' ',m.group(2)).strip()[:6000]
    return rec
records=[extract(p) for p in sorted(glob.glob(os.path.join(SRC,"*.PDF"))+glob.glob(os.path.join(SRC,"*.pdf")))]
json.dump(records,open(os.path.join(OUT,"extraction_gpar.json"),"w",encoding="utf-8"),indent=1,ensure_ascii=False)
print("extracted",len(records),"gPAR PDFs →",os.path.join(OUT,"extraction_gpar.json"))
