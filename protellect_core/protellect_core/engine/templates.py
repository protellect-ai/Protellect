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

MATRIX = {
    "label": "Multi-context expression matrix (optional, for the GPCRome analysis)",
    "from": "TPM, counts or log-normalised expression per cell type, tumour or condition (for example pseudobulk of a single-cell atlas)",
    "required": "gene + at least 5 numeric context columns with non-negative values",
    "optional": "more contexts give more statistical power",
    "columns": ["gene", "Tumor cells", "CD8 T cells", "Macrophages", "Fibroblasts", "Endothelial"],
    "rows": [["EXAMPLE_GENE_1", 80.5, 3.2, 5.1, 10.4, 2.2], ["EXAMPLE_GENE_2", 4.0, 60.1, 22.7, 3.3, 1.9]],
}

COUPLING = {
    "label": "G-protein coupling table (optional; replaces the built-in seed)",
    "from": "IUPHAR / GproteinDb primary coupling, or your own measurements",
    "required": "gene + primary coupling (Gs, Gi/o, Gq/11 or G12/13)",
    "optional": "-",
    "columns": ["gene", "primary"],
    "rows": [["ADRB2", "Gs"], ["CXCR4", "Gi/o"], ["AGTR1", "Gq/11"]],
}
ALTERATIONS = {
    "label": "Pan-cancer alteration table (optional)",
    "from": "cBioPortal, GDC / TCGA or your own analysis",
    "required": "gene + cancer type + at least one of mutation, amplification, deletion frequency (0-1 or percent)",
    "optional": "-",
    "columns": ["gene", "cancer_type", "mutation_freq", "amp_freq", "del_freq"],
    "rows": [["EXAMPLE_GENE_1", "HNSC", 0.02, 0.18, 0.0], ["EXAMPLE_GENE_2", "SKCM", 0.05, 0.0, 0.01]],
}

NOT_SUPPORTED = [
    "Raw sequencing reads, FASTQ, BAM or raw VCF files (run your usual pipeline first).",
    "Non-human species (convert to human orthologs first).",
    "Proteomics or metabolomics tables (not parsed in this version).",
]


def template_df(shape: str) -> pd.DataFrame:
    s = SHAPES[shape] if shape in SHAPES else {"matrix": MATRIX, "coupling": COUPLING, "alterations": ALTERATIONS}[shape]
    return pd.DataFrame(s["rows"], columns=s["columns"])


def template_csv(shape: str) -> str:
    return template_df(shape).to_csv(index=False)
