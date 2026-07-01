#!/usr/bin/env python3
"""
DataMaster Subject Data-Collection Sheet generator.

Single source of truth for the *orderly list of data to collect for a DataMaster
1004-family order*, derived by comparing three corners of VDV's past reports:

  * .dma  (DataMaster's own files)  — 368 inline field names across 113 files
           (172 present in every file); DM's actual input schema.
  * .XML  (ACI / MISMO 2.6)         — 453 element.attr fields; the structured report.
  * .PDF  (URAR / gPAR rendered)    — confirmation of what lands on the form.

Emits two artifacts from ONE catalog so they can never drift:
  1. a Markdown reference  — the orderly field list (DM input order) with the
     DM field name(s), the MISMO equivalent, where to collect each, the form
     applicability, and whether the *current* adopted template already covers it.
  2. a blank HTML worksheet — same visual format as the adopted
     `Operations/Template files/Subject-Worksheet_TEMPLATE.html` (tabs · flag box ·
     NOT CERTIFIED footer · {{TOKEN}} placeholders), but completed to the full
     DM-aligned field set (the gaps the audit found are marked ★ here).

Stdlib-only, deterministic. No client data in this file — field NAMES only.

Usage:
    python build_collection_sheet.py --html OUT.html --md OUT.md
"""

import argparse
import html

# Source legend used in the reference + as a hint chip on the sheet.
#   APEX = county assessment portal (SOR)   ZIL = Zillow/portal supplement
#   MLS  = Matrix/MLS sheet                  PUB = public record / deed / tax
#   INSP = appraiser confirms at inspection
SRC = {
    "APEX": "County assessment portal (SOR)",
    "ZIL":  "Zillow / public portal",
    "MLS":  "MLS / Matrix sheet",
    "PUB":  "Public record (deed / tax)",
    "INSP": "Appraiser — confirm at inspection",
}

# Current Cowork agent persona (the interactive lane). Cowork agents get replaced
# periodically — this constant is the ONLY place the name is rendered into a worksheet;
# change it here on rename. Process docs refer to the agent symbolically as COWORK_AGENT.
COWORK_AGENT = "Ton"

# ---------------------------------------------------------------------------
# THE CATALOG  — DM 1004 input order. Each field:
#   (label, token, [dm_names], [mismo], "SRC1/SRC2", forms, gap?, note)
# gap=True  => DM tracks it but the current adopted template omits it (audit add).
# forms: "all" or e.g. "1004C","1073","FHA" notes where it especially matters.
# ---------------------------------------------------------------------------
CATALOG = [
 ("Identification", [
  ("Address (house # / street)", "ADDRESS",
   ["AddressLine1","HouseNumber","StreetName","StreetSuffix"],
   ["LOCATION.PropertyStreetAddress"], "APEX/MLS", "all", False, ""),
  ("City / State / Zip", "CITY_STATE_ZIP",
   ["City","State","Zip","ZipPlusFourCode"],
   ["LOCATION.PropertyStreetAddress2"], "APEX", "all", False, ""),
  ("County", "COUNTY", ["County"], [], "APEX", "all", False,
   "Drives which county SOR verifies the comps."),
  ("Legal description", "LEGAL", ["LegalDescription"], [], "APEX/PUB", "all", False, ""),
  ("Parcel ID / PID / GPIN", "PID", ["Apn"],
   [], "APEX", "all", False, "DM stores it as APN; in Hanover PID==GPIN."),
  ("APN / Tax ID", "APN", ["Apn"], [], "APEX", "all", True,
   "DM keeps APN distinct from PID — record both when they differ."),
  ("Census tract", "CENSUS", ["CensusTract"], [], "APEX/PUB", "all", True,
   "Required UAD field; DM has CensusTract — current template omits it."),
  ("Owner of public record", "OWNER", ["OwnerOfPublicRecord","OwnerOfPublicRecord1"],
   [], "APEX/PUB", "all", True, "Optional for Alan hand-off; DM tracks it."),
  ("Subdivision / Neighborhood", "SUBDIVISION", ["NeighborhoodName"],
   [], "APEX/MLS", "all", False, ""),
  ("Property rights appraised", "RIGHTS", ["PropertyRightsAppraised"],
   [], "PUB", "all", True, "Fee Simple / Leasehold — DM field, template gap."),
  ("Tax year / RE taxes / assessment", "ASSESSMENT",
   ["TaxYear","RETaxes","AssessmentLand"], [], "APEX", "all", False, ""),
 ]),
 ("Site", [
  ("Lot size (sf / acres)", "LOT", ["SiteArea","GrossBuildingArea","LotDimensions"],
   [], "APEX/ZIL", "all", False,
   "Often blank in Henrico APEX → go to Zillow immediately; don't leave blank."),
  ("Site shape / location", "SITE_SHAPE", ["CornerLot","InsideLot","CulDeSac"],
   ["_OFF_SITE_IMPROVEMENT._Type"], "APEX/INSP", "all", True,
   "Corner / inside / cul-de-sac — DM flags these."),
  ("Topography / view", "VIEW", ["ViewTypes","ViewFactor1"],
   ["COMPARISON_VIEW_DETAIL.GSEViewType"], "INSP/ZIL", "all", False, ""),
  ("Zoning classification", "ZONING", ["ZoningClassification","ZoningDescription"],
   [], "APEX", "all", False, ""),
  ("Water", "WATER", ["WaterPublic","WaterOther","WaterDescription"],
   ["SITE_UTILITY._Type"], "APEX", "all", False, ""),
  ("Sewer", "SEWER", ["SewerPublic","SewerOther","SewerDescription"],
   ["SITE_UTILITY._Type"], "APEX", "all", False, ""),
  ("Electricity / Gas", "UTILITIES", ["ElectricityPublic","GasPublic","GasOther"],
   ["SITE_UTILITY._Type"], "APEX", "all", True,
   "DM tracks electric + gas separately — current template only had water/sewer."),
  ("Street / alley / sidewalk", "STREET", ["StreetPublic","StreetPrivate",
   "AlleyPublic","SidewalkPublic","CurbGutterPublic","StreetLightsPublic"],
   ["_OFF_SITE_IMPROVEMENT._Type"], "APEX/INSP", "all", True,
   "Off-site improvements — DM/MISMO carry the full set; template gap."),
  ("FEMA flood zone / map / date", "FLOOD", [],
   [], "PUB", "all", False, "Zone + map# + map date (URAR requires all three)."),
  ("HOA (amount / period)", "HOA", ["HoaPerYear","HoaPerMonth","HoaAmount","HoaPeriod"],
   [], "MLS/PUB", "1073/1004C", False, ""),
 ]),
 ("General Description", [
  ("Units / Stories", "UNITS_STORIES", ["GeneralUnits","TotalNumberOfUnits",
   "NumberOfStories","StoriesTypes"], [], "APEX", "all", False, ""),
  ("Type / Attachment", "TYPE_ATT", ["PropertyType","Manufactured","ManufacturedHousing"],
   [], "APEX/INSP", "all", True,
   "Det/Att; flag Manufactured for 1004C (HUD plate, no APN path)."),
  ("Design (style)", "TYPE_STYLE", ["ArchitecturalStyleTypes"],
   ["COMPARISON_DETAIL.GSE...","_PRESENT_LAND_USE._Type"], "APEX/INSP", "all", False, ""),
  ("Year built", "YEAR_BUILT", ["YearBuilt"], [], "APEX", "all", False, ""),
  ("Actual age", "ACT_AGE", ["ActualAge"], [], "APEX", "all", True,
   "DM keeps ActualAge separate from effective age — template gap."),
  ("Effective age", "EFF_AGE", [], [], "INSP", "all", False, "Appraiser judgment."),
 ]),
 ("Foundation / Basement", [
  ("Foundation type", "FOUNDATION", ["CrawlSpace","ConcreteSlab","FullBasement",
   "PartialBasement","BasementNone","PouredConcrete","BlockAndPier"],
   [], "APEX/INSP", "all", False, "APEX has TYPE only; material = inspection."),
  ("Basement area (sf)", "BSMT_SF", ["BasementTotalSqFt"],
   ["COMPARISON_DETAIL.GSEBelowGradeTotalSquareFeetNumber"], "APEX/INSP", "all", True,
   "DM stores basement sf + % finished — template only had a 'below grade' line."),
  ("Basement finished %", "BSMT_FIN", ["BasementFinishedPercent","BasementFinishedSqFt",
   "FullBasementFinished","PartialBasementFinished"], [], "INSP", "all", True, ""),
  ("Basement — outside entry / sump / dampness / settlement", "BSMT_COND",
   ["OutsideEntryExit","SumpPump","EvidenceOfDampness","EvidenceOfSettlement",
    "EvidenceOfInfestation"], [], "INSP", "all", True,
   "URAR basement checkboxes — DM tracks each; template gap."),
 ]),
 ("Exterior", [
  ("Exterior walls", "EXT_WALLS", ["ExteriorWallMaterialTypes","Exterior"],
   ["EXTERIOR_FEATURE._Type"], "APEX/INSP", "all", False, ""),
  ("Roof surface", "ROOF", ["RoofSurfaceMaterialTypes","Roof"],
   ["EXTERIOR_FEATURE._Type"], "APEX/INSP", "all", False, ""),
  ("Window type", "WINDOWS", [],
   ["EXTERIOR_FEATURE._Type"], "INSP", "all", True,
   "MISMO EXTERIOR_FEATURE WindowType — appraiser at inspection."),
  ("Gutters & downspouts", "GUTTERS", [],
   ["EXTERIOR_FEATURE._Type"], "INSP", "all", True, ""),
  ("Attic", "ATTIC", ["AtticScuttle","AtticStairs","AtticDropStair","AtticFinished",
   "AtticNone","AtticHeated","AtticFloor"], ["ATTIC_FEATURE._Type"], "INSP", "all", False, ""),
 ]),
 ("Interior", [
  ("Floors", "FLOORS", ["FloorMaterialTypes"],
   ["INTERIOR_FEATURE._Type"], "INSP/ZIL", "all", False,
   "Zillow photos often show floor material — flag 'confirm at inspection'."),
  ("Walls / trim & finish", "WALLS_BATH", [],
   ["INTERIOR_FEATURE._Type"], "INSP", "all", False, ""),
  ("Bath floor / wainscot", "BATH_FIN", [],
   ["INTERIOR_FEATURE._Type"], "INSP", "all", True, ""),
  ("Appliances (range/oven · refrig · dishwasher · disposal · microwave · washer/dryer)",
   "KITCHEN", ["RangeOven","Refrigerator","Dishwasher","Disposal","Microwave",
   "WasherDryer","FanHood","AppliancesOther"], ["KITCHEN_EQUIPMENT._Type"],
   "INSP/ZIL", "all", True, "DM itemizes each appliance — template lumped them."),
  ("Functional utility", "FUNC", ["QualityFair"],
   ["PROPERTY_ANALYSIS._Type"], "INSP", "all", True, "Average / adequate / issues."),
 ]),
 ("Heating / Cooling", [
  ("Heating type", "HEATING", ["FWA","HWBB","Radiant","WoodStoves","HeatOther"],
   ["AMENITY._Type"], "APEX/INSP", "all", False, ""),
  ("Fuel", "FUEL", ["FuelTypes"], [], "APEX/INSP", "all", True,
   "DM FuelTypes — gas/electric/oil; template gap."),
  ("Cooling", "COOLING", ["CentralAirConditioning","IndividualCooling","CoolingOther"],
   ["AMENITY._Type"], "APEX/INSP", "all", False, ""),
 ]),
 ("Amenities / Car Storage", [
  ("Fireplace(s) — count", "FIREPLACE", ["FireplaceCount","NumberOfFireplaces",
   "Fireplaces","FireplaceTypes"], ["AMENITY._Type"], "APEX/INSP", "all", False,
   "Record the COUNT (DM FireplaceCount), not just yes/no."),
  ("Patio / Porch / Deck", "PATIO", ["Porch","Patio","Deck","PatioDeck","PorchBalcony",
   "PorchTypes","DeckTypes","PatioTypes"], ["AMENITY._Type"], "INSP/ZIL", "all", False, ""),
  ("Pool", "POOL", ["Pool","PoolYes","PoolNo","PoolTypes"],
   ["AMENITY._Type"], "INSP/ZIL", "all", True,
   "DM has a Pool field + type — current template had no pool row."),
  ("Fence", "FENCE", ["Fence","FenceTypes"], ["AMENITY._Type"], "INSP/ZIL", "all", True, ""),
  ("Woodstove", "WOODSTOVE", ["WoodStoves"], ["AMENITY._Type"], "INSP", "all", True, ""),
  ("Driveway (surface / spaces)", "DRIVEWAY", ["Driveway","DrivewaySpacesCount"],
   [], "INSP/ZIL", "all", True, ""),
  ("Garage / Carport (type + count)", "GARAGE", ["GarageAttached","GarageDetached",
   "GarageBuiltIn","CarportAttached","CarportDetached","GarageCount","CarStorageTypes",
   "CarStorageCoveredCount","DrivewaySpacesCount"], [], "APEX/INSP", "all", False,
   "Capture type AND # cars (DM keeps per-type counts)."),
  ("Energy-efficient items", "ENERGY", ["EnergyEfficientItemTypes"],
   [], "INSP", "all", True, ""),
 ]),
 ("Room Count · Size · Quality · Condition", [
  ("Total rooms", "ROOMS", ["TotalAboveGradeRooms"],
   ["ROOM_ADJUSTMENT.TotalRoomCount"], "APEX/INSP", "all", False, ""),
  ("Bedrooms", "BEDS", ["TotalAboveGradeBedrooms"],
   ["ROOM_ADJUSTMENT.TotalBedroomCount"], "APEX/INSP", "all", False, ""),
  ("Baths (full / half · ¾ · ¼)", "BATHS", ["FullBathrooms","HalfBathrooms",
   "ThreeQuartersBathrooms","QuarterBathrooms"], ["ROOM_ADJUSTMENT.TotalBathroomCount"],
   "APEX/INSP", "all", False, ""),
  ("GLA above grade (sf)", "GLA", ["AboveGradeGla","SquareFootage"],
   [], "APEX/MLS", "all", False,
   "County SOR governs; note any MLS conflict. Never enter unverified GLA."),
  ("Below-grade GLA (sf)", "BELOW_GRADE", ["BelowGradeGla","BasementTotalSqFt"],
   ["COMPARISON_DETAIL.GSEBelowGradeTotalSquareFeetNumber"], "APEX/INSP", "all", False, ""),
  ("Quality of construction (Q)", "QUALITY", ["QualityExcellent","QualityGood",
   "QualityAverage","QualityFair","QualityPoor","QualityOfConstruction"],
   ["COMPARISON_DETAIL.GSEQualityOfConstructionRatingType"], "INSP", "all", True,
   "UAD Q1–Q6 — DM tracks it; template only had Condition. Capture BOTH Q and C."),
  ("Condition (C)", "CONDITION", ["Condition"],
   ["COMPARISON_DETAIL.GSEOverallConditionType"], "INSP", "all", False,
   "UAD C1–C6 — appraiser judgment at inspection."),
 ]),
]

# 1004C / 1073 form-specific extras (surfaced as a note block, not Subject rows).
FORM_EXTRAS = {
 "1004C (Manufactured)": [
   "HUD data plate / certification label #", "Manufacturer / model / year",
   "Serial / VIN", "Dimensions & towing hitch removed?", "Permanent foundation type",
 ],
 "1073 (Condo)": [
   "Project name", "# units in project / # for sale", "Owner vs tenant occupancy",
   "Unit floor # / # levels", "Parking type & space #", "Common elements / amenities",
   "Monthly HOA & what it covers",
 ],
 "1004 FHA": [
   "FHA case #", "Appliances working (FHA)", "Attic & crawl observed (FHA req.)",
   "Roof remaining life (FHA)", "Handrails / safety / health-and-safety items",
 ],
}


# ---------------------------------------------------------------------------
# TAB GROUPING — the flat CATALOG above stays the data model; this groups its
# sections into the DM/ACI tabs (Subject · Neighborhood · Site · Improvements)
# WITHOUT moving field tuples or tokens (prefill_worksheet.py depends on the
# token ids, not the grouping). New sections added later map here.
# ---------------------------------------------------------------------------
TAB_ORDER = ["Subject", "Neighborhood", "Site", "Improvements"]
SECTION_TAB = {
    "Identification": "Subject",
    "Contract": "Subject",
    "Site": "Site",
    "General Description": "Improvements",
    "Foundation / Basement": "Improvements",
    "Exterior": "Improvements",
    "Interior": "Improvements",
    "Heating / Cooling": "Improvements",
    "Amenities / Car Storage": "Improvements",
    "Room Count · Size · Quality · Condition": "Improvements",
}


def tabs_with_sections():
    """Group the flat CATALOG into (tab, [(section, fields), ...]) in TAB_ORDER.
    Unmapped sections fall to Improvements; a tab with no sections renders pending."""
    by_tab = {t: [] for t in TAB_ORDER}
    for section, fields in CATALOG:
        by_tab[SECTION_TAB.get(section, "Improvements")].append((section, fields))
    return [(t, by_tab[t]) for t in TAB_ORDER]


# ---------------------------------------------------------------------------
# HTML emit — mirrors the adopted Subject-Worksheet_TEMPLATE.html style.
# ---------------------------------------------------------------------------
CSS = """
  :root{--ink:#1a2330;--mut:#5b6776;--line:#dde3ea;--bg:#f7f9fc;--card:#fff;
        --red:#c0392b;--amber:#b9770e;--green:#1e7d4f;--blue:#2257a8;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:980px;margin:0 auto;padding:22px 18px 60px}
  h1{font-size:20px;margin:0 0 2px}
  .sub{color:var(--mut);margin:0 0 14px;font-size:13px}
  .tabs{display:flex;gap:6px;border-bottom:2px solid var(--line);margin:14px 0 0;flex-wrap:wrap}
  .tab{padding:8px 14px;cursor:pointer;border:1px solid var(--line);border-bottom:none;
       border-radius:7px 7px 0 0;background:#eef2f7;color:var(--mut);font-weight:600;font-size:13px}
  .tab.active{background:var(--card);color:var(--ink);box-shadow:0 -2px 0 var(--blue) inset}
  .panel{display:none;background:var(--card);border:1px solid var(--line);border-top:none;
         padding:16px 16px 20px;border-radius:0 0 8px 8px}
  .panel.active{display:block}
  h3{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--blue);
     margin:18px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}
  h3:first-child{margin-top:4px}
  table{width:100%;border-collapse:collapse;font-size:13.5px}
  td,th{padding:5px 9px;border-bottom:1px solid #eef1f5;vertical-align:top;text-align:left}
  td.f{width:40%;color:var(--mut);font-weight:600}
  td.v{width:46%}
  td.s{width:14%;color:var(--blue);font-size:11px;font-weight:600;white-space:nowrap}
  .star{color:var(--amber)}
  .flag{color:var(--amber);font-weight:600}
  .flagbox{border:1px solid var(--line);border-left:4px solid var(--red);background:#fff;
           border-radius:6px;padding:10px 14px;margin:12px 0}
  .flagbox h4{margin:0 0 6px;font-size:13px;color:var(--red)}
  .flagbox ol{margin:0;padding-left:18px}.flagbox li{margin:4px 0}
  .pending{color:var(--mut);font-style:italic;padding:18px 4px}
  .note{color:var(--mut);font-size:11.5px}
  .grid{font-size:12.5px}.grid th{background:#eef2f7;color:var(--mut);font-size:11.5px;text-transform:uppercase}
  .grid td:first-child,.grid th:first-child{color:var(--mut);font-weight:600}
  .legend{font-size:11.5px;color:var(--mut);margin:8px 0 0}
  .foot{margin-top:22px;border-top:1px solid var(--line);padding-top:10px;color:var(--mut);font-size:12px}
  .cert{display:inline-block;background:#fbe9ef;color:var(--red);border-radius:5px;padding:2px 9px;font-weight:700;font-size:12px}
"""

JS = """
  document.querySelectorAll('.tab').forEach(function(t){
    t.addEventListener('click',function(){
      document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
      t.classList.add('active');
      document.getElementById(t.dataset.p).classList.add('active');
    });
  });
"""


def esc(s):
    return html.escape(str(s))


_PANEL_IDS = {"Subject": "subj", "Neighborhood": "nbhd",
              "Site": "site", "Improvements": "impr"}

_LEGEND = ('    <p class="legend">Source: APEX = county portal · ZIL = Zillow · '
           'MLS = Matrix · PUB = public record/deed · INSP = confirm at inspection. '
           '&#9733; = field DataMaster tracks that the prior template omitted.</p>')


def _fields_table(fields):
    out = ["    <table>"]
    for (label, token, dm, mismo, src, forms, gap, note) in fields:
        star = ' <span class="star" title="DM tracks this; added by the dma audit">&#9733;</span>' if gap else ""
        ntitle = ' title="{}"'.format(esc(note)) if note else ""
        out.append(
            '      <tr><td class="f"{nt}>{lab}{st}</td>'
            '<td class="v">{{{{{tok}}}}}</td>'
            '<td class="s">{src}</td></tr>'.format(
                nt=ntitle, lab=esc(label), st=star, tok=token, src=esc(src)))
    out.append("    </table>")
    return "\n".join(out)


def data_tabs_html():
    """Emit the 4 DM/ACI subject-data panels: Subject · Neighborhood · Site · Improvements."""
    panels = []
    first = True
    for tab, sections in tabs_with_sections():
        pid = _PANEL_IDS.get(tab, tab.lower())
        cls = "panel active" if first else "panel"
        first = False
        out = ['<div class="{}" id="{}">'.format(cls, pid)]
        if not sections:
            out.append('    <p class="pending">Pending &mdash; added in a later build phase.</p>')
        for section, fields in sections:
            out.append("    <h3>{}</h3>".format(esc(section)))
            out.append(_fields_table(fields) if fields
                       else '    <p class="pending">Pending.</p>')
        out.append(_LEGEND)
        out.append("  </div>")
        panels.append("\n".join(out))
    return "\n\n".join(panels)


def extras_html():
    out = []
    for form, items in FORM_EXTRAS.items():
        lis = "".join("<li>{}</li>".format(esc(i)) for i in items)
        out.append('      <h3>{}</h3>\n      <ul class="note">{}</ul>'.format(esc(form), lis))
    return "\n".join(out)


COMP_ROWS = ["Address","Proximity","Sale price","Price / GLA sf","Data source / MLS#",
             "Sale / contract date","Location","Site (lot)","View","Design / style",
             "Quality","Year built","Condition","Room ct (Tot/Bd/Ba)","GLA above grade",
             "Basement","Heating / cooling","Garage / car storage","Porch / patio / deck",
             "Net adjustment","Adjusted price"]


def comp_grid_html():
    rows = []
    for r in COMP_ROWS:
        subj = "{{ADDRESS}}" if r == "Address" else ("&mdash;" if r in
               ("Proximity","Net adjustment","Adjusted price") else "")
        rows.append("      <tr><td>{}</td><td>{}</td><td></td><td></td><td></td><td></td></tr>"
                    .format(esc(r), subj))
    return "\n".join(rows)


def build_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ADDRESS}} &mdash; {{FORM}} Subject Worksheet (DM-complete)</title>
<!--
  VDV SUBJECT-WORKSHEET TEMPLATE  ·  DM-COMPLETE variant (generated)
  Field set audited against DataMaster's own .dma schema (368 fields / 113 files),
  ACI MISMO 2.6 XML (453 fields), and the delivered URAR/gPAR PDFs.
  Sections follow DM 1004 input order. Fields marked the star are ones DataMaster
  tracks that the prior hand template omitted.
  HOW TO USE: copy to the order folder, rename "<address>_worksheet.html",
  replace every {{TOKEN}}, delete flag <li>s you don't need, leave comp cells
  blank until the export lands. Self-contained — opens/prints anywhere.
  Regenerate via tools/dm-collection-sheet/build_collection_sheet.py.
-->
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <h1>{{{{ADDRESS}}}}, {{{{CITY_STATE_ZIP}}}} &nbsp;&middot;&nbsp; {{{{FORM}}}}</h1>
  <p class="sub">Subject worksheet &middot; {{{{COUNTY}}}} County &middot; due {{{{DUE}}}} &middot; assembled by {agent} from {{{{SOURCES}}}}.</p>

  <div class="flagbox">
    <h4>&#9888; Flags for the appraiser (not adjusted &mdash; your call)</h4>
    <ol>
      <li>{{{{FLAG_1}}}}</li>
      <li>{{{{FLAG_2}}}}</li>
    </ol>
  </div>

  <div class="tabs">
    <div class="tab active" data-p="subj">Subject</div>
    <div class="tab" data-p="nbhd">Neighborhood</div>
    <div class="tab" data-p="site">Site</div>
    <div class="tab" data-p="impr">Improvements</div>
    <div class="tab" data-p="hist">Sale / Listing History</div>
    <div class="tab" data-p="comps">Comp Grid</div>
    <div class="tab" data-p="forms">Form-specific</div>
  </div>

  <!-- SUBJECT -->
{subject}

  <!-- HISTORY -->
  <div class="panel" id="hist">
    <h3>Subject &mdash; current listing (if any)</h3>
    <table>
      <tr><td class="f">MLS # / Status</td><td class="v">{{{{MLS_STATUS}}}}</td></tr>
      <tr><td class="f">List price / DOM</td><td class="v">{{{{LIST_DOM}}}}</td></tr>
      <tr><td class="f">List / contract date</td><td class="v">{{{{LIST_DATES}}}}</td></tr>
      <tr><td class="f">Original list / price revisions</td><td class="v">{{{{PRICE_REV}}}}</td></tr>
      <tr><td class="f">List office / agent</td><td class="v">{{{{LIST_AGENT}}}}</td></tr>
    </table>
    <h3>Prior transfers &mdash; public record (3-yr disclosure)</h3>
    <table>
      <tr><td class="f">{{{{PRIOR_1_DATE}}}}</td><td class="v">{{{{PRIOR_1}}}}</td></tr>
      <tr><td class="f">{{{{PRIOR_2_DATE}}}}</td><td class="v">{{{{PRIOR_2}}}}</td></tr>
    </table>
    <p class="note">DM fields: ListingContractDate, OriginalListPrice, DaysOnMarket,
      MlsNumber, PriorSaleOrTransferDataSources, SettlementDate. Comps also need each
      comp's 3-yr prior sale + DOM (1004 requirement).</p>
  </div>

  <!-- COMP GRID -->
  <div class="panel" id="comps">
    <p class="pending">Fill once the closed-comp export lands. &ge;3 closed (segregate
      active/pending as listing analysis only); verify out-of-county GLA against that
      county's SOR; never enter unverified GLA.</p>
    <table class="grid">
      <tr><th>Feature</th><th>Subject</th><th>Comp 1</th><th>Comp 2</th><th>Comp 3</th><th>Comp 4</th></tr>
{comps}
    </table>
  </div>

  <!-- FORM-SPECIFIC -->
  <div class="panel" id="forms">
    <p class="note">Only fill the block matching this order's form. These are the
      extra required fields the base 1004 Subject tab doesn't cover.</p>
{extras}
  </div>

  <div class="foot">
    <span class="cert">NOT CERTIFIED</span> &nbsp; {agent} assembles + flags conflicts; the
    licensed appraiser verifies at inspection, judges all adjustments, and certifies.
    Never auto-submitted.
  </div>
</div>
<script>{js}</script>
</body>
</html>
""".format(css=CSS, js=JS, subject=data_tabs_html(), agent=COWORK_AGENT,
           comps=comp_grid_html(), extras=extras_html())


# ---------------------------------------------------------------------------
# Markdown emit — the orderly reference list.
# ---------------------------------------------------------------------------
def build_md():
    n_gap = sum(1 for _, fs in CATALOG for f in fs if f[6])
    n_tot = sum(len(fs) for _, fs in CATALOG)
    lines = []
    lines.append("# DataMaster subject data-collection — orderly field reference")
    lines.append("")
    lines.append("Derived by comparing **.dma** (DataMaster's own files: 368 inline field "
                 "names across 113 reports, 172 in every file) against **.XML** (ACI/MISMO "
                 "2.6: 453 fields) and the delivered **.PDF** reports. Ordered in DataMaster "
                 "1004 input order. **★ marks the {} (of {}) fields DataMaster tracks that the "
                 "prior hand template omitted.**".format(n_gap, n_tot))
    lines.append("")
    lines.append("Collect-from legend: **APEX** county portal · **ZIL** Zillow · **MLS** "
                 "Matrix · **PUB** public record/deed · **INSP** appraiser at inspection.")
    lines.append("")
    for tab, sections in tabs_with_sections():
        lines.append("## {} tab".format(tab))
        lines.append("")
        if not sections:
            lines.append("_Pending — added in a later build phase._")
            lines.append("")
            continue
        for section, fields in sections:
            lines.append("### {}".format(section))
            lines.append("")
            lines.append("| Field | DataMaster field name(s) | MISMO (XML) | Collect | Note |")
            lines.append("|---|---|---|---|---|")
            for (label, token, dm, mismo, src, forms, gap, note) in fields:
                mark = "★ " if gap else ""
                dmn = "`" + "`, `".join(dm) + "`" if dm else "—"
                mis = "`" + "`, `".join(mismo) + "`" if mismo else "—"
                lines.append("| {}{} | {} | {} | {} | {} |".format(
                    mark, label, dmn, mis, src, note))
            lines.append("")
    lines.append("## Form-specific extras (beyond the base 1004 Subject tab)")
    lines.append("")
    for form, items in FORM_EXTRAS.items():
        lines.append("**{}** — {}".format(form, "; ".join(items)))
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate the DM data-collection sheet + reference")
    ap.add_argument("--html", required=True, help="Output HTML template path")
    ap.add_argument("--md", required=True, help="Output Markdown reference path")
    args = ap.parse_args(argv)
    with open(args.html, "w", encoding="utf-8") as f:
        f.write(build_html())
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(build_md())
    n_gap = sum(1 for _, fs in CATALOG for f in fs if f[6])
    n_tot = sum(len(fs) for _, fs in CATALOG)
    print("Wrote {} and {} | {} fields ({} dma-audit additions)".format(
        args.html, args.md, n_tot, n_gap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
