"""Turn an engine RunSummary into tables and a downloadable report."""
from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd

SHORT_TEST = {
    "fatty acid": "Fatty-acid panel screen (Ca2+ / cAMP)",
    "lipid mediator": "Lipid-mediator screen (cAMP / beta-arrestin)",
    "organic acid": "Organic-acid metabolite screen",
    "peptide": "Reverse pharmacology with tissue extracts",
}


def _top(r, category):
    return next((h for h in r.hypotheses if h.category == category), None)


def results_table(summary) -> pd.DataFrame:
    """One row per orphan receptor: the at-a-glance answer."""
    rows = []
    for r in summary.results:
        lig, sig = _top(r, "ligand-class"), _top(r, "signaling")
        base = {"Receptor": r.gene, "Your signal": f"{r.effect_type} {r.effect:.2f}"}
        if lig is None:
            rows.append({**base, "Top ligand-class hypothesis": "No hypothesis (insufficient evidence)", "Relative support": None,
                         "Critic": "-", "Likely coupling": "-", "First experiment": "Add annotation or tissue context"})
        else:
            rows.append({**base, "Top ligand-class hypothesis": lig.value, "Relative support": lig.support, "Critic": lig.verdict,
                         "Likely coupling": sig.value if sig else "-", "First experiment": SHORT_TEST.get(lig.value, "see card")})
    return pd.DataFrame(rows)


def hypotheses_table(summary) -> pd.DataFrame:
    """Flat table of every hypothesis, for spreadsheets."""
    rows = []
    for r in summary.results:
        for h in r.hypotheses:
            rows.append({
                "receptor": r.gene, "category": h.category, "hypothesis": h.statement, "value": h.value,
                "relative_support": h.support, "adjusted_support": h.adjusted_support, "critic_verdict": h.verdict,
                "n_counterarguments": len(h.counterarguments),
                "counterarguments": " | ".join(f"[{c['severity']}] {c['text']}" for c in h.counterarguments),
                "why": " | ".join(h.rationale),
                "precedents": ", ".join(p["case"] for p in h.precedents),
                "test_experiment": h.test_experiment,
                "evidence_type": h.evidence_axes.get("evidence_type", ""),
                "signal_character": h.evidence_axes.get("signal_character", ""),
                "diagnostic_potential": h.flags.get("diagnostic_potential", ""),
                "druggability": h.flags.get("druggability", ""),
            })
    return pd.DataFrame(rows)


def markdown_report(summary, context: Optional[dict] = None, calibration_note: str = "", library_verified: bool = False) -> str:
    context = context or {}
    L = ["# Protellect hypothesis report", "",
         f"Generated: {datetime.date.today().isoformat()}", "",
         f"- Disease: {context.get('disease') or 'not given'}",
         f"- Tissue: {context.get('tissue') or 'not given'}",
         f"- Comparison: {context.get('comparison') or 'not given'}",
         f"- Genes read: {summary.n_input_genes}; GPCRs found: {summary.n_gpcr}; orphan GPCRs: {summary.n_orphan}", ""]
    if summary.characterized:
        L += ["Already-characterized GPCRs in your data (no hypotheses needed): " + ", ".join(summary.characterized), ""]
    L += ["> **These are hypotheses, not findings. Only a wet-lab experiment can confirm what a receptor does.**"]
    if not library_verified:
        L += ["> **The historical case library has not been expert-verified. Treat all rankings as illustrative.**"]
    if calibration_note:
        L += [f"> {calibration_note}"]
    L += ["", "## Results at a glance", ""]
    t = results_table(summary)
    if t.empty:
        L += ["No orphan GPCRs from the current registry were found in this data.", ""]
    else:
        L += ["| " + " | ".join(t.columns) + " |", "|" + "---|" * len(t.columns)]
        for _, row in t.iterrows():
            L.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
        L.append("")
    for r in summary.results:
        L += [f"## {r.gene}", ""]
        if r.status != "hypotheses":
            L += [r.message, ""]
            continue
        for h in r.hypotheses:
            L += [f"### {h.category.replace('-', ' ').title()}: {h.statement}",
                  f"- Relative support: {h.support} (a ranking, not a probability)",
                  f"- Critic verdict: {h.verdict}",
                  f"- Why: {' | '.join(h.rationale)}",
                  f"- Test it: {h.test_experiment}"]
            for c in h.counterarguments:
                L.append(f"- Counter-argument [{c['severity']}]: {c['text']}")
            L.append("")
    L += ["## How to read this", "",
          "- Relative support splits 1.0 across one receptor's candidates. It is not the chance the hypothesis is right.",
          "- Critic verdicts: holds up (few or no counter-arguments), weakened (one major or several minor), contested (a refuted pairing or two major counter-arguments).",
          "- Structural (binding-pocket) similarity is not part of this version.", ""]
    return "\n".join(L)
