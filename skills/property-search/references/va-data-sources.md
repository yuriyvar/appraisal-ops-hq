# Virginia county data sources (assessment + GIS)

> Routing/adapters + comp-source flags now live in `county-registry.md`.
> This file remains the endpoint/quirk detail mirror.
> Cross-cutting source quirks & handling fixes: see `data-quirks.md`.

**Source of truth: the "VA Counties Assessment & GIS Records" tab of the
Operational Records Google Sheet** (doc `12zZgU1ULHasOrgh_WHDOME40HdqEkKIL`,
gid `686822370`). Yuriy adds counties there. This file is the skill's local
mirror — reconcile per the skill's Step 1 (fetch the tab as CSV via the
logged-in Chrome session: `/gviz/tq?tqx=out:csv&gid=686822370`).
Last reconciled: 2026-06-11.

Deep links in the sheet often carry session/state params; this mirror keeps
durable base URLs (marked ⚓ where the sheet has a deeper link). Endpoint and
quirk columns are discovered on real orders — record them as you go.

## Vendor patterns (recognize these, reuse the technique)
- **civ.quest / CivQuest** (Caroline, Chesapeake, Franklin, Hanover, New Kent,
  Powhatan): ArcGIS Experience apps; find the live FeatureServer via
  `performance.getEntriesByType('resource')` — same pipeline as Hanover.
- **gis.vgsi.com (Vision)**: assessment cards searchable by address; parcel page
  URL pattern `/Parcel.aspx?Pid=N`.
- **actdatascout.com**: common assessment portal (Alleghany, Falls Church,
  Fauquier, Fluvanna alt, Frederick, Richmond City, Salem, Shenandoah,
  Southampton, Tazewell, Waynesboro).
- **webgis.net**: lightweight county GIS (Amelia, Fluvanna, Galax, Halifax).
- **interactivegis.com**: Buckingham, Cumberland, Nottoway, Rockingham.
- **qPublic (schneidercorp)**: Hopewell.
- **ConciseCAMA (concisesystems.com)** (Mecklenburg, Orange): ASP.NET CAMA portal; search by
  Address / Owner / Map; parcel detail at `PropertyPage.aspx?id=<PRN>`. `web_fetch` is **blocked** by
  a `Disclaimer.aspx` cookie gate, so use a **logged-in browser tab** — which also allows an **in-page
  synchronous XHR batch-pull** of a whole project's parcels (Sale Histories, Heated Sq Ft, Bedrooms,
  TOTALS, Land Segments incl. **DOCK/BUOY** premium). Invaluable for **1073 same-project comps when MLS
  isn't reachable** (e.g. Mecklenburg / Kerr Lake, a Navica market).

## Counties / cities

| Jurisdiction | Assessment | GIS / parcel map | Live REST endpoint / quirks |
|---|---|---|---|
| Albemarle Co | — | https://experience.arcgis.com/experience/fdf2f078208c487ebf7a733ab3a38db2 | |
| Alleghany Co | https://www.actdatascout.com/RealProperty/Virginia/Alleghany | — | |
| Amelia Co | https://eservices.ameliacova.com/Applications/TXApps/PropCardsIndex.htm | https://www.webgis.net/va/amelia/ | |
| Amherst Co | — | https://experience.arcgis.com/experience/45d7ce9ea48c44cdb1e35afc94aa62e9 | |
| Appomattox Co | https://appomattox-gov-revmgt.secure.openrda.net/portal/ | https://experience.arcgis.com/experience/dc7e850b09a64019a04398dadaba2729/page/Map | Same GIS URL listed for Bedford — verify which is right |
| Bedford Co | — | https://experience.arcgis.com/experience/dc7e850b09a64019a04398dadaba2729/page/Map | Duplicate of Appomattox GIS URL in sheet — verify |
| Brunswick Co | https://eservices.brunswickco.com/applications/txapps/PropCardsIndex.htm | — | |
| Buckingham Co | — | https://buckcova.interactivegis.com/map/ | |
| Campbell Co | — | https://parcelviewer.geodecisions.com/Campbell/Account/Logon | Logon page — may need account |
| Caroline Co | — | https://caroline.civ.quest/ ⚓ | CivQuest — Hanover technique applies |
| Charles City Co | — | https://charlescityvagis.maps.arcgis.com/apps/webappviewer/index.html ⚓ | |
| Charlottesville City | — | — | TODO: sources needed |
| Chesapeake City | https://chesapeake.civ.quest/ ⚓ | — | CivQuest |
| Chesterfield Co | https://www.chesterfield.gov/828/Real-Estate-Assessment-Data (also READ portal: https://read.chesterfield.gov) | https://opengisdata.chesterfield.gov/datasets/62be4db4758b4492a7b0b524cf51188a_7/explore | **Live FeatureServer (ParcelsEnriched):** `https://services3.arcgis.com/TsynfzBSE6sXfoLq/arcgis/rest/services/Cadastral_ProdA/FeatureServer/3` — fields: TaxID (14-digit no-dash), HouseNum, StreetName, StreetType, GPIN, OwnerName, YearBuilt, FinishedArea, Bedrooms, FullBath, HalfBath, SaleDate, SalePrice, FairMarketValue, SubdivisionName. Matrix shows TaxID with dashes (e.g. 722-67-00-30-900-133); strip dashes for API/ArcGIS. **New-construction condo quirk:** even-numbered sides of new condo streets (e.g. Hancock Towns DR) may remain under undivided builder parcels (OwnerName=builder, SF=0) for 1-2 yrs after construction — no individual Tax ID will exist yet; Matrix/CoreLogic also blank. **GLA validation — Dimensions section:** on the parcel detail page → Residential tab → expand "Dimensions" to see floor-by-floor area breakdown (F1=1st floor finished, F2=2nd floor finished, DA=daylight basement, OH=overhang, WD=wood deck, OP=open porch, etc.). Sum of finished stories (F1+F2+any finished basement) must reconcile to the ft² shown in the Residential Buildings header. Always cross-check Dimensions when GLA is disputed. Example: 7861 Alexandria Dr → F1=608+F2=608+DA(finished portion) = 1586 ft² total. |
| Cumberland Co | https://eservices.cumberlandcounty.virginia.gov/applications/txapps/PropCardsIndex.htm | https://cumberland.interactivegis.com/map/ | |
| Dinwiddie Co | — | https://gis.vgsi.com/dinwiddieva/Parcel.aspx ⚓ | Vision |
| Essex Co | https://gis.vgsi.com/essexva/Search.aspx | https://essex-county-virginia-gis-portal-essex-virginia.hub.arcgis.com/apps/7df57207953741a1896c8c4629469d76/explore | |
| Fairfax Co | https://icare.fairfaxcounty.gov/ffxcare/Main/Home.aspx | — | |
| Falls Church City | https://www.actdatascout.com/RealProperty/Virginia/FallsChurch | — | |
| Farmville (town) | — | https://experience.arcgis.com/experience/f0ddae8440004153a4df01231b281db9/page/Map | |
| Fauquier Co | https://www.actdatascout.com/RealProperty/Virginia/Fauquier | — | |
| Fluvanna Co | https://gis.vgsi.com/fluvannacountyva/Search.aspx (alt: https://www.actdatascout.com/RealProperty/Virginia/Fluvanna) | https://www.webgis.net/va/fluvanna/ | Two assessment sources in sheet |
| Franklin City | — | https://franklin.civ.quest/ ⚓ | CivQuest |
| Frederick Co | https://www.actdatascout.com/RealProperty/Virginia/Frederick | — | |
| Galax City | — | https://www.webgis.net/va/galax/ | |
| Goochland Co | — | https://gis.co.goochland.va.us/GoochlandPV/ | |
| Greene Co | https://treasurer.gcva.us/applications/txapps/PropCardsIndex.htm | — | |
| Halifax Co | (tax card available from within GIS form) | https://www.webgis.net/va/halifax/ | |
| Hampton City | https://webgis2.hampton.gov/sites/ParcelViewer/ | — | |
| Hanover Co | (via parcel map Summary tab) | https://parcelmap.hanovercounty.gov/ ⚓ | **Live:** `maps.civ.quest/arcgis/rest/services/Hanover/Public/FeatureServer` — Tax Parcels=0, Summary=31, Improvements=34, Sales=38. SALEDATE is ISO string; GPIN is join key; Sales has no geometry. AGO mirror "HanoverCivQuest" is STALE (sales end 2025-04). |
| Henrico Co | https://realestate.henrico.gov/ (APEX; enter at ROOT, deep link :1 = 410 firewall) | open-data parcel layer is a 735-row SAMPLE — NOT usable | **No queryable sales layer -> MLS-only for comps.** Subject via APEX assessment search. |
| Hopewell City | https://qpublic.schneidercorp.com/Application.aspx ⚓ | — | qPublic |
| King George Co | https://www.kinggeorgecountyva.gov/2269/Vision-Property-Card-Search | https://www.arcgis.com/apps/webappviewer/index.html ⚓ | |
| King William Co | https://gis.vgsi.com/KingWilliam2023VA/Search.aspx | — | Vision |
| Loudoun Co | https://reparcelasmt.loudoun.gov/pt/search/commonsearch.aspx ⚓ | — | |
| Louisa Co | https://louweb.louisa.org/assess/master_Q.asp | https://www.louisacounty.gov/2836/GIS-Mapping | Sheet spells "Lousa" |
| Lynchburg City | — | https://mapviewer.lynchburgva.gov/ParcelViewer/Account/Logon | Logon page — may need account |
| Martinsville City | https://gis.vgsi.com/martinsvilleVA/Search.aspx | — | Vision |
| Mecklenburg Co / Kerr Lake | https://mecklenburg.cama.concisesystems.com/Search.aspx (ConciseCAMA) | — | **MLS = Navica (Lake Country)**, not CVR (CVR returned 0 condo sales for 23927 over 5 yr). Parcel detail `PropertyPage.aspx?id=<PRN>`; `web_fetch` blocked by `Disclaimer.aspx` cookie gate → logged-in browser tab + in-page synchronous XHR batch-pulls a whole condo project's Sale Histories / Heated Sq Ft / Bedrooms / TOTALS / Land Segments (incl. **DOCK/BUOY** premium). Use for 1073 same-project comps when MLS isn't reachable. Surrounding comp set: Lunenburg, Charlotte, Halifax, Brunswick + NC Kerr Lake shore (Vance/Granville/Warren NC). |
| New Kent Co | https://gis.vgsi.com/newkentcountyva/Search.aspx | https://atlas.civ.quest/newkent_va | Vision + CivQuest |
| Nottoway Co | https://eservices.nottoway.org/Applications/TXApps/PropCardsIndex.htm | https://nottowaycova.interactivegis.com/map/ | |
| Orange Co | https://orange.cama.concisesystems.com/Search.aspx | — | |
| Page Co | https://eservices.pagecounty.virginia.gov/applications/txapps/PropCardsIndex.htm | https://www.pagecountygis.com/ ⚓ | |
| Petersburg City | — | https://parcelviewer.geodecisions.com/Petersburg/ | |
| Powhatan Co | https://keynet.powhatanva.gov/webpaas/ ⚓ | https://powhatan.civ.quest/ ⚓ | CivQuest. AGO has hosted "Vision_Powhatan" FeatureServer (services1.arcgis.com/ue5fMdTkPeHLCobS/.../Vision_Powhatan) incl. VISION_SALEHIST — verify freshness before relying on it |
| Prince Edward Co | https://epayments.co.prince-edward.va.us/applications/txapps/VPCindex.htm | — | **MLS = Navica (Lake Country)**, not CVR (Southside; CVR ~0 sales). Surrounding comp set: Buckingham, Appomattox, Charlotte, Cumberland, Nottoway, Lunenburg. |
| Richmond City | https://www.actdatascout.com/RealProperty/Virginia/Richmond | https://cor.maps.arcgis.com/apps/instant/basic/index.html ⚓ | |
| Rockingham Co | — | https://rockcova.interactivegis.com/map/ | |
| Salem City | https://www.actdatascout.com/RealProperty/Virginia/Salem | — | |
| Shenandoah Co | https://www.actdatascout.com/RealProperty/Virginia/Shenandoah | — | |
| Southampton Co | https://www.actdatascout.com/RealProperty/Virginia/Southampton | — | |
| Spotsylvania Co | https://www.spotsylvania.va.us/505/2025-Assessment-Search | https://experience.arcgis.com/experience/c73ae0e1367d408a835840aeb713614a | |
| Staunton City | https://gis.vgsi.com/stauntonva/Search.aspx | https://stauntonvabusiness.giswebtechguru.com/ ⚓ | Vision |
| Sussex Co | https://eservices.sussexcountyva.gov/applications/txapps/PropCardsIndex.htm | https://www.arcgis.com/apps/mapviewer/index.html ⚓ | |
| Tazewell Co | https://www.actdatascout.com/RealProperty/Virginia/Tazewell | — | |
| Waynesboro City | https://www.actdatascout.com/RealProperty/V