"""The Seance: run COBOL and Python on many generated inputs and compare.

Inputs are generated with Hypothesis from a per-program input spec. COBOL
truncates silently on overflow, so each spec gives a safe range and the
generator stays inside it. Input lines are plain decimal text. Programs must
read them with ACCEPT into a text field plus FUNCTION NUMVAL, because GnuCOBOL
ACCEPT straight into a numeric field copies characters (so "19.99" into
PIC 9(2)V99 becomes 19.90).

Extras that make the proof stronger:
  * boundary hunter: constants found in the COBOL (40, 100, 0.0825 ...) are
    tested exactly and one step either side
  * shrinking: every failure is reduced to its smallest failing input
  * certificate: hashes and counts that identify exactly what was verified
  * mutation testing: inject bugs into the Python and check the seance
    catches them (see mutate.py)

Any input where the outputs differ is returned as a "restless spirit".
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache

from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

from .cobol_runner import CobolError, CompiledCobol
from .python_runner import run_python_batch

MAX_COBOL_FAILURES = 5


def format_value(n: int, scale: int) -> str:
    """Plain decimal text for a scaled integer, e.g. (3579, 2) -> "35.79"."""
    if scale == 0:
        return str(n)
    factor = 10 ** scale
    return f"{n // factor}.{n % factor:0{scale}d}"


def parse_value(text: str, scale: int) -> int:
    return int(Decimal(text) * 10 ** scale)


def boundary_literals(cobol: str) -> list[Decimal]:
    """Numeric constants used in the PROCEDURE DIVISION (thresholds, rates, caps)."""
    marker = re.search(r"PROCEDURE\s+DIVISION", cobol, re.I)
    if not marker:
        return []
    body = cobol[marker.end():]
    body = re.sub(r'"[^"]*"|\'[^\']*\'', " ", body)           # drop string literals
    body = "\n".join(l for l in body.splitlines() if not l.lstrip()[:1] == "*" and "*>" not in l[:12])
    found: list[Decimal] = []
    for m in re.finditer(r"(?<![A-Za-z0-9-])(\d+(?:\.\d+)?)(?![A-Za-z0-9-])", body):
        value = Decimal(m.group(1))
        if value not in found and value != 0:
            found.append(value)
    return found


def field_strategy(field: dict, boundaries: list[Decimal] | None = None) -> st.SearchStrategy[str]:
    scale = field["scale"]
    factor = 10 ** scale
    lo = int(Decimal(field["min"]) * factor)
    hi = int(Decimal(field["max"]) * factor)
    edge_values = {lo, hi, min(lo + 1, hi), max(hi - 1, lo)}
    for b in boundaries or []:
        n = int(b * factor)
        for candidate in (n - 1, n, n + 1):
            if lo <= candidate <= hi:
                edge_values.add(candidate)
    edges = st.sampled_from(sorted(edge_values))
    body = st.one_of(edges, st.integers(min_value=lo, max_value=hi))
    return body.map(lambda n: format_value(n, scale))


def inputs_strategy(spec: list[dict], boundaries: list[Decimal] | None = None):
    return st.tuples(*[field_strategy(f, boundaries) for f in spec]).map(list)


def generate_cases(spec: list[dict], n: int, seed: int = 0, boundaries: list[Decimal] | None = None) -> list[list[str]]:
    """Generate up to n distinct input cases (deterministic for a given seed)."""
    cases: list[list[str]] = []

    @settings(
        max_examples=n, database=None, derandomize=(seed == 0),
        phases=[Phase.generate], deadline=None,
        suppress_health_check=list(HealthCheck),
    )
    @given(inputs_strategy(spec, boundaries))
    def collect(case: list[str]) -> None:
        cases.append(case)

    collect()
    return cases


def _cobol_outputs(program: CompiledCobol, cases: list[list[str]]):
    outs: list[list[str] | None] = []
    errs: list[str | None] = []
    failures = 0
    for case in cases:
        try:
            outs.append(program.run(case))
            errs.append(None)
        except CobolError as exc:
            # A hang or crash in the old program is itself a finding.
            outs.append(None)
            errs.append(str(exc))
            failures += 1
            if failures >= MAX_COBOL_FAILURES:
                break
    return outs, errs


def _spirits(cases, outs, errs, py_out) -> list[dict]:
    spirits = []
    for case, expected, err, got in zip(cases, outs, errs, py_out):
        actual = got.get("ok")
        if err or actual != expected:
            spirits.append({"inputs": case, "cobol": expected, "python": actual, "error": err or got.get("error")})
    return spirits


def shrink_case(program: CompiledCobol, python_source: str, spec: list[dict], case: list[str]) -> dict:
    """Greedily reduce a failing case to a smaller one that still fails."""
    scales = [f["scale"] for f in spec]
    lows = [int(Decimal(f["min"]) * 10 ** f["scale"]) for f in spec]
    current = [parse_value(v, s) for v, s in zip(case, scales)]

    def evaluate(batch: list[list[int]]):
        texts = [[format_value(n, s) for n, s in zip(c, scales)] for c in batch]
        py = run_python_batch(python_source, texts)
        results = []
        for t, p in zip(texts, py):
            try:
                cobol_out, err = program.run(t), None
            except CobolError as exc:
                cobol_out, err = None, str(exc)
            if err or p.get("ok") != cobol_out:
                results.append({"inputs": t, "cobol": cobol_out, "python": p.get("ok"), "error": err or p.get("error")})
            else:
                results.append(None)
        return results

    best = evaluate([current])[0]
    if best is None:
        return {"inputs": case, "cobol": None, "python": None, "error": "could not reproduce"}
    for _ in range(25):
        candidates: list[list[int]] = []
        for i, n in enumerate(current):
            lo = lows[i]
            for smaller in (lo, (n + lo) // 2, n - (n - lo) // 4, n - 1):
                if lo <= smaller < n:
                    cand = current[:i] + [smaller] + current[i + 1:]
                    if cand not in candidates:
                        candidates.append(cand)
        if not candidates:
            break
        candidates.sort(key=sum)
        results = evaluate(candidates)
        improved = next(((c, r) for c, r in zip(candidates, results) if r is not None), None)
        if not improved:
            break
        current, best = improved
    return best


@lru_cache(maxsize=1)
def _cobc_version() -> str:
    try:
        out = subprocess.run(["cobc", "--version"], capture_output=True, text=True, timeout=10).stdout
        return out.splitlines()[0].strip()
    except Exception:
        return "unknown"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def run_seance(cobol_source: str, python_source: str, spec: list[dict], n: int = 200, shrink: bool = True) -> dict:
    boundaries = boundary_literals(cobol_source)
    cases = generate_cases(spec, n, boundaries=boundaries)
    with CompiledCobol(cobol_source) as program:
        outs, errs = _cobol_outputs(program, cases)
        cases = cases[: len(outs)]
        py_out = run_python_batch(python_source, cases)
        spirits = _spirits(cases, outs, errs, py_out)

        minimal = None
        if spirits and shrink:
            scales = [f["scale"] for f in spec]
            easiest = min((s for s in spirits if not s["error"] or s["cobol"] is not None),
                          key=lambda s: sum(parse_value(v, sc) for v, sc in zip(s["inputs"], scales)),
                          default=None)
            if easiest:
                minimal = shrink_case(program, python_source, spec, easiest["inputs"])

    verified = len(spirits) == 0 and len(cases) > 0
    return {
        "cases_run": len(cases),
        "matched": len(cases) - len(spirits),
        "verified": verified,
        "restless_spirits": spirits[:20],
        "spirit_count": len(spirits),
        "minimal_spirit": minimal,
        "boundaries_tested": [str(b) for b in boundaries],
        "certificate": {
            "verified": verified,
            "cases_run": len(cases),
            "matched": len(cases) - len(spirits),
            "cobol_sha256": _sha(cobol_source),
            "python_sha256": _sha(python_source),
            "input_spec": spec,
            "boundaries_tested": [str(b) for b in boundaries],
            "generator": "hypothesis (deterministic)",
            "cobol_compiler": _cobc_version(),
            "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
