import json
import pytest
import requests

import protellect_data as pdm


class Resp:
    def __init__(self, code=200, body=None, text="", headers=None):
        self.status_code, self._b, self.text, self.headers = code, body, text, headers or {}
    def json(self):
        if self._b is None:
            raise ValueError("not json")
        return self._b
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setattr(pdm.time, "sleep", lambda s: None)
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    pdm.FETCH_ERRORS.clear()
    for f in (pdm.fetch_dgidb, pdm.fetch_opentargets, pdm.fetch_clingen, pdm.fetch_isoforms):
        f.clear()
    pdm._clingen_download.clear()
    yield


# ---------------------------------------------------------------- reliability layer
def test_retries_rate_limits_then_succeeds(monkeypatch):
    seq = [Resp(429, {}), Resp(503, {}), Resp(200, {"ok": 1})]
    calls = []
    monkeypatch.setattr(requests, "get", lambda url, **k: (calls.append(url), seq.pop(0))[1])
    assert pdm._get("https://example.org/x").json() == {"ok": 1} and len(calls) == 3


def test_retries_connection_errors_and_finally_raises(monkeypatch):
    n = []
    def boom(url, **k):
        n.append(1); raise requests.ConnectionError("down")
    monkeypatch.setattr(requests, "get", boom)
    with pytest.raises(requests.ConnectionError):
        pdm._get("https://example.org/x")
    assert len(n) == 4


def test_ncbi_key_goes_only_to_ncbi(monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "SECRETKEY")
    seen = {}
    monkeypatch.setattr(requests, "get", lambda url, **k: (seen.__setitem__(url, k), Resp(200, {}))[1])
    pdm._get(pdm.ESEARCH, params={"db": "pubmed"})
    pdm._get("https://dgidb.org/x", params={"a": 1})
    assert seen[pdm.ESEARCH]["params"]["api_key"] == "SECRETKEY" and seen[pdm.ESEARCH]["params"]["tool"] == "protellect"
    assert "api_key" not in (seen["https://dgidb.org/x"].get("params") or {})


def test_ncbi_calls_are_throttled(monkeypatch):
    sleeps, now = [], [1000.0]
    monkeypatch.setattr(pdm.time, "time", lambda: now[0])
    monkeypatch.setattr(pdm.time, "sleep", lambda s: (sleeps.append(round(s, 2)), now.__setitem__(0, now[0] + s)))
    monkeypatch.setattr(requests, "get", lambda url, **k: Resp(200, {}))
    pdm._NCBI_LAST[0] = 0.0
    pdm._get(pdm.ESEARCH); pdm._get(pdm.ESEARCH)
    assert sleeps and sleeps[0] == pytest.approx(0.36, abs=0.02)         # 3 requests/second without a key


# ---------------------------------------------------------------- isoforms
def test_isoforms_use_the_real_uniprot_comment_type(monkeypatch):
    js = {"comments": [{"commentType": "ALTERNATIVE PRODUCTS", "isoforms": [{"name": {"value": "1"}, "isoformIds": ["P04637-1"], "note": {"texts": [{"value": "Disease variant isoform"}]}}, {"name": {"value": "2"}, "isoformIds": ["P04637-2"]}]}]}
    monkeypatch.setattr(requests, "get", lambda url, **k: Resp(200, js))
    out = pdm.fetch_isoforms("P04637")
    assert [i["name"] for i in out] == ["1", "2"] and out[0]["disease_relevant"] is True


# ---------------------------------------------------------------- DGIdb
V5 = {"data": {"genes": {"nodes": [{"name": "TP53", "interactions": [
    {"drug": {"name": "NUTLIN-3"}, "interactionScore": 0.4, "interactionTypes": [{"type": "inhibitor"}], "sources": [{"sourceDbName": "ChEMBL"}, {"sourceDbName": "DrugBank"}, {"sourceDbName": "X"}]},
    {"drug": {"name": "ADVEXIN"}, "interactionScore": 2.1, "interactionTypes": [], "sources": []},
    {"drug": {"name": "nutlin-3"}, "interactionScore": 0.1, "interactionTypes": [], "sources": []}]}]}}}


def test_dgidb_v5_parses_ranks_and_dedupes(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda url, **k: Resp(200, V5))
    out = pdm.fetch_dgidb("TP53")
    assert [d["drug"] for d in out] == ["ADVEXIN", "NUTLIN-3"] and out[0]["type"] == "unknown" and out[1]["type"] == "inhibitor" and out[1]["sources"] == "ChEMBL, DrugBank"
    assert set(out[0]) == {"drug", "type", "sources", "url"}                      # the shape the app already consumes


def test_dgidb_graphql_error_is_reported_and_not_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "post", lambda url, **k: (calls.append(1), Resp(200, {"errors": [{"message": "Cannot query field x"}]}))[1])
    assert pdm.fetch_dgidb("TP53") == [] and "DGIdb GraphQL" in pdm.FETCH_ERRORS["DGIdb"]
    pdm.fetch_dgidb("TP53")
    assert len(calls) == 2                                                          # a failure is retried next time, not cached for an hour


def test_dgidb_falls_back_to_legacy_if_v5_is_down(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda url, **k: Resp(404, {}))
    monkeypatch.setattr(requests, "get", lambda url, **k: Resp(200, {"matchedTerms": [{"interactions": [{"drugName": "OLDDRUG", "interactionTypes": ["inhibitor"], "sources": ["DrugBank"]}]}]}))
    assert pdm.fetch_dgidb("TP53")[0]["drug"] == "OLDDRUG"


def test_dgidb_genuinely_empty_is_cached_and_not_an_error(monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "post", lambda url, **k: (calls.append(1), Resp(200, {"data": {"genes": {"nodes": []}}}))[1])
    assert pdm.fetch_dgidb("NOVEL1") == [] and pdm.fetch_dgidb("NOVEL1") == [] and len(calls) == 1 and "DGIdb" not in pdm.FETCH_ERRORS


# ---------------------------------------------------------------- Open Targets
def ot_router(fail=(), drugs_variant="a"):
    state = {"calls": []}
    def get(url, **k):
        if "mygene" in url:
            return Resp(200, {"hits": [{"symbol": "TP53BP1", "ensembl": {"gene": "ENSG_WRONG"}}, {"symbol": "TP53", "ensembl": [{"gene": "ENSG00000141510"}]}]})
        return Resp(404, {})
    def post(url, **k):
        q = k["json"]["query"]; state["calls"].append(q)
        for bad in fail:
            if bad in q:
                return Resp(200, {"errors": [{"message": f'Cannot query field "{bad}" on type "Target".'}]})
        if "tractability" in q:
            return Resp(200, {"data": {"target": {"tractability": [{"label": "Approved Drug", "modality": "SM", "value": True}, {"label": "Predicted Tractable", "modality": "AB", "value": False}, {"label": "Clinical Precedence", "modality": "PR", "value": True}]}}})
        if "knownDrugs" in q:
            return Resp(200, {"data": {"target": {"knownDrugs": {"count": 2, "rows": [{"drug": {"id": "CHEMBL1", "name": "DRUGA"}, "phase": 3, "mechanismOfAction": "inhibitor", "disease": {"name": "cancer"}}]}}}})
        if "drugAndClinicalCandidates" in q:
            return Resp(200, {"data": {"target": {"drugAndClinicalCandidates": {"count": 1, "rows": [{"drug": {"id": "CHEMBL2", "name": "DRUGB"}, "maxClinicalStage": 2, "diseases": [{"disease": {"name": "lymphoma"}}]}]}}}})
        if "associatedDiseases" in q:
            return Resp(200, {"data": {"target": {"associatedDiseases": {"rows": [{"disease": {"id": "EFO_1", "name": "Li-Fraumeni syndrome"}, "score": 0.87654}]}}}})
        if "expressions" in q:
            return Resp(200, {"data": {"target": {"expressions": [{"tissue": {"label": "lung"}, "rna": {"value": 12}}, {"tissue": {"label": "x"}, "rna": {"value": 0}}]}}})
    return get, post, state


def test_opentargets_resolves_the_right_gene_and_maps_tractability(monkeypatch):
    g, p, st = ot_router()
    monkeypatch.setattr(requests, "get", g); monkeypatch.setattr(requests, "post", p)
    out = pdm.fetch_opentargets("TP53")
    assert out["ensembl_id"] == "ENSG00000141510"                                    # not the first free-text hit (TP53BP1)
    assert out["tractability"].get("Small molecule") and out["tractability"].get("PROTAC") and not out["tractability"].get("Antibody")
    assert "SM" not in out["tractability"]                                           # the app reads 'Small molecule', never 'SM'
    assert out["known_drugs"][0]["name"] == "DRUGA" and out["drug_count"] == 2
    assert out["disease_associations"][0]["score"] == 0.877 and out["top_tissues"] == [("lung", 12)] and "_errors" not in out


def test_opentargets_one_bad_field_no_longer_blanks_everything(monkeypatch):
    g, p, st = ot_router(fail=("knownDrugs", "associatedDiseases(size"))
    monkeypatch.setattr(requests, "get", g); monkeypatch.setattr(requests, "post", p)
    out = pdm.fetch_opentargets("TP53")
    assert out["known_drugs"][0]["name"] == "DRUGB"                                  # fell back to the newer drug query
    assert out["disease_associations"][0]["disease"] == "Li-Fraumeni syndrome"      # fell back to the paged argument form
    assert out["tractability"]["Small molecule"] and "_errors" not in out


def test_opentargets_partial_failure_is_reported_not_hidden(monkeypatch):
    g, p, st = ot_router(fail=("knownDrugs", "drugAndClinicalCandidates"))
    monkeypatch.setattr(requests, "get", g); monkeypatch.setattr(requests, "post", p)
    out = pdm.fetch_opentargets("TP53")
    assert out["known_drugs"] == [] and "drugs" in out["_errors"] and "Cannot query field" in out["_errors"]["drugs"]
    assert out["tractability"]["Small molecule"]


def test_opentargets_total_failure_is_not_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "get", lambda url, **k: Resp(200, {"hits": [{"symbol": "TP53", "ensembl": {"gene": "ENSG1"}}]}))
    monkeypatch.setattr(requests, "post", lambda url, **k: (calls.append(1), Resp(503, {}))[1])
    assert pdm.fetch_opentargets("TP53") == {} and "Open Targets" in pdm.FETCH_ERRORS
    n = len(calls); pdm.fetch_opentargets("TP53")
    assert len(calls) > n


# ---------------------------------------------------------------- ClinGen
CSV = "CLINGEN GENE VALIDITY CURATIONS\nFILE CREATED: 2026-01-01\n+++++\nGENE SYMBOL,GENE ID (HGNC),DISEASE LABEL,DISEASE ID (MONDO),MOI,SOP,CLASSIFICATION,ONLINE REPORT,CLASSIFICATION DATE,GCEP\nTP53,HGNC:11998,Li-Fraumeni syndrome,MONDO:0018875,AD,SOP9,Definitive,https://search.clinicalgenome.org/kb/gene-validity/X,2020-01-01,Hered Cancer\nTP53,HGNC:11998,other disease,MONDO:1,AD,SOP9,Limited,https://x,2020-01-01,G\nBRCA1,HGNC:1100,breast,MONDO:2,AD,SOP9,Definitive,https://y,2020-01-01,G\n"


def test_clingen_returns_the_key_the_app_actually_reads(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, **k: Resp(200, None, text=CSV))
    out = pdm.fetch_clingen("TP53")
    assert out["classification"] == "Definitive" and out["disease"] == "Li-Fraumeni syndrome" and out["n"] == 2
    assert pdm.fetch_clingen("NOTINCLINGEN")["classification"] == ""


def test_clingen_download_failure_is_reported_and_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "get", lambda url, **k: (calls.append(1), Resp(500, None))[1])
    assert pdm.fetch_clingen("TP53")["classification"] == "" and "ClinGen" in pdm.FETCH_ERRORS
    n = len(calls); pdm.fetch_clingen("TP53")
    assert len(calls) > n


# ---------------------------------------------------------------- diagnostics
def test_diagnostics_never_raises_and_flags_missing_key(monkeypatch):
    def down(url, **k): raise requests.ConnectionError("no network")
    monkeypatch.setattr(requests, "get", down); monkeypatch.setattr(requests, "post", down)
    rows = pdm.source_diagnostics("TP53", "P04637")
    assert len(rows) == 8 and not any(r["ok"] for r in rows[:7])
    assert rows[-1]["source"] == "NCBI API key" and "NCBI_API_KEY" in rows[-1]["detail"]


def test_diagnostics_reports_success(monkeypatch):
    g, p, st = ot_router()
    def get(url, **k):
        if "mygene" in url or "rest.ensembl" in url: return g(url, **k)
        if "gene-validity" in url: return Resp(200, None, text=CSV)
        if "esearch" in url: return Resp(200, {"esearchresult": {"count": "123"}})
        return Resp(200, {"comments": [{"commentType": "ALTERNATIVE PRODUCTS", "isoforms": [{}, {}]}]})
    def post(url, **k):
        return Resp(200, V5) if "dgidb" in url else p(url, **k)
    monkeypatch.setattr(requests, "get", get); monkeypatch.setattr(requests, "post", post)
    rows = {r["source"]: r for r in pdm.source_diagnostics("TP53", "P04637")}
    assert rows["DGIdb (v5 GraphQL)"]["ok"] and "3 interactions" in rows["DGIdb (v5 GraphQL)"]["detail"]
    assert rows["Open Targets: tractability"]["ok"] and rows["ClinGen validity download"]["ok"] and rows["UniProt isoforms"]["detail"] == "2 isoforms"


# ---------------------------------------------------------------- batched drug lookup and the GPCRdb entry name
def test_dgidb_many_uses_one_request_for_the_whole_panel(monkeypatch):
    calls = []
    body = {"data": {"genes": {"nodes": [
        {"name": "PTGER4", "interactions": [{"drug": {"name": "GRAPIPRANT"}, "interactionScore": 2, "interactionTypes": [{"type": "antagonist"}], "sources": [{"sourceDbName": "ChEMBL"}]},
                                            {"drug": {"name": "grapiprant"}, "interactionScore": 1, "interactionTypes": [], "sources": []}]},
        {"name": "ADORA2A", "interactions": []}]}}}
    monkeypatch.setattr(requests, "post", lambda url, **k: (calls.append(k["json"]["variables"]["names"]), Resp(200, body))[1])
    out = pdm.fetch_dgidb_many(("ptger4", "adora2a", "ptger2"))
    assert len(calls) == 1 and calls[0] == ["PTGER4", "ADORA2A", "PTGER2"]
    assert [d["drug"] for d in out["PTGER4"]] == ["GRAPIPRANT"] and out["PTGER4"][0]["type"] == "antagonist" and out["ADORA2A"] == [] and "PTGER2" not in out


def test_dgidb_many_failure_is_reported_and_not_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(requests, "post", lambda url, **k: (calls.append(1), Resp(200, {"errors": [{"message": "boom"}]}))[1])
    assert pdm.fetch_dgidb_many(("A",)) == {} and "DGIdb" in pdm.FETCH_ERRORS
    pdm.fetch_dgidb_many(("A",))
    assert len(calls) == 2
    assert pdm.fetch_dgidb_many(()) == {}


def test_gpcrdb_is_queried_by_entry_name_not_bare_gene_symbol(monkeypatch):
    seen = []
    def get(url, **k):
        seen.append(url)
        return Resp(200, {"family": "Adrenoceptors", "receptor_class": "Class A"}) if "adrb2_human" in url else Resp(404, {})
    monkeypatch.setattr(requests, "get", get)
    pdm.fetch_gpcrdb.clear()
    out = pdm.fetch_gpcrdb("ADRB2")
    assert out.get("confirmed_gpcr") and any("/protein/adrb2_human/" in u for u in seen) and not any(u.endswith("/protein/adrb2/") for u in seen)
