"""A transcription factor that the researcher's own experiment singles out must not be dismissed by a druggability score."""
import pandas as pd
import pytest

from protellect_core.adapters import build_bundle
from protellect_core.analysis import biomarker_lens, modality_note, possibility, user_signal
from protellect_core.routing import priorities
from protellect_core.tests.test_analysis import session


def tcf7_like():
    """No germline variants, no tractability, no drugs, nuclear with a DNA-binding region: the profile of a lineage transcription factor."""
    b = build_bundle(session("TCF7", "P36402"))
    b.variants, b.drugs, b.trials, b.tractability, b.clingen, b.n_known_drugs = [], [], [], {"Small molecule": False, "Antibody": False, "PROTAC": False}, "", 0
    b.domains = [{"start": 270, "end": 338, "type": "DNA binding", "desc": "HMG box"}]
    b.subcellular = ["Nucleus"]
    b.constraint = {"pLI": 0.99, "oe_lof": 0.1, "oe_lof_upper": 0.2, "mis_z": 3.0}
    return b


def table(effect=3.12, p=1e-6, n=500):
    rows = [{"gene": f"G{i}", "shape": "expression", "effect": 0.01 * (i % 50), "effect_type": "log2 fold-change", "significance": 0.5} for i in range(n)]
    rows.append({"gene": "TCF7", "shape": "expression", "effect": effect, "effect_type": "log2 fold-change", "significance": p})
    return pd.DataFrame(rows)


def test_drug_lens_is_low_but_bio_lens_is_high_for_a_strong_tf_signal():
    b = tcf7_like()
    poss = possibility(b)
    assert poss["level"] in ("LOW", "INSUFFICIENT DATA") and poss["lens"].startswith("drug target")
    u = user_signal(table(), "TCF7", b.aliases)
    assert u and u["rank"] == 1 and abs(u["log2fc"] - 3.12) < 1e-9
    bio = biomarker_lens(b, u, "my_table.csv")
    assert bio["level"] == "HIGH" and bio["pct"] >= 60
    eff = next(c for c in bio["components"] if c["name"] == "Effect in your experiment")
    assert eff["points"] == 35 and "Your uploaded table" in eff["proof"].source


def test_banner_leads_with_the_experiment_and_does_not_deprioritise():
    b = tcf7_like()
    poss = possibility(b)
    bio = biomarker_lens(b, user_signal(table(), "TCF7", b.aliases))
    note = modality_note(b)
    assert "DNA-binding region" in note and "HMG box" in note
    out = priorities(b, poss, [], None, None, 0, None, None, bio=bio, modality=note)
    assert out[0].level == "PRIORITIZE" and "role in your experiment" in out[0].headline
    assert not any(p.level == "DEPRIORITIZE" for p in out)
    drug = next(p for p in out if "drug target" in p.headline)
    assert "not a measure of biological or biomarker importance" in " ".join(drug.reasons) and note in drug.reasons


def test_without_an_experiment_the_original_verdict_is_unchanged():
    b = tcf7_like()
    out = priorities(b, possibility(b), [], None, None, 0, None, None)
    assert any(p.level in ("DEPRIORITIZE", "DATA GAP") for p in out)
    assert biomarker_lens(b, None) is None and user_signal(table(), "NOTINTABLE", ()) is None


def test_weak_signal_scores_low_and_scoring_is_honest_about_missing_columns():
    b = tcf7_like()
    weak = biomarker_lens(b, user_signal(table(effect=0.1, p=0.6), "TCF7", b.aliases))
    assert weak["level"] in ("LOW", "MODERATE") and next(c for c in weak["components"] if c["name"] == "Effect in your experiment")["points"] == 0
    nosig = table(); nosig["significance"] = float("nan")
    r = biomarker_lens(b, user_signal(nosig, "TCF7", b.aliases))
    assert "no significance" in next(c for c in r["components"] if c["name"] == "Effect in your experiment")["value"]
    other = table(); other["effect_type"] = "phenotype score"
    o = biomarker_lens(b, user_signal(other, "TCF7", b.aliases))
    assert next(c for c in o["components"] if c["name"] == "Effect in your experiment")["available"] is False


def test_non_tf_has_no_modality_note():
    b = build_bundle(session())
    b.domains, b.subcellular = [], ["Cell membrane"]
    assert modality_note(b) == ""
