import json
import pathlib

import pandas as pd
import pytest

from protellect_hypothesis import HypothesisEngine, load_cases, parse_experiment
from protellect_hypothesis.benchmark import evaluate, main as bench_main
from protellect_hypothesis.cases import temporal_precedents, usable
from protellect_hypothesis.ranker import PrecedentRanker, profile_from_case
from protellect_hypothesis.registry import import_iuphar_csv, normalize_tissues

CASES = load_cases()


def test_case_library_loads_and_is_flagged_unverified():
    assert len(CASES) >= 10
    assert all(c.verified is False for c in CASES)          # nothing may claim to be verified by default
    assert [c.id for c in CASES if c.contested] == ["GPR35"]
    assert "GPR35" not in {c.id for c in usable(CASES)}


def test_temporal_split_has_no_leakage():
    for q in usable(CASES):
        lib = temporal_precedents(CASES, q.resolution_year, exclude_id=q.id)
        assert all(c.resolution_year < q.resolution_year for c in lib)
        assert q.id not in {c.id for c in lib}


def test_query_never_in_its_own_library_for_loo():
    res = evaluate(CASES, "loo")
    assert res["n_evaluable"] == len(usable(CASES))


def test_ranker_learns_and_abstains_without_evidence():
    lib = usable(CASES)
    r = PrecedentRanker().fit(lib, "ligand_class")
    w = r.weights()
    assert set(w) == {"tissue_overlap", "neighbor_link", "same_cluster"}
    from protellect_hypothesis.schema import QueryProfile
    assert r.value_scores(QueryProfile(id="X", tissues=[], neighbors=[], cluster=""), lib) == {}


def test_ranker_prefers_cluster_mates():
    lib = [c for c in usable(CASES) if c.id != "GPR40"]
    r = PrecedentRanker().fit(lib, "ligand_class")
    scores = r.value_scores(profile_from_case(next(c for c in CASES if c.id == "GPR40")), lib)
    assert max(scores, key=scores.get) == "fatty acid"       # FFAR cluster-mates bind fatty acids


def test_engine_end_to_end_and_never_claims_certainty():
    eng = HypothesisEngine()
    df = parse_experiment(pd.DataFrame({"gene": ["GPR151", "GPR6", "FFAR1", "TP53"], "log2fc": [1.7, 1.2, 0.9, 0.8]}))
    s = eng.run(df, {"disease": "colitis", "tissue": "colon"})
    assert s.n_gpcr == 3 and s.n_orphan == 2 and s.characterized == ["FFAR1"]
    for r in s.results:
        assert r.status == "hypotheses"
        for h in r.hypotheses:
            assert 0.0 <= h.support <= 1.0
            assert any("wet-lab" in c for c in h.caveats)
            assert any("NOT been expert-verified" in c for c in h.caveats)   # library is unverified
            assert h.test_experiment


def test_engine_abstains_when_no_evidence():
    eng = HypothesisEngine(annotations={}, use_live_annotations=False)
    df = parse_experiment(pd.DataFrame({"gene": ["GPR151"], "log2fc": [1.5]}))
    s = eng.run(df, {})                                      # no context, no annotation
    assert s.results[0].status == "insufficient_evidence" and s.results[0].hypotheses == []


def test_unknown_genes_are_ignored_not_invented():
    eng = HypothesisEngine()
    df = parse_experiment(pd.DataFrame({"gene": ["NOTAGENE", "TP53"], "log2fc": [1.5, 2]}))
    s = eng.run(df, {"tissue": "colon"})
    assert s.n_gpcr == 0 and s.results == []


def test_benchmark_refuses_to_save_unverified_summary(tmp_path):
    assert bench_main(["--save-summary"]) == 2


def test_benchmark_report_warns_when_unverified(capsys):
    assert bench_main(["--mode", "temporal"]) == 0
    assert "WARNING" in capsys.readouterr().out


def test_tissue_normalizer():
    assert normalize_tissues(["colon biopsy", "pancreatic islets"]) == ["gut", "pancreas"]


def test_iuphar_importer_on_synthetic_file(tmp_path):
    src = tmp_path / "t.csv"
    src.write_text('# GtoPdb synthetic\nType,Family name,HGNC symbol\n'
                   'gpcr,Class A Orphans,GPR151\ngpcr,Free fatty acid receptors,FFAR1\nlgic,Nicotinic,CHRNA1\n')
    out = tmp_path / "reg.csv"
    assert import_iuphar_csv(str(src), str(out)) == 2
    df = pd.read_csv(out).set_index("gene")
    assert df.loc["GPR151", "status"] == "orphan" and df.loc["FFAR1", "status"] == "characterized"
    bad = tmp_path / "bad.csv"; bad.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        import_iuphar_csv(str(bad), str(tmp_path / "x.csv"))


def test_random_baseline_is_reported_and_sane():
    res = evaluate(CASES, "loo")
    # 4 classes in each LOO library -> about 1/4 expected per case
    assert 2.5 <= res["random_expected_hits"] <= 4.0
    assert res["top1_hits"] >= 0
