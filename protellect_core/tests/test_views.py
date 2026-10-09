import re
import pytest
import requests
from streamlit.testing.v1 import AppTest

import protellect_data as s
from protellect_core.tests.test_analysis import session

PDB = "\n".join(f"ATOM  {i:5d}  CA  ALA A{i:4d}      0.000   0.000   0.000  1.00 {85.0 if i % 5 else 45.0:5.2f}           C" for i in range(1, 394))


class R:
    def __init__(self, code, body): self.status_code, self._b = code, body
    def json(self): return self._b


@pytest.fixture(autouse=True)
def fake_net(monkeypatch):
    def fake_get(url, timeout=0, **k):
        if "pubchem" in url:
            return R(200, {"PropertyTable": {"Properties": [{"CID": 1, "MolecularWeight": "412.5", "XLogP": 3.1, "TPSA": 72.0, "HBondDonorCount": 2, "HBondAcceptorCount": 6, "RotatableBondCount": 5}]}})
        if "count=" in url:
            return R(200, {"results": [{"term": "NAUSEA", "count": 40}, {"term": "FATIGUE", "count": 22}]})
        return R(200, {"meta": {"results": {"total": 1234}}})
    monkeypatch.setattr(requests, "get", fake_get)


def app_for(view: str, gene="TP53", uid="P04637", extra=None):
    ss = session(gene, uid, pdb=PDB, **(extra or {}))
    def script():
        import streamlit as st
        from protellect_core.views.shell import build_analysis
        from protellect_core.views import overview, triage, hotspots, genetics, casestudy, experiments
        a = build_analysis(st.session_state, couplings=st.session_state.get("_couplings"))
        {"overview": lambda: overview.render_overview(a), "triage": lambda: triage.render_triage(a, {}), "hotspots": lambda: hotspots.render_hotspots(a),
         "genetics": lambda: genetics.render_genetics(a), "experiments": lambda: experiments.render_experiments(a, {}), "casestudy": lambda: casestudy.render_casestudy(a, {"chr": "17", "map": "17p13.1", "exons": 11})}[st.session_state["_view"]]()
    at = AppTest.from_function(script, default_timeout=120)
    for k, v in ss.items(): at.session_state[k] = v
    at.session_state["_view"] = view
    return at.run()


def text(at):
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


@pytest.mark.parametrize("view", ["overview", "triage", "hotspots", "genetics", "casestudy"])
def test_every_view_renders_without_error(view):
    at = app_for(view)
    assert not at.exception, [str(e.value)[:200] for e in at.exception]


def test_overview_content_is_evidence_backed():
    t = text(app_for("overview"))
    assert "Associated diseases" in t and "Li-Fraumeni" in t and "POSSIBILITY" in t
    at = app_for("overview")
    assert any("<svg" in m.value for m in at.markdown)                      # the animation
    pops = [p.proto.popover.label for p in at.get("popover")]
    assert pops and all("Proof and ML validation" in p for p in pops)       # every claim carries a proof popover


def test_overview_for_orphan_gpcr_shows_ranked_hypotheses_with_validation():
    at = app_for("overview", "GPR151", "Q8TDV0")
    assert not at.exception
    t = text(at)
    assert "What may happen" in t and "GPR151" in t and "ML validation:" in t
    assert "orphan" in t.lower()


def test_triage_drives_selection_and_shows_plan():
    at = app_for("triage")
    assert not at.exception
    sel = next(x for x in at.selectbox if x.key == "tri_variant_sel")
    first = sel.options[0]
    assert "pathogenic" in first
    assert at.session_state["sel_variant_name"]
    assert "How to work this variant" in " ".join(e.label for e in at.expander)
    sel.set_value(sel.options[3]).run()
    assert not at.exception


def test_hotspots_show_real_admet_and_faers_not_invented_numbers():
    at = app_for("hotspots")
    assert not at.exception
    t = text(at)
    assert "Pharmacokinetics and ADMET screen" in t and "FAERS" in t
    assert any("Rule of Five" in str(df.value.to_dict()) for df in at.dataframe)


def test_genetics_thresholds_cite_sources():
    at = app_for("genetics")
    assert not at.exception
    t = text(at)
    assert "Genetic thresholds" in t and "gnomAD" in t and "Variant cascade" in t


def test_case_study_maps_systems_with_rules_disclosed():
    at = app_for("casestudy")
    assert not at.exception
    assert "Cancer predisposition" in text(at) or any("Cancer predisposition" in str(d.value) for d in at.dataframe)
    assert "keyword" in text(at)


def test_context_changes_what_is_shown():
    plain = text(app_for("overview"))
    at = app_for("overview", extra={"ctx_disease": "hepatocellular carcinoma", "pt_meds": "nutlin-3", "ctx_factors": ["DNA damage"]})
    t = text(at)
    assert "Tailored to your microenvironment" in t and "Tailored to your microenvironment" not in plain
    # each context fact has ONE home tab: medications on Hotspots, factors on Genetics (not repeated on Overview)
    assert "nutlin-3" in text(app_for("hotspots", extra={"pt_meds": "nutlin-3"})).lower()
    assert "DNA damage" in text(app_for("genetics", extra={"ctx_factors": ["DNA damage"]}))


def test_data_audit_shows_fetch_errors_and_a_diagnostics_button(monkeypatch):
    import types, sys
    fake = types.ModuleType("protellect_data")
    fake.FETCH_ERRORS = {"DGIdb": "RuntimeError: DGIdb GraphQL: boom"}
    fake.source_diagnostics = lambda g, u: [{"source": "DGIdb (v5 GraphQL)", "ok": False, "http": 500, "ms": 12, "detail": "ERROR x"}]
    monkeypatch.setitem(sys.modules, "protellect_data", fake)
    for other in ("casestudy", "genetics", "hotspots", "triage", "experiments"):
        at_o = app_for(other)
        assert not at_o.exception, other
        assert "Data audit" not in text(at_o), f"data audit repeated on {other}"
    at = app_for("overview")
    assert not at.exception
    assert "Fetch problems" in text(at) or any("DGIdb" in str(d.value) for d in at.dataframe)
    btn = next(b for b in at.button if b.label == "Check data sources now")
    btn.click().run()
    assert not at.exception and any("DGIdb (v5 GraphQL)" in str(d.value) for d in at.dataframe)


def test_experiments_has_kinetics_calculator_and_viewer_has_motion():
    at = app_for("experiments")
    assert not at.exception
    ex = [e for e in at.expander if "kinetics calculator" in e.label.lower()]
    assert ex
    from protellect_core.viewer import structure_viewer_html
    from protellect_core.motion import normal_modes
    from protellect_core.tests.test_motion import helix_pdb
    p = helix_pdb(80)
    html = structure_viewer_html(p, [], 520, None, [], {}, {}, normal_modes(p))
    assert 'id="mot"' in html and "NOT an active state" in html
    assert "MOT=null" in structure_viewer_html(p, [], 520)   # no structure motion -> button hidden, no crash


def test_fit_table_parsing_and_panel_renders():
    import pandas as pd
    from protellect_core.views.fits import parse_dose_table, parse_spr_table, TEMPLATE_DOSE
    import io
    g = parse_dose_table(pd.read_csv(io.StringIO(TEMPLATE_DOSE)), "M")
    assert set(g) == {"alone", "co-expressed"} and len(g["alone"][0]) == 6
    g2 = parse_dose_table(pd.DataFrame({"Dose (nM)": [1, 10, 100, 0], "Signal": [1, 2, 3, 4]}), "nM")
    assert len(g2["all"][0]) == 3 and abs(g2["all"][0][0] - 1e-9) < 1e-15   # zero concentration dropped
    import pytest
    with pytest.raises(ValueError):
        parse_dose_table(pd.DataFrame({"a": [1], "b": [2]}), "M")
    with pytest.raises(ValueError):
        parse_spr_table(pd.DataFrame({"time": [1], "x": [1]}), "nM")
    at = app_for("experiments")
    assert not at.exception and any("Fit your own data" in e.label for e in at.expander)


def test_mouse_phenotypes_reach_the_genetics_tab_and_the_audit():
    at = app_for("genetics")
    assert "What knocking it out does in mice" in text(at)
    dfs = " ".join(str(d.value) for d in at.dataframe)
    assert "homeostasis/metabolism phenotype" in dfs and "abnormal glucose homeostasis" in dfs
    assert any("Mouse knockout" in str(d.value) for d in app_for("overview").dataframe)


def test_score_table_parsing_and_external_panel_renders():
    import pandas as pd, io
    from protellect_core.views.fits import parse_score_table, TEMPLATE_SCORES
    pos, neg, q = parse_score_table(pd.read_csv(io.StringIO(TEMPLATE_SCORES)))
    assert len(pos) == 2 and len(neg) == 2 and q == [("new_compound_A", -9.4)]
    with pytest.raises(ValueError):
        parse_score_table(pd.DataFrame({"a": [1]}))
    at = app_for("experiments")
    assert not at.exception and any("docking or structure-prediction" in e.label for e in at.expander)


def test_coupling_classifier_panel_declines_on_the_small_unverified_table(monkeypatch):
    import random
    from protellect_core.tests.test_coupling_ml import receptor
    from protellect_core.gpcrome import load_couplings
    rng = random.Random(2)
    data = {g: dict(zip(("seq", "tms"), receptor(rng, "Gi"))) for g in load_couplings()}
    monkeypatch.setattr(s, "fetch_gpcr_sequences", lambda *a, **k: data, raising=False)
    at = app_for("overview")
    assert not at.exception
    btn = next(b for b in at.button if b.label == "Fetch sequences and run the test")
    btn.click().run()
    assert not at.exception
    cap = text(at) + " ".join(w.value for w in at.warning)
    assert "No prediction is shown" in cap or "noise" in cap
    assert "predicted primary coupling" not in cap


def test_html_frame_falls_back_to_st_iframe_when_components_html_is_gone(monkeypatch):
    import streamlit as st
    import streamlit.components.v1 as comp
    from protellect_core.frame import html_frame
    calls = []
    monkeypatch.setattr(comp, "html", lambda *a, **k: (_ for _ in ()).throw(AttributeError("removed")))
    monkeypatch.setattr(st, "iframe", lambda src, **k: calls.append((src, k)), raising=False)
    html_frame("<html>x</html>", 0)
    assert calls and calls[0][0] == "<html>x</html>" and calls[0][1]["height"] >= 1
    monkeypatch.setattr(comp, "html", lambda m, **k: calls.append(("old", k)))
    html_frame("<p>y</p>", 200)
    assert calls[-1][0] == "old"


def test_triage_renders_when_components_html_is_removed(monkeypatch):
    import streamlit.components.v1 as comp
    monkeypatch.delattr(comp, "html")
    at = app_for("triage")
    assert not at.exception
