"""LLM access. Runs on the backend only, key comes from the environment."""
from __future__ import annotations

import json
import os
import re

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


class LLMUnavailable(Exception):
    pass


def complete(system: str, user: str, max_tokens: int = 4000) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMUnavailable("No ANTHROPIC_API_KEY is set on the server")
    resp = httpx.post(
        API_URL,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        json={
            "model": os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise LLMUnavailable(f"Model request failed ({resp.status_code})")
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
