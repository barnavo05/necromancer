"""The Seance: run COBOL and Python on many generated inputs and compare.

Inputs are generated with Hypothesis from a per-program input spec. COBOL
truncates silently on overflow, so each spec gives a safe range and the
generator stays inside it. Input lines are plain decimal text. Programs must read them with ACCEPT into
a text field plus FUNCTION NUMVAL, because GnuCOBOL ACCEPT straight into a
numeric field copies characters (so "19.99" into PIC 9(2)V99 becomes 19.90).
Any input where the outputs differ is returned
as a "restless spirit".
"""
from __future__ import annotations

from decimal import Decimal

from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

from .cobol_runner import CompiledCobol
from .python_runner import run_python_batch


def field_strategy(field: dict) -> st.SearchStrategy[str]:
    scale = field["scale"]
    factor = 10 ** scale
    lo = int(Decimal(field["min"]) * factor)
    hi = int(Decimal(field["max"]) * factor)
    # Mix edge values with uniform draws so boundaries are always hit.
    edges = st.sampled_from([lo, hi, min(lo + 1, hi), max(hi - 1, lo)])
    body = st.one_of(edges, st.integers(min_value=lo, max_value=hi))

    def fmt(n: int) -> str:
        # Plain decimal text, e.g. "35.79". COBOL reads it with ACCEPT + NUMVAL.
        if scale == 0:
            return str(n)
        return f"{n // factor}.{n % factor:0{scale}d}"

    return body.map(fmt)


def inputs_strategy(spec: list[dict]) -> st.SearchStrategy[list[str]]:
    return st.tuples(*[field_strategy(f) for f in spec]).map(list)


def generate_cases(spec: list[dict], n: int, seed: int = 0) -> list[list[str]]:
    """Generate up to n distinct input cases (deterministic for a given seed)."""
    cases: list[list[str]] = []

    @settings(
        max_examples=n, database=None, derandomize=(seed == 0),
        phases=[Phase.generate], deadline=None,
        suppress_health_check=list(HealthCheck),
    )
    @given(inputs_strategy(spec))
    def collect(case: list[str]) -> None:
        cases.append(case)

    collect()
    return cases


def run_seance(cobol_source: str, python_source: str, spec: list[dict], n: int = 200) -> dict:
    cases = generate_cases(spec, n)
    with CompiledCobol(cobol_source) as program:
        cobol_out = [program.run(c) for c in cases]
    py_out = run_python_batch(python_source, cases)

    spirits = []
    for case, expected, got in zip(cases, cobol_out, py_out):
        actual = got.get("ok")
        if actual != expected:
            spirits.append({
                "inputs": case,
                "cobol": expected,
                "python": actual,
                "error": got.get("error"),
            })
    return {
        "cases_run": len(cases),
        "matched": len(cases) - len(spirits),
        "verified": len(spirits) == 0 and len(cases) > 0,
        "restless_spirits": spirits[:20],
        "spirit_count": len(spirits),
    }
