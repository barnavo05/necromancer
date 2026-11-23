# Design: Exhume, Resurrect and Exorcise

## Overview

`backend/app/llm.py` is the only file that talks to a model. It speaks the OpenAI compatible chat format, so any provider with that API works. The live deployment uses the Gemini free tier through its OpenAI compatible endpoint.

## Components

| Function | Job |
|----------|-----|
| `complete(system, user, max_tokens)` | Tries each model in `LLM_MODEL` in order and retries temporary errors |
| `exhume(cobol)` | Returns a plain English explanation by paragraph |
| `resurrect(cobol)` | Returns Python, with code fences stripped |
| `repair(cobol, python, spirits)` | Returns a fixed Python program given the failing cases |
| `LLMUnavailable` | Raised when no model could answer, mapped to HTTP 503 |

Endpoints in `backend/app/main.py`: `/api/exhume`, `/api/resurrect`, `/api/exorcise`.

## Exorcise flow

1. Run the seance on the current Python.
2. If Verified or out of rounds, return the result and the list of rounds.
3. Otherwise call `repair` with the restless spirits and loop.

The seance runs after every repair, so a repaired program is only reported as Verified if it passes.

## Configuration

Environment variables: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (comma separated list). No key in code. The browser never sees the key and never calls the model.

## Decisions

- Bundled samples carry their own explanation and translation so the demo works with no key and no network.
- Model names change. A list with fallbacks means a retired model (gemini-2.5-flash returned 404 on 18 Nov) does not break the app, and the list can be edited on Render without a deploy.

## Testing

`backend/tests/test_llm_provider.py` covers model fallback, retry and error mapping with a mock provider. `backend/tests/test_seance.py` covers the Exorcise loop with a mock model. A real model run was verified on the live site on 18 Nov: Exorcise repaired an injected rounding bug in 2 rounds (152 of 200, then 200 of 200).
