#!/usr/bin/env python3
"""
DM fill-map (read-only) — match a Subject-Worksheet HTML to a DataMaster .dma's
field vocabulary, and emit a "what to enter in DataMaster" list.

This does NOT write the .dma (writing is a separate, sandboxed POC). It:
  1. reads the .dma read-only (via tools/dma-decoder) → DM's 1004/UAD field registry
     (field 3) + everything DM has ALREADY imported (source records in fields 7-10);
  2. parses the Subject + History panels of the worksheet HTML;
  3. maps each worksheet field -> the DM registry field name(s) it belongs in;
  4. flags status per row: ENTER (ready) / CONFIRM (inspection ⚠) / MANUAL (no DM field) /
     and whether the value already appears in the .dma (so stale/missing/conflicting
     DM data is visible);
  5. writes an HTML + JSON fill-map to the OUTPUT path (keep it under VDV Appraisals,
     NOT the repo — it carries client values).

Usage:
  python dma_fill_map.py --dma "<file.dma>" --worksheet "<sheet.html>" --out "<out.html>"

Stdlib only. Run via PowerShell (see memory: python-env).
"""
import argparse
import html
import json
import os
import re
import sys

# import the read-only decoder from the sibling tool
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "dma-decoder"))
import dma_decode as dd  # noqa: E402


# ---------------------------------------------------------------------------
# worksheet parsing
# ---------------------------------------------------------------------------
def _clean(cell_html):
    """Strip tags + decode entities; return (text, confirm_flag)."""
    raw = cell_html
    confirm = ("&#9888;" in raw or "confirm" in raw.lower()
               or 'class="amber"' in raw or "appraiser judgment" in raw.lower())
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = html.unescape(txt)
    txt = txt.replace("—", "-").replace("–", "-").replace("★", "")
    txt = re.sub(r"\s+", " ", txt).strip(" -|")
    return txt, confirm


def parse_worksheet(path):
    """Return list of {label, value, source, confirm} from Subject + History panels."""
    htmltext = open(path, encoding="utf-8").read()
    rows = []
    # rows look like: <td class="f">LABEL</td><td class="v">VALUE</td><td class="s">SRC</td>
    pat = re.compile(
        r'<td class="f">(.*?)</td>\s*<td class="v">(.*?)</td>'
        r'(?:\s*<td class="s">(.*?)</td>)?', re.S)
    for m in pat.finditer(htmltext):
        label, _ = _clean(m.group(1))
        value, confirm = _clean(m.group(2))
        source, _ = _clean(m.group(3) or "")
        if label:
            rows.append({"label": label, "value": value,
                         "source": source, "confirm": confirm})
    return rows


# ---------------------------------------------------------------------------
# .dma extraction (read-only)
# ---------------------------------------------------------------------------
def dma_registry(blob):
    """field 3 -> ordered list of DM form field names."""
    top = dd._top_level_fields(blob)
    names = []
    for f3 in top.get(3, []):
        leaves = dd.decode_message(f3, path="3")
        ent = {}
        for lf in leaves:
            mm = re.match(r"3\.3(?:\[(\d+)\])?\.(\d+)$", lf["path"])
            if mm and mm.group(2) == "1" and lf["type"] == "str":
                ent[int(mm.group(1) or 0)] = lf["value"]
        for i in sorted(ent):
            names.append(ent[i])
    return names


def dma_current_pairs(blob):
    """Pull (key,value) string pairs DM has already imported from the source
    records in fields 7-10. Best-effort — groups sibling .1/.2 leaves."""
    top = dd._top_level_fields(blob)
    pairs = {}
    for fn in (7, 8, 9, 10):
        for b in top.get(fn, []):
            leaves = dd.decode_message(b, path=str(fn))
            grp = {}
            for lf in leaves:
                mm = re.match(r"(.*)\.(\d+)$", lf["path"])
                if not mm:
                    continue
                grp.setdefault(mm.group(1), {})[mm.group(2)] = lf
            for g in grp.values():
                k, v = g.get("1"), g.get("2")
                if k and v and k["type"] == "str" and v["type"] == "str":
                    key = k["value"].strip()
                    if key and key not in pairs:
                        pairs[key] = v["value"].strip()
            # also catch decoder-merged "key\x12value" leaves
            for lf in leaves:
                if lf["type"] == "str" and "\x12" in lf["value"]:
                    mm = re.match(r"[\n\x00-\x1f]*([A-Za-z0-9_]{3,})\x12.(.*)", lf["value"])
                    if mm and mm.group(1) not in pairs:
                        pairs[mm.group(1)] = mm.group(2).strip()
    return pairs


# ---------------------------------------------------------------------------
# worksheet-label -> DM field mapping
# (key phrase matched against a normalized label; first match wins)
# ---------------------------------------------------------------------------
MAP = [
    # Identification
    ("address house",          "HouseNumber + StreetName + StreetSuffix"),
    ("city state zip",         "City + State + Zip (+ ZipPlusFourCode)"),
    ("county",                 "County"),
    ("legal description",      "LegalDescription"),
    ("parcel id",              "Apn"),
    ("apn tax id",             "Apn"),
    ("census tract",           "CensusTract"),
    ("owner of public record", "OwnerOfPublicRecord"),
    ("subdivision",            "NeighborhoodName"),
    ("property rights",        "PropertyRightsAppraised"),
    ("zoning",                 "ZoningClassification (+ ZoningDescription)"),
    ("tax year",              "TaxYear + RETaxes (+ assessment: AssessmentLand)"),
    # Site
    ("lot size",               "SiteArea"),
    ("parcel dimensions",      None),
    ("site shape",             "InsideLot / CornerLot / CulDeSac"),
    ("topography",             None),
    ("water",                  "WaterPublic / WaterUtilityTypes"),
    ("sewer",                  "SewerPublic / SewerUtilityTypes"),
    ("electricity",            "ElectricityPublic + GasPublic / GasOther"),
    ("street alley",           "StreetPublic / AlleyPublic / SidewalkPublic"),
    ("fema flood",             None),
    ("hoa",                    None),
    # General
    ("units",                  "NumberOfStories / GeneralStoriesOne"),
    ("type attachment",        "Attachment / AttachmentTypes / PropertyType"),
    ("design",                 "ArchitecturalStyleTypes"),
    ("year built",             "YearBuilt"),
    ("actual age",             "ActualAge"),
    ("effective age",          None),
    # Foundation
    ("foundation type",        "CrawlSpace / ConcreteSlab / FullBasement / PartialBasement"),
    ("basement area",          "BasementTotalSqFt"),
    ("basement finished",      "BasementFinishedPercent"),
    ("basement",               "BasementNone / OutsideEntryExit / SumpPump / EvidenceOfDampness / EvidenceOfSettlement"),
    # Exterior
    ("exterior walls",         "ExteriorWallMaterialTypes"),
    ("roof surface",           "RoofSurfaceMaterialTypes / Roof"),
    ("window type",            None),
    ("gutters",                None),
    ("attic",                  "AtticDropStair / AtticStairs / AtticScuttle / AtticNone"),
    # Interior
    ("floors",                 "FloorMaterialTypes"),
    ("walls trim",             None),
    ("bath floor",             None),
    ("appliances",             "ApplianceTypes / RangeOven / Refrigerator / Dishwasher / Disposal / Microwave / WasherDryer"),
    ("functional utility",     None),
    # HVAC
    ("heating type",           "HeatingTypes (FWA / HWBB / Radiant / HeatOther)"),
    ("fuel",                   "FuelTypes"),
    ("cooling",                "CentralAirConditioning / CoolingTypes"),
    # Amenities
    ("fireplace",              "NumberOfFireplaces / FireplaceCount / FireplaceTypes"),
    ("patio",                  "Deck / Patio / Porch / PatioDeck"),
    ("pool",                   "PoolNo / PoolYes / PoolTypes"),
    ("fence",                  "Fence"),
    ("woodstove",              "WoodStoves"),
    ("driveway",               "Driveway"),
    ("garage",                 "CarStorageNone / Garage / Carport / GarageDetached / CarportDetached"),
    ("energy",                 None),
    # Room count
    ("total rooms",            "TotalAboveGradeRooms"),
    ("bedrooms",               "TotalAboveGradeBedrooms"),
    ("baths",                  "FullBathrooms / HalfBathrooms"),
    ("gla above grade",        "AboveGradeGla / SquareFootage"),
    ("below grade gla",        "BasementTotalSqFt (finished portion)"),
    ("quality",                "QualityExcellent/Good/Average/Fair/Poor"),
    ("condition",              None),
    # History
    ("mls",                    "MlsNumber + ListingStatusTypes"),
    ("list price dom",         "ListPrice / OriginalListPrice + DaysOnMarket"),
    ("list contract date",     "ListingContractDate / ContractDate / OriginalListDate"),
    ("original list",          "OriginalListPrice / PreviousListPrice"),
    ("list office",            "ListingOffice / ListingAgent (+ phone numbers)"),
    ("prior transfers",        "PriorSaleOrTransferDataSources (DM imported CoreLogic deed history)"),
    # Additional notes (no direct 1004 field — narrative / Remarks)
    ("recent updates",         None),
    ("storage",                None),
    ("school district",        None),
    ("water heater",           None),
]


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def map_field(label):
    # prior sale/transfer rows are keyed by a date (e.g. "9/6/2016")
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", label.strip()):
        return "SettlementDate / ClosingPrice (prior sale/transfer — 3-yr disclosure)"
    n = _norm(label)
    for key, dm in MAP:
        if all(w in n for w in key.split()):
            return dm
    return "?"  # unrecognized label


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(dma_path, ws_path):
    blob = dd.read_appraisal_blob(dma_path)
    registry = set(dma_registry(blob))
    pairs = dma_current_pairs(blob)
    blobtext = blob.decode("latin-1", errors="ignore")
    rows = parse_worksheet(ws_path)

    out = []
    for r in rows:
        dm = map_field(r["label"])
        # status
        if r["confirm"] or not r["value"] or r["value"].lower() in ("n/a", "none stated"):
            status = "confirm" if r["confirm"] else "enter"
        else:
            status = "enter"
        if dm is None:
            status = "manual"
        elif dm == "?":
            status = "unmapped"
        # is the worksheet value already in the .dma?
        v = r["value"]
        in_dma = bool(v) and len(v) >= 3 and (v in blobtext or v.split()[0] in blobtext)
        out.append({**r, "dm_field": dm, "status": status, "in_dma": in_dma})

    # headline conflict checks
    conflicts = []
    bd = pairs.get("BedroomsTotal") or pairs.get("TotalAboveGradeBedrooms")
    ws_bd = next((r["value"] for r in rows if _norm(r["label"]).startswith("bedrooms")), None)
    if bd and ws_bd and bd.strip() != ws_bd.strip():
        conflicts.append(f"Bedrooms: DM imported **{bd}**, worksheet says **{ws_bd}** (Zillow). Reconcile.")
    ws_mls = next((r["value"] for r in rows if "mls" in _norm(r["label"])), "")
    mlsnum = re.search(r"\d{6,}", ws_mls)
    if mlsnum and mlsnum.group(0) not in blobtext:
        conflicts.append(f"Current listing MLS #{mlsnum.group(0)} is NOT in the .dma — DM has a different/older MLS record. Re-pull the current listing in DataMaster.")

    return {"rows": out, "registry_size": len(registry),
            "dm_current": pairs, "conflicts": conflicts,
            "dma": dma_path, "worksheet": ws_path}


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
_BADGE = {"enter": ("#1e7d4f", "ENTER"), "confirm": ("#b9770e", "CONFIRM@INSP"),
          "manual": ("#5b6776", "MANUAL"), "unmapped": ("#c0392b", "UNMAPPED")}


def render_html(data, subject_title):
    def esc(s):
        return html.escape(str(s))
    rws = data["rows"]
    body = []
    body.append(f"<h1>DataMaster fill-map &middot; {esc(subject_title)}</h1>")
    body.append('<p class="sub">READ-ONLY analysis. Maps the Subject-Worksheet to DataMaster\'s '
                f'{data["registry_size"]} 1004/UAD fields. Nothing was written to the .dma. '
                'Enter the ENTER rows in DataMaster; CONFIRM@INSP rows wait for inspection.</p>')

    if data["conflicts"]:
        body.append('<div class="box red"><h3>&#9888; Reconcile first — DM data vs worksheet</h3><ol>')
        for c in data["conflicts"]:
            body.append("<li>" + re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(c).replace("&amp;","&")) + "</li>")
        body.append("</ol></div>")

    # main table
    body.append('<table><tr><th>Worksheet field</th><th>Value</th><th>&rarr; DM field</th>'
                '<th>Src</th><th>Status</th><th>In .dma?</th></tr>')
    for r in rws:
        color, lab = _BADGE[r["status"]]
        dmf = "&mdash;" if r["dm_field"] in (None,) else esc(r["dm_field"])
        if r["dm_field"] == "?":
            dmf = "<i>unrecognized</i>"
        ind = "yes" if r["in_dma"] else "<b style='color:#c0392b'>no</b>"
        body.append(
            f'<tr><td class="f">{esc(r["label"])}</td><td>{esc(r["value"])}</td>'
            f'<td><code>{dmf}</code></td><td class="s">{esc(r["source"])}</td>'
            f'<td><span class="badge" style="background:{color}">{lab}</span></td>'
            f'<td>{ind}</td></tr>')
    body.append("</table>")

    # appendix: what DM already has
    body.append(f'<h3>DataMaster already imported ({len(data["dm_current"])} key/values) &mdash; spot-check for stale data</h3>')
    body.append('<table class="mono"><tr><th>DM source key</th><th>value</th></tr>')
    for k in sorted(data["dm_current"]):
        v = data["dm_current"][k]
        if not v:
            continue
        body.append(f'<tr><td>{esc(k)}</td><td>{esc(v[:80])}</td></tr>')
    body.append("</table>")

    css = """body{font:14px/1.5 Segoe UI,Arial,sans-serif;color:#1a2330;max-width:1040px;margin:0 auto;padding:20px}
    h1{font-size:19px;margin:0 0 2px} .sub{color:#5b6776;font-size:12.5px;margin:0 0 14px}
    h3{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#2257a8;margin:20px 0 6px;border-bottom:1px solid #dde3ea;padding-bottom:4px}
    table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
    td,th{padding:4px 8px;border-bottom:1px solid #eef1f5;text-align:left;vertical-align:top}
    th{background:#eef2f7;color:#5b6776;font-size:11px;text-transform:uppercase}
    td.f{font-weight:600;color:#33414f;width:21%} td.s{color:#2257a8;font-size:11px;white-space:nowrap}
    code{font-size:12px;color:#1a2330} .mono td{font-family:Consolas,monospace;font-size:11.5px}
    .badge{color:#fff;border-radius:4px;padding:1px 6px;font-size:10.5px;font-weight:700;white-space:nowrap}
    .box{border:1px solid #dde3ea;border-radius:6px;padding:8px 14px;margin:10px 0}
    .box.red{border-left:4px solid #c0392b} .box h3{border:none;color:#c0392b;margin:2px 0 6px}
    .box ol{margin:0;padding-left:18px}"""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(body)}</body></html>"


def main(argv=None):
    ap = argparse.ArgumentParser(description="DM fill-map (read-only)")
    ap.add_argument("--dma", required=True)
    ap.add_argument("--worksheet", required=True)
    ap.add_argument("--out", required=True, help="output .html path (under VDV Appraisals, not repo)")
    args = ap.parse_args(argv)

    data = build(args.dma, args.worksheet)
    title = os.path.splitext(os.path.basename(args.worksheet))[0].replace("_worksheet", "")
    open(args.out, "w", encoding="utf-8").write(render_html(data, title))
    with open(os.path.splitext(args.out)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    n = {"enter": 0, "confirm": 0, "manual": 0, "unmapped": 0}
    for r in data["rows"]:
        n[r["status"]] += 1
    print(f"rows={len(data['rows'])}  enter={n['enter']} confirm={n['confirm']} "
          f"manual={n['manual']} unmapped={n['unmapped']}  conflicts={len(data['conflicts'])}")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
