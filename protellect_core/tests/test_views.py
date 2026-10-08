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
        from protellect_core.views import overview, triage, hotspots, genetics, casestudy
        a = build_analysis(st.session_state, couplings=st.session_state.get("_couplings"))
        {"overview": lambda: overview.render_overview(a), "triage": lambda: triage.render_triage(a, {}), "hotspots": lambda: hotspots.render_hotspots(a),
         "genetics": lambda: genetics.render_genetics(a), "casestudy": lambda: casestudy.render_casestudy(a, {"chr": "17", "map": "17p13.1", "exons": 11})}[st.session_state["_view"]]()
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
    assert "Relevance to your setup" in t and "Tailored to your microenvironment" in t and "Relevance to your setup" not in plain
    assert "nutlin-3" in t.lower() and "DNA damage" in t


def test_data_audit_shows_fetch_errors_and_a_diagnostics_button(monkeypatch):
    import types, sys
    fake = types.ModuleType("protellect_data")
    fake.FETCH_ERRORS = {"DGIdb": "RuntimeError: DGIdb GraphQL: boom"}
    fake.source_diagnostics = lambda g, u: [{"source": "DGIdb (v5 GraphQL)", "ok": False, "http": 500, "ms": 12, "detail": "ERROR x"}]
    monkeypatch.setitem(sys.modules, "protellect_data", fake)
    at = app_for("casestudy")
    assert not at.exception
    assert "Fetch problems" in text(at) or any("DGIdb" in str(d.value) for d in at.dataframe)
    btn = next(b for b in at.button if b.label == "Check data sources now")
    btn.click().run()
    assert not at.exception and any("DGIdb (v5 GraphQL)" in str(d.value) for d in at.dataframe)
