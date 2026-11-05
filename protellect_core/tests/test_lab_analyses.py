import sys
import types

import numpy as np
import pandas as pd
import pytest

from protellect_core import example_case
from protellect_core.alterations import label, parse_alterations
from protellect_core.engine.io_parsers import parse_experiment, parse_matrix
from protellect_core.engine.registry import load_registry_text
from protellect_core.enrichment import gsea_preranked, enrichment_claims, parse_coupling_table, norm_coupling
from protellect_core.gpcrome import check_truth, load_couplings
from protellect_core.methods import methods_markdown
from protellect_core.oncocrine import axes
from protellect_core.programs import PROGRAMS, associate
from protellect_core.repurpose import action_of, table as repurpose_table
from protellect_core.workbench import build, matrix_ranking
from protellect_core.tests.test_gpcrome import app_empty, text

EX = example_case.EX


@pytest.fixture(scope="module")
def ex():
    m = parse_matrix(EX / "gpcrome_matrix.csv")
    reg = load_registry_text((EX / "gpcrome_registry.csv").read_text())
    de = parse_experiment(pd.read_csv(EX / "gpcrome_differential.csv"))
    return m, reg, de.set_index("gene")["effect"], de.set_index("gene")["significance"]


@pytest.fixture(scope="module")
def wb(ex):
    m, reg, eff, sig = ex
    return build(m, reg, load_couplings(), "built-in seed table (unverified)", de_effect=eff, de_sig=sig, comparison="exhausted versus effector CD8 T cells")


def test_all_planted_answers_are_recovered_across_every_analysis(wb):
    import json
    chk = check_truth(wb.gpcrome, json.loads((EX / "truth.json").read_text()), wb)
    assert len(chk) == 19 and all(c["ok"] for c in chk), [c for c in chk if not c["ok"]]


# ---------------------------------------------------------------- coupling enrichment
def test_enrichment_finds_planted_signal_and_nothing_in_shuffled_data():
    coup = load_couplings()
    rng = np.random.default_rng(1)
    genes = list(coup)
    sc = pd.Series({g: (rng.normal(1.2, .4) if coup[g] == "Gs" else rng.normal(-.8, .4) if coup[g] == "Gi" else rng.normal(0, .5)) for g in genes})
    t = gsea_preranked(sc, coup, "t").table.set_index("Coupling class")
    assert t.loc["Gs", "Significant"] == "yes" and t.loc["Gs", "NES"] > 0 and t.loc["Gi", "NES"] < 0 and t.loc["Gq", "Significant"] == "no"
    false_pos = 0
    for seed in range(8):                                  # repeated shuffles: false positives must stay rare
        sh = pd.Series(np.random.default_rng(seed).permutation(sc.to_numpy()), index=sc.index)
        false_pos += int((gsea_preranked(sh, coup, "t", n_perm=1000).table["Significant"] == "yes").sum())
    assert false_pos <= 2                                  # 8 shuffles x 3 classes = 24 tests at FDR 0.10


def test_enrichment_refuses_tiny_inputs_and_explains():
    r = gsea_preranked(pd.Series({"A": 1.0, "B": 2.0}), {"A": "Gs"}, "t")
    assert r.table.empty and "at least 20" in r.note


def test_enrichment_claims_disclose_an_unverified_coupling_table(ex):
    m, reg, eff, sig = ex
    seed = build(m, reg, load_couplings(), "built-in seed table (unverified)", de_effect=eff, de_sig=sig)
    better = build(m, reg, load_couplings(), "IUPHAR 2025 primary coupling", de_effect=eff, de_sig=sig)
    assert seed.enrich_claims and all(any(x["check"] == "unverified_coupling_table" for x in c.counters) for c in seed.enrich_claims)
    assert all(not any(x["check"] == "unverified_coupling_table" for x in c.counters) for c in better.enrich_claims)


def test_coupling_table_parser_accepts_common_spellings_and_rejects_junk():
    df = pd.DataFrame({"Gene": [f"R{i}" for i in range(9)], "Primary": ["Gs", "Gi/o", "Gq/11", "G12/13", "gs", "Gαi", "Gq", "G13", "Gs"]})
    t = parse_coupling_table(df)
    assert t["R1"] == "Gi" and t["R2"] == "Gq" and t["R3"] == "G12" and t["R5"] == "Gi" and norm_coupling("Gαs") == "Gs"
    with pytest.raises(ValueError):
        parse_coupling_table(pd.DataFrame({"gene": ["A"], "primary": ["Gs"]}))
    with pytest.raises(ValueError):
        parse_coupling_table(pd.DataFrame({"x": [1]}))


def test_matrix_ranking_matches_the_planted_direction(ex):
    m = ex[0]
    r = matrix_ranking(m, ["CD8 T exhausted"])
    assert r["PTGER4"] > 1 and r["CXCR4"] < r["PTGER4"]


# ---------------------------------------------------------------- programs, axes
def test_noise_receptors_do_not_associate_with_any_program(wb):
    noise = wb.programs[wb.programs["GPCR"].isin(["GPR35", "GPR37", "GPR19", "GPR82"])]
    assert not len(noise) == 0 and (noise["FDR"] > 0.05).all() and noise["Pearson r (log)"].max() < 0.6


def test_a_gene_is_never_correlated_with_a_program_it_belongs_to(wb):
    assert not ((wb.programs["GPCR"] == "CTLA4") & (wb.programs["Program"] == "T-cell exhaustion")).any()


def test_custom_program_is_used_and_needs_three_genes(ex):
    m, reg, eff, sig = ex
    w = build(m, reg, load_couplings(), "x", de_effect=eff, extra_programs={"My signature": ["CCN1", "CCN2", "ANKRD1"]})
    assert "My signature" in w.program_names and (w.programs["Program"] == "My signature").any()
    w2 = build(m, reg, load_couplings(), "x", de_effect=eff, extra_programs={"Tiny": ["CCN1", "NOTAGENE", "ALSOFAKE"]})
    assert not (w2.programs["Program"] == "Tiny").any()


def test_oncocrine_axes_recover_the_planted_pairs_and_stay_silent_without_producers(ex):
    m = ex[0]
    a = axes(m, load_couplings())
    row = a[(a["Ligand"] == "CXCL12") & (a["Receptor"] == "CXCR4")].iloc[0]
    assert row["Source context"] == "CAF fibroblast" and row["Relationship"] == "paracrine"
    assert axes(m.drop(index=["PTGS2", "PTGES", "NT5E", "ENTPD1", "CXCL12"]), load_couplings())["Ligand"].tolist().count("CXCL12") == 0


# ---------------------------------------------------------------- alterations, repurposing
def test_alterations_convert_percentages_and_label():
    a = parse_alterations(pd.DataFrame({"Hugo_Symbol": ["gpr87", "gpr87", "x"], "Study": ["HNSC", "LUSC", "HNSC"], "amp": [18, 3, 50]}))
    assert a["amp"].max() <= 0.5 and label(a, "GPR87") == "HNSC (amplified 18%)"
    with pytest.raises(ValueError):
        parse_alterations(pd.DataFrame({"gene": ["A"], "cancer": ["X"], "mut": [3.5]}).assign(mut=[2.5]) if False else pd.DataFrame({"x": [1]}))


def test_action_classification_and_table_ranking():
    assert [action_of(x) for x in ("antagonist", "inverse agonist", "negative allosteric modulator", "agonist", "positive allosteric modulator", "binder")] == \
        ["inhibit", "inhibit", "inhibit", "activate", "activate", "unspecified"]
    t = repurpose_table(["A", "B", "C"], {"A": [{"drug": "d1", "type": "antagonist", "url": "u"}], "B": [{"drug": "d2", "type": "agonist"}], "C": []}, "inhibit")
    assert t.iloc[0]["GPCR"] == "A" and t.set_index("GPCR").loc["C", "Count"] == 0 and "none recorded" in t.set_index("GPCR").loc["C", "Recorded inhibit-type drugs"]


# ---------------------------------------------------------------- workbench and methods
def test_workbench_is_reproducible(ex):
    m, reg, eff, sig = ex
    a = build(m, reg, load_couplings(), "s", de_effect=eff, de_sig=sig, seed=3)
    b = build(m, reg, load_couplings(), "s", de_effect=eff, de_sig=sig, seed=3)
    assert a.enrichment.table.drop(columns="_lead").equals(b.enrichment.table.drop(columns="_lead")) and a.programs.equals(b.programs)


def test_ranking_falls_back_to_matrix_foreground_when_there_is_no_table(ex):
    m, reg = ex[0], ex[1]
    w = build(m, reg, load_couplings(), "s", fg=["CD8 T exhausted"])
    assert w.enrichment is not None and "CD8 T exhausted" in w.enrich_contrast and "matrix" in w.params["ranking"]
    assert build(m, reg, load_couplings(), "s").enrichment is None                # nothing to contrast: no enrichment, not a made-up one


def test_methods_text_describes_only_what_was_run_and_uses_real_parameters(ex, wb):
    m = ex[0]
    md = methods_markdown(wb, m.shape, list(m.columns), 46, alterations=False)
    assert f"{m.shape[1]} contexts" in md and "2000 permutations" in md and "Coupling-class enrichment" in md and "Pan-cancer" not in md and "seed 0" in md
    bare = build(m, ex[1], load_couplings(), "s")
    assert "Coupling-class enrichment" not in methods_markdown(bare, m.shape, list(m.columns), 46)


# ---------------------------------------------------------------- in the app
def _loaded():
    at = app_empty()
    next(b for b in at.button if b.key == "ex_load").click().run()
    return at


def _view(at, name):
    next(r for r in at.radio if r.key == "gp_view").set_value(name).run()
    return at


def test_every_analysis_view_renders_with_content():
    at = _loaded()
    for view, needle in (("G-protein coupling enrichment", "NES"), ("Programs", "Pearson"), ("Oncocrine axes", "Producer"), ("Pan-cancer alterations", "Amplified"), ("Methods and downloads", "Methods paragraph")):
        _view(at, view)
        assert not at.exception, (view, [str(e.value)[:200] for e in at.exception])
        assert needle in text(at) + " ".join(str(d.value.columns.tolist()) for d in at.dataframe), view


def test_enrichment_view_shows_the_finding_and_the_banner_leads_with_it():
    at = _loaded()
    assert at.session_state["_pri"][0].startswith(("Gs-coupled", "Gi-coupled"))
    _view(at, "G-protein coupling enrichment")
    assert "Gs-coupled receptors are enriched" in text(at)
    assert any("Gs" in str(d.value) for d in at.dataframe)


def test_repurposing_lookup_filters_by_direction_with_a_fake_drug_service(monkeypatch):
    fake = types.ModuleType("protellect_data")
    fake.fetch_dgidb_many = lambda genes: {"ADORA2A": [{"drug": "ISTRADEFYLLINE", "type": "antagonist", "url": "https://y"}, {"drug": "AGONISTX", "type": "agonist"}]}
    monkeypatch.setitem(sys.modules, "protellect_data", fake)
    at = _view(_loaded(), "G-protein coupling enrichment")
    assert "ADORA2A" in at.multiselect(key="rp_genes").value
    next(b for b in at.button if b.key == "rp_go").click().run()
    assert not at.exception
    t = next(d.value for d in at.dataframe if "Why listed" in d.value.columns).set_index("GPCR")
    assert "ISTRADEFYLLINE" in t.loc["ADORA2A", "Recorded inhibit-type drugs"] and "AGONISTX" not in t.loc["ADORA2A", "Recorded inhibit-type drugs"]
    assert "AGONISTX" in t.loc["ADORA2A", "Other recorded interactions"] and t.loc["ADORA2A", "Why listed"].startswith("leading edge")


def test_a_user_coupling_table_replaces_the_seed_and_removes_the_unverified_warning():
    at = _loaded()
    seed = load_couplings()
    at.session_state["coupling_table"], at.session_state["coupling_source"] = dict(seed), "IUPHAR primary coupling (uploaded)"
    at.run()
    assert not at.exception and "IUPHAR primary coupling (uploaded)" in text(at)
    _view(at, "G-protein coupling enrichment")
    assert "not been verified" not in text(at)


def test_choosing_foreground_contexts_changes_the_contrast():
    at = _loaded()
    at.session_state["gp_rank_source"] = "matrix"
    at.session_state["gp_fg"] = ["CD8 T exhausted"]
    at.run()
    _view(at, "G-protein coupling enrichment")
    assert not at.exception and "CD8 T exhausted versus the other contexts" in text(at)
