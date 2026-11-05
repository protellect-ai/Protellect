"""Gene-name reconciliation, literature-reported pharmacology, sample metadata, and the adhesion-receptor assay."""
import pandas as pd

from protellect_core.assays import ASSAYS, assays_for
from protellect_core.context import metadata_from_df
from protellect_core.engine import HypothesisEngine, parse_experiment
from protellect_core.engine.report import markdown_report, results_table
from protellect_core.evidence import truth_gate
from protellect_core.reported import REPORTED, alias_map, canonicalize, prior_claims, prior_text

REG = {
    "ADGRG1": {"status": "orphan", "family": "Adhesion receptors", "aliases": ["GPR56|TM7XN1"], "note": ""},
    "GPR171": {"status": "orphan", "family": "Class A Orphans", "aliases": [], "note": ""},
    "GPR3": {"status": "orphan", "family": "Class A Orphans", "aliases": [], "note": ""},
    "ADORA2A": {"status": "characterized", "family": "Adenosine receptors", "aliases": [], "note": ""},
}


def frame():
    return pd.DataFrame({"gene": ["GPR56", "ADGRG1", "GPR171", "GPR3", "ADORA2A", "TCF7"], "log2FoldChange": [2.1, 3.4, 1.8, 1.1, 2.0, 3.12],
                         "padj": [1e-5, 1e-8, 1e-4, 1e-3, 1e-3, 1e-9]})


def test_legacy_and_official_names_become_one_gene_and_say_so():
    p = parse_experiment(frame())
    assert list(p["gene"]).count("ADGRG1") == 1 and "GPR56" not in set(p["gene"])
    assert float(p.loc[p["gene"] == "ADGRG1", "effect"].iloc[0]) == 3.4          # the larger effect is kept
    assert any("GPR56" in n and "ADGRG1" in n and "same gene" in n for n in p.attrs["alias_notes"])


def test_registry_synonym_is_mapped_only_when_it_points_to_one_gene():
    d = pd.DataFrame({"gene": ["TM7XN1", "GPR171"], "effect": [1.0, 2.0]})
    out = canonicalize(d, REG)
    assert list(out["gene"]) == ["ADGRG1", "GPR171"]
    clash = dict(REG, GPR3={**REG["GPR3"], "aliases": ["TM7XN1"]})
    assert "TM7XN1" not in alias_map(clash)


def test_an_official_symbol_is_never_renamed_even_if_a_table_lists_it_as_an_alias():
    reg = {"GPR56": {"status": "orphan", "family": "", "aliases": [], "note": ""}}
    out = canonicalize(pd.DataFrame({"gene": ["GPR56"], "effect": [1.0]}), reg)
    assert list(out["gene"]) == ["GPR56"]


def test_engine_run_merges_and_reports_names():
    eng = HypothesisEngine(registry=REG, use_live_annotations=False)
    s = eng.run(parse_experiment(frame(), None, 0.05), {})
    assert s.n_orphan == 3 and any("same gene" in n for n in s.alias_notes)
    assert {r.gene for r in s.results} == {"ADGRG1", "GPR171", "GPR3"}


def test_orphan_without_precedent_shows_reported_pharmacology_labelled_as_such():
    eng = HypothesisEngine(registry=REG, use_live_annotations=False)
    s = eng.run(parse_experiment(frame(), None, 0.05), {})
    t = results_table(s, REG).set_index("Receptor")
    assert "G12/13" in t.loc["ADGRG1", "Likely coupling"] and "(reported)" in t.loc["ADGRG1", "Likely coupling"]
    assert "(reported)" in t.loc["GPR171", "Top ligand-class hypothesis"] and "Gi/o" in t.loc["GPR171", "Likely coupling"]
    assert t.loc["GPR3", "Top ligand-class hypothesis"].startswith("No hypothesis")        # nothing is invented for a receptor with no source
    old = results_table(s).set_index("Receptor")                    # the old call (no registry) still works
    assert "(reported)" in old.loc["GPR171", "Top ligand-class hypothesis"] and old.loc["GPR3", "Top ligand-class hypothesis"].startswith("No hypothesis")


def test_prior_claims_pass_the_truth_gate_and_carry_a_test_plan():
    cs = prior_claims("ADGRG1", REG["ADGRG1"], 3.4, "log2 fold-change")
    shown, withheld = truth_gate(cs)
    assert len(shown) == 2 and not withheld
    cp = next(c for c in shown if c.tags["category"] == "reported-coupling")
    assert cp.how and cp.outcomes and cp.controls
    assert any(p.kind == "literature" for p in cp.proofs) and "NOT" not in cp.text
    assert "not derived from your data" in cp.basis and "not been checked" in cp.basis
    assert cp.tags["assay"] == "adhesion_gpcr"


def test_family_level_prior_is_labelled_family_and_needs_the_family_to_match():
    fam = prior_claims("GPR999", {"status": "orphan", "family": "Adhesion receptors"})
    assert fam and all("family-level" in c.text for c in fam) and all(c.tags["prior"] == "family" for c in fam)
    assert prior_claims("GPR3", REG["GPR3"]) == []
    assert prior_text("GPR3", REG["GPR3"]) is None
    assert prior_text("GPR999", {"family": "Adhesion receptors"})["basis"] == "family-level"


def test_every_reported_entry_names_papers_for_both_claims():
    for g, r in REPORTED.items():
        assert r.coupling and r.coupling_refs and r.ligands and r.ligand_refs, g


def test_report_names_reported_section_and_alias_note():
    eng = HypothesisEngine(registry=REG, use_live_annotations=False)
    s = eng.run(parse_experiment(frame(), None, 0.05), {})
    md = markdown_report(s, {}, "", False, REG)
    assert "Reported in the literature (not learned from your data)" in md and "Gene names:" in md and "not been checked" in md


def test_upload_metadata_fills_context_only_when_the_file_agrees():
    df = frame().assign(Disease="Hepatocellular carcinoma", cell_type="CD8+ T cells", tissue=["tumor", "blood"] * 3)
    m = metadata_from_df(df)
    assert m["ctx_disease"] == "Hepatocellular carcinoma" and m["ctx_tissue"] == "CD8+ T cells"
    assert any("tissue" in x for x in m["ignored"])
    assert metadata_from_df(frame()) == {"found": [], "ignored": []}


def test_adhesion_assay_exists_and_is_complete():
    a = ASSAYS["adhesion_gpcr"]
    assert len(a.do) >= 4 and len(a.outcomes) >= 5 and a.refs
    assert all(o.see and o.means and o.then for o in a.outcomes)
    assert "adhesion_gpcr" in assays_for("adhesion")


def test_engine_answer_is_compared_with_the_literature_entry_and_a_difference_is_shown():
    from protellect_core.reported import compare_with_literature
    assert compare_with_literature("ADGRG1", "peptide", "Gi")["status"] == "differs"          # 'peptide' is not 'tethered peptide'
    assert compare_with_literature("ADGRG1", "extracellular-matrix protein", "G12/13")["status"] == "matches"
    assert compare_with_literature("GPR171", "peptide", "Gi")["status"] == "matches"            # Gi equals Gi/o
    assert compare_with_literature("GPR3", "peptide", "Gi")["status"] == "no entry"
    eng = HypothesisEngine(registry=REG, use_live_annotations=False)
    s = eng.run(parse_experiment(frame(), None, 0.05), {"disease": "glioma", "tissue": "brain"})
    t = results_table(s, REG).set_index("Receptor")
    assert t.loc["ADGRG1", "Versus the literature"] == "differs" and "G12/13" in t.loc["ADGRG1", "Reported in the literature"]
    from protellect_core.engine.memo import decision_memo
    assert "DIFFERS FROM THE LITERATURE ENTRY" in decision_memo(s, {}, REG)
