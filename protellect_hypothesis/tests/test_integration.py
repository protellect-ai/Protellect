import io

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from protellect_hypothesis import patch_app
from protellect_hypothesis.app_integration import extra_annotations_from_app, uniprot_tissue_text

HOST = '''
import streamlit as st
class _SinkTab:
    def __enter__(self): return self
    def __exit__(self, *a): return False
ALL_TAB_NAMES = ["Summary","Triage","Case Study"]
_ob_selected_tabs = st.session_state.get("ob_tabs_selected") or ALL_TAB_NAMES
_visible_tab_names = [n for n in ALL_TAB_NAMES if n in _ob_selected_tabs] or ALL_TAB_NAMES

def _tab_visible(name):
    return name in _visible_tab_names

_visible_tab_objs = st.tabs(_visible_tab_names)
_tab_by_name = {n: _visible_tab_objs[i] for i, n in enumerate(_visible_tab_names)}
tab0 = _tab_by_name.get("Summary", _SinkTab())
tab1 = _tab_by_name.get("Triage", _SinkTab())
tab2 = _tab_by_name.get("Case Study", _SinkTab())
with tab0:
    st.write("summary")
'''


def test_patch_is_idempotent_and_reports_each_step():
    new, rep = patch_app.patch(HOST)
    assert [s for s, _ in rep] == ["add to ALL_TAB_NAMES", "force tab visible", "add tab block"]
    assert all(st == "applied" for _, st in rep)
    assert compile(new, "x", "exec")
    again, rep2 = patch_app.patch(new)
    assert again == new and rep2 == [("all steps", "already present")]


def test_patch_refuses_when_anchors_are_missing(tmp_path):
    p = tmp_path / "app.py"
    p.write_text("import streamlit as st\nst.write('hi')\n")
    assert patch_app.main([str(p)]) == 1
    assert p.read_text() == "import streamlit as st\nst.write('hi')\n"      # untouched
    assert not (tmp_path / "app.py.bak").exists()


def test_patch_cli_backup_and_undo(tmp_path):
    p = tmp_path / "app.py"
    p.write_text(HOST)
    assert patch_app.main([str(p), "--check"]) == 0 and p.read_text() == HOST
    assert patch_app.main([str(p)]) == 0
    assert "Hypotheses" in p.read_text() and (tmp_path / "app.py.bak").read_text() == HOST
    assert patch_app.main([str(p), "--undo"]) == 0 and p.read_text() == HOST


def _run_host(session=None):
    patched, _ = patch_app.patch(HOST)
    at = AppTest.from_string(patched, default_timeout=90)
    for k, v in (session or {}).items():
        at.session_state[k] = v
    return at.run()


def test_tab_appears_after_triage_even_if_user_onboarded_without_it():
    at = _run_host({"ob_tabs_selected": ["Summary", "Triage"]})
    assert not at.exception
    names = [t.label for t in at.tabs]
    assert names[:3] == ["Summary", "Triage", "Hypotheses"]


def test_tab_appended_when_triage_is_hidden():
    at = _run_host({"ob_tabs_selected": ["Summary"]})
    assert [t.label for t in at.tabs][:2] == ["Summary", "Hypotheses"]


def test_sidebar_csv_flows_into_the_hypotheses_tab():
    df = pd.DataFrame({"gene": ["GPR151", "GPR6", "TP53"], "log2FoldChange": [1.7, 1.2, 0.8], "padj": [0.004, 0.02, 0.03]})
    at = _run_host({"csv_df": df, "csv_filename": "my_rnaseq.csv"})
    assert not at.exception
    assert [(m.label, m.value) for m in at.metric] == [("Genes read", "3"), ("GPCRs found", "2"), ("Orphan GPCRs", "2")]
    assert any("my_rnaseq.csv" in c.value for c in at.caption)


def test_loaded_protein_runs_in_lookup_mode_with_uniprot_tissue():
    pdata = {"comments": [{"commentType": "TISSUE SPECIFICITY", "texts": [{"value": "Expressed in the habenula and brain."}]}]}
    at = _run_host({"gene": "GPR151", "pdata": pdata})
    assert not at.exception
    assert [m.value for m in at.metric][-1] == "1"                  # one orphan GPCR found
    assert any("Lookup mode for GPR151" in c.value for c in at.caption)
    assert any("no experimental signal" in c.value for c in at.caption)


def test_uniprot_tissue_helpers():
    pdata = {"comments": [{"commentType": "TISSUE SPECIFICITY", "texts": [{"value": "Pancreatic islets and colon."}]}]}
    assert uniprot_tissue_text(pdata).startswith("Pancreatic")
    assert extra_annotations_from_app("gpr40", pdata)["GPR40"]["tissues"] == ["pancreas", "gut"]
    assert extra_annotations_from_app("", pdata) == {} and extra_annotations_from_app("X", {}) == {}


def test_engine_failure_cannot_break_the_host_app(monkeypatch):
    patched, _ = patch_app.patch(HOST)
    broken = patched.replace("render_hypothesis_workspace()", "raise RuntimeError('boom')")
    at = AppTest.from_string(broken, default_timeout=60).run()
    assert not at.exception
    assert any("unavailable" in w.value and "boom" in w.value for w in at.warning)
    assert any("summary" in m.value for m in at.markdown)         # the rest of the app still rendered


def test_registry_import_via_uploaded_iuphar_bytes():
    from protellect_hypothesis.registry import convert_iuphar_bytes, load_registry_text
    data = b"Type,Family name,HGNC symbol\ngpcr,Class A Orphans,GPR151\ngpcr,Chemokine receptors,CCR5\n"
    reg = load_registry_text(convert_iuphar_bytes(data))
    assert reg["GPR151"]["status"] == "orphan" and reg["CCR5"]["status"] == "characterized"
    with pytest.raises(ValueError):
        convert_iuphar_bytes(b"a,b\n1,2\n")
