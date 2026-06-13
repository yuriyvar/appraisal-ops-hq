#!/usr/bin/env python3
"""Pair-QA: validate XML extraction against the delivered PDF for the XML<->PDF
pairs. Every numeric value the parser pulled must appear in the rendered PDF text.
Reports to the client zone (they cite real values). Stdlib + pdftotext.

Usage: python pair_qa.py --base "<VDV Appraisals root>"
"""
import json, os, re, subprocess, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True, help="VDV Appraisals root")
A = ap.parse_args()
BASE = os.path.join(A.base, "Past Reports")
ANALYSIS = os.path.join(BASE, "_analysis")
OUT = os.path.join(ANALYSIS, "_pairs-qa"); os.makedirs(OUT, exist_ok=True)

PAIRS = [
    ("7217 wytheville.XML", "7217 wytheville.PDF", "URAR"),
    ("1114 skipwith.XML",   "1114 skipwith.PDF",   "URAR"),
    ("1284 hammock.XML",    "1284 hammock.PDF",    "URAR"),
    ("11597 leeds chapel.XML", "GPAR PDFs/11597 leeds chapel.PDF", "gPAR"),
]
raw = {r["file"]: r for r in json.load(open(os.path.join(ANALYSIS, "extraction.json"), encoding="utf-8"))}

def pdf_text(p): return subprocess.run(["pdftotext","-layout",p,"-"],capture_output=True,text=True).stdout
def in_text(val, txt):
    if val is None: return None
    s = re.sub(r"[^\d.]","",str(val))
    if not s or s=="0": return None
    try: n=int(round(float(s)))
    except: return None
    return any(c in txt for c in (str(n), f"{n:,}"))

summary=[]
for xmlf,pdff,kind in PAIRS:
    rec=raw.get(xmlf); txt=pdf_text(os.path.join(BASE,pdff)); rows=[]
    def check(p,v):
        f=in_text(v,txt)
        if f is not None: rows.append((p,v,f))
    check("market.indicated_value", rec.get("appraised_value"))
    for c in rec.get("comps",[]):
        seq=c.get("seq")
        if seq in ("0",None): continue
        check(f"comps[{seq}].sale.sale_price", c.get("price"))
        check(f"comps[{seq}].sale.adjusted_price", c.get("adj_price"))
        check(f"comps[{seq}].sale.net_amount", c.get("net_amt"))
        for a in c.get("adj",[]):
            if a.get("amt") and a["amt"] not in ("0",): check(f"comps[{seq}].adj[{a['f']}]", a["amt"])
    hit=sum(1 for _,_,f in rows if f); tot=len(rows); rate=round(100*hit/tot,1) if tot else 0
    summary.append((xmlf,kind,hit,tot,rate))
    lines=[f"# Pair-QA — {xmlf} ↔ {pdff}",f"_Kind: {kind}. XML value vs delivered PDF._\n",
           f"**Match rate: {hit}/{tot} = {rate}%**\n","| record_path | xml value | in PDF? |","|---|---|---|"]
    for p,v,f in rows: lines.append(f"| {p} | {v} | {'✓' if f else '✗ MISS'} |")
    miss=[r for r in rows if not r[2]]
    if miss:
        lines.append("\n## Misses\n"); lines += [f"- {p} = {v}" for p,v,_ in miss]
    open(os.path.join(OUT,"pair_"+re.sub(r'[^a-z0-9]+','-',xmlf.lower().replace('.xml',''))+".md"),"w",encoding="utf-8").write("\n".join(lines)+"\n")

sl=["# Pair-QA summary","","| pair | kind | match | rate |","|---|---|---|---|"]
for xmlf,kind,hit,tot,rate in summary: sl.append(f"| {xmlf} | {kind} | {hit}/{tot} | {rate}% |")
open(os.path.join(OUT,"_qa-summary.md"),"w",encoding="utf-8").write("\n".join(sl)+"\n")
for s in summary: print(s)
