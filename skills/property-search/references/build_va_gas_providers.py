#!/usr/bin/env python3
"""Build va-gas-providers.sqlite — the VA natural-gas provider/county reference DB.

Source of truth for worksheet-builder Source 3 (gas utility availability check) and
county-registry gas rows. Query by county -> provider + lookup_method + lookup_url + notes.

Stdlib only (sqlite3). Idempotent: drops + rebuilds both tables on each run.
Provenance: docs/2026-06-18_gas-utility-check-step_claude-code-brief.md (Task 4 spec).
Run:  python build_va_gas_providers.py
"""
import os
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "va-gas-providers.sqlite")
LV = "2026-06-18"  # last_verified (ISO)

# (id, provider_name, also_known_as, parent_company, service_area_desc,
#  lookup_url, lookup_method, lookup_notes, phone, website, last_verified)
PROVIDERS = [
    (1, "Richmond Gas Works", "Richmond DPU Gas",
     "City of Richmond Dept of Public Utilities",
     "City of Richmond, Henrico County, and northern Chesterfield County.",
     "https://cor.maps.arcgis.com/apps/webappviewer/index.html?id=32fb679315c0451e88f80402a4deb1a5",
     "instant_map",
     "Search address -> click the STREET or PARCEL AREA (NOT the address-result pin). "
     "Popup shows one of three results: (a) natural gas connected; (b) 'available in area "
     "but not at this address - can be brought to it'; (c) outside service area. "
     "Result (b) means heating fuel is NOT gas. Chesterfield is split: RGW serves the NORTH, "
     "Columbia Gas (id 2) the south - if both rows return, present both.",
     "804-646-4646", "https://richmondgasworks.com", LV),

    (2, "Columbia Gas of Virginia", None, "NiSource",
     "Central/Piedmont, Shenandoah Valley, and Fredericksburg areas; southern Chesterfield County.",
     "https://www.columbiagasva.com/services/add-or-convert-to-gas/gas-availability-form",
     "form_callback",
     "Submit form (name, phone, address); callback within ~2 business days - not instant. "
     "Faster to call 1-800-440-6111. Overlaps: southern Chesterfield (RGW id 1 = north), "
     "Frederick (Washington Gas id 4), Rockingham (Shenandoah Gas id 6).",
     "1-800-440-6111", "https://www.columbiagasva.com", LV),

    (3, "Virginia Natural Gas", None, "Southern Company Gas",
     "Hampton Roads / Tidewater region.",
     "https://www.virginianaturalgas.com/company/our-service-area.html",
     "zip_checker",
     "Enter ZIP on the service-area page to confirm zone coverage. If the ZIP is in zone, "
     "call to confirm the individual address is serviceable.",
     "1-866-229-3578", "https://www.virginianaturalgas.com", LV),

    (4, "Washington Gas", "Washington Gas Light Company", "AltaGas",
     "Northern Virginia.",
     "https://www.washingtongas.com/services/contractors/service-territory",
     "map_only",
     "Territory map shows coverage by area; no address-level instant check - confirm by phone "
     "for a specific address. Overlaps: Frederick (Columbia Gas id 2), Warren & Clarke "
     "(Shenandoah Gas id 6).",
     "1-844-927-4427", "https://www.washingtongas.com", LV),

    (5, "Roanoke Gas Company", None, "RGC Resources",
     "Roanoke Valley.",
     None, "phone_only",
     "No online address-level tool. Call the provider directly to check availability.",
     "540-777-4427", "https://roanokegas.com", LV),

    (6, "Shenandoah Gas", "Shenandoah Gas Division", "Washington Gas",
     "Northern Shenandoah Valley.",
     "https://www.washingtongas.com/services/contractors/service-territory",
     "map_only",
     "Washington Gas division; territory map only, no address-level instant check - call to "
     "confirm. Overlaps: Rockingham (Columbia Gas id 2), Warren & Clarke (Washington Gas id 4).",
     "1-844-927-4427", "https://www.washingtongas.com", LV),

    (7, "Atmos Energy", None, "Atmos Energy Corporation",
     "Far Southwest Virginia.",
     "https://www.atmosenergy.com/account-support/start-stop-transfer",
     "form_callback",
     "Submit the start/stop/transfer form (response via callback, not instant); or call "
     "1-888-286-6700 to check address-level availability.",
     "1-888-286-6700", "https://www.atmosenergy.com", LV),

    (8, "Appalachian Natural Gas Distribution Company", None, None,
     "Southwest Virginia (limited distribution).",
     None, "phone_only",
     "No online tool and no published phone in this reference. Call the provider directly.",
     None, None, LV),

    (9, "Southwestern Virginia Gas Company", None, None,
     "Southwest Virginia.",
     None, "phone_only",
     "No online tool and no published phone in this reference. Call the provider directly.",
     None, None, LV),
]

# provider_id -> list of jurisdictions. Overlap counties intentionally appear under BOTH
# providers (Chesterfield 1+2, Frederick 2+4, Rockingham 2+6, Warren 4+6, Clarke 4+6).
COUNTIES = {
    1: ["Richmond City", "Henrico County", "Chesterfield County"],
    2: ["Chesterfield County", "Albemarle County", "Augusta County", "Bath County",
        "Culpeper County", "Frederick County", "Greene County", "Highland County",
        "Madison County", "Nelson County", "Orange County", "Rockbridge County",
        "Rockingham County", "Waynesboro City", "Staunton City", "Harrisonburg City",
        "Fredericksburg City"],
    3: ["Virginia Beach City", "Norfolk City", "Chesapeake City", "Portsmouth City",
        "Suffolk City", "Isle of Wight County", "James City County", "York County",
        "Newport News City", "Hampton City", "Williamsburg City", "Poquoson City"],
    4: ["Arlington County", "Fairfax County", "Alexandria City", "Falls Church City",
        "Manassas City", "Manassas Park City", "Prince William County", "Loudoun County",
        "Fauquier County", "Clarke County", "Warren County", "Frederick County"],
    5: ["Roanoke City", "Roanoke County", "Salem City", "Montgomery County",
        "Botetourt County", "Craig County"],
    6: ["Shenandoah County", "Page County", "Rockingham County", "Clarke County",
        "Warren County"],
    7: ["Wise County", "Scott County", "Lee County", "Dickenson County", "Buchanan County",
        "Russell County", "Tazewell County", "Washington County", "Smyth County",
        "Bland County", "Wythe County", "Carroll County", "Grayson County"],
}


def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON;")
    con.executescript("""
        DROP TABLE IF EXISTS va_gas_provider_counties;
        DROP TABLE IF EXISTS va_gas_providers;

        CREATE TABLE va_gas_providers (
          id                INTEGER PRIMARY KEY,
          provider_name     TEXT NOT NULL,
          also_known_as     TEXT,
          parent_company    TEXT,
          service_area_desc TEXT,
          lookup_url        TEXT,
          lookup_method     TEXT,
          lookup_notes      TEXT,
          phone             TEXT,
          website           TEXT,
          last_verified     TEXT
        );

        CREATE TABLE va_gas_provider_counties (
          id           INTEGER PRIMARY KEY,
          provider_id  INTEGER REFERENCES va_gas_providers(id),
          county_city  TEXT NOT NULL
        );
        CREATE INDEX idx_county ON va_gas_provider_counties(county_city);
    """)
    con.executemany(
        "INSERT INTO va_gas_providers VALUES (?,?,?,?,?,?,?,?,?,?,?)", PROVIDERS)
    rows = [(pid, cc) for pid, ccs in COUNTIES.items() for cc in ccs]
    con.executemany(
        "INSERT INTO va_gas_provider_counties (provider_id, county_city) VALUES (?,?)", rows)
    con.commit()
    print(f"providers={con.execute('SELECT COUNT(*) FROM va_gas_providers').fetchone()[0]} "
          f"county_rows={con.execute('SELECT COUNT(*) FROM va_gas_provider_counties').fetchone()[0]}")
    con.close()


if __name__ == "__main__":
    main()
