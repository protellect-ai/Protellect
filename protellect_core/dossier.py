"""'This is present in your experiment... it might mean...': evidence synthesis for each orphan GPCR and for the experiment as a whole.

Everything shown is either a number from the user's own data or a stated rule applied to it. Hypotheses are ranked within a question (what does it couple to, what might
it bind, what is its role) using scores whose components are listed with them. A score is a relative support among the options shown, NOT a probability.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .assays import assays_for
from .gpcrome import PATHWAYS

# Receptor nomenclature encodes ligand type (HGNC / IUPHAR naming). A deterministic rule, used only to describe what a receptor's expression neighbours bind.
NEIGHBOUR_CLASS = [
    ("lipid mediator", r"^(PTG[A-Z0-9]+|TBXA2R|LTB4R2?|CYSLTR[12]|OXER1|S1PR[1-5]|LPAR[1-6]|CNR[12]|GPR183|GPR55|PTGDR2|GPR132|GPR174|GPR34)$"),
    ("fatty acid", r"^(FFAR[1-4]|GPR84|GPR120)$"),
    ("organic acid", r"^(HCAR[1-3]|SUCNR1|OXGR1)$"),
    ("nucleotide", r"^(P2RY[0-9]+|ADORA[123][AB]?|GPR17|GPR87)$"),
    ("ion / proton", r"^(CASR|GPRC6A|GPR39|GPR4|GPR65|GPR68)$"),
    ("amine", r"^(CHRM[1-5]|ADRB[1-3]|ADRA[12][ABC]|DRD[1-5]|HTR[1-7][A-F]?|HRH[1-4]|TAAR[0-9]+|MTNR1[AB])$"),
    ("peptide", r"^(AGTR[12]|EDNR[AB]|OPR[DKLM]1|NPY[1-5]R|TACR[1-3]|NTSR[12]|CCR[0-9]+|CXCR[1-7]|CX3CR1|XCR1|ACKR[1-4]|C3AR1|C5AR[12]|FPR[1-3]|BDKRB[12]|GAL[R]?[1-3]|HCRTR[12]|OXTR|AVPR[12][AB]?|GHSR|MC[1-5]R|CCK[AB]R|GRPR|NMUR[12]|SSTR[1-5]|TRHR|GNRHR|KISS1R|APLNR|CMKLR1|F2R|F2RL[1-3]|MLNR|PTH[12]R|CALCR|CRHR[12]|GCGR|GIPR|GLP[12]R|SCTR|VIPR[12]|RXFP[1-4]|UTS2R)$"),
]
_NB = [(c, re.compile(p)) for c, p in NEIGHBOUR_CLASS]


def neighbour_class(gene: str) -> str:
    g = str(gene).upper()
    return next((c for c, p in _NB if p.match(g)), "")


@dataclass
class Evidence:
    label: str
    detail: str
    source: str


@dataclass
class Hyp:
    statement: str
    score: float
    why: List[str]
    against: List[str] = field(default_factory=list)
    assays: List[str] = field(default_factory=list)
    expect: Dict[str, str] = field(default_factory=dict)      # assay key -> text of the outcome that would support this hypothesis
    components: Dict[str, float] = field(default_factory=dict)


@dataclass
class Question:
    title: str
    hyps: List[Hyp]
    note: str = ""


@dataclass
class Dossier:
    gene: str
    status: str
    present: List[Evidence]
    questions: List[Question]
    interest: float = 0.0
    contexts: List[str] = field(default_factory=list)

    @property
    def headline(self) -> str:
        top = [q.hyps[0].statement for q in self.questions if q.hyps]
        return "; ".join(top[:3])


@dataclass
class Pattern:
    title: str
    present: List[Evidence]
    hyps: List[Hyp]


def _f(x, d=float("nan")) -> float:
    try:
        v = float(x)
        return v if v == v else d
    except (TypeError, ValueError):
        return d


def _parse_neighbours(text: str) -> List[tuple]:
    return [(m.group(1).upper(), float(m.group(2))) for m in re.finditer(r"([A-Za-z0-9\-]+)\s*\(r=([0-9.\-]+)\)", str(text or ""))]


def _norm(d: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(v, 0) for v in d.values())
    return {k: (max(v, 0) / s if s else 0.0) for k, v in d.items()}


def _coupling_hyps(gene, row, coupling, val, prec_sig, nb) -> Question:
    votes: Dict[str, float] = defaultdict(float)
    for g, r in nb:
        c = coupling.get(g)
        if c:
            votes[c] += max(r, 0)
    share = _norm(votes)
    reliable = bool(val.get("ok") and val.get("beats_baseline"))
    rel = 1.0 if reliable else 0.4
    classes = set(share) | set(prec_sig)
    hyps = []
    for c in classes:
        s_co, s_pr = share.get(c, 0.0), prec_sig.get(c, 0.0)
        score = 0.7 * rel * s_co + 0.3 * s_pr
        why, against = [], []
        mine = [f"{g} (r={r:.2f})" for g, r in nb if coupling.get(g) == c]
        if mine:
            why.append(f"Co-expressed with {c}-coupled receptors in your matrix: {', '.join(mine)}.")
        if val.get("ok"):
            why.append(f"The co-expression method {'recovered' if reliable else 'did not clearly beat the baseline on'} the characterised receptors in your own data ({val.get('hits')}/{val.get('n')} correct, naive baseline {val.get('baseline')}).")
        if s_pr:
            why.append(f"The precedent model also leans {c} (relative support {s_pr:.2f}), based on tissue context only.")
        if s_co and not s_pr and prec_sig:
            against.append("The precedent model leans a different class, so two lines of evidence disagree.")
        if s_pr and not s_co and share:
            against.append("Its expression neighbours point to a different class.")
        if not reliable:
            against.append("The co-expression self-test did not beat the baseline, so its calls carry less weight.")
        hyps.append(Hyp(f"Couples to {c}", score, why, against, assays_for("coupling"), {"gprotein_panel": {"Gq": "Gq/11", "Gi": "Gi/o", "Gs": "Gs"}.get(c, c)},
                        {"co-expression": round(s_co, 2), "precedent": round(s_pr, 2), "reliability": rel}))
    hyps.sort(key=lambda h: -h.score)
    note = ""
    co_top = max(share, key=share.get) if share else ""
    pr_top = max(prec_sig, key=prec_sig.get) if prec_sig else ""
    if co_top and pr_top and co_top != pr_top:
        better = ("The co-expression call is better supported: it was tested on your own characterised receptors, whereas the precedent call uses tissue context only and has not been benchmarked for coupling."
                  if reliable else "Neither is strongly supported: the co-expression method did not clearly beat its baseline on your data.")
        note = f"Two lines of evidence disagree: co-expression says {co_top}, the precedent model says {pr_top}. {better} The G-protein panel settles it, and its outcome table says how to read each possibility."
    return Question("What does it couple to?", hyps, note)


def _coupling_likelihood(cases, cls, coupling) -> float:
    n = [c for c in cases if c.ligand_class == cls]
    return (sum(c.coupling == coupling for c in n) + 1) / (len(n) + 3)


def _ligand_hyps(gene, res, cases, pred_coupling, nb, tissues_known) -> Question:
    prec = {}
    prec_h = {}
    for h in (res.hypotheses if res is not None else []):
        if h.category == "ligand-class":
            m = re.search(r"by an? (.+?)-class", h.statement)
            if m:
                prec[m.group(1)] = h.support
                prec_h[m.group(1)] = h
    nbc = Counter()
    nb_by = defaultdict(list)
    for g, r in nb:
        c = neighbour_class(g)
        if c:
            nbc[c] += max(r, 0)
            nb_by[c].append(g)
    nbs = _norm(nbc)
    classes = set(prec) | set(nbs)
    lik = {c: _coupling_likelihood(cases, c, pred_coupling) for c in classes} if pred_coupling in ("Gq", "Gi", "Gs") else {}
    likn = _norm(lik)
    hyps = []
    for c in classes:
        comp = {"precedent": round(prec.get(c, 0.0), 2), "coupling fit": round(likn.get(c, 0.0), 2), "neighbours": round(nbs.get(c, 0.0), 2)}
        score = 0.55 * comp["precedent"] + 0.25 * comp["coupling fit"] + 0.20 * comp["neighbours"]
        why, against = [], []
        h = prec_h.get(c)
        if h is not None:
            for r in h.rationale[:3]:
                why.append("Documented precedent: " + r + ".")
            why.append(f"{len(h.precedents)} documented deorphanisation(s) in this class match its context (relative support {h.support:.2f}).")
        if c in nb_by:
            why.append(f"Its closest co-expressed characterised receptors include {', '.join(nb_by[c])}, which bind {c} ligands (receptor nomenclature).")
        if lik:
            why.append(f"Among documented {c} receptors, {lik[c] * 100:.0f}% (smoothed) couple through {pred_coupling}, which fits the coupling predicted from your data.")
        if not h and tissues_known:
            against.append("No documented precedent in this class shares its tissue context.")
        if not tissues_known:
            against.append("Its measured context maps to no tissue in the precedent library, so the precedent model cannot weigh in; this ranking rests on weaker evidence.")
        hyps.append(Hyp(f"May bind a {c}-type ligand", score, why, against, assays_for("ligand-class"), {}, comp))
    hyps.sort(key=lambda x: -x.score)
    tot = sum(h.score for h in hyps) or 1
    for h in hyps:
        h.score = h.score / tot
    note = "Relative support among the classes shown, not a probability. The precedent model is only modestly better than always guessing the commonest class, so treat the order as where to start screening, not as an answer."
    if not tissues_known:
        note = "The precedent model abstains: " + note
    return Question("What might it bind?", hyps, note)


def _role_hyps(gene, r_de, progs, alt_rows, tau, ctxs, disease_h, state_name) -> Question:
    hyps: List[Hyp] = []
    for _, p in progs.iterrows():
        if _f(p["FDR"], 1) <= 0.05 and _f(p["Pearson r (log)"], 0) >= 0.7:
            rr = float(p["Pearson r (log)"])
            hyps.append(Hyp(f"Linked to the {p['Program']} program", 0.5 * rr, [f"Tracks {p['Program']} across your contexts (r = {rr:.2f}, FDR {p['FDR']:.2g}, {p['Program genes used']} program genes)."],
                            ["Correlation across few contexts often reflects shared cell identity, not regulation: both can simply be high in the same cell types."], assays_for("program"),
                            {"program_test": "Blocking the program lowers receptor RNA"}, {"r": round(rr, 2)}))
    if r_de is not None and abs(_f(r_de.effect, 0)) >= 1.0 and state_name:
        e = float(r_de.effect)
        pv = f", p = {r_de.significance:.2g}" if r_de.significance is not None else ""
        hyps.append(Hyp(f"{'Marks or promotes' if e > 0 else 'Is lost from'} the state: {state_name}", min(0.9, abs(e) / 4), [f"{r_de.effect_type} {e:+.2f}{pv} in your differential table."],
                        ["A change in RNA does not show the receptor does anything in that state."], assays_for("state"), {"knockdown_function": "Loss improves function"}, {"effect": round(e, 2)}))
    for x in alt_rows[:2]:
        hyps.append(Hyp(f"Altered in {x['cancer']}: a possible tumour dependency", min(0.9, x["max"] * 2), [f"{x['text']} in {x['cancer']} (your alteration table)."],
                        ["Amplicons carry many genes; the receptor may be amplified only because a neighbour is the driver."], assays_for("disease"), {}, {"freq": round(x["max"], 2)}))
    if disease_h is not None:
        hyps.append(Hyp(disease_h.statement.split(", by analogy")[0] if "by analogy" in disease_h.statement else disease_h.statement, 0.4 * disease_h.support,
                        ["By analogy with: " + "; ".join(p["gene"] + " (" + p.get("later_outcome", "") + ")" for p in disease_h.precedents[:2]) + "."],
                        ["An analogy from tissue context, not evidence about this receptor."], assays_for("disease"), {}, {"precedent": round(disease_h.support, 2)}))
    if tau >= 0.8 and ctxs:
        hyps.append(Hyp(f"A marker that could allow targeting of {ctxs[0]}", 0.3, [f"Highly context-specific (tau = {tau:.2f}); highest in {', '.join(ctxs[:2])}."],
                        ["Needs protein-level confirmation at the cell surface."], assays_for("specificity"), {}, {"tau": round(tau, 2)}))
    hyps.sort(key=lambda h: -h.score)
    return Question("What might it be doing?", hyps)


def build_dossier(a, gene: str, alt=None) -> Optional[Dossier]:
    gp = a.gpcrome
    if gp is None or not len(gp.orphans):
        return None
    row = gp.orphans[gp.orphans["GPCR"] == gene]
    if not len(row):
        return None
    row = row.iloc[0]
    res = next((r for r in (a.summary.results if a.summary is not None else []) if r.gene.upper() == gene.upper()), None)
    coupling = a.wb.coupling if a.wb is not None else {}
    nb = _parse_neighbours(row["Supported neighbours"])
    ctxs = a.matrix_tissues.get(gene.upper(), {}).get("contexts") or [str(row["Most expressed in"])]
    tissues = a.matrix_tissues.get(gene.upper(), {}).get("tissues", [])
    present: List[Evidence] = []
    if res is not None and _f(res.effect) == _f(res.effect):
        present.append(Evidence("Differential expression", f"{res.effect_type} {res.effect:+.2f}" + (f", p = {res.significance:.2g}" if res.significance is not None else ""), "your differential table"))
    present.append(Evidence("Where it is expressed", f"highest in {', '.join(ctxs[:3])}; specificity tau = {float(row['Specificity (tau)']):.2f}", "your matrix"))
    pc = str(row["Predicted coupling"])
    if nb:
        present.append(Evidence("Expression neighbours", ", ".join(f"{g} (r={r:.2f}{', ' + coupling[g] if g in coupling else ''})" for g, r in nb[:5]), "your matrix"))
    progs = a.wb.programs[a.wb.programs["GPCR"] == gene] if a.wb is not None and len(a.wb.programs) else None
    if progs is not None:
        for _, p in progs[(progs["FDR"] <= 0.05)].iterrows():
            present.append(Evidence("Tracks a program", f"{p['Program']} (r = {p['Pearson r (log)']:.2f}, FDR {p['FDR']:.2g})", "your matrix"))
    alt_rows = []
    if alt is not None:
        from .alterations import summary as alt_summary
        alt_rows = alt_summary(alt, gene)
        for x in alt_rows[:2]:
            present.append(Evidence("Altered in tumours", f"{x['text']} in {x['cancer']}", "your alteration table"))
    prec_sig = {}
    if res is not None:
        for h in res.hypotheses:
            m = re.search(r"couples to (G\w+)", h.statement)
            if h.category == "signaling" and m:
                prec_sig[m.group(1)] = h.support
    q_c = _coupling_hyps(gene, row, coupling, gp.validation or {}, prec_sig, nb) if (nb or prec_sig) else Question("What does it couple to?", [], "No supported co-expression neighbours and no precedent call.")
    pred = pc if pc in ("Gq", "Gi", "Gs") else (q_c.hyps[0].statement.split()[-1] if q_c.hyps else "")
    q_l = _ligand_hyps(gene, res, a.engine.cases, pred, nb, bool(tissues))
    dh = next((h for h in (res.hypotheses if res else []) if h.category == "disease-association"), None)
    state = a.ctx.comparison if getattr(a, "ctx", None) is not None and a.ctx.comparison else ""
    q_r = _role_hyps(gene, res, progs if progs is not None else __import__("pandas").DataFrame(columns=["GPCR", "Program", "Pearson r (log)", "FDR", "Program genes used"]), alt_rows, float(row["Specificity (tau)"]), ctxs, dh, state)
    interest = (abs(_f(res.effect, 0)) * min(30, -math.log10(max(res.significance, 1e-30))) if res is not None and res.significance else abs(_f(res.effect, 0)) if res is not None else 0) + float(row["Specificity (tau)"])
    return Dossier(gene, "orphan", present, [q for q in (q_c, q_l, q_r) if q.hyps or q.note], interest, ctxs)


def build_all(a, alt=None, limit: int = 8) -> List[Dossier]:
    if a.gpcrome is None or not len(a.gpcrome.orphans):
        return []
    out = [d for d in (build_dossier(a, g, alt) for g in a.gpcrome.orphans["GPCR"]) if d]
    return sorted(out, key=lambda d: -d.interest)[:limit]


def experiment_patterns(a, dossiers: List[Dossier], alt=None) -> List[Pattern]:
    """What the experiment says as a whole: patterns that only show up when the receptors are read together."""
    pats: List[Pattern] = []
    wb = a.wb
    if wb is not None and wb.enrichment is not None and len(wb.enrichment.table):
        t = wb.enrichment.table
        ccol = next((c for c in t.columns if "class" in str(c).lower()), t.columns[0])
        fcol = next((c for c in t.columns if "fdr" in str(c).lower()), None)
        for _, r in t.iterrows():
            if fcol and _f(r[fcol], 1) <= 0.05:
                cls, nes = str(r[ccol]), _f(r.get("NES"), 0)
                up = nes > 0
                lead = ""
                if wb.enrichment.curves and cls in wb.enrichment.curves:
                    lead = ", ".join(map(str, (wb.enrichment.curves[cls].get("leading") or [])[:6])) if isinstance(wb.enrichment.curves[cls], dict) else ""
                present = [Evidence("Coupling-class enrichment", f"{cls}-coupled receptors are {'over' if up else 'under'}-represented in {a.wb.enrich_contrast} (NES {nes:+.2f}, FDR {r[fcol]:.2g})" + (f"; leading edge: {lead}" if lead else ""), "your ranking and the coupling table")]
                path = PATHWAYS.get(cls.replace("Gi/o", "Gi").replace("Gq/11", "Gq"), "")
                hyps = [Hyp(f"A {cls}-driven pathway characterises this state", 0.6, [path] if path else ["The class's canonical second messenger is the likely readout."],
                            ["Depends on the coupling table, which is unverified unless you uploaded your own."], ["second_messenger", "antagonist_pathway", "knockdown_function"], {}),
                        Hyp("Cell-composition effect: these receptors are simply high in the cell types that dominate the foreground", 0.3,
                            ["Many receptors of one class can be high in the same cell type for reasons unrelated to signalling."], [], ["protein_validation"], {}),
                        Hyp("Artefact of the coupling table", 0.1, ["Mis-assigned couplings can create or hide an enrichment."], [], [], {})]
                pats.append(Pattern(f"{cls} receptors {'dominate' if up else 'are depleted in'} the cell state", present, hyps))
    if dossiers:
        tally: Dict[str, List[str]] = defaultdict(list)
        for d in dossiers:
            q = next((q for q in d.questions if q.title == "What might it bind?"), None)
            if q and q.hyps and q.hyps[0].components.get("precedent", 0) > 0 and q.hyps[0].components.get("neighbours", 0) > 0:   # needs independent backing, or it is just the shared tissue
                tally[q.hyps[0].statement.replace("May bind a ", "").replace("-type ligand", "")].append(d.gene)
        for cls, genes in sorted(tally.items(), key=lambda kv: -len(kv[1])):
            if len(genes) >= 2:
                pats.append(Pattern(f"{len(genes)} orphans point to the same ligand class", [Evidence("Shared top ligand class", f"{cls}: {', '.join(genes)}", "precedent model, applied to each receptor's own context")],
                                    [Hyp(f"A shared {cls} signalling axis operates in this tissue", 0.5, [f"{len(genes)} orphans independently rank {cls} first from their own expression contexts."], ["The precedent model and the expression neighbours are separate lines of evidence, but the library is small."], ["ligand_screen", "ligand_presence"], {}),
                                     Hyp("Coincidence of a thin precedent library", 0.3, ["The library has few cases for some classes."], [], [], {})]))
    if wb is not None and len(wb.axes):
        for _, r in wb.axes.head(2).iterrows():
            present = [Evidence("Ligand-producing and receptor-bearing contexts", f"{r['Ligand']}: {r['Producer']} high in {r['Source context']}; {r['Receptor']} ({r['Receptor coupling']}) high in {r['Target context']} ({r['Relationship']})", "your matrix")]
            pats.append(Pattern(f"A {r['Ligand']} axis: {r['Source context']} to {r['Target context']}", present,
                                [Hyp(f"{r['Ligand']} made in {r['Source context']} signals to {r['Target context']} through {r['Receptor']}", 0.6, ["Both halves of the axis are expressed in your data."], ["RNA for the synthesising enzyme is a proxy for the molecule."], ["conditioned_medium", "ligand_presence"], {}),
                                 Hyp("The enzyme is high but the molecule is not produced or does not accumulate", 0.3, ["Enzyme RNA does not guarantee product."], [], ["ligand_presence"], {})]))
    return pats


@dataclass
class PlanItem:
    title: str
    targets: List[str]
    why: List[str]
    assay: str
    expect: Dict[str, str] = field(default_factory=dict)      # gene -> the outcome that would support the hypothesis for that gene
    order: int = 0


def experiment_plan(a, dossiers: Optional[List[Dossier]] = None, patterns: Optional[List[Pattern]] = None) -> List[PlanItem]:
    """Next experiments straight from the uploaded experiment, grouped so that one plate answers several receptors. Works from a differential table alone."""
    items: List[PlanItem] = []
    ds = dossiers or []
    orphans: Dict[str, dict] = {}
    for d in ds:
        qc = next((q for q in d.questions if q.title.startswith("What does it couple")), None)
        ql = next((q for q in d.questions if q.title.startswith("What might it bind")), None)
        qr = next((q for q in d.questions if q.title.startswith("What might it be")), None)
        orphans[d.gene] = {"coup": qc.hyps[0] if qc and qc.hyps else None, "lig": ql.hyps[0] if ql and ql.hyps else None, "role": qr.hyps[0] if qr and qr.hyps else None,
                           "ev": "; ".join(f"{e.label}: {e.detail}" for e in d.present[:2])}
    if not orphans and a.summary is not None:
        for r in a.summary.results:
            lig = next((h for h in r.hypotheses if h.category == "ligand-class"), None)
            sig = next((h for h in r.hypotheses if h.category == "signaling"), None)
            m_l = re.search(r"by an? (.+?)-class", lig.statement) if lig else None
            m_s = re.search(r"couples to (G\w+)", sig.statement) if sig else None
            orphans[r.gene] = {"coup": Hyp(f"Couples to {m_s.group(1)}", sig.support, [f"Precedent model, tissue context only (support {sig.support:.2f})."]) if m_s else None,
                               "lig": Hyp(f"May bind a {m_l.group(1)}-type ligand", lig.support, [f"Precedent model, tissue context only (support {lig.support:.2f})."]) if m_l else None,
                               "role": Hyp("Marks or promotes the state", min(.9, abs(_f(r.effect, 0)) / 4), [f"{r.effect_type} {_f(r.effect, 0):+.2f}"]) if abs(_f(r.effect, 0)) >= 1 else None,
                               "ev": f"{r.effect_type} {_f(r.effect, 0):+.2f}" + (f", p = {r.significance:.2g}" if r.significance is not None else "")}
    if not orphans:
        return items
    genes = list(orphans)
    items.append(PlanItem("Confirm the receptor protein is there before anything else", genes[:6], ["RNA is not protein. Every hypothesis below assumes the receptor is expressed at the protein level in the same cells.", "Orphan-receptor antibodies are unreliable, so validate against a knockout."], "protein_validation", {}, 1))
    cg = {g: o["coup"] for g, o in orphans.items() if o["coup"]}
    if cg:
        items.append(PlanItem("G-protein coupling profile, all candidate orphans on one plate", list(cg), [f"{g}: {h.statement.lower()} ({h.why[0][:120]})" for g, h in cg.items()], "gprotein_panel",
                              {g: {"Gq": "Gq/11", "Gi": "Gi/o", "Gs": "Gs"}.get(h.statement.split()[-1], h.statement.split()[-1]) for g, h in cg.items()}, 2))
    no_c = [g for g, o in orphans.items() if not o["coup"]]
    if no_c:
        items.append(PlanItem("G-protein coupling profile, no prediction available: run the full panel", no_c,
                              ["No coupling prediction could be made for these (no supported co-expression neighbours and no precedent in the context given), so run every G-protein family and let the data decide.",
                               "Include a basal-activity check against empty vector: many orphans signal without a ligand."], "gprotein_panel", {}, 2))
    byc: Dict[str, List[str]] = defaultdict(list)
    for g, o in orphans.items():
        if o["lig"]:
            byc[o["lig"].statement.replace("May bind a ", "").replace("-type ligand", "")].append(g)
    for cls, gs in byc.items():
        items.append(PlanItem(f"Focused {cls} library screen on {', '.join(gs[:5])}", gs, [f"{g}: top-ranked class is {cls}." + (" " + orphans[g]["lig"].why[0][:110] if orphans[g]["lig"].why else "") for g in gs[:4]]
                              + ["Run all of them in one screen: the same library and the same empty-vector control serve every receptor."], "ligand_screen", {}, 3))
    no_l = [g for g, o in orphans.items() if not o["lig"]]
    if no_l:
        items.append(PlanItem("Unbiased ligand screen: conditioned medium and broad focused libraries", no_l,
                              ["The precedent model has no documented case matching these receptors' context, so it cannot rank ligand classes. Set the tissue in the sidebar to give it something to match, or screen broadly.",
                               "Start with conditioned medium from the cell type where each receptor is highest in your data, plus lipid-mediator, nucleotide and metabolite libraries."], "ligand_screen", {}, 3))
    rg = [g for g, o in orphans.items() if o["role"] and o["role"].statement.startswith("Linked to")]
    if rg:
        items.append(PlanItem("Is each receptor upstream or downstream of the program it tracks?", rg[:5], [f"{g}: {orphans[g]['role'].statement}. {orphans[g]['role'].why[0][:110]}" for g in rg[:4]], "program_test", {}, 4))
    kg = [g for g, o in orphans.items() if o["role"] and o["role"].statement.startswith(("Marks", "Is lost"))]
    if kg:
        items.append(PlanItem("Does losing the receptor change the cell state?", kg[:5], [f"{g}: {orphans[g]['ev']}" for g in kg[:4]], "knockdown_function", {}, 5))
    for p in (patterns or []):
        for h in p.hyps[:1]:
            for k in h.assays[:1]:
                if k in ("conditioned_medium", "ligand_presence"):
                    items.append(PlanItem(f"Test the axis: {p.title}", [], [e.detail for e in p.present], k, {}, 6))
    return sorted(items, key=lambda i: i.order)
