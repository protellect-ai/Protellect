"""Unknowns: what a variant of uncertain significance, an 'Unknown' tractability, or an empty disease list might actually be, and how to find out.

What this is: a rule-based hypothesis generator. A hypothesis is only offered when real data from this protein triggers it (a ClinVar record,
an AlphaMissense score, a UniProt feature, an AlphaFold confidence value, a geometric pocket, a neighbouring pathogenic variant). Each one comes
with the experiment, what each possible result would mean, and the controls that make the result interpretable.

What this is NOT: a pathogenicity call. The 'evidence score' adds design-choice weights (shown in WEIGHTS and on screen) to rank hypotheses against each
other for the same variant; it is not a probability, and it is never used to reclassify a variant. Under ACMG/AMP only functional or genetic evidence
moves a VUS (Richards 2015); computational scores are supporting evidence at most.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from .adapters import Bundle, Variant
from .evidence import Claim, Proof
from .topology import Segment, segment_of

# --------------------------------------------------------------------------------------------- sources
CITE = {
    "acmg": Proof("ACMG/AMP guidelines", "Richards et al. 2015, Genet Med 17:405-424 (PM1, PM5, PP3, BP4, PS3/BS3)", "https://doi.org/10.1038/gim.2015.30", "literature"),
    "am": Proof("AlphaMissense", "Cheng et al. 2023, Science 381:eadg7492 (>0.564 likely pathogenic, <0.34 likely benign)", "https://doi.org/10.1126/science.adg7492", "literature"),
    "brnich": Proof("ClinGen SVI functional-evidence guidance", "Brnich et al. 2019, Genome Med 12:3: how much a functional assay counts depends on the validated pathogenic and benign controls it was calibrated on",
                    "https://doi.org/10.1186/s13073-019-0690-2", "literature"),
    "pejaver": Proof("ClinGen SVI computational-evidence calibration", "Pejaver et al. 2022, Am J Hum Genet 109:2163: calibrated thresholds for using predictors as PP3/BP4 evidence",
                     "https://doi.org/10.1016/j.ajhg.2022.10.013", "literature"),
    "hauser": Proof("GPCR variant landscape", "Hauser et al. 2018, Cell 172:41-54: missense variants across GPCR drug targets and their positions", "https://doi.org/10.1016/j.cell.2017.11.033", "literature"),
    "trupath": Proof("TRUPATH", "Olsen et al. 2020, Nat Chem Biol 16:841: BRET biosensors for G protein activation across families", "https://doi.org/10.1038/s41589-020-0535-8", "literature"),
    "tango": Proof("PRESTO-Tango", "Kroeze et al. 2015, Nat Struct Mol Biol 22:362: beta-arrestin recruitment assay for the GPCRome", "https://doi.org/10.1038/nsmb.3014", "literature"),
    "alphafold": Proof("AlphaFold", "Jumper et al. 2021, Nature 596:583: pLDDT below 50 is usually unstructured or unreliable", "https://doi.org/10.1038/s41586-021-03819-2", "literature"),
    "spliceai": Proof("SpliceAI", "Jaganathan et al. 2019, Cell 176:535: in-silico splice effect predictor (a prediction, to be confirmed by RNA)", "https://doi.org/10.1016/j.cell.2018.12.015", "literature"),
}

# Design-choice weights. Shown to the user. Positive = evidence for the hypothesis, negative = evidence against.
WEIGHTS: Dict[str, List[Tuple[str, float, str]]] = {
    "folding": [("AlphaMissense above 0.564", 2.0, "predicted damaging"), ("AlphaMissense 0.34 to 0.564", 0.5, "ambiguous"), ("AlphaFold pLDDT 70 or more at the residue", 1.0, "structured, so packing matters"),
                ("residue inside a transmembrane helix", 1.0, "helix packing"), ("AlphaMissense below 0.34", -2.0, "predicted tolerated"), ("pLDDT below 50", -1.5, "likely disordered")],
    "signalling": [("inside a conserved class A motif", 2.5, "microswitch"), ("on the intracellular face (ICL1-3, C-terminus)", 1.5, "G protein / arrestin surface"), ("in TM3, TM6 or TM7", 1.0, "activation helices"),
                   ("AlphaMissense above 0.564", 1.0, "predicted damaging"), ("AlphaMissense below 0.34", -1.0, "predicted tolerated")],
    "binding": [("annotated binding site within 2 residues", 3.0, "UniProt feature"), ("lines a candidate pocket (top 3, geometry only)", 2.0, "pocket module"),
                ("in a large extracellular domain", 1.5, "ligand-binding domain of class C and adhesion receptors"), ("AlphaMissense above 0.564", 0.5, "predicted damaging")],
    "dimer": [("receptor has a large extracellular domain or is class C", 1.5, "class C receptors act as dimers"), ("dominant inheritance recorded", 1.5, "UniProt disease record"),
              ("missense in the extracellular domain or transmembrane region", 0.5, "interface candidates")],
    "neighbours": [("another pathogenic variant at the same residue", 3.0, "ACMG PM5-like"), ("residue sits in a variant hotspot", 2.0, "ACMG PM1-like"),
                   ("1 or 2 pathogenic variants within 5 residues", 1.5, "local clustering"), ("3 or more pathogenic variants within 5 residues", 2.5, "local clustering")],
    "splice": [("synonymous or intronic or splice-site notation", 3.0, "can act through RNA, not protein")],
    "lof": [("nonsense, frameshift or canonical splice change", 3.0, "expected to remove protein")],
    "trans": [("recessive inheritance recorded", 2.0, "UniProt disease record"), ("a pathogenic loss-of-function variant exists elsewhere in the gene", 1.0, "ClinVar")],
    "tolerated": [("AlphaMissense below 0.34", 2.0, "predicted tolerated"), ("pLDDT below 50", 1.5, "likely disordered"), ("2 or more benign neighbours and no pathogenic ones within 5 residues", 1.5, "ClinVar")],
}


def _uni(b: Bundle) -> str:
    return f"https://www.uniprot.org/uniprotkb/{b.uid}/entry" if b.uid else "https://www.uniprot.org/"


def _cv(b: Bundle) -> str:
    return f"https://www.ncbi.nlm.nih.gov/clinvar/?term={b.gene}%5Bgene%5D"


def plddt_map(pdb: str) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for line in (pdb or "").splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try:
                out[int(line[22:26])] = float(line[60:66])
            except ValueError:
                pass
    return out


def _short(v: Variant) -> str:
    m = re.search(r"\(p\.[^)]+\)", v.name)
    return m.group(0).strip("()") if m else v.name[-30:]


def _assays(b: Bundle, orphan: bool, coupling: str) -> Dict[str, str]:
    """Names of the readouts for this kind of protein. A GPCR gets receptor assays; anything else gets generic ones."""
    if b.is_gpcr:
        sig = ("constitutive signalling (basal cAMP, Ca2+ or NFAT-RE reporter against an empty-vector control), because no confirmed ligand exists" if orphan else
               f"agonist dose-response in the {coupling} pathway (GloSensor cAMP, Ca2+ or IP1) plus beta-arrestin recruitment" if coupling else
               "agonist dose-response across G protein families (TRUPATH BRET) plus beta-arrestin recruitment (PRESTO-Tango or NanoBiT)")
        return {"surface": "N-terminally HA or FLAG tagged receptor in HEK293 cells: surface versus total staining (flow cytometry or cell-surface ELISA), with empty vector and wild type",
                "signal": sig,
                "bind": ("a tracer or radioligand saturation binding (Kd, Bmax); there is no known ligand, so use a conformational antibody or a tagged-receptor pull-down instead" if orphan
                         else "saturation binding with a labelled ligand (radioligand or NanoBRET tracer) to get Kd and Bmax, normalised to surface expression"),
                "pos_note": "a P/LP missense variant from ClinVar"}
    return {"surface": "expression and stability: Western blot of total protein, cycloheximide chase for half-life, and a thermal-shift or CETSA read-out against wild type",
            "signal": "the protein's own activity assay (enzymatic, binding or reporter) against wild type",
            "bind": "binding of its known partner or ligand (co-IP, SPR or ITC) against wild type",
            "pos_note": "a P/LP missense variant from ClinVar"}


def _controls(v: Variant, b: Bundle, assay_pos: str) -> List[str]:
    pos = sorted([x for x in b.plp if x.consequence == "missense" and x.pos and x.name != v.name], key=lambda x: (abs((x.pos or 0) - (v.pos or 0)), -x.stars))[:2]
    neg = sorted([x for x in b.variants if x.significance in ("benign", "likely benign") and x.consequence == "missense" and x.pos], key=lambda x: (-x.stars, abs((x.pos or 0) - (v.pos or 0))))[:2]
    out = ["Wild type and empty vector in every plate; three or more independent transfections; express every construct at a matched level (surface and total)."]
    out.append("Positive control (should fail): " + (", ".join(_short(x) + f" (residue {x.pos}, {x.stars}★)" for x in pos) if pos else f"no missense P/LP variant retrieved, so use {assay_pos} from the literature or a deliberately dead mutant of a conserved motif residue") + ".")
    out.append("Negative control (should behave like wild type): " + (", ".join(_short(x) + f" (residue {x.pos}, {x.significance})" for x in neg) if neg else "no benign missense variant retrieved, so use a conservative substitution at a poorly conserved site") + ".")
    out.append("Call the variant abnormal only if it falls outside the range of your benign controls and inside the range of your pathogenic ones; the strength of the evidence depends on how many validated controls the assay was calibrated on (Brnich 2019).")
    return out


def _motif_near(motifs: Sequence[dict], pos: int, pad: int = 2) -> Optional[dict]:
    return next((m for m in motifs or [] if m["start"] - pad <= pos <= m["end"] + pad), None)


def _cls_c(b: Bundle) -> bool:
    return bool(re.search(r"\bclass\s*c\b|\bc\b\s*\(|glutamate", (b.gpcr_class or "").lower()))


def _ecd_len(b: Bundle, segs: Optional[Sequence[Segment]]) -> int:
    best = 0
    for s in segs or []:
        if s.kind == "N-term":
            best = max(best, s.length)
    for d in b.domains:
        if "extracellular" in f"{d.get('desc', '')} {d.get('type', '')}".lower():
            best = max(best, int(d["end"]) - int(d["start"]) + 1)
    return best


def _fmt_neighbours(vs: Sequence[Variant]) -> str:
    return ", ".join(f"{_short(x)} ({x.significance}, {x.stars}★, {x.condition[:40] or 'condition not given'})" for x in vs[:4])


class _Ev:
    """Collects the triggers of one hypothesis: a running score, the data proofs, and the evidence for and against in plain words."""

    def __init__(self, key: str):
        self.key, self.score, self.proofs, self.fors, self.against = key, 0.0, [], [], []

    def add(self, w: float, text: str, proof: Optional[Proof] = None) -> None:
        self.score += w
        (self.fors if w > 0 else self.against).append(text)
        if proof is not None:
            self.proofs.append(proof)

    @property
    def fired(self) -> bool:
        return bool(self.fors)


def variant_hypotheses(v: Variant, b: Bundle, segs: Optional[Sequence[Segment]] = None, motifs: Optional[Sequence[dict]] = None, pockets: Optional[Sequence[dict]] = None,
                       orphan: bool = False, coupling: str = "", plddt: Optional[Dict[int, float]] = None) -> List[Claim]:
    """Ranked hypotheses for what this variant does, each with the test, the meaning of each result, and controls. Best first; a competing 'tolerated' hypothesis is always considered."""
    pos = v.pos
    pl = (plddt or {}).get(pos) if pos else None
    seg = segment_of(list(segs) if segs else None, pos) if pos else ""
    dom = b.domain_at(pos) if pos else ""
    am = v.am_score
    ass = _assays(b, orphan, coupling)
    cvp = Proof("ClinVar", f"{v.name[-60:]}: {v.significance}, {v.stars} star(s), consequence {v.consequence}", v.url if (v.url or "").startswith("http") else _cv(b))
    amp = Proof("AlphaMissense", f"worst-case substitution at residue {pos}: {am:.2f} ({v.am_class or 'class not given'})", "https://alphamissense.hegelab.org/") if am is not None else None
    plp_ = Proof("AlphaFold DB (pLDDT)", f"pLDDT {pl:.0f} at residue {pos}", f"https://alphafold.ebi.ac.uk/entry/{b.uid}") if pl is not None else None
    segp = Proof("UniProt topology", f"residue {pos} lies in {seg}" + (f" ({dom})" if dom else ""), _uni(b)) if seg else None
    miss = v.consequence in ("missense", "inframe indel")
    out: List[Claim] = []
    near = [x for x in b.plp if x.pos and pos and x.name != v.name and abs(x.pos - pos) <= 5]
    same = [x for x in near if x.pos == pos]
    benign_near = [x for x in b.variants if x.significance in ("benign", "likely benign") and x.pos and pos and abs(x.pos - pos) <= 5]
    hot = next((h for h in b.hotspots if pos and h.start <= pos <= h.end), None)
    ctrl = _controls(v, b, ass["pos_note"])

    def finish(ev: _Ev, text: str, basis: str, how: List[str], outcomes: List[str], extra: Sequence[Proof] = (), disease: str = "") -> None:
        if not ev.fired:
            return
        proofs = [cvp] + [p for p in ev.proofs if p is not None] + list(extra) + [CITE["acmg"], CITE["brnich"]]
        seen, uniq = set(), []
        for p in proofs:
            if (p.source, p.detail) not in seen:
                seen.add((p.source, p.detail)); uniq.append(p)
        out.append(Claim(text=text, proofs=uniq, kind="rule", basis=basis, score=round(ev.score, 2),
                         tags={"hyp": ev.key, "for": list(ev.fors), "against": list(ev.against), "n_supporting": len(ev.fors), "disease": disease},
                         how=how, outcomes=outcomes, controls=ctrl))

    # 1. folding / trafficking
    if miss and pos:
        e = _Ev("folding")
        if am is not None and am > 0.564: e.add(2.0, f"AlphaMissense {am:.2f} (above 0.564)", amp)
        elif am is not None and am >= 0.34: e.add(0.5, f"AlphaMissense {am:.2f} (ambiguous band)", amp)
        elif am is not None: e.add(-2.0, f"AlphaMissense {am:.2f} (below 0.34, predicted tolerated)", amp)
        if pl is not None and pl >= 70: e.add(1.0, f"structured region (pLDDT {pl:.0f})", plp_)
        elif pl is not None and pl < 50: e.add(-1.5, f"low-confidence, probably disordered region (pLDDT {pl:.0f})", plp_)
        if seg.startswith("TM"): e.add(1.0, f"inside {seg}, where side chains pack against neighbouring helices", segp)
        finish(e, f"{_short(v)} reduces how much receptor reaches the cell surface (misfolding, ER retention or instability)" if b.is_gpcr else f"{_short(v)} destabilises the protein so less of it is present",
               "Missense variants in structured, damaged-looking positions most often act by lowering the amount of working protein before they change its chemistry. This is the first thing to exclude because it changes how every later assay is read.",
               [f"Measure it: {ass['surface']}.", "Repeat at 27-30 C, or with a membrane-permeant ligand or pharmacological chaperone if one exists, to test whether it is a folding problem that can be rescued.",
                "Western blot for the glycosylation pattern (Endo H sensitive bands mean the protein is stuck in the ER)."],
               ["Surface expression below your benign controls and rescued by low temperature or a chaperone: a folding or trafficking defect, and potentially rescuable (that is also a therapeutic angle).",
                "Surface expression low and NOT rescued: more likely a true instability or degradation problem; check half-life with a cycloheximide chase.",
                "Surface expression normal: this is not the mechanism. Go to the signalling and binding hypotheses."])

    # 2. signalling
    if miss and pos:
        e = _Ev("signalling")
        mt = _motif_near(motifs or [], pos)
        if mt: e.add(2.5, f"within 2 residues of the {mt['motif']} motif ({mt['start']}-{mt['end']}, {mt['seq']})", Proof("Sequence motif search", f"{mt['motif']} found at {mt['start']}-{mt['end']} in the UniProt sequence", _uni(b)))
        if seg in ("ICL1", "ICL2", "ICL3", "C-terminus"): e.add(1.5, f"{seg} faces the cytoplasm, where G proteins and arrestins bind", segp)
        if seg in ("TM3", "TM6", "TM7"): e.add(1.0, f"{seg} moves during activation", segp)
        if am is not None and am > 0.564 and e.fired: e.add(1.0, f"AlphaMissense {am:.2f}", amp)
        elif am is not None and am < 0.34 and e.fired: e.add(-1.0, f"AlphaMissense {am:.2f} (predicted tolerated)", amp)
        finish(e, f"{_short(v)} reaches the surface but changes signalling (lost, reduced, increased or biased)" if b.is_gpcr else f"{_short(v)} changes the protein's activity without changing how much there is",
               "Residues in activation helices, conserved motifs and the intracellular face are where receptor-specific effects on coupling occur, independent of expression. Only informative once expression is known to be normal, so always normalise to surface level.",
               [f"Measure it: {ass['signal']}. Normalise every response to surface expression.", "Fit full concentration-response curves rather than a single dose, so potency (EC50) and efficacy (Emax) can be separated.",
                "Include basal activity (no ligand) to catch constitutive activation."],
               ["Emax lower with normal EC50: lost efficacy (coupling or activation). Emax unchanged but EC50 shifted right: lost affinity or potency.",
                "Activity with no ligand ABOVE wild type: constitutive activation (gain of function), which points to a different clinical and drug direction than loss.",
                "One pathway lost and another kept (for example G protein normal, arrestin lost): biased signalling; report it as that, not as loss of function.",
                "Everything within the benign-control range: no signalling effect in this assay; consider the pathway you did not test."])

    # 3. ligand binding
    if miss and pos:
        e = _Ev("binding")
        site = next((s for s in b.sites if s["start"] - 2 <= pos <= s["end"] + 2 and "binding" in f"{s['type']} {s['desc']}".lower()), None)
        if site: e.add(3.0, f"within 2 residues of an annotated {site['type'].lower()}: {site['desc'] or 'no description'} ({site['start']}-{site['end']})", Proof("UniProt feature", f"{site['type']} {site['desc']} {site['start']}-{site['end']}", _uni(b)))
        pk = next((p for p in (pockets or []) if pos in set(p.get("residues", [])) and p.get("rank", 99) <= 3), None)
        if pk: e.add(2.0, f"lines candidate pocket {pk['rank']} (geometry only, not a docking result)", Proof("Pocket module (LIGSITE-style geometry)", f"residue {pos} lines pocket {pk['rank']} on the AlphaFold model", ""))
        if _ecd_len(b, segs) >= 300 and (dom or seg == "N-terminus") and ("extracellular" in dom.lower() or seg == "N-terminus"):
            e.add(1.5, "inside a large extracellular domain, the ligand-binding region of class C and adhesion receptors", Proof("UniProt topology", f"{dom or 'N-terminus'} spans {_ecd_len(b, segs)} residues", _uni(b)))
        if am is not None and am > 0.564 and e.fired: e.add(0.5, f"AlphaMissense {am:.2f}", amp)
        finish(e, f"{_short(v)} changes ligand binding" + (" (the ligand is not known, so this can only be tested indirectly)" if orphan else ""),
               "A residue in or next to a binding site or a lining pocket can change affinity without changing expression. For an orphan receptor there is no ligand to measure, so the reading is indirect.",
               [f"Measure it: {ass['bind']}.", "Compare Kd and Bmax with wild type at matched surface expression: Bmax tracks the amount of receptor, Kd tracks the binding site."],
               ["Kd shifted and Bmax proportional to surface expression: a true binding-site effect.", "Bmax low but Kd normal: this is an expression problem seen through binding (see the trafficking hypothesis).",
                "No binding change but signalling changed: the effect is downstream of binding (see the signalling hypothesis)."])

    # 4. dominant-negative / dimer
    if miss and pos:
        e = _Ev("dimer")
        dom_inh = next((d for d in b.diseases if "dominant" in (d.inheritance or "").lower()), None)
        big = _ecd_len(b, segs)
        if _cls_c(b) or big >= 300: e.add(1.5, f"class C or large-extracellular-domain receptor (extracellular region of {big} residues)" if big else "class C receptor", Proof("UniProt topology", f"extracellular region {big} residues; GPCR class: {b.gpcr_class or 'not recorded'}", _uni(b)))
        if dom_inh: e.add(1.5, f"{dom_inh.name} is recorded with dominant inheritance", Proof("UniProt disease record", f"{dom_inh.name}: {dom_inh.inheritance}", _uni(b)))
        if (e.fors) and (seg.startswith("TM") or "extracellular" in dom.lower() or seg in ("N-terminus", "ECL1", "ECL2", "ECL3")): e.add(0.5, "in a region that could form a dimer interface", segp)
        if len(e.fors) >= 2:
            finish(e, f"{_short(v)} poisons the wild-type partner in a dimer (dominant-negative effect)",
                   "Receptors that signal as dimers can be disabled by a mutant subunit, which would explain dominant disease from a variant that looks mild on its own.",
                   ["Co-express wild type and variant at 1:1 and measure the same signalling read-out as for the variant alone.", "Check whether the variant still dimerises with wild type (BRET or FRET between tagged subunits, or co-immunoprecipitation)."],
                   ["Wild type + variant gives much less than half of wild type alone: dominant-negative. The dimer is the unit to rescue.", "Wild type + variant gives about half of wild type: simple loss of function (haploinsufficiency).",
                    "Wild type + variant is the same as wild type alone: the variant is silent in this assay or does not enter the dimer."])

    # 5. neighbours / disease association
    if pos:
        e = _Ev("neighbours")
        if same: e.add(3.0, f"{len(same)} other pathogenic variant(s) at residue {pos}: {_fmt_neighbours(same)}", Proof("ClinVar", f"pathogenic at the same residue: {_fmt_neighbours(same)}", same[0].url if (same[0].url or "").startswith("http") else _cv(b)))
        if hot: e.add(2.0, f"inside the variant hotspot {hot.start}-{hot.end} ({hot.count} variants, {hot.fold:.1f}x enriched)", Proof("Hotspot analysis (ClinVar)", f"{hot.start}-{hot.end}: {hot.count} variants, {hot.fold:.1f}x", _cv(b)))
        far = [x for x in near if x.pos != pos]
        if len(far) >= 3: e.add(2.5, f"{len(far)} pathogenic variants within 5 residues: {_fmt_neighbours(far)}", Proof("ClinVar", f"{len(far)} P/LP within 5 residues: {_fmt_neighbours(far)}", _cv(b)))
        elif far: e.add(1.5, f"{len(far)} pathogenic variant(s) within 5 residues: {_fmt_neighbours(far)}", Proof("ClinVar", f"{len(far)} P/LP within 5 residues: {_fmt_neighbours(far)}", far[0].url if (far[0].url or "").startswith("http") else _cv(b)))
        conds = sorted({x.condition for x in (same + near) if x.condition and x.condition.lower() not in ("not provided", "not specified")})
        finish(e, f"{_short(v)} causes the same condition as its pathogenic neighbours" + (f" ({'; '.join(c[:50] for c in conds[:3])})" if conds else ""),
               "Under ACMG, a missense change at a residue where a different change is already pathogenic (PM5), or inside a region where pathogenic variants cluster (PM1), is supporting evidence of pathogenicity. It raises the odds; it does not settle them.",
               ["Genetic test: find carriers of this variant and check whether they have the neighbours' phenotype, and whether it co-segregates with disease in the family (ACMG PP1) or is enriched in cases over controls (PS4).",
                "Functional test: run the neighbouring pathogenic variant side by side with this one in the same assay (the neighbour is your positive control).",
                "Ask the submitters: open the ClinVar record and see whether the lab holds phenotype or segregation data it can share."],
               ["Variant behaves like the pathogenic neighbour in the assay AND carriers share the phenotype: strong case for reclassification to likely pathogenic.",
                "Behaves like the neighbour in the assay but carriers have no phenotype: reduced penetrance or a modifier; report both facts.",
                "Behaves like wild type: the neighbours' mechanism does not apply to this residue; the clustering is not informative for this one."],
               disease="; ".join(conds))

    # 6. splice / RNA
    if pos is not None or v.consequence in ("synonymous", "splice", "other"):
        e = _Ev("splice")
        intronic = bool(re.search(r"c\.[\d*-]+[+-]\d+", v.name))
        if v.consequence in ("synonymous", "splice") or intronic:
            e.add(3.0, f"{'synonymous' if v.consequence == 'synonymous' else 'splice-site or intronic'} change: it does not alter the protein sequence directly", Proof("ClinVar", f"{v.name[-60:]} consequence {v.consequence}", v.url if (v.url or "").startswith("http") else _cv(b)))
        finish(e, f"{_short(v)} acts through RNA splicing, not through the amino acid sequence",
               "A change that leaves the protein sequence unchanged can only matter if it alters splicing, stability or translation of the transcript.",
               ["Run SpliceAI as a first, in-silico pass (a prediction only).", "Confirm in RNA: RT-PCR from patient-derived cells, or a minigene splicing assay with wild-type and variant exons.",
                "Sequence the product to see which exon is skipped or which cryptic site is used."],
               ["New or missing bands, or an exon skipped or extended: splicing effect confirmed; the consequence is then whatever the new reading frame does.", "Single wild-type band: splicing is unaffected in this system; check translation efficiency and the cell type used."], extra=[CITE["spliceai"]])

    # 7. loss of expression (truncating)
    if pos is not None or v.consequence in LOF_TYPES_LOCAL:
        e = _Ev("lof")
        if v.consequence in LOF_TYPES_LOCAL:
            e.add(3.0, f"{v.consequence} change: expected to remove or truncate the protein", Proof("ClinVar", f"{v.name[-60:]} consequence {v.consequence}", v.url if (v.url or "").startswith("http") else _cv(b)))
        finish(e, f"{_short(v)} removes the protein (loss of function through truncation or decay)",
               "Truncating changes usually trigger nonsense-mediated decay and leave little or no protein, unless they sit in the last exon.",
               ["RT-qPCR for the transcript (with and without a decay inhibitor such as cycloheximide) in patient-derived or edited cells.", "Western blot with an antibody to a region before and after the change, to see any truncated product."],
               ["Transcript restored by the decay inhibitor: nonsense-mediated decay, so the allele is a null.", "Transcript present and a truncated protein seen: escape from decay; test whether the product is functional or dominant-negative."])

    # 8. in trans
    if pos:
        e = _Ev("trans")
        rec = next((d for d in b.diseases if "recessive" in (d.inheritance or "").lower()), None)
        lof = [x for x in b.plp if x.consequence in LOF_TYPES_LOCAL and x.name != v.name]
        if rec: e.add(2.0, f"{rec.name} is recorded as recessive", Proof("UniProt disease record", f"{rec.name}: {rec.inheritance}", _uni(b)))
        if rec and lof: e.add(1.0, f"{len(lof)} pathogenic loss-of-function variant(s) exist in this gene to pair with", Proof("ClinVar", f"{len(lof)} P/LP truncating variants, for example {_short(lof[0])}", lof[0].url if (lof[0].url or "").startswith("http") else _cv(b)))
        if len(e.fors) >= 1 and rec:
            finish(e, f"{_short(v)} only causes disease when paired with a second damaging allele (compound heterozygote)",
                   "For recessive conditions a single hypomorphic variant is not enough; it matters when it sits opposite a null or a second damaging allele.",
                   ["Genetic test: phase the two alleles (parental testing or long-read sequencing) in any patient who carries this variant.", "Functional test: express the variant alone and together with a known null to see if the combined activity falls below a disease threshold."],
                   ["Patients carry it in trans with a damaging allele and have the phenotype; carriers of the variant alone do not: supports a recessive hypomorph.", "Homozygotes or trans-carriers are healthy: the variant is probably tolerated even if the assay shows reduced activity."])

    # 9. competing hypothesis: tolerated
    if pos:
        e = _Ev("tolerated")
        if am is not None and am < 0.34: e.add(2.0, f"AlphaMissense {am:.2f} (below 0.34)", amp)
        if pl is not None and pl < 50: e.add(1.5, f"low-confidence region (pLDDT {pl:.0f})", plp_)
        if len(benign_near) >= 2 and not near: e.add(1.5, f"{len(benign_near)} benign or likely benign variants within 5 residues and none pathogenic", Proof("ClinVar", f"{len(benign_near)} benign neighbours: {', '.join(_short(x) for x in benign_near[:3])}", _cv(b)))
        finish(e, f"{_short(v)} is tolerated: it has no effect on the receptor and is a bystander",
               "This is the null hypothesis, and for most VUS it is the likeliest. It has to be tested with the same assays, because a clean result is what lets a lab reclassify the variant as likely benign (ACMG BS3).",
               ["Look up the allele frequency in gnomAD: a frequency above 5% is stand-alone benign evidence (BA1), and frequencies far above the disease prevalence argue against pathogenicity.", "Run the surface and signalling assays above; a wild-type-like result in both is the evidence."],
               ["Wild-type-like in surface expression AND signalling AND binding: supports benign (BS3); submit to ClinVar with the assay as evidence.", "Wild-type-like in one assay but not tested in the others: this does not support benign; an untested pathway is still possible."])

    if not out:
        ev = Claim(text=f"No mechanism is favoured for {_short(v)} by the data retrieved; run the default panel", kind="rule", score=0.0,
                   basis="None of the triggers for a specific mechanism fired (no AlphaMissense score, no structure, no annotated feature, no pathogenic neighbour), so the data cannot rank the hypotheses. The default panel tests all of them.",
                   proofs=[cvp, CITE["acmg"], CITE["brnich"]], tags={"hyp": "default", "for": [], "against": [], "n_supporting": 1},
                   how=[f"Surface expression: {ass['surface']}.", f"Signalling: {ass['signal']}.", f"Binding: {ass['bind']}.", "Allele frequency in gnomAD."],
                   outcomes=["Any readout outside the benign-control range is a lead; all within range supports a tolerated variant."], controls=ctrl)
        out.append(ev)
    out.sort(key=lambda c: -c.score)
    return out


LOF_TYPES_LOCAL = {"nonsense", "frameshift", "splice"}


# --------------------------------------------------------------------------------------------- board
def is_unknown(v: Variant) -> bool:
    return v.significance in ("uncertain", "conflicting", "other")


def vus_board(b: Bundle, segs=None, motifs=None, pockets=None, orphan=False, coupling="", limit: int = 40) -> List[dict]:
    """Every variant of unknown significance with its leading hypothesis, ranked by how much data supports that hypothesis."""
    pl = plddt_map(b.pdb)
    rows = []
    for v in b.variants:
        if not is_unknown(v) or not v.pos:
            continue
        hs = variant_hypotheses(v, b, segs, motifs, pockets, orphan, coupling, pl)
        top = hs[0]
        seg = segment_of(list(segs) if segs else None, v.pos)
        rows.append({"variant": v, "claim": top, "n_hyp": len(hs), "region": seg or b.domain_at(v.pos) or "", "score": top.score})
    rows.sort(key=lambda r: (-r["score"], -(r["variant"].am_score or 0), -r["variant"].stars))
    return rows[:limit]


# --------------------------------------------------------------------------------------------- protein-level unknowns
def _low_conf_spans(pl: Dict[int, float], min_len: int = 30, thr: float = 50.0) -> List[Tuple[int, int]]:
    spans, start, prev = [], None, None
    for p in sorted(pl):
        if pl[p] < thr:
            if start is None or p != (prev or 0) + 1:
                if start is not None and prev - start + 1 >= min_len:
                    spans.append((start, prev))
                start = p
            prev = p
        else:
            if start is not None and prev - start + 1 >= min_len:
                spans.append((start, prev))
            start = prev = None
    if start is not None and prev - start + 1 >= min_len:
        spans.append((start, prev))
    return spans


def protein_unknowns(b: Bundle, segs=None, pockets=None, orphan: bool = False, coupling: str = "") -> List[Claim]:
    """Things the data says nothing about, each with the hypotheses that data supports and how to test them."""
    out: List[Claim] = []
    uni = Proof("UniProt", f"{b.gene} ({b.uid}) entry", _uni(b))
    ass = _assays(b, orphan, coupling)
    tr = b.tractability or {}

    # tractability
    if tr:
        ext = [s for s in (segs or []) if s.side == "extracellular" and s.length >= 25]
        ext_len = sum(s.length for s in ext) or _ecd_len(b, segs)
        if tr.get("Antibody") is False and ext_len >= 25:
            out.append(Claim(text=f"Antibody tractability is 'unknown' for {b.gene}, but it has {ext_len} extracellular residues an antibody could reach", kind="rule", score=2.0,
                             basis="Open Targets lists no antibody tractability, which means nobody has shown it, not that it cannot work. An accessible extracellular region is the precondition, and the topology says one exists.",
                             proofs=[Proof("Open Targets tractability", "Antibody: no evidence recorded", "https://platform.opentargets.org/target"), Proof("UniProt topology", f"extracellular segments total {ext_len} residues", _uni(b))],
                             tags={"unknown": "antibody tractability", "n_supporting": 2},
                             how=["Test for an epitope: flow cytometry on cells expressing the tagged receptor versus parental cells, with a commercial antibody against the extracellular region.", "If none exists, immunise or run phage display against the recombinant extracellular domain and confirm binding on live cells.", "Check that the epitope is not buried under glycans or a tag."],
                             outcomes=["Antibody stains receptor-expressing cells and not parental cells: the epitope is reachable; next, test whether binding changes signalling.", "No staining despite surface expression (confirmed with the tag): the extracellular region is short, glycosylated or hidden; antibodies are a poor route."]))
        if tr.get("Small molecule") is False and pockets:
            p0 = pockets[0]
            out.append(Claim(text=f"Small-molecule tractability is 'unknown' for {b.gene}, but the AlphaFold model has {len(pockets)} candidate pocket(s), the largest {p0.get('volume', 0):.0f} A^3", kind="rule", score=1.5,
                             basis="Open Targets has no small-molecule tractability evidence. A pocket on a predicted model is only a place to look: it says nothing about whether a ligand binds there.",
                             proofs=[Proof("Open Targets tractability", "Small molecule: no evidence recorded", "https://platform.opentargets.org/target"), Proof("Pocket module (LIGSITE-style geometry)", f"pocket 1: volume {p0.get('volume', 0):.0f} A^3, lined by {', '.join(p0.get('helices', [])) or 'non-helical residues'}", "")],
                             tags={"unknown": "small-molecule tractability", "n_supporting": 2},
                             how=["Mutate two or three residues lining the top pocket and check that any known ligand response, or constitutive activity, changes (a site-directed test, not a binding test).", "Screen a small fragment library by thermal shift or SPR on purified receptor, or by a NanoBRET/BRET read-out in cells.", "Confirm any hit by an orthogonal assay and show loss of effect when the pocket residues are mutated."],
                             outcomes=["Pocket mutants lose a ligand's effect: the pocket is functionally relevant to that ligand.", "Hits shift the melting temperature and mutants abolish it: a real binder at that pocket.", "Hits shift melting temperature but pocket mutants do not matter: binding elsewhere or nonspecific; do not call it tractable."]))
        if tr.get("PROTAC") is False:
            icl = [s for s in (segs or []) if s.side == "intracellular"]
            lys = sum(b.sequence[s.start - 1:s.end].count("K") for s in icl) if (b.sequence and icl) else 0
            if lys:
                out.append(Claim(text=f"PROTAC tractability is 'unknown' for {b.gene}; {lys} intracellular lysines exist, but a binder has to come first", kind="rule", score=1.0,
                                 basis="A degrader needs a ligand to recruit the E3 ligase, and a surface lysine on the cytoplasmic side for ubiquitination. The first condition is not met until any binder exists.",
                                 proofs=[Proof("Open Targets tractability", "PROTAC: no evidence recorded", "https://platform.opentargets.org/target"), Proof("UniProt sequence", f"{lys} lysines in intracellular segments", _uni(b))],
                                 tags={"unknown": "PROTAC tractability", "n_supporting": 2},
                                 how=["Find any binder first (see the small-molecule entry), then attach a linker and an E3 recruiter and measure loss of tagged receptor (HiBiT or Western) over a dose range.", "Include a non-degrading control (the binder alone) and a proteasome or neddylation inhibitor control."],
                                 outcomes=["Dose-dependent loss that the proteasome inhibitor reverses: genuine degradation.", "Loss with the binder alone: inhibition or toxicity, not a PROTAC effect."]))

    # coupling
    if b.is_gpcr and not coupling and not orphan:
        out.append(Claim(text=f"G protein coupling of {b.gene} is unknown in the data loaded", kind="rule", score=1.0,
                         basis="No recorded coupling and no co-expression prediction exist for this receptor in this session, so there is nothing to rank the four families by. The honest step is one panel that tests all of them.",
                         proofs=[Proof("UniProt", f"{b.gene} is annotated as a G protein-coupled receptor", _uni(b)), CITE["trupath"], CITE["tango"]],
                         tags={"unknown": "coupling", "n_supporting": 1},
                         how=[f"Run {ass['signal']} in one experiment.", "Use a chimeric Gα (Gα16 or Gqi5) only as a screen for activation, then rerun in the native pathway."],
                         outcomes=["Signal only in the Gi/o biosensor: Gi/o coupling; confirm with pertussis toxin loss of effect.", "Signal in several families: promiscuous coupling; report relative efficacies rather than one class.", "No signal in any family with arrestin positive: arrestin-biased receptor."]))

    # no disease
    if not b.diseases and not b.plp:
        e = _Ev("nodisease")
        pli, loeuf = b.constraint.get("pLI"), b.constraint.get("oe_lof_upper")
        proofs = []
        if (pli is not None and pli >= 0.9) or (loeuf is not None and loeuf < 0.6):
            proofs.append(Proof("gnomAD constraint", f"pLI {pli if pli is not None else 'n/a'}, LOEUF {loeuf if loeuf is not None else 'n/a'}", f"https://gnomad.broadinstitute.org/gene/{b.gene}"))
        if proofs:
            out.append(Claim(text=f"No disease is linked to {b.gene} in the records, yet the gene does not tolerate loss of function", kind="rule", score=2.0,
                             basis="Strong constraint means carriers of damaging variants are depleted in the population, which fits an unrecognised disease or early lethality; it does not show either.",
                             proofs=proofs + [uni], tags={"unknown": "disease association", "n_supporting": 1},
                             how=["Search GeneMatcher and rare-disease cohorts for people with damaging variants in this gene and compare their phenotypes.", "Check biobank exomes (UK Biobank, All of Us, gnomAD) for phenotype associations with rare damaging variants in this gene.", "Model the loss in a relevant cell type (CRISPR knockout) and read out the pathway the gene sits in."],
                             outcomes=["Unrelated patients with damaging variants share a phenotype: a new gene-disease link worth publishing.", "Carriers of damaging variants are healthy: the constraint reflects something other than disease (such as fitness effects in development); revisit."]))
        mp = b.mouse_phenotypes[:6]
        if mp:
            out.append(Claim(text=f"No human disease is recorded for {b.gene}, but mouse knockout affects: " + ", ".join(sorted({c for m in mp for c in (m.get('classes') or [])})[:4] or ["phenotypes not classified"]), kind="rule", score=1.5,
                             basis="A knockout phenotype in the mouse points to a physiological role that may have a human disease counterpart; mouse and human biology differ, and a normal knockout would not rule out a role.",
                             proofs=[Proof("Open Targets (IMPC/MGI)", f"{len(b.mouse_phenotypes)} mouse phenotype(s), e.g. {mp[0]['label']}", "https://platform.opentargets.org/target")],
                             tags={"unknown": "disease association", "n_supporting": len(mp)},
                             how=["Check whether the human gene is expressed in the tissue the mouse phenotype involves (UniProt tissue text, GTEx).", "Knock out or knock down the gene in a human cell line from that tissue and test the corresponding phenotype."],
                             outcomes=["Human cells reproduce the mouse phenotype: a conserved role; look for patients.", "Human cells show nothing: species difference or redundancy."]))

    # low-confidence structure
    pl = plddt_map(b.pdb)
    spans = _low_conf_spans(pl)
    if spans:
        tot = sum(e - s + 1 for s, e in spans)
        out.append(Claim(text=f"{len(spans)} region(s) of {b.gene} ({tot} residues) have no reliable structure: {', '.join(f'{s}-{e}' for s, e in spans[:4])}", kind="rule", score=1.0,
                         basis="AlphaFold confidence below 50 usually means the region is disordered or not modelled well. Disordered regions often carry regulatory motifs, phosphorylation sites and partner-binding sites that a static model cannot show; variants there are the hardest to interpret.",
                         proofs=[Proof("AlphaFold DB (pLDDT)", f"residues below pLDDT 50: {', '.join(f'{s}-{e}' for s, e in spans[:4])}", f"https://alphafold.ebi.ac.uk/entry/{b.uid}"), CITE["alphafold"]],
                         tags={"unknown": "structure", "n_supporting": len(spans)},
                         how=["Look up phosphorylation and other modification sites in these spans (PhosphoSitePlus, UniProt features).", "Delete or truncate the span and test whether surface expression, signalling or partner binding change.", "Try limited proteolysis or HDX-MS on purified protein to see whether the span is protected."],
                         outcomes=["Deleting the span changes signalling or partner binding: it is a functional regulatory region, not filler.", "Deleting it changes nothing measurable: likely a flexible linker; variants inside it are probably tolerated."]))

    out.sort(key=lambda c: -c.score)
    return out
