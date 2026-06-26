#!/usr/bin/env python3
"""
Build A — Appraisal worksheet renderer.

Turns an `appraisal-record.json` (conforming to appraisal-record.schema.json)
into a single self-contained, tabbed `worksheet.html` for copy-paste into ACI.

Design rules (per ADR-002 / session handoff 2026-06-13):
  * Deterministic. Same input -> same output. NO external/network calls.
  * Stdlib only. No pip installs.
  * Single-file HTML output (CSS + JS inlined) so the appraiser can open it
    anywhere and copy fields straight into the form.
  * The agent ASSEMBLES; the licensed appraiser judges adjustments & certifies.
    This renderer therefore shows data + flags, and leaves the adjustment grid
    for the appraiser.

Tabs: Subject · Comp grid · Sale/Listing history · Photos · Map.

Usage:
    python render_worksheet.py RECORD.json [-o OUTPUT.html]
    # default output: <record_dir>/worksheet.html
"""

import argparse
import html
import json
import os
import sys
from datetime import datetime

SCHEMA_VERSION_SUPPORTED = "1.0"


# ----------------------------------------------------------------------------
# small safe-access / formatting helpers
# ----------------------------------------------------------------------------
def g(obj, *path, default=None):
    """Safe nested get. g(rec,'subject','characteristics','gla_sf')."""
    cur = obj
    for key in path:
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return default
        if cur is None:
            return default
    return cur if cur is not None else default


def esc(v):
    """HTML-escape any value; None/'' -> em dash placeholder handled by dash()."""
    if v is None:
        return ""
    return html.escape(str(v))


def safe_url(u):
    """Return the URL only if it uses an http(s) scheme (or is a bare relative
    path). Anything else (javascript:, data:, file:, ...) is rejected so it can
    be rendered as inert text instead of a live href. Defense-in-depth: source
    URLs are assembled from web data."""
    if not u:
        return None
    s = str(u).strip()
    low = s.lower()
    if low.startswith("http://") or low.startswith("https://"):
        return s
    # reject any explicit scheme we didn't allow; permit scheme-less relatives
    if ":" in s.split("/")[0]:
        return None
    return s


def dash(v):
    """Display value or an em dash when empty/None."""
    if v is None or v == "" or v == []:
        return "&mdash;"
    return esc(v)


def money(v):
    if v is None or v == "":
        return "&mdash;"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return esc(v)
    if n == 0:
        return "$0"
    return "${:,.0f}".format(n)


def money2(v):
    if v is None or v == "":
        return "&mdash;"
    try:
        return "${:,.2f}".format(float(v))
    except (TypeError, ValueError):
        return esc(v)


def num(v, suffix=""):
    if v is None or v == "":
        return "&mdash;"
    try:
        f = float(v)
        s = "{:,.0f}".format(f) if f == int(f) else "{:,.2f}".format(f)
    except (TypeError, ValueError):
        s = esc(v)
        return s
    return s + suffix


def sf(v):
    if v is None or v == "":
        return "&mdash;"
    try:
        return "{:,.0f} sf".format(float(v))
    except (TypeError, ValueError):
        return esc(v)


def signed(v, suffix=""):
    """Signed number, e.g. comp GLA delta vs subject."""
    if v is None or v == "":
        return "&mdash;"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    s = "{:+,.0f}".format(f) if f == int(f) else "{:+,.2f}".format(f)
    return s + suffix


def baths(ch):
    """'5 / 2' style full/half summary."""
    full = g(ch, "full_baths")
    half = g(ch, "half_baths")
    if full is None and half is None:
        return "&mdash;"
    return "{} full / {} half".format(full if full is not None else "?",
                                       half if half is not None else "?")


def flag_chips(flags, kind="flag"):
    if not flags:
        return ""
    out = []
    for f in flags:
        out.append('<span class="chip chip-{}">{}</span>'.format(kind, esc(f)))
    return '<div class="chips">' + "".join(out) + "</div>"


# ----------------------------------------------------------------------------
# tab builders
# ----------------------------------------------------------------------------
def build_header(rec):
    order = g(rec, "order", default={})
    subj_addr = g(rec, "subject", "address", "full", default="(no subject address)")
    status = g(order, "status", default="")
    form_type = g(order, "form_type", default="")
    badge = '<span class="status status-{}">{}</span>'.format(
        esc(status).replace(" ", "-"), esc(status) or "&mdash;")
    meta_rows = [
        ("Order ID", dash(g(order, "order_id"))),
        ("Form", dash(form_type)),
        ("Client", dash(g(order, "client"))),
        ("Loan #", dash(g(order, "loan_number"))),
        ("Effective date", dash(g(order, "effective_date"))),
        ("Due date", dash(g(order, "due_date"))),
        ("Inspection", dash(g(order, "inspection"))),
        ("Fee", money(g(order, "fee"))),
    ]
    meta_html = "".join(
        '<div class="meta-item"><span class="meta-k">{}</span>'
        '<span class="meta-v">{}</span></div>'.format(k, v)
        for k, v in meta_rows
    )
    flags = g(rec, "subject", "flags", default=[])
    return """
    <header class="sheet-head">
      <div class="head-top">
        <div>
          <div class="eyebrow">VDV Appraisal Worksheet</div>
          <h1>{addr}</h1>
        </div>
        <div class="head-status">{badge}</div>
      </div>
      <div class="meta-grid">{meta}</div>
      {flags}
    </header>
    """.format(addr=esc(subj_addr), badge=badge, meta=meta_html,
               flags=flag_chips(flags, "warn"))


def kv_table(rows):
    """rows: list of (label, value_html)."""
    body = "".join(
        '<tr><th>{}</th><td>{}</td></tr>'.format(esc(k), v) for k, v in rows
    )
    return '<table class="kv">{}</table>'.format(body)


def build_subject_tab(rec):
    subj = g(rec, "subject", default={})
    ch = g(subj, "characteristics", default={})
    ids = g(subj, "identifiers", default={})
    addr = g(subj, "address", default={})
    res = g(subj, "resolution", default={})
    assess = g(subj, "assessment", default={})

    char_rows = [
        ("Property type", dash(g(ch, "property_type"))),
        ("Use code", dash(g(ch, "use_code"))),
        ("Zoning", dash(g(ch, "zoning"))),
        ("GLA (governing)", sf(g(ch, "gla_sf"))),
        ("Above-grade", sf(g(ch, "above_grade_sf"))),
        ("Below-grade finished", sf(g(ch, "below_grade_finished_sf"))),
        ("Basement", dash(g(ch, "basement"))),
        ("Year built", dash(g(ch, "year_built"))),
        ("Stories", dash(g(ch, "stories"))),
        ("Style", dash(g(ch, "style"))),
        ("Grade / condition", dash(g(ch, "grade_or_condition"))),
        ("Bedrooms", dash(g(ch, "bedrooms"))),
        ("Baths", baths(ch)),
        ("Total rooms", dash(g(ch, "total_rooms"))),
        ("Lot size", dash(
            (num(g(ch, "lot_size_sf")) + " sf") if g(ch, "lot_size_sf") else None)
            + ((" (" + num(g(ch, "lot_size_acres")) + " ac)")
               if g(ch, "lot_size_acres") else "")),
        ("Garage", dash(g(ch, "garage"))),
        ("Pool", "Yes" if g(ch, "pool") else ("No" if g(ch, "pool") is False else "&mdash;")),
        ("Fireplaces", dash(g(ch, "fireplaces"))),
        ("Heating / cooling", dash(g(ch, "heating")) + " / " + dash(g(ch, "cooling"))),
        ("Exterior", dash(g(ch, "exterior"))),
    ]

    id_rows = [
        ("GPIN", dash(g(ids, "gpin"))),
        ("PID", dash(g(ids, "pid"))),
        ("APN / Tax ID", dash(g(ids, "apn") or g(ids, "pid") or g(ids, "map_id"))),
        ("Subdivision", dash(g(ids, "subdivision"))),
        ("Section / Block / Lot",
         "{} / {} / {}".format(dash(g(ids, "section")), dash(g(ids, "block")), dash(g(ids, "lot")))),
        ("Magisterial district", dash(g(ids, "magisterial_district"))),
        ("Neighborhood code", dash(g(ids, "neighborhood_code"))),
        ("Legal description", dash(g(ids, "legal_description"))),
        ("County", dash(g(addr, "county"))),
    ]

    assess_rows = [
        ("Tax year", dash(g(assess, "tax_year"))),
        ("Land value", money(g(assess, "land_value"))),
        ("Improvements", money(g(assess, "improvements_value"))),
        ("Total assessed", money(g(assess, "total_value"))),
    ]

    res_rows = [
        ("Address-only input", "Yes" if g(res, "input_was_address_only") else "No"),
        ("Method", dash(g(res, "method"))),
        ("No tax ID (new construction)",
         '<span class="chip chip-warn">YES — enter subject MANUALLY in DataMaster</span>'
         if g(res, "no_tax_id") else "No"),
        ("Neighbor proxy", dash(g(res, "neighbor_unit_proxy"))),
        ("From cache", "Yes" if g(res, "cached") else "No"),
        ("Resolved on", dash(g(res, "resolved_on"))),
    ]

    # verification (multi-source) table
    ver = g(subj, "verification", default=[])
    if ver:
        cols = ["attribute", "county", "zillow", "realtor", "redfin", "homes", "mls"]
        present = [c for c in cols if any(g(v, c) is not None for v in ver)]
        if "attribute" not in present:
            present = ["attribute"] + present
        head = "".join("<th>{}</th>".format(esc(c.title())) for c in present) \
            + "<th>Governing</th><th>Flag</th>"
        body = ""
        for v in ver:
            flag = g(v, "flag")
            cls = ' class="row-flagged"' if flag else ""
            cells = "".join("<td>{}</td>".format(dash(g(v, c))) for c in present)
            body += "<tr{}>{}<td><b>{}</b></td><td>{}</td></tr>".format(
                cls, cells, dash(g(v, "governing_source")),
                ('<span class="chip chip-warn">{}</span>'.format(esc(flag)) if flag else "&mdash;"))
        verification = (
            '<h3>Cross-source verification</h3>'
            '<table class="grid"><thead><tr>{}</tr></thead><tbody>{}</tbody></table>'
            .format(head, body))
    else:
        verification = ""

    return """
    <section class="tab-pane" id="tab-subject">
      <div class="two-col">
        <div><h3>Characteristics (governing)</h3>{char}</div>
        <div>
          <h3>Identifiers</h3>{ids}
          <h3>Assessment</h3>{assess}
          <h3>Subject resolution</h3>{res}
        </div>
      </div>
      {verification}
    </section>
    """.format(char=kv_table(char_rows), ids=kv_table(id_rows),
               assess=kv_table(assess_rows), res=kv_table(res_rows),
               verification=verification)


# Comp grid — URAR-style: features as rows, subject + comps as columns.
# Each row binds its SUBJECT accessor and its COMP accessor together, so the two
# columns can never silently desync when a row is renamed/reordered.
DASH = "&mdash;"
COMP_TAX_ID_LABEL = "Tax ID (PID/APN)"


def _comp_tax_id(obj):
    """First non-empty parcel identifier on a comp or the subject, in the comp
    grid's precedence: pid -> apn -> map_id. Single source of truth shared by the
    COMP_ROWS Tax ID row and audit_comp_tax_ids() so render and gate can't drift."""
    return (g(obj, "identifiers", "pid")
            or g(obj, "identifiers", "apn")
            or g(obj, "identifiers", "map_id"))


COMP_ROWS = [
    # (label, subject_fn(rec), comp_fn(comp))
    ("Address",
     lambda r: dash(g(r, "subject", "address", "full")),
     lambda c: dash(g(c, "address", "full"))),
    ("County",
     lambda r: dash(g(r, "subject", "address", "county")),
     lambda c: dash(g(c, "address", "county"))),
    ("Proximity",
     lambda r: DASH,
     lambda c: (num(g(c, "distance_mi")) + " mi") if g(c, "distance_mi") is not None else DASH),
    ("Sale price",
     lambda r: DASH,
     lambda c: money(g(c, "sale", "sale_price"))),
    ("List price",
     lambda r: money(g(r, "subject", "listing", "list_price")),
     lambda c: money(g(c, "sale", "list_price"))),
    ("$/sf",
     lambda r: DASH,
     lambda c: money2(g(c, "price_per_sf"))),
    ("DOM",
     lambda r: dash(g(r, "subject", "listing", "dom")),
     lambda c: dash(g(c, "sale", "dom"))),
    ("GLA",
     lambda r: sf(g(r, "subject", "characteristics", "gla_sf")),
     lambda c: sf(g(c, "characteristics", "gla_sf"))),
    ("Above-grade",
     lambda r: sf(g(r, "subject", "characteristics", "above_grade_sf")),
     lambda c: sf(g(c, "characteristics", "above_grade_sf"))),
    ("GLA vs subj",
     lambda r: DASH,
     lambda c: signed(g(c, "gla_delta_vs_subject_sf"), " sf")),
    ("Year built",
     lambda r: dash(g(r, "subject", "characteristics", "year_built")),
     lambda c: dash(g(c, "characteristics", "year_built"))),
    ("Beds",
     lambda r: dash(g(r, "subject", "characteristics", "bedrooms")),
     lambda c: dash(g(c, "characteristics", "bedrooms"))),
    ("Baths",
     lambda r: baths(g(r, "subject", "characteristics", default={})),
     lambda c: baths(g(c, "characteristics", default={}))),
    (COMP_TAX_ID_LABEL,
     lambda r: dash(_comp_tax_id(g(r, "subject", default={}))),
     lambda c: dash(_comp_tax_id(c))),
    ("MLS #",
     lambda r: DASH,
     lambda c: dash(g(c, "identifiers", "mls_number"))),
    ("MLS system",
     lambda r: DASH,
     lambda c: dash(g(c, "identifiers", "mls_system"))),
]


def audit_comp_tax_ids(rec, html_doc):
    """Completeness gate (interlane 2026-06-26 [ACTION] #1 / vault andon #1).

    The comp grid once rendered MLS# but had no Tax ID row, so every comp's
    APN/PID sat in the record JSON yet was invisible in the worksheet HTML.
    This audit fails when a comp HAS a Tax ID (pid || apn || map_id) but that
    value does not actually appear in the rendered HTML. Returns a list of
    human-readable problem strings; an empty list means the gate passed."""
    problems = []
    comps = g(rec, "comps", default=[]) or []
    if not comps:
        return problems
    if COMP_TAX_ID_LABEL not in html_doc:
        problems.append('comp grid is missing the "{}" row entirely'
                        .format(COMP_TAX_ID_LABEL))
    for c in comps:
        tax_id = _comp_tax_id(c)
        if not tax_id:
            continue  # no identifier in the record -> a blank cell is correct
        if esc(str(tax_id)) not in html_doc:
            problems.append(
                "comp #{} ({}) has Tax ID {!r} in the record but it is not in "
                "the rendered HTML".format(g(c, "position", default="?"),
                                           g(c, "address", "full", default="?"),
                                           tax_id))
    return problems


def _comp_grid(rec, comps, title, note=""):
    if not comps:
        return ""
    # header: feature col + Subject + each comp
    head = "<th class='rowlabel'>Feature</th><th class='subjcol'>SUBJECT</th>"
    for c in comps:
        head += "<th>#{} <span class='st st-{}'>{}</span></th>".format(
            esc(g(c, "position", default="?")), esc(g(c, "status", default="")),
            esc(g(c, "status", default="")).upper())
    body = ""
    for label, subj_fn, comp_fn in COMP_ROWS:
        cells = "<td class='subjcol'>{}</td>".format(subj_fn(rec))
        for c in comps:
            cells += "<td>{}</td>".format(comp_fn(c))
        body += "<tr><th class='rowlabel'>{}</th>{}</tr>".format(esc(label), cells)
    # flags row
    flagcells = "<td class='subjcol'>&mdash;</td>"
    for c in comps:
        flagcells += "<td>{}</td>".format(flag_chips(g(c, "flags", default=[]), "warn") or "&mdash;")
    body += "<tr><th class='rowlabel'>Flags</th>{}</tr>".format(flagcells)
    note_html = '<p class="note">{}</p>'.format(esc(note)) if note else ""
    return """
      <h3>{title} <span class="count">({n})</span></h3>
      {note}
      <div class="grid-scroll">
        <table class="grid compgrid"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
      </div>
    """.format(title=esc(title), n=len(comps), note=note_html, head=head, body=body)


def build_comps_tab(rec):
    comps = g(rec, "comps", default=[]) or []
    closed = [c for c in comps if g(c, "status") == "closed"]
    active = [c for c in comps if g(c, "status") in ("active", "pending")]

    # market search summary
    s = g(rec, "market", "search", default={})
    band = g(s, "gla_band", default={})
    search_rows = [
        ("Radius", (num(g(s, "radius_mi")) + " mi") if g(s, "radius_mi") is not None else "&mdash;"),
        ("Sale window", (num(g(s, "sale_window_months")) + " mo") if g(s, "sale_window_months") is not None else "&mdash;"),
        ("GLA band", "{} – {}{}".format(
            sf(g(band, "low_sf")), sf(g(band, "high_sf")),
            " (luxury-widened)" if g(band, "luxury_widened") else "")),
        ("MLS systems", dash(", ".join(g(s, "mls_systems", default=[])) or None)),
    ]
    nbhd = g(rec, "market", "neighborhood_notes")
    nbhd_html = '<div class="callout"><b>Neighborhood:</b> {}</div>'.format(esc(nbhd)) if nbhd else ""

    closed_grid = _comp_grid(
        rec, closed, "Closed sales — the comps",
        "Minimum 3 closed required; target 3–5. These drive the opinion of value.")
    active_grid = _comp_grid(
        rec, active, "Active / Pending — supporting listing analysis only",
        "Listings support the market trend; they are NOT the comparable sales.")

    if not closed and not active:
        grids = '<p class="empty">No comps in this record yet.</p>'
    else:
        grids = closed_grid + active_grid

    return """
    <section class="tab-pane" id="tab-comps">
      <div class="two-col">
        <div><h3>Search parameters</h3>{search}</div>
        <div>{nbhd}</div>
      </div>
      {grids}
    </section>
    """.format(search=kv_table(search_rows), nbhd=nbhd_html, grids=grids)


def build_history_tab(rec):
    # subject sales history
    sh = g(rec, "subject", "sales_history", default=[]) or []
    if sh:
        rows = ""
        for e in sh:
            rows += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                dash(g(e, "date")), money(g(e, "price")), dash(g(e, "deed_book_page")),
                dash(g(e, "qualification")), dash(g(e, "source")))
        subj_hist = (
            '<h3>Subject — sales history</h3>'
            '<table class="grid"><thead><tr><th>Date</th><th>Price</th>'
            '<th>Deed bk/pg</th><th>Qualification</th><th>Source</th></tr></thead>'
            '<tbody>{}</tbody></table>'.format(rows))
    else:
        subj_hist = '<h3>Subject — sales history</h3><p class="empty">None recorded.</p>'

    # subject current listing
    lst = g(rec, "subject", "listing", default={}) or {}
    if lst:
        listing_rows = [
            ("Status", dash(g(lst, "status"))),
            ("List price", money(g(lst, "list_price"))),
            ("Original list", money(g(lst, "original_list_price"))),
            ("DOM", dash(g(lst, "dom"))),
            ("Contract date", dash(g(lst, "contract_date"))),
            ("MLS #", dash(g(lst, "mls_number"))),
            ("MLS system", dash(g(lst, "mls_system"))),
        ]
        subj_listing = "<h3>Subject — current listing</h3>" + kv_table(listing_rows)
    else:
        subj_listing = ""

    # comp prior sales
    comps = g(rec, "comps", default=[]) or []
    prior_rows = ""
    for c in comps:
        ps = g(c, "prior_sale", default={}) or {}
        if g(ps, "date") or g(ps, "price"):
            prior_rows += "<tr><td>#{} {}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                esc(g(c, "position", default="?")), dash(g(c, "address", "full")),
                dash(g(ps, "date")), money(g(ps, "price")), dash(g(ps, "source")))
    if prior_rows:
        comp_prior = (
            '<h3>Comps — prior sales</h3>'
            '<table class="grid"><thead><tr><th>Comp</th><th>Date</th>'
            '<th>Price</th><th>Source</th></tr></thead><tbody>{}</tbody></table>'.format(prior_rows))
    else:
        comp_prior = '<h3>Comps — prior sales</h3><p class="empty">No prior-sale data captured yet.</p>'

    return """
    <section class="tab-pane" id="tab-history">
      {subj_hist}
      {subj_listing}
      {comp_prior}
    </section>
    """.format(subj_hist=subj_hist, subj_listing=subj_listing, comp_prior=comp_prior)


def build_photos_tab(rec):
    photos = g(rec, "photos", default=[]) or []
    if not photos:
        return ('<section class="tab-pane" id="tab-photos">'
                '<p class="empty">No photos attached. (Photos tab populates after the '
                'photo-organizer build — see handoff §5.)</p></section>')
    cards = ""
    for p in photos:
        cards += """
        <figure class="photo-card">
          <div class="photo-thumb">{cat}</div>
          <figcaption>
            <b>{label}</b><br>
            <span class="muted">{cat} · {rel} · {status}</span>
          </figcaption>
        </figure>""".format(
            cat=esc(g(p, "category", default="")),
            label=dash(g(p, "label")),
            rel=esc(g(p, "related_to", default="")),
            status=esc(g(p, "status", default="")))
    return ('<section class="tab-pane" id="tab-photos">'
            '<div class="photo-grid">{}</div></section>'.format(cards))


def build_map_tab(rec):
    """No external map calls (deterministic). Render an inline SVG scatter when
    coordinates exist, plus a coordinate/distance table."""
    subj_geo = g(rec, "subject", "geo", default={})
    pts = []
    slat, slon = g(subj_geo, "lat"), g(subj_geo, "lon")
    if slat is not None and slon is not None:
        pts.append(("SUBJECT", slat, slon, True))
    comps = g(rec, "comps", default=[]) or []
    for c in comps:
        cg = g(c, "geo", default={})
        if g(cg, "lat") is not None and g(cg, "lon") is not None:
            pts.append(("#" + str(g(c, "position", default="?")), g(cg, "lat"), g(cg, "lon"), False))

    # coordinate/distance table (always render)
    rows = ""
    rows += "<tr><td><b>SUBJECT</b></td><td>{}</td><td>{}</td><td>&mdash;</td></tr>".format(
        dash(slat), dash(slon))
    for c in comps:
        cg = g(c, "geo", default={})
        rows += "<tr><td>#{} {}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(g(c, "position", default="?")), dash(g(c, "address", "full")),
            dash(g(cg, "lat")), dash(g(cg, "lon")),
            (num(g(c, "distance_mi")) + " mi") if g(c, "distance_mi") is not None else "&mdash;")
    coord_table = (
        '<table class="grid"><thead><tr><th>Point</th><th>Lat</th><th>Lon</th>'
        '<th>Proximity</th></tr></thead><tbody>{}</tbody></table>'.format(rows))

    # SVG scatter if 2+ points have coords
    svg = ""
    if len(pts) >= 2:
        lats = [p[1] for p in pts]
        lons = [p[2] for p in pts]
        minlat, maxlat = min(lats), max(lats)
        minlon, maxlon = min(lons), max(lons)
        W, H, pad = 560, 380, 40
        dlat = (maxlat - minlat) or 1e-6
        dlon = (maxlon - minlon) or 1e-6

        def x(lon):
            return pad + (lon - minlon) / dlon * (W - 2 * pad)

        def y(lat):
            # invert: north (max lat) at top
            return pad + (maxlat - lat) / dlat * (H - 2 * pad)

        dots = ""
        for label, lat, lon, is_subj in pts:
            cx, cy = x(lon), y(lat)
            cls = "subj" if is_subj else "comp"
            r = 9 if is_subj else 6
            dots += ('<circle cx="{:.1f}" cy="{:.1f}" r="{}" class="dot-{}"/>'
                     '<text x="{:.1f}" y="{:.1f}" class="dotlabel">{}</text>').format(
                cx, cy, r, cls, cx + 11, cy + 4, esc(label))
        svg = (
            '<div class="mapwrap"><svg viewBox="0 0 {w} {h}" class="mapsvg" '
            'preserveAspectRatio="xMidYMid meet">'
            '<rect x="0" y="0" width="{w}" height="{h}" class="mapbg"/>{dots}</svg>'
            '<p class="note">Relative positions from lat/lon (not to scale; no map tiles — '
            'deterministic render).</p></div>'.format(w=W, h=H, dots=dots))
    else:
        svg = ('<p class="empty">Not enough geocoded points to plot. '
               '(Comps in the example carry distance but not lat/lon.)</p>')

    return ('<section class="tab-pane" id="tab-map">{svg}<h3>Coordinates &amp; proximity</h3>'
            '{table}</section>'.format(svg=svg, table=coord_table))


def build_sources_footer(rec):
    srcs = g(rec, "sources", default=[]) or []
    review = g(rec, "review", default={})
    items = ""
    for s in srcs:
        name = esc(g(s, "name", default=""))
        url = g(s, "url")
        at = g(s, "retrieved_at")
        ok = safe_url(url)
        link = ('<a href="{u}" target="_blank" rel="noopener">{n}</a>'.format(u=esc(ok), n=name)
                if ok else (name + (' <span class="muted">[{}]</span>'.format(esc(url)) if url else "")))
        items += "<li>{} <span class='muted'>{}</span></li>".format(
            link, ("· " + esc(at)) if at else "")
    reviewed = g(review, "human_reviewed")
    rbadge = ('<span class="chip chip-ok">REVIEWED</span>' if reviewed
              else '<span class="chip chip-warn">NOT YET REVIEWED — appraiser must certify</span>')
    rnotes = g(review, "notes")
    return """
    <footer class="sheet-foot">
      <div class="foot-review">{rbadge}{notes}</div>
      <details><summary>Sources ({n})</summary><ul class="sources">{items}</ul></details>
      <p class="muted">Generated {gen} by {by} · schema {ver} · This worksheet ASSEMBLES data;
      the licensed appraiser judges adjustments and certifies. Nothing is filed automatically.</p>
    </footer>
    """.format(rbadge=rbadge,
               notes=(' <span class="muted">' + esc(rnotes) + '</span>') if rnotes else "",
               n=len(srcs), items=items,
               gen=esc(g(rec, "generated_at", default="")),
               by=esc(g(rec, "generated_by", default="")),
               ver=esc(g(rec, "schema_version", default="")))


# ----------------------------------------------------------------------------
# page assembly
# ----------------------------------------------------------------------------
CSS = """
:root{
  --ink:#1d2733; --muted:#6b7785; --line:#dce3ea; --bg:#f4f6f8; --card:#fff;
  --accent:#1f5fa8; --accent-2:#0d3b66; --warn-bg:#fff4e0; --warn-ink:#8a5a00;
  --ok-bg:#e3f6e9; --ok-ink:#1d6b3a; --subj:#eef4fb;
}
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink);background:var(--bg);}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 60px}
.sheet-head{background:linear-gradient(135deg,var(--accent-2),var(--accent));color:#fff;
  padding:22px 26px;border-radius:0 0 12px 12px;}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;opacity:.8}
.sheet-head h1{margin:2px 0 0;font-size:24px;font-weight:650}
.head-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.status{display:inline-block;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;
  letter-spacing:.04em;text-transform:uppercase;background:rgba(255,255,255,.18)}
.status-delivered{background:var(--ok-bg);color:var(--ok-ink)}
.status-in-progress{background:#ffe9b8;color:#7a5200}
.meta-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px 18px;margin-top:16px}
.meta-item{display:flex;flex-direction:column}
.meta-k{font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.75}
.meta-v{font-size:14px;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.chip{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11.5px;font-weight:600}
.chip-warn{background:var(--warn-bg);color:var(--warn-ink)}
.chip-ok{background:var(--ok-bg);color:var(--ok-ink)}
.chip-flag{background:#eef1f4;color:#475260}
nav.tabs{display:flex;gap:4px;margin:18px 0 14px;flex-wrap:wrap}
nav.tabs button{border:1px solid var(--line);background:var(--card);color:var(--muted);
  padding:9px 16px;border-radius:9px;font-size:13.5px;font-weight:600;cursor:pointer}
nav.tabs button.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.tab-pane{display:none;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px}
.tab-pane.active{display:block}
h3{font-size:14px;margin:20px 0 8px;color:var(--accent-2);font-weight:700;
  text-transform:uppercase;letter-spacing:.04em}
h3:first-child{margin-top:0}
.count{color:var(--muted);font-weight:500;text-transform:none}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:26px}
table{border-collapse:collapse;width:100%}
table.kv th{text-align:left;color:var(--muted);font-weight:600;width:46%;
  padding:6px 10px 6px 0;vertical-align:top;border-bottom:1px solid var(--line);font-size:13px}
table.kv td{padding:6px 0;border-bottom:1px solid var(--line);font-weight:600}
table.grid{font-size:13px;margin:6px 0 4px}
table.grid th{background:#f0f4f8;text-align:left;padding:8px 10px;border:1px solid var(--line);
  font-weight:700;font-size:12px}
table.grid td{padding:7px 10px;border:1px solid var(--line);vertical-align:top}
.row-flagged{background:var(--warn-bg)}
.grid-scroll{overflow-x:auto}
.compgrid th.rowlabel,.compgrid td.rowlabel{position:sticky;left:0;background:#f0f4f8;
  font-weight:700;font-size:12px;white-space:nowrap}
.compgrid .subjcol{background:var(--subj);font-weight:600}
.compgrid thead th{white-space:nowrap}
.st{display:inline-block;font-size:9px;font-weight:800;padding:1px 5px;border-radius:4px;
  vertical-align:middle;margin-left:2px}
.st-closed{background:var(--ok-bg);color:var(--ok-ink)}
.st-active,.st-pending{background:#ffe9b8;color:#7a5200}
.callout{background:var(--subj);border-left:3px solid var(--accent);padding:10px 14px;
  border-radius:0 8px 8px 0;font-size:13px}
.note{color:var(--muted);font-size:12.5px;margin:2px 0 8px}
.empty{color:var(--muted);font-style:italic;padding:8px 0}
.photo-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}
.photo-card{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.photo-thumb{height:110px;background:#eef1f4;display:flex;align-items:center;justify-content:center;
  color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}
.photo-card figcaption{padding:8px 10px;font-size:12px}
.mapwrap{margin-bottom:14px}
.mapsvg{width:100%;height:auto;border:1px solid var(--line);border-radius:10px}
.mapbg{fill:#eef4fb}
.dot-subj{fill:var(--accent-2);stroke:#fff;stroke-width:2}
.dot-comp{fill:#e07b39;stroke:#fff;stroke-width:1.5}
.dotlabel{font:11px sans-serif;fill:var(--ink);font-weight:600}
.muted{color:var(--muted)}
.sheet-foot{margin-top:18px;padding:16px 22px;background:var(--card);border:1px solid var(--line);
  border-radius:12px;font-size:13px}
.foot-review{margin-bottom:10px}
.sources{margin:6px 0 0;padding-left:18px}
details summary{cursor:pointer;font-weight:600;color:var(--accent-2)}
a{color:var(--accent)}
@media(max-width:760px){.two-col{grid-template-columns:1fr}.meta-grid{grid-template-columns:repeat(2,1fr)}}
@media print{nav.tabs{display:none}.tab-pane{display:block!important;page-break-inside:avoid;margin-bottom:14px}
  body{background:#fff}}
"""

JS = """
(function(){
  var btns=document.querySelectorAll('nav.tabs button');
  var panes=document.querySelectorAll('.tab-pane');
  function show(id){
    panes.forEach(function(p){p.classList.toggle('active',p.id===id);});
    btns.forEach(function(b){b.classList.toggle('active',b.dataset.tab===id);});
  }
  btns.forEach(function(b){b.addEventListener('click',function(){show(b.dataset.tab);});});
  if(btns.length)show(btns[0].dataset.tab);
})();
"""


def render(rec, with_photos=False, with_map=False):
    # Default tabs. Photos and Map are OPTIONAL — included only on Yuriy's approval
    # (via --with-photos / --with-map). Off by default.
    tabs = [
        ("tab-subject", "Subject"),
        ("tab-comps", "Comp grid"),
        ("tab-history", "Sale / Listing history"),
    ]
    panes = build_subject_tab(rec) + build_comps_tab(rec) + build_history_tab(rec)
    if with_photos:
        tabs.append(("tab-photos", "Photos"))
        panes += build_photos_tab(rec)
    if with_map:
        tabs.append(("tab-map", "Map"))
        panes += build_map_tab(rec)
    nav = "".join(
        '<button data-tab="{}">{}</button>'.format(tid, esc(label)) for tid, label in tabs
    )
    title = esc(g(rec, "subject", "address", "full", default="Appraisal worksheet"))
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Worksheet — {title}</title>
<style>{css}</style></head>
<body><div class="wrap">
{header}
<nav class="tabs">{nav}</nav>
{panes}
{footer}
</div><script>{js}</script></body></html>""".format(
        title=title, css=CSS, header=build_header(rec), nav=nav,
        panes=panes, footer=build_sources_footer(rec), js=JS)


# ----------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Render appraisal-record.json -> worksheet.html")
    ap.add_argument("record", help="Path to appraisal-record.json")
    ap.add_argument("-o", "--output", help="Output HTML path (default: <record_dir>/worksheet.html)")
    ap.add_argument("--with-photos", action="store_true",
                    help="Include the Photos tab (optional; requires Yuriy's approval)")
    ap.add_argument("--with-map", action="store_true",
                    help="Include the Map tab (optional; requires Yuriy's approval)")
    args = ap.parse_args(argv)

    with open(args.record, "r", encoding="utf-8") as f:
        rec = json.load(f)

    ver = rec.get("schema_version")
    if ver != SCHEMA_VERSION_SUPPORTED:
        sys.stderr.write(
            "WARNING: record schema_version={!r}, renderer built for {!r}. "
            "Rendering anyway.\n".format(ver, SCHEMA_VERSION_SUPPORTED))

    out = args.output or os.path.join(os.path.dirname(os.path.abspath(args.record)), "worksheet.html")
    html_doc = render(rec, with_photos=args.with_photos, with_map=args.with_map)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print("Wrote {} ({:,} bytes)".format(out, len(html_doc)))

    # Completeness gate: every comp Tax ID present in the record must render in
    # the HTML (interlane 2026-06-26 [ACTION] #1). The worksheet is still written
    # so it can be inspected, but a violation exits non-zero to stop the pipeline.
    problems = audit_comp_tax_ids(rec, html_doc)
    if problems:
        sys.stderr.write("QA GATE FAILED - comp Tax ID completeness:\n")
        for p in problems:
            sys.stderr.write("  - {}\n".format(p))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# end of render_worksheet.py
