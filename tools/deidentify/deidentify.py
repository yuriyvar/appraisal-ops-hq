#!/usr/bin/env python3
"""
De-identify appraiser note text before it enters the repo.

Policy: STRICT + keep locality.
  SCRUB  → typed slots: street addresses, named roads, MLS#, parcel IDs
           (GPIN/PID/APN), dollar amounts, dates, route names, explicit
           subdivision/neighborhood proper names.
  KEEP   → county/city names (locality), state, condition/quality codes
           (C1-C6/Q1-Q6), and adjustment RATES ($/sf, per sf) — knowledge, not PII.

This tool is the ONE-WAY GATE from the client zone into the repo. It reads
client-zone text and writes de-identified candidates to a client-zone STAGING
dir for human review (--report writes a scrub diff). It never writes into the
repo itself — a human promotes reviewed content. `scrub()` is importable so the
notes-library builder reuses the exact same policy.

Determinism: pure regex, stdlib only, no network.
"""
import re

KEEP_LOCALITIES = {
    "henrico", "chesterfield", "richmond", "hanover", "goochland", "powhatan",
    "petersburg", "colonial heights", "hopewell", "dinwiddie", "amelia",
    "new kent", "charles city", "prince george", "spotsylvania", "fredericksburg",
    "caroline", "louisa", "fluvanna", "cumberland", "nottoway", "virginia", "va",
    "chesapeake", "norfolk", "fairfax",
}
STREET_SUFFIX = (r"St|Street|Rd|Road|Dr|Drive|Ln|Lane|Ave|Avenue|Blvd|Boulevard|"
                 r"Ct|Court|Way|Pkwy|Parkway|Pl|Place|Cir|Circle|Ter|Terrace|"
                 r"Hwy|Highway|Pike|Run|Trl|Trail|Loop|Path|Row|Sq|Square|Aly|Alley")
RATE_PAT = re.compile(r"\$\s?\d+(?:\.\d+)?\s*(?:/|per\s+)\s*s(?:q\s?\.?\s?ft|f|quare\s+feet)\b", re.I)

def _rules():
    # order: specific → general
    return [
        ("{mls_number}", re.compile(r"\b(?:bright\s*mls|cvr\s*mls|mls)\s*(?:id|no\.?|#)?\s*#?\s*[A-Z0-9]*\d{4,}[A-Z0-9]*\b", re.I)),
        ("{mls_number}", re.compile(r"#\s?[A-Z0-9]*\d{4,}[A-Z0-9]*\b")),
        ("{parcel_id}", re.compile(r"\b\d{3}-\d{3}-\d{4}\b")),                 # GPIN
        ("{parcel_id}", re.compile(r"\b(?:GPIN|PID|APN|Tax\s*ID|Parcel)\s*[:#]?\s*[\w-]{5,}\b", re.I)),
        ("{route}", re.compile(r"\b(?:Rt\.?|Route|Hwy)\s*\.?\s*\d+\b", re.I)),
        ("{address}", re.compile(r"\b\d{1,6}\s+(?:[A-Z][A-Za-z'\.]+\s+){1,4}(?:%s)\b\.?" % STREET_SUFFIX)),
        ("{road}", re.compile(r"\b[A-Z][A-Za-z']+(?:\s+[A-Z][A-Za-z']+)?\s+(?:%s)\b\.?" % STREET_SUFFIX)),
        ("{money}", re.compile(r"\$\s?\d[\d,]*(?:\.\d{1,2})?\b")),
        ("{money}", re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\b")),
        ("{money}", re.compile(r"\b\d{5,7}\b")),                                # bare price/zip (sqft is 4 digits)
        ("{date}", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
        ("{date}", re.compile(r"\b[sc]\d{2}/\d{2}\b")),                          # s05/25 ; c06/25
        ("{date}", re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b")),
    ]

SUBDIV = re.compile(r"\b((?:[A-Z][A-Za-z']+\s){0,3}[A-Z][A-Za-z']+)\s+(subdivision|neighborhood)\b")
SUBDIV2 = re.compile(r"\b(?:in|of|within|the)\s+((?:[A-Z][A-Za-z']+\s){0,2}[A-Z][A-Za-z']+)\s+(?:subdivision|neighborhood|community)\b")
SUB_STOP = {"overall", "the", "this", "subject", "comparable", "recent", "all",
            "no", "per", "based", "market", "current", "above", "data"}


def scrub(text):
    """Return (clean_text, found) where found is a list of (slot, original)."""
    if not text:
        return text, []
    found = []
    s = text
    rates = []
    def _stash(m):
        rates.append(m.group(0)); return f"\x00R{len(rates)-1}\x00"
    s = RATE_PAT.sub(_stash, s)

    def repl(slot, pat, s):
        res = []
        for m in pat.finditer(s):
            if m.group(0).strip().lower() in KEEP_LOCALITIES:
                continue
            found.append((slot, m.group(0).strip()))
            res.append((m.start(), m.end()))
        if not res:
            return s
        buf = []; idx = 0
        for a, b in res:
            buf.append(s[idx:a]); buf.append(slot); idx = b
        buf.append(s[idx:])
        return "".join(buf)

    for slot, pat in _rules():
        s = repl(slot, pat, s)

    def sub_repl(m):
        name = m.group(1)
        if name.strip().lower() in KEEP_LOCALITIES:
            return m.group(0)
        if name.split()[0].lower() in SUB_STOP:
            return m.group(0)
        found.append(("{subdivision}", name.strip()))
        return m.group(0).replace(name, "{subdivision}")
    s = SUBDIV.sub(sub_repl, s)
    s = SUBDIV2.sub(sub_repl, s)

    for i, r in enumerate(rates):
        s = s.replace(f"\x00R{i}\x00", r)
    return s, found


if __name__ == "__main__":
    import argparse, json, os, collections
    ap = argparse.ArgumentParser(description="De-identify note text (strict + keep locality).")
    ap.add_argument("--in", dest="inp", required=True, help="extraction.json (client zone)")
    ap.add_argument("--out", required=True, help="staging dir (client zone) for review")
    ap.add_argument("--report", action="store_true", help="also write a scrub diff report")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data = json.load(open(a.inp, encoding="utf-8"))
    allfound = []; clean = []
    for rec in data:
        cr = {"file": rec.get("file"), "form": rec.get("form"), "notes": {}}
        for k, v in (rec.get("notes") or {}).items():
            cv, found = scrub(v)
            cr["notes"][k] = cv
            for slot, orig in found:
                allfound.append({"file": rec.get("file"), "field": k, "slot": slot, "orig": orig})
        clean.append(cr)
    json.dump(clean, open(os.path.join(a.out, "notes_deidentified.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    if a.report:
        json.dump(allfound, open(os.path.join(a.out, "scrub_report.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
    print("reports", len(clean), "scrubbed", len(allfound),
          "slots", dict(collections.Counter(x['slot'] for x in allfound)))
