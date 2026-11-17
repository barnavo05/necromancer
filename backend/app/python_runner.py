"""Run a translated Python program in a separate process.

Contract: the translated module defines `main(lines: list[str]) -> list[str]`
which takes the stdin lines and returns the stdout lines, exactly as the
COBOL program would. It runs in a child process with a timeout so a bad
translation cannot hang or crash the server.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_TIMEOUT = 10

_HARNESS = """
import json, sys
src = open(sys.argv[1]).read()
ns = {"__name__": "translated"}
exec(compile(src, "translated.py", "exec"), ns)
cases = json.load(sys.stdin)
out = []
for lines in cases:
    try:
        out.append({"ok": [str(x).rstrip() for x in ns["main"](lines)]})
    except Exception as exc:
        out.append({"error": type(exc).__name__ + ": " + str(exc)[:200]})
json.dump(out, sys.stdout)
"""


class PythonError(Exception):
    pass


def run_python_batch(source: str, cases: list[list[str]]) -> list[dict]:
    """Run many input cases in one process. Each result is {"ok": [...]} or {"error": "..."}."""
    with tempfile.TemporaryDirectory(prefix="necro-py-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "translated.py").write_text(source)
        (tmp_path / "harness.py").write_text(_HARNESS)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(tmp_path / "harness.py"), str(tmp_path / "translated.py")],
                input=json.dumps(cases), capture_output=True, text=True,
                timeout=RUN_TIMEOUT, cwd=tmp,
            )
        except subprocess.TimeoutExpired as exc:
            raise PythonError("Python program timed out") from exc
    if proc.returncode != 0:
        raise PythonError(f"Python program failed to load: {proc.stderr.strip()[-300:]}")
    return json.loads(proc.stdout)
