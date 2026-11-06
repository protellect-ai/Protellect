"""Evidence lines the app can build by itself from data it has already retrieved for a searched protein.

Rules: only retrieved data is used; every line names its database; a line only SUPPORTS the link when the retrieved text mentions the disease you typed
(a keyword match on names and labels, not a judgement of direction); everything else is shown as neutral context. Nothing here searches the literature
for drug or pharmacology papers: that still has to be supplied by a person.
"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import quote

from .audit import EvidenceLine

_SKIP = {"chronic", "acute", "primary", "secondary", "type", "disease", "disorder", "disorders", "syndrome", "of", "the", "and", "with", "related"}


def disease_terms(disease: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (disease or "").lower()) if len(t) >= 3 and t not in _SKIP]


def matches(disease: str, text: str) -> bool:
    terms = disease_terms(disease)
    if not terms:
        return False
    blob = (text or "").lower()
    return any(t in blob for t in terms)


def lines_from_bundle(b, disease: str) -> List[EvidenceLine]:
    """Evidence lines from a loaded Bundle (protellect_core.adapters.Bundle). Empty if nothing is loaded."""
    if not getattr(b, "loaded", False):
        return []
    g, d = b.gene, (disease or "").strip()
    out: List[EvidenceLine] = []

    def add(kind, direction, strength, summary, source, url="", sid=None):
        out.append(EvidenceLine(gene=g, disease=d, kind=kind, direction=direction, strength=strength, summary=summary, source=source, url=url, study_id=sid or source))

    plp = list(getattr(b, "plp", []) or [])
    cv_url = f"https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(g)}[gene]"
    if d:
        hit = [v for v in plp if matches(d, v.condition)]
        if hit:
            add("genetics", "supports", "moderate" if len(hit) >= 3 else "weak",
                f"{len(hit)} pathogenic or likely pathogenic germline ClinVar variant(s) list a condition matching '{d}' (keyword match on the condition text; check each record)",
                "ClinVar (retrieved by the app)", cv_url)
        else:
            add("genetics", "neutral", "weak", f"{len(plp)} pathogenic or likely pathogenic germline ClinVar variant(s); none list a condition matching '{d}'", "ClinVar (retrieved by the app)", cv_url)
    else:
        add("genetics", "neutral", "weak", f"{len(plp)} pathogenic or likely pathogenic germline ClinVar variant(s); no disease was entered to compare with", "ClinVar (retrieved by the app)", cv_url)

    dis = [x for x in (getattr(b, "diseases", []) or []) if d and matches(d, f"{x.name} {x.desc}")]
    if dis:
        add("literature", "supports", "moderate", "UniProt lists a disease annotation matching '" + d + "': " + "; ".join(x.name for x in dis[:3]), "UniProt (retrieved by the app)",
            f"https://www.uniprot.org/uniprotkb?query={quote(g)}+AND+organism_id:9606")

    mp = list(getattr(b, "mouse_phenotypes", []) or [])
    if mp:
        hit = [m for m in mp if d and matches(d, str(m.get("label", "")))]
        if hit:
            add("perturbation", "supports", "weak", f"{len(hit)} mouse knockout phenotype label(s) match '{d}' (label match only; the direction of the effect is not assessed): "
                + "; ".join(str(m.get("label")) for m in hit[:4]), "Open Targets / IMPC mouse phenotypes (retrieved by the app)", f"https://platform.opentargets.org/target?search={quote(g)}")
        else:
            add("perturbation", "neutral", "weak", f"{len(mp)} mouse knockout phenotype(s) returned; none match '{d or 'the disease'}'", "Open Targets / IMPC mouse phenotypes (retrieved by the app)",
                f"https://platform.opentargets.org/target?search={quote(g)}")
    else:
        add("perturbation", "neutral", "weak", "No mouse knockout phenotypes were returned (none recorded, or the fetch failed)", "Open Targets / IMPC mouse phenotypes (retrieved by the app)")

    c = {k: v for k, v in (getattr(b, "constraint", {}) or {}).items() if v is not None}
    if c:
        add("genetics", "neutral", "weak", "gnomAD constraint: " + ", ".join(f"{k} {v:.2f}" for k, v in c.items()) + " (context for how tolerant the gene is of loss of function; not evidence for this disease)",
            "gnomAD constraint (retrieved by the app)")

    if getattr(b, "tissue_text", ""):
        add("expression", "neutral", "weak", "UniProt tissue specificity text: " + b.tissue_text[:220] + ("…" if len(b.tissue_text) > 220 else ""), "UniProt (retrieved by the app)",
            f"https://www.uniprot.org/uniprotkb?query={quote(g)}+AND+organism_id:9606")

    papers = [p for p in (getattr(b, "papers", []) or []) if d and matches(d, " ".join(str(p.get(k, "")) for k in ("title", "abstract", "text", "summary")))]
    if papers:
        add("literature", "supports", "weak", f"{len(papers)} retrieved literature record(s) mention '{d}' (a mention is not evidence of a causal link)", "Literature records retrieved by the app")

    tr = getattr(b, "tractability", {}) or {}
    if tr:
        add("tractability", "neutral", "weak", "Open Targets tractability: " + ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in tr.items()), "Open Targets (retrieved by the app)",
            f"https://platform.opentargets.org/target?search={quote(g)}")
    return out


CHECKPOINTS = [
    "Open each source link in the evidence table and confirm the line says what the report says it does.",
    "Run the cross-checks marked 'not run' and add any finding as an evidence line (with its source and whether it supports or argues against).",
    "For every literature line, check whether the studies come from separate groups. The tool counts studies by the ID entered and cannot tell.",
    "Check the lines for selection bias: a person chose which findings to enter. Have a second person search independently and compare, and make sure findings that argue against the link were searched for as hard as those that support it.",
    "Check whether the animal or cell results used both sexes, more than one model, and a compound or perturbation from more than one class.",
    "Record anything you change, and re-run the audit. A changed tier should be traceable to a changed line.",
]
DISCLAIMERS = [
    "The tool does not search the literature for pharmacology papers; a person supplied those lines. When the search button is used, it retrieves records and classifies them by keyword only.",
    "Keyword matching decides whether a retrieved database line mentions the disease. It does not judge the direction or size of an effect.",
    "The strength labels (weak, moderate, strong) and tags are judgements made by whoever entered the line, and they can move the tier.",
    "The tier describes the evidence entered, not the biology, and it is not a probability of clinical success.",
    "The rules have been tested for software correctness only. They have not been tested against real project outcomes.",
    "This is not clinical, regulatory or investment advice.",
]


def cross_check_rows(au, bundle=None, lit=None):
    """(check, status, link label, url) for the genetic and literature cross-checks."""
    g = au.gene
    q = quote(g)
    ran = bool(bundle is not None and getattr(bundle, "loaded", False) and bundle.gene.upper() == g.upper())
    dq = quote(disease_terms(au.disease)[0]) if disease_terms(au.disease) else ""
    return [
        ("ClinVar pathogenic germline variants and their listed conditions", "ran" if ran else "not run: no protein was loaded", "ClinVar", f"https://www.ncbi.nlm.nih.gov/clinvar/?term={q}[gene]"),
        ("gnomAD loss-of-function constraint", "ran (context only)" if ran else "not run", "gnomAD", f"https://gnomad.broadinstitute.org/gene/{q}?dataset=gnomad_r4"),
        ("Mouse knockout phenotypes (Open Targets / IMPC)", "ran (label match only)" if ran else "not run", "Open Targets", f"https://platform.opentargets.org/target?search={q}"),
        ("GWAS associations for the disease or related traits", "partly: via the Open Targets genetic association score" if lit and lit.get("ot") else "not run", "GWAS Catalog gene page", f"https://www.ebi.ac.uk/gwas/genes/{q}"),
        ("Rare-variant and PheWAS results in large cohorts", "not run", "Open Targets (genetic associations)", f"https://platform.opentargets.org/target?search={q}"),
        ("eQTLs and expression in the relevant tissue (for pain: dorsal root ganglion, spinal cord)", "not run", "GTEx", f"https://gtexportal.org/home/gene/{q}"),
        ("Human-specific genes or copy-number variation that change the target's function", "not run", "PubMed search", f"https://pubmed.ncbi.nlm.nih.gov/?term={q}+AND+copy+number+OR+human-specific"),
        ("Published human studies of the disease and the target", "partly: Europe PMC records classified by keyword" if lit and lit.get("records") else "not run", "PubMed search", f"https://pubmed.ncbi.nlm.nih.gov/?term={q}{('+AND+' + dq) if dq else ''}"),
    ]


def report_markdown(au, auto_lines, bundle=None, version="", lit=None, question="") -> str:
    """The downloadable report: tier and evidence, which genetic cross-checks the app ran and which it did not, checkpoints for a person, and disclaimers."""
    from .audit import audit_markdown
    g, d = au.gene, au.disease or "(no disease entered)"
    auto_ids = {id(l) for l in auto_lines}
    n_auto = sum(1 for l in au.lines if id(l) in auto_ids)
    n_mine = len(au.lines) - n_auto
    ran = bool(bundle is not None and getattr(bundle, "loaded", False) and bundle.gene.upper() == g.upper())
    q = quote(g)
    dq = quote(disease_terms(au.disease)[0]) if disease_terms(au.disease) else ""
    L = [f"# Protellect evidence audit: {g} and {d}", "",
         "**Status: early tool, not validated.** This report rates how well supported a gene-disease link is. It is **not** a probability that a drug will work.", "",
         f"- Lines retrieved automatically by the app: **{n_auto}**. Lines entered by a person: **{n_mine}**. Each line below is marked with its origin in the app's table.",
         "- Rules are in the tool and can be argued with: Strong needs 3 or more separate studies, 2 or more kinds of evidence, a causal kind and nothing against; Mixed and Weak are defined in `audit.py`.", "",
         ] + _verdict_md(au, question) + [
         audit_markdown(au).replace("### ", "## ", 1), "",
         ] + _lit_section(au, lit) + [
         "## Genetic cross-checks: what the app ran and what it did not", "",
         "Human genetic support is the strongest evidence that changing a target will change a disease. Across drug programmes, mechanisms with genetic support were estimated to be 2.6 times more likely to succeed "
         "(Minikel et al., Nature 2024). That is a base rate across many targets, not a number for this one.", "",
         "| Cross-check | Status in this report | Where to check it |", "|---|---|---|",
         f"| ClinVar pathogenic germline variants and their listed conditions | {'ran (see table)' if ran else 'not run: no protein was loaded'} | [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/?term={q}[gene]) |",
         f"| gnomAD loss-of-function constraint | {'ran (context only)' if ran else 'not run'} | [gnomAD](https://gnomad.broadinstitute.org/gene/{q}?dataset=gnomad_r4) |",
         f"| Mouse knockout phenotypes (Open Targets / IMPC) | {'ran (label match only)' if ran else 'not run'} | [Open Targets](https://platform.opentargets.org/target?search={q}) |",
         f"| GWAS associations for the disease or related traits | {'partly: via the Open Targets genetic association score' if lit and lit.get('ot') else '**not run**'} | [GWAS Catalog gene page](https://www.ebi.ac.uk/gwas/genes/{q}) |",
         f"| Rare-variant and PheWAS results in large cohorts | **not run** | [Open Targets](https://platform.opentargets.org/target?search={q}) (genetic associations tab) |",
         f"| eQTLs and expression in the relevant tissue (for pain: dorsal root ganglion, spinal cord) | **not run** | [GTEx](https://gtexportal.org/home/gene/{q}) |",
         f"| Human-specific genes or copy-number variation that change the target's function | **not run** | [PubMed search](https://pubmed.ncbi.nlm.nih.gov/?term={q}+AND+copy+number+OR+human-specific) |",
         f"| Published human studies of the disease and the target | {'partly: Europe PMC records classified by keyword' if lit and lit.get('records') else '**not run**'} | [PubMed search](https://pubmed.ncbi.nlm.nih.gov/?term={q}{('+AND+' + dq) if dq else ''}) |", "",
         "## Checkpoints for a person to complete before relying on this", "",
         "1. Open each source link in the table above and confirm the line says what the report says it does.",
         "2. Run the **not run** rows above and add any finding as an evidence line (with its source and whether it supports or argues against).",
         "3. For every literature line, check whether the studies come from separate groups. The tool counts studies by the ID entered and cannot tell.",
         "4. Check the lines for selection bias: a person chose which findings to enter. Have a second person search independently and compare, and make sure findings that argue against the link were searched for as hard as those that support it.",
         "5. Check whether the animal or cell results used both sexes, more than one model, and a compound or perturbation from more than one class.",
         "6. Record anything you change, and re-run the audit. A changed tier should be traceable to a changed line.", "",
         "## Disclaimers", "",
         "- The tool does not search the literature; a person supplied the pharmacology and literature lines.",
         "- Keyword matching decides whether a retrieved database line mentions the disease. It does not judge the direction or size of an effect.",
         "- The strength labels (weak, moderate, strong) and tags are judgements made by whoever entered the line, and they can move the tier.",
         "- The tier describes the evidence entered, not the biology, and it is not a probability of clinical success.",
         "- The rules have been tested for software correctness only. They have not been tested against real project outcomes.",
         "- This is not clinical, regulatory or investment advice."]
    return "\n".join(L)


def _lit_section(au, lit):
    if not lit:
        return ["## Cell and animal evidence compared with human evidence", "", "Not run. Use the search button in the app to retrieve literature and Open Targets scores.", ""]
    from .literature import LEVELS, best_ot_row, comparison, gap_statement
    comp = comparison(lit["records"])
    row = best_ot_row(lit["ot"], au.disease)
    L = ["## Cell and animal evidence compared with human evidence", "",
         f"Query: `{lit.get('query', '')}`. {len(lit['records'])} Europe PMC record(s) retrieved (top by relevance, with abstracts). Records are placed in levels by keywords in the title and abstract; "
         "one record can sit in several levels; direction was not judged; a mention is not a finding.", ""]
    for e in lit.get("errors", []):
        L.append(f"**Missing:** {e}")
    L += ["", "| Level | Records | Newest records |", "|---|---|---|"]
    for k, label in LEVELS:
        L.append(f"| {label} | {comp[k]['n']} | " + "; ".join(f"[{p.get('year', '')} {p['title'][:60]}]({p['url']})" for p in comp[k]["papers"]) + " |")
    if lit["ot"]:
        L += ["", "Open Targets association scores (0 to 1; aggregate several sources, not separate studies):", "", "| Disease | Overall | Genetic association | Animal model | Literature | Known drug |", "|---|---|---|---|---|---|"]
        for r in lit["ot"][:6]:
            dt = r["datatypes"]
            L.append(f"| {r['disease']} | {r['score']:.2f} | {dt.get('genetic_association', 0):.2f} | {dt.get('animal_model', 0):.2f} | {dt.get('literature', 0):.2f} | {dt.get('known_drug', 0):.2f} |")
    L += ["", f"**Reading this:** {gap_statement(comp, row, len(lit['records']))}", ""]
    return L


def _verdict_md(au, question):
    from .audit import verdict
    v = verdict(au, question)
    return ["## Your question and the verdict", "", f"**Question:** {v['question']}", "", f"**Verdict:** {v['headline']} {v['body']}", "",
            f"**Cheapest next step:** {v['next_step']}", "", f"_{v['caveat']}_", ""]
