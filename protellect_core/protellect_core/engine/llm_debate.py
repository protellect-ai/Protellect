"""Optional ML-validation cross-check (propose -> critique -> judge) with hard grounding rules.

Why it is built this way: an unconstrained LLM critic invents confident counter-arguments. Here the model
may ONLY cite evidence items we hand it (E1, E2, ...), which come from the deterministic critic and the
hypothesis itself. Code enforces three rules, regardless of what the model says:
  1. a reason with no valid citation is dropped;
  2. the final verdict can be kept or made MORE cautious, never made more confident than the deterministic one;
  3. anything the model wants checked that is not in the evidence is returned as an "open question", labeled
     unverified, never as a finding.
`llm` is any callable str -> str, so it is testable offline. `anthropic_llm` (Claude, paid) and `gemini_llm` (Google Gemini,
free tier may apply) are the live adapters. Neither was run against its real API in development (no keys in the build
environment); their request/response handling is tested with a fake HTTP layer, so try one real click first.
"""
from __future__ import annotations

import json
import os
import re
from typing import Callable, Dict, List, Optional

from .critic import VERDICT_ORDER

LLM = Callable[[str], str]


class LLMError(RuntimeError):
    pass


def anthropic_llm(api_key: Optional[str] = None, model: Optional[str] = None, max_tokens: int = 800) -> LLM:
    import requests
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("No ANTHROPIC_API_KEY available.")
    mdl = model or os.environ.get("PROTELLECT_MODEL", "claude-sonnet-4-20250514")

    def call(prompt: str) -> str:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=60,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": mdl, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})
        if r.status_code == 401:
            raise LLMError("Claude rejected the API key (401). Check ANTHROPIC_API_KEY in Streamlit secrets: it should start with sk-ant-, "
                           "with no extra spaces or quote marks, and must be active in the Anthropic Console.")
        if r.status_code == 429:
            raise LLMError("Claude rate limit or credit problem (429). Check your usage and credits in the Anthropic Console.")
        if r.status_code == 404:
            raise LLMError(f"Claude model '{mdl}' not found (404). Set PROTELLECT_MODEL to a model your account can use.")
        if r.status_code != 200:
            raise LLMError(f"Claude API error {r.status_code}: {r.text[:200]}")
        return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    return call


GEMINI_DEFAULTS = ("gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest")
_GEMINI_SKIP = ("image", "tts", "live", "audio", "embedding", "thinking", "lite", "vision")


def gemini_llm(api_key: Optional[str] = None, model: Optional[str] = None, max_tokens: int = 800) -> LLM:
    """Google Gemini adapter. Reads GEMINI_API_KEY or GOOGLE_API_KEY (same names the main Protellect app uses).

    The key is sent in a header, not in the URL, so it cannot leak through error messages or logs.
    If a model name has been retired (404), it tries fallbacks, then asks the API which models this key can
    use, and remembers whichever one works. Set PROTELLECT_GEMINI_MODEL to pin a model.
    """
    import requests
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise LLMError("No GEMINI_API_KEY or GOOGLE_API_KEY available.")
    pinned = model or os.environ.get("PROTELLECT_GEMINI_MODEL")
    base = "https://generativelanguage.googleapis.com/v1beta"
    headers = {"x-goog-api-key": key, "content-type": "application/json"}
    state = {"model": None}

    def _post(mdl: str, prompt: str):
        return requests.post(f"{base}/models/{mdl}:generateContent", timeout=60, headers=headers,
                             json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                                   "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2}})

    def _discover() -> List[str]:
        try:
            r = requests.get(f"{base}/models?pageSize=100", timeout=30, headers=headers)
            if r.status_code != 200:
                return []
            names = []
            for m in r.json().get("models", []):
                n = m.get("name", "").replace("models/", "")
                if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in n and not any(x in n for x in _GEMINI_SKIP):
                    names.append(n)
            return sorted(names, key=lambda n: ("preview" in n or "exp" in n, n))
        except Exception:
            return []

    def _text(r) -> str:
        cands = r.json().get("candidates") or []
        parts = ((cands[0].get("content") or {}).get("parts") or []) if cands else []
        out = "".join(p.get("text", "") for p in parts)
        if not out.strip():
            raise LLMError("Gemini returned an empty response.")
        return out

    def call(prompt: str) -> str:
        candidates = [pinned] if pinned else list(GEMINI_DEFAULTS)
        order = ([state["model"]] if state["model"] else []) + [m for m in candidates if m != state["model"]]
        tried, discovered = [], False
        i = 0
        while i < len(order):
            m = order[i]
            i += 1
            r = _post(m, prompt)
            if r.status_code == 404:
                tried.append(m)
                if i == len(order) and not discovered and not pinned:
                    discovered = True
                    order += [n for n in _discover() if n not in tried]
                continue
            if r.status_code in (401, 403):
                raise LLMError("Gemini rejected the key (401/403). Check the key in Streamlit secrets, and that the Generative Language API is enabled for it.")
            if r.status_code == 429:
                raise LLMError("Gemini rate limit reached (429). Wait a moment, or you may have hit the free-tier limit.")
            if r.status_code != 200:
                raise LLMError(f"Gemini API error {r.status_code}: {r.text[:200]}")
            state["model"] = m
            return _text(r)
        raise LLMError(f"Gemini model not found (404) for: {', '.join(tried)}. Set PROTELLECT_GEMINI_MODEL to a model your key can use.")
    return call


PROVIDERS = {
    "gemini": {"label": "Gemini (free tier may apply)", "keys": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "factory": gemini_llm},
    "claude": {"label": "Claude (paid API)", "keys": ("ANTHROPIC_API_KEY",), "factory": anthropic_llm},
}


def _env_getter(name: str) -> Optional[str]:
    return os.environ.get(name)


def find_key(provider: str, getter: Callable[[str], Optional[str]] = _env_getter) -> Optional[str]:
    for name in PROVIDERS[provider]["keys"]:
        v = getter(name)
        if v:
            return v
    return None


def available_providers(getter: Callable[[str], Optional[str]] = _env_getter) -> List[str]:
    return [p for p in PROVIDERS if find_key(p, getter)]


def fallback_llm(order: List[str], getter: Callable[[str], Optional[str]] = _env_getter) -> LLM:
    """Try providers in order; on an LLMError (bad key, rate limit, retired model...) move to the next.

    The returned callable has .used() (label of the provider that answered) and .failures (what failed first).
    """
    adapters: Dict[str, LLM] = {}
    state = {"used": None, "failures": []}

    def call(prompt: str) -> str:
        state["failures"] = []
        for p in order:
            try:
                if p not in adapters:
                    adapters[p] = make_llm(p, getter)
                out = adapters[p](prompt)
                state["used"] = PROVIDERS[p]["label"]
                return out
            except LLMError as e:
                state["failures"].append(f"{PROVIDERS[p]['label']}: {e}")
        raise LLMError(" | ".join(state["failures"]) or "No AI provider is configured.")
    call.used = lambda: state["used"]            # type: ignore[attr-defined]
    call.failures = lambda: list(state["failures"])   # type: ignore[attr-defined]
    return call


def make_llm(provider: str, getter: Callable[[str], Optional[str]] = _env_getter) -> LLM:
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown provider {provider!r}.")
    key = find_key(provider, getter)
    if not key:
        raise LLMError("No key found. Add " + " or ".join(PROVIDERS[provider]["keys"]) + " to Streamlit secrets.")
    return PROVIDERS[provider]["factory"](key)


def build_evidence(gene: str, hyp: dict, context: dict) -> List[dict]:
    ev = [{"id": "E1", "text": f"Hypothesis for {gene}: {hyp['statement']} (relative support {hyp['support']}; a ranking, not a probability)."}]
    for p in hyp.get("precedents", []):
        ev.append({"id": f"E{len(ev)+1}", "text": f"Precedent {p['gene']} (similarity {p['similarity']}): ligand {p['ligand']}; later outcome: {p['later_outcome']}."})
    for pr in hyp.get("proofs", []):
        ev.append({"id": f"E{len(ev)+1}", "text": f"Proof: {pr}"})
    for k, v in hyp.get("evidence_axes", {}).items():
        ev.append({"id": f"E{len(ev)+1}", "text": f"{k.replace('_', ' ')}: {v}"})
    for c in hyp.get("counterarguments", []):
        ev.append({"id": f"E{len(ev)+1}", "text": f"[{c['severity']}] {c['text']}"})
    if context.get("disease") or context.get("tissue"):
        ev.append({"id": f"E{len(ev)+1}", "text": f"Experiment context: disease={context.get('disease','')}, tissue={context.get('tissue','')}."})
    return ev


PROMPT = """You are a skeptical reviewer of a computational hypothesis about an orphan GPCR.
Use ONLY the numbered evidence below. Do not use outside knowledge as fact.

EVIDENCE:
{evidence}

Task: give the strongest counter-arguments against the hypothesis, then say whether it still stands.
Reply with JSON only:
{{"verdict": "holds up" | "weakened" | "contested",
  "reasons": [{{"text": "...", "cites": ["E2", "E5"]}}],
  "open_questions": ["things a researcher should look up that the evidence does not cover"]}}
Every reason MUST cite at least one evidence id. Maximum 4 reasons."""


def _parse(txt: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def debate(gene: str, hyp: dict, context: dict, llm: LLM) -> Dict:
    evidence = build_evidence(gene, hyp, context)
    valid = {e["id"] for e in evidence}
    det_verdict = hyp.get("verdict", "holds up")
    if det_verdict not in VERDICT_ORDER:
        det_verdict = "holds up"
    base = {"deterministic_verdict": det_verdict, "final_verdict": det_verdict, "reasons": [], "open_questions": [], "dropped": 0, "note": ""}
    try:
        raw = llm(PROMPT.format(evidence="\n".join(f"{e['id']}: {e['text']}" for e in evidence)))
    except Exception as ex:  # network, key, quota: fail safe to the deterministic verdict
        # LLMError messages are written to be user-readable and never contain keys (keys travel in headers).
        reason = str(ex) if isinstance(ex, LLMError) else f"{type(ex).__name__}: {str(ex)[:200]}"
        base["note"] = f"ML validation cross-check unavailable: {reason} Showing the evidence-rule validation only."
        return base
    parsed = _parse(raw)
    if not parsed:
        base["note"] = "AI reply could not be parsed; showing the deterministic critic only."
        return base
    reasons = []
    for r in parsed.get("reasons", [])[:4]:
        cites = [c for c in r.get("cites", []) if c in valid]
        if cites and str(r.get("text", "")).strip():
            reasons.append({"text": str(r["text"]).strip(), "cites": cites})
        else:
            base["dropped"] += 1
    llm_verdict = parsed.get("verdict", det_verdict)
    if llm_verdict not in VERDICT_ORDER:
        llm_verdict = det_verdict
    base["final_verdict"] = max(det_verdict, llm_verdict, key=lambda v: VERDICT_ORDER[v])   # never more confident
    base["reasons"] = reasons
    base["open_questions"] = [str(q) for q in parsed.get("open_questions", [])[:4]]
    if llm_verdict != base["final_verdict"]:
        base["note"] = "The AI judged this more favorably than the deterministic critic; the cautious verdict was kept."
    return base
