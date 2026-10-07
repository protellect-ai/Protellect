import json

import pytest

import protellect_hypothesis.llm_debate as L
from protellect_hypothesis.llm_debate import (LLMError, available_providers, debate, find_key, gemini_llm, make_llm)

KEY = "AIza-SECRET-KEY-123"


class Resp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body, self.text = status, body or {}, text

    def json(self):
        return self._body


def _patch(monkeypatch, resp, captured):
    import requests

    def fake_post(url, **kw):
        captured.update(url=url, **kw)
        return resp
    monkeypatch.setattr(requests, "post", fake_post)


def test_gemini_request_shape_and_key_stays_out_of_the_url(monkeypatch):
    cap = {}
    body = {"candidates": [{"content": {"parts": [{"text": "hello "}, {"text": "world"}]}}]}
    _patch(monkeypatch, Resp(200, body), cap)
    out = gemini_llm(KEY, model="gemini-test")("prompt text")
    assert out == "hello world"
    assert cap["url"].endswith("/models/gemini-test:generateContent") and KEY not in cap["url"]
    assert cap["headers"]["x-goog-api-key"] == KEY
    assert cap["json"]["contents"][0]["parts"][0]["text"] == "prompt text"


@pytest.mark.parametrize("status,needle", [(403, "rejected"), (401, "rejected"), (429, "rate limit"), (404, "not found"), (500, "error 500")])
def test_gemini_errors_are_clear_and_never_leak_the_key(monkeypatch, status, needle):
    _patch(monkeypatch, Resp(status, text="server said no"), {})
    with pytest.raises(LLMError) as ei:
        gemini_llm(KEY)("p")
    assert needle in str(ei.value) and KEY not in str(ei.value)


def test_gemini_empty_response_is_an_error(monkeypatch):
    _patch(monkeypatch, Resp(200, {"candidates": []}), {})
    with pytest.raises(LLMError):
        gemini_llm(KEY)("p")


def test_key_lookup_and_provider_availability():
    env = {"GOOGLE_API_KEY": "g"}
    assert find_key("gemini", env.get) == "g"
    assert find_key("claude", env.get) is None
    assert available_providers(env.get) == ["gemini"]
    assert available_providers({"GEMINI_API_KEY": "a", "ANTHROPIC_API_KEY": "b"}.get) == ["gemini", "claude"]
    assert available_providers({}.get) == []


def test_make_llm_errors_without_key_or_with_unknown_provider():
    with pytest.raises(LLMError):
        make_llm("gemini", {}.get)
    with pytest.raises(LLMError):
        make_llm("nope", {}.get)


def test_debate_end_to_end_through_the_gemini_adapter(monkeypatch):
    reply = json.dumps({"verdict": "weakened", "reasons": [{"text": "tissue only", "cites": ["E1"]}], "open_questions": []})
    _patch(monkeypatch, Resp(200, {"candidates": [{"content": {"parts": [{"text": reply}]}}]}), {})
    hyp = {"statement": "s", "support": 0.4, "verdict": "holds up", "precedents": [], "evidence_axes": {}, "counterarguments": []}
    out = debate("GPR151", hyp, {}, make_llm("gemini", {"GEMINI_API_KEY": KEY}.get))
    assert out["final_verdict"] == "weakened" and out["reasons"][0]["cites"] == ["E1"]
