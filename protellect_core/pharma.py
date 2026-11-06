"""'What could happen if this target is drugged?' as ranked, evidence-tagged scenarios.

Each scenario states what it is built from (data) and what is inference (rule + basis). Nothing here predicts a
clinical outcome: it organises what the records say about direction of effect, tissues, precedent and modality.
"""
from __future__ import annotations

from typing import List

from .adapters import Bundle
from .analysis import CITE, _clinvar_url
from .evidence import Claim, Proof

DIRECTIONS = {
    "Inhibit / antagonise": ("inhibit", ("inhibit", "antagon", "block", "inverse")),
    "Activate / restore": ("activate", ("agonist", "activat", "positive allosteric", "potentiat")),
    "Degrade / silence": ("degrade", ("degrad", "silenc", "antisense", "sirna")),
}


def _extracellular(b: Bundle) -> bool:
    s = " ".join(b.subcellular).lower()
    return any(k in s for k in ("membrane", "secreted", "extracellular")) or b.is_gpcr


def _cns(b: Bundle) -> bool:
    t = (b.tissue_text or "").lower()
    return any(k in t for k in ("brain", "neuron", "cortex", "habenula", "striat", "cerebell", "hippocamp"))


def modality_notes(b: Bundle, direction: str) -> List[dict]:
    notes = []
    cns, ext = _cns(b), _extracellular(b)
    tr = b.tractability
    if tr.get("Small molecule") or b.is_gpcr or b.drugs:
        route = "oral" if not cns else "oral, with brain-penetrant chemistry"
        notes.append({"modality": "Small molecule", "route": route,
                      "must_have": "Rule-of-Five compliant" + ("; polar surface area <= 90 A^2, MW <= 450, HBD <= 3 to reach the brain" if cns else ""),
                      "basis": "Standard medicinal-chemistry guidance (Lipinski 2001; Pajouhesh & Lenz 2005)." if cns else "Lipinski 2001.",
                      "proof": Proof("Open Targets" if tr.get("Small molecule") else "UniProt", "small-molecule tractable" if tr.get("Small molecule") else "receptor/target class", "https://platform.opentargets.org/target")})
    if ext and (tr.get("Antibody") or direction in ("inhibit", "activate")) and tr.get("Antibody"):
        notes.append({"modality": "Antibody", "route": "intravenous or subcutaneous", "must_have": "an accessible extracellular epitope" + ("; large biologics cross the blood-brain barrier poorly" if cns else ""),
                      "basis": "Antibodies act on extracellular or membrane-exposed targets.", "proof": Proof("Open Targets", "antibody tractable", "https://platform.opentargets.org/target")})
    if direction == "degrade" and tr.get("PROTAC"):
        notes.append({"modality": "Targeted degrader (PROTAC)", "route": "oral possible, often beyond Rule-of-Five size", "must_have": "an intracellular binding site and a usable E3 ligase handle",
                      "basis": "Degraders link a target binder to an E3 ligase ligand.", "proof": Proof("Open Targets", "PROTAC tractable", "https://platform.opentargets.org/target")})
    if direction in ("degrade", "inhibit") and not ext:
        notes.append({"modality": "Antisense / siRNA", "route": "systemic (liver-targeted conjugates) or intrathecal for CNS", "must_have": "an accessible transcript and a delivery route to the tissue",
                      "basis": "Oligonucleotides lower protein levels without needing a binding pocket.", "proof": Proof("UniProt", f"subcellular location: {', '.join(b.subcellular) or 'not recorded'}", f"https://www.uniprot.org/uniprotkb/{b.uid}/entry")})
    return notes


def scenarios(b: Bundle, defects: List[Claim], systems: List[Claim], diseases: List[Claim], ctx=None) -> List[Claim]:
    if not b.loaded:
        return []
    mech_lof = any(c.tags.get("mechanism") == "loss-of-function" for c in defects)
    cv = Proof("ClinVar", f"{len(b.plp)} pathogenic/likely-pathogenic variants", _clinvar_url(b))
    organs = [s for s in systems if s.tags.get("has_tissue")]
    essential = (b.constraint.get("pLI") or 0) >= 0.9
    out = []
    for label, (key, kws) in DIRECTIONS.items():
        proofs: List[Proof] = []
        fit, parts, basis = 0.0, [], []
        if key == "activate" and mech_lof:
            fit += 3; parts.append("fits the loss-of-function mechanism"); proofs += [p for d in defects if d.tags.get("mechanism") == "loss-of-function" for p in d.proofs][:3]
            basis.append("Loss-of-function disease is addressed by restoring activity.")
        elif key in ("inhibit", "degrade") and mech_lof:
            fit -= 2; parts.append("conflicts with the loss-of-function mechanism: further reduction may phenocopy disease"); proofs += [cv]
            basis.append("Lowering activity of a gene whose loss causes disease can reproduce that disease.")
        elif b.plp:
            parts.append("direction cannot be justified until loss vs gain of function is established"); proofs += [cv]
            basis.append("Mechanism is unresolved in these data.")
        known = [d for d in b.drugs if any(k in (d.kind + " " + d.mechanism).lower() for k in kws)]
        if known:
            fit += 1.5; parts.append(f"{len(known)} recorded drug(s) already act in this direction ({', '.join(d.name for d in known[:3])})")
            proofs += [Proof(d.source or "DGIdb", f"{d.name}: {d.kind or d.mechanism}", d.url) for d in known[:3]]
        notes = modality_notes(b, key)
        if notes:
            fit += 1; proofs += [n["proof"] for n in notes[:2]]
        if organs:
            parts.append("on-target effects expected in " + ", ".join(s.tags["system"] for s in organs[:3]) + " (where the protein is expressed)")
            proofs += [p for s in organs[:2] for p in s.proofs if p.kind == "data"][:2]
            basis.append("A drug acts wherever its target is present.")
        if essential:
            parts.append("gene is intolerant of loss of function (pLI >= 0.9), so strong inhibition carries on-target safety risk" if key != "activate" else "gene is LoF-intolerant")
            proofs.append(Proof("gnomAD", f"pLI = {b.constraint.get('pLI'):.2f}", "https://gnomad.broadinstitute.org/gene/" + b.gene))
            if key != "activate":
                fit -= 1
        if not proofs:
            continue
        risk = "HIGHER" if (essential and key != "activate") or (key != "activate" and mech_lof) else "MODERATE" if len(organs) >= 2 else "LOWER"
        c = Claim(text=f"{label}: " + "; ".join(parts), proofs=proofs + [Proof("Scenario rule", "direction of effect x tissue x precedent x modality", kind="rule")], kind="rule",
                  basis=" ".join(dict.fromkeys(basis)) or "Direction, tissue and precedent combined.", score=fit,
                  tags={"direction": key, "risk": risk, "n_supporting": len(proofs), "known_drugs": [d.name for d in known], "modalities": notes, "organs": [s.tags["system"] for s in organs],
                        "phenocopy": [d.tags.get("disease", d.text) for d in diseases[:3]] if key != "activate" and mech_lof else []})
        c.how = [f"{n['modality']}: {n['route']}. Needs {n['must_have']}. ({n['basis']})" for n in notes]
        out.append(c)
    return sorted(out, key=lambda c: -c.score)
