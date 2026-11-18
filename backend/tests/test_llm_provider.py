import httpx
import pytest

from app import llm


class _Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


def _clear(monkeypatch):
    for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)


def test_openai_compatible_provider_is_used_when_configured(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "free-model")
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, json=json)
        return _Resp(200, {"choices": [{"message": {"content": "hello"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert llm.complete("sys", "user") == "hello"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer k"
    assert seen["json"]["model"] == "free-model"
    assert seen["json"]["messages"][0] == {"role": "system", "content": "sys"}


def test_openai_compatible_errors_become_llm_unavailable(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(429, {}))
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("s", "u")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(200, {"oops": 1}))
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("s", "u")


def test_no_key_at_all_is_llm_unavailable(monkeypatch):
    _clear(monkeypatch)
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("s", "u")
