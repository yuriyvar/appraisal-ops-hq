#!/usr/bin/env python3
"""
Pick a condition tier -> pre-fill the Subject worksheet.

Reads a condition profile
(`skills/worksheet-builder/references/condition-profiles/condition-profiles.<form>.yaml`)
for a tier (new | average | fair), maps its default Improvements + Quality/Condition
values onto the blank DM-complete worksheet, and writes a pre-filled
`<address>_worksheet.html` for the order folder.

Defaults are visually marked (amber, dashed underline) as "verify"; fair-tier and all
1073 values are flagged EXTRAPOLATED in the banner. The appraiser edits to the real
property and certifies — these are starting points, not findings.

Stdlib only. Includes a tiny YAML-subset reader for the constrained profile format
(no PyYAML dependency — the YAML stays the single human-editable source of truth).

Usage:
    python prefill_worksheet.py --form 1004 --tier average \\
        --out "C:\\Users\\yuriy\\VDV Appraisals\\<order>\\<addr>_worksheet.html"
    # custom profiles dir / blank already generated:
    python prefill_worksheet.py --form 2055 --tier fair --out OUT.html \\
        --profiles-dir "...\\condition-profiles"
"""

import argparse
import html
import os
import sys

import build_collection_sheet as bcs   # same folder; provides build_html()

# Default location of the profiles relative to this tool (repo layout).
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_PROFILES = os.path.abspath(os.path.join(
    _HERE, "..", "..", "skills", "worksheet-builder",
    "references", "condition-profiles"))


# ---------------------------------------------------------------------------
# tiny YAML-subset reader (only what the condition-profiles format uses:
# 2-space nesting, `key: "scalar"`, bools, nested maps, and `>` folded blocks;
# `#` comments stripped outside quotes). NOT a general YAML parser.
# ---------------------------------------------------------------------------
def _scalar(raw):
    s = raw.strip()
    if not s:
        return ""
    if s[0] in ('"', "'"):
        q = s[0]
        end = s.find(q, 1)
        return s[1:end] if end != -1 else s[1:]
    # unquoted -> strip inline comment
    if "#" in s:
        s = s.split("#", 1)[0].strip()
    if s in ("true", "false"):
        return s == "true"
    return s


def _strip_comment(val):
    """Remove an inline `# ...` comment, respecting a leading quoted scalar.
    Used to decide a line's branch (nested-map vs scalar vs folded block) so that
    `key:   # comment` is correctly seen as opening a nested map."""
    v = val.strip()
    if not v:
        return v
    if v[0] in ('"', "'"):
        q = v[0]
        end = v.find(q, 1)
        return v[:end + 1] if end != -1 else v
    if "#" in v:
        return v.split("#", 1)[0].strip()
    return v


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def parse_profile_yaml(path):
    """Parse the constrained condition-profiles YAML into nested dicts."""
    with open(path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    # strip full-line comments / blanks but keep line indices for folded blocks
    lines = []
    for ln in raw_lines:
        stripped = ln.rstrip("\n")
        if not stripped.strip() or stripped.lstrip().startswith("#"):
            continue
        lines.append(stripped)

    root = {}
    # stack of (indent, container)
    stack = [(-1, root)]
    i = 0
    while i < len(lines):
        line = lines[i]
        ind = _indent(line)
        body = line.strip()

        # pop to parent at this indent
        while stack and ind <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if ":" not in body:
            i += 1
            continue
        key, _, val = body.partition(":")
        key = key.strip()
        val = _strip_comment(val)

        if val in (">", "|", ">-", "|-", ">+", "|+"):
            # folded/literal block: gather deeper-indented lines
            block = []
            j = i + 1
            while j < len(lines) and (_indent(lines[j]) > ind or not lines[j].strip()):
                block.append(lines[j].strip())
                j += 1
            sep = " " if val.startswith(">") else "\n"
            parent[key] = sep.join(b for b in block if b).strip()
            i = j
            continue

        if val == "":
            # nested mapping follows
            d = {}
            parent[key] = d
            stack.append((ind, d))
            i += 1
            continue

        parent[key] = _scalar(val)
        i += 1

    return root


# ---------------------------------------------------------------------------
# profile -> worksheet token values  (per-form structure handled here)
# ---------------------------------------------------------------------------
def _join(*parts):
    vals = [str(p).strip() for p in parts if p and str(p).strip()]
    return " · ".join(vals)


def profile_to_tokens(profile, form):
    """Flatten one tier's profile dict into {WORKSHEET_TOKEN: value}."""
    p = profile
    ext = p.get("exterior", {}) or {}
    # interior lives under different keys per form
    interior = (p.get("interior") or p.get("interior_estimated")
                or p.get("unit_interior") or {})
    t = {}

    def put(tok, val):
        if val:
            t[tok] = val

    put("QUALITY", p.get("quality"))
    put("CONDITION", p.get("condition"))
    put("EFF_AGE", p.get("effective_age_hint"))

    # exterior (none for 1073)
    put("EXT_WALLS", ext.get("walls"))
    put("ROOF", ext.get("roof"))
    put("WINDOWS", ext.get("windows"))
    put("GUTTERS", ext.get("gutters"))
    put("FOUNDATION", ext.get("foundation"))

    # interior
    put("FLOORS", interior.get("floors"))
    put("WALLS_BATH", _join(interior.get("walls"), interior.get("trim_finish")))
    put("BATH_FIN", _join(interior.get("bath_floors"), interior.get("bath_wainscot"),
                          interior.get("baths")))
    put("KITCHEN", p.get("kitchen") or interior.get("kitchen"))
    return t


# ---------------------------------------------------------------------------
# fill the blank template
# ---------------------------------------------------------------------------
_DFLT_CSS = (".dflt{background:#fff5e6;border-bottom:1px dashed #b9770e;"
             "padding:0 3px;border-radius:2px}"
             ".prefill-bar{background:#fff5e6;border:1px solid #b9770e;color:#7a4e06;"
             "border-radius:6px;padding:8px 12px;margin:10px 0;font-size:12.5px}")


def build_prefilled(form, tier, profiles_dir):
    path = os.path.join(profiles_dir, "condition-profiles.{}.yaml".format(form))
    if not os.path.isfile(path):
        raise SystemExit("No profile for form {!r}: {}".format(form, path))
    data = parse_profile_yaml(path)
    profiles = data.get("profiles", {})
    if tier not in profiles:
        raise SystemExit("Tier {!r} not in {} (have: {})".format(
            tier, os.path.basename(path), ", ".join(profiles)))
    prof = profiles[tier]
    tokens = profile_to_tokens(prof, form)

    extrapolated = (str(data.get("extrapolated")).lower() == "true"
                    or str(prof.get("observed_in_corpus")).lower() == "false")
    rating = data.get("rating_system", "")

    html_doc = bcs.build_html()

    # inject CSS
    html_doc = html_doc.replace("</style>", _DFLT_CSS + "\n</style>", 1)

    # banner under the H1
    prov = ("EXTRAPOLATED (not from observed VDV reports) — treat as a scaffold"
            if extrapolated else "grounded in past VDV reports")
    banner = (
        '<div class="prefill-bar"><b>Pre-filled: {form} &middot; {tier} tier</b> '
        '({rating}). Amber = tier default &mdash; <b>verify &amp; edit to the real '
        'property</b>. These defaults are {prov}. '
        '{cmt}</div>').format(
            form=html.escape(form), tier=html.escape(tier.upper()),
            rating=html.escape(rating), prov=prov,
            cmt=("<br>Condition comment seed: <i>{}</i>".format(
                html.escape(prof.get("condition_comment", "")))
                if prof.get("condition_comment") else ""))
    html_doc = html_doc.replace('<div class="flagbox">',
                                banner + '\n  <div class="flagbox">', 1)

    # substitute tokens
    filled = []
    for tok, val in tokens.items():
        needle = "{{" + tok + "}}"
        if needle in html_doc:
            html_doc = html_doc.replace(
                needle, '<span class="dflt" title="{} default — verify">{}</span>'.format(
                    html.escape(tier), html.escape(str(val))))
            filled.append(tok)

    return html_doc, filled, extrapolated


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pre-fill the subject worksheet from a condition tier")
    ap.add_argument("--form", required=True, choices=["1004", "2055", "gpar", "1073"])
    ap.add_argument("--tier", required=True, choices=["new", "average", "fair"])
    ap.add_argument("--out", required=True, help="Output worksheet HTML path")
    ap.add_argument("--profiles-dir", default=_DEFAULT_PROFILES,
                    help="condition-profiles dir (default: repo skill references)")
    args = ap.parse_args(argv)

    html_doc, filled, extrap = build_prefilled(args.form, args.tier, args.profiles_dir)
    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print("Wrote {} | {} {} tier | {} fields pre-filled{}".format(
        args.out, args.form, args.tier, len(filled),
        " | EXTRAPOLATED tier (verify all)" if extrap else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
