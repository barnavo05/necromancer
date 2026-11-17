"""Compile and run COBOL with GnuCOBOL (cobc).

I/O contract: programs read one value per line from stdin (ACCEPT) and
write results to stdout (DISPLAY). Source is compiled in a throwaway
directory, run with a timeout and an output cap, and never sees the network
when run inside the Docker image (see Dockerfile).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

COMPILE_TIMEOUT = 30
RUN_TIMEOUT = 5
MAX_OUTPUT_BYTES = 64_000
MAX_SOURCE_BYTES = 100_000


class CobolError(Exception):
    pass


class CompiledCobol:
    """A compiled COBOL program. Use as a context manager to clean up."""

    def __init__(self, source: str):
        if len(source.encode()) > MAX_SOURCE_BYTES:
            raise CobolError("COBOL source is too large")
        if shutil.which("cobc") is None:
            raise CobolError("cobc (GnuCOBOL) is not installed")
        self._dir = Path(tempfile.mkdtemp(prefix="necro-"))
        src = self._dir / "prog.cbl"
        src.write_text(source)
        self.binary = self._dir / "prog"
        # Try fixed format first (classic COBOL), then free format.
        errors = []
        for fmt in ("-fixed", "-free"):
            proc = subprocess.run(
                ["cobc", "-x", fmt, "-o", str(self.binary), str(src)],
                capture_output=True, text=True, timeout=COMPILE_TIMEOUT,
                cwd=self._dir,
            )
            if proc.returncode == 0:
                return
            errors.append(proc.stderr)
        self.close()
        raise CobolError(_clean_compiler_errors(errors[0]))

    def run(self, inputs: list[str]) -> list[str]:
        """Run once. Returns stdout lines (right-stripped)."""
        stdin = "".join(line + "\n" for line in inputs)
        try:
            proc = subprocess.run(
                [str(self.binary)], input=stdin, capture_output=True, text=True,
                timeout=RUN_TIMEOUT, cwd=self._dir,
            )
        except subprocess.TimeoutExpired as exc:
            raise CobolError("COBOL program timed out") from exc
        if proc.returncode != 0:
            raise CobolError(f"COBOL program failed: {proc.stderr.strip()[:300]}")
        out = proc.stdout[:MAX_OUTPUT_BYTES]
        return [line.rstrip() for line in out.splitlines()]

    def close(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)

    def __enter__(self) -> "CompiledCobol":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _clean_compiler_errors(text: str) -> str:
    lines = [l for l in text.splitlines() if "_FORTIFY_SOURCE" not in l and "command-line" not in l]
    return "\n".join(lines)[:1500]
