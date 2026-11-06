"""Target evidence audit: how far should you trust a receptor-disease link before you spend months on it?

The audit does not look anything up and invents nothing. It takes evidence LINES (each with a named source), applies written rules,
and returns a tier, the red flags, what would raise confidence, and the cheapest experiment that separates a real link from a false one.

Tiers (the rules are stated here so anyone can argue with them):
  Strong       3 or more independent sources, 2 or more kinds of evidence, at least one causal kind (genetics or perturbation),
               and nothing against it.
  Mixed        2 or more independent sources with 2 or more kinds or a causal kind; or a strong case that something argues against.
  Weak         one independent source, or support from expression or literature mentions alone.
  Contradicted a strong line argues against it and at most one source supports it.
  Unchecked    no evidence lines at all.
A tier is a statement about the evidence you supplied, not about the biology. 'Independent' means a different study_id; two lines from
one paper are one source.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Dict, List, Optional

KINDS = ("genetics", "perturbation", "expression", "literature", "tractability", "other")
CAUSAL = {"genetics", "perturbation"}
DIRECTIONS = ("supports", "against", "neutral")
STRENGTHS = ("strong", "moderate", "weak")
TIERS = ("Strong", "Mixed", "Weak", "Contradicted", "Unchecked")

FLAG_RULES: Dict[str, dict] = {
    "single_source": {"why": "Everything rests on one study. One study can be wrong, or specific to one lab's cells or cohort.",
                      "test": "Find or run an independent line of evidence in a different cohort or system before committing."},
    "expression_only": {"why": "A receptor can be switched on in a tissue without doing anything there; expression is not function.",
                        "test": "A knockdown or knockout in the relevant cells, read against a phenotype that matters to the disease."},
    "no_causal_evidence": {"why": "There is no genetic or perturbation evidence, so nothing shows the receptor changes the disease rather than just tracking it.",
                           "test": "Look for human genetic evidence (variants, GWAS fine-mapping, loss-of-function carriers) or run a perturbation."},
    "cell_line_only": {"why": "Results from a single cell line often do not carry over to primary cells or patients.",
                       "test": "Repeat the key result in primary cells or a second, unrelated model."},
    "gwas_nearest_gene": {"why": "A GWAS hit is often assigned to the nearest gene, which is frequently not the causal one.",
                          "test": "Check fine-mapping and eQTL colocalisation to see which gene at the locus is actually affected."},
    "low_expression_in_tissue": {"why": "If the receptor is barely expressed in the disease tissue, a role there is unlikely.",
                                 "test": "Confirm expression with a second method (RNA and protein) in the relevant cell type."},
    "antibody_only": {"why": "Receptor antibodies are often unreliable; a band or stain without a knockout control may not be the target.",
                      "test": "Validate the antibody on knockout or knockdown cells, or confirm with a tagged receptor."},
    "species_mismatch": {"why": "Pharmacology and expression often differ between rodent and human, and a human-only gene can change the response.",
                         "test": "Test the human receptor and human samples before relying on the rodent result."},
    "paralog_redundancy": {"why": "A close relative may cover for the receptor, hiding its effect or making a drug less specific.",
                           "test": "Check the paralog's expression and test the double knockdown."},
    "no_human_evidence": {"why": "All the support comes from animals or cells. Nothing yet shows the effect in people.",
                          "test": "Look for human genetic, biobank or early clinical data, or test the key result in human cells or tissue."},
    "class_dependent": {"why": "The effect appeared with one type of compound but not another, so it may not carry over to a different drug class.",
                        "test": "Test a second, structurally different compound against the same endpoint before generalising."},
    "disputed_ligand": {"why": "The ligand claims for this receptor conflict between laboratories, so any pathway built on one is shaky.",
                        "test": "Do not rely on a ligand claim until an independent group reproduces it; use a ligand-free readout first."},
}


@dataclass
class EvidenceLine:
    gene: str
    disease: str
    kind: str
    direction: str
    strength: str
    summary: str
    source: str            # a named source: a paper, a database release, or "Your experiment"
    url: str = ""
    study_id: str = ""     # lines with the same study_id count as one source; defaults to `source`
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.kind, self.direction, self.strength = self.kind.strip().lower(), self.direction.strip().lower(), self.strength.strip().lower()
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)} (got '{self.kind}')")
        if self.direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {', '.join(DIRECTIONS)}")
        if self.strength not in STRENGTHS:
            raise ValueError(f"strength must be one of {', '.join(STRENGTHS)}")
        if not str(self.source).strip():
            raise ValueError("every evidence line needs a named source (the truth gate)")
        self.study_id = (self.study_id or self.source).strip()
        self.tags = [t.strip().lower() for t in self.tags if t.strip()]


@dataclass
class Audit:
    gene: str
    disease: str
    tier: str
    reasons: List[str]
    flags: List[dict]
    lines: List[EvidenceLine]
    to_raise: List[str]
    cheapest_test: str


def _disputed(gene: str) -> bool:
    try:
        from .reported import REPORTED
        r = REPORTED.get(gene.upper())
        return bool(r) and any(w in r.caution.lower() for w in ("contest", "disput", "conflict"))
    except Exception:  # noqa: BLE001
        return False


def audit_target(gene: str, disease: str, lines: List[EvidenceLine]) -> Audit:
    g = gene.upper()
    mine = [l for l in lines if l.gene.upper() == g and (not disease or l.disease.lower() in ("", disease.lower()))]
    evid = [l for l in mine if l.kind != "tractability"]
    sup = [l for l in evid if l.direction == "supports"]
    ag = [l for l in evid if l.direction == "against"]
    src = {l.study_id for l in sup}
    kinds = {l.kind for l in sup}
    causal = bool(kinds & CAUSAL)
    strong_against = any(l.strength == "strong" for l in ag)
    reasons: List[str] = []
    if not evid:
        tier = "Unchecked"
        reasons.append("No evidence lines were supplied for this receptor and disease.")
    elif strong_against and len(src) <= 1:
        tier = "Contradicted"
        reasons.append("A strong line argues against the link and at most one source supports it.")
    elif strong_against:
        tier = "Mixed"
        reasons.append("A strong line argues against the link even though several sources support it.")
    elif len(src) >= 3 and len(kinds) >= 2 and causal and not ag:
        tier = "Strong"
        reasons.append(f"{len(src)} separate studies (counted by study_id; the tool cannot tell whether two are from the same group), {len(kinds)} kinds of evidence including causal evidence, and nothing against it.")
    elif len(src) >= 2 and (len(kinds) >= 2 or causal):
        tier = "Mixed"
        reasons.append(f"{len(src)} separate studies (counted by study_id; the tool cannot tell whether two are from the same group)" + (", but " + str(len(ag)) + " line(s) argue against it" if ag else ", but not enough kinds of evidence or causal support for Strong") + ".")
    else:
        tier = "Weak"
        reasons.append("Only one independent source supports it." if len(src) == 1 else "Support is limited to one weak or non-causal line.")
    flags: List[dict] = []

    def add(name: str, detail: str = ""):
        if not any(f["flag"] == name for f in flags):
            flags.append({"flag": name, "why": FLAG_RULES[name]["why"], "test": FLAG_RULES[name]["test"], "detail": detail})

    if tier != "Unchecked":
        if len(src) == 1:
            add("single_source", f"only {next(iter(src))}")
        if sup and kinds <= {"expression", "literature", "other"}:
            add("expression_only")
        if sup and not causal:
            add("no_causal_evidence")
        for l in sup:
            for t in l.tags:
                if t in FLAG_RULES and t not in ("single_source", "expression_only", "no_causal_evidence", "disputed_ligand"):
                    add(t, l.source)
    if _disputed(g):
        add("disputed_ligand")
    to_raise: List[str] = []
    if tier in ("Weak", "Mixed", "Contradicted", "Unchecked"):
        if not causal:
            to_raise.append("Add causal evidence: human genetics or a knockdown/knockout phenotype.")
        if len(src) < 3:
            to_raise.append(f"Add independent sources (now {len(src)}; Strong needs 3).")
        if len(kinds) < 2:
            to_raise.append("Add a second kind of evidence (for example expression plus perturbation).")
        if ag:
            to_raise.append("Resolve the evidence that argues against the link: find out why the studies disagree.")
    tests = [f["test"] for f in flags]
    cheapest = tests[0] if tests else ("The link has support from several independent kinds of evidence; move to the functional experiment." if tier == "Strong" else "Collect evidence lines first; there is nothing to test yet.")
    return Audit(g, disease, tier, reasons, flags, mine, to_raise, cheapest)


def lines_from_csv(text: str) -> List[EvidenceLine]:
    """Read evidence lines from CSV. Columns: gene, disease, kind, direction, strength, summary, source, url, study_id, tags (separate tags with ;)."""
    rows = csv.DictReader(io.StringIO(text))
    out, errs = [], []
    for i, r in enumerate(rows, start=2):
        try:
            out.append(EvidenceLine(gene=(r.get("gene") or "").strip(), disease=(r.get("disease") or "").strip(), kind=r.get("kind") or "other",
                                    direction=r.get("direction") or "supports", strength=r.get("strength") or "weak", summary=(r.get("summary") or "").strip(),
                                    source=(r.get("source") or "").strip(), url=(r.get("url") or "").strip(), study_id=(r.get("study_id") or "").strip(),
                                    tags=(r.get("tags") or "").split(";")))
        except ValueError as e:
            errs.append(f"row {i}: {e}")
    if errs:
        raise ValueError("; ".join(errs))
    return out


def your_experiment_line(gene: str, disease: str, effect: float, effect_type: str, significance: Optional[float] = None) -> EvidenceLine:
    """The one evidence line the app can create by itself: the user's own expression result, labelled as such."""
    sig = f", adjusted p {significance:.2g}" if significance is not None and significance == significance else ""
    return EvidenceLine(gene=gene, disease=disease, kind="expression", direction="supports", strength="moderate" if significance and significance < 0.01 else "weak",
                        summary=f"{effect_type} {effect:.2f}{sig} in your uploaded experiment", source="Your experiment", study_id="Your experiment")


def audit_markdown(a: Audit) -> str:
    L = [f"### {a.gene}" + (f" and {a.disease}" if a.disease else ""), "", f"**Evidence tier: {a.tier}.** " + " ".join(a.reasons), ""]
    if a.lines:
        L += ["| Kind | Direction | Strength | What it shows | Source |", "|---|---|---|---|---|"]
        for l in a.lines:
            src = f"[{l.source}]({l.url})" if l.url else l.source
            L.append(f"| {l.kind} | {l.direction} | {l.strength} | {l.summary.replace('|', '/')} | {src} |")
        L.append("")
    if a.flags:
        L += ["**Red flags**", ""] + [f"- **{f['flag'].replace('_', ' ')}**: {f['why']} Cheapest check: {f['test']}" for f in a.flags] + [""]
    if a.to_raise:
        L += ["**What would raise confidence**", ""] + [f"- {x}" for x in a.to_raise] + [""]
    L += [f"**Cheapest experiment that separates a real link from a false one:** {a.cheapest_test}", "",
          "_The tier describes the evidence supplied, not the biology. Every line above has a named source; check each against the paper before relying on it._"]
    return "\n".join(L)


TEMPLATE_CSV = ("gene,disease,kind,direction,strength,summary,source,url,study_id,tags\n"
                "EXAMPLE_GENE,example disease,genetics,supports,moderate,what the paper found in one sentence,Author et al. Journal Year,https://example.org/paper,Author2020,gwas_nearest_gene\n")


# A worked example for a non-GPCR target (the alpha7 nicotinic receptor in chronic neuropathic pain). Every line names its source; two are second-hand
# (read through a 2022 review, primary paper not read) and are marked so. Independence between the three animal studies has NOT been checked.
EXAMPLE_A7_CSV = (
"gene,disease,kind,direction,strength,summary,source,url,study_id,tags\n"
"CHRNA7,chronic neuropathic pain,perturbation,supports,moderate,\"Type II PAM PNU-120596 reduced mechanical allodynia and thermal hyperalgesia in mouse chronic constriction injury; antagonist MLA reversed it; type I PAM NS1738 was inactive (abstract read)\","
"\"Freitas thesis, VCU 2012 (published as PubMed 23079470)\",https://scholarscompass.vcu.edu/etd/2827/,Freitas2012,species_mismatch;no_human_evidence;class_dependent\n"
"CHRNA7,chronic neuropathic pain,perturbation,supports,weak,\"GAT107 (agonist-PAM) reduced CCI neuropathic pain in mice (second-hand: read via a 2022 review; independence from other studies not checked)\","
"Frontiers Mol Neurosci 2022 review: Targeting alpha7 nAChRs for chronic pain,https://www.frontiersin.org/journals/molecular-neuroscience/articles/10.3389/fnmol.2022.970040/full,GAT107 study via review,species_mismatch;no_human_evidence\n"
"CHRNA7,chronic neuropathic pain,perturbation,supports,weak,\"PAM-4 reduced formalin and CCI pain without motor impairment in mice (second-hand: read via a 2022 review; independence not checked)\","
"Frontiers Mol Neurosci 2022 review: Targeting alpha7 nAChRs for chronic pain,https://www.frontiersin.org/journals/molecular-neuroscience/articles/10.3389/fnmol.2022.970040/full,PAM-4 study via review,species_mismatch;no_human_evidence\n"
"CHRNA7,chronic neuropathic pain,genetics,against,moderate,\"Human-only CHRFAM7A acts as a dominant negative regulator of alpha7: transgenic mice had more pain behaviour and a weaker dorsal root ganglion response to the agonist nicotine; human chondrocytes with two copies responded less. Tested an agonist, not a PAM\","
"Courties et al. Ann Rheum Dis 2023 (PMID 36627169),https://pmc.ncbi.nlm.nih.gov/articles/PMC10101906,Courties2023,\n"
"CHRNA7,chronic neuropathic pain,other,against,weak,\"No clinical trials of alpha7 agonists or PAMs in chronic pain are available (2022 review)\","
"Frontiers Mol Neurosci 2022 review: Targeting alpha7 nAChRs for chronic pain,https://www.frontiersin.org/journals/molecular-neuroscience/articles/10.3389/fnmol.2022.970040/full,Review2022 clinical status,\n"
"CHRNA7,chronic neuropathic pain,other,against,weak,\"The alpha7 agonist encenicline missed both co-primary endpoints in two Phase 3 schizophrenia trials (a different disease)\","
"Alzforum: Encenicline misses endpoints in two Phase 3 schizophrenia trials,https://alzforum.org/node/601071,Encenicline Phase 3,\n"
)
