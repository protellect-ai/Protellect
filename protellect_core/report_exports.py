"""Excel versions of every report the app used to offer as markdown: the hypothesis report, the decision memo, the methods text,
the per-receptor audit list, and plain tables. All of them are built with xlsx_kit.Book, so they share one layout:
a Contents sheet, a title and a one-line description on each sheet, filters, frozen headers, and a reason in place of an empty table.

Nothing here adds a claim. Each builder lays out what the engine or the audit already produced.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Iterable, List, Mapping, Optional

import pandas as pd

from .engine.memo import TIERS, _sort_key, _tier
from .engine.report import SHORT_TEST, _signal, _top, hypotheses_table, results_table
from .xlsx_kit import FILLS, TIER_FILL, Book

TIER_COLOUR = {"Test first": FILLS["good"], "Check objections first": FILLS["warn"], "Literature only": FILLS["info"], "Not enough evidence": FILLS["none"]}
VERDICT_COLOUR = {"holds up": FILLS["good"], "weakened": FILLS["warn"], "contested": FILLS["bad"]}
HYP_NOTE = "These are hypotheses, not findings. Only a wet-lab experiment can confirm what a receptor does."


def _widths(df: pd.DataFrame, lo: int = 12, hi: int = 70) -> List[int]:
    out = []
    for c in df.columns:
        longest = max([len(str(c))] + [len(str(x)) for x in df[c].head(200).tolist()])
        out.append(int(min(hi, max(lo, longest * 0.95))))
    return out


def table_xlsx(title: str, intro: str, df: pd.DataFrame, sheet: str = "Table", note: str = "", status: str = "") -> bytes:
    """Any dataframe as a one-sheet workbook with a Contents sheet. Used where the app used to offer a CSV of results."""
    book = Book(title, intro, status)
    df = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
    book.table(sheet, title, note or intro, [str(c) for c in df.columns], df.astype(object).where(pd.notna(df), None).values.tolist(), widths=_widths(df),
               empty="No rows. The analysis produced nothing for this table with the data and settings used.", what=title)
    return book.to_bytes()


# ── hypothesis report ───────────────────────────────────────────────────────────────────────────
def hypotheses_xlsx(summary, context: Optional[Mapping] = None, calibration_note: str = "", library_verified: bool = False, registry: Optional[Mapping] = None) -> bytes:
    from .reported import REPORTED_NOTE, prior_claims
    context = context or {}
    registry = registry or {}
    book = Book("Protellect hypothesis report", HYP_NOTE, f"Generated {_dt.date.today().isoformat()}. "
                + ("" if library_verified else "The historical case library has not been expert-verified, so treat every ranking as illustrative."))
    read = [
        ("Disease", context.get("disease") or "not given", ""),
        ("Tissue", context.get("tissue") or "not given", ""),
        ("Comparison", context.get("comparison") or "not given", ""),
        ("Genes read", summary.n_input_genes, "In the file you uploaded"),
        ("GPCRs found", summary.n_gpcr, "Against the receptor registry in use"),
        ("Orphan GPCRs", summary.n_orphan, "Hypotheses are made only for these"),
        ("Already-characterised GPCRs in your data", ", ".join(summary.characterized) or "none", "No hypotheses needed"),
        ("Calibration note", calibration_note or "none", ""),
    ] + [("Gene-name reconciliation", n, "") for n in (getattr(summary, "alias_notes", []) or [])] + [
        ("Relative support", "Splits 1.0 across one receptor's candidates.", "A ranking, not the chance the hypothesis is right."),
        ("Critic verdicts", "holds up: few or no counter-arguments. weakened: one major or several minor. contested: a refuted pairing or two major counter-arguments.", ""),
        ("Not computed", "Structural binding-pocket similarity, docking scores, binding energies and kinetics are not part of this version.", ""),
    ]
    book.kv("Read me", "Hypothesis report: how to read it", HYP_NOTE, read, widths=(38, 80, 60), what="Context, counts, and how to read the rankings.")
    t = results_table(summary, registry)
    if len(t):
        cols = [str(c) for c in t.columns]
        book.table("Results at a glance", "Results at a glance: one row per orphan receptor",
                   "The top ligand-class hypothesis, the critic's verdict and the first experiment for each orphan. '(reported)' or '(family-level)' entries come from the literature or the family pattern, not from your data.",
                   cols, t.astype(object).where(pd.notna(t), None).values.tolist(), widths=_widths(t, 12, 60),
                   fill_col=cols.index("Critic") if "Critic" in cols else None, fill_map=VERDICT_COLOUR,
                   what="The at-a-glance answer for each orphan receptor.")
    else:
        book.table("Results at a glance", "Results at a glance", "", ["Receptor"], [], empty="No orphan GPCRs from the current registry were found in this data.", what="The at-a-glance answer for each orphan receptor.")
    h = hypotheses_table(summary)
    hcols = {"receptor": "Receptor", "category": "Question", "hypothesis": "Hypothesis", "value": "Value", "relative_support": "Relative support", "adjusted_support": "Support after critic",
             "critic_verdict": "Critic verdict", "n_counterarguments": "Counter-arguments", "counterarguments": "Counter-argument text", "why": "Why", "precedents": "Precedent cases",
             "test_experiment": "Experiment to test it", "evidence_type": "Evidence type", "signal_character": "Signal character", "diagnostic_potential": "Diagnostic potential", "druggability": "Druggability"}
    hh = h.rename(columns=hcols) if len(h) else pd.DataFrame(columns=list(hcols.values()))
    book.table("All hypotheses", "Every hypothesis the engine produced", "Relative support is a ranking within one receptor, not a probability.",
               list(hh.columns), hh.astype(object).where(pd.notna(hh), None).values.tolist(), widths=[14, 14, 50, 16, 11, 11, 13, 12, 60, 60, 30, 50, 18, 18, 18, 18][: len(hh.columns)],
               fill_col=list(hh.columns).index("Critic verdict") if "Critic verdict" in hh.columns else None, fill_map=VERDICT_COLOUR,
               empty="No hypotheses were produced. Check the 'No hypothesis' sheet for the reason for each receptor.", what="One row per hypothesis with its support, critic verdict and test.")
    ca = []
    for r in summary.results:
        for hy in r.hypotheses:
            for c in hy.counterarguments:
                ca.append([r.gene, hy.category, hy.value, c.get("severity", ""), c.get("text", "")])
    book.table("Counter-arguments", "What the critic raised against each hypothesis", "Read these before spending bench time. 'major' ones can change which hypothesis leads.",
               ["Receptor", "Question", "Hypothesis value", "Severity", "Counter-argument"], ca, widths=[14, 16, 24, 11, 110], fill_col=3, fill_map={"major": FILLS["bad"], "minor": FILLS["warn"]},
               empty="The critic raised no counter-argument against any hypothesis. That is unusual: check that the case library and your data were loaded.", what="Every objection the critic raised.")
    rep = []
    for r in summary.results:
        for c in prior_claims(r.gene, registry.get(r.gene.upper())):
            rep.append([r.gene, c.text, "; ".join(p.detail for p in c.proofs if p.kind == "literature"), " ".join(c.how or [])])
    book.table("Reported in literature", "Findings from the literature (not learned from your data)", REPORTED_NOTE,
               ["Receptor", "Reported finding", "Papers", "How to test it"], rep, widths=[14, 70, 70, 70],
               empty="No orphan in this analysis has a typed literature entry.", what="Literature entries that sit beside the engine's hypotheses.")
    nohyp = [[r.gene, r.status, r.message or ""] for r in summary.results if r.status != "hypotheses"]
    book.table("No hypothesis", "Receptors for which no hypothesis was made, and why", "An honest 'not enough evidence' is a result.",
               ["Receptor", "Status", "Reason"], nohyp, widths=[14, 20, 120], empty="Every orphan receptor received at least one hypothesis.", what="Orphans the engine abstained on, with the reason.")
    book.limit(HYP_NOTE)
    book.limit("Relative support is not a probability. Critic verdicts are rule-based counter-arguments, not a literature review.")
    if not library_verified:
        book.limit("The historical case library behind the rankings has not been expert-verified.")
    return book.to_bytes()


# ── decision memo ──────────────────────────────────────────────────────────────────────────────
def decision_memo_xlsx(summary, context: Optional[Mapping] = None, registry: Optional[Mapping] = None, library_verified: bool = False, record: Optional[Mapping] = None) -> bytes:
    from .reported import compare_with_literature, prior_text
    context, record, registry = context or {}, record or {}, registry or {}
    rows = []
    for r in summary.results:
        pr = prior_text(r.gene, registry.get(r.gene.upper()))
        rows.append((_tier(r, bool(pr)), r, _top(r, "ligand-class"), pr))
    rows.sort(key=lambda t: _sort_key(t[:3]))
    n = {t: sum(1 for x in rows if x[0] == t) for t in TIERS}
    book = Book("Target decision memo", "Which orphan receptors are worth bench time, and what to test first. Hypotheses, not findings.", f"Date {_dt.date.today().isoformat()}")

    bl = []
    if not rows:
        bl.append(("Bottom line", "No orphan receptors from the current registry were found in this data, so there is nothing to prioritise."))
    else:
        first = next((x for x in rows if x[0] == "Test first"), None)
        if first:
            _, r, lig, _p = first
            bl.append(("Bottom line", f"{n['Test first']} of {len(rows)} orphan receptors have a leading hypothesis that holds up against the critic. Start with {r.gene} (your signal: {_signal(r)}): "
                                      f"leading ligand-class hypothesis {lig.value}, relative support {lig.support}. This is a ranking of candidates, not the chance it is right."))
        else:
            bl.append(("Bottom line", f"None of the {len(rows)} orphan receptors has a leading hypothesis that holds up against the critic. Read the objections before spending bench time, and consider adding tissue or disease context."))
        bl.append(("Counts", f"Test first: {n['Test first']}. Check objections first: {n['Check objections first']}. Literature only: {n['Literature only']}. Not enough evidence: {n['Not enough evidence']}."))
    bl.insert(0, ("Decision question", "Which orphan receptors in this data are worth bench time, and what should be tested first?"))
    bl.append(("Context given", f"Disease: {context.get('disease') or 'not given'}. Tissue: {context.get('tissue') or 'not given'}. Comparison: {context.get('comparison') or 'not given'}."))
    book.text("Bottom line", "Bottom line", "", bl, what="The answer in a few sentences.")

    prio = []
    for tier, r, lig, pr in rows:
        if lig is not None:
            sig = _top(r, "signaling")
            cmp = compare_with_literature(r.gene, lig.value, sig.value if sig else None)
            obj = next((c for c in lig.counterarguments if c.get("severity") == "major"), None) or (lig.counterarguments[0] if lig.counterarguments else None)
            prio.append([tier, r.gene, _signal(r), f"{lig.value} (support {lig.support})", lig.verdict, SHORT_TEST.get(lig.value, "see the receptor card"),
                         ("DIFFERS FROM THE LITERATURE ENTRY (" + cmp["text"] + ") " if cmp["status"] == "differs" else "") + (obj["text"] if obj else "none raised")])
        elif pr:
            prio.append([tier, r.gene, _signal(r), pr["ligand"] + " (reported, not learned from your data)", "-", "Test the reported coupling first", "Entry typed from the literature and not yet checked against the papers"])
        else:
            prio.append([tier, r.gene, _signal(r), "No hypothesis", "-", "G-protein panel and constitutive-activity check", "No source supports a ligand class"])
    book.table("Priority table", "Priority table", "Sorted by priority tier, then by relative support. The main objection is the critic's most serious counter-argument.",
               ["Priority", "Receptor", "Your signal", "Leading ligand-class hypothesis", "Critic", "First experiment", "Main objection"], prio,
               widths=[22, 12, 22, 40, 12, 40, 80], fill_col=0, fill_map=TIER_COLOUR, empty="No orphan receptors to prioritise.", what="Every orphan ranked, with first experiment and main objection.")

    det = []
    for _, r, lig, _p in [x for x in rows if x[0] == "Test first"]:
        det.append([r.gene, lig.statement, " | ".join(lig.rationale), lig.test_experiment, ", ".join(p["case"] for p in lig.precedents),
                    "\n".join(f"[{c['severity']}] {c['text']}" for c in lig.counterarguments)])
    book.table("Test first", "Receptors to test first, in detail", "Only receptors whose leading hypothesis holds up against the critic appear here.",
               ["Receptor", "Hypothesis", "Why", "Experiment to run", "Precedent cases", "Could be wrong because"], det, widths=[12, 50, 60, 60, 36, 70],
               empty="No receptor has a leading hypothesis that holds up against the critic.", what="Hypothesis, rationale, experiment and objections for the top receptors.")

    lim = [("Hypotheses, not findings", "Only a wet-lab experiment can confirm what a receptor does."),
           ("Relative support", "Splits 1.0 across one receptor's candidates. It is not a probability."),
           ("Not computed", "Docking scores, binding energies, binding kinetics and active-state structures are not computed, and nothing here implies they were.")]
    if not library_verified:
        lim.append(("Case library", "The historical case library behind the rankings has not been expert-verified, so treat the ranking as illustrative."))
    lim.append(("Literature entries", "Reported-literature entries were typed from papers and have not yet been checked against them."))
    try:
        import json as _json
        from .engine.cases import DATA_DIR
        g = _json.loads((DATA_DIR / "benchmark_gate.json").read_text(encoding="utf-8"))
        lim.append(("Testing so far", g["sentence"]))
    except Exception:  # noqa: BLE001
        pass
    book.text("Limits", "What this memo does not tell you", "", lim, what="What the memo cannot say.")

    rec = [("Date", _dt.date.today().isoformat(), ""),
           ("Uploaded file", record.get("file_name") or "not recorded", ""),
           ("File size (bytes)", record.get("n_bytes") if record.get("n_bytes") is not None else "not recorded", ""),
           ("SHA-256 of the uploaded file", record.get("sha256") or "not recorded", "Lets someone confirm they analysed the same file"),
           ("Genes read / GPCRs found / orphan GPCRs", f"{summary.n_input_genes} / {summary.n_gpcr} / {summary.n_orphan}", ""),
           ("Receptor registry", record.get("registry_label") or "not recorded", ""),
           ("Historical cases in the library", record.get("n_cases") if record.get("n_cases") is not None else "not recorded", ""),
           ("Case library expert-verified", "yes" if library_verified else "no", "")] + [("Gene-name merge", nn, "") for nn in (getattr(summary, "alias_notes", []) or [])]
    book.kv("Analysis record", "Analysis record", "So that someone else can repeat or audit this analysis.", rec, widths=(40, 70, 60), what="File, counts, registry and settings behind this memo.")
    book.table("Sign-off", "Sign-off", "Fill in by hand.", ["Reviewed by", "Date", "Decision (test / hold / drop)", "Notes"], [["", "", "", ""]], widths=[30, 16, 30, 70], what="A line for the reviewer's decision.")
    book.limit(HYP_NOTE)
    return book.to_bytes()


# ── methods ────────────────────────────────────────────────────────────────────────────────────
def methods_xlsx(methods_md: str, record: Optional[Mapping] = None) -> bytes:
    """The methods paragraph, split into one row per analysis so each can be copied into a paper's methods section."""
    book = Book("Methods for the analyses you ran", "Parameters are filled in from this run. Copy a row into a methods section; cite the papers named in it.", f"Generated {_dt.date.today().isoformat()}")
    blocks = []
    for para in [p.strip() for p in methods_md.split("\n\n") if p.strip()]:
        m = re.match(r"\*\*(.+?)\*\*\s*(.*)", para, re.S)
        blocks.append((m.group(1).strip(" .") if m else "Note", (m.group(2) if m else para).replace("**", "").strip()))
    book.text("Methods", "Methods paragraphs", "One row per analysis. Wording is generated from the parameters actually used.", blocks, widths=(34, 150), what="Methods text, one row per analysis.")
    if record:
        book.kv("Run record", "Run record", "", [(k, v, "") for k, v in record.items()], widths=(34, 80, 40), what="Software version, date and data shape.")
    book.limit("Predictions here are reasons to run an assay, not results. State that in any methods section that uses them.")
    return book.to_bytes()


# ── audit list ─────────────────────────────────────────────────────────────────────────────────
def audit_list_xlsx(audits: Iterable, disease: str = "") -> bytes:
    audits = list(audits)
    book = Book("Evidence audit: all receptors", "How well supported is each receptor's link to the disease? A tier describes the evidence entered, not a probability.",
                f"Disease or condition: {disease or 'not given'}")
    book.table("Audit overview", "One row per receptor", "With only your own experiment as evidence, every receptor is Weak by design: one source.",
               ["Receptor", "Disease", "Tier", "Why", "Evidence lines", "Red flags", "Cheapest experiment to separate real from false"],
               [[a.gene, a.disease or "", a.tier, " ".join(a.reasons), len(a.lines), len(a.flags), a.cheapest_test] for a in audits],
               widths=[14, 28, 14, 70, 12, 10, 80], fill_col=2, fill_map=TIER_FILL, empty="No receptors were audited.", what="Tier and cheapest next experiment for each receptor.")
    book.table("Red flags", "Red flags by receptor", "A flag is a reason for caution found by a written rule, not proof of a problem.", ["Receptor", "Flag", "Why it matters", "Cheapest check"],
               [[a.gene, f["flag"].replace("_", " "), f["why"], f["test"]] for a in audits for f in a.flags], widths=[14, 26, 80, 80], empty="No red flag rule fired.", what="Every red flag with its cheapest check.")
    book.table("Evidence lines", "Evidence lines by receptor", "Each line has a named source.", ["Receptor", "Kind", "Direction", "Strength", "What it shows", "Source", "Link"],
               [[a.gene, l.kind, l.direction, l.strength, l.summary, l.source, l.url] for a in audits for l in a.lines], widths=[14, 13, 12, 11, 80, 50, 46], link_cols=[6],
               fill_col=2, fill_map={"supports": FILLS["good"], "against": FILLS["bad"], "neutral": FILLS["none"]}, empty="No evidence lines were entered.", what="Every evidence line.")
    book.table("To raise confidence", "What would raise confidence", "", ["Receptor", "What would raise confidence"], [[a.gene, t] for a in audits for t in a.to_raise], widths=[14, 130],
               empty="Nothing further is suggested.", what="Suggested next evidence for each receptor.")
    book.limit("Tiers are written rules applied to the lines entered. They have been tested for software correctness only, not against drug-development outcomes.")
    return book.to_bytes()
