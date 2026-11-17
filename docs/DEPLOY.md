# Deploy

Two pieces: the backend (Docker, needs GnuCOBOL) and the frontend (Vercel).

## 1. Backend on Render

1. In Render, choose New, then Blueprint, and pick this repo. It reads `render.yaml`.
2. Set `ANTHROPIC_API_KEY` (only needed for your own COBOL, the bundled samples work without it).
3. Set `CORS_ORIGINS` to your frontend URL once you have it (step 2).
4. Wait for the deploy, then open `https://<your-service>.onrender.com/api/health`. It should say `{"status":"alive"}`.

The free plan sleeps when idle, so the first request after a pause is slow. Open the site a minute before you record the demo.

Railway also works: create a service from the repo, set the Dockerfile path to `backend/Dockerfile`, and keep the build context at the repo root.

## 2. Frontend on Vercel

1. Import the repo, set the **Root Directory** to `frontend`.
2. Add the environment variable `NEXT_PUBLIC_API_URL` set to your Render URL (no trailing slash).
3. Deploy, then put the Vercel URL into `CORS_ORIGINS` on the backend and redeploy it.

## Checklist before you record

- Health URL answers
- Open the site, run the seance on all three samples, then Introduce a bug and run it again
- Browser console is clean
