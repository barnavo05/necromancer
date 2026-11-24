# Design: Seance proof of equivalence

## Overview

FastAPI backend, Hypothesis for input generation, GnuCOBOL (`cobc`) for the original program. The model is never involved in the seance, so the proof does not depend on an API key.

## Components

| File | Job |
|------|-----|
| `backend/app/cobol_runner.py` | Compiles COBOL with `cobc`, runs it on a batch of inputs, raises `CobolError` |
| `backend/app/python_runner.py` | Runs the Python translation on the same inputs with a time limit, raises `PythonError` |
| `backend/app/infer.py` | Reads the data division and proposes input fields and ranges |
| `backend/app/seance.py` | Builds cases with Hypothesis, compares outputs, shrinks failures, builds the certificate |
| `backend/app/mutate.py` | Haunt: injects bugs into the Python and runs the seance on each |
| `backend/app/autopsy.py` | Static list of gotchas per COBOL paragraph |
| `backend/app/main.py` | Endpoints: `/api/seance`, `/api/haunt`, `/api/infer-inputs`, `/api/autopsy`, `/api/samples` |

## Flow

1. The request carries a `sample_id`, or COBOL plus Python plus an input spec.
2. `boundary_literals` pulls constants out of the procedure division.
3. `generate_cases` makes inputs inside each range and adds the boundary values and one step either side.
4. COBOL is compiled once and run on every case. Python runs on the same cases.
5. Differences become restless spirits. `shrink_case` reduces a failure to the smallest failing input.
6. A Verified run returns counts, hashes and the `cobc` version for the certificate.

## Decisions

- Inputs are plain decimal text and programs use ACCEPT into text plus FUNCTION NUMVAL, because ACCEPT straight into a numeric field copies characters (19.99 into PIC 9(2)V99 becomes 19.90).
- Money is translated with Python `Decimal`. COMPUTE truncates (ROUND_DOWN), COMPUTE ROUNDED rounds half up (ROUND_HALF_UP).
- Requests are limited: COBOL 20,000 characters, Python 50,000, at most 8 inputs, at most 500 cases.
- The main seance is deterministic (Hypothesis derandomized), so the same program gives the same cases. The 500 extra stress inputs in Haunt are random on each run, so a borderline survivor can be caught on one run and survive on another.

## Testing

`backend/tests/test_seance.py` covers all four samples, boundary generation, shrinking, mutation catching, input inference, autopsy and the endpoints. CI runs it with GnuCOBOL on every push. The Kiro hook `.kiro/hooks/run-tests-on-save.kiro.hook` runs it when backend files or samples change.
