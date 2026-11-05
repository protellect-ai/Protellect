"""A one-page target decision memo with an analysis record.

What a decision-maker or a reviewer needs is not a list of hits but a short answer they can defend: which orphan
receptors are worth bench time, what to run first, what could be wrong, and exactly what data and settings produced it.
The memo is built only from what the engine already produced. It adds no new claims, never says a hypothesis is validated,
and ends with an analysis record (file name, size, SHA-256 of the uploaded file, counts, registry, gene-name merges, date)
so the same analysis can be repeated and audited later.
"""
from __future__ import annotations

import datetime
from typing import Optional

from .report import SHORT_TEST, _signal, _top
from ..reported import compare_with_literature

TIERS = ("Test first", "Check objections first", "Literature only", "Not enough evidence")


def _tier(r, has_prior: bool) -> str:
    lig = _top(r, "ligand-class")
    if r.status == "hypotheses" and lig is not None:
        return "Test first" if lig.verdict == "holds up" else "Check objections first"
    return "Literature only" if has_prior else "Not enough evidence"


def _sort_key(item):
    tier, r, lig = item
    return (TIERS.index(tier), -(lig.adjusted_support or lig.support) if lig else 0.0, r.gene)


def _cell(x) -> str:
    return str(x).replace("|", "/").replace("\n", " ").strip()


def decision_memo(summary, context: Optional[dict] = None, registry: Optional[dict] = None, library_verified: bool = False,
                  record: Optional[dict] = None) -> str:
    from ..reported import prior_text
    context = context or {}
    record = record or {}
    registry = registry or {}
    rows = []
    for r in summary.results:
        pr = prior_text(r.gene, registry.get(r.gene.upper()))
        rows.append((_tier(r, bool(pr)), r, _top(r, "ligand-class"), pr))
    rows.sort(key=lambda t: _sort_key(t[:3]))
    n = {t: sum(1 for x in rows if x[0] == t) for t in TIERS}

    L = ["# Target decision memo", "",
         f"Date: {datetime.date.today().isoformat()}", "",
         "**Decision question:** which orphan receptors in this data are worth bench time, and what should be tested first?", ""]
    if context.get("disease") or context.get("tissue") or context.get("comparison"):
        L += [f"Context given: disease {context.get('disease') or 'not given'}; tissue {context.get('tissue') or 'not given'}; "
              f"comparison {context.get('comparison') or 'not given'}.", ""]

    L += ["## Bottom line", ""]
    if not rows:
        L += ["No orphan receptors from the current registry were found in this data, so there is nothing to prioritise.", ""]
    else:
        first = next((x for x in rows if x[0] == "Test first"), None)
        if first:
            _, r, lig, _ = first
            L += [f"{n['Test first']} of {len(rows)} orphan receptors have a leading hypothesis that holds up against the critic. "
                  f"Start with **{r.gene}** (your signal: {_signal(r)}): leading ligand-class hypothesis {lig.value}, "
                  f"relative support {lig.support}. This is a ranking of candidates, not the chance it is right.", ""]
        else:
            L += [f"None of the {len(rows)} orphan receptors has a leading hypothesis that holds up against the critic. "
                  "Read the objections in the table before spending bench time, and consider adding tissue or disease context.", ""]
        if n["Check objections first"]:
            L += [f"{n['Check objections first']}{' more' if first else ''} {'has' if n['Check objections first'] == 1 and not first else 'have'} a hypothesis with unresolved objections.", ""]
        if n["Literature only"] or n["Not enough evidence"]:
            L += [f"{n['Literature only']} have only a reported finding from the literature and {n['Not enough evidence']} have no supported hypothesis.", ""]

        L += ["## Priority table", "",
              "| Priority | Receptor | Your signal | Leading ligand-class hypothesis | Critic | First experiment | Main objection |",
              "|---|---|---|---|---|---|---|"]
        for tier, r, lig, pr in rows:
            if lig is not None:
                sig = _top(r, "signaling")
                cmp = compare_with_literature(r.gene, lig.value, sig.value if sig else None)
                top_obj = next((c for c in lig.counterarguments if c.get("severity") == "major"), None) or (lig.counterarguments[0] if lig.counterarguments else None)
                L.append("| " + " | ".join(_cell(x) for x in [
                    tier, r.gene, _signal(r), f"{lig.value} (support {lig.support})", lig.verdict, SHORT_TEST.get(lig.value, "see the receptor card"),
                    ("DIFFERS FROM THE LITERATURE ENTRY (" + cmp["text"] + ") " if cmp["status"] == "differs" else "") + (top_obj["text"] if top_obj else "none raised")]) + " |")
            elif pr:
                L.append("| " + " | ".join(_cell(x) for x in [tier, r.gene, _signal(r), pr["ligand"] + " (reported, not learned from your data)", "-",
                                                                   "Test the reported coupling first", "Entry typed from the literature and not yet checked against the papers"]) + " |")
            else:
                L.append("| " + " | ".join(_cell(x) for x in [tier, r.gene, _signal(r), "No hypothesis", "-", "G-protein panel and constitutive-activity check",
                                                                   "No source supports a ligand class"]) + " |")
        L.append("")

        firsts = [x for x in rows if x[0] == "Test first"]
        if firsts:
            L += ["## Test first", ""]
            for _, r, lig, _p in firsts:
                L += [f"### {r.gene}", "", f"- Hypothesis: {lig.statement}", f"- Why: {' | '.join(lig.rationale)}", f"- Run: {lig.test_experiment}"]
                if lig.precedents:
                    L.append("- Precedents: " + ", ".join(p["case"] for p in lig.precedents))
                for c in lig.counterarguments:
                    L.append(f"- Could be wrong [{c['severity']}]: {c['text']}")
                L.append("")

    L += ["## What this memo does not tell you", "",
          "- These are hypotheses, not findings. Only a wet-lab experiment can confirm what a receptor does.",
          "- Relative support splits 1.0 across one receptor's candidates. It is not a probability.",
          "- Docking scores, binding energies, binding kinetics and active-state structures are not computed, and nothing here implies they were."]
    if not library_verified:
        L += ["- The historical case library behind the rankings has not been expert-verified, so treat the ranking as illustrative."]
    L += ["- Reported-literature entries were typed from papers and have not yet been checked against them."]
    try:
        import json as _json
        from .cases import DATA_DIR
        g = _json.loads((DATA_DIR / "benchmark_gate.json").read_text(encoding="utf-8"))
        L += [f"- Testing so far: {g['sentence']}"]
    except Exception:  # no benchmark file shipped: say nothing rather than guess
        pass
    L += [""]

    L += ["## Analysis record", "",
          "So that someone else can repeat or audit this analysis.", "",
          "| Item | Value |", "|---|---|",
          f"| Date | {datetime.date.today().isoformat()} |",
          f"| Uploaded file | {_cell(record.get('file_name') or 'not recorded')} |",
          f"| File size (bytes) | {record.get('n_bytes') if record.get('n_bytes') is not None else 'not recorded'} |",
          f"| SHA-256 of the uploaded file | {record.get('sha256') or 'not recorded'} |",
          f"| Genes read / GPCRs found / orphan GPCRs | {summary.n_input_genes} / {summary.n_gpcr} / {summary.n_orphan} |",
          f"| Receptor registry | {_cell(record.get('registry_label') or 'not recorded')} |",
          f"| Historical cases in the library | {record.get('n_cases') if record.get('n_cases') is not None else 'not recorded'} |",
          f"| Case library expert-verified | {'yes' if library_verified else 'no'} |"]
    for note in getattr(summary, "alias_notes", []) or []:
        L.append(f"| Gene-name merge | {_cell(note)} |")
    L += ["", "## Sign-off", "", "Reviewed by: ____________  Date: ________  Decision:  [ ] test   [ ] hold   [ ] drop", ""]
    return "\n".join(L)
