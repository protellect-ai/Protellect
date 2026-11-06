"""The Excel version of the evidence audit: verdict, every evidence line, red flags, the model-level comparison,
what was and was not cross-checked, checkpoints and disclaimers.

`add_audit_sheets` writes these into any Book, so the protein report can carry the audit inside the same workbook.
`audit_xlsx` makes a stand-alone audit workbook (used when a gene is audited without a protein search).
"""
from __future__ import annotations

from typing import List

from .audit import verdict
from .audit_auto import CHECKPOINTS, DISCLAIMERS, cross_check_rows
from .literature import LEVELS, OT_MODERATE, OT_WEAK, best_ot_row, classify, comparison, gap_statement
from .xlsx_kit import FILLS, TIER_FILL, Book

TIER_RULES = ("Strong: 3 or more separate studies, 2 or more kinds of evidence, a causal kind (genetics or perturbation) and nothing against. "
              "Mixed: 2 or more separate studies with 2 or more kinds or a causal kind, or a strong line arguing against. "
              "Weak: one study, or expression or literature mentions alone. Contradicted: a strong line against and at most one supporting study. "
              "Unchecked: no lines. Studies are counted by study ID; the tool cannot tell whether two are from the same group.")
GROUP = "Evidence audit: how well supported is the target-disease link"


def add_audit_sheets(book: Book, au, auto_lines: List, bundle=None, lit=None, question: str = "") -> None:
    v = verdict(au, question)
    auto_ids = {id(l) for l in auto_lines}
    n_auto = sum(1 for l in au.lines if id(l) in auto_ids)
    n_sup = sum(1 for l in au.lines if l.direction == "supports")
    n_ag = sum(1 for l in au.lines if l.direction == "against")
    studies = len({(l.study_id or l.source) for l in au.lines})
    rows = [
        ("Question", v["question"], "Typed in the Research Goal box, or the default if none was typed."),
        ("Gene", au.gene, ""),
        ("Disease or condition", au.disease or "(none entered)", ""),
        ("Evidence tier", au.tier, "A statement about the evidence entered, not a probability that a drug will work."),
        ("Verdict", f"{v['headline']} {v['body']}", "Built from the tier, the counts and the flags by a fixed template. It does not read the question."),
        ("Cheapest next step", v["next_step"], ""),
        ("Evidence lines", len(au.lines), f"{n_auto} retrieved by the app, {len(au.lines) - n_auto} entered by a person"),
        ("  supporting / against", f"{n_sup} / {n_ag}", "The remainder are neutral."),
        ("  separate studies", studies, "Counted by study ID."),
        ("Red flags raised", len(au.flags), "See the Audit red flags sheet."),
        ("Caveat", v["caveat"], ""),
        ("Tier rules", TIER_RULES, "These rules are design choices. They have been tested for software correctness only, not against drug-development outcomes."),
    ]
    book.kv("Audit summary", f"Evidence audit: {au.gene}" + (f" and {au.disease}" if au.disease else ""),
            "How well supported the link is, and what to check next. Early tool, not validated: it rates the evidence you and the app supplied; it does not look for evidence it was not given.",
            rows, widths=(26, 100, 62), fills={3: au.tier if au.tier in TIER_FILL else "none"}, group=GROUP, what="Question, tier, verdict, next step and the tier rules.")

    book.table("Audit evidence", "Every evidence line behind the tier",
               "Origin says whether the app retrieved the line from a database or a person entered it. A retrieved line counts as support only if its retrieved text mentions the disease. Strength and tags on entered lines are human judgment.",
               ["Origin", "Kind", "Direction", "Strength", "What it shows", "Source", "Link", "Study ID", "Tags"],
               [["retrieved by the app" if id(l) in auto_ids else "you entered", l.kind, l.direction, l.strength, l.summary, l.source, l.url, l.study_id or l.source, "; ".join(l.tags)] for l in au.lines],
               widths=[18, 13, 12, 11, 80, 48, 42, 26, 26], link_cols=[6], fill_col=2,
               fill_map={"supports": FILLS["good"], "against": FILLS["bad"], "neutral": FILLS["none"]},
               empty="No evidence lines were entered or retrieved, so the tier is Unchecked.", group=GROUP, what="One row per line of evidence, with its source and link.")

    book.table("Audit red flags", "Red flags and the cheapest check for each",
               "A flag is a reason for caution found by a written rule. It is not proof that the link is wrong.",
               ["Flag", "Why it matters", "Cheapest check"],
               [[f["flag"].replace("_", " "), f["why"], f["test"]] for f in au.flags], widths=[26, 80, 80],
               empty="No red flag rule fired for the lines entered. That does not mean none apply: the rules only see what was entered.", group=GROUP, what="Reasons for caution and the cheapest way to resolve each.")

    if not lit:
        book.table("Lit vs genetics", "Cell and animal evidence against human evidence",
                   "Compares what the literature says in cells and animals with what human genetics and clinical studies say.",
                   ["Level", "Records", "Newest records"], [], widths=[44, 12, 120],
                   empty="Not run. In the app, open Overview > Check any target, enter a disease and press the search button (it queries Europe PMC and Open Targets), then download again.",
                   group=GROUP, what="How many papers sit at each level (human clinical, human genetic, animal, cell).")
    else:
        comp = comparison(lit["records"])
        row = best_ot_row(lit["ot"], au.disease)
        book.table("Lit vs genetics", "Cell and animal evidence against human evidence",
                   f"Europe PMC query: {lit.get('query', '')}. {len(lit['records'])} record(s) retrieved (top results by relevance only: absence among them is not absence in the literature). "
                   "Levels come from keywords in the title, abstract and publication type; one record can sit in several levels; direction was not judged; a mention is not a finding.",
                   ["Level", "Records", "Newest records (year, title, link)"],
                   [[label, comp[k]["n"], "\n".join(f"{p.get('year', '')}  {p['title'][:110]}  {p['url']}" for p in comp[k]["papers"])] for k, label in LEVELS] + [["Not classified", comp["unclassified"]["n"], ""]],
                   widths=[44, 12, 130], group=GROUP, what="Papers at each level of evidence, from the live Europe PMC search.")
        book.table("Open Targets", "Open Targets: strength of the gene-disease link by type of evidence",
                   f"Scores run from 0 to 1 and aggregate several sources, so they are not separate studies. A genetic-association score from {OT_WEAK} counts as weak support and from {OT_MODERATE} as moderate in the tier: design choices, not fitted.",
                   ["Disease", "Overall", "Genetic association", "Animal model", "Literature", "Known drug"],
                   [[r["disease"], round(r["score"], 3), round(r["datatypes"].get("genetic_association", 0), 3), round(r["datatypes"].get("animal_model", 0), 3),
                     round(r["datatypes"].get("literature", 0), 3), round(r["datatypes"].get("known_drug", 0), 3)] for r in lit["ot"][:12]],
                   widths=[50, 12, 18, 14, 14, 14], number_formats={1: "0.000", 2: "0.000", 3: "0.000", 4: "0.000", 5: "0.000"},
                   empty="Open Targets returned no matching disease for this gene and term, or the call failed (" + "; ".join(lit.get("errors", [])) + ").",
                   group=GROUP, what="Open Targets scores split by genetic, animal-model, literature and known-drug evidence.")
        book.kv("Reading the comparison", "What the comparison does and does not say", "", [
            ("Reading", gap_statement(comp, row, len(lit["records"])), ""),
            ("How levels were assigned", "By keywords in the title, abstract and publication type.", "Not a judgment of study quality or of whether a paper supports or argues against the link."),
            ("Errors", "; ".join(lit.get("errors", [])) or "none", "A missing source means that part of the comparison is absent."),
        ], widths=(30, 110, 60), group=GROUP, what="Plain-language reading of the gap between model and human evidence.")
        if lit.get("records"):
            book.table("Retrieved papers", "Every record the literature search returned",
                       "Use this to check the keyword levels yourself. Levels are guesses from keywords.",
                       ["Year", "Title", "Journal", "Levels (by keyword)", "Link"],
                       [[r.get("year", ""), r["title"], r.get("journal", ""), ", ".join(dict(LEVELS).get(k, k) for k in classify(r)) or "not classified", r["url"]] for r in lit["records"]],
                       widths=[8, 90, 34, 40, 46], link_cols=[4], group=GROUP, what="All papers returned by the search with their keyword levels.")

    book.table("Cross-checks", "What was cross-checked, and what you still need to check",
               "'Not run' means this report did not consult that source. Each row says where to check it.",
               ["Cross-check", "Status in this report", "Where to check it", "Link"],
               [[c, s, lab, url] for c, s, lab, url in cross_check_rows(au, bundle, lit)], widths=[66, 50, 32, 56], link_cols=[3],
               group=GROUP, what="Sources consulted and sources not consulted, with links.")
    book.table("Checkpoints", "Checkpoints for the reader", "Fill in Done and Notes as you check each item.",
               ["#", "Checkpoint", "Done (yes/no)", "Notes"], [[i, c, "", ""] for i, c in enumerate(CHECKPOINTS, 1)], widths=[5, 110, 14, 50],
               group=GROUP, what="Things a reviewer should confirm before relying on this report.")
    book.table("Disclaimers", "Disclaimers", "", ["#", "Disclaimer"], [[i, d] for i, d in enumerate(DISCLAIMERS, 1)], widths=[5, 140],
               group=GROUP, what="What this report is not.")
    book.limit("The evidence tier is not a probability that a drug will work, and the rules have not been tested against drug-development outcomes.")
    book.limit("Retrieved database lines count as support only when their text mentions the disease (a keyword match). Lines you entered carry your own strength and tags.")


def audit_xlsx(au, auto_lines: List, bundle=None, lit=None, question: str = "") -> bytes:
    book = Book(f"Protellect evidence audit: {au.gene}",
                "Early tool, not validated. It rates how well supported a gene-disease link is; it is not a probability that a drug will work.",
                f"Question: {verdict(au, question)['question']}")
    add_audit_sheets(book, au, auto_lines, bundle, lit, question)
    return book.to_bytes()
