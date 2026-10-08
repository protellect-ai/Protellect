"""Experiment-driven routing: what to prioritise, deprioritise or fill in, and which tab to go to."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .adapters import Bundle


@dataclass
class Priority:
    level: str            # PRIORITIZE | INVESTIGATE | DEPRIORITIZE | DATA GAP | INFO
    headline: str
    reasons: List[str] = field(default_factory=list)
    goto: str = ""
    action: str = ""


def priorities(b: Bundle, poss: Optional[dict], defects: list, hyp_summary=None, csv_top: Optional[list] = None, n_orphans_in_registry: int = 0, gpcrome=None, workbench=None) -> List[Priority]:
    out: List[Priority] = []
    if hyp_summary is not None and getattr(hyp_summary, "n_orphan", 0) > 0:
        genes = [r.gene for r in hyp_summary.results][:4]
        first = next((r for r in hyp_summary.results if r.hypotheses), None)
        why = [f"{hyp_summary.n_input_genes} genes read, {hyp_summary.n_gpcr} GPCRs, {hyp_summary.n_orphan} orphan."]
        if first:
            why.append(f"Top hypothesis for {first.gene}: {first.hypotheses[0].statement} (ML validation: {first.hypotheses[0].verdict}).")
        out.append(Priority("PRIORITIZE", f"{hyp_summary.n_orphan} orphan GPCR(s) in your experiment: {', '.join(genes)}", why, "Overview", "Review the ranked hypotheses and run the suggested confirmatory assay."))
    elif hyp_summary is not None and csv_top is not None:
        out.append(Priority("INFO", "No orphan GPCRs recognised in your data", [f"The registry lists {n_orphans_in_registry} orphan GPCRs. Load the full list in the Overview tab if this is too few."], "Overview",
                            "Search the strongest signals below one by one."))
    if gpcrome is not None and len(gpcrome.orphans):
        n_call = int((gpcrome.orphans["Predicted coupling"] != "no supported call").sum())
        v = gpcrome.validation
        trusted = bool(v.get("ok") and v.get("beats_baseline"))
        out.insert(0, Priority("PRIORITIZE" if (n_call and trusted) else "INVESTIGATE", f"GPCRome: {n_call} of {len(gpcrome.orphans)} orphan GPCRs have a supported signalling call",
                               [v.get("note", ""), "The method beat the baseline on your characterised GPCRs." if trusted else "The method did not clearly beat the baseline on your data: read the calls with caution."],
                               "Overview", "Open the GPCRome section: test the top call with a G-protein-selective assay."))
    if workbench is not None and workbench.enrich_claims:
        c = workbench.enrich_claims[0]
        lead = c.tags.get("lead", [])
        out.insert(0, Priority("PRIORITIZE", c.text.split(" (")[0], [c.proofs[0].detail[:140], "Leading edge: " + ", ".join(lead[:6])], "Overview",
                               "Open the coupling-enrichment section: pick the leading-edge receptors and look up their recorded drugs."))
    if csv_top:
        out.append(Priority("INVESTIGATE", "Strongest signals in your data", [f"{g} ({e:+.2f})" for g, e in csv_top[:5]], "Triage", "Search each in the sidebar to pull its evidence."))
    if not b.loaded:
        if not out:
            out.append(Priority("DATA GAP", "Nothing loaded yet", ["Search a protein in the sidebar, or upload an experiment table."], "", ""))
        return out
    lvl = poss["level"] if poss else "INSUFFICIENT DATA"
    weak = [c["name"] for c in (poss or {}).get("components", []) if c["available"] and c["points"] == 0][:3]
    gaps = [a.name.strip() for a in b.audit if a.note and a.n == 0][:4]
    cov = (poss or {}).get("coverage", "")
    if lvl == "HIGH":
        out.append(Priority("PRIORITIZE", f"{b.gene}: strong evidence to pursue ({poss['pct']}/100)", [cov, f"Missing or weak: {', '.join(weak) or 'nothing notable'}"], "Overview", "Read the strategy options and the ranked hypotheses."))
    elif lvl == "MODERATE":
        out.append(Priority("INVESTIGATE", f"{b.gene}: promising but incomplete ({poss['pct']}/100)", [cov, f"Weakest evidence: {', '.join(weak) or 'none flagged'}"], "Overview", "Close the evidence gaps before committing."))
    elif lvl == "LOW":
        out.append(Priority("DEPRIORITIZE", f"{b.gene}: weak evidence on what is available ({poss['pct']}/100)", [cov, "Score reflects the data retrieved; absence from ClinVar is not proof of irrelevance."], "Genetics", "Check the genetic thresholds before dropping it."))
    else:
        out.append(Priority("DATA GAP", f"{b.gene}: too little data to judge", [cov, "Empty sources: " + (", ".join(gaps) or "several")], "Overview", "See the data audit for what came back empty."))
    if b.plp:
        out.append(Priority("INVESTIGATE", f"{len(b.plp)} pathogenic/likely-pathogenic variants to work through", [f"Best review: {max(v.stars for v in b.plp)} star(s)."], "Triage", "Pick a variant on the structure and follow its plan."))
    if any(b.tractability.values()) or b.drugs or b.trials:
        out.append(Priority("INVESTIGATE", "Existing chemistry or tractability found", [f"{len(b.drugs)} drug record(s), {len(b.trials)} trial(s)."], "Druggable hotspots", "Review pharmacokinetics, ADMET and adverse-event evidence."))
    if any(v is not None for v in b.constraint.values()):
        out.append(Priority("INFO", "Genetic thresholds available", ["pLI / LOEUF / missense Z and ClinVar quality are tabulated."], "Genetics", "Check which thresholds the gene meets."))
    return out
