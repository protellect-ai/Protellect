# modules/config.py
from __future__ import annotations

# Constants
SIG_SCORE = {
    "pathogenic":5,"likely pathogenic":4,"pathogenic/likely pathogenic":4,
    "risk factor":3,"uncertain significance":2,"conflicting interpretations":2,
    "conflicting interpretations of pathogenicity":2,"likely benign":1,
    "benign":0,"benign/likely benign":0,"not provided":-1,"not classified":-1,
    "4":5,"3":4,"3/4":4,"5":3,"2":2,"1":1,"0":0,
}

SIG_LABEL = {
    "pathogenic": "Disease-causing (Pathogenic)",
    "likely pathogenic": "Likely Disease-causing",
    "pathogenic/likely pathogenic": "Pathogenic / Likely Path.",
    "risk factor": "Risk Factor",
    "uncertain significance": "Unknown Significance (VUS)",
    "conflicting interpretations": "Conflicting Evidence",
    "conflicting interpretations of pathogenicity": "Conflicting Evidence",
    "likely benign": "Likely Harmless (Likely Benign)",
    "benign": "Harmless (Benign)",
    "benign/likely benign": "Benign / Likely Benign",
    "not provided": "Not Classified",
    "not classified": "Not Classified",
    "4":"Likely Disease-causing","3/4":"Pathogenic/LP","5":"Risk Factor",
    "2":"Unknown Significance","1":"Likely Harmless","0":"Harmless",
}

AA_HYDRO = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
            "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
            "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG = {"R":1,"K":1,"H":.5,"D":-1,"E":-1}
AA_NAMES = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
            "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
            "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
            "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}
RANK_CLR = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
RANK_CSS = {"CRITICAL":"bC","HIGH":"bH","MEDIUM":"bM","NEUTRAL":"bN"}
PLAIN = {
    "apoptosis":"cell death (apoptosis)","phosphorylation":"chemical tagging (phosphorylation)",
    "haploinsufficiency":"half-dose shortage (haploinsufficiency)",
    "missense":"letter-swap mutation (missense)","nonsense":"early-stop mutation (stop-gain)",
    "frameshift":"reading-frame shift (frameshift)","splice":"splice-site disruption",
    "dominant negative":"protein blocker (dominant-negative)","gain of function":"hyperactive mutation (gain-of-function)",
    "loss of function":"broken gene (loss-of-function)","germline":"heritable / born-with (germline)",
    "somatic":"acquired / developed (somatic)","heterozygous":"one-copy affected (heterozygous)",
    "homozygous":"both-copies affected (homozygous)","GPCR":"cell-surface signal receiver (GPCR)",
    "second messenger":"internal signal relay (second messenger)","G-protein":"signal relay switch (G-protein)",
    "kinase":"protein tagger/activator (kinase)","phenotype":"observable trait (phenotype)",
    "pathogenic":"disease-causing (pathogenic)","benign":"harmless variant (benign)",
    "VUS":"unknown-significance variant (VUS)","variant":"DNA spelling change (variant)",
}

GOAL_OPTIONS = ["🎯 Identify therapeutic targets","🔬 Understand disease mechanism",
                "💊 Drug discovery & development","📊 Biomarker identification",
                "🧬 Basic research / functional characterisation",
                "🧪 Experimental pathway prioritisation","📋 Clinical variant interpretation",
                "✏️ Custom goal (type below)"]

PLAN_LIMITS = {
    "free": {"searches": 5, "history": 5, "excel": False, "ai_report": False, "price_id": None},
    "pro": {"searches": 200, "history": 100, "excel": True, "ai_report": True, "price_id": "price_pro_monthly"},
    "enterprise": {"searches": 9999, "history": 999, "excel": True, "ai_report": True, "price_id": "price_ent_monthly"},
}

STRIPE_LINKS = {
    "pro": "https://buy.stripe.com/test_pro_placeholder",
    "enterprise": "https://buy.stripe.com/test_ent_placeholder",
}

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

LOGO_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiB2aWV3Qm94PSIwIDAgMjAwIDIwMCI+CiAgPHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iIzAwMDAwMCIvPgo8L3N2Zz4="
LOGO_SVG_RAW = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200"><defs><radialGradient id="bg" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#001a2e" stop-opacity="0.6"/><stop offset="100%" stop-color="#000508" stop-opacity="0"/></radialGradient></defs><circle cx="100" cy="100" r="92" fill="url(#bg)"/></svg>"""
_logo_src = f"data:image/svg+xml;base64,{LOGO_B64}"

# CSV Guide
CSV_GUIDE = {
    "expression": {
        "icon":"📊", "name":"Gene Expression (RNA-seq / Microarray / qPCR)",
        "required_cols":["gene/symbol", "fold_change OR log2FC", "p-value OR padj"],
        "optional_cols":["sample names", "RPKM/TPM/counts"],
        "produces":["Volcano plot","Up/downregulated gene lists","Pathway enrichment (if gene list)","Target prioritisation against ClinVar"],
        "example":"DESeq2 / edgeR output, GEO series matrix, qPCR Ct values",
        "tip":"Export from DESeq2 with gene symbol column named 'gene' and columns 'log2FoldChange' and 'padj'.",
    },
    "variants": {
        "icon":"🧬", "name":"Variant / Mutation Table (VCF-derived / clinical)",
        "required_cols":["gene OR symbol", "variant (HGVS or rsID)", "clinical significance OR consequence"],
        "optional_cols":["chromosome","position","ref","alt","AF (allele frequency)"],
        "produces":["Variant pathogenicity ranking","ClinVar cross-reference","Hotspot mapping","Protein position annotation"],
        "example":"VCF annotated by ANNOVAR/VEP, clinical genetics lab report, gnomAD export",
        "tip":"Include a 'p.' notation column (protein change) for best positional mapping.",
    },
    "proteomics": {
        "icon":"🔬", "name":"Proteomics (MS intensity / LFQ / TMT)",
        "required_cols":["protein/gene name", "intensity OR abundance OR LFQ"],
        "optional_cols":["fold-change","p-value","peptide count","sequence"],
        "produces":["Abundance comparison","Interaction network overlay","Post-translational modification mapping"],
        "example":"MaxQuant proteinGroups.txt, Perseus output, Spectronaut report",
        "tip":"Use 'LFQ intensity' columns from MaxQuant for best quantification.",
    },
    "stats": {
        "icon":"📈", "name":"Statistical Results (GWAS / differential analysis)",
        "required_cols":["identifier (gene/SNP/probe)", "p-value OR q-value"],
        "optional_cols":["effect size","beta","OR","confidence interval"],
        "produces":["Manhattan-style plot","Significant hit prioritisation","ClinVar comparison"],
        "example":"GWAS summary stats, PLINK output, limma/edgeR results",
        "tip":"Include rsID or gene symbol for cross-referencing ClinVar.",
    },
    "generic": {
        "icon":"📋", "name":"Generic tabular data",
        "required_cols":["Any structured columns"],
        "optional_cols":["gene names help link to protein data"],
        "produces":["Data summary","Column statistics","AI-powered interpretation"],
        "example":"Any CSV/TSV from your experiment",
        "tip":"Name columns clearly — gene, protein, sample, treatment, control.",
    },
}

# Research Domains
RESEARCH_DOMAINS = {
    "Neuroscience": {
        "icon": "🧠", "color": "#6366f1", "color2": "#818cf8",
        "tagline": "Synaptic proteins · Neural circuits · Neurodegeneration · BBB · Ion channels",
        "desc": "Deep synaptic biology — presynaptic vesicle machinery, glutamate/GABA receptors, PSD scaffolds, axonal transport, and neurodegeneration. BBB requirements flagged automatically.",
        "proteins": ["APP","SNCA","MAPT","LRRK2","TARDBP","HTT","GBA","SOD1","SHANK3","NRXN1","GRIN2B","GRIA1","DLG4","SNAP25","SYT1","VAMP2","SCN1A","KCNQ2","CACNA1A","KIF5A"],
        "key_experiments": [
            ("iPSC-Neuron (NGN2/NeuroD1) + isogenic control", "2–3 weeks", "Patient-specific neurons; isogenic eliminates background", "#22c55e"),
            ("Multi-electrode array (MEA) — Axion Maestro", "2 weeks", "Network burst rate, synchrony, ISI — seizure vs silence phenotype", "#22c55e"),
        ],
    },
    "Oncology": {
        "icon": "🎗", "color": "#f43f5e", "color2": "#fb7185",
        "tagline": "Metastasis · Early Detection · Patient-Specific · Driver Mutations · Tumour Biology",
        "desc": "Patient-first oncology. Enter cancer type and variant for personalised treatment stratification. Metastasis cascade, early detection, somatic/germline split, companion Dx.",
        "proteins": ["TP53","KRAS","BRCA1","BRCA2","EGFR","MYC","PTEN","BRAF","RB1","CDK4","PIK3CA","APC","VHL","IDH1","ALK","ROS1","ERBB2","PALB2"],
    },
    "Pharmaceuticals": {
        "icon": "💊", "color": "#00d4ff", "color2": "#38bdf8",
        "tagline": "GPCR Targets · Druggability · HTS · Filamin Assay · Clinical Pipeline",
        "desc": "Full drug discovery pipeline. GPCR Filamin piggyback, OpenTargets tractability, ChEMBL scaffolds, ADMET, selectivity panel, patent landscape, clinical development timeline.",
        "proteins": ["ADRB2","ADRB1","AGTR1","DRD2","FLNA","GRK2","OPRM1","CHRM2","HTR2A","ADORA2A","CXCR4","GLP1R","GCGR","GHRL"],
    },
    "Microbiome": {
        "icon": "🦠", "color": "#22c55e", "color2": "#4ade80",
        "tagline": "Annotation Engine · Taxonomy · Host-Microbe · BGC · Pathobionts · SCFA",
        "desc": "AI annotation engine converts vague annotations (biosynthesis, chemosynthesis) to specific EC-numbered pathways. Curated taxonomy KB with animated microbe visuals. BGC prediction, host-receptor mapping.",
        "proteins": [],
    },
    "Molecular Biology": {
        "icon": "⚛️", "color": "#f97316", "color2": "#fb923c",
        "tagline": "Phosphorylation · Kinase-substrate · AlphaFold · STRING · PTMs · Structural",
        "desc": "Deep mechanistic analysis. Phosphorylation cascades, kinase-substrate networks, structural domain function, PPI biology, and full PTM landscape. Integrated with PhosphoSitePlus and AlphaFold.",
        "proteins": ["FLNA","MAPK1","AKT1","SRC","CDK2","EGFR","JAK2","PIK3CA","MTOR","PRKACA","CAMK2A","GSK3B","CHEK1","ATM","AURKA","PLK1"],
    },
    "Rare Disease": {
        "icon": "🧬", "color": "#c084fc", "color2": "#d8b4fe",
        "tagline": "VUS Prioritisation · HPO → Gene · Inheritance · ClinGen · Functional Validation",
        "desc": "The niche Protellect masters. WES/WGS candidate gene triage for rare Mendelian disease labs. HPO phenotype → ranked candidate genes. VUS pathogenicity scoring from ClinVar+AlphaMissense+gnomAD.",
        "proteins": ["BRCA1","BRCA2","TP53","NF1","PTEN","TSC1","TSC2","PKD1","PKD2","HBB","CFTR","DMD","MECP2","FMR1","HTT","LDLR","PAH","HEXA","GBA","LRRK2"],
    },
}
