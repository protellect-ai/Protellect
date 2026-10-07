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


@pytest.mark.parametrize("status,needle", [(403, "rejected"), (401, "rejected"), (429, "rate limit"), (500, "error 500")])
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


def test_gemini_404_message_names_the_models_tried(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda url, **kw: Resp(404, text="nf"))
    monkeypatch.setattr(requests, "get", lambda url, **kw: Resp(200, {"models": []}))
    with pytest.raises(LLMError) as ei:
        gemini_llm(KEY)("p")
    assert "gemini-2.0-flash" in str(ei.value) and "PROTELLECT_GEMINI_MODEL" in str(ei.value) and KEY not in str(ei.value)


def test_gemini_falls_back_when_the_default_model_is_retired(monkeypatch):
    import requests
    seen = []

    def fake_post(url, **kw):
        seen.append(url.split("/models/")[1].split(":")[0])
        if "2.0-flash" in url:
            return Resp(404, text="retired")
        return Resp(200, {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
    monkeypatch.setattr(requests, "post", fake_post)
    call = gemini_llm(KEY)
    assert call("p") == "ok" and seen == ["gemini-2.0-flash", "gemini-2.5-flash"]
    seen.clear()
    assert call("p") == "ok" and seen == ["gemini-2.5-flash"]          # remembers the model that worked


def test_gemini_discovers_a_model_from_the_models_list(monkeypatch):
    import requests
    listing = {"models": [
        {"name": "models/gemini-9-flash-image", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-9-flash-preview", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-9-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-9-pro", "supportedGenerationMethods": ["generateContent"]}]}
    used = []

    def fake_post(url, **kw):
        m = url.split("/models/")[1].split(":")[0]
        used.append(m)
        return Resp(200, {"candidates": [{"content": {"parts": [{"text": "found"}]}}]}) if m == "gemini-9-flash" else Resp(404, text="nf")
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", lambda url, **kw: Resp(200, listing))
    assert gemini_llm(KEY)("p") == "found" and used[-1] == "gemini-9-flash"


def test_pinned_gemini_model_is_never_second_guessed(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda url, **kw: Resp(404, text="nf"))
    with pytest.raises(LLMError) as ei:
        gemini_llm(KEY, model="my-pinned-model")("p")
    assert "my-pinned-model" in str(ei.value)


def test_debate_note_shows_the_real_reason():
    def boom(_):
        raise LLMError("Gemini rate limit reached (429). Wait a moment.")
    hyp = {"statement": "s", "support": 0.4, "verdict": "weakened", "precedents": [], "evidence_axes": {}, "counterarguments": []}
    out = debate("G", hyp, {}, boom)
    assert "rate limit reached (429)" in out["note"] and out["final_verdict"] == "weakened"
