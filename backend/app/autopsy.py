"""Autopsy: static findings about COBOL behaviour that surprises modern programmers.

Pure text analysis, no model and no compiler. Each finding says where it
happens and why it matters for a translation.
"""
from __future__ import annotations

import re

from .infer import _fields

_VERBS = r"COMPUTE|MOVE|ADD|SUBTRACT|MULTIPLY|DIVIDE|IF|ELSE|END-IF|PERFORM|END-PERFORM|DISPLAY|ACCEPT|STOP|EVALUATE|WHEN|END-EVALUATE|GO|EXIT|CONTINUE"


def _paragraphs(cobol: str) -> list[tuple[str, str]]:
    """(paragraph name, text) for the PROCEDURE DIVISION, with comments removed."""
    lines = cobol.splitlines()
    start = next((i for i, l in enumerate(lines) if re.search(r"PROCEDURE\s+DIVISION", l, re.I)), None)
    if start is None:
        return []
    paras: list[tuple[str, list[str]]] = [("(start)", [])]
    for raw in lines[start + 1:]:
        stripped = raw.strip()
        if stripped.startswith("*") or stripped.startswith("*>"):
            continue
        m = re.match(r"^ {7}([A-Z0-9-]+)\.\s*$", raw)
        if m:
            paras.append((m.group(1), []))
        else:
            paras[-1][1].append(raw.strip())
    return [(name, " ".join(body)) for name, body in paras if body]


def _statements(text: str, verb: str):
    pattern = rf"\b{verb}\b(.*?)(?=\b(?:{_VERBS})\b|\.\s|\.$|$)"
    for m in re.finditer(pattern, text, re.S):
        yield m.group(0)


def autopsy(cobol: str) -> list[dict]:
    fields = _fields(cobol)
    paragraphs = _paragraphs(cobol)
    findings: list[dict] = []

    def add(kind: str, where: str, title: str, detail: str) -> None:
        findings.append({"kind": kind, "where": where, "title": title, "detail": detail})

    unsigned = {n for n in fields}  # _fields only matches unsigned PIC 9 forms
    sized_targets: dict[str, list[str]] = {}
    unsigned_hits: list[tuple[str, str]] = []

    for name, text in paragraphs:
        for stmt in _statements(text, "COMPUTE"):
            m = re.match(r"COMPUTE\s+([A-Z0-9-]+)(\s+ROUNDED)?\s*=\s*(.*)", stmt, re.S)
            if not m:
                continue
            target, rounded, expr = m.group(1), bool(m.group(2)), m.group(3)
            if "NUMVAL" in expr.upper():
                continue
            if rounded:
                add("rounds", name, f"{target} is rounded",
                    "ROUNDED rounds half away from zero to the target's decimals. In Python that is ROUND_HALF_UP, not the default banker's rounding.")
            elif re.search(r"[*/]", expr):
                add("truncates", name, f"{target} is cut off, not rounded",
                    "Without ROUNDED, extra decimals are dropped when the result is stored. A Python translation must quantize with ROUND_DOWN.")
            if "ON SIZE ERROR" not in text.upper():
                sized_targets.setdefault(name, []).append(target)
            if target in unsigned and re.search(r"\s-\s", expr):
                unsigned_hits.append((name, target))

        for stmt in _statements(text, "SUBTRACT"):
            m = re.search(r"FROM\s+([A-Z0-9-]+)", stmt)
            if m and m.group(1) in unsigned:
                unsigned_hits.append((name, m.group(1)))

        for m in re.finditer(r"PERFORM\s+([A-Z0-9-]+)?\s*VARYING\s+([A-Z0-9-]+)\s+FROM\s+\S+\s+BY\s+\S+\s+UNTIL\s+([A-Z0-9-]+)\s*(>=|>|=)\s*([A-Z0-9-]+)", text):
            counter = m.group(2)
            if counter in fields:
                digits = fields[counter][0]
                limit = 10 ** digits - 1
                add("loop", name, f"Loop counter {counter} wraps at {limit}",
                    f"{counter} holds at most {limit}. If the loop limit can reach {limit}, the counter wraps to 0 and the loop never ends.")
        if re.search(r"UNTIL\s+[A-Z0-9-]+\s*=\s*0\s+OR\s+[A-Z0-9-]+\s*>=\s*\d+", text):
            add("loop", name, "Loop has a safety cap",
                "The loop stops at a fixed count even when its main condition is never met. A translation must keep that cap.")

        for m in re.finditer(r"ACCEPT\s+([A-Z0-9-]+)\s*(?=[A-Z]|$)", text):
            if m.group(1) in fields:
                add("accept", name, f"ACCEPT reads straight into numeric {m.group(1)}",
                    "GnuCOBOL copies the typed characters into the number, so 19.99 into PIC 9(2)V99 becomes 19.90. Read text first, then FUNCTION NUMVAL.")

        if re.search(r"\bEVALUATE\b", text):
            add("order", name, "EVALUATE picks the first matching WHEN",
                "Order matters. A translation to if/elif must keep the same order.")

    if unsigned_hits:
        names = sorted({t for _, t in unsigned_hits})
        where = ", ".join(sorted({w for w, _ in unsigned_hits}))
        add("unsigned", where, "Unsigned fields that are subtracted into: " + ", ".join(names),
            "An unsigned PIC cannot hold a negative number. If a result can go below zero, COBOL stores the absolute value, so it comes out positive instead of negative.")

    wide: dict[str, str] = {}
    for name, targets in sized_targets.items():
        for t in targets:
            if t in fields:
                wide.setdefault(t, name)
    if wide:
        smallest = min(wide, key=lambda t: fields[t][0] + fields[t][1])
        add("overflow", ", ".join(sorted(set(wide.values()))),
            "No ON SIZE ERROR guard on: " + ", ".join(sorted(wide)),
            f"If a result is too big for its PIC, COBOL silently drops the high digits instead of failing. The tightest field is {smallest}, {fields[smallest][0] + fields[smallest][1]} digits, so test inputs must stay in range.")

    rates = {m for _, text in paragraphs for m in re.findall(r"(?<![A-Z0-9-])0\.\d{2,}(?![A-Z0-9-])", text)}
    if rates:
        add("constants", "PROCEDURE DIVISION", "Hard coded rates: " + ", ".join(sorted(rates)),
            "These numbers are business rules buried in code. Keep them exact as Decimal values in the translation.")

    # De-duplicate identical findings and keep order.
    seen, unique = set(), []
    for f in findings:
        key = (f["kind"], f["where"], f["title"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique
