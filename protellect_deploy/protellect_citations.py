"""Protellect citation library — peer-reviewed references + cite() footer helper."""

PROTELLECT_CITATIONS = {
    "uniprot":   ("The UniProt Consortium (2025). UniProt: the universal protein knowledgebase. Nucleic Acids Res. 53, D609–D617.", "https://doi.org/10.1093/nar/gkae1010"),
    "clinvar":   ("Landrum, M. J. et al. (2020). ClinVar: improvements to accessing data. Nucleic Acids Res. 48, D835–D844.", "https://doi.org/10.1093/nar/gkz972"),
    "gnomad":    ("Karczewski, K. J. et al. (2020). The mutational constraint spectrum quantified from variation in 141,456 humans. Nature 581, 434–443.", "https://doi.org/10.1038/s41586-020-2308-7"),
    "alphafold": ("Jumper, J. et al. (2021). Highly accurate protein structure prediction with AlphaFold. Nature 596, 583–589.", "https://doi.org/10.1038/s41586-021-03819-2"),
    "alphamissense": ("Cheng, J. et al. (2023). Accurate proteome-wide missense variant effect prediction with AlphaMissense. Science 381, eadg7492.", "https://doi.org/10.1126/science.adg7492"),
    "string":    ("Szklarczyk, D. et al. (2023). The STRING database in 2023. Nucleic Acids Res. 51, D638–D646.", "https://doi.org/10.1093/nar/gkac1000"),
    "opentargets":("Ochoa, D. et al. (2023). The next-generation Open Targets Platform: reimagined, redesigned, rebuilt. Nucleic Acids Res. 51, D1353–D1359.", "https://doi.org/10.1093/nar/gkac1046"),
    "dgidb":     ("Cannon, M. et al. (2024). DGIdb 5.0. Nucleic Acids Res. 52, D1227–D1235.", "https://doi.org/10.1093/nar/gkad1040"),
    "acmg":      ("Richards, S. et al. (2015). Standards and guidelines for the interpretation of sequence variants: ACMG/AMP. Genet. Med. 17, 405–423.", "https://doi.org/10.1038/gim.2015.30"),
    "clingen":   ("Strande, N. T. et al. (2017). Evaluating the clinical validity of gene-disease associations: ClinGen framework. AJHG 100, 895–906.", "https://doi.org/10.1016/j.ajhg.2017.04.015"),
    "phosphositeplus": ("Hornbeck, P. V. et al. (2015). PhosphoSitePlus 2014: mutations, PTMs and recalibrations. Nucleic Acids Res. 43, D512–D520.", "https://doi.org/10.1093/nar/gku1267"),
    "iuphar_gpcr":("Alexander, S. P. H. et al. (2019). IUPHAR/BPS guide to pharmacology: GPCRs. Br. J. Pharmacol. 176, S21–S141.", "https://doi.org/10.1111/bph.14748"),
    "gpcr_scaffold":("Bockaert, J. & Pin, J. P. (2010). GPCR-interacting proteins (GIPs): nature, functions, and implications. Annu. Rev. Pharmacol. Toxicol. 50, 207–227.", "https://doi.org/10.1146/annurev.pharmtox.42.083101.135950"),
    "genetic_evidence":("Nelson, M. R. et al. (2015). The support of human genetic evidence for approved drug indications. Nat. Genet. 47, 856–860.", "https://doi.org/10.1038/ng.3314"),
    "drug_progression":("King, E. A. et al. (2019). Are drug targets with genetic support twice as likely to be approved? PLoS Genet. 15, e1008489.", "https://doi.org/10.1371/journal.pgen.1008489"),
    "lightgbm":  ("Ke, G. et al. (2017). LightGBM: A highly efficient gradient boosting decision tree. NeurIPS 30.", "https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree"),
    "hotspot":   ("Chang, M. T. et al. (2016). Identifying recurrent mutations in cancer reveals widespread lineage diversity and mutational specificity. Nat. Biotechnol. 34, 155–163.", "https://doi.org/10.1038/nbt.3391"),
    "filamin_scaffold": ("Nakamura, F., Stossel, T. P. & Hartwig, J. H. (2011). The filamins: organizers of cell structure and function. Cell Adh. Migr. 5, 160–169.", "https://doi.org/10.4161/cam.5.2.14401"),
}

def cite(*keys) -> str:
    """Render a small citation footer with linked references for the given keys."""
    items = []
    for k in keys:
        if k in PROTELLECT_CITATIONS:
            cite_text, cite_url = PROTELLECT_CITATIONS[k]
            items.append(
                f"<a href='{cite_url}' target='_blank' style='color:#94a3b8;text-decoration:none;'>"
                f"<span style='color:#a78bfa;'>↗</span> {cite_text}</a>"
            )
    if not items:
        return ""
    return (
        f"<div style='color:var(--text3);font-size:.62rem;margin-top:14px;padding:8px 12px;"
        f"border-top:1px solid var(--border);background:rgba(255,255,255,.01);border-radius:0 0 8px 8px;'>"
        f"<b style='color:var(--text2);letter-spacing:.4px;'>References:</b><br>"
        + "<br>".join(items) +
        f"</div>"
    )