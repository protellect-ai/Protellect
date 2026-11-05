import protellect_data as s
from protellect_core.adapters import build_bundle
from protellect_core.adme import admet_rules, fetch_faers, fetch_properties, parse_faers, parse_pubchem
from protellect_core.analysis import body_systems, defect_claims, possibility, rank_diseases
from protellect_core.context import Context, disease_context_claims, factor_claims, medication_claims
from protellect_core.evidence import has_proof
from protellect_core.pharma import scenarios
from protellect_core.routing import priorities
from protellect_core.tests.test_analysis import session


class R:
    def __init__(self, code, body): self.status_code, self._b = code, body
    def json(self): return self._b


def _b(**o): return build_bundle(session(**o))


def test_context_from_session_and_summary():
    c = Context.from_session({"ctx_disease": "colitis", "pt_comorbid": "type 2 diabetes\nhypertension", "pt_meds": "metformin, nutlin-3", "pt_sex": "?", "ctx_factors": ["Hypoxia"]})
    assert c.tailored and c.comorbid == ["type 2 diabetes", "hypertension"] and c.sex == "" and "disease: colitis" in c.summary()
    assert not Context.from_session({}).tailored


def test_medication_matches_only_real_drug_records():
    b = _b()
    assert medication_claims(Context(meds=["nutlin-3"]), b)[0].proofs[0].source
    assert medication_claims(Context(meds=["aspirin"]), b) == []


def test_factor_claims_require_real_partner_overlap():
    b = _b()
    got = factor_claims(Context(factors=["DNA damage", "Hypoxia"]), b)
    assert [c.tags["factor"] for c in got] == ["DNA damage"] and all(has_proof(c) for c in got)     # stand-in partners include ATM, CHEK2, BRCA1


def test_comorbidity_flag_links_to_associated_disease():
    b = _b()
    flags = disease_context_claims(Context(comorbid=["hepatocellular carcinoma"]), rank_diseases(b))
    assert flags and "matches your listed comorbidity" in flags[0].text


def test_pubchem_parse_and_rules():
    js = {"PropertyTable": {"Properties": [{"CID": 5, "MolecularWeight": "400.5", "XLogP": 3.2, "TPSA": 70.1, "HBondDonorCount": 2, "HBondAcceptorCount": 6, "RotatableBondCount": 5}]}}
    p = parse_pubchem(js)
    rules = {r["test"]: r["pass"] for r in admet_rules(p)}
    assert all(rules.values()) and len(rules) == 3
    big = admet_rules(parse_pubchem({"PropertyTable": {"Properties": [{"MolecularWeight": "900", "XLogP": 7, "TPSA": 220, "HBondDonorCount": 9, "HBondAcceptorCount": 15, "RotatableBondCount": 20}]}}))
    assert not any(r["pass"] for r in big)
    assert parse_pubchem({}) is None and fetch_properties("x", lambda u, timeout: (_ for _ in ()).throw(RuntimeError("down"))) is None


def test_faers_parse_and_fetch():
    assert parse_faers({"results": [{"term": "NAUSEA", "count": 12}]}) == [("Nausea", 12)] and parse_faers({}) == []
    def get(url, timeout):
        return R(200, {"results": [{"term": "HEADACHE", "count": 5}]}) if "count=" in url else R(200, {"meta": {"results": {"total": 321}}})
    assert fetch_faers("drug", get) == {"top": [("Headache", 5)], "total": 321}
    assert fetch_faers("drug", lambda u, timeout: R(404, {})) is None


def test_scenarios_are_evidence_tagged_and_direction_aware():
    b = _b()
    for v in b.variants:
        if v.is_plp: v.consequence = "nonsense"
    b.constraint["pLI"] = 0.99
    d = rank_diseases(b); df = defect_claims(b); sy = body_systems(b, d)
    sc = scenarios(b, df, sy, d)
    assert sc and all(has_proof(c) for c in sc)
    top = sc[0]
    assert top.tags["direction"] == "activate"                 # LoF mechanism => restoring function ranks first
    inhibit = next(c for c in sc if c.tags["direction"] == "inhibit")
    assert inhibit.tags["risk"] == "HIGHER" and inhibit.tags["phenocopy"]


def test_routing_levels_and_destinations():
    b = _b()
    p = priorities(b, possibility(b), defect_claims(b))
    assert p[0].level in ("PRIORITIZE", "INVESTIGATE", "DEPRIORITIZE", "DATA GAP") and p[0].goto
    assert any(x.goto == "Triage" for x in p) and any(x.goto == "Druggable hotspots" for x in p)
    empty = priorities(build_bundle({}), None, [])
    assert empty[0].level == "DATA GAP"
    thin = build_bundle(session(cv={}, gnomad={}, ot={}, clingen={}, am={}, string=[], drugs=[], trials=[], abstracts=[]))
    assert priorities(thin, possibility(thin), [])[0].level == "DATA GAP"
