# Necromancer

**Bring dead COBOL back to life, and prove it still behaves the same.**

Banks, insurers and governments still run on COBOL, and the people who understand it are retiring. Necromancer takes a legacy COBOL program and walks it through three steps.

| Step | What happens |
|---|---|
| 01 / 03 **Exhume** | Reads the COBOL and explains what it does in plain English, paragraph by paragraph |
| 02 / 03 **Resurrect** | Translates it into clean, modern Python (Decimal for money, never float) |
| 03 / 03 **Seance** | Runs the original COBOL and the new Python on hundreds of generated inputs and checks that every output matches. Any mismatch shows up as a "restless spirit" you can inspect |

The seance is the point. A translation is never shown as correct unless it has been verified.

Built for **Kiroween 2026**, Resurrection category, with Kiro.

## Run it

You need Python 3.11+, Node 20+ and GnuCOBOL (`cobc`). The backend Docker image installs GnuCOBOL for you.

```bash
# backend
cd backend
pip install -r requirements.txt
python3 -m pytest -q
python3 -m uvicorn app.main:app --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The three bundled samples work without any API key, because their explanations and translations are bundled and the seance runs for real.

To use **Your own program**, paste COBOL that reads each input with `ACCEPT` into a text field followed by `FUNCTION NUMVAL`, click Find inputs, and adjust the ranges. You can write the Python yourself and run the seance with no key. To have Necromancer explain and translate it for you, set `ANTHROPIC_API_KEY` in the backend environment (see `.env.example`). The key is only ever used on the server.

Docker, from the repo root:

```bash
docker build -f backend/Dockerfile -t necromancer-api .
docker run -p 8000:8000 necromancer-api
```

## Samples

| Sample | What it shows |
|---|---|
| `interest` | Compound interest, cents cut off every year |
| `payroll` | Overtime at 1.5x, tax on the part above 500.00 |
| `loan` | Month by month repayment loop with a 360 month cap |

Each sample has a `.cbl` program, a `.json` file (summary, paragraph explanations, input ranges) and a `.py` translation. All three are verified by the seance in the test suite.

## What the seance caught

Three real COBOL traps showed up while building this, and the seance is what exposed them.

1. **COBOL truncates, Python rounds.** `COMPUTE` without `ROUNDED` cuts extra decimals off when it stores a result. A natural Python translation rounds instead, and the totals drift by cents. Translations must quantize with `ROUND_DOWN`.
2. **`ACCEPT` into a numeric field copies characters.** `19.99` read into `PIC 9(2)V99` silently becomes `19.90`. Programs here read each line as text and convert it with `FUNCTION NUMVAL`.

3. **Loop counters wrap.** A `PIC 9(2)` counter that must reach 99 wraps to 00, so the loop never ends. The seance reports a hang or crash in the old program as a restless spirit instead of stopping, and input ranges leave one digit of headroom.

## The I/O contract

- Input: one value per line on stdin, as plain decimal text such as `35.79`
- Output: lines on stdout from `DISPLAY`, exactly as the program prints them
- Python translations define `main(lines: list[str]) -> list[str]` with the same input and output
- Each sample declares safe input ranges, because COBOL silently overflows and a seance should test behaviour, not overflow luck

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness |
| `GET /api/samples`, `GET /api/samples/{id}` | Bundled programs |
| `POST /api/infer-inputs` | Detect a program's inputs (ACCEPT plus NUMVAL) and safe default ranges |
| `POST /api/exhume` | Plain English explanation (bundled sample or custom COBOL via the model) |
| `POST /api/resurrect` | Python translation (bundled sample or custom COBOL via the model) |
| `POST /api/seance` | Run COBOL and Python on generated inputs, return matches and restless spirits |

## Stack

- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS
- Backend: Python, FastAPI
- COBOL runtime: GnuCOBOL (`cobc`)
- Equivalence checking: property based testing with Hypothesis
- LLM calls happen on the backend only, never in the browser

## How Kiro is used

- **Steering** in [`.kiro/steering`](.kiro/steering) holds the product, tech and design rules that every change follows
- **Agent hook** in [`.kiro/hooks`](.kiro/hooks) runs the test suite whenever backend code or a COBOL sample changes
- **Specs** drive the build from requirements to design to tasks

## Ground rules

- Sample COBOL programs stay small (under 200 lines) and live in `/samples`
- Every backend endpoint has a test
- No API keys in code, only environment variables and a `.env.example`
- Simple, readable code over clever code

## Design

Off-white background, near-black text, one accent colour (phosphor green, `#2BD46B`) used sparingly. The only dark element is the green-screen terminal panel that shows the old COBOL. Calm, slow transitions, and spooky only through restraint.

## License

[MIT](LICENSE)
