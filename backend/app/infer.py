"""Guess the stdin inputs of a COBOL program so the Seance can generate cases.

Recognises the contract used by the samples: each input is read with
ACCEPT into a text field and then converted with FUNCTION NUMVAL into a
numeric field. The numeric field's PIC gives the digits and scale. Ranges are
deliberately conservative (one digit of headroom, at most 4 whole digits)
because COBOL silently overflows, and a false mismatch caused by overflow would be misleading.
The user can edit the ranges before running the Seance.
"""
from __future__ import annotations

import re

MAX_WHOLE_DIGITS = 4

_PIC = re.compile(
    r"^\s*\d+\s+([A-Z0-9-]+)\s+PIC\s+(?:9\((\d+)\)|(9+))(?:V(?:9\((\d+)\)|(9+)))?\s*(?:VALUE\s+\S+)?\s*\.\s*$",
    re.I,
)
_ACCEPT = re.compile(r"^\s*ACCEPT\s+([A-Z0-9-]+)\s*$", re.I)
_NUMVAL = re.compile(r"COMPUTE\s+([A-Z0-9-]+)\s*=\s*FUNCTION\s+NUMVAL\s*\(\s*([A-Z0-9-]+)\s*\)", re.I)


def _fields(cobol: str) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for raw in cobol.splitlines():
        line = raw[6:] if len(raw) > 6 and raw[6] in " *-/D" else raw
        m = _PIC.match(line)
        if not m:
            continue
        name = m.group(1).upper()
        whole = int(m.group(2)) if m.group(2) else len(m.group(3))
        frac = 0
        if m.group(4):
            frac = int(m.group(4))
        elif m.group(5):
            frac = len(m.group(5))
        out[name] = (whole, frac)
    return out


def infer_inputs(cobol: str) -> list[dict]:
    fields = _fields(cobol)
    lines = cobol.splitlines()
    inputs: list[dict] = []
    for i, raw in enumerate(lines):
        if not _ACCEPT.match(raw[6:] if raw[6:7] in (" ", "*") and len(raw) > 6 else raw):
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        m = _NUMVAL.search(nxt)
        if not m or m.group(1).upper() not in fields:
            continue
        target = m.group(1).upper()
        digits, scale = fields[target]
        # Leave one digit of headroom: a PIC 9(2) loop counter that must reach 99
        # wraps to 00 and the program never ends.
        cap = max(1, min(digits - 1, MAX_WHOLE_DIGITS))
        inputs.append({
            "name": target.removeprefix("WS-").lower().replace("-", " "),
            "digits": digits,
            "scale": scale,
            "min": "0",
            "max": str(10**cap - 1),
        })
    return inputs
