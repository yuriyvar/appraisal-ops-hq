# Claude Code Brief — 2026-06-18
## Gas utility availability check — wire into worksheet-builder + county-registry + memory

**Requested by:** Cowork/Bob, 2026-06-18 session  
**Urgency:** Next Code session — low urgency, no blocker

---

## What happened (context)

While building the 1214 Hillside Ave worksheet, Bob looked up gas availability via
Richmond Gas Works' ArcGIS tool and found: *"gas available in area but not at this
address."* This changed the subject's utility profile — forced air heating is likely
NOT gas (probably heat pump or oil), to be confirmed at inspection.

The lookup was manual and ad-hoc. It should be a standard step in the subject data
pull checklist so it's never skipped.

---

## Tasks (all three, in order)

### Task 1 — Add gas utility lookup to `skills/worksheet-builder/SKILL.md`

In the **Subject data pull checklist**, after Source 2 (Zillow), add a new **Source 3 —
Gas utility availability** block:

```markdown
### Source 3 — Gas utility availability
Check the local gas provider's online availability tool BEFORE flagging fuel as unknown:
- **Henrico / Richmond City / N. Chesterfield** → Richmond Gas Works ArcGIS tool:
  `https://cor.maps.arcgis.com/apps/webappviewer/index.html?id=32fb679315c0451e88f80402a4deb1a5`
  Search address → click on the street/parcel area (NOT the search result pin) → read the popup.
  Three outcomes:
  - "Natural gas is available" → gas connected; heating fuel is likely gas
  - "Service can be brought to it" → gas NOT currently connected; heating fuel is NOT gas
  - No result / outside boundary → outside service area; no gas
- **Other counties** → check `references/county-registry.md` for the provider + lookup URL.
  If none listed, note "gas provider unknown — confirm at inspection."
Record the result in the subject's Utilities row (Gas: Connected / Available-not-connected /
Not available) and adjust the heating fuel inference accordingly.
```

Also update the **Output before moving to comps** paragraph to include Gas utility as a
required field (alongside the other utilities).

### Task 2 — Add Richmond Gas Works to `skills/property-search/references/county-registry.md`

On the **Henrico** row (and Richmond City row if present), add:
- **Gas provider:** Richmond Gas Works (City of Richmond Dept of Public Utilities)
- **Gas availability lookup:** `https://cor.maps.arcgis.com/apps/webappviewer/index.html?id=32fb679315c0451e88f80402a4deb1a5`
- **How to use:** Search address → click street/parcel area (not the pin) → read popup

Richmond Gas Works serves: City of Richmond, Henrico County, northern Chesterfield.
So the same URL applies to all three.

### Task 3 — Add to Code memory ("the rock")

Add a memory entry (e.g. `~/.claude/projects/.../memory/gas-utility-check.md` or
append to an existing startup/skills memory file) with:

```
Gas utility lookup is now a standard step in worksheet-builder subject data pull (Source 3).
For Henrico / Richmond City / N. Chesterfield: use Richmond Gas Works ArcGIS tool —
https://cor.maps.arcgis.com/apps/webappviewer/index.html?id=32fb679315c0451e88f80402a4deb1a5
Click street/parcel area (not the address pin) to get the availability popup.
Result "not at this location, can be brought to it" = no gas connection = heating fuel is NOT gas.
```

Update `MEMORY.md` index if one exists.

---

### Task 4 — Build the Virginia gas providers SQLite reference database

**Purpose:** worksheet-builder Source 3 needs to know WHICH provider covers a given county,
and whether an instant online lookup exists. Hard-coding per-county URLs in SKILL.md won't
scale. Build a SQLite DB that Code and skills can query by county name → get provider +
lookup URL + method.

**File location:** `appraisal-ops-hq/skills/property-search/references/va-gas-providers.sqlite`

#### Schema

```sql
CREATE TABLE va_gas_providers (
  id                INTEGER PRIMARY KEY,
  provider_name     TEXT NOT NULL,
  also_known_as     TEXT,
  parent_company    TEXT,
  service_area_desc TEXT,       -- free-text human summary
  lookup_url        TEXT,       -- URL for availability check (NULL if phone-only)
  lookup_method     TEXT,       -- see values below
  lookup_notes      TEXT,       -- how-to notes for Bob / Code using the tool
  phone             TEXT,
  website           TEXT,
  last_verified     TEXT        -- ISO date
);

-- lookup_method values:
--   instant_map    → interactive map, result in seconds (e.g. ArcGIS)
--   zip_checker    → enter zip code, instant yes/no
--   map_only       → static/territory map; no address-level check; call to confirm
--   form_callback  → submit form; response via phone callback (days, not instant)
--   phone_only     → no online tool; call the provider

CREATE TABLE va_gas_provider_counties (
  id           INTEGER PRIMARY KEY,
  provider_id  INTEGER REFERENCES va_gas_providers(id),
  county_city  TEXT NOT NULL   -- e.g. "Henrico County" or "Richmond City"
);

-- Usage pattern (lookup by county):
--   SELECT p.provider_name, p.lookup_method, p.lookup_url, p.lookup_notes, p.phone
--   FROM va_gas_providers p
--   JOIN va_gas_provider_counties c ON c.provider_id = p.id
--   WHERE c.county_city = 'Henrico County';
```

#### Seed data (all 9 SCC-regulated VA providers as of 2026-06-18)

| id | provider_name | also_known_as | parent_company | lookup_method | lookup_url | phone | website |
|----|--------------|--------------|---------------|--------------|-----------|-------|---------|
| 1 | Richmond Gas Works | Richmond DPU Gas | City of Richmond Dept of Public Utilities | instant_map | https://cor.maps.arcgis.com/apps/webappviewer/index.html?id=32fb679315c0451e88f80402a4deb1a5 | 804-646-4646 | https://richmondgasworks.com |
| 2 | Columbia Gas of Virginia | — | NiSource | form_callback | https://www.columbiagasva.com/services/add-or-convert-to-gas/gas-availability-form | 1-800-440-6111 | https://www.columbiagasva.com |
| 3 | Virginia Natural Gas | — | Southern Company Gas | zip_checker | https://www.virginianaturalgas.com/company/our-service-area.html | 1-866-229-3578 | https://www.virginianaturalgas.com |
| 4 | Washington Gas | Washington Gas Light Company | AltaGas | map_only | https://www.washingtongas.com/services/contractors/service-territory | 1-844-927-4427 | https://www.washingtongas.com |
| 5 | Roanoke Gas Company | — | RGC Resources | phone_only | NULL | 540-777-4427 | https://roanokegas.com |
| 6 | Shenandoah Gas | Shenandoah Gas Division | Washington Gas | map_only | https://www.washingtongas.com/services/contractors/service-territory | 1-844-927-4427 | https://www.washingtongas.com |
| 7 | Atmos Energy | — | Atmos Energy Corporation | form_callback | https://www.atmosenergy.com/account-support/start-stop-transfer | 1-888-286-6700 | https://www.atmosenergy.com |
| 8 | Appalachian Natural Gas Distribution Company | — | — | phone_only | NULL | NULL | NULL |
| 9 | Southwestern Virginia Gas Company | — | — | phone_only | NULL | NULL | NULL |

**lookup_notes for each provider:**

- **Richmond Gas Works (1):** Search address → click on the STREET or PARCEL AREA (NOT the
  address-result pin). Popup shows one of three results: (a) gas connected, (b) "available
  in area but not at this address — can be extended", (c) outside service area.
  Result (b) means heating is NOT gas.

- **Columbia Gas of Virginia (2):** Submit form with name, phone, address. Callback within
  2 business days. Not instant. Faster to call 1-800-440-6111.

- **Virginia Natural Gas (3):** Enter ZIP code on service area page to confirm zone coverage.
  If ZIP is in zone, call to confirm individual address is serviceable.

- **Washington Gas (4):** Map shows service territory by area. No address-level instant check.
  Confirm by phone for specific address.

- **Roanoke Gas (5), Shenandoah Gas (6), Atmos (7), Appalachian (8), SW Virginia Gas (9):**
  Call provider directly to check address-level availability.

**County → provider assignments:**

```
Richmond City         → Richmond Gas Works (1)
Henrico County        → Richmond Gas Works (1)
Chesterfield County   → Richmond Gas Works (1) [northern only; Columbia Gas (2) for southern]

Albemarle County      → Columbia Gas of Virginia (2)
Augusta County        → Columbia Gas of Virginia (2)
Bath County           → Columbia Gas of Virginia (2)
Culpeper County       → Columbia Gas of Virginia (2)
Frederick County      → Columbia Gas of Virginia (2) [also Washington Gas overlap]
Greene County         → Columbia Gas of Virginia (2)
Highland County       → Columbia Gas of Virginia (2)
Madison County        → Columbia Gas of Virginia (2)
Nelson County         → Columbia Gas of Virginia (2)
Orange County         → Columbia Gas of Virginia (2)
Rockbridge County     → Columbia Gas of Virginia (2)
Waynesboro City       → Columbia Gas of Virginia (2)
Staunton City         → Columbia Gas of Virginia (2)
Harrisonburg City     → Columbia Gas of Virginia (2)
Fredericksburg City   → Columbia Gas of Virginia (2)

Virginia Beach City   → Virginia Natural Gas (3)
Norfolk City          → Virginia Natural Gas (3)
Chesapeake City       → Virginia Natural Gas (3)
Portsmouth City       → Virginia Natural Gas (3)
Suffolk City          → Virginia Natural Gas (3)
Isle of Wight County  → Virginia Natural Gas (3)
James City County     → Virginia Natural Gas (3)
York County           → Virginia Natural Gas (3)
Newport News City     → Virginia Natural Gas (3)
Hampton City          → Virginia Natural Gas (3)
Williamsburg City     → Virginia Natural Gas (3)
Poquoson City         → Virginia Natural Gas (3)

Arlington County      → Washington Gas (4)
Fairfax County        → Washington Gas (4)
Alexandria City       → Washington Gas (4)
Falls Church City     → Washington Gas (4)
Manassas City         → Washington Gas (4)
Manassas Park City    → Washington Gas (4)
Prince William County → Washington Gas (4)
Loudoun County        → Washington Gas (4)
Fauquier County       → Washington Gas (4)
Clarke County         → Washington Gas (4) [also Shenandoah Gas overlap]
Warren County         → Washington Gas (4) [also Shenandoah Gas overlap]

Roanoke City          → Roanoke Gas (5)
Roanoke County        → Roanoke Gas (5)
Salem City            → Roanoke Gas (5)
Montgomery County     → Roanoke Gas (5)
Botetourt County      → Roanoke Gas (5)
Craig County          → Roanoke Gas (5)

Shenandoah County     → Shenandoah Gas (6)
Page County           → Shenandoah Gas (6)
Rockingham County     → Shenandoah Gas (6) [also Columbia Gas overlap]

Wise County           → Atmos Energy (7)
Scott County          → Atmos Energy (7)
Lee County            → Atmos Energy (7)
Dickenson County      → Atmos Energy (7)
Buchanan County       → Atmos Energy (7)
Russell County        → Atmos Energy (7)
Tazewell County       → Atmos Energy (7)
Washington County     → Atmos Energy (7)
Smyth County          → Atmos Energy (7)
Bland County          → Atmos Energy (7)
Wythe County          → Atmos Energy (7)
Carroll County        → Atmos Energy (7)
Grayson County        → Atmos Energy (7)
```

> **Note on overlaps:** A few counties have two providers (e.g. Chesterfield has RGW in
> the north, Columbia Gas further south). Insert BOTH rows in `va_gas_provider_counties`
> and add a note in `lookup_notes`. At query time, if two rows return, present both to
> the user and note the overlap.

#### After building the DB — also update

1. **`skills/worksheet-builder/SKILL.md` Source 3 block** (Task 1 above): replace the
   hardcoded Henrico/Richmond/N. Chesterfield URL with a reference to the DB lookup:
   ```
   For any county: query `references/va-gas-providers.sqlite` by county name
   to get the provider + lookup_method + lookup_url. See Task 4 of this brief.
   ```

2. **`skills/property-search/references/county-registry.md`** (Task 2 above): same — add
   a `gas_provider_db` reference note to the Henrico, Richmond City, and Chesterfield rows,
   instead of inlining the full URL (the DB is the source of truth now).

3. **Code memory ("the rock")** (Task 3 above): also mention the DB path so Code knows
   where to look it up.

#### Verification step
After creating the DB, run this query and confirm it returns one row for Henrico with
`lookup_method = instant_map`:
```sql
SELECT p.provider_name, p.lookup_method, p.lookup_url
FROM va_gas_providers p
JOIN va_gas_provider_counties c ON c.provider_id = p.id
WHERE c.county_city = 'Henrico County';
```

---

## What NOT to do

- Do NOT open a kaizen branch — these are skill edits, not `vault/20-standard-work/` SOPs.
- Do NOT skip Task 3 — the memory entry ensures Code applies this on the next order
  without re-reading the skill from scratch.
- Do NOT inline all provider URLs into SKILL.md or county-registry — the DB is the source
  of truth; skill files just reference it.

---

## Reply-to

`interlane/INBOX-for-Cowork.md` — confirm tasks done + commit hash.
