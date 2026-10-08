import json

import pandas as pd
import pytest

from protellect_core.engine import HypothesisEngine, load_cases, parse_experiment
from protellect_core.engine.benchmark import evaluate_critic
from protellect_core.engine.critic import penalty, verdict_from
from protellect_core.engine.llm_debate import LLMError, anthropic_llm, debate


def _mk(sev, check="x"):
    return {"check": check, "severity": sev, "text": "t", "evidence": "e"}


def test_verdict_rules():
    assert verdict_from([]) == "holds up"
    assert verdict_from([_mk("minor")]) == "holds up"
    assert verdict_from([_mk("minor"), _mk("minor")]) == "weakened"
    assert verdict_from([_mk("major")]) == "weakened"
    assert verdict_from([_mk("major"), _mk("major")]) == "contested"
    assert verdict_from([_mk("major", "known_pairing_problem")]) == "contested"
    assert penalty([_mk("major"), _mk("minor")]) == pytest.approx(0.75 * 0.9)


def _run_gpr151():
    eng = HypothesisEngine()
    df = parse_experiment(pd.DataFrame({"gene": ["GPR151"], "log2fc": [1.7], "padj": [0.004]}))
    return eng.run(df, {"disease": "colitis", "tissue": "colon"}).results[0]


def test_refuted_galanin_pairing_is_flagged_for_gpr151():
    r = _run_gpr151()
    peptide = next(h for h in r.hypotheses if h.category == "ligand-class" and h.value == "peptide")
    assert peptide.verdict == "contested"
    assert any(c["check"] == "known_pairing_problem" and c["severity"] == "major" for c in peptide.counterarguments)


def test_every_hypothesis_is_critiqued_and_has_adjusted_support():
    r = _run_gpr151()
    for h in r.hypotheses:
        assert h.verdict in ("holds up", "weakened", "contested")
        assert 0.0 <= h.adjusted_support <= h.support + 1e-9


def _hyp(verdict="holds up"):
    return {"statement": "Likely activated by a peptide-class ligand", "support": 0.4, "verdict": verdict,
            "precedents": [{"gene": "GHSR", "similarity": 0.5, "ligand": "ghrelin", "later_outcome": "x"}],
            "evidence_axes": {"signal_character": "fold-change"},
            "counterarguments": [{"severity": "minor", "text": "tissue only", "evidence": "e"}]}


def test_debate_drops_uncited_reasons_and_cannot_upgrade():
    def llm(_):
        return json.dumps({"verdict": "holds up",
                           "reasons": [{"text": "valid", "cites": ["E2"]},
                                       {"text": "invented", "cites": ["E99"]},
                                       {"text": "no cite", "cites": []}],
                           "open_questions": ["check PubMed for replication"]})
    out = debate("GPR151", _hyp("contested"), {}, llm)
    assert [r["text"] for r in out["reasons"]] == ["valid"]
    assert out["dropped"] == 2
    assert out["final_verdict"] == "contested"          # model said 'holds up'; cautious verdict kept
    assert out["note"] and out["open_questions"] == ["check PubMed for replication"]


def test_debate_can_make_verdict_more_cautious():
    llm = lambda _: json.dumps({"verdict": "weakened", "reasons": [{"text": "r", "cites": ["E1"]}], "open_questions": []})
    assert debate("G", _hyp("holds up"), {}, llm)["final_verdict"] == "weakened"


def test_debate_fails_safe():
    assert "unavailable" in debate("G", _hyp(), {}, lambda _: (_ for _ in ()).throw(RuntimeError("boom")))["note"]
    out = debate("G", _hyp("weakened"), {}, lambda _: "not json at all")
    assert out["final_verdict"] == "weakened" and "parsed" in out["note"]


def test_anthropic_adapter_needs_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMError):
        anthropic_llm()


def test_critic_benchmark_runs_and_is_consistent():
    res = evaluate_critic(load_cases())
    assert res["n"] == 13
    assert sum(d["n"] for d in res["by_verdict"].values()) == res["n"]
