# Necromancer

**Bring dead COBOL back to life, and prove it still behaves the same.**

Banks, insurers and governments still run on COBOL, and the people who understand it are retiring. Necromancer takes a legacy COBOL program and walks it through three steps.

| Step | What happens |
|---|---|
| 01 / 03 **Exhume** | Parses the COBOL and explains what it does in plain English |
| 02 / 03 **Resurrect** | Translates it into clean, modern Python |
| 03 / 03 **Seance** | Runs the original COBOL and the new Python on hundreds of random inputs and checks that the outputs match. Any mismatch shows up as a "restless spirit" you can inspect |

The seance is the point. A translation is never shown as correct unless it has been verified.

Built for **Kiroween 2026**, Resurrection category.

## Status

Early stage. The product, tech and design rules are written down in [`.kiro/steering`](.kiro/steering) and drive how the project is built with Kiro. Application code is not in this repo yet.

## Planned stack

- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS
- Backend: Python 3.11, FastAPI
- COBOL runtime: GnuCOBOL (`cobc`) inside Docker
- Equivalence checking: property-based testing with Hypothesis
- LLM calls happen on the backend only, never in the browser
- Deploy: Vercel for the frontend, Render or Railway for the Docker backend

## Ground rules

- Sample COBOL programs stay small (under 200 lines) and live in `/samples`
- Every backend endpoint has a test
- No API keys in code, only environment variables and a `.env.example`
- Simple, readable code over clever code

## Design

Off-white background, near-black text, one accent colour (phosphor green, `#2BD46B`) used sparingly. The only dark element is the green-screen terminal panel that shows the old COBOL. Calm, slow transitions, and spooky only through restraint.

## License

[MIT](LICENSE)
