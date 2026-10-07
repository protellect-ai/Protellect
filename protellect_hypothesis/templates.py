"""Single source of truth for 'what to upload': used by the app UI, the downloadable templates, and the user guide."""
from __future__ import annotations

import pandas as pd

GENERAL_RULES = [
    "Human gene symbols (HGNC), for example GPR151. Ensembl IDs and mouse symbols are not converted.",
    "One row per gene. If a gene appears twice, the row with the strongest effect is kept.",
    "CSV or TSV with a header row.",
    "Processed results from your analysis, not raw reads or raw VCFs.",
    "Fill in disease and tissue. The engine uses them as evidence, so leaving them blank means fewer hypotheses.",
]

SHAPES = {
    "expression": {
        "label": "Differential expression",
        "from": "RNA-seq, microarray or qPCR panel, after your differential analysis",
        "required": "gene + a fold-change column (log2FoldChange, log2FC, logFC, foldchange)",
        "optional": "adjusted p-value (padj, FDR, pvalue)",
        "columns": ["gene", "log2FoldChange", "padj"],
        "rows": [["EXAMPLE_GENE_1", 1.8, 0.001], ["EXAMPLE_GENE_2", -1.2, 0.02]],
    },
    "variant": {
        "label": "Variant / association",
        "from": "GWAS output or a processed patient-cohort sequencing study",
        "required": "gene + a variant id column (variant, rsid, snp) + an effect column (odds_ratio, beta, effect)",
        "optional": "p-value",
        "columns": ["gene", "rsid", "odds_ratio", "p_value"],
        "rows": [["EXAMPLE_GENE_1", "rs0000001", 1.4, 0.00001], ["EXAMPLE_GENE_2", "rs0000002", 0.8, 0.03]],
    },
    "screen": {
        "label": "Functional screen hits",
        "from": "CRISPR or RNAi screen, or a reporter / viability assay panel",
        "required": "gene + a phenotype column (phenotype_score, score, zscore)",
        "optional": "p-value",
        "columns": ["gene", "phenotype_score", "p_value"],
        "rows": [["EXAMPLE_GENE_1", -2.3, 0.004], ["EXAMPLE_GENE_2", 0.4, 0.4]],
    },
}

NOT_SUPPORTED = [
    "Raw sequencing reads, FASTQ, BAM or raw VCF files (run your usual pipeline first).",
    "Non-human species (convert to human orthologs first).",
    "Proteomics or metabolomics tables (not parsed in this version).",
]


def template_df(shape: str) -> pd.DataFrame:
    s = SHAPES[shape]
    return pd.DataFrame(s["rows"], columns=s["columns"])


def template_csv(shape: str) -> str:
    return template_df(shape).to_csv(index=False)
