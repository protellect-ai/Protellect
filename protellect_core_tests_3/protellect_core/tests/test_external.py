import json
import numpy as np
import pytest
from protellect_core.external import auroc, calibrate, reading, parse_confidence_json, interface_reading

rng = np.random.default_rng(5)


def test_auroc_known_values():
    assert auroc([3, 4, 5], [0, 1, 2]) == 1.0 and auroc([0, 1, 2], [3, 4, 5]) == 0.0 and auroc([1, 2], [1, 2]) == 0.5


def test_separating_score_is_useful_and_query_is_placed():
    pos = rng.normal(8, 1, 20); neg = rng.normal(5, 1, 60)
    c = calibrate(pos, neg, query=[8.5, 4.0])
    assert c["verdict"] == "useful" and c["ci95"][0] > 0.85
    assert c["queries"][0]["call"] == "looks like the known binders" and c["queries"][1]["call"] == "indistinguishable from decoys"
    assert "AUROC" in reading(c)


def test_uninformative_score_is_called_not_useful_and_never_trusts_a_query():
    pos = rng.normal(5, 1, 20); neg = rng.normal(5, 1, 60)
    c = calibrate(pos, neg, query=[9.0])
    assert c["verdict"] in ("not useful", "weak") and (c["verdict"] != "not useful" or c["queries"][0]["call"] == "indistinguishable from decoys")
    assert "NOT separate" in reading(calibrate(pos, rng.normal(5, 1, 60))) or c["verdict"] == "weak"


def test_lower_is_better_for_vina_style_scores():
    pos = rng.normal(-9, 0.8, 15); neg = rng.normal(-6, 0.8, 50)
    c = calibrate(pos, neg, query=[-9.5], higher_is_better=False)
    assert c["verdict"] == "useful" and c["queries"][0]["p_vs_decoys"] < 0.05 and c["threshold"] < -6


def test_too_few_examples_refused():
    with pytest.raises(ValueError):
        calibrate([1, 2, 3], [0] * 20)


def test_confidence_json_nested_and_garbage():
    conf = parse_confidence_json(json.dumps({"summary": {"iptm": 0.71, "ptm": 0.83}, "chains_ptm": {"A": 0.8}, "x": [{"complex_plddt": 82.5}]}))
    assert conf["iptm"] == 0.71 and conf["complex_plddt"] == 82.5
    assert any("intermediate" in s for s in interface_reading(conf)) and any("not binding affinity" in s for s in interface_reading(conf))
    with pytest.raises(ValueError):
        parse_confidence_json("not json")
    with pytest.raises(ValueError):
        parse_confidence_json("{\"foo\": 1}")
