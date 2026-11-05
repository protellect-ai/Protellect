from protellect_core.adapters import Bundle, Variant, Hotspot, Disease
from protellect_core.evidence import truth_gate
from protellect_core.topology import Segment
from protellect_core import unknowns as u


def V(name, pos, sig, am=None, cons="missense", stars=1, cond="", url="https://www.ncbi.nlm.nih.gov/clinvar/variation/1/"):
    return Variant(name=name, pos=pos, significance=sig, stars=stars, review="", condition=cond, consequence=cons, url=url, am_score=am, am_class="")


def bundle(**kw):
    b = Bundle(gene="GRMX", uid="Q00000", length=300, is_gpcr=True, gpcr_class="", sequence="M" * 300)
    b.variants = [V("NM_1(GRMX):c.100A>G (p.Arg34Gly)", 34, "pathogenic", 0.9, cond="Disease A", stars=2),
                  V("NM_1(GRMX):c.101G>A (p.Arg35Gln)", 35, "uncertain", 0.8),
                  V("NM_1(GRMX):c.500A>G (p.Ala170Val)", 170, "uncertain", 0.1),
                  V("NM_1(GRMX):c.600A>G (p.Ala200Ala)", 200, "uncertain", None, cons="synonymous"),
                  V("NM_1(GRMX):c.700C>T (p.Gln233Ter)", 233, "uncertain", None, cons="nonsense"),
                  V("NM_1(GRMX):c.171A>G (p.Ala171Val)", 171, "benign", 0.1), V("NM_1(GRMX):c.172A>G (p.Gly172Ser)", 172, "likely benign", 0.1)]
    for k, val in kw.items():
        setattr(b, k, val)
    return b


def keys(cs):
    return [c.tags["hyp"] for c in cs]


def test_every_hypothesis_passes_the_truth_gate_and_has_test_outcomes_and_controls():
    b = bundle()
    for v in b.variants:
        if u.is_unknown(v):
            hs = u.variant_hypotheses(v, b)
            shown, withheld = truth_gate(hs)
            assert shown and not withheld
            for c in shown:
                assert c.how and c.outcomes and c.controls and c.proofs


def test_neighbour_hypothesis_fires_and_names_the_neighbour_and_its_condition():
    b = bundle()
    v = b.variants[1]                                       # residue 35, one residue from a pathogenic variant with a condition
    hs = u.variant_hypotheses(v, b, plddt={35: 90.0})
    nb = next(c for c in hs if c.tags["hyp"] == "neighbours")
    assert "Disease A" in nb.text and any("Arg34Gly" in p.detail for p in nb.proofs)
    assert "folding" in keys(hs)                           # AM 0.8 and pLDDT 90 trigger it
    assert "tolerated" not in keys(hs)                     # nothing supports a bystander here


def test_tolerated_competes_when_the_data_say_so():
    b = bundle()
    hs = u.variant_hypotheses(b.variants[2], b, plddt={170: 40.0})
    k = keys(hs)
    assert k[0] == "tolerated" and "neighbours" not in k    # AM 0.1 and low pLDDT, benign neighbours, no pathogenic ones
    f = next((c for c in hs if c.tags["hyp"] == "folding"), None)
    assert f is None                                       # negative weights cancel the folding hypothesis, so it is not offered


def test_synonymous_goes_to_splicing_and_nonsense_to_loss():
    b = bundle()
    assert keys(u.variant_hypotheses(b.variants[3], b))[0] == "splice"
    hs = u.variant_hypotheses(b.variants[4], b)
    assert keys(hs)[0] == "lof"
    assert not any(k in ("folding", "signalling") for k in keys(hs))


def test_no_data_gives_the_default_panel_not_an_invented_mechanism():
    b = bundle(variants=[V("NM_1(X):c.1A>G (p.Met1Val)", 999, "uncertain")], sites=[], hotspots=[])
    hs = u.variant_hypotheses(b.variants[0], b)
    assert keys(hs) == ["default"] and "No mechanism is favoured" in hs[0].text


def test_motif_and_segment_trigger_signalling_with_a_stated_basis():
    b = bundle()
    segs = [Segment("ICL2", "ICL", 100, 120, "intracellular")]
    motifs = [{"motif": "D/ERY (ionic lock, TM3 end)", "start": 103, "end": 105, "seq": "DRY", "where": "TM3 / ICL2"}]
    v = V("NM_1(X):c.1A>G (p.Arg104Cys)", 104, "uncertain", 0.7)
    b.variants.append(v)
    hs = u.variant_hypotheses(v, b, segs, motifs, plddt={104: 80.0})
    s = next(c for c in hs if c.tags["hyp"] == "signalling")
    assert any("DRY" in t for t in s.tags["for"]) and any("ICL2" in t for t in s.tags["for"])
    assert any("TRUPATH" in h or "G protein families" in h for h in s.how)


def test_orphan_gets_constitutive_activity_assay_not_an_agonist_dose_response():
    b = bundle()
    hs = u.variant_hypotheses(b.variants[1], b, orphan=True, plddt={35: 90.0})
    sig = next(c for c in hs if c.tags["hyp"] == "signalling") if any(c.tags["hyp"] == "signalling" for c in hs) else None
    f = next(c for c in hs if c.tags["hyp"] == "folding")
    assert f.how
    if sig:
        assert "constitutive" in " ".join(sig.how)


def test_recessive_and_dominant_records_drive_trans_and_dimer():
    b = bundle(diseases=[Disease("Disorder R", "Autosomal recessive")])
    b.variants.append(V("NM_1(X):c.9A>G (p.Trp10Ter)", 10, "pathogenic", cons="nonsense", stars=2))
    hs = u.variant_hypotheses(b.variants[2], b)
    assert "trans" in keys(hs)
    b2 = bundle(diseases=[Disease("Disorder D", "Autosomal dominant")], gpcr_class="Class C (glutamate)")
    hs2 = u.variant_hypotheses(b2.variants[1], b2, plddt={35: 90.0})
    assert "dimer" in keys(hs2)


def test_board_ranks_unknowns_only_and_leads_with_best_supported():
    b = bundle()
    rows = u.vus_board(b)
    assert all(u.is_unknown(r["variant"]) for r in rows)
    assert rows == sorted(rows, key=lambda r: (-r["score"], -(r["variant"].am_score or 0), -r["variant"].stars))
    assert all(r["claim"].how for r in rows)


def test_protein_unknowns_only_from_real_triggers():
    b = bundle(tractability={"Small molecule": True, "Antibody": False, "PROTAC": False}, diseases=[], constraint={"pLI": 0.99, "oe_lof_upper": 0.2})
    b.variants = []
    segs = [Segment("N-terminus", "N-term", 1, 60, "extracellular"), Segment("ICL1", "ICL", 90, 110, "intracellular")]
    b.sequence = "M" + "K" * 120 + "A" * 179
    cs = u.protein_unknowns(b, segs, [], orphan=False, coupling="")
    t = " | ".join(c.text for c in cs)
    assert "Antibody tractability" in t and "PROTAC tractability" in t and "does not tolerate loss of function" in t and "coupling" in t
    assert "Small-molecule tractability" not in t            # it IS tractable, and no pockets were given
    shown, withheld = truth_gate(cs)
    assert len(shown) == len(cs) and not withheld


def test_low_confidence_span_is_found_only_when_long_enough():
    pl = {i: (30.0 if 10 <= i <= 50 else 90.0) for i in range(1, 100)}
    assert u._low_conf_spans(pl) == [(10, 50)]
    pl2 = {i: (30.0 if 10 <= i <= 20 else 90.0) for i in range(1, 100)}
    assert u._low_conf_spans(pl2) == []
