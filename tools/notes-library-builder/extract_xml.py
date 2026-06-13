#!/usr/bin/env python3
"""Extract adjustments + appraiser notes from ACI/MISMO 2.6 appraisal XMLs into
_analysis/extraction.json + a grouped markdown. Stdlib only.
Usage: python extract_xml.py --base "<VDV Appraisals root>"
Writes to <base>/Past Reports/_analysis/ (client zone — stays OUT of the repo)."""
import xml.etree.ElementTree as ET, re, json, os, glob, argparse

ap = argparse.ArgumentParser(); ap.add_argument("--base", required=True); A = ap.parse_args()
SRC = os.path.join(A.base, "Past Reports"); OUT = os.path.join(SRC, "_analysis"); os.makedirs(OUT, exist_ok=True)
def lname(t): return t.split('}')[-1]
def At(el,*keys):
    d={k.split('}')[-1]:v for k,v in el.attrib.items()}
    for k in keys:
        if k in d: return d[k]
    return None
NOTE_RE=re.compile(r'Comment|Narrative|Remark|Description|Explanation|Addendum|AdditionalText|_Text$')
def is_b64(v): return bool(re.match(r'^[A-Za-z0-9+/=\s]{300,}$',v))

def extract(path):
    rec={"file":os.path.basename(path),"form":None,"form_other":None,"effective_date":None,
         "appraised_value":None,"comps":[],"notes":{}}; cur=None
    for ev,el in ET.iterparse(path,events=('start','end')):
        n=lname(el.tag)
        if ev=='start':
            if n=='COMPARABLE_SALE': cur={'adj':[]}
            continue
        if n=='REPORT' and rec["form"] is None:
            rec["form"]=At(el,'AppraisalFormType'); rec["form_other"]=At(el,'AppraisalFormTypeOtherDescription')
            rec["effective_date"]=At(el,'AppraisalEffectiveDate','AppraiserReportSignedDate')
        elif n=='SALE_PRICE_ADJUSTMENT' and cur is not None:
            t=At(el,'_Type'); t=(At(el,'_TypeOtherDescription') or 'Other') if t=='Other' else t
            cur['adj'].append({'f':t,'v':At(el,'_Description'),'amt':At(el,'_Amount')})
        elif n=='COMPARABLE_SALE':
            cur.update(seq=At(el,'PropertySequenceIdentifier'),price=At(el,'PropertySalesAmount'),
                       ppsf=At(el,'SalesPricePerGrossLivingAreaAmount'),adj_price=At(el,'AdjustedSalesPriceAmount'),
                       net_amt=At(el,'SalePriceTotalAdjustmentAmount'),net_pct=At(el,'SalePriceTotalAdjustmentNetPercent'),
                       gross_pct=At(el,'SalesPriceTotalAdjustmentGrossPercent'))
            rec["comps"].append(cur); cur=None
        elif n=='SALES_COMPARISON':
            rec["appraised_value"]=At(el,'ValueIndicatedBySalesComparisonApproachAmount') or rec["appraised_value"]
        for kk,v in el.attrib.items():
            k2=kk.split('}')[-1]
            if v and NOTE_RE.search(k2):
                vs=v.strip()
                if len(vs)>=40 and not is_b64(vs):
                    key=f"{n}.{k2}"
                    if key not in rec["notes"] or len(vs)>len(rec["notes"][key]): rec["notes"][key]=vs[:6000]
        el.clear()
    return rec

records=[]
for p in sorted(glob.glob(os.path.join(SRC,"*.XML"))+glob.glob(os.path.join(SRC,"*.xml"))):
    try: records.append(extract(p))
    except Exception as e: records.append({"file":os.path.basename(p),"error":str(e)})
json.dump(records,open(os.path.join(OUT,"extraction.json"),"w",encoding="utf-8"),indent=1,ensure_ascii=False)
print("extracted",len(records),"XML reports →",os.path.join(OUT,"extraction.json"))
