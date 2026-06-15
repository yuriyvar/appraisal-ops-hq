#!/usr/bin/env python3
"""
DataMaster .dma decoder (stdlib-only, read-only).

A .dma file is a ZIP containing two entries:
  * FileVersion  — a tiny protobuf stub (version marker)
  * Appraisal    — a protobuf-serialized DataMaster appraisal message (no public schema)

This tool decodes the Appraisal blob WITHOUT a schema by walking the protobuf
wire format generically, producing:
  (a) a structural tree of {field_path: leaf_value}, and
  (b) a brute-force pass of every printable string in the blob (backup, so we
      never miss an address/name even if a nested message mis-splits).

Read-only: NEVER writes .dma files. Only DataMaster creates/edits them.

Protobuf wire format recap:
  tag = (field_number << 3) | wire_type
  wire_type 0 = varint        (int/bool/enum)
  wire_type 1 = 64-bit        (fixed64/double)
  wire_type 2 = length-delim  (string/bytes/embedded message/packed)
  wire_type 5 = 32-bit        (fixed32/float)

Usage:
    python dma_decode.py "path/to/file.dma"            # pretty tree to stdout
    python dma_decode.py "path/to/file.dma" --json OUT # full decode to JSON
    python dma_decode.py "path/to/file.dma" --strings  # just printable strings
"""

import argparse
import io
import json
import struct
import sys
import zipfile


# ---------------------------------------------------------------------------
# low-level varint
# ---------------------------------------------------------------------------
def _read_varint(buf, pos):
    """Return (value, new_pos). Raises ValueError on truncation/overflow."""
    result = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise ValueError("varint truncated")
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


# ---------------------------------------------------------------------------
# printable-string heuristics
# ---------------------------------------------------------------------------
def _printable_ratio(bs):
    if not bs:
        return 0.0
    ok = sum(1 for c in bs if 0x20 <= c <= 0x7E or c in (0x09, 0x0A, 0x0D))
    return ok / len(bs)


def _as_text(bs):
    """Return a decoded string if bytes look like clean text, else None."""
    try:
        s = bs.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if _printable_ratio(bs) >= 0.90 and len(s.strip()) > 0:
        return s
    return None


# ---------------------------------------------------------------------------
# generic message walker
# ---------------------------------------------------------------------------
def _looks_like_message(buf):
    """Heuristic: can `buf` be fully consumed as a sequence of protobuf fields
    with plausible tags? Used to decide nested-message vs. string."""
    pos = 0
    n = len(buf)
    fields = 0
    if n == 0:
        return False
    try:
        while pos < n:
            tag, pos = _read_varint(buf, pos)
            wt = tag & 0x07
            fn = tag >> 3
            if fn == 0 or wt in (3, 4, 6, 7):
                return False
            if wt == 0:
                _, pos = _read_varint(buf, pos)
            elif wt == 1:
                pos += 8
            elif wt == 5:
                pos += 4
            elif wt == 2:
                ln, pos = _read_varint(buf, pos)
                pos += ln
            if pos > n:
                return False
            fields += 1
            if fields > 5000:
                return False
        return pos == n and fields > 0
    except ValueError:
        return False


def decode_message(buf, path="", out=None, depth=0, max_depth=40):
    """
    Recursively decode a protobuf message buffer into a list of leaf records:
      {"path": "1.3.2", "wire": 2, "type": "str"|"int"|"f64"|"f32"|"bytes"|"msg",
       "value": <python value>}
    Nested messages recurse; their leaves carry the dotted path.
    """
    if out is None:
        out = []
    pos = 0
    n = len(buf)
    # track repeated field index per (path, field) so paths stay unique-ish
    seen = {}
    while pos < n:
        try:
            tag, pos = _read_varint(buf, pos)
        except ValueError:
            break
        wt = tag & 0x07
        fn = tag >> 3
        idx = seen.get(fn, 0)
        seen[fn] = idx + 1
        fld = "{}.{}".format(path, fn) if path else str(fn)
        if idx:
            fld = "{}[{}]".format(fld, idx)

        if wt == 0:  # varint
            try:
                val, pos = _read_varint(buf, pos)
            except ValueError:
                break
            out.append({"path": fld, "wire": 0, "type": "int", "value": val})
        elif wt == 1:  # 64-bit
            if pos + 8 > n:
                break
            raw = buf[pos:pos + 8]
            pos += 8
            dval = struct.unpack("<d", raw)[0]
            out.append({"path": fld, "wire": 1, "type": "f64", "value": dval})
        elif wt == 5:  # 32-bit
            if pos + 4 > n:
                break
            raw = buf[pos:pos + 4]
            pos += 4
            fval = struct.unpack("<f", raw)[0]
            out.append({"path": fld, "wire": 5, "type": "f32", "value": fval})
        elif wt == 2:  # length-delimited
            try:
                ln, pos = _read_varint(buf, pos)
            except ValueError:
                break
            if pos + ln > n:
                break
            sub = buf[pos:pos + ln]
            pos += ln
            text = _as_text(sub)
            is_msg = _looks_like_message(sub) and depth < max_depth
            # Decision: prefer message when it parses AND the text looks non-wordy
            # (no spaces / mostly non-letters). Real strings (addresses, names)
            # contain spaces/letters and should win.
            wordy = bool(text) and (
                " " in text or sum(c.isalpha() for c in text) >= max(3, 0.5 * len(text)))
            if is_msg and not wordy:
                decode_message(sub, fld, out, depth + 1, max_depth)
            elif text is not None:
                out.append({"path": fld, "wire": 2, "type": "str", "value": text})
            elif is_msg:
                decode_message(sub, fld, out, depth + 1, max_depth)
            else:
                out.append({"path": fld, "wire": 2, "type": "bytes",
                            "value": sub.hex(), "len": ln})
        else:
            # unknown/group wire types — stop this level
            break
    return out


# ---------------------------------------------------------------------------
# brute-force printable strings (backup; structure-independent)
# ---------------------------------------------------------------------------
def brute_strings(buf, min_len=3):
    """Scan for length-delimited printable runs: a varint length immediately
    followed by that many printable bytes. Returns list of (offset, text)."""
    out = []
    n = len(buf)
    pos = 0
    while pos < n:
        start = pos
        try:
            ln, after = _read_varint(buf, pos)
        except ValueError:
            pos += 1
            continue
        if min_len <= ln <= 4096 and after + ln <= n:
            chunk = buf[after:after + ln]
            if _printable_ratio(chunk) >= 0.95:
                try:
                    s = chunk.decode("utf-8")
                    if sum(c.isprintable() for c in s) == len(s):
                        out.append((start, s))
                        pos = after + ln
                        continue
                except UnicodeDecodeError:
                    pass
        pos += 1
    return out


# ---------------------------------------------------------------------------
# .dma reading
# ---------------------------------------------------------------------------
def read_appraisal_blob(dma_path):
    """Return the raw bytes of the 'Appraisal' entry inside a .dma zip."""
    with zipfile.ZipFile(dma_path, "r") as zf:
        names = zf.namelist()
        target = None
        for nm in names:
            if nm.lower().endswith("appraisal") or nm.lower() == "appraisal":
                target = nm
                break
        if target is None:
            # fall back to the largest entry
            target = max(names, key=lambda nm: zf.getinfo(nm).file_size)
        return zf.read(target)


def decode_dma(dma_path):
    """Decode a .dma into {'leaves': [...], 'strings': [...]}"""
    blob = read_appraisal_blob(dma_path)
    leaves = decode_message(blob)
    strings = brute_strings(blob)
    return {"leaves": leaves, "strings": strings, "blob_len": len(blob)}


def _top_level_fields(buf):
    """Decode only the top level; return {field_number: [sub-bytes, ...]} for
    length-delimited fields (wire type 2). Cheap — no recursion."""
    out = {}
    pos = 0
    n = len(buf)
    while pos < n:
        try:
            tag, pos = _read_varint(buf, pos)
        except ValueError:
            break
        wt = tag & 0x07
        fn = tag >> 3
        if wt == 0:
            try:
                _, pos = _read_varint(buf, pos)
            except ValueError:
                break
        elif wt == 1:
            pos += 8
        elif wt == 5:
            pos += 4
        elif wt == 2:
            try:
                ln, pos = _read_varint(buf, pos)
            except ValueError:
                break
            if pos + ln > n:
                break
            out.setdefault(fn, []).append(buf[pos:pos + ln])
            pos += ln
        else:
            break
    return out


def extract_schema_names(dma_path):
    """Fast: pull DataMaster's inline field-name dictionary (top-level field 3,
    sub-field 3) WITHOUT decoding the whole (possibly huge) blob.

    Returns a de-duplicated, order-preserving list of field-name strings.
    """
    blob = read_appraisal_blob(dma_path)
    top = _top_level_fields(blob)
    names = []
    seen = set()
    for f3 in top.get(3, []):
        # within field 3, the schema entries are sub-field 3 (repeated message),
        # each starting with a string name. Decode just this subtree.
        leaves = decode_message(f3, path="3")
        for lf in leaves:
            if lf["type"] != "str":
                continue
            p = lf["path"]
            # entries look like 3.3[k].1 (name) or bare 3.3[k]
            if p.startswith("3.3") and (p.endswith(".1") or "].1" not in p and p.count(".") == 1 or "[" in p):
                val = lf["value"].strip().lstrip(".'\"")
                # keep plausible identifiers (letters/digits, no spaces)
                if val and " " not in val and val[0].isalpha() and val not in seen:
                    seen.add(val)
                    names.append(val)
    return names


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Decode a DataMaster .dma (read-only)")
    ap.add_argument("dma", help="Path to .dma file")
    ap.add_argument("--json", help="Write full decode to this JSON path")
    ap.add_argument("--strings", action="store_true", help="Print brute-force strings only")
    ap.add_argument("--limit", type=int, default=120, help="Max leaves to print")
    args = ap.parse_args(argv)

    result = decode_dma(args.dma)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("Wrote {} ({} leaves, {} strings, blob {} bytes)".format(
            args.json, len(result["leaves"]), len(result["strings"]), result["blob_len"]))
        return 0

    if args.strings:
        for off, s in result["strings"]:
            print("{:>8}  {}".format(off, s))
        return 0

    print("# blob {} bytes | {} leaves | {} brute strings".format(
        result["blob_len"], len(result["leaves"]), len(result["strings"])))
    for leaf in result["leaves"][:args.limit]:
        v = leaf["value"]
        if isinstance(v, str) and len(v) > 70:
            v = v[:67] + "..."
        print("  {:<24} {:<5} {}".format(leaf["path"], leaf["type"], v))
    if len(result["leaves"]) > args.limit:
        print("  ... (+{} more leaves)".format(len(result["leaves"]) - args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
