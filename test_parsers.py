import pandas as pd
import pytest

from protellect_hypothesis import InputError, parse_experiment


def test_expression_autodetect_and_clean():
    df = pd.DataFrame({"Gene": [" gpr151", "TP53", "TP53"], "log2FoldChange": [1.5, 0.2, -2.0], "padj": [0.01, 0.5, 0.02]})
    out = parse_experiment(df)
    assert set(out["gene"]) == {"GPR151", "TP53"}
    assert (out["shape"] == "expression").all()
    # duplicate gene keeps the strongest effect
    assert out.loc[out.gene == "TP53", "effect"].iloc[0] == -2.0


def test_variant_shape():
    df = pd.DataFrame({"gene_symbol": ["A", "B"], "rsid": ["rs1", "rs2"], "odds_ratio": [1.4, 0.8], "p_value": [1e-6, 0.2]})
    assert (parse_experiment(df)["shape"] == "variant").all()


def test_screen_shape():
    df = pd.DataFrame({"gene": ["A", "B"], "phenotype_score": [-2.1, 0.3]})
    assert (parse_experiment(df)["shape"] == "screen").all()


def test_significance_filter():
    df = pd.DataFrame({"gene": ["A", "B"], "log2fc": [1, 1], "padj": [0.01, 0.9]})
    assert list(parse_experiment(df, max_significance=0.05)["gene"]) == ["A"]


def test_errors_are_explicit():
    with pytest.raises(InputError):
        parse_experiment(pd.DataFrame({"x": [1]}))
    with pytest.raises(InputError):
        parse_experiment(pd.DataFrame({"gene": ["A"], "notes": ["hi"]}))
    with pytest.raises(InputError):
        parse_experiment(pd.DataFrame({"gene": ["A"], "log2fc": [1]}), shape="bogus")
