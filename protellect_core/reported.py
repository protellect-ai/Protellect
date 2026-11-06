"""Gene-name reconciliation and literature-reported pharmacology for receptors the precedent model cannot speak about.

Two jobs, both kept apart from anything computed on your data:

1. ALIASES. A table can name the same gene two ways (ADGRG1 and its legacy name GPR56). Left alone, the two rows are scored as
   two genes. `canonicalize` maps every name to the official symbol, merges duplicates (keeping the larger effect) and says
   what it did. Names come from this short table (HGNC renames; Hamann et al., Pharmacol Rev 2015 for adhesion GPCRs) plus
   the alias column of the receptor registry, and a name is mapped only if it points to exactly one gene.

2. REPORTED PHARMACOLOGY. For a few orphan or recently deorphanised receptors, and for whole families, what the literature has
   reported about coupling and ligand class. Each entry names its papers. These entries were typed in from the literature by
   hand and have NOT been checked against the papers: the app says so wherever they are shown. They are leads to test, never
   results, and they are labelled "reported" or "family-level", never "predicted from your data".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .evidence import Claim, Proof

ALIASES: Dict[str, str] = {
    # adhesion GPCRs (HGNC 2013-2015 renaming; Hamann et al. 2015)
    "GPR56": "ADGRG1", "GPR64": "ADGRG2", "GPR97": "ADGRG3", "GPR112": "ADGRG4", "GPR114": "ADGRG5", "GPR126": "ADGRG6", "GPR128": "ADGRG7",
    "GPR133": "ADGRD1", "GPR144": "ADGRD2", "GPR123": "ADGRA1", "GPR124": "ADGRA2", "GPR125": "ADGRA3",
    "GPR110": "ADGRF1", "GPR111": "ADGRF2", "GPR113": "ADGRF3", "GPR115": "ADGRF4", "GPR116": "ADGRF5",
    "BAI1": "ADGRB1", "BAI2": "ADGRB2", "BAI3": "ADGRB3", "CELSR1": "ADGRC1", "CELSR2": "ADGRC2", "CELSR3": "ADGRC3",
    "EMR1": "ADGRE1", "EMR2": "ADGRE2", "EMR3": "ADGRE3", "CD97": "ADGRE5", "ELTD1": "ADGRL4",
    "LPHN1": "ADGRL1", "LPHN2": "ADGRL2", "LPHN3": "ADGRL3", "GPR98": "ADGRV1", "VLGR1": "ADGRV1",
    # other renamed GPCRs that appear in older tables
    "GPR40": "FFAR1", "GPR41": "FFAR3", "GPR43": "FFAR2", "GPR120": "FFAR4", "GPR54": "KISS1R", "GPR103": "QRFPR",
    "GPR7": "NPBWR1", "GPR8": "NPBWR2", "GPR14": "UTS2R", "GPR73": "PROKR1", "GPR73L1": "PROKR2",
    "GPR81": "HCAR1", "GPR109A": "HCAR2", "GPR109B": "HCAR3", "TDAG8": "GPR65", "OGR1": "GPR68",
}
ALIAS_SOURCE = "HGNC symbol history and Hamann et al., Pharmacol Rev 2015 (adhesion GPCR nomenclature); registry alias column"


def _norm(s: str) -> str:
    return "".join(ch for ch in str(s).upper() if ch.isalnum())


def alias_map(registry: Optional[dict] = None) -> Dict[str, str]:
    """name (upper case, as typed) -> official symbol. Registry aliases are added only when they point to a single gene."""
    m = {k: v for k, v in ALIASES.items()}
    if registry:
        seen: Dict[str, set] = {}
        for gene, info in registry.items():
            for al in (info or {}).get("aliases", []) or []:
                for part in str(al).replace(";", "|").replace(",", "|").split("|"):
                    p = part.strip().upper()
                    if p and p != gene.upper() and len(p) > 2:
                        seen.setdefault(p, set()).add(gene.upper())
        for p, genes in seen.items():
            if len(genes) == 1 and p not in registry and p not in m:
                m[p] = next(iter(genes))
    return m


def canonicalize(parsed: pd.DataFrame, registry: Optional[dict] = None) -> pd.DataFrame:
    """Map gene names to official symbols and merge rows that turn out to be the same gene.

    The row with the larger |effect| is kept (the same rule parse_experiment uses for repeated symbols). Whatever was merged is
    recorded in `df.attrs['alias_notes']` so the page can say it. A symbol that is already official is never renamed."""
    if parsed is None or parsed.empty or "gene" not in parsed.columns:
        return parsed
    m = alias_map(registry)
    official = set(registry or {}) | set(m.values())
    df = parsed.copy()
    orig = df["gene"].astype(str).str.upper()
    # a name that is itself a registry symbol stays as it is, even if some table lists it as an alias of something else
    df["gene"] = [m.get(g, g) if g not in (registry or {}) else g for g in orig]
    notes: List[str] = list(parsed.attrs.get("alias_notes", []))
    renamed = {o: n for o, n in zip(orig, df["gene"]) if o != n}
    dup = df["gene"].duplicated(keep=False)
    if dup.any() and "effect" in df.columns:
        keep = df.loc[dup].assign(_abs=lambda d: d["effect"].abs()).sort_values("_abs", ascending=False)
        for gene, grp in keep.groupby("gene", sort=False):
            names = [o for o, n in zip(orig, df["gene"]) if n == gene]
            if len(set(names)) < 2:
                continue
            best = grp.iloc[0]
            best_name = next(o for o, e, n in zip(orig, df["effect"], df["gene"]) if n == gene and e == best["effect"])
            notes.append(f"{' and '.join(sorted(set(names)))} are the same gene ({gene}). The rows were merged and the one with the larger effect was kept ({best_name}, {best['effect']:.2f}).")
        df = df.loc[df["effect"].abs().groupby(df["gene"]).idxmax()].reset_index(drop=True)
    for o, n in renamed.items():
        if not any(o in x for x in notes):
            notes.append(f"{o} is a legacy name for {n}; it is shown as {n}.")
    df.attrs["alias_notes"] = notes
    return df


# ───────────────────────────────────────────────────────── reported pharmacology
@dataclass(frozen=True)
class Reported:
    coupling: Tuple[str, ...]
    coupling_refs: Tuple[str, ...]
    ligands: Tuple[str, ...]
    ligand_class: str
    ligand_refs: Tuple[str, ...]
    caution: str = ""


REPORTED: Dict[str, Reported] = {
    "ADGRG1": Reported(("G12/13",), ("Iguchi et al., J Biol Chem 2008 (GPR56, G12/13 and Rho)",),
                       ("collagen III (extracellular matrix, binds the N-terminal fragment)", "a tethered agonist peptide exposed after the receptor's own cleavage"),
                       "extracellular-matrix protein / tethered peptide",
                       ("Luo et al., PNAS 2011 (GPR56 and collagen III)", "Stoveken et al., PNAS 2015 (tethered agonists of adhesion GPCRs)"),
                       "Adhesion GPCRs often need the N-terminal fragment removed or the tethered peptide exposed before they signal in a dish."),
    "GPR171": Reported(("Gi/o",), ("Gomes et al., PNAS 2013 (GPR171 and BigLEN)",),
                       ("BigLEN, a neuropeptide cleaved from proSAAS",), "peptide",
                       ("Gomes et al., PNAS 2013 (GPR171 and BigLEN)",),
                       "Reported in hypothalamus; its ligand has not been shown in the tumour setting."),
    "GPR35": Reported(("Gi/o", "G13"), ("Divorty et al., Front Pharmacol 2015 (review of GPR35 signalling)",),
                      ("kynurenic acid (a tryptophan metabolite)", "2-acyl lysophosphatidic acid", "CXCL17 (disputed)"), "organic acid / lipid mediator",
                      ("Wang et al., J Biol Chem 2006 (kynurenic acid)", "Oka et al., Biochem Biophys Res Commun 2010 (lysophosphatidic acid)"),
                      "Agonist potency differs strongly between human and rodent receptors, and the ligand list is contested."),
    "GPR18": Reported(("Gi/o",), ("McHugh et al., BMC Neurosci 2010 (GPR18 signalling)",),
                      ("N-arachidonoyl glycine (contested)", "resolvin D2", "abnormal cannabidiol"), "lipid mediator",
                      ("Kohno et al., Biochem Biophys Res Commun 2006 (N-arachidonoyl glycine)", "Chiang et al., J Exp Med 2015 (resolvin D2)"),
                      "Ligand claims for GPR18 conflict between laboratories; treat every one as a lead."),
    "GPR65": Reported(("Gs",), ("Ishii et al., J Biol Chem 2005 (TDAG8 as an acid-sensing receptor)",),
                      ("protons (extracellular acidification)", "psychosine (historic, disputed)"), "ion / proton",
                      ("Ishii et al., J Biol Chem 2005 (TDAG8 as an acid-sensing receptor)",),
                      "A proton-sensing receptor is most active in acidic tumour regions; keep the medium pH fixed in every control."),
}
REPORTED_NOTE = ("Reported pharmacology was typed in from the literature and has not been checked against the papers. "
                 "Each entry names its papers so you can check them before relying on it.")

FAMILY: List[dict] = [
    {"match": "adhesion", "coupling": ("G12/13",), "alt": ("Gs", "Gi/o", "Gq/11"),
     "ligand_class": "extracellular-matrix protein / tethered peptide",
     "ligands": "large extracellular matrix or cell-surface proteins that bind the long N-terminal fragment, and a tethered 'Stachel' peptide that is exposed after the receptor cleaves itself",
     "refs": ("Hamann et al., Pharmacol Rev 2015 (adhesion GPCR review)", "Liebscher et al., Cell Rep 2014 (tethered agonist, GPR126 and GPR133)")},
]


def _family_prior(info: dict) -> Optional[dict]:
    fam = str((info or {}).get("family", "")).lower()
    return next((f for f in FAMILY if f["match"] in fam), None)


def has_prior(gene: str, info: Optional[dict]) -> bool:
    return gene.upper() in REPORTED or _family_prior(info or {}) is not None


def prior_text(gene: str, info: Optional[dict]) -> Optional[dict]:
    """{'coupling': str, 'ligand': str, 'basis': 'reported'|'family-level'} for the results table."""
    g = gene.upper()
    if g in REPORTED:
        r = REPORTED[g]
        return {"coupling": "/".join(r.coupling) + " (reported)", "ligand": r.ligand_class + " (reported)", "basis": "reported"}
    f = _family_prior(info or {})
    if f:
        return {"coupling": "/".join(f["coupling"]) + " (family-level)", "ligand": f["ligand_class"] + " (family-level)", "basis": "family-level"}
    return None


# ─────────────────────────────────────────────── test plans (assay interpretation rules)
COUPLING_PLAN: Dict[str, dict] = {
    "G12/13": {
        "how": ["Express the receptor with an N-terminal tag in HEK293 cells; include an empty-vector control and a receptor of known G12/13 coupling.",
                "Read RhoA activation (pull-down or G-LISA) or an SRE/SRF-luciferase reporter, and a G12/13 BRET sensor if you have one.",
                "Block with the Rho kinase inhibitor Y-27632 or C3 toxin, and with a Gq/11 inhibitor (YM-254890) to rule out Gq crosstalk.",
                "Measure surface expression in parallel so a flat result can be interpreted."],
        "outcomes": ["SRE or RhoA signal above empty vector that Y-27632 or C3 removes: supports G12/13 (and Rho) signalling.",
                     "Signal that YM-254890 removes: it runs through Gq/11, not G12/13 alone.",
                     "No signal and the receptor is at the surface: it may need its ligand or the exposed tethered peptide (see the adhesion-receptor assay).",
                     "No signal and the receptor is not at the surface: a trafficking problem; inconclusive."],
        "controls": ["Empty-vector cells", "A receptor with known G12/13 coupling", "Surface-expression readout", "Y-27632 / C3 and YM-254890 blockers"]},
    "Gi/o": {
        "how": ["Express the receptor in HEK293 cells with a cAMP sensor (for example GloSensor) and an empty-vector control.",
                "Stimulate with forskolin, add the candidate ligand, and measure the fall in cAMP; repeat after overnight pertussis toxin.",
                "Add a TRUPATH Gi/o BRET sensor to confirm at the G-protein level."],
        "outcomes": ["Forskolin-stimulated cAMP falls and pertussis toxin removes the fall: supports Gi/o.",
                     "cAMP falls but pertussis toxin does not remove it: not Gi/o; look for another route.",
                     "No change: the ligand may be wrong, or the receptor is not at the surface."],
        "controls": ["Empty-vector cells", "Pertussis toxin", "A receptor with known Gi/o coupling", "Surface-expression readout"]},
    "Gs": {
        "how": ["Express the receptor in HEK293 cells with a cAMP sensor and an empty-vector control.",
                "Measure basal cAMP and the response to the candidate ligand; for a proton-sensing receptor vary pH in small steps in a well-buffered medium.",
                "Confirm with a Gs BRET sensor."],
        "outcomes": ["cAMP rises above empty vector and scales with the stimulus: supports Gs.",
                     "A rise that is also present in empty-vector cells: an endogenous receptor, not yours.",
                     "No rise: the ligand may be wrong or the receptor is not at the surface."],
        "controls": ["Empty-vector cells", "Forskolin as a maximal-cAMP reference", "pH-matched buffers", "Surface-expression readout"]},
}
LIGAND_PLAN: Dict[str, List[str]] = {
    "extracellular-matrix protein / tethered peptide": [
        "Coat plates with the candidate matrix protein (for example collagen III) and test receptor-expressing cells against uncoated and irrelevant-protein wells.",
        "Test the N-terminal-fragment-deleted (constitutively active) construct against the full-length receptor; a gain of signal suggests the tethered peptide is the activator.",
        "Add a synthetic tethered-agonist peptide to full-length receptor cells with a scrambled-peptide control, and read the G12/13 output."],
    "peptide": ["Screen candidate peptides and fractionated tissue extract from the receptor's tissue against receptor cells and empty-vector cells.",
                "Confirm the hit with a dose-response, a second readout and an antagonist or a scrambled peptide."],
    "organic acid / lipid mediator": ["Screen a panel of the candidate metabolites and lipid mediators with empty-vector controls, using cAMP, calcium or arrestin readouts.",
                                      "Treat any hit as a lead until it shows a dose-response and is absent in empty-vector cells."],
    "lipid mediator": ["Screen lipid-mediator candidates (lysophospholipids, N-acyl amides) with empty-vector controls using cAMP or arrestin readouts."],
    "ion / proton": ["Vary pH in small steps in a well-buffered system, receptor cells against empty-vector cells; test zinc and calcium as well."],
}


def _is_adhesion(g: str, info: Optional[dict]) -> bool:
    return g.startswith("ADGR") or "adhesion" in str((info or {}).get("family", "")).lower()


def prior_claims(gene: str, info: Optional[dict], effect: Optional[float] = None, effect_type: str = "") -> List[Claim]:
    """Claims for the coupling and the ligand class that the literature reports for this receptor, or that its family reports.
    Empty unless a source exists. Never presented as derived from the user's data."""
    g = gene.upper()
    out: List[Claim] = []
    reg_proof = Proof("Receptor registry", f"{g} is listed with family '{(info or {}).get('family') or 'not given'}' and status '{(info or {}).get('status') or 'not given'}'", "https://www.guidetopharmacology.org/")
    adh = {"assay": "adhesion_gpcr"} if _is_adhesion(g, info) else {}
    mine = Proof("Your experiment", f"{effect_type or 'effect'} {effect:.2f}") if isinstance(effect, (int, float)) and effect == effect else None

    def _extras(proofs):
        return proofs + ([mine] if mine else [])

    if g in REPORTED:
        r = REPORTED[g]
        cp = [Proof(ref.split(" (")[0], ref, kind="literature") for ref in r.coupling_refs]
        lp = [Proof(ref.split(" (")[0], ref, kind="literature") for ref in r.ligand_refs]
        c0 = "/".join(r.coupling)
        plan = COUPLING_PLAN.get(r.coupling[0], {})
        out.append(Claim(text=f"{g}: reported to signal through {c0}", proofs=_extras(cp + [reg_proof]), kind="inference",
                         basis=f"Published reports for this receptor (not derived from your data). {REPORTED_NOTE} {r.caution}", score=0.5,
                         tags={"category": "reported-coupling", "n_supporting": len(cp), "support": 0.5, "prior": "reported", **adh},
                         how=plan.get("how", []), outcomes=plan.get("outcomes", []), controls=plan.get("controls", [])))
        lig = "; ".join(r.ligands)
        out.append(Claim(text=f"{g}: reported ligand class is {r.ligand_class}: {lig}", proofs=_extras(lp + [reg_proof]), kind="inference",
                         basis=f"Published reports for this receptor (not derived from your data). {REPORTED_NOTE} {r.caution}", score=0.5,
                         tags={"category": "reported-ligand", "n_supporting": len(lp), "support": 0.5, "prior": "reported", **adh},
                         how=LIGAND_PLAN.get(r.ligand_class, []),
                         outcomes=["A compound or protein that activates receptor cells in a dose-response and not empty-vector cells: a candidate ligand, still needing a second assay and native-cell confirmation.",
                                   "Activity in empty-vector cells too: it acts on a host-cell receptor; switch host cells or knock out the endogenous receptor and retest.",
                                   "No activity: the reported ligand is not confirmed in your system; the literature on some of these ligands is contested."],
                         controls=["Empty-vector cells", "Scrambled or irrelevant-protein control", "Dose-response on every hit", "Surface-expression readout"]))
        return out
    f = _family_prior(info or {})
    if f:
        cp = [Proof(ref.split(" (")[0], ref, kind="literature") for ref in f["refs"]]
        c0 = f["coupling"][0]
        plan = COUPLING_PLAN.get(c0, {})
        out.append(Claim(text=f"{g}: family-level expectation is signalling through {'/'.join(f['coupling'])} (others reported: {', '.join(f['alt'])})", proofs=_extras(cp + [reg_proof]), kind="inference",
                         basis=f"This receptor is in the '{(info or {}).get('family')}' family; the statement is about the family, not measured for {g}. {REPORTED_NOTE}", score=0.3,
                         tags={"category": "family-coupling", "n_supporting": len(cp), "support": 0.3, "prior": "family", **adh},
                         how=plan.get("how", []), outcomes=plan.get("outcomes", []), controls=plan.get("controls", [])))
        out.append(Claim(text=f"{g}: family-level ligand class is {f['ligand_class']}: {f['ligands']}", proofs=_extras(cp + [reg_proof]), kind="inference",
                         basis=f"Family-level pattern, not measured for {g}. {REPORTED_NOTE}", score=0.3,
                         tags={"category": "family-ligand", "n_supporting": len(cp), "support": 0.3, "prior": "family", **adh},
                         how=LIGAND_PLAN.get(f["ligand_class"], []),
                         outcomes=["Signal that appears only with the N-terminal fragment removed or the tethered peptide added: the receptor is held inactive by its own N-terminus.",
                                   "No signal in either construct and the receptor is at the surface: look for the matrix partner or a different transducer."],
                         controls=["Empty-vector cells", "Scrambled peptide", "Full-length versus fragment-deleted construct", "Surface-expression readout"]))
    return out


# ─────────────────────────────────────────────── compare the engine's answer with the literature entry
def _coupling_family(x: str) -> str:
    t = str(x).lower().replace(" ", "")
    if t.startswith(("gi", "go", "g_i")): return "gi/o"
    if t.startswith(("gq", "g11")): return "gq/11"
    if t.startswith("gs"): return "gs"
    if "12" in t or "13" in t: return "g12/13"
    return t


def compare_with_literature(gene: str, ligand_value: Optional[str], coupling_value: Optional[str]) -> dict:
    """Does the engine's pick agree with what the literature entry for this receptor reports? Receptor-level entries only
    (a family-level pattern is not compared). Returns {'status': 'matches'|'differs'|'no entry'|'not compared', 'text': str}.
    A difference is shown, never hidden: either the entry or the engine may be wrong, and only the papers can say which."""
    r = REPORTED.get(gene.upper())
    if r is None:
        return {"status": "no entry", "text": "No literature entry for this receptor"}
    if not ligand_value and not coupling_value:
        return {"status": "not compared", "text": "Nothing from the engine to compare"}
    notes, differs = [], False
    if ligand_value:
        toks = {t.strip().lower() for t in r.ligand_class.split("/")}
        if str(ligand_value).strip().lower() in toks:
            notes.append(f"ligand class {ligand_value} matches the reported {r.ligand_class}")
        else:
            differs = True
            notes.append(f"ligand class {ligand_value} differs from the reported {r.ligand_class}")
    if coupling_value and not str(coupling_value).endswith(("(reported)", "(family-level)")):
        rep = {_coupling_family(c) for c in r.coupling}
        if _coupling_family(coupling_value) in rep:
            notes.append(f"coupling {coupling_value} matches the reported {'/'.join(r.coupling)}")
        else:
            differs = True
            notes.append(f"coupling {coupling_value} differs from the reported {'/'.join(r.coupling)}")
    return {"status": "differs" if differs else "matches",
            "text": "; ".join(notes) + ". The literature entry is typed by hand and unchecked, so read the papers before deciding which is right."}
