from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import llm
from .cobol_runner import CobolError
from .infer import infer_inputs
from .python_runner import PythonError
from .seance import run_seance

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"

app = FastAPI(title="Necromancer API")

# Comma separated list of allowed frontend origins, e.g. your Vercel URL.
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _origins], allow_methods=["GET", "POST"], allow_headers=["*"])


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


class InputField(BaseModel):
    name: str = Field(max_length=40)
    digits: int = Field(ge=1, le=18)
    scale: int = Field(ge=0, le=6)
    min: str = Field(pattern=r"^\d{1,18}(\.\d{1,6})?$")
    max: str = Field(pattern=r"^\d{1,18}(\.\d{1,6})?$")


class CodeRequest(BaseModel):
    """Either a bundled sample id or custom COBOL source."""
    sample_id: str | None = None
    cobol: str | None = Field(default=None, max_length=20_000)


def _resolve_cobol(req: CodeRequest) -> tuple[str, dict | None]:
    if req.sample_id:
        sample = _load_sample(req.sample_id)
        return sample["cobol"], sample
    if req.cobol:
        return req.cobol, None
    raise HTTPException(422, "Provide sample_id or cobol")


@app.post("/api/infer-inputs")
def infer(req: CodeRequest) -> dict:
    cobol, sample = _resolve_cobol(req)
    spec = sample["inputs"] if sample else infer_inputs(cobol)
    if not spec:
        raise HTTPException(
            422,
            "Could not find any inputs. Read each value with ACCEPT into a text field, "
            "then COMPUTE the number with FUNCTION NUMVAL on the next line.",
        )
    return {"inputs": spec}


@app.post("/api/exhume")
def exhume(req: CodeRequest) -> dict:
    cobol, sample = _resolve_cobol(req)
    if sample and sample.get("paragraphs"):
        return {"summary": sample["summary"], "paragraphs": sample["paragraphs"], "source": "bundled"}
    try:
        return {**llm.exhume(cobol), "source": "model"}
    except llm.LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/resurrect")
def resurrect(req: CodeRequest) -> dict:
    cobol, sample = _resolve_cobol(req)
    if sample and sample.get("python"):
        return {"python": sample["python"], "source": "bundled"}
    try:
        return {"python": llm.resurrect(cobol), "source": "model"}
    except llm.LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


class SeanceRequest(BaseModel):
    sample_id: str | None = None
    cobol: str | None = Field(default=None, max_length=20_000)
    python: str | None = Field(default=None, max_length=50_000)
    inputs: list[InputField] | None = Field(default=None, max_length=8)
    cases: int = Field(default=200, ge=1, le=500)


@app.post("/api/seance")
def seance(req: SeanceRequest) -> dict:
    sample = _load_sample(req.sample_id) if req.sample_id else None
    cobol = req.cobol or (sample["cobol"] if sample else None)
    python_src = req.python or (sample["python"] if sample else None)
    spec = [f.model_dump() for f in req.inputs] if req.inputs else (sample["inputs"] if sample else None)
    if not cobol or not python_src or not spec:
        raise HTTPException(422, "Seance needs COBOL, Python and an input spec (or a sample_id)")
    try:
        return run_seance(cobol, python_src, spec, req.cases)
    except (CobolError, PythonError) as exc:
        raise HTTPException(422, str(exc)) from exc
