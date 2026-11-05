import re
import sys
import types
import xml.dom.minidom as md

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from protellect_core import example_case
from protellect_core.adapters import Partner, build_bundle
from protellect_core.candidates import MAXP, candidate_claims, rank
from protellect_core.engine import load_cases
from protellect_core.engine.benchmark import retrodict
from protellect_core.engine.io_parsers import parse_experiment, parse_matrix
from protellect_core.engine.registry import convert_iuphar_bytes, load_registry_text
from protellect_core.gpcrome import load_couplings
from protellect_core.network import bars_svg, interaction_svg, role_of
from protellect_core.tests.test_analysis import session
from protellect_core.topology import motifs, segment_of, segment_stats, topology
from protellect_core.viz import architecture_svg, communication_svg, gsea_svg, heatmap_svg, signalling_svg, topology_svg
from protellect_core.workbench import build

EX = example_case.EX


def ffar1(**kw):
    return build_bundle(session("FFAR1", "O14842", **kw))


@pytest.fixture(scope="module")
def wb():
    m = parse_matrix(EX / "gpcrome_matrix.csv")
    reg = load_registry_text((EX / "gpcrome_registry.csv").read_text())
    de = parse_experiment(pd.read_csv(EX / "gpcrome_differential.csv"))
    return build(m, reg, load_couplings(), "built-in seed table (unverified)", de_effect=de.set_index("gene")["effect"], de_sig=de.set_index("gene")["significance"], comparison="exhausted versus effector"), m


def ok_xml(s):
    md.parseString(s)
    return s


# ---------------------------------------------------------------- topology
def test_topology_is_built_from_the_real_annotation_and_motifs_from_the_real_sequence():
    b = ffar1()
    segs = topology(b)
    names = [s.name for s in segs]
    assert names[0] == "N-terminus" and names[-1] == "C-terminus" and [n for n in names if n.startswith("TM")] == [f"TM{i}" for i in range(1, 8)]
    assert [n for n in names if "L" in n and n[:3] in ("ICL", "ECL")] == ["ICL1", "ECL1", "ICL2", "ECL2", "ICL3", "ECL3"]
    assert sum(s.length for s in segs) == b.length                                           # the segments tile the whole sequence, no gaps
    assert segment_of(segs, 232) == "TM6" and segment_of(segs, 5) == "N-terminus"
    mm = {m["seq"]: m for m in motifs(b, segs)}
    assert set(mm) == {"DRY", "CWLP", "NPLVY"} and (mm["CWLP"]["start"], mm["CWLP"]["end"]) == (232, 235) and mm["CWLP"]["where"] == "TM6"
    assert topology(build_bundle(session())) is None                                         # TP53: no helices, so no GPCR topology is invented
    no_motif = ffar1(); no_motif.sequence = "A" * no_motif.length
    assert motifs(no_motif, topology(no_motif)) == []                                         # absent motifs are not reported


def test_segment_stats_count_variants_per_segment():
    b = ffar1()
    st = segment_stats(b, topology(b))
    assert sum(d["plp"] for d in st.values()) == len(b.plp) and sum(d["n"] for d in st.values()) <= len(b.variants)


# ---------------------------------------------------------------- the maps
def test_topology_map_labels_come_from_the_data():
    b = ffar1()
    segs = topology(b)
    sel = next(v for v in b.variants if v.is_plp and 220 <= (v.pos or 0) <= 243)
    s = ok_xml(topology_svg(b, segs, motifs(b, segs), segment_stats(b, segs), sel))
    for must in ("FFAR1", "TM1", "TM7", "ECL2", "ICL3", "20–42", "220–243", "N-terminus", "C-terminus", "112–114", "232–235", f"residue {sel.pos} · TM6"):
        assert must in s, must


def test_architecture_map_has_scale_domains_and_strips():
    b = ffar1(pdb="")
    s = ok_xml(architecture_svg(b))
    assert "residue-scaled map" in s and "AlphaMissense" in s and "AlphaFold pLDDT" in s and "no structure loaded" in s and "7TM domain" in s


# ---------------------------------------------------------------- the animation
def anim(b, **kw):
    segs = topology(b)
    return ok_xml(signalling_svg(b, segs, motifs(b, segs), segment_stats(b, segs), **kw))


def test_animation_for_a_characterised_receptor_never_claims_the_ligand_is_unknown():
    s = anim(ffar1(), coupling="Gq", coupling_source="curated seed table, unverified", status="characterised", ligand_lines=["Recorded drug-gene interactions: 1."])
    assert "not an orphan" in s and "ORPHAN (" not in s and "ligand: known" in s
    assert "the experiment must find" not in s and "ligand not identified" not in s
    assert "curated seed table, unverified" in s and "Phospholipase C-β" in s and "PLCB1–4" in s


def test_animation_for_an_orphan_states_every_unknown_and_proposes_the_first_experiment():
    s = anim(ffar1(), coupling="", status="orphan", hypothesis={"statement": "may bind a lipid-class ligand", "support": 0.41})
    assert "ORPHAN (no confirmed ligand" in s and "not established" in s and "ligand: unknown (orphan)" in s
    assert "G-protein panel" in s and "may bind a lipid-class ligand (support 0.41)" in s
    for cls in ("Gαs (GNAS)", "Gαi/o", "Gαq/11", "Gα12/13"):
        assert cls in s                                                                         # all four candidate branches are shown when coupling is unknown


@pytest.mark.parametrize("cls, needle", [("Gs", "ADCY1–9"), ("Gi", "KCNJ3"), ("Gq", "ITPR1–3"), ("G12", "ROCK1")])
def test_each_coupling_class_gets_its_own_effectors_and_assays(cls, needle):
    s = anim(ffar1(), coupling=cls, coupling_source="recorded in GPCRdb", status="characterised")
    assert needle in s and "recorded in GPCRdb" in s and "TRUPATH" in s and "PRESTO-Tango" in s


def test_animation_reads_the_selected_data_and_escapes_text():
    b = ffar1(); b.name = "<script>alert(1)</script> receptor"
    s = anim(b, coupling="Gq", status="characterised", context="a <b>tissue</b>", signal="log2FC +1.8")
    assert "<script>" not in s and "&lt;script&gt;" in s and "log2FC +1.8" in s


def test_animation_declares_all_five_steps_and_its_keyframes():
    s = anim(ffar1(), coupling="Gq", status="characterised")
    assert all(f"STEP {k}" in s for k in range(1, 6)) and all(k in s for k in ("@keyframes tm6", "@keyframes galpha", "@keyframes s34"))


# ---------------------------------------------------------------- the GPCRome visuals
def test_heatmap_communication_and_enrichment_plot_carry_the_data(wb):
    w, m = wb
    g = w.gpcrome.all_gpcr
    h = ok_xml(heatmap_svg(m, list(g["GPCR"]), dict(zip(g["GPCR"], g["Status"])), w.coupling, dict(zip(g["GPCR"], g["Specificity (tau)"]))))
    assert "GPR87" in h and "tau" in h and "CD8 T exhausted" in h and "orphan" in h
    c = ok_xml(communication_svg(w.axes, w.coupling))
    assert "CXCL12 → CXCR4" in c and "CAF fibroblast" in c and "paracrine" not in c and "secretion is not measured" in c
    e = ok_xml(gsea_svg(w.enrichment, "Gs"))
    assert "NES" in e and "FDR" in e and "ADORA2A" in e and "peak at rank" in e


def test_enrichment_plot_curve_ends_at_zero_and_peaks_at_the_enrichment_score(wb):
    w, _ = wb
    cv = w.enrichment.curves["Gs"]
    es = w.enrichment.table.set_index("Coupling class").loc["Gs", "ES"]
    assert abs(cv["run"][cv["peak"]] - es) < 1e-2 and abs(cv["run"][-1]) < 1e-6 and len(cv["run"]) == w.enrichment.n_ranked


# ---------------------------------------------------------------- network, bars
def test_network_roles_and_labels():
    reg = {"ADRB2": {"status": "characterized"}}
    assert [role_of(n, reg)[0] for n in ("GNAS", "GNB1", "ARRB2", "GRK2", "RGS2", "ADCY5", "ARHGEF1", "ADRB2", "TP53")] == \
        ["G protein alpha", "G protein beta/gamma", "Arrestin", "GRK kinase", "RGS regulator", "Effector enzyme / kinase", "Rho pathway", "GPCR", "other"]
    s = ok_xml(interaction_svg("FFAR1", [Partner("GNAS", .99, "https://x"), Partner("<b>x</b>", .5)], registry=reg))
    assert "G protein alpha" in s and "&lt;b&gt;x" in s and "0.99" in s
    assert "No interaction partners" in ok_xml(interaction_svg("X", []))


def test_bars_show_values_and_handle_negatives():
    s = ok_xml(bars_svg(["Gs", "Gi"], [1.73, -1.54], "NES", signed=True, fmt="{:+.2f}"))
    assert "+1.73" in s and "-1.54" in s and bars_svg([], [], "x") == ""


# ---------------------------------------------------------------- candidates
def test_candidate_scores_rank_the_planted_receptors_and_ignore_what_could_not_be_scored(wb):
    w, m = wb
    status = dict(zip(w.gpcrome.all_gpcr["GPCR"], w.gpcrome.all_gpcr["Status"]))
    df = rank(w, status, None, None, "up")
    top = list(df[df["Status"] == "characterised"].head(8)["GPCR"])
    assert {"ADORA2A", "PTGER4"} & set(top)                                              # Gs receptors on exhausted T cells lead the characterised list
    noise = df[df["GPCR"].isin(["GPR35", "GPR37", "GPR19", "GPR82"])]
    assert (noise["Score"] <= df["Score"].median()).all()
    row = df.iloc[0]
    assert not row["_avail"]["Altered in cancer"] and not row["_avail"]["Recorded drug"]  # no table and no lookup: left out of the denominator, not scored zero
    assert row["Score"] == round(100 * sum(row["_pts"][k] for k, v in row["_avail"].items() if v) / sum(MAXP[k] for k, v in row["_avail"].items() if v))
    alt = pd.DataFrame({"gene": ["GPR87"], "cancer": ["HNSC"], "mut": [0.0], "amp": [0.2], "del": [0.0]})
    with_alt = rank(w, status, alt, {"PTGER4": [{"drug": "x"}]}, "up")
    assert with_alt.set_index("GPCR").loc["GPR87", "_avail"]["Altered in cancer"] and "altered" in with_alt.set_index("GPCR").loc["GPR87", "Evidence"]


def test_direction_flips_the_ranking(wb):
    w, _ = wb
    status = dict(zip(w.gpcrome.all_gpcr["GPCR"], w.gpcrome.all_gpcr["Status"]))
    up = rank(w, status, None, None, "up").set_index("GPCR")["Score"]
    down = rank(w, status, None, None, "down").set_index("GPCR")["Score"]
    assert up["ADORA2A"] > down["ADORA2A"] and down["CXCR4"] >= up["CXCR4"] - 20


def test_candidate_claims_have_proof_and_disclose_the_weights(wb):
    w, _ = wb
    status = dict(zip(w.gpcrome.all_gpcr["GPCR"], w.gpcrome.all_gpcr["Status"]))
    from protellect_core.evidence import has_proof
    cl = candidate_claims(rank(w, status, None, None, "up"), w, "characterised", 4)
    assert cl and all(has_proof(c) for c in cl) and all(any(p.kind == "rule" and "design choices" in p.detail for p in c.proofs) for c in cl)


# ---------------------------------------------------------------- blind retrodiction
def test_retrodiction_hides_the_receptor_and_still_finds_its_ligand_class():
    r = retrodict(load_cases(), "FFAR1")
    assert r and r["truth"] == "fatty acid" and r["hit"] and r["ranked"][0][0] == "fatty acid" and r["library"] == len(load_cases()) - 2
    assert retrodict(load_cases(), "TP53") is None


def test_retrodiction_does_not_leak_the_held_out_case():
    cases = load_cases()
    only_self = [c for c in cases if c.gene == "FFAR1"]
    assert retrodict(only_self, "FFAR1") is None                                           # nothing left to learn from: refuses instead of predicting from itself


# ---------------------------------------------------------------- registry
def test_iuphar_file_layouts_and_aliases():
    rows = ['"GtoPdb Version: 2026.2","Release date: 2026-06-15"',
            '"Type","Family id","Family name","Target id","Target name","Subunits","Target systematic name","Target abbreviated name","Synonyms","HGNC id","HGNC symbol","HGNC name"',
            '"gpcr","1","Free fatty acid receptors","101","FFA1 receptor","","","FFA1","GPR40|free fatty acid receptor 1","4498","FFAR1","x"',
            '"gpcr","9","Class A Orphans","2","GPR87","","","GPR87","","4524","GPR87","y"', '"lgic","4","Nicotinic","5","x","","","","","1","CHRNA1","z"']
    reg = load_registry_text(convert_iuphar_bytes("\n".join(rows).encode()))
    assert reg["GPR87"]["status"] == "orphan" and reg["FFAR1"]["status"] == "characterized" and "CHRNA1" not in reg and "GPR40" in reg["FFAR1"]["aliases"]
    with pytest.raises(ValueError):
        convert_iuphar_bytes(b"a,b\n1,2")


# ---------------------------------------------------------------- in the app
def view_script():
    import streamlit as st
    from protellect_core.views.shell import build_analysis
    from protellect_core.views.overview import render_overview
    from protellect_core.views.common import registry_text
    a = build_analysis(st.session_state)
    st.session_state["_n_registry"] = len(a.engine.registry)
    render_overview(a)


def run(extra=None, fetch=None, monkeypatch=None):
    ss = session("FFAR1", "O14842", last="GPR-40", pdb="")
    ss.update(extra or {})
    at = AppTest.from_function(view_script, default_timeout=180)
    for k, v in ss.items():
        at.session_state[k] = v
    return at.run()


def txt(at):
    return re.sub(r"\s+", " ", (" ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption) + " " + " ".join(x.value for x in list(at.info) + list(at.success) + list(at.warning))).replace("**", ""))


def test_a_search_by_alias_says_so(monkeypatch):
    import protellect_core.views.common as common
    monkeypatch.setattr(common, "_fetch_iuphar", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    t = txt(run())
    assert "You searched GPR-40" in t and "recorded alias of FFAR1" in t and "official symbol is FFAR1" in t


def test_the_pattern_section_shows_the_blind_test_for_a_receptor_in_the_case_library(monkeypatch):
    import protellect_core.views.common as common
    monkeypatch.setattr(common, "_fetch_iuphar", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    t = txt(run())
    assert "Pattern-learned hypotheses" in t and "Blind test of the precedent model on FFAR1" in t and "documented ligand class" in t and "fatty acid" in t


def test_full_registry_loads_automatically_and_failure_falls_back_with_the_reason(monkeypatch):
    import protellect_core.views.common as common
    big = "gene,status,family,aliases,source,note\n" + "\n".join(f"G{i},{'orphan' if i % 9 == 0 else 'characterized'},fam,,iuphar-import,x" for i in range(396)) + "\nFFAR1,characterized,Free fatty acid receptors,GPR40,iuphar-import,x\n"
    monkeypatch.setattr(common, "_fetch_iuphar", lambda: big)
    at = run()
    assert at.session_state["_n_registry"] == 397 and "loaded automatically" in at.session_state["_registry_label"]
    monkeypatch.setattr(common, "_fetch_iuphar", lambda: (_ for _ in ()).throw(RuntimeError("HTTP 503")))
    at2 = run()
    assert at2.session_state["_n_registry"] < 30 and "seed" in at2.session_state["_registry_label"] and "HTTP 503" in at2.session_state["_registry_error"]
    assert "could not be loaded automatically" in " ".join(w.value for w in at2.warning) + txt(at2)
