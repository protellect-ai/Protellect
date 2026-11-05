import json
from protellect_core.engine import HypothesisEngine, load_cases
from protellect_core.engine.cases import cases_from_outcomes


def rec(**o):
    r = {"gene": "GPR999", "status": "confirmed", "ligand_class": "lipid mediator", "coupling": "Gs", "resolution_year": 2025, "ligand": "X", "tissues": ["pancreas", "gut"], "neighbors": [], "cluster": "", "notes": "Confirmed by Ca2+/cAMP assay, our lab", "citations": []}
    r.update(o); return r


def test_only_confirmed_outcomes_with_a_note_become_cases():
    cases, rej = cases_from_outcomes([rec(), rec(status="refuted"), rec(gene="GPR998", notes="", citations=[]), rec(gene="GPR997", ligand_class="not-a-class")])
    assert [c.gene for c in cases] == ["GPR999"] and len(rej) == 2
    assert cases[0].verified is False and cases[0].id.startswith("OUT-")


def test_recording_an_outcome_changes_the_trained_model_and_the_track_record():
    base = load_cases()
    before = HypothesisEngine(cases=base)
    extra, _ = cases_from_outcomes([rec(gene=f"GPR9{i}", resolution_year=2020 + i) for i in range(3)], [c.id for c in base])
    after = HypothesisEngine(cases=base + extra)
    assert len(after.library) == len(before.library) + 3
    assert after.ligand_ranker.weights() != before.ligand_ranker.weights()          # the learned weights actually moved
    assert before.calibration_note() != after.calibration_note()


def test_bad_outcomes_file_never_blocks_startup(tmp_path, monkeypatch):
    import protellect_core.engine.cases as c
    p = c.DATA_DIR / "outcomes.json"
    p.write_text("{ not json")
    try:
        assert len(load_cases()) >= 10
    finally:
        p.unlink()
