import json
from pathlib import Path
from protellect_core.engine.verify import split_citation, build_query, judge, run


def test_citation_parsing():
    assert split_citation("Itoh 2003") == ("Itoh", 2003)
    assert split_citation("Kotarsky et al. 2003") == ("Kotarsky", 2003)
    assert split_citation("nonsense") == (None, None)


def test_judge_prefers_title_match_and_flags_weak_ones():
    res = {"resultList": {"result": [
        {"pmid": "1", "authorString": "Itoh Y, Kawamata Y.", "pubYear": "2003", "title": "Nutrient regulation of insulin by GPR40"},
        {"pmid": "2", "authorString": "Smith J.", "pubYear": "2003", "title": "GPR40 something"}]}}
    j = judge(res, "Itoh", 2003, ["GPR40", "FFAR1"])
    assert j["found"] and j["pmid"] == "1" and "names the receptor" in j["note"]
    weak = judge({"resultList": {"result": [{"pmid": "9", "authorString": "Itoh Y", "pubYear": "2003", "title": "A paper about orphan receptors"}]}}, "Itoh", 2003, ["GPR40"])
    assert weak["found"] and "read it to confirm" in weak["note"]
    assert not judge({"resultList": {"result": []}}, "Itoh", 2003, ["GPR40"])["found"]
    assert not judge({"resultList": {"result": [{"pmid": "3", "authorString": "Itoh Y", "pubYear": "1999", "title": "GPR40"}]}}, "Itoh", 2003, ["GPR40"])["found"]


def test_run_writes_csv_and_never_touches_verified(tmp_path):
    cases = tmp_path / "c.json"
    cases.write_text(json.dumps({"GPR40": {"id": "GPR40", "gene": "FFAR1", "citations": ["Itoh 2003", "bad cite"], "verified": False}}))
    fake = lambda q: {"resultList": {"result": [{"pmid": "12802337", "authorString": "Itoh Y, X Y.", "pubYear": "2003", "title": "GPR40 paper"}]}}
    out = tmp_path / "o.csv"
    rows = run(cases, out, fetch=fake, sleep=0)
    assert rows[0]["found"] and rows[1]["found"] is False and out.read_text().count("\n") == 3
    assert json.loads(cases.read_text())["GPR40"]["verified"] is False
    assert "AUTH:\"Itoh\"" in build_query("Itoh", 2003, ["GPR40"])
