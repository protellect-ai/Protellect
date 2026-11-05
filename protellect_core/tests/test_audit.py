import pytest

from protellect_core.audit import EvidenceLine, audit_target, lines_from_csv, audit_markdown, your_experiment_line, TEMPLATE_CSV


def L(kind="genetics", direction="supports", strength="moderate", study="S1", tags=(), gene="GPR1", disease="d"):
    return EvidenceLine(gene=gene, disease=disease, kind=kind, direction=direction, strength=strength, summary="x", source=study, study_id=study, tags=list(tags))


def test_no_lines_is_unchecked_and_nothing_is_invented():
    a = audit_target("GPR1", "d", [])
    assert a.tier == "Unchecked" and not a.flags


def test_one_source_is_weak_and_flagged():
    a = audit_target("GPR1", "d", [L("genetics")])
    assert a.tier == "Weak" and any(f["flag"] == "single_source" for f in a.flags)


def test_expression_only_is_weak_and_has_no_causal_flag():
    a = audit_target("GPR1", "d", [L("expression", study="A"), L("literature", study="B"), L("expression", study="C")])
    assert a.tier in ("Weak", "Mixed") and {"expression_only", "no_causal_evidence"} <= {f["flag"] for f in a.flags}
    assert a.tier != "Strong"


def test_strong_needs_three_sources_two_kinds_causal_and_nothing_against():
    good = [L("genetics", study="A"), L("perturbation", study="B"), L("expression", study="C")]
    assert audit_target("GPR1", "d", good).tier == "Strong"
    assert audit_target("GPR1", "d", good + [L("expression", "against", "weak", "D")]).tier == "Mixed"
    assert audit_target("GPR1", "d", good[:2]).tier == "Mixed"


def test_two_lines_from_the_same_paper_are_one_source():
    a = audit_target("GPR1", "d", [L("genetics", study="A"), L("perturbation", study="A"), L("expression", study="A")])
    assert a.tier == "Weak" and any(f["flag"] == "single_source" for f in a.flags)


def test_strong_contradiction_with_thin_support_is_contradicted():
    assert audit_target("GPR1", "d", [L("genetics", study="A"), L("perturbation", "against", "strong", "B")]).tier == "Contradicted"


def test_tractability_is_not_evidence_for_the_link():
    assert audit_target("GPR1", "d", [L("tractability")]).tier == "Unchecked"


def test_tags_raise_flags_and_every_flag_carries_a_test():
    a = audit_target("GPR1", "d", [L("genetics", tags=["gwas_nearest_gene", "cell_line_only"])])
    names = {f["flag"] for f in a.flags}
    assert {"gwas_nearest_gene", "cell_line_only"} <= names and all(f["test"] for f in a.flags)


def test_a_line_without_a_source_is_refused():
    with pytest.raises(ValueError):
        EvidenceLine(gene="G", disease="d", kind="genetics", direction="supports", strength="weak", summary="x", source=" ")


def test_csv_round_trip_and_markdown_names_sources():
    csv_text = TEMPLATE_CSV.replace("EXAMPLE_GENE", "GPR1")
    lines = lines_from_csv(csv_text)
    a = audit_target("GPR1", "example disease", lines)
    md = audit_markdown(a)
    assert "Author et al. Journal Year" in md and "Evidence tier" in md and "gwas nearest gene" in md


def test_disputed_ligand_flag_comes_from_the_reported_entry():
    a = audit_target("GPR18", "d", [L("genetics", gene="GPR18")])
    assert any(f["flag"] == "disputed_ligand" for f in a.flags)


def test_the_apps_own_expression_line_is_labelled_as_such():
    l = your_experiment_line("GPR1", "d", 2.0, "log2 fold-change", 1e-5)
    assert l.source == "Your experiment" and l.kind == "expression"
    assert audit_target("GPR1", "d", [l]).tier == "Weak"


def test_audit_view_renders_for_an_experiment_without_errors():
    import pandas as pd
    from streamlit.testing.v1 import AppTest

    def script():
        import streamlit as st
        import pandas as pd
        from protellect_core.engine import HypothesisEngine, parse_experiment
        from protellect_core.tests.test_reported import REG
        from protellect_core.views.audit_view import render_audit

        class A:  # the audit view only reads .summary
            pass
        a = A()
        df = pd.DataFrame({"gene": ["GPR171", "GPR3"], "log2FoldChange": [1.8, 1.1], "padj": [1e-4, 1e-3]})
        a.summary = HypothesisEngine(registry=REG, use_live_annotations=False).run(parse_experiment(df, None, 0.05), {})
        render_audit(a)

    at = AppTest.from_function(script, default_timeout=60).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "GPR171" in text and "Weak" in text and "Evidence audit" in text
