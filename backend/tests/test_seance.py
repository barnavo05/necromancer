import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cobol_runner import CobolError, CompiledCobol
from app.main import app
from app.python_runner import run_python_batch
from app.seance import generate_cases, run_seance

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
META = json.loads((SAMPLES / "interest.json").read_text())
COBOL = (SAMPLES / "interest.cbl").read_text()
PYTHON = (SAMPLES / "interest.py").read_text()

client = TestClient(app)


def test_cobol_compiles_and_runs():
    with CompiledCobol(COBOL) as prog:
        assert prog.run(["1000.00", "5.00", "10"]) == [
            "BALANCE=000001628.86",
            "INTEREST=000000628.86",
        ]


def test_cobol_compile_error_is_reported():
    with pytest.raises(CobolError):
        CompiledCobol("THIS IS NOT COBOL")


def test_case_generation_stays_in_range_and_hits_edges():
    cases = generate_cases(META["inputs"], 100)
    assert len(cases) > 50
    for principal, rate, years in cases:
        assert 0 <= float(principal) <= 100000
        assert 0 <= float(rate) <= 20
        assert 0 <= int(years) <= 30


def test_python_runner_reports_errors_per_case():
    out = run_python_batch("def main(lines):\n    return [1 / int(lines[0])]\n", [["2"], ["0"]])
    assert out[0] == {"ok": ["0.5"]}
    assert "ZeroDivisionError" in out[1]["error"]


def test_good_translation_is_verified():
    result = run_seance(COBOL, PYTHON, META["inputs"], 150)
    assert result["verified"] is True
    assert result["spirit_count"] == 0


def test_wrong_translation_raises_restless_spirits():
    # Rounds half-up instead of truncating, like a careless translation would.
    bad = PYTHON.replace("ROUND_DOWN)", "ROUND_HALF_UP)").replace(
        "import Decimal, ROUND_DOWN", "import Decimal, ROUND_HALF_UP, ROUND_DOWN"
    ).replace("from decimal import Decimal, ROUND_DOWN,", "from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN,")
    result = run_seance(COBOL, bad, META["inputs"], 150)
    assert result["verified"] is False
    assert result["spirit_count"] > 0
    spirit = result["restless_spirits"][0]
    assert spirit["cobol"] != spirit["python"]


# API endpoints

def test_health():
    assert client.get("/api/health").json() == {"status": "alive"}


def test_list_samples():
    data = client.get("/api/samples").json()
    assert any(s["id"] == "interest" for s in data)


def test_get_sample_and_unknown_sample():
    sample = client.get("/api/samples/interest").json()
    assert "PROGRAM-ID. INTEREST" in sample["cobol"]
    assert client.get("/api/samples/nope").status_code == 404
    assert client.get("/api/samples/..%2Fetc").status_code == 404


def test_seance_endpoint():
    res = client.post("/api/seance", json={"sample_id": "interest", "cases": 50})
    assert res.status_code == 200
    assert res.json()["verified"] is True


def test_seance_endpoint_rejects_broken_python():
    res = client.post("/api/seance", json={"sample_id": "interest", "python": "def nope(:", "cases": 5})
    assert res.status_code == 422
