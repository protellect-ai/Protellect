"""With an uploaded experiment: the list of proteins is always shown; details follow ONE protein (the searched one, or the one picked)."""
import pandas as pd
from protellect_core.tests.test_views import app_for, text

DF = pd.DataFrame({"gene": ["GPR151", "GPR88", "TP53", "ACTB", "TCF7"], "log2FoldChange": [2.4, -1.8, 0.2, 0.0, 3.12], "padj": [1e-6, 1e-4, 0.5, 0.9, 1e-8]})
UP = {"csv_df": DF, "csv_triage_active": True, "csv_filename": "mine.csv"}


def dfs(at):
    return " ".join(str(d.value) + " " + " ".join(map(str, d.value.columns)) for d in at.dataframe)


def detail_rows(at):
    return [x for x in at.dataframe if "Top ligand-class hypothesis" in list(x.value.columns)]


def md(at):
    return " ".join(m.value for m in at.markdown)


def test_unrelated_search_shows_protein_list_only_and_asks_to_pick():
    at = app_for("overview", extra=UP)                    # TP53 searched; it is not an orphan in the table
    assert not at.exception
    d = dfs(at)
    assert "GPR151" in d and "GPR88" in d
    assert not detail_rows(at)                           # no per-protein detail for everyone
    assert "Pick a protein" in " ".join(i.value for i in at.info) or "one protein at a time" in text(at)


def test_searching_a_listed_protein_selects_it_and_shows_only_its_detail():
    at = app_for("overview", "GPR151", "Q8TDV0", extra=UP)
    assert not at.exception
    assert at.session_state["focus_gene"] == "GPR151"
    rows = detail_rows(at)                               # its own row, and only one row
    assert len(rows) == 1 and len(rows[0].value) == 1
    assert "**GPR151**" in md(at) and "**GPR88**" not in md(at)


def test_experiments_tab_lists_proteins_until_one_is_chosen_then_filters_the_plan():
    at = app_for("experiments", extra=UP)
    assert not at.exception
    assert "Proteins in your experiment" in text(at) and "one protein at a time" in " ".join(i.value for i in at.info)
    at2 = app_for("experiments", "GPR151", "Q8TDV0", extra=UP)
    assert not at2.exception and "Proteins in your experiment" not in text(at2)


def test_picking_a_protein_in_the_selector_changes_the_detail():
    at = app_for("overview", extra=UP)
    sb = next(s for s in at.selectbox if s.key == "focus_gene")
    assert sb.value == "(none)" and "GPR88" in sb.options
    sb.select("GPR88").run()
    assert not at.exception and at.session_state["focus_gene"] == "GPR88"
    rows = detail_rows(at)
    assert len(rows) == 1 and len(rows[0].value) == 1
    assert "**GPR88**" in md(at) and "**GPR151**" not in md(at)


def test_without_an_experiment_nothing_changes():
    at = app_for("overview")
    assert not at.exception and not [s for s in at.selectbox if s.key == "focus_gene"]
