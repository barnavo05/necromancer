"""LLM access. Runs on the backend only, key comes from the environment."""
from __future__ import annotations

import json
import os
import re
import time

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


class LLMUnavailable(Exception):
    pass


RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_DELAYS = (2, 5, 10)


def _post(url: str, headers: dict, payload: dict, retry: bool = True):
    """POST with a few retries on temporary errors, which free tiers return often."""
    resp = None
    for delay in (*RETRY_DELAYS, None) if retry else (None,):
        resp = httpx.post(url, headers=headers, json=payload, timeout=90)
        if resp.status_code not in RETRY_STATUSES or delay is None:
            break
        time.sleep(delay)
    return resp


def _failure(resp) -> LLMUnavailable:
    detail = ""
    try:
        body = resp.json()
        err = body[0] if isinstance(body, list) and body else body
        detail = str((err.get("error") or {}).get("message") or "")[:160]
    except Exception:
        pass
    return LLMUnavailable(f"Model request failed ({resp.status_code}){': ' + detail if detail else ''}")


def _complete_openai_compatible(system: str, user: str, max_tokens: int) -> str:
    """Any OpenAI compatible chat endpoint, for example the free tiers of Gemini or Groq.

    LLM_MODEL may hold several model names separated by commas. They are tried in order,
    so a busy or retired model falls through to the next one.
    """
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    models = [m.strip() for m in os.environ.get("LLM_MODEL", "").split(",") if m.strip()] or [""]
    last: LLMUnavailable | None = None
    for model in models:
        resp = _post(
            f"{base}/chat/completions",
            {"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
            {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            retry=len(models) == 1,
        )
        if resp.status_code != 200:
            last = _failure(resp)
            continue
        try:
            return resp.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            last = LLMUnavailable("The model returned an unreadable reply")
            last.__cause__ = exc
    assert last is not None
    raise last


def complete(system: str, user: str, max_tokens: int = 4000) -> str:
    # Optional free provider: set LLM_API_KEY, LLM_BASE_URL and LLM_MODEL.
    if os.environ.get("LLM_API_KEY") and os.environ.get("LLM_BASE_URL"):
        return _complete_openai_compatible(system, user, max_tokens)
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMUnavailable("No model key is set on the server")
    resp = _post(
        API_URL,
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
        {
            "model": os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
    )
    if resp.status_code != 200:
        raise _failure(resp)
    return "".join(b.get("text", "") for b in resp.json().get("content", []))


EXHUME_SYSTEM = (
    "You explain legacy COBOL programs to engineers who have never seen COBOL. "
    "Reply with JSON only: {\"summary\": string, \"paragraphs\": [{\"name\": string, \"explanation\": string}]}. "
    "Plain English, no jargon, mention any silent truncation, overflow or rounding behaviour. "
    "One entry per paragraph (procedure section) in the order they appear."
)

RESURRECT_SYSTEM = (
    "Translate the COBOL program into Python 3.11. Output only Python code, no markdown fences. "
    "Define main(lines: list[str]) -> list[str]. lines are the stdin lines, plain decimal text; "
    "return the stdout lines exactly as the COBOL DISPLAY statements would print them, including "
    "zero padding of edited pictures. Use decimal.Decimal for every numeric value, never float. "
    "COBOL COMPUTE without ROUNDED truncates toward zero when stored, so use ROUND_DOWN quantize "
    "to the PIC scale. Add a comment on each block naming the COBOL paragraph it came from."
)


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:python|json)?\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def exhume(cobol: str) -> dict:
    raw = _strip_fences(complete(EXHUME_SYSTEM, cobol))
    try:
        data = json.loads(raw)
        return {"summary": str(data["summary"]), "paragraphs": list(data["paragraphs"])}
    except (ValueError, KeyError, TypeError) as exc:
        raise LLMUnavailable("The model returned an unreadable explanation") from exc


def resurrect(cobol: str) -> str:
    code = _strip_fences(complete(RESURRECT_SYSTEM, cobol, max_tokens=6000))
    if "def main" not in code:
        raise LLMUnavailable("The model did not return a main() function")
    return code


REPAIR_SYSTEM = (
    "You fix a Python translation of a COBOL program. You are given the COBOL, the current Python, "
    "and inputs where the two programs printed different output. Find the COBOL rule the Python "
    "missed (truncation versus ROUNDED, field overflow, loop counter wrap, unsigned fields, "
    "EVALUATE order) and fix it. Keep main(lines: list[str]) -> list[str] and keep using Decimal. "
    "Output only the full corrected Python code, no markdown fences, no explanation."
)


def repair(cobol: str, python: str, spirits: list[dict]) -> str:
    cases = "\n".join(
        f"inputs={s['inputs']} cobol_output={s['cobol']} python_output={s['python']} error={s['error']}"
        for s in spirits[:5]
    )
    prompt = f"COBOL:\n{cobol}\n\nCurrent Python:\n{python}\n\nMismatches:\n{cases}"
    code = _strip_fences(complete(REPAIR_SYSTEM, prompt, max_tokens=6000))
    if "def main" not in code:
        raise LLMUnavailable("The model did not return a main() function")
    return code
