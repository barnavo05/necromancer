# Tech stack

- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS
- Backend: Python 3.11, FastAPI
- COBOL runtime: GnuCOBOL (cobc) inside Docker
- Property-based testing: Hypothesis (Python)
- LLM: called from the backend only, never from the browser
- Deploy: Vercel (frontend), Render or Railway (backend with Docker)

Rules
- Keep sample COBOL programs small (under 200 lines) and stored in /samples
- Every backend endpoint has a test
- Never put API keys in code. Use environment variables and a .env.example file
- Prefer simple, readable code over clever code