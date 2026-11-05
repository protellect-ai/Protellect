import json

import pandas as pd

from protellect_core.engine.gate import evaluate_gate, _sign_test_p
from protellect_core.engine.learned import LearnedModel
from protellect_core.engine.outcomes_io import outcomes_from_csv
from protellect_core.engine.schema import Case
from protellect_core.engine.pipeline import build_cases, orphan_table
from protellect_core.engine.freeze import freeze, check


def _case(i, cls, band, tissues=()):
    return Case(id=i, gene=i, resolution_year=2026, ligand="x", ligand_class=cls, coupling="Gq", cluster=band, neighbors=[], tissues=list(tissues), later_outcome="", citations=[])


def test_sign_test_is_exact():
    assert _sign_test_p(0, 0) == 1.0 and _sign_test_p(10, 0) < 0.01 and abs(_sign_test_p(5, 5) - 1.0) < 1e-9


def test_learned_model_uses_neighbours_and_abstains_without_information():
    cases = [_case(f"P{i}", "peptide", "1p1") for i in range(5)] + [_case(f"M{i}", "metabolite", "2q2") for i in range(5)]
    m = LearnedModel(use_tissue=False).fit(cases)
    assert max(m.predict(_case("Q", "", "1p1")).items(), key=lambda kv: kv[1])[0] == "peptide"
    assert m.predict(_case("R", "", "")) is None


def test_gate_reports_abstention_honestly_and_does_not_flatter_a_useless_model():
    cases = [_case(f"A{i}", "peptide" if i % 2 else "metabolite", "9q9") for i in range(12)]        # neighbours carry no information
    g = evaluate_gate(cases, use_tissue=False, include_precedent=False)
    assert g["tests"]["learned"]["beats_baseline"] is False and 0.0 <= g["tests"]["learned"]["coverage"] <= 1.0


def test_outcomes_csv_becomes_outcome_records(tmp_path):
    c = tmp_path / "o.csv"
    c.write_text("gene,status,ligand,ligand_class,coupling,resolution_year,notes,citations\nGPR1,confirmed,foo,peptide,Gi,2026,tested in lab,PMID 1;PMID 2\nGPR2,refuted,,,,,no signal,\n")
    out = tmp_path / "outcomes.json"
    assert outcomes_from_csv(c, out) == 2
    recs = json.loads(out.read_text())["outcomes"]
    assert recs[0]["citations"] == ["PMID 1", "PMID 2"] and recs[1]["status"] == "refuted"
