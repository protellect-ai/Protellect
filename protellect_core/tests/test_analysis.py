import copy
import pytest

import protellect_data as s
from protellect_core.adapters import Bundle, build_bundle, norm_sig, parse_consequence, parse_position, stars_from_review, mean_plddt
from protellect_core.analysis import (body_systems, defect_claims, genetic_thresholds, possibility, rank_diseases, rank_variants, strategy_options, variant_plan)
from protellect_core.evidence import Claim, Proof, has_proof, truth_gate
from protellect_core.validation import validate, validate_all


def session(gene="TP53", uid="P04637", **over):
    ss = {"gene": gene, "uid": uid, "pdata": s.fetch_uniprot(gene), "cv": s.fetch_clinvar(gene), "scored": [], "gnomad": s.fetch_gnomad(),
          "string": s.fetch_string_interactions(), "drugs": s.fetch_dgidb(), "ot": s.fetch_opentargets(), "am": s.fetch_alphamissense("x"),
          "clingen": s.fetch_clingen(), "trials": s.fetch_clinical_trials(), "abstracts": s.fetch_pubmed_abstracts(), "hotspots": []}
    ss.update(over)
    return ss


@pytest.fixture
def b():
    return build_bundle(session())


def test_normalisers():
    assert norm_sig("Pathogenic/Likely pathogenic") == "pathogenic"
    assert norm_sig("Likely pathogenic") == "likely pathogenic"
    assert norm_sig("Benign/Likely benign") == "benign"
    assert norm_sig("Conflicting interpretations of pathogenicity") == "conflicting"
    assert norm_sig("", 4) == "likely pathogenic" and norm_sig("", 0) == "benign"
    assert stars_from_review("criteria provided, multiple submitters, no conflicts") == 2
    assert stars_from_review("reviewed by expert panel") == 3
    assert parse_position({"title": "NM_1(G):c.742C>T (p.Arg248Trp)"}) == 248
    assert parse_consequence({"title": "c.1A>G (p.Arg248Trp)"}) == "missense"
    assert parse_consequence({"title": "c.100C>T (p.Gln34Ter)"}) == "nonsense"
    assert parse_consequence({"title": "c.100del (p.Lys34fs)"}) == "frameshift"


def test_alphamissense_nested_shape_is_handled_not_summed(b):
    assert len(b.am) == 393 and all(isinstance(v, dict) for v in b.am.values())
    assert any(v.am_score is not None for v in b.variants)           # the shape that crashed the original is parsed correctly


def test_ot_known_drugs_accepts_int_or_list():
    as_int = build_bundle(session(ot={"tractability": {"Small molecule": True}, "known_drugs": 3}))
    as_list = build_bundle(session(ot={"tractability": {}, "known_drugs": [{"name": "X", "phase": 2}]}))
    assert as_int.n_known_drugs == 3 and as_list.n_known_drugs == 1 and as_list.drugs[-1].source == "Open Targets"


def test_empty_session_is_safe_and_audited():
    e = build_bundle({})
    assert not e.loaded and e.audit == []
    thin = build_bundle(session(cv={}, string=[], drugs=[], ot={}, gnomad={}, am={}, clingen={}))
    assert thin.loaded and any("returned nothing" in a.note for a in thin.audit)


def test_every_ranked_disease_has_proof(b):
    ds = rank_diseases(b)
    assert [d.text for d in ds][0].startswith("Li-Fraumeni")
    assert all(has_proof(d) for d in ds) and all(d.score > 0 for d in ds)
    assert ds[0].score >= ds[-1].score


def test_context_boosts_but_flags_transparently(b):
    class Ctx: disease = "hepatocellular carcinoma"
    base = {d.tags["disease"]: d.score for d in rank_diseases(b)}
    boosted = {d.tags["disease"]: (d.score, d.tags["context_flag"]) for d in rank_diseases(b, Ctx())}
    assert boosted["Hepatocellular carcinoma"][0] == base["Hepatocellular carcinoma"] + 1.5 and boosted["Hepatocellular carcinoma"][1]


def test_defects_mechanism_requires_both_signals(b):
    claims = defect_claims(b)
    assert claims and all(has_proof(c) for c in claims)
    assert not any(c.tags.get("mechanism") == "loss-of-function" for c in claims)        # stand-in variants are missense, pLI 0
    lof = copy.deepcopy(b)
    for v in lof.variants:
        if v.is_plp: v.consequence = "nonsense"
    lof.constraint["pLI"] = 0.99
    assert any(c.tags.get("mechanism") == "loss-of-function" for c in defect_claims(lof))


def test_possibility_is_transparent_and_honest_about_gaps(b):
    p = possibility(b)
    assert p["level"] in ("HIGH", "MODERATE", "LOW") and 0 <= p["pct"] <= 100 and p["components"]
    assert all(c["rule"] and c["proof"].source for c in p["components"])
    thin = possibility(build_bundle(session(cv={}, gnomad={}, ot={}, clingen={}, am={}, string=[], drugs=[], trials=[], abstracts=[])))
    assert thin["level"] == "INSUFFICIENT DATA"


def test_strategy_rules_need_triggers(b):
    out = strategy_options(b, defect_claims(b), orphan=False)
    assert all(has_proof(c) and c.kind == "rule" and c.basis for c in out)
    assert not any("Deorphan" in c.text for c in out)
    assert any("Deorphan" in c.text for c in strategy_options(b, [], orphan=True))


def test_thresholds_report_unavailable_not_invented():
    t = genetic_thresholds(build_bundle(session(gnomad={})))
    assert next(r for r in t if r["metric"] == "pLI")["status"] == "unavailable"


def test_body_systems_are_labelled_as_lookups(b):
    bs = body_systems(b, rank_diseases(b))
    assert bs and all(c.kind == "rule" and "keyword" in c.basis for c in bs)
    assert any(c.tags["system"] == "Cancer predisposition" for c in bs)


def test_variant_plan_branches_on_consequence(b):
    v = next(x for x in rank_variants(b))
    assert len(variant_plan(v, b)) == 5
    v.consequence = "nonsense"
    assert any(st["step"] == "Test expression" for st in variant_plan(v, b))


def test_truth_gate_withholds_unproven_claims():
    good = Claim("ok", [Proof("ClinVar", "n=3", "u")])
    no_proof = Claim("bare assertion")
    rule_without_basis = Claim("rule", [Proof("ClinVar", "x")], kind="rule")
    rule_only_rule_proofs = Claim("rule", [Proof("Rule", "x", kind="rule")], kind="rule", basis="b")
    shown, withheld = truth_gate([good, no_proof, rule_without_basis, rule_only_rule_proofs])
    assert shown == [good] and len(withheld) == 3


def test_ml_validation_flags_constraint_mismatch_and_single_source(b):
    b.constraint.update({"pLI": 0.0, "oe_lof_upper": 0.9})
    c = Claim("LoF mechanism", [Proof("ClinVar", "n")], kind="inference", basis="why", tags={"mechanism": "loss-of-function", "n_supporting": 2})
    validate(c, b)
    checks = {x["check"] for x in c.counters}
    assert {"constraint_mismatch", "thin_evidence", "not_measured"} <= checks and c.verdict == "contested"
    strong = validate(Claim("x", [Proof("ClinVar", "a"), Proof("UniProt", "b")], tags={"n_supporting": 9}), b)
    assert strong.verdict == "holds up"
    assert validate(Claim("none"), b).verdict == "contested"        # no proof => never "holds up"
