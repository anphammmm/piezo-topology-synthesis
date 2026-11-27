"""Minimal reader for LTspice .raw waveform files (real-valued transient data, binary or ASCII).

Use uncompressed files (`.options plotwinsize=0`, as reproduce.py --waveforms does).
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, List


def _decode_header(raw: bytes):
    """Return (header_text, data_start, kind) with kind 'binary' or 'ascii'."""
    utf16 = len(raw) > 1 and raw[1] == 0
    enc = "utf-16-le" if utf16 else "latin-1"
    for marker, kind in (("Binary:\n", "binary"), ("Values:\n", "ascii")):
        m = marker.encode(enc)
        i = raw.find(m)
        if i < 0 and not utf16:
            m = marker.replace("\n", "\r\n").encode(enc)
            i = raw.find(m)
        if i >= 0:
            return raw[:i].decode(enc), i + len(m), kind, enc
    raise ValueError("not an LTspice raw file: no 'Binary:' or 'Values:' section")


def read_raw(path) -> Dict[str, List[float]]:
    raw = Path(path).read_bytes()
    header, start, kind, enc = _decode_header(raw)
    lines = header.replace("\r\n", "\n").split("\n")
    info, names = {}, []
    in_vars = False
    for line in lines:
        if in_vars:
            parts = line.split()
            if len(parts) >= 3:
                names.append(parts[1])
            continue
        if line.startswith("Variables:"):
            in_vars = True
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip().lower()] = v.strip()
    nvars = int(info["no. variables"])
    npts = int(info["no. points"])
    names = names[:nvars]
    flags = info.get("flags", "").lower()
    if "complex" in flags:
        raise ValueError("complex (AC) data is not supported")
    out: Dict[str, List[float]] = {n: [] for n in names}
    if kind == "binary":
        double = "double" in flags
        fmt = "<" + "d" * nvars if double else "<d" + "f" * (nvars - 1)
        size = struct.calcsize(fmt)
        data = raw[start:]
        npts = min(npts, len(data) // size)
        for k in range(npts):
            vals = struct.unpack_from(fmt, data, k * size)
            for n, v in zip(names, vals):
                out[n].append(v)
    else:
        toks = raw[start:].decode(enc).split()
        step = nvars + 1
        for k in range(min(npts, len(toks) // step)):
            vals = toks[k * step + 1:(k + 1) * step]
            for n, v in zip(names, vals):
                out[n].append(float(v.split(",")[0]))
    if names and names[0].lower() == "time":
        out[names[0]] = [abs(t) for t in out[names[0]]]   # LTspice marks some points with a negative time
    return out
