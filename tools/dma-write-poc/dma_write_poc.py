#!/usr/bin/env python3
"""
DataMaster .dma WRITE proof-of-concept (SANDBOX ONLY).

Goal of the experiment (see Code handoff 2026-06-18): learn whether a hand-edited .dma
copy round-trips through DataMaster. We do the LOWEST-RISK edit possible first:

  * roundtrip : rewrite the zip with the Appraisal blob byte-IDENTICAL (tests only whether
                DM accepts a Python-rewritten zip container).
  * patch     : replace a free-text value with a SAME-LENGTH string (no protobuf length-prefix
                surgery — zero structural change to the message).
  * inspect   : list the zip entries + count occurrences of a search string.

HARD RULES
  - NEVER write the live OneDrive file. --out must be a copy under VDV Appraisals (client zone).
  - Same-length only for `patch` (asserts len(old)==len(new)); refuses otherwise.
  - Preserves entry names, order, and per-entry compression so the container matches DM's.
  - Verifies after writing (re-reads the output zip, confirms the blob change + decodes).

Usage:
  python dma_write_poc.py inspect   --src "<copy.dma>" [--find "Sterlingwwod"]
  python dma_write_poc.py roundtrip --src "<copy.dma>" --out "<copy.rt.dma>"
  python dma_write_poc.py patch     --src "<copy.dma>" --out "<copy.patched.dma>" \
                                    --old "Sterlingwwod" --new "Sterlingwood"
"""
import argparse
import os
import sys
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "dma-decoder"))
import dma_decode as dd  # noqa: E402

_APPRAISAL = "Appraisal"
_ONEDRIVE = "onedrive"


def _guard_out(path):
    p = path.replace("/", "\\").lower()
    if _ONEDRIVE in p:
        sys.exit("REFUSED: --out points into OneDrive. Write copies under VDV Appraisals only.")
    if "vdv appraisals" not in p:
        sys.exit("REFUSED: --out must be under 'VDV Appraisals\\' (client zone), not the repo.")


def _entries(src):
    """Return ordered list of (ZipInfo, bytes) for every entry."""
    out = []
    with zipfile.ZipFile(src, "r") as zf:
        for zi in zf.infolist():
            out.append((zi, zf.read(zi.filename)))
    return out


def _appraisal_name(entries):
    for zi, _ in entries:
        if zi.filename.lower().endswith("appraisal") or zi.filename.lower() == "appraisal":
            return zi.filename
    # fallback: largest entry
    return max(entries, key=lambda e: len(e[1]))[0].filename


def _write_zip(out_path, entries, new_blob_for):
    """Rewrite the zip preserving names/order/compression; swap one entry's bytes."""
    with zipfile.ZipFile(out_path, "w") as zf:
        for zi, data in entries:
            payload = new_blob_for.get(zi.filename, data)
            # preserve the original compression type + name + timestamp
            ni = zipfile.ZipInfo(zi.filename, date_time=zi.date_time)
            ni.compress_type = zi.compress_type
            ni.external_attr = zi.external_attr
            ni.internal_attr = zi.internal_attr
            ni.create_system = zi.create_system
            zf.writestr(ni, payload)


def cmd_inspect(args):
    entries = _entries(args.src)
    print(f"zip: {args.src}")
    for zi, data in entries:
        ct = {0: "STORED", 8: "DEFLATE"}.get(zi.compress_type, zi.compress_type)
        print(f"  entry {zi.filename!r:14} {len(data):>8} bytes  compress={ct}")
    name = _appraisal_name(entries)
    blob = dict((zi.filename, d) for zi, d in entries)[name]
    print(f"  -> Appraisal entry: {name!r} ({len(blob)} bytes)")
    if args.find:
        needle = args.find.encode()
        print(f"  occurrences of {args.find!r} in Appraisal blob: {blob.count(needle)}")
    leaves = dd.decode_message(blob)
    print(f"  decodes to {len(leaves)} leaves")


def cmd_roundtrip(args):
    _guard_out(args.out)
    entries = _entries(args.src)
    name = _appraisal_name(entries)
    src_blob = dict((zi.filename, d) for zi, d in entries)[name]
    _write_zip(args.out, entries, {})  # no change
    # verify byte-identity of the Appraisal blob after rewrite
    out_blob = dict((zi.filename, d) for zi, d in _entries(args.out))[name]
    ok = out_blob == src_blob
    print(f"roundtrip -> {args.out}")
    print(f"  Appraisal blob byte-identical after rezip: {ok} ({len(out_blob)} bytes)")
    if not ok:
        sys.exit("FAIL: rezip changed the Appraisal bytes")


def cmd_patch(args):
    _guard_out(args.out)
    old, new = args.old.encode(), args.new.encode()
    if len(old) != len(new):
        sys.exit(f"REFUSED: same-length only. old={len(old)}B new={len(new)}B")
    entries = _entries(args.src)
    name = _appraisal_name(entries)
    blob = dict((zi.filename, d) for zi, d in entries)[name]
    count = blob.count(old)
    if count == 0:
        sys.exit(f"REFUSED: {args.old!r} not found in Appraisal blob")
    patched = blob.replace(old, new)
    assert len(patched) == len(blob), "length drift — aborting"
    _write_zip(args.out, entries, {name: patched})
    # verify
    out_blob = dict((zi.filename, d) for zi, d in _entries(args.out))[name]
    leaves_before = len(dd.decode_message(blob))
    leaves_after = len(dd.decode_message(out_blob))
    print(f"patch -> {args.out}")
    print(f"  replaced {count}x {args.old!r} -> {args.new!r} (same length, {len(old)}B)")
    print(f"  blob size unchanged: {len(out_blob) == len(blob)} ({len(out_blob)}B)")
    print(f"  decode leaves before/after: {leaves_before} / {leaves_after} "
          f"({'stable' if leaves_before == leaves_after else 'CHANGED — investigate'})")
    print(f"  new value present in output: {new in out_blob}; old gone: {old not in out_blob}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="DataMaster .dma write POC (sandbox only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("inspect"); pi.add_argument("--src", required=True); pi.add_argument("--find")
    pr = sub.add_parser("roundtrip"); pr.add_argument("--src", required=True); pr.add_argument("--out", required=True)
    pp = sub.add_parser("patch")
    pp.add_argument("--src", required=True); pp.add_argument("--out", required=True)
    pp.add_argument("--old", required=True); pp.add_argument("--new", required=True)
    args = ap.parse_args(argv)
    {"inspect": cmd_inspect, "roundtrip": cmd_roundtrip, "patch": cmd_patch}[args.cmd](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
