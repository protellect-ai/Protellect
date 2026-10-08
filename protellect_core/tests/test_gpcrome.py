import json
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from protellect_core import example_case
from protellect_core.engine.io_parsers import InputError, parse_matrix
from protellect_core.engine.registry import load_registry_text
from protellect_core.gpcrome import _bh, analyse, check_truth, load_couplings, tau_index
from protellect_core.validation import validate

EX = example_case.EX


@pytest.fixture(scope="module")
def setup():
    m = parse_matrix(EX / "gpcrome_matrix.csv")
    reg = load_registry_text((EX / "gpcrome_registry.csv").read_text())
    return m, reg, load_couplings()


@pytest.fixture(scope="module")
def result(setup):
    return analyse(*setup)


def test_planted_answers_are_recovered_and_noise_gets_no_call(result):
    chk = check_truth(result, example_case.truth())
    assert len(chk) == 11 and all(c["ok"] for c in chk), [c for c in chk if not c["ok"]]


def test_self_test_beats_baseline_on_the_example(result):
    v = result.validation
    assert v["ok"] and v["beats_baseline"] and v["hits"] >= 30 and v["baseline"] < v["hits"]


def test_a_sabotaged_self_test_downgrades_every_prediction(setup):
    m, reg, coup = setup
    rng = np.random.default_rng(1)
    shuffled = dict(zip(coup, rng.permutation(list(coup.values()))))           # couplings no longer match the expression profiles
    res = analyse(m, reg, shuffled)
    assert res.validation["ok"] and not res.validation["beats_baseline"]
    calls = [c for c in res.claims if c.tags.get("call")]
    assert calls                                                                  # it still produces calls...
    for c in calls:
        assert any(x["check"] == "self_test_failed" and x["severity"] == "major" for x in c.counters)   # ...but each is flagged as unsupported


def test_single_context_flag_applies_to_exactly_the_confined_receptors(result):
    from protellect_core.adapters import Bundle
    tau = dict(zip(result.all_gpcr["GPCR"], result.all_gpcr["Specificity (tau)"]))
    calls = [c for c in result.claims if c.tags.get("call")]
    assert calls
    flagged = [c for c in calls if tau[c.tags["gene"]] >= 0.9]
    assert flagged, "the example should contain at least one confined receptor with a call"
    for c in calls:
        has = any(x["check"] == "single_context_driven" for x in c.counters)
        assert has == (tau[c.tags["gene"]] >= 0.9), (c.tags["gene"], tau[c.tags["gene"]])
    for c in flagged:
        validate(c, Bundle())
        assert c.verdict != "holds up"


def test_every_claim_has_proof_and_cites_a_method(result):
    for c in result.claims:
        assert c.proofs and c.kind in ("inference", "data") and (c.kind == "data" or c.basis)
        assert any("Guilt by association" in p.source or "Tau" in p.source for p in c.proofs)


def test_too_few_contexts_or_genes_is_refused_not_guessed(setup):
    m, reg, coup = setup
    res = analyse(m.iloc[:, :4], reg, coup)
    assert res.skipped and res.orphans.empty


def test_without_enough_known_receptors_the_self_test_says_so(setup):
    m, reg, coup = setup
    few = dict(list(coup.items())[:5])
    res = analyse(m, reg, few)
    assert not res.validation["ok"] and "at least 8" in res.validation["note"]


def test_bh_and_tau_basics():
    p = np.array([[0.001, 0.04], [0.5, 0.9]])
    q = _bh(p)
    assert q.shape == p.shape and (q >= p - 1e-12).all() and q.max() <= 1
    m = pd.DataFrame([[10, 0, 0, 0, 0], [5, 5, 5, 5, 5]], index=["spec", "flat"])
    t = tau_index(m)
    assert t["spec"] == pytest.approx(1.0) and t["flat"] == pytest.approx(0.0)


def test_matrix_parser_rejects_bad_input():
    with pytest.raises(InputError):
        parse_matrix(pd.DataFrame({"gene": ["a"], "c1": [1], "c2": [2]}))
    with pytest.raises(InputError):
        parse_matrix(pd.DataFrame({"gene": ["a"], **{f"c{i}": [-1.0] for i in range(6)}}))


# ---------------------------------------------------------------- in the app
def app_empty():
    def script():
        import streamlit as st
        from protellect_core.views.shell import build_analysis
        from protellect_core.views.overview import render_overview
        a = build_analysis(st.session_state)
        st.session_state["_pri"] = [p.headline for p in a.priorities]
        render_overview(a)
    return AppTest.from_function(script, default_timeout=180).run()


def text(at):
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption) + " " + " ".join(s.value for s in list(at.success) + list(at.warning) + list(at.error) + list(at.info))


def test_example_loads_through_the_ui_and_is_labelled_synthetic():
    at = app_empty()
    assert not at.exception and "Load the example case" in " ".join(b.label for b in at.button)
    next(b for b in at.button if b.key == "ex_load").click().run()
    assert not at.exception, [str(e.value)[:200] for e in at.exception]
    t = text(at)
    assert "Synthetic example loaded" in t and "GPCRome analysis" in t and "Self-test on your own data" in t
    assert "19 of 19 recovered" in " ".join(e.label for e in at.expander)
    pri = at.session_state["_pri"]
    assert pri[0].startswith("Gs-coupled receptors are enriched")             # the banner leads with the coupling-enrichment finding
    assert any(p.startswith("GPCRome:") for p in pri)                         # followed by the orphan-signalling summary
    assert at.session_state["ctx_disease_inp"] == "head and neck squamous cell carcinoma"


def test_example_feeds_the_hypothesis_engine_in_the_same_window():
    at = app_empty()
    next(b for b in at.button if b.key == "ex_load").click().run()
    t = text(at)
    assert "Orphan GPCRs found in your experiment" in t                         # the three-column table went through the hypothesis engine
    assert "What may happen" in t and "ML validation:" in t
    assert any("GPR87" in str(d.value) for d in at.dataframe)


def test_open_in_every_tab_uses_the_apps_own_search_hook():
    at = app_empty()
    next(b for b in at.button if b.key == "ex_load").click().run()
    next(x for x in at.selectbox if x.key == "cand_pick").set_value("GPR87").run()               # the default view is Candidates
    next(b for b in at.button if b.key == "cand_open").click().run()
    assert not at.exception and at.session_state["_pending_search_query"] == "GPR87"          # the key app.py pops to fill the search box and run the analysis
    at.session_state["_pending_search_query"] = ""
    next(r for r in at.radio if r.key == "gp_view").set_value("Signalling and specificity").run()
    next(x for x in at.selectbox if x.key == "gp_pick").set_value("GPR65").run()
    next(b for b in at.button if b.key == "gp_open").click().run()
    assert not at.exception and at.session_state["_pending_search_query"] == "GPR65"


def test_clearing_the_example_resets_everything():
    at = app_empty()
    next(b for b in at.button if b.key == "ex_load").click().run()
    next(b for b in at.button if b.key == "ex_clear").click().run()
    assert not at.exception and at.session_state["csv_df"] is None and not at.session_state["example_loaded"]
    assert at.session_state["ctx_disease_inp"] == ""
