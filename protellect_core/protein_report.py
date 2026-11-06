"""The full Excel report for one searched protein: everything the app retrieved, laid out so nothing is blank or repeated,
plus the evidence audit (when one has been run) in the same workbook.

It reads the typed `Bundle` (adapters.py) so it never depends on the raw shapes of the data sources.
Where a source returned nothing, the sheet says so and says why that might be; it is never silently empty.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Optional

from .adapters import Bundle, mean_plddt
from .literature import LEVELS, classify
from .xlsx_kit import FILLS, Book

G_OVER, G_DATA, G_ABOUT = "Overview", "Retrieved data", "About this report"
SIG_FILL = {"likely pathogenic": "FBD5B5", "pathogenic": FILLS["bad"], "likely benign": FILLS["ok"], "benign": FILLS["good"], "uncertain": FILLS["info"], "conflicting": FILLS["warn"]}


def _int(x) -> Optional[int]:
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _split_conditions(s: str) -> List[str]:
    return [c.strip() for c in str(s or "").split(";") if c.strip() and c.strip().lower() not in ("not provided", "not specified")]


def variant_counts(b: Bundle) -> Dict[str, int]:
    pts = [v for v in b.variants if not v.is_structural]
    st = [v for v in b.variants if v.is_structural]
    return {"total": len(b.variants), "point": len(pts), "structural": len(st),
            "plp_point": sum(v.is_plp for v in pts), "plp_struct": sum(v.is_plp for v in st),
            "vus_point": sum(v.significance == "uncertain" for v in pts), "with_pos": sum(v.pos is not None for v in pts)}


def protein_xlsx(b: Bundle, *, gi: Optional[Mapping] = None, raw: Optional[Mapping] = None, audit: Optional[tuple] = None,
                 fetch_errors: Optional[Mapping] = None, version: str = "") -> bytes:
    """audit = (Audit, auto_lines, lit, question) from the Check any target panel, or None."""
    raw = raw or {}
    gi = gi or {}
    fetch_errors = fetch_errors or {}
    pdata = raw.get("pdata") or {}
    ot = raw.get("ot") or {}
    ot = ot if isinstance(ot, dict) else {}
    cnt = variant_counts(b)
    book = Book(f"Protellect report: {b.gene}" + (f" ({b.name})" if b.name else ""),
                "Everything Protellect retrieved for this protein, with the evidence audit when one was run. Early tool, not validated: hypotheses to test, not findings.",
                (f"Software {version}. " if version else "") + "Public databases only (UniProt, ClinVar, AlphaMissense, gnomAD, STRING, Open Targets, DGIdb, ClinicalTrials.gov, PubMed). Every sheet names its source.")

    # ── Summary ─────────────────────────────────────────────────────────────────────────────────
    au = audit[0] if audit else None
    org = ((pdata.get("organism") or {}).get("scientificName")) if isinstance(pdata, dict) else ""
    rows = [
        ("Gene symbol", b.gene, "Your search"),
        ("Protein name", b.name or "not retrieved", "UniProt"),
        ("UniProt ID", b.uid or (pdata.get("primaryAccession", "") if isinstance(pdata, dict) else ""), "UniProt"),
        ("Organism", org or "not retrieved", "UniProt"),
        ("Protein length (amino acids)", b.length or "not retrieved", "UniProt"),
        ("GPCR", "yes" if b.is_gpcr else "no", "UniProt keyword 'G-protein coupled receptor'"),
        ("ClinVar records retrieved", cnt["total"], "ClinVar (up to 150 records are fetched, most severe first)"),
        ("  small / point variants in this gene", cnt["point"], "Protellect split: records with a protein-level or small change"),
        ("  structural records (copy-number, large deletions or duplications)", cnt["structural"],
         "Protellect split. These often span several genes, so a pathogenic call here does not by itself implicate this gene"),
        ("  pathogenic or likely pathogenic, point variants", cnt["plp_point"], "ClinVar classification"),
        ("  pathogenic or likely pathogenic, structural records", cnt["plp_struct"], "ClinVar classification"),
        ("  uncertain significance, point variants", cnt["vus_point"], "ClinVar classification"),
        ("Disease annotations", len(b.diseases), "UniProt"),
        ("Known drugs / compounds with a recorded interaction", len(b.drugs), "DGIdb and Open Targets"),
        ("Recruiting or active clinical trials found", len(b.trials), "ClinicalTrials.gov, gene-symbol search, recruiting or active only (completed and terminated trials are not retrieved)"),
        ("Interaction partners", len(b.partners), "STRING"),
        ("Mouse knockout phenotypes", len(b.mouse_phenotypes), "Open Targets / IMPC"),
        ("Loss-of-function constraint (pLI)", b.constraint.get("pLI") if b.constraint.get("pLI") is not None else "not retrieved", "gnomAD"),
        ("Observed / expected loss-of-function", b.constraint.get("oe_lof") if b.constraint.get("oe_lof") is not None else "not retrieved", "gnomAD"),
        ("ClinGen gene-disease validity", (f"{b.clingen} (for {(raw.get('clingen') or {}).get('disease')})" if b.clingen and (raw.get("clingen") or {}).get("disease") else b.clingen) or "no classification found",
         "ClinGen: the strongest classification for any disease. See the ClinGen sheet for every disease and its date. It is about that disease, not about yours"),
    ]
    if gi.get("verdict"):
        if cnt["plp_point"] == 0 and cnt["plp_struct"] > 0:
            rows.append(("Variant-burden label", "not applied",
                         f"Protellect's rule of thumb would read '{gi.get('verdict')}', but every pathogenic or likely pathogenic record ({cnt['plp_struct']}) is a structural copy-number record that can span several genes, "
                         "and no small variant in this gene is classified pathogenic. The label would mislead, so it is not shown."))
        else:
            note = "Protellect rule of thumb computed from ClinVar counts (not a published score)."
            if cnt["structural"]:
                note += f" These counts include {cnt['structural']} structural record(s) that may span several genes, so read the ClinVar summary sheet before relying on the label."
            rows.append(("Variant-burden label", f"{gi.get('verdict')} / {str(gi.get('pursue', '')).upper()}", note))
    fills = {}
    if au is not None:
        rows.insert(1, ("Evidence tier (audit)", f"{au.tier} for {au.disease or 'no disease entered'}", "See the Audit sheets: a statement about the evidence, not a probability"))
        fills[1] = au.tier
    book.kv("Summary", f"{b.gene}: summary", "One row per fact, with where it came from. 'Not retrieved' means the source returned nothing: that is different from 'none exists'.",
            rows, widths=(46, 40, 90), fills=fills, group=G_OVER, what="Key facts about the protein and counts from every source.")

    if audit:
        from .audit_report import add_audit_sheets
        add_audit_sheets(book, audit[0], audit[1], b, audit[2], audit[3])
    else:
        book.omit("Evidence audit sheets", "no audit was run for this protein. In the app: Overview > Check any target, enter a disease, optionally search the literature, then download again.")

    # ── ClinVar summary ─────────────────────────────────────────────────────────────────────────
    sigs = Counter((v.significance, "structural" if v.is_structural else "point") for v in b.variants)
    order = ["pathogenic", "likely pathogenic", "uncertain", "conflicting", "likely benign", "benign", "other"]
    srows = [[s, sigs.get((s, "point"), 0), sigs.get((s, "structural"), 0), sigs.get((s, "point"), 0) + sigs.get((s, "structural"), 0)] for s in order if sum(sigs.get((s, t), 0) for t in ("point", "structural"))]
    book.table("ClinVar summary", "ClinVar records by classification and type",
               "Structural records (copy-number changes, large deletions and duplications) often cover several genes at once. Count them separately before saying anything about this gene.",
               ["Classification", "Small / point variants", "Structural records", "All records"], srows, widths=[28, 24, 22, 14], fill_col=0, fill_map=SIG_FILL,
               empty="ClinVar returned no records for this gene, or the fetch failed (see Data sources).", group=G_DATA, what="How many ClinVar records fall in each class, split by small versus structural.")

    conds = Counter()
    conds_plp = Counter()
    for v in b.variants:
        for c in _split_conditions(v.condition):
            conds[c] += 1
            if v.is_plp:
                conds_plp[c] += 1
    book.table("ClinVar conditions", "Conditions named by ClinVar records",
               "Each ClinVar record can name several conditions. Counts are records, not patients.",
               ["Condition", "Records naming it", "Of which pathogenic or likely pathogenic", "Of which structural"],
               [[c, n, conds_plp.get(c, 0), sum(1 for v in b.variants if v.is_structural and c in _split_conditions(v.condition))] for c, n in conds.most_common(60)],
               widths=[70, 18, 26, 18], empty="No condition names were returned with the ClinVar records. This is a retrieval gap to check, not evidence that the gene is unrelated to disease.",
               group=G_DATA, what="Which conditions the ClinVar records name, most frequent first.")

    # ── ClinVar variants ───────────────────────────────────────────────────────────────────────
    def sort_key(v):
        rank = {"pathogenic": 0, "likely pathogenic": 1, "conflicting": 2, "uncertain": 3, "likely benign": 4, "benign": 5}.get(v.significance, 6)
        return (v.is_structural, rank, -(v.stars or 0), v.pos or 10**9)
    vrows = []
    for i, v in enumerate(sorted(b.variants, key=sort_key), 1):
        st = v.is_structural
        vrows.append([i, v.name, f"structural ({len(v.genes)} genes)" if st and len(v.genes) > 1 else ("structural" if st else "small / point"),
                      v.protein_change or "", v.pos if v.pos is not None else None, v.consequence if not st else "", v.significance, v.stars, v.review or "",
                      "; ".join(_split_conditions(v.condition)), "; ".join(v.genes), "somatic" if v.somatic else "", v.am_score if not st else None, v.am_class if not st else "",
                      "n/a (structural)" if st else (v.ml_rank or ""), None if st else v.ml_score, v.url])
    book.table("ClinVar variants", "Every ClinVar record retrieved",
               "Small variants first, structural records after. 'Position' is the protein residue (from the p. change, or coding position for plain exonic changes) and is blank when ClinVar gives none. "
               "AlphaMissense is the worst-case substitution at that residue. Protellect ML rank and score were built for single-residue changes, so they are shown only for those.",
               ["#", "ClinVar name", "Type", "Protein change", "Residue", "Consequence", "Classification", "Review stars (0-4)", "Review status", "Condition(s)", "Genes ClinVar lists",
                "Origin flag", "AlphaMissense", "AM class", "Protellect ML rank", "Protellect ML score", "ClinVar link"],
               vrows, widths=[5, 52, 16, 22, 9, 16, 18, 10, 30, 46, 22, 10, 12, 14, 14, 12, 46], link_cols=[16], fill_col=6, fill_map=SIG_FILL,
               number_formats={12: "0.000", 15: "0.00"}, empty="ClinVar returned no records for this gene, or the fetch failed (see Data sources).", group=G_DATA,
               what="One row per ClinVar record: change, classification, review level, conditions and scores.")

    # ── Diseases ───────────────────────────────────────────────────────────────────────────────
    drows = []
    for d in b.diseases:
        drows.append([d.name, d.source or "UniProt", d.inheritance, d.omim, None, d.desc])
    for c, n in conds.most_common(40):
        drows.append([c, "ClinVar", "", "", n, f"{conds_plp.get(c, 0)} of {n} record(s) are pathogenic or likely pathogenic"])
    for r in (ot.get("disease_associations") or [])[:25]:
        if isinstance(r, dict) and r.get("disease"):
            drows.append([r["disease"], "Open Targets", "", "", None, f"Overall association score {r.get('score')} (0 to 1)  {r.get('url', '')}"])
    book.table("Diseases", "Diseases linked to this gene, by source",
               "Three independent kinds of source, kept apart: UniProt curation, ClinVar condition names, and Open Targets association scores. A disease listed here is a lead to check, not proof of causation.",
               ["Disease or condition", "Source", "Inheritance", "OMIM", "ClinVar records", "Detail"], drows, widths=[52, 16, 20, 10, 14, 90],
               empty="UniProt lists no disease for this gene, ClinVar records named no condition, and Open Targets returned no association. Check Data sources for failed calls.",
               group=G_DATA, what="Disease links from UniProt, ClinVar and Open Targets.")

    # ── Domains with variant overlap + hotspots ────────────────────────────────────────────────
    pts = [v for v in b.variants if not v.is_structural and v.pos is not None]
    plp_pts = [v for v in pts if v.is_plp]
    dom = []
    for d in sorted(b.domains + b.sites, key=lambda x: (x["start"], x["end"])):
        inside = [v for v in pts if d["start"] <= v.pos <= d["end"]]
        dom.append([d["type"], d["desc"], d["start"], d["end"], d["end"] - d["start"] + 1, len(inside), sum(v.is_plp for v in inside)])
    book.table("Domains and sites", "UniProt domains and sites, with ClinVar variants that fall inside",
               "Counts use only small variants that have a protein residue. A domain with many variants may simply be a large domain, or one that was sequenced more.",
               ["Type", "Description", "Start", "End", "Length", "Small variants inside", "Pathogenic or likely pathogenic inside"], dom,
               widths=[22, 56, 8, 8, 8, 18, 22], empty="UniProt lists no domain, region or site features for this protein.", group=G_DATA, what="Where the variants fall relative to known protein regions.")

    book.table("Hotspots", "Clusters of pathogenic variants along the protein",
               "A cluster is 3 or more pathogenic or likely pathogenic small variants in a 20-residue window at 4 times or more the protein-wide average density. This is a Protellect rule of thumb, not a published statistic.",
               ["Cluster", "Start residue", "End residue", "Pathogenic count", "Fold over average"], [[i, h.start, h.end, h.count, h.fold] for i, h in enumerate(b.hotspots, 1)],
               widths=[10, 14, 14, 18, 18], number_formats={4: "0.0"},
               empty=f"No cluster met the rule. {len(plp_pts)} pathogenic or likely pathogenic small variant(s) have a protein residue, out of {cnt['point']} small variants and {cnt['structural']} structural record(s); "
                     "too few located variants, or variants spread out, give no cluster. This says nothing about whether hotspots exist.",
               group=G_DATA, what="Regions where pathogenic variants concentrate.")

    # ── Gene context ───────────────────────────────────────────────────────────────────────────
    tr = ot.get("tractability") if isinstance(ot.get("tractability"), dict) else {}
    ens = ot.get("ensembl_id", "")
    plddt = mean_plddt(b.pdb)
    ctx = [
        ("Tissue specificity (UniProt)", b.tissue_text or "not recorded", "UniProt"),
        ("Subcellular location", "; ".join(x for x in b.subcellular if x) or "not recorded", "UniProt"),
        ("Small-molecule tractability", "; ".join(tr.get("Small molecule", [])) or ("none returned" if tr else "not retrieved"), "Open Targets"),
        ("Antibody tractability", "; ".join(tr.get("Antibody", [])) or ("none returned" if tr else "not retrieved"), "Open Targets"),
        ("PROTAC tractability", "; ".join(tr.get("PROTAC", [])) or ("none returned" if tr else "not retrieved"), "Open Targets"),
        ("Highest-expressing tissues (RNA)", "; ".join(f"{t} ({v})" for t, v in (ot.get("top_tissues") or [])[:8]) or "not retrieved", "Open Targets / Expression Atlas"),
        ("Mean AlphaFold confidence (pLDDT)", round(plddt, 1) if plddt else "no structure loaded", "AlphaFold model; above 70 is generally treated as confident"),
        ("Known-drug rows reported by Open Targets", b.n_known_drugs, "Open Targets"),
        ("UniProt entry", f"https://www.uniprot.org/uniprotkb/{b.uid}" if b.uid else "", "Link"),
        ("ClinVar records for this gene", f"https://www.ncbi.nlm.nih.gov/clinvar/?term={b.gene}%5Bgene%5D", "Link"),
        ("Open Targets target page", f"https://platform.opentargets.org/target/{ens}" if ens else f"https://platform.opentargets.org/search?q={b.gene}", "Link"),
        ("gnomAD gene page", f"https://gnomad.broadinstitute.org/gene/{b.gene}", "Link"),
        ("ClinicalTrials.gov, all statuses", f"https://clinicaltrials.gov/search?term={b.gene}", "Link: includes completed and terminated trials, which this report does not retrieve"),
    ]
    ws = book.kv("Gene context", f"{b.gene}: gene and protein context", "Tissue, location, tractability and structure confidence, with links to check each at the source.", ctx,
                 widths=(40, 90, 60), group=G_DATA, what="Tissue, location, tractability, structure confidence and source links.")
    for r in ws.iter_rows(min_row=5, max_row=4 + len(ctx), min_col=2, max_col=2):
        for c in r:
            if isinstance(c.value, str) and c.value.startswith("http"):
                c.hyperlink = c.value

    cg = raw.get("clingen") or {}
    book.table("ClinGen", "ClinGen gene-disease validity: every disease classified for this gene",
               "ClinGen's expert panels rate how strong the evidence is that a gene causes a specific disease (Definitive, Strong, Moderate, Limited, Disputed, Refuted). A rating belongs to that disease only: "
               "a 'Refuted' for one disease does not say anything about a different disease or about drug targeting, and it is not evidence about your disease unless it is the same condition.",
               ["Disease", "Classification", "Date", "Standard", "Report"],
               [[c.get("disease"), c.get("classification"), c.get("date"), c.get("sop"), c.get("url")] for c in (cg.get("classifications") or []) if isinstance(c, dict)],
               widths=[56, 18, 14, 12, 56], link_cols=[4], fill_col=1, fill_map={"definitive": FILLS["good"], "strong": FILLS["good"], "moderate": FILLS["ok"], "limited": FILLS["warn"],
                                                                                  "disputed": FILLS["bad"], "refuted": FILLS["bad"], "no known": FILLS["none"]},
               empty="ClinGen lists no gene-disease classification for this gene, or the download failed (see Data sources).", group=G_DATA, what="ClinGen expert-panel classification for each disease.")

    # ── Drugs ──────────────────────────────────────────────────────────────────────────────────
    seen, rows_d = set(), []
    for d in b.drugs:
        key = (d.name.upper(), "ot" if d.source == "Open Targets" else "dgidb")
        if key in seen:
            continue
        seen.add(key)
        is_ot = d.source == "Open Targets"
        rows_d.append([d.name, "Open Targets" if is_ot else "DGIdb", d.mechanism if is_ot else (d.kind if d.kind and d.kind.lower() != "unknown" else "not recorded"),
                       d.phase if is_ot else "", d.indication if is_ot else "", "" if is_ot else d.source, d.url])
    book.table("Drugs", "Compounds with a recorded interaction with this protein",
               "These are records of interaction, not approvals or recommendations. Phase and indication come only from Open Targets. 'Underlying sources' are the databases DGIdb drew each record from.",
               ["Compound", "Database", "Interaction type or mechanism", "Max clinical phase", "Indication", "Underlying sources", "Link"], rows_d,
               widths=[26, 14, 30, 16, 36, 40, 44], link_cols=[6], empty="DGIdb and Open Targets returned no compound for this gene, or the calls failed (see Data sources).",
               group=G_DATA, what="Drugs and tool compounds with a recorded interaction.")

    # ── Interactions ───────────────────────────────────────────────────────────────────────────
    def band(sc):
        sc = sc or 0
        return "highest (900+)" if sc >= 900 else "high (700+)" if sc >= 700 else "medium (400+)" if sc >= 400 else "low"
    srows2 = []
    for p in raw.get("string") or []:
        if isinstance(p, dict) and p.get("partner"):
            sc = _int(p.get("score"))
            srows2.append([p["partner"], sc, band(sc), _int(p.get("experiments")), _int(p.get("coexpression")), p.get("url", "")])
    book.table("Interactions", "Predicted and known protein partners (STRING)",
               "STRING combined scores run 0 to 1000. The band uses STRING's own cut-offs (400 medium, 700 high, 900 highest). A score mixes experiments, databases, text mining and co-expression, so read the experiment column too.",
               ["Partner", "Combined score", "Confidence band", "Experimental score", "Co-expression score", "STRING link"], srows2,
               widths=[22, 16, 18, 18, 18, 52], link_cols=[5], number_formats={1: "0", 3: "0", 4: "0"}, empty="STRING returned no partner, or the call failed (see Data sources).",
               group=G_DATA, what="Interaction partners with confidence bands.")

    book.table("Mouse knockouts", "Mouse knockout phenotypes (Open Targets / IMPC)",
               "Phenotypes seen when this gene is disrupted in mice. Mouse results do not always carry over to humans: compare with the human genetics before relying on them.",
               ["Phenotype", "Phenotype ID", "Phenotype class(es)", "Mouse models"],
               [[m.get("label"), m.get("id"), m.get("classes"), m.get("models")] for m in b.mouse_phenotypes], widths=[56, 16, 56, 14],
               empty="Open Targets returned no mouse phenotype for this gene, or the call failed (see Data sources). No knockout data is not evidence of no phenotype.",
               group=G_DATA, what="What happens in mice when the gene is knocked out.")

    book.table("Clinical trials", "Clinical trials found",
               f"ClinicalTrials.gov, searched by the gene symbol '{b.gene}', recruiting or active trials only, up to 8. Completed or terminated trials (for example an earlier phase 3 programme) are NOT retrieved: "
               f"search all statuses at https://clinicaltrials.gov/search?term={b.gene}. A trial that mentions the symbol may not test this protein.",
               ["NCT ID", "Title", "Status", "Phase", "Link"], [[t.get("nct_id", ""), t.get("title", ""), t.get("status", ""), t.get("phase", ""), t.get("url", "")] for t in b.trials],
               widths=[16, 90, 24, 12, 48], link_cols=[4], fill_col=2, fill_map={"recruiting": FILLS["good"], "active": FILLS["ok"]},
               empty=f"No recruiting or active trial matched '{b.gene}', or the call failed (see Data sources). Check all statuses at https://clinicaltrials.gov/search?term={b.gene}.",
               group=G_DATA, what="Recruiting or active trials that mention the gene symbol.")

    prow = []
    for p in b.papers:
        yr = _int(p.get("year"))
        lv = ", ".join(dict(LEVELS).get(k, k) for k in classify(p)) or "not classified"
        prow.append([p.get("pmid", ""), p.get("title", ""), p.get("authors", ""), p.get("journal", ""), yr if yr else p.get("year", ""), lv, p.get("url", "")])
    book.table("Literature", "Papers retrieved for this protein",
               "From PubMed searches run for the protein. 'Level' is a keyword guess (human clinical, human genetics, animal, cell, review), not a reading of the paper. Absence of a paper here is not absence in the literature.",
               ["PMID", "Title", "Authors", "Journal", "Year", "Level (by keyword)", "Link"], prow, widths=[12, 84, 34, 30, 8, 40, 42], link_cols=[6],
               empty="No paper was retrieved, or the PubMed call failed (see Data sources).", group=G_DATA, what="PubMed records with a keyword evidence level.")

    # ── Data sources and methods ───────────────────────────────────────────────────────────────
    srcs = []
    for d in b.audit:
        srcs.append([d.name.strip(), d.n, "ok" if d.n else "empty", d.note])
    for k, v in {**b.source_errors, **{k: v for k, v in fetch_errors.items() if v}}.items():
        srcs.append([k, "", "error", str(v)])
    book.table("Data sources", "Which sources returned data in this run",
               "Use this to tell a real 'none' from a failed call. 'empty' can mean the source has nothing, or that the call failed quietly: errors are listed below when the app recorded one.",
               ["Source", "Records", "Status", "Note or error"], srcs, widths=[48, 12, 12, 100], fill_col=2, fill_map={"ok": FILLS["good"], "empty": FILLS["warn"], "error": FILLS["bad"]},
               empty="No source audit is available.", group=G_ABOUT, what="Source-by-source record counts and any errors.")

    book.text("Methods and limits", "How the numbers in this report were made", "", [
        ("Small versus structural records", "A record is called structural when ClinVar labels it a copy-number change, deletion, duplication, inversion or translocation without a protein change, when its name has a genomic range or copy number, or when it lists more than one gene. Everything else is treated as small."),
        ("Residue position", "Taken from the protein change (p.) in the ClinVar name, or from the coding position (c.) divided by 3 for plain exonic changes. Intronic, range and structural records get no position. A genomic coordinate is never used as a residue."),
        ("Protellect ML rank and score", "A rule-based score built for single-residue changes. It is a prioritisation aid, not a pathogenicity call, and it has not been validated against outcomes. It is not shown for structural records."),
        ("Variant-burden label", "A rule of thumb from the share of pathogenic ClinVar records. It is not a published score."),
        ("Hotspots", "3 or more pathogenic or likely pathogenic small variants in a 20-residue window at 4 times or more the protein-wide density. Design choice, not a statistical test."),
        ("Literature levels", "Keyword matching on the title, abstract and publication type. One paper can sit in several levels. Direction (supports or argues against) is not judged."),
        ("Evidence tier", "Only present when an audit was run. Written rules count separate studies and kinds of evidence. It is not a probability that a drug will work."),
    ], widths=(34, 150), group=G_ABOUT, what="Definitions and design choices behind the derived numbers.")

    book.omit("Experiment cost, return-on-investment and success-probability table", "removed: the costs and probabilities had no source. Use the Audit red-flag sheet's cheapest checks instead.")
    book.omit("Estimated patient numbers and orphan-drug eligibility", "removed: they came from a hand-typed table with no source, so the report no longer prints them.")
    book.limit("Hypotheses to test, not findings. Nothing in this report has been validated in the lab.")
    book.limit("Public databases are incomplete and uneven: a gene studied more heavily has more records. More records is not stronger evidence.")
    book.limit("'Not retrieved' and 'empty' can mean a failed call. Check the Data sources sheet before concluding anything is absent.")
    return book.to_bytes()
