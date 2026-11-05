import hashlib

import pandas as pd

from protellect_core.engine import HypothesisEngine, parse_experiment
from protellect_core.engine.memo import decision_memo

REC = {"file_name": "my_data.csv", "n_bytes": 123, "sha256": hashlib.sha256(b"x").hexdigest(), "registry_label": "IUPHAR 2026.2", "n_cases": 30}


def _run(genes, effects, ctx, **kw):
    eng = HypothesisEngine(**kw)
    s = eng.run(parse_experiment(pd.DataFrame({"gene": genes, "log2fc": effects})), ctx)
    return eng, s


def test_memo_has_answer_record_limits_and_signoff():
    eng, s = _run(["GPR151", "GPR6", "FFAR1", "TP53"], [1.7, 1.2, 0.9, 0.8], {"disease": "colitis", "tissue": "colon"})
    md = decision_memo(s, {"disease": "colitis", "tissue": "colon"}, eng.registry, eng.library_verified, REC)
    for part in ["# Target decision memo", "## Bottom line", "## Priority table", "## What this memo does not tell you", "## Analysis record", "## Sign-off"]:
        assert part in md
    assert REC["sha256"] in md and "my_data.csv" in md and "IUPHAR 2026.2" in md
    assert "GPR151" in md and "GPR6" in md
    assert "not expert-verified" in md or "has not been expert-verified" in md
    assert "not computed" in md and "hypotheses, not findings" in md
    assert "validated" not in md.lower().replace("not been expert-verified", "")      # never says validated


def test_memo_sorts_best_first_and_never_invents_a_hypothesis():
    eng, s = _run(["GPR151"], [1.5], {}, annotations={}, use_live_annotations=False)       # no evidence at all
    md = decision_memo(s, {}, eng.registry, eng.library_verified, {})
    assert "No hypothesis" in md and "Not enough evidence" in md
    assert "Test first" not in md.split("## What this memo")[0] or "None of the" in md
    assert "not recorded" in md                                                                 # missing record fields are said, not faked


def test_memo_handles_no_orphans_and_pipes_in_text():
    eng, s = _run(["TP53"], [2.0], {})
    md = decision_memo(s, {}, eng.registry, False, REC)
    assert "nothing to prioritise" in md and "## Analysis record" in md
    from protellect_core.engine.memo import _cell
    assert "|" not in _cell("a|b\nc")
