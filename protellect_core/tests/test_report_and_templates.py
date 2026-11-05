import pandas as pd
import pytest

from protellect_core.engine import HypothesisEngine, parse_experiment
from protellect_core.engine.report import hypotheses_table, markdown_report, results_table
from protellect_core.engine.templates import SHAPES, template_csv, template_df
import io


@pytest.mark.parametrize("shape", list(SHAPES))
def test_every_template_parses_with_the_right_shape(shape):
    parsed = parse_experiment(pd.read_csv(io.StringIO(template_csv(shape))))
    assert (parsed["shape"] == shape).all()
    assert len(parsed) == len(template_df(shape))


def _summary():
    eng = HypothesisEngine()
    df = parse_experiment(pd.DataFrame({"gene": ["GPR151", "GPR6", "FFAR1"], "log2fc": [1.7, 1.2, 0.9], "padj": [0.004, 0.02, 0.04]}))
    return eng, eng.run(df, {"disease": "colitis", "tissue": "colon"})


def test_results_table_has_one_row_per_orphan_with_expected_columns():
    _, s = _summary()
    t = results_table(s)
    assert list(t["Receptor"]) == ["GPR151", "GPR6"]
    assert {"Top ligand-class hypothesis", "Relative support", "Critic", "Likely coupling", "First experiment"} <= set(t.columns)
    assert t["Critic"].isin(["holds up", "weakened", "contested"]).all()


def test_results_table_marks_insufficient_evidence_honestly():
    eng = HypothesisEngine(annotations={}, use_live_annotations=False)
    s = eng.run(parse_experiment(pd.DataFrame({"gene": ["GPR151"], "log2fc": [1.5]})), {})
    t = results_table(s)
    assert "insufficient evidence" in t.loc[0, "Top ligand-class hypothesis"]


def test_hypotheses_table_is_flat_and_complete():
    _, s = _summary()
    t = hypotheses_table(s)
    assert {"receptor", "category", "critic_verdict", "counterarguments", "test_experiment"} <= set(t.columns)
    assert len(t) == sum(len(r.hypotheses) for r in s.results)


def test_markdown_report_carries_the_caveats():
    eng, s = _summary()
    md = markdown_report(s, {"disease": "colitis", "tissue": "colon"}, eng.calibration_note(), eng.library_verified)
    assert "hypotheses, not findings" in md.lower()
    assert "not been expert-verified" in md
    assert "GPR151" in md and "Results at a glance" in md
