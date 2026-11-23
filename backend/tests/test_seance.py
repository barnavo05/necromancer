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


# All bundled samples, Exhume, Resurrect

SAMPLE_IDS = sorted(p.stem for p in SAMPLES.glob("*.json"))


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_every_sample_is_verified(sample_id):
    res = client.post("/api/seance", json={"sample_id": sample_id, "cases": 100})
    assert res.status_code == 200
    assert res.json()["verified"] is True, res.json()["restless_spirits"][:1]


def test_five_samples_exist():
    assert SAMPLE_IDS == ["balance", "interest", "invoice", "loan", "payroll"]


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_bundled_exhume_and_resurrect(sample_id):
    ex = client.post("/api/exhume", json={"sample_id": sample_id}).json()
    assert ex["source"] == "bundled" and ex["paragraphs"]
    re_ = client.post("/api/resurrect", json={"sample_id": sample_id}).json()
    assert "def main" in re_["python"]


def test_custom_cobol_without_key_is_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    res = client.post("/api/exhume", json={"cobol": "       IDENTIFICATION DIVISION."})
    assert res.status_code == 503


def test_exhume_and_resurrect_with_mocked_model(monkeypatch):
    from app import llm

    replies = iter([
        '```json\n{"summary": "Adds numbers.", "paragraphs": [{"name": "MAIN", "explanation": "Adds."}]}\n```',
        "```python\ndef main(lines):\n    return []\n```",
    ])
    monkeypatch.setattr(llm, "complete", lambda *a, **k: next(replies))
    ex = client.post("/api/exhume", json={"cobol": "X"}).json()
    assert ex["source"] == "model" and ex["summary"] == "Adds numbers."
    py = client.post("/api/resurrect", json={"cobol": "X"}).json()
    assert py["python"].startswith("def main")


def test_resurrect_rejects_model_output_without_main(monkeypatch):
    from app import llm

    monkeypatch.setattr(llm, "complete", lambda *a, **k: "print('hi')")
    assert client.post("/api/resurrect", json={"cobol": "X"}).status_code == 503


def test_custom_seance_validates_input_spec():
    bad = {"cobol": COBOL, "python": PYTHON, "inputs": [{"name": "x", "digits": 2, "scale": 0, "min": "abc", "max": "9"}]}
    assert client.post("/api/seance", json=bad).status_code == 422


def test_custom_seance_with_own_spec():
    body = {"cobol": COBOL, "python": PYTHON, "inputs": META["inputs"], "cases": 30}
    res = client.post("/api/seance", json=body)
    assert res.status_code == 200 and res.json()["verified"] is True


# Input inference for custom COBOL

@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_infer_inputs_matches_each_sample_shape(sample_id):
    from app.infer import infer_inputs

    sample = json.loads((SAMPLES / f"{sample_id}.json").read_text())
    cobol = (SAMPLES / f"{sample_id}.cbl").read_text()
    guessed = infer_inputs(cobol)
    assert [(g["digits"], g["scale"]) for g in guessed] == [(f["digits"], f["scale"]) for f in sample["inputs"]]


def test_inferred_inputs_run_a_clean_seance():
    from app.infer import infer_inputs

    spec = infer_inputs(COBOL)
    result = run_seance(COBOL, PYTHON, spec, 60)
    assert result["verified"] is True


def test_infer_endpoint_for_custom_cobol_and_failure():
    ok = client.post("/api/infer-inputs", json={"cobol": COBOL})
    assert ok.status_code == 200 and len(ok.json()["inputs"]) == 3
    bad = client.post("/api/infer-inputs", json={"cobol": "       IDENTIFICATION DIVISION."})
    assert bad.status_code == 422


def test_cobol_hang_is_reported_as_a_restless_spirit():
    hang = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. HANG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE PIC X(20).
       01 WS-N PIC 9(2).
       01 WS-I PIC 9(2).
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-N = FUNCTION NUMVAL(WS-LINE)
           PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > WS-N
               CONTINUE
           END-PERFORM
           DISPLAY "DONE"
           STOP RUN.
"""
    py = "def main(lines):\n    return ['DONE']\n"
    spec = [{"name": "n", "digits": 2, "scale": 0, "min": "98", "max": "99"}]
    result = run_seance(hang, py, spec, 6)
    assert result["verified"] is False
    spirit = result["restless_spirits"][0]
    assert spirit["cobol"] is None and "timed out" in spirit["error"]


def test_invoice_truncating_the_rounded_tax_is_caught():
    meta = json.loads((SAMPLES / "invoice.json").read_text())
    cobol = (SAMPLES / "invoice.cbl").read_text()
    py = (SAMPLES / "invoice.py").read_text()
    assert run_seance(cobol, py, meta["inputs"], 150)["verified"] is True
    wrong = py.replace("ROUND_HALF_UP)", "ROUND_DOWN)")
    result = run_seance(cobol, wrong, meta["inputs"], 150)
    assert result["verified"] is False
    assert any(s["cobol"][2] != s["python"][2] for s in result["restless_spirits"])


# Autopsy, smallest failing input, certificate, boundary hunter, haunt, exorcise

def test_autopsy_flags_the_real_traps():
    findings = client.post("/api/autopsy", json={"sample_id": "invoice"}).json()["findings"]
    kinds = {f["kind"] for f in findings}
    assert {"rounds", "truncates", "order", "overflow", "constants"} <= kinds
    loop = client.post("/api/autopsy", json={"sample_id": "interest"}).json()["findings"]
    assert any(f["kind"] == "loop" and "wraps at 99" in f["title"] for f in loop)


def test_autopsy_flags_accept_into_numeric():
    risky = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. R.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-RATE PIC 9(2)V99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-RATE
           DISPLAY WS-RATE
           STOP RUN.
"""
    findings = client.post("/api/autopsy", json={"cobol": risky}).json()["findings"]
    assert any(f["kind"] == "accept" for f in findings)


def test_boundary_hunter_finds_constants_and_tests_both_sides():
    from app.seance import boundary_literals

    assert {str(b) for b in boundary_literals((SAMPLES / "payroll.cbl").read_text())} >= {"40", "1.5", "500", "0.20"}
    spec = [{"name": "hours", "digits": 3, "scale": 1, "min": "0", "max": "100"}]
    cases = {c[0] for c in generate_cases(spec, 400, boundaries=boundary_literals((SAMPLES / "payroll.cbl").read_text()))}
    assert {"39.9", "40.0", "40.1"} <= cases


def test_failures_shrink_to_a_tiny_input_and_certificate_is_issued():
    meta = json.loads((SAMPLES / "invoice.json").read_text())
    cobol = (SAMPLES / "invoice.cbl").read_text()
    py = (SAMPLES / "invoice.py").read_text()
    wrong = py.replace("ROUND_HALF_UP)", "ROUND_DOWN)")
    result = run_seance(cobol, wrong, meta["inputs"], 200)
    minimal = result["minimal_spirit"]
    assert minimal and minimal["cobol"] != minimal["python"]
    assert minimal["inputs"] == ["1", "0.07"]
    good = run_seance(cobol, py, meta["inputs"], 60)
    cert = good["certificate"]
    assert cert["verified"] is True and len(cert["cobol_sha256"]) == 64 and len(cert["python_sha256"]) == 64
    assert cert["cobol_compiler"].startswith("cobc")


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_haunt_catches_most_injected_bugs(sample_id):
    res = client.post("/api/haunt", json={"sample_id": sample_id, "cases": 100})
    assert res.status_code == 200
    body = res.json()
    # balance is a two line program, so it only offers one bug to inject
    assert body["total"] >= (1 if sample_id == "balance" else 3)
    assert body["caught"] / body["total"] >= 0.6
    assert all(m["status"] in {"caught", "caught_on_stress", "survived"} for m in body["mutants"])


def test_haunt_refuses_a_translation_that_already_fails():
    bad = PYTHON.replace("ROUND_DOWN)", "ROUND_HALF_UP)").replace(
        "from decimal import Decimal, ROUND_DOWN,", "from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN,")
    res = client.post("/api/haunt", json={"sample_id": "interest", "python": bad, "cases": 80})
    assert res.status_code == 422


def test_exorcise_repairs_a_bad_translation_with_a_mocked_model(monkeypatch):
    from app import llm

    bad = PYTHON.replace("ROUND_DOWN)", "ROUND_HALF_UP)").replace(
        "from decimal import Decimal, ROUND_DOWN,", "from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN,")
    seen = {}

    def fake_repair(cobol, python, spirits):
        seen["spirits"] = spirits
        return PYTHON

    monkeypatch.setattr(llm, "repair", fake_repair)
    res = client.post("/api/exorcise", json={"sample_id": "interest", "python": bad, "cases": 60})
    assert res.status_code == 200
    body = res.json()
    assert body["verified"] is True
    assert len(body["rounds"]) == 2 and body["rounds"][0]["spirit_count"] > 0
    assert seen["spirits"]


def test_exorcise_without_a_key_is_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    bad = PYTHON.replace("ROUND_DOWN)", "ROUND_HALF_UP)").replace(
        "from decimal import Decimal, ROUND_DOWN,", "from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN,")
    res = client.post("/api/exorcise", json={"sample_id": "interest", "python": bad, "cases": 40})
    assert res.status_code == 503


# Signed fields

SIGNED_COBOL = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. SIGNEDDIFF.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-LINE           PIC X(20).
       01 WS-PAID           PIC S9(4)V99.
       01 WS-OWED           PIC S9(4)V99.
       01 WS-DIFF           PIC S9(4)V99.
       01 WS-DIFF-OUT       PIC -9(4).99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-LINE
           COMPUTE WS-PAID = FUNCTION NUMVAL(WS-LINE)
           ACCEPT WS-LINE
           COMPUTE WS-OWED = FUNCTION NUMVAL(WS-LINE)
           COMPUTE WS-DIFF = WS-PAID - WS-OWED
           MOVE WS-DIFF TO WS-DIFF-OUT
           DISPLAY "DIFF=" WS-DIFF-OUT
           STOP RUN.
"""

SIGNED_PYTHON = """from decimal import Decimal

def main(lines):
    diff = Decimal(lines[0]) - Decimal(lines[1])
    sign = "-" if diff < 0 else " "
    return [f"DIFF={sign}{abs(diff):07.2f}"]
"""


def test_infer_finds_signed_fields_with_negative_range():
    from app.infer import infer_inputs

    spec = infer_inputs(SIGNED_COBOL)
    assert [(f["name"], f["min"], f["max"]) for f in spec] == [("paid", "-999", "999"), ("owed", "-999", "999")]


def test_negative_values_are_formatted_as_plain_decimal_text():
    from app.seance import format_value

    assert format_value(-5, 2) == "-0.05"
    assert format_value(-1234, 2) == "-12.34"
    assert format_value(-7, 0) == "-7"
    assert format_value(1234, 2) == "12.34"


def test_signed_program_runs_a_clean_seance_with_negative_inputs():
    from app.infer import infer_inputs

    spec = infer_inputs(SIGNED_COBOL)
    result = run_seance(SIGNED_COBOL, SIGNED_PYTHON, spec, 80)
    assert result["verified"] is True


def test_unsigned_subtraction_sample_catches_a_signed_translation():
    cobol = (SAMPLES / "balance.cbl").read_text()
    naive = (SAMPLES / "balance.py").read_text().replace("abs(paid - owed)", "paid - owed")
    result = run_seance(cobol, naive, json.loads((SAMPLES / "balance.json").read_text())["inputs"], 100)
    assert result["verified"] is False
    assert result["minimal_spirit"] is not None
