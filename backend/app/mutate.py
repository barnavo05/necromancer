"""Mutation testing for the Seance: inject bugs into a Python translation and
check that the seance notices every one.

A strong seance kills the mutants. A mutant that survives is either an
equivalent change (it really behaves the same) or a gap in the test inputs,
and it is reported honestly either way.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .cobol_runner import CompiledCobol
from .python_runner import PythonError, run_python_batch
from .seance import _cobol_outputs, _spirits, boundary_literals, generate_cases

MAX_MUTANTS = 12
STRESS_CASES = 500


def _code_lines(source: str):
    """Yield (line_no, text) for lines that are real code (not comments or docstrings)."""
    in_doc = False
    for i, line in enumerate(source.splitlines()):
        s = line.strip()
        if s.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or s.startswith("#") or s.count('"""') == 2:
            continue
        yield i, line


def _sites(source: str) -> list[tuple[str, int, str, str]]:
    """(kind, line_index, new_line, description) for every possible single change."""
    out: list[tuple[str, int, str, str]] = []
    for i, line in _code_lines(source):
        if re.search(r"getcontext|CENTS\s*=|prec\b", line):
            continue  # precision settings and the quantum are not behaviour
        code, _, comment = line.partition("#")
        tail = ("  #" + comment) if comment else ""

        def swap(kind: str, old: str, new: str, regex: str | None = None, desc: str | None = None):
            pat = regex or re.escape(old)
            for m in re.finditer(pat, code):
                mutated = code[: m.start()] + (new if not regex else re.sub(pat, new, m.group(0))) + code[m.end():]
                out.append((kind, i, mutated + tail, desc or f"line {i + 1}: {old.strip()} became {new.strip()}"))

        swap("rounding", "ROUND_DOWN", "ROUND_HALF_UP")
        swap("rounding", "ROUND_HALF_UP", "ROUND_DOWN")
        swap("compare", ">=", ">")
        swap("compare", "<=", "<")
        swap("compare", " > ", " >= ", desc=f"line {i + 1}: > became >=")
        swap("compare", " < ", " <= ", desc=f"line {i + 1}: < became <=")
        for m in re.finditer(r'Decimal\("(\d+\.\d*?)(\d)"\)', code):
            digit = (int(m.group(2)) + 1) % 10
            new = f'Decimal("{m.group(1)}{digit}")'
            out.append(("constant", i, code[: m.start()] + new + code[m.end():] + tail,
                        f"line {i + 1}: {m.group(0)} became {new}"))
        for m in re.finditer(r"(?<![\w.\"'])(\d+)(?![\w.\"'])", code):
            if "Decimal(" in code[max(0, m.start() - 8): m.start()]:
                continue
            value = int(m.group(1))
            if value >= 5:
                new = str(value + 1)
                out.append(("constant", i, code[: m.start()] + new + code[m.end():] + tail,
                            f"line {i + 1}: {value} became {new}"))
        swap("arithmetic", " + ", " - ", desc=f"line {i + 1}: + became -")
    return out


def make_mutants(source: str) -> list[dict]:
    lines = source.splitlines()
    by_kind: dict[str, list[tuple[int, str, str]]] = {}
    for kind, i, new_line, desc in _sites(source):
        by_kind.setdefault(kind, []).append((i, new_line, desc))
    picked: list[tuple[int, str, str, str]] = []
    # Round robin over kinds so the sample covers every kind of mistake.
    queues = {k: list(v) for k, v in by_kind.items()}
    while queues and len(picked) < MAX_MUTANTS:
        for kind in list(queues):
            if not queues[kind]:
                del queues[kind]
                continue
            i, new_line, desc = queues[kind].pop(0)
            picked.append((i, new_line, desc, kind))
            if len(picked) >= MAX_MUTANTS:
                break
    mutants = []
    for i, new_line, desc, kind in picked:
        mutated = "\n".join(lines[:i] + [new_line] + lines[i + 1:]) + "\n"
        try:
            compile(mutated, "mutant.py", "exec")
        except SyntaxError:
            continue
        mutants.append({"kind": kind, "description": desc, "source": mutated})
    return mutants


def haunt(cobol_source: str, python_source: str, spec: list[dict], n: int = 150) -> dict:
    cases = generate_cases(spec, n, boundaries=boundary_literals(cobol_source))
    with CompiledCobol(cobol_source) as program:
        outs, errs = _cobol_outputs(program, cases)
    cases = cases[: len(outs)]
    baseline = _spirits(cases, outs, errs, run_python_batch(python_source, cases))
    if baseline:
        raise ValueError("The translation must pass the seance before it can be haunted")

    stress = {}

    def stress_pass(mutant_source: str):
        # Second chance for survivors: many more random inputs.
        if not stress:
            sc = generate_cases(spec, STRESS_CASES, seed=1, boundaries=boundary_literals(cobol_source))
            with CompiledCobol(cobol_source) as program:
                so, se = _cobol_outputs(program, sc)
            stress.update(cases=sc[: len(so)], outs=so, errs=se)
        sp = _spirits(stress["cases"], stress["outs"], stress["errs"], run_python_batch(mutant_source, stress["cases"]))
        return sp[0] if sp else None

    results = []
    for m in make_mutants(python_source):
        status, example = "survived", None
        try:
            spirits = _spirits(cases, outs, errs, run_python_batch(m["source"], cases))
            if spirits:
                status, example = "caught", spirits[0]
            else:
                late = stress_pass(m["source"])
                if late:
                    status, example = "caught_on_stress", late
        except PythonError:
            status = "caught"  # a mutant that hangs or will not load is also caught
        results.append({"kind": m["kind"], "description": m["description"], "status": status, "example": example})
    caught = sum(r["status"] != "survived" for r in results)
    return {
        "total": len(results),
        "caught": caught,
        "survived": len(results) - caught,
        "cases_per_mutant": len(cases),
        "stress_cases": STRESS_CASES,
        "mutants": results,
    }
