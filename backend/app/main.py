from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .cobol_runner import CobolError
from .python_runner import PythonError
from .seance import run_seance

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"

app = FastAPI(title="Necromancer API")


def _load_sample(sample_id: str) -> dict:
    if not sample_id.isalnum():
        raise HTTPException(404, "Unknown sample")
    meta_path = SAMPLES_DIR / f"{sample_id}.json"
    if not meta_path.exists():
        raise HTTPException(404, "Unknown sample")
    meta = json.loads(meta_path.read_text())
    meta["id"] = sample_id
    meta["cobol"] = (SAMPLES_DIR / f"{sample_id}.cbl").read_text()
    py = SAMPLES_DIR / f"{sample_id}.py"
    meta["python"] = py.read_text() if py.exists() else None
    return meta


@app.get("/api/health")
def health() -> dict:
    return {"status": "alive"}


@app.get("/api/samples")
def list_samples() -> list[dict]:
    out = []
    for p in sorted(SAMPLES_DIR.glob("*.json")):
        meta = json.loads(p.read_text())
        out.append({"id": p.stem, "name": meta["name"], "summary": meta["summary"]})
    return out


@app.get("/api/samples/{sample_id}")
def get_sample(sample_id: str) -> dict:
    return _load_sample(sample_id)


class SeanceRequest(BaseModel):
    sample_id: str
    python: str | None = Field(default=None, max_length=50_000)
    cases: int = Field(default=200, ge=1, le=500)


@app.post("/api/seance")
def seance(req: SeanceRequest) -> dict:
    sample = _load_sample(req.sample_id)
    python_src = req.python or sample["python"]
    if not python_src:
        raise HTTPException(422, "No Python translation to test")
    try:
        return run_seance(sample["cobol"], python_src, sample["inputs"], req.cases)
    except (CobolError, PythonError) as exc:
        raise HTTPException(422, str(exc)) from exc
